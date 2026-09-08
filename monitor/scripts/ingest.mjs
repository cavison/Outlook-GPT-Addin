#!/usr/bin/env node
// Put a batch of KPI readings on the map.
//
//   node scripts/ingest.mjs <kpi-id> <file.csv|file.json|file.xlsx> [options]
//   node scripts/ingest.mjs --list
//   cat batch.json | node scripts/ingest.mjs --stdin
//
//   --as-of 2026-09-08     when the readings were taken (default: today)
//   --source "signage API" where they came from, for the audit trail
//   --sheet  "Sheet1"      which tab, for xlsx
//   --dry-run              validate and report, write nothing
//
// This is the same normalizer the HTTP endpoint uses, so a file dropped by hand
// and a Power Automate flow posting JSON land in exactly the same place in
// exactly the same shape. See docs/INGEST.md.

import fs from 'node:fs';
import path from 'node:path';
import { loadRegistry, validateBatch, writeBatch, scaleFor, scoreReading, KINDS } from '../server/kpi.js';

// Column names people actually use, so an export does not have to be edited
// before it can be ingested. Declared up here because the work below runs at
// module top level, before any `const` further down exists.
const ALIASES = {
  property: ['property', 'community', 'community name', 'property name', 'site', 'location'],
  value: ['value', 'variance', 'count', 'actual', 'result', 'online', 'completed', 'status', 'done'],
  total: ['total', 'installed', 'expected', 'due', 'possible', 'denominator'],
  budget: ['budget', 'ytd budget'],
  actual: ['ytd actual', 'actual'],
  target: ['target', 'goal', 'standard'],
  applicable: ['applicable', 'n/a', 'na'],
  note: ['note', 'notes', 'comment', 'reason'],
  url: ['url', 'link'],
};

const args = process.argv.slice(2);
const flag = (name, fallback = null) => {
  const i = args.indexOf(`--${name}`);
  return i === -1 ? fallback : args[i + 1];
};
const has = (name) => args.includes(`--${name}`);
const positional = args.filter((a, i) => !a.startsWith('--') && !args[i - 1]?.startsWith('--'));

const registry = loadRegistry();

if (has('list') || (!positional.length && !has('stdin'))) {
  listKpis();
  process.exit(has('list') ? 0 : 1);
}

let batch;

if (has('stdin')) {
  batch = JSON.parse(fs.readFileSync(0, 'utf8'));
} else {
  const [kpiId, file] = positional;
  if (!kpiId || !file) {
    console.error('Usage: node scripts/ingest.mjs <kpi-id> <file> [--as-of DATE] [--source TEXT]');
    process.exit(1);
  }
  if (!registry[kpiId]) {
    console.error(`Unknown KPI "${kpiId}".\n`);
    listKpis();
    process.exit(1);
  }
  if (!fs.existsSync(file)) {
    console.error(`No such file: ${file}`);
    process.exit(1);
  }
  batch = {
    kpi: kpiId,
    asOf: flag('as-of') ?? new Date().toISOString(),
    source: flag('source') ?? path.basename(file),
    rows: await readRows(file, registry[kpiId]),
  };
}

const result = validateBatch(batch, registry);
if (!result.ok) {
  console.error(`\n  ${result.errors.length} problem(s) — nothing was written:\n`);
  for (const e of result.errors.slice(0, 25)) console.error(`    - ${e}`);
  if (result.errors.length > 25) console.error(`    … and ${result.errors.length - 25} more`);
  console.error('');
  process.exit(1);
}

report(result.batch, registry[result.batch.kpi]);

if (has('dry-run')) {
  console.log('  --dry-run: nothing written.\n');
  process.exit(0);
}

const written = writeBatch(result.batch);
console.log(`  Wrote ${path.relative(process.cwd(), written)}`);
console.log('  data/ is gitignored — readings stay off GitHub.\n');

// ---------------------------------------------------------------------------

function listKpis() {
  console.log('\n  KPIs in config/kpis.json:\n');
  const width = Math.max(...Object.keys(registry).map((k) => k.length));
  for (const [id, spec] of Object.entries(registry)) {
    const where = spec.parcel ? `parcel ${spec.parcel}` : 'no parcel';
    console.log(
      `    ${id.padEnd(width)}  ${spec.kind.padEnd(8)} ${where.padEnd(11)} ${spec.cadence.padEnd(9)} ${spec.label}`,
    );
  }
  console.log(`\n  Kinds: ${KINDS.join(', ')}. Columns expected per kind:\n`);
  console.log('    variance   property, value (budget - actual), [budget], [actual]');
  console.log('    ratio      property, value, total');
  console.log('    count      property, value, [target]');
  console.log('    boolean    property, value (yes/no, true/false, done/missing)');
  console.log('    label      property, value');
  console.log('\n  Any row may also carry: applicable (false = not applicable here),');
  console.log('  note, url. See docs/INGEST.md.\n');
}

/** Read rows from CSV, JSON or a spreadsheet, mapping loose column names. */
async function readRows(file, spec) {
  const ext = path.extname(file).toLowerCase();
  if (ext === '.json') {
    const parsed = JSON.parse(fs.readFileSync(file, 'utf8'));
    const rows = Array.isArray(parsed) ? parsed : parsed.rows;
    if (!Array.isArray(rows)) throw new Error('JSON must be an array of rows, or { rows: [...] }');
    return rows;
  }
  if (ext === '.csv' || ext === '.tsv') {
    return mapColumns(parseDelimited(fs.readFileSync(file, 'utf8'), ext === '.tsv' ? '\t' : ','), spec);
  }
  if (['.xlsx', '.xls', '.xlsm'].includes(ext)) {
    const { default: xlsx } = await import('xlsx');
    const book = xlsx.readFile(file);
    const name = flag('sheet') ?? book.SheetNames[0];
    const sheet = book.Sheets[name];
    if (!sheet) throw new Error(`No sheet "${name}". Present: ${book.SheetNames.join(', ')}`);
    return mapColumns(xlsx.utils.sheet_to_json(sheet, { defval: null }), spec);
  }
  throw new Error(`Don't know how to read ${ext} — use .csv, .json or .xlsx`);
}

/**
 * A small CSV reader rather than a dependency. Handles quoted fields and
 * embedded commas and newlines, which is all a KPI export ever needs.
 */
function parseDelimited(text, sep) {
  const rows = [];
  let row = [];
  let field = '';
  let quoted = false;

  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"') {
        if (text[i + 1] === '"') { field += '"'; i++; } else quoted = false;
      } else field += c;
      continue;
    }
    if (c === '"') { quoted = true; continue; }
    if (c === sep) { row.push(field); field = ''; continue; }
    if (c === '\r') continue;
    if (c === '\n') { row.push(field); rows.push(row); row = []; field = ''; continue; }
    field += c;
  }
  if (field !== '' || row.length) { row.push(field); rows.push(row); }

  const header = (rows.shift() ?? []).map((h) => h.trim());
  return rows
    .filter((r) => r.some((c) => String(c).trim() !== ''))
    .map((r) => Object.fromEntries(header.map((h, i) => [h, r[i] ?? ''])));
}

function mapColumns(records, spec) {
  if (!records.length) return [];
  const keys = Object.keys(records[0]);
  const pick = {};
  for (const [field, names] of Object.entries(ALIASES)) {
    const match = keys.find((k) => names.includes(String(k).trim().toLowerCase()));
    if (match) pick[field] = match;
  }
  if (!pick.property) {
    throw new Error(
      `No property column. Found: ${keys.join(', ')}.\n` +
        `  Rename one to "Property" (or ${ALIASES.property.slice(1).join(', ')}).`,
    );
  }
  if (!pick.value) {
    throw new Error(
      `No value column for a ${spec.kind} KPI. Found: ${keys.join(', ')}.\n` +
        `  Rename one to "Value".`,
    );
  }

  return records.map((rec) => {
    const row = { property: rec[pick.property] };
    for (const field of ['value', 'total', 'budget', 'actual', 'target', 'note', 'url']) {
      if (pick[field] != null && rec[pick[field]] !== '' && rec[pick[field]] != null) {
        row[field] = field === 'note' || field === 'url' ? rec[pick[field]] : cleanNumeric(rec[pick[field]], field, spec);
      }
    }
    if (pick.applicable != null) {
      const raw = String(rec[pick.applicable] ?? '').trim().toLowerCase();
      if (['no', 'false', '0', 'n/a', 'na', 'not applicable'].includes(raw)) row.applicable = false;
    }
    return row;
  });
}

/** Strip $ and thousands separators; leave booleans and labels alone. */
function cleanNumeric(raw, field, spec) {
  if (spec.kind === 'boolean' && field === 'value') return raw;
  if (spec.kind === 'label' && field === 'value') return raw;
  if (typeof raw === 'number') return raw;
  const s = String(raw).trim();
  const n = Number(s.replace(/[$,\s%]/g, '').replace(/^\((.*)\)$/, '-$1'));
  return Number.isFinite(n) ? n : raw;
}

function report(batch, spec) {
  const rows = batch.rows;
  const na = rows.filter((r) => r.applicable === false).length;
  const scale = spec.kind === 'variance' ? scaleFor(batch) : null;
  const scored = rows
    .filter((r) => r.applicable !== false)
    .map((r) => scoreReading(r, spec, { scale }).severity);

  const bands = { failed: 0, blocked: 0, warning: 0, flat: 0 };
  for (const s of scored) {
    if (s >= 0.75) bands.failed++;
    else if (s >= 0.5) bands.blocked++;
    else if (s >= 0.28) bands.warning++;
    else bands.flat++;
  }

  console.log(`\n  ${spec.label} — ${rows.length} rows as of ${batch.asOf.slice(0, 10)}`);
  console.log(`  source: ${batch.source}`);
  if (scale) console.log(`  scale: $${Math.round(scale).toLocaleString('en-US')} (90th percentile unfavourable)`);
  console.log(
    `  ${bands.flat} flat · ${bands.warning} degraded · ${bands.blocked} blocked · ${bands.failed} failed` +
      (na ? ` · ${na} not applicable` : ''),
  );
}
