#!/usr/bin/env node
// bughunt evidence gate: a plain script (no AI) that checks every finding's evidence after a hunt.
//
//   node evidence-gate.mjs <findings.json> [project root]
//
// Code evidence: the cited file must exist inside the project, and the quoted code must appear within
// WINDOW lines of the cited line. If the quote is found elsewhere in the same file, the line number is
// corrected and noted. Runtime evidence: the screenshot file must exist and be non-empty, and the
// reproduction steps must be non-empty. Every finding also needs "checkpoint" and "evidence_type".
//
// Findings that fail are moved from "confirmed"/"disputed" to "rejected_evidence", so they can never
// enter a fix plan. The file is rewritten in place and "clean" is recomputed.
import { readFileSync, writeFileSync, statSync, existsSync } from 'node:fs'
import { resolve, relative, isAbsolute, dirname } from 'node:path'

const WINDOW = 10
const SEV = ['critical', 'high', 'medium', 'low']

const [, , findingsPath, rootArg] = process.argv
if (!findingsPath) {
  console.error('usage: node evidence-gate.mjs <findings.json> [project root]')
  process.exit(2)
}
const findings = JSON.parse(readFileSync(findingsPath, 'utf8'))
const root = resolve(rootArg || findings.root || process.cwd())

const norm = s => String(s).replace(/\s+/g, ' ').trim()
const fileCache = new Map()
function readLines(abs) {
  if (!fileCache.has(abs)) fileCache.set(abs, readFileSync(abs, 'utf8').split(/\r?\n/).map(norm))
  return fileCache.get(abs)
}

// Turn a quoted snippet into normalized lines worth matching: strip line-number prefixes ("42:", "42 |", "L42:"),
// quote markers and ellipses; drop lines that are only punctuation.
function quoteLines(evidence) {
  return String(evidence || '').split(/\r?\n/)
    .map(l => l.replace(/^\s*(?:L?\d+\s*[:|]\s?|>\s?)/, ''))
    .map(l => l.replace(/^\s*(?:\.\.\.|…)\s*/, '').replace(/\s*(?:\.\.\.|…)\s*$/, ''))
    .map(norm)
    .filter(l => l.length >= 4 && !/^[\s{}()[\];,.]*$/.test(l))
}

function insideRoot(abs) {
  const rel = relative(root, abs)
  return rel === '' || (!rel.startsWith('..') && !isAbsolute(rel))
}

function checkCode(f) {
  if (!f.file) return { ok: false, reason: 'missing file' }
  if (!Number.isInteger(f.line) || f.line < 1) return { ok: false, reason: 'missing or invalid line' }
  const abs = resolve(root, String(f.file))
  if (!insideRoot(abs)) return { ok: false, reason: `file is outside the project: ${f.file}` }
  if (!existsSync(abs) || !statSync(abs).isFile()) return { ok: false, reason: `file not found: ${f.file}` }
  const lines = readLines(abs)
  const quotes = quoteLines(f.evidence)
  if (!quotes.length) return { ok: false, reason: 'no quotable code in evidence' }
  const significant = quotes.filter(q => q.length >= 8)
  const probe = significant.length ? significant : quotes
  const need = Math.max(1, Math.ceil(probe.length / 2))
  const hits = (from, to) => {
    let n = 0, first = -1
    for (const q of probe) {
      for (let i = Math.max(0, from); i <= Math.min(lines.length - 1, to); i++) {
        if (lines[i].includes(q)) { n++; if (first < 0) first = i; break }
      }
    }
    return { n, first }
  }
  const near = hits(f.line - 1 - WINDOW, f.line - 1 + WINDOW)
  if (near.n >= need) return { ok: true, reason: `quoted code found near line ${f.line}` }
  const anywhere = hits(0, lines.length - 1)
  if (anywhere.n >= need) {
    return { ok: true, reason: `quoted code found at line ${anywhere.first + 1}, not near cited line ${f.line}; line corrected`, corrected_line: anywhere.first + 1 }
  }
  return { ok: false, reason: `quoted code not found in ${f.file} (${near.n}/${probe.length} quoted lines near line ${f.line})` }
}

function checkRuntime(f) {
  const shot = f.screenshot || f.screenshot_path
  if (!shot) return { ok: false, reason: 'missing screenshot' }
  const abs = isAbsolute(shot) ? shot : [resolve(root, shot), resolve(dirname(resolve(findingsPath)), shot)].find(p => existsSync(p))
  if (!abs || !existsSync(abs) || !statSync(abs).isFile() || statSync(abs).size === 0) return { ok: false, reason: `screenshot missing or empty: ${shot}` }
  const steps = Array.isArray(f.steps) ? f.steps.filter(s => norm(s).length > 0) : []
  if (!steps.length) return { ok: false, reason: 'no reproduction steps' }
  return { ok: true, reason: 'screenshot exists and steps are present' }
}

function check(f) {
  for (const field of ['checkpoint', 'evidence_type', 'severity']) {
    if (!f[field]) return { ok: false, reason: `missing required field "${field}"` }
  }
  if (!SEV.includes(f.severity)) return { ok: false, reason: `invalid severity "${f.severity}"` }
  if (f.evidence_type === 'code') return checkCode(f)
  if (f.evidence_type === 'runtime') return checkRuntime(f)
  return { ok: false, reason: `unknown evidence_type "${f.evidence_type}"` }
}

const rejected = Array.isArray(findings.rejected_evidence) ? findings.rejected_evidence : []
const newlyRejected = []
let checked = 0, passed = 0, corrected = 0
for (const list of ['confirmed', 'disputed']) {
  const keep = []
  for (const f of findings[list] || []) {
    checked++
    let res
    try { res = check(f) } catch (e) { res = { ok: false, reason: `check failed: ${e.message}` } }
    f.evidence_check = { ok: res.ok, reason: res.reason }
    if (res.corrected_line) { f.evidence_check.line_corrected_from = f.line; f.line = res.corrected_line; corrected++ }
    if (res.ok) { passed++; keep.push(f) } else newlyRejected.push({ ...f, rejected_from: list })
  }
  findings[list] = keep
}
findings.rejected_evidence = [...rejected, ...newlyRejected]

// Recompute "clean" from what survived the gate.
const blocking = (findings.confirmed || []).filter(b => b.blocks)
const openRegressions = (findings.regressions || []).filter(r => r.status === 'still-present' || r.status === 'partially-fixed')
const coverageComplete = !!(findings.coverage && findings.coverage.complete)
if (findings.stats) findings.stats.blocking = blocking.length
findings.clean = blocking.length === 0 && openRegressions.length === 0 && coverageComplete
findings.evidence_gate = { checked, passed, rejected: checked - passed, lines_corrected: corrected, window_lines: WINDOW }

writeFileSync(findingsPath, JSON.stringify(findings, null, 2) + '\n')
console.log(JSON.stringify(findings.evidence_gate))
for (const r of newlyRejected) console.log(`rejected ${r.id || ''} ${r.file || ''}:${r.line || ''} - ${r.evidence_check.reason}`)
