// Offline tests for the bughunt kit (no agents, no tokens). Run: node .claude/bughunt-tests/test.mjs
import assert from 'node:assert/strict'
import { fileURLToPath } from 'node:url'
import { mkdtempSync, writeFileSync, readFileSync, mkdirSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { execFileSync } from 'node:child_process'
import { runWorkflow } from './harness.mjs'

const WF = fileURLToPath(new URL('../workflows', import.meta.url))
const GATE = fileURLToPath(new URL('../skills/bughunt/evidence-gate.mjs', import.meta.url))
let failures = 0
async function test(name, fn) {
  try { await fn(); console.log('PASS', name) } catch (e) { failures++; console.log('FAIL', name, '\n   ', e.message.split('\n')[0], '\n   ', (e.stack.split('\n').find(l => l.includes('test.mjs')) || '').trim()) }
}

// Checkpoint ids a hunter prompt asks for, e.g. "[logic] Core logic..." lines.
const idsIn = prompt => [...prompt.matchAll(/^\[([a-z-]+)\] /gm)].map(m => m[1])
const attest = (prompt, except = []) => idsIn(prompt).filter(id => !except.includes(id)).map(id => ({ id, status: 'checked' }))
const bug = (o) => ({ severity: 'medium', category: 'logic', description: 'd', trigger: 't', evidence: 'e', confidence: 'high', evidence_type: 'code', ...o })

// --- bughunt-scan -----------------------------------------------------------

const files = [
  ['src/api/client.js', 400], ['src/api/server.js', 900], ['src/ui/app.js', 1200],
  ['src/ui/form.js', 300], ['src/util/big.js', 5000], ['Src/Home.pa.yaml', 200],
]

const hunterMock = (prompt, opts) => {
  if (opts.agentType === 'bug-hunter') {
    const ids = idsIn(prompt)
    const bugs = []
    if (ids.includes('logic') && prompt.includes('- src/api/client.js')) bugs.push(bug({ title: 'Null token crash in request', file: 'src/api/client.js', line: 42, severity: 'high', category: 'null-safety', checkpoint: 'logic' }))
    if (ids.includes('x-integration')) bugs.push(bug({ title: 'Null token crash in request', file: 'src/api/client.js', line: 43, severity: 'high', category: 'null-safety', checkpoint: 'x-integration' }))
    if (ids.includes('logic') && prompt.includes('- src/ui/app.js') && !prompt.includes('Already reported')) {
      bugs.push(bug({ title: 'Imaginary bug', file: 'src/ui/app.js', line: 10, confidence: 'low', checkpoint: 'logic' }))
      bugs.push(bug({ title: 'Disputed race', file: 'src/ui/app.js', line: 99, severity: 'critical', category: 'async-race', checkpoint: 'edge-cases' }))
      bugs.push(bug({ title: 'Event delegation handler misses new rows', file: 'src/ui/app.js', line: 300, category: 'logic', checkpoint: 'logic' }))
    }
    if (ids.includes('logic') && prompt.includes('src/util/big.js lines 1-')) bugs.push(bug({ title: 'Off by one', file: '/proj/src/util/big.js', line: 12, severity: 'low', checkpoint: 'logic' }))
    if (ids.includes('powerapps')) bugs.push(bug({ title: 'Filter on SharePoint list is not delegable', file: 'Src/Home.pa.yaml', line: 7, severity: 'high', category: 'delegation', checkpoint: 'powerapps' }))
    const listed = [...prompt.matchAll(/^- (\S+)/gm)].map(m => m[1])
    return { bugs, checkpoints: attest(prompt), files_reviewed: listed }
  }
  if (opts.agentType === 'bug-skeptic') {
    if (prompt.includes('previous cycle')) return { status: 'still-present', evidence: 'same code' }
    if (prompt.includes('Imaginary bug')) return { verdict: 'refuted', reasoning: 'guarded upstream', severity: 'low' }
    if (prompt.includes('Disputed race')) {
      const k = Number((prompt.match(/skeptic (\d) of/) || [])[1] || 1)
      return { verdict: k === 1 ? 'confirmed' : k === 2 ? 'refuted' : 'uncertain', reasoning: 'split', severity: 'high' }
    }
    const sev = (prompt.match(/Claimed severity: (\w+)/) || [])[1] || 'low'
    return { verdict: 'confirmed', reasoning: 'real', severity: sev, reproduction: 'repro' }
  }
  throw new Error('unexpected agent type ' + opts.agentType)
}

await test('scan: required passes per slice, whole-codebase passes, coverage grid complete', async () => {
  const { result: r, calls, logs } = await runWorkflow(`${WF}/bughunt-scan.js`, { root: '/proj', files, mode: 'auto', powerapps: { detected: true } }, hunterMock)
  assert.equal(r.ok, true, JSON.stringify(r).slice(0, 500))
  assert.equal(r.tier, 'medium')
  const r1 = calls.filter(c => c.opts.agentType === 'bug-hunter' && !c.opts.label.includes(' r2'))
  // every slice gets a correctness pass and a safety pass; the .pa.yaml slice also gets a powerapps pass
  for (const s of r.coverage.grid) {
    assert.equal(s.cells.logic, 'checked'); assert.equal(s.cells['edge-cases'], 'checked')
    assert.equal(s.cells.security, 'checked'); assert.equal(s.cells.contracts, 'checked')
    assert.equal(s.cells.performance, 'checked'); assert.equal(s.cells['code-health'], 'checked')
    const pa = s.files.some(f => f.endsWith('.pa.yaml'))
    assert.equal(s.cells.powerapps, pa ? 'checked' : 'n/a')
    for (const id of ['interaction', 'ui-states', 'accessibility']) assert.equal(s.cells[id], pa ? 'checked' : 'n/a', `${s.row}/${id}`)
  }
  assert.equal(r1.filter(c => c.opts.label.includes('[correctness]')).length, r.stats.slices)
  assert.equal(r1.filter(c => c.opts.label.includes('[safety]')).length, r.stats.slices)
  // medium tier: one agent per whole-codebase checkpoint, including the Power Apps one
  for (const id of ['x-integration', 'x-data', 'x-security', 'x-state', 'x-config', 'x-powerapps']) {
    assert.ok(calls.some(c => c.opts.label === `hunt whole-codebase [${id}]`), id)
    assert.equal(r.coverage.whole_codebase[id].status, 'checked')
  }
  assert.equal(r.coverage.complete, true)
  assert.deepEqual(r.coverage.gaps, [])
  // security prompts carry the "switching selections is intended" note
  assert.ok(r1.filter(c => idsIn(c.prompt).includes('security')).every(c => c.prompt.includes('Switching freely between selections is intended')))
  // big file split into ranges
  assert.ok(r1.some(c => /src\/util\/big\.js lines 1-\d+ of 5000/.test(c.prompt)))
  console.log('    agents', r.stats.agents_used, '| required slice passes', r.stats.required_slice_passes, '| logs:', logs[0])
})

await test('scan: kinds, IDs, blocking, dedup across checkpoints, skeptic counts', async () => {
  const { result: r, calls } = await runWorkflow(`${WF}/bughunt-scan.js`, { root: '/proj', files, powerapps: { detected: true } }, hunterMock)
  const byTitle = t => r.confirmed.find(b => b.title === t)
  // Power Apps delegation -> warning (fixed rule), never blocks, gets a W id and one skeptic
  const del = byTitle('Filter on SharePoint list is not delegable')
  assert.equal(del.kind, 'warning'); assert.equal(del.blocks, false); assert.match(del.id, /^W\d+$/)
  assert.equal(calls.filter(c => c.opts.agentType === 'bug-skeptic' && c.prompt.includes('not delegable')).length, 1)
  // "event delegation" in a JS file is NOT a Power Apps delegation warning
  assert.equal(byTitle('Event delegation handler misses new rows').kind, 'bug')
  // duplicate reported by the slice and by the whole-codebase pass is merged
  assert.equal(r.confirmed.filter(b => b.title === 'Null token crash in request').length, 1)
  assert.ok(r.stats.duplicates_merged >= 1)
  // high bug: 3 skeptics in medium tier; refuted dropped; split vote -> disputed
  assert.equal(calls.filter(c => c.opts.agentType === 'bug-skeptic' && c.prompt.includes('Null token')).length, 3)
  assert.equal(r.refuted.length, 1)
  assert.equal(r.disputed.length, 1); assert.equal(r.disputed[0].id, 'D1')
  // every finding carries checkpoint, evidence_type and kind; bugs come first, B1 is the high one
  assert.ok(r.confirmed.every(b => b.checkpoint && b.evidence_type === 'code' && b.kind && b.checkpoint_name))
  assert.equal(r.confirmed[0].id, 'B1'); assert.equal(r.confirmed[0].severity, 'high')
  assert.ok(r.confirmed.some(b => b.file === 'src/util/big.js'), 'absolute path normalized')
  assert.equal(r.clean, false)
  assert.equal(r.stats.confirmed_by_kind.warning, 1)
})

await test('scan: only warnings and low bugs -> clean', async () => {
  const mock = (p, o) => o.agentType === 'bug-hunter'
    ? { bugs: idsIn(p).includes('logic') ? [bug({ title: 'Typo in message', file: 'a.js', line: 3, severity: 'low', checkpoint: 'logic' })] : [], checkpoints: attest(p), files_reviewed: ['a.js'] }
    : { verdict: 'confirmed', reasoning: 'ok', severity: 'low' }
  const { result: r, calls } = await runWorkflow(`${WF}/bughunt-scan.js`, { root: '/proj', files: [['a.js', 50]] }, mock)
  assert.equal(r.tier, 'small')
  // small tier: one whole-codebase agent covers all four whole-codebase checkpoints
  const cross = calls.filter(c => c.opts.label.startsWith('hunt whole-codebase'))
  assert.equal(cross.length, 1)
  assert.deepEqual(idsIn(cross[0].prompt), ['x-integration', 'x-data', 'x-security', 'x-state', 'x-config'])
  assert.equal(r.coverage.whole_codebase['x-powerapps'].status, 'n/a')
  assert.equal(r.clean, true)
})

await test('scan: a checkpoint not signed off gets a follow-up pass; still missing -> unattested, not clean', async () => {
  let followups = 0
  const mock = (p, o) => {
    if (o.agentType !== 'bug-hunter') return { verdict: 'confirmed', reasoning: 'ok', severity: 'low' }
    if (o.label.includes('recheck')) { followups++; return { bugs: [], checkpoints: [], files_reviewed: [] } }
    return { bugs: [], checkpoints: attest(p, ['edge-cases']), files_reviewed: ['a.js'] }
  }
  const { result: r } = await runWorkflow(`${WF}/bughunt-scan.js`, { root: '/proj', files: [['a.js', 50]] }, mock)
  assert.equal(followups >= 1, true)
  assert.equal(r.coverage.grid[0].cells['edge-cases'], 'unattested')
  assert.equal(r.coverage.complete, false)
  assert.ok(r.coverage.gaps.includes('S1/edge-cases: unattested'))
  assert.equal(r.clean, false)
})

await test('scan: follow-up pass that signs off fills the gap', async () => {
  const mock = (p, o) => {
    if (o.agentType !== 'bug-hunter') return { verdict: 'confirmed', reasoning: 'ok', severity: 'low' }
    if (o.label.includes('recheck')) return { bugs: [], checkpoints: attest(p), files_reviewed: [] }
    return { bugs: [], checkpoints: attest(p, ['contracts']), files_reviewed: ['a.js'] }
  }
  const { result: r } = await runWorkflow(`${WF}/bughunt-scan.js`, { root: '/proj', files: [['a.js', 50]] }, mock)
  assert.equal(r.coverage.grid[0].cells.contracts, 'checked')
  assert.equal(r.clean, true)
})

await test('scan: failed pass -> retried; double failure marks grid cells failed and blocks clean', async () => {
  const mock = (p, o) => {
    if (o.agentType === 'bug-hunter' && p.includes('- z/b.js') && idsIn(p).includes('security')) return null
    if (o.agentType === 'bug-hunter') return { bugs: [], checkpoints: attest(p), files_reviewed: [] }
    return { verdict: 'confirmed', reasoning: 'ok', severity: 'low' }
  }
  const { result: r, calls } = await runWorkflow(`${WF}/bughunt-scan.js`, { root: '/proj', files: [['a.js', 1400], ['z/b.js', 1400]] }, mock)
  assert.ok(calls.some(c => c.opts.label.includes('retry')))
  const row = r.coverage.grid.find(g => g.files.includes('z/b.js'))
  assert.equal(row.cells.security, 'failed'); assert.equal(row.cells.contracts, 'failed'); assert.equal(row.cells.logic, 'checked')
  assert.equal(r.coverage.complete, false)
  assert.equal(r.clean, false)
})

await test('scan: disabled checkpoint shows "off" and is not a gap', async () => {
  const mock = (p, o) => (o.agentType === 'bug-hunter' ? { bugs: [], checkpoints: attest(p), files_reviewed: [] } : null)
  const { result: r, calls } = await runWorkflow(`${WF}/bughunt-scan.js`, { root: '/proj', files: [['a.js', 50]], disable_checkpoints: ['contracts', 'x-config'] }, mock)
  assert.equal(r.coverage.grid[0].cells.contracts, 'off')
  assert.equal(r.coverage.whole_codebase['x-config'].status, 'off')
  assert.ok(!calls.some(c => idsIn(c.prompt).includes('contracts')))
  assert.equal(r.coverage.complete, true)
})

await test('scan: lean merges all slice checkpoints into one pass; max splits one per checkpoint', async () => {
  const mock = (p, o) => (o.agentType === 'bug-hunter' ? { bugs: [], checkpoints: attest(p), files_reviewed: [] } : null)
  const lean = await runWorkflow(`${WF}/bughunt-scan.js`, { root: '/proj', files: [['a.js', 50]], mode: 'lean' }, mock)
  const leanSlice = lean.calls.filter(c => c.opts.label.startsWith('hunt S1'))
  assert.equal(leanSlice.length, 1)
  assert.deepEqual(idsIn(leanSlice[0].prompt), ['logic', 'edge-cases', 'performance', 'security', 'contracts', 'code-health'])
  const max = await runWorkflow(`${WF}/bughunt-scan.js`, { root: '/proj', files: [['a.js', 50]], mode: 'max' }, mock)
  assert.equal(max.calls.filter(c => c.opts.label.startsWith('hunt S1')).length, 6)
  assert.equal(max.calls.filter(c => c.opts.label.startsWith('hunt whole-codebase')).length, 5)
  assert.equal(max.result.coverage.complete, true)
})

await test('scan: unknown agent type -> ok:false (never a false "clean")', async () => {
  const { result: r } = await runWorkflow(`${WF}/bughunt-scan.js`, { root: '/proj', files: [['a.js', 50]] }, () => { throw new Error("Agent type 'bug-hunter' not found") })
  assert.equal(r.ok, false); assert.match(r.error, /restart/); assert.ok(r.errors.length > 0)
})

await test('scan: regression check of previous bugs blocks clean when still present', async () => {
  const mock = (p, o) => (o.agentType === 'bug-hunter' ? { bugs: [], checkpoints: attest(p), files_reviewed: ['a.js'] } : hunterMock(p, o))
  const { result: r } = await runWorkflow(`${WF}/bughunt-scan.js`, { root: '/proj', files: [['a.js', 50]], previous_bugs: [{ id: 'B1', title: 'x', file: 'a.js', line: 3 }] }, mock)
  assert.equal(r.regressions[0].status, 'still-present')
  assert.equal(r.clean, false)
})

await test('scan: extra sweeps stop after a dry sweep (large tier); grid comes from the required round only', async () => {
  const mock = (p, o) => {
    if (o.agentType === 'bug-hunter') {
      const r1 = !/ r[23] /.test(o.label) && !o.label.includes('whole-codebase') && idsIn(p).includes('logic')
      const file = (p.match(/^- (\S+)/m) || [])[1]
      return { bugs: r1 ? [bug({ title: `bug in ${file}`, file, line: 5, checkpoint: 'logic' })] : [], checkpoints: /r[23] /.test(o.label) ? [] : attest(p), files_reviewed: [] }
    }
    return { verdict: 'confirmed', reasoning: 'ok', severity: 'medium' }
  }
  const big = Array.from({ length: 30 }, (_, i) => [`m${i}/f.js`, 1500])
  const { result: r } = await runWorkflow(`${WF}/bughunt-scan.js`, { root: '/proj', files: big }, mock)
  assert.equal(r.tier, 'large')
  assert.equal(r.stats.rounds_run, 2)
  assert.equal(r.coverage.complete, true, 'sweeps without sign-offs do not create gaps')
})

await test('scan: hunter cap raises slice size; every file still reaches a required pass', async () => {
  const many = Array.from({ length: 200 }, (_, i) => [`d${i}/x.js`, 1000])
  const mock = (p, o) => (o.agentType === 'bug-hunter' ? { bugs: [], checkpoints: attest(p), files_reviewed: [] } : null)
  const { result: r, logs, calls } = await runWorkflow(`${WF}/bughunt-scan.js`, { root: '/proj', files: many }, mock)
  assert.ok(r.stats.slices <= 48)
  assert.ok(logs.some(l => l.includes('Slice size raised')))
  const correctness = calls.filter(c => c.opts.label.includes('[correctness]')).map(c => c.prompt).join('\n')
  const safety = calls.filter(c => c.opts.label.includes('[safety]')).map(c => c.prompt).join('\n')
  assert.equal(many.filter(([f]) => !correctness.includes(`- ${f} (`)).length, 0)
  assert.equal(many.filter(([f]) => !safety.includes(`- ${f} (`)).length, 0)
})

await test('scan: missing args -> helpful error', async () => {
  const { result: r } = await runWorkflow(`${WF}/bughunt-scan.js`, undefined, () => null)
  assert.equal(r.ok, false); assert.match(r.error, /\/bughunt/)
})

// --- Step 2 layers -----------------------------------------------------------------

await test('layers: screen-code slices get the ui pass; kinds per checkpoint; IDs per kind', async () => {
  const mock = (p, o) => {
    if (o.agentType === 'bug-hunter' && o.label.startsWith('map')) return { found: false, reason: 'no selection concept', consumers: [] }
    if (o.agentType === 'bug-hunter') {
      const ids = idsIn(p), bugs = []
      if (ids.includes('performance')) bugs.push(bug({ title: 'Query per row in loop', file: 'src/list.js', line: 4, category: 'performance', checkpoint: 'performance' }))
      if (ids.includes('code-health')) bugs.push(bug({ title: 'Hard-coded prod URL', file: 'src/list.js', line: 9, severity: 'low', category: 'config', checkpoint: 'code-health' }))
      if (ids.includes('interaction')) bugs.push(bug({ title: 'Save can be clicked twice', file: 'src/Form.jsx', line: 20, severity: 'medium', category: 'logic', checkpoint: 'interaction' }))
      if (ids.includes('ui-states')) bugs.push(bug({ title: 'No empty state for list', file: 'src/Form.jsx', line: 40, severity: 'low', category: 'other', checkpoint: 'ui-states' }))
      if (ids.includes('accessibility')) bugs.push(bug({ title: 'Icon button has no label', file: 'src/Form.jsx', line: 55, severity: 'low', category: 'other', checkpoint: 'accessibility' }))
      return { bugs, checkpoints: attest(p), files_reviewed: [] }
    }
    return { verdict: 'confirmed', reasoning: 'ok', severity: (p.match(/Claimed severity: (\w+)/) || [])[1] || 'low' }
  }
  const { result: r, calls } = await runWorkflow(`${WF}/bughunt-scan.js`, { root: '/proj', mode: 'small', files: [['a/list.js', 1400], ['b/Form.jsx', 1400], ['c/helper.js', 1400, 'ui']] }, mock)
  const row = f => r.coverage.grid.find(g => g.files.includes(f))
  assert.equal(row('a/list.js').cells.interaction, 'n/a')
  assert.equal(row('b/Form.jsx').cells.interaction, 'checked')
  assert.equal(row('c/helper.js').cells.accessibility, 'checked', 'scope.sh "ui" tag routes plain .js files')
  const ui = calls.filter(c => c.opts.label.includes('[ui]'))
  assert.equal(ui.length, 2)
  assert.ok(ui[0].prompt.includes('(findings reported as: accessibility)'))
  const k = t => r.confirmed.find(b => b.title === t)
  assert.equal(k('Query per row in loop').kind, 'warning')
  assert.equal(k('Hard-coded prod URL').kind, 'code-health'); assert.match(k('Hard-coded prod URL').id, /^H\d/)
  assert.equal(k('Save can be clicked twice').kind, 'bug'); assert.equal(k('Save can be clicked twice').blocks, true)
  assert.equal(k('No empty state for list').kind, 'cosmetic'); assert.match(k('No empty state for list').id, /^V\d/)
  assert.equal(k('Icon button has no label').kind, 'accessibility'); assert.match(k('Icon button has no label').id, /^A\d/)
  assert.equal(r.stats.blocking, 1)
  // code-health skeptic gets its hint; non-bug kinds get one skeptic
  const hc = calls.filter(c => c.opts.agentType === 'bug-skeptic' && c.prompt.includes('Hard-coded prod URL'))
  assert.equal(hc.length, 1); assert.ok(hc[0].prompt.includes('Confirm by searching for references'))
  assert.equal(r.coverage.whole_codebase.scoping.status, 'n/a')
  assert.equal(r.coverage.complete, true)
})

await test('layers: x-data gets the database/schema file list', async () => {
  const mock = (p, o) => (o.agentType === 'bug-hunter' ? { bugs: [], checkpoints: attest(p), files_reviewed: [], found: false, reason: 'none', consumers: [] } : null)
  const { calls } = await runWorkflow(`${WF}/bughunt-scan.js`, { root: '/proj', files: [['api/units.js', 300], ['db/migrations/001.sql', 40, 'data']], mode: 'medium' }, mock)
  const xd = calls.find(c => c.opts.label === 'hunt whole-codebase [x-data]')
  assert.ok(xd.prompt.includes('Database and schema files found by the scope scan:\ndb/migrations/001.sql'))
})

const scopingMap = n => ({
  found: true, reason: 'property selector in header',
  levels: [{ name: 'property' }, { name: 'regional' }, { name: 'region' }],
  hierarchy: [{ relationship: 'property.regionalId -> regional', where: 'db/schema.sql:10' }],
  selection_state: [{ where: 'store.selection', file: 'src/store.js', line: 3 }],
  change_handlers: [{ description: 'onSelectionChange', file: 'src/store.js', line: 20 }],
  consumers: Array.from({ length: n }, (_, i) => ({ kind: 'query', file: `src/q${i}.js`, line: 5, description: `units query ${i}` })),
})

await test('scoping: map -> batches of 8 + switching check; findings are bugs; delegation stays a warning', async () => {
  const mock = (p, o) => {
    if (o.label === 'map scoping') return scopingMap(20)
    if (o.label.startsWith('check scoping')) {
      const bugs = []
      if (p.includes('src/q3.js')) bugs.push(bug({ title: 'Regional total misses properties without a manager', file: 'src/q3.js', line: 5, severity: 'high', category: 'logic', checkpoint: 'scoping' }))
      if (p.includes('src/q12.js')) bugs.push(bug({ title: 'Filter not delegable on SharePoint', file: 'Src/Home.pa.yaml', line: 9, severity: 'high', category: 'delegation', checkpoint: 'scoping' }))
      if (o.label.endsWith('switching')) bugs.push(bug({ title: 'Units appended on switch instead of replaced', file: 'src/store.js', line: 22, severity: 'high', category: 'logic', checkpoint: 'scoping' }))
      return { bugs, checkpoints: [{ id: 'scoping', status: 'checked' }], files_reviewed: [] }
    }
    if (o.agentType === 'bug-hunter') return { bugs: [], checkpoints: attest(p), files_reviewed: [] }
    return { verdict: 'confirmed', reasoning: 'ok', severity: (p.match(/Claimed severity: (\w+)/) || [])[1] || 'low' }
  }
  const { result: r, calls } = await runWorkflow(`${WF}/bughunt-scan.js`, { root: '/proj', files: [['src/a.js', 100]] }, mock)
  const checks = calls.filter(c => c.opts.label.startsWith('check scoping'))
  assert.equal(checks.length, 4, '20 consumers in batches of 8 = 3, plus switching')
  assert.ok(checks[0].prompt.includes('Hierarchy relationships: property.regionalId -> regional'))
  assert.ok(checks[0].prompt.includes('not a privacy one'))
  assert.equal(r.coverage.whole_codebase.scoping.status, 'checked')
  assert.equal(r.maps.scoping.consumers, 20); assert.equal(r.maps.scoping.batches, 3)
  const t = x => r.confirmed.find(b => b.title === x)
  assert.equal(t('Regional total misses properties without a manager').kind, 'bug')
  assert.equal(t('Units appended on switch instead of replaced').blocks, true)
  assert.equal(t('Filter not delegable on SharePoint').kind, 'warning')
  const skep = calls.find(c => c.opts.agentType === 'bug-skeptic' && c.prompt.includes('Regional total'))
  assert.ok(skep.prompt.includes('switching between selections is intended'))
  assert.equal(r.clean, false)
})

await test('scoping: a failed checker batch marks scoping failed and blocks clean', async () => {
  const mock = (p, o) => {
    if (o.label === 'map scoping') return scopingMap(10)
    if (o.label.startsWith('check scoping 2/2')) return null
    if (o.label.startsWith('check scoping')) return { bugs: [], checkpoints: [{ id: 'scoping', status: 'checked' }], files_reviewed: [] }
    if (o.agentType === 'bug-hunter') return { bugs: [], checkpoints: attest(p), files_reviewed: [] }
    return null
  }
  const { result: r } = await runWorkflow(`${WF}/bughunt-scan.js`, { root: '/proj', files: [['src/a.js', 100]] }, mock)
  assert.equal(r.coverage.whole_codebase.scoping.status, 'failed')
  assert.ok(r.coverage.gaps.includes('scoping: failed'))
  assert.equal(r.clean, false)
})

await test('scoping: very large maps are re-batched to at most 30 checker batches', async () => {
  const mock = (p, o) => {
    if (o.label === 'map scoping') return scopingMap(400)
    if (o.agentType === 'bug-hunter') return { bugs: [], checkpoints: o.label.startsWith('check') ? [{ id: 'scoping', status: 'checked' }] : attest(p), files_reviewed: [] }
    return null
  }
  const { result: r, calls } = await runWorkflow(`${WF}/bughunt-scan.js`, { root: '/proj', files: [['src/a.js', 100]] }, mock)
  assert.ok(r.maps.scoping.batches <= 30)
  const checked = calls.filter(c => /^check scoping \d/.test(c.opts.label)).map(c => c.prompt).join('\n')
  assert.equal(Array.from({ length: 400 }, (_, i) => `src/q${i}.js:`).filter(x => !checked.includes(x)).length, 0, 'every consumer is checked')
})

// --- evidence-gate.mjs ---------------------------------------------------------

await test('gate: real quotes pass, paraphrase and fake files are rejected, wrong line corrected, clean recomputed', async () => {
  const dir = mkdtempSync(join(tmpdir(), 'bughunt-gate-'))
  mkdirSync(join(dir, 'src'))
  const code = Array.from({ length: 60 }, (_, i) => `const filler${i} = ${i}`)
  code[41] = '  const token = session.user.token.value'
  code[42] = '  return fetch(url, { headers: { auth: token } })'
  writeFileSync(join(dir, 'src/app.js'), code.join('\n'))
  writeFileSync(join(dir, 'shot.png'), 'png')
  const base = { checkpoint: 'logic', evidence_type: 'code', severity: 'high', kind: 'bug', blocks: true, file: 'src/app.js' }
  const findings = {
    root: dir, clean: false, stats: { blocking: 5 }, regressions: [], coverage: { complete: true },
    confirmed: [
      { ...base, id: 'B1', line: 42, evidence: '42: const token = session.user.token.value\n  return fetch(url, { headers: { auth: token } })' },
      { ...base, id: 'B2', line: 5, evidence: 'const token = session.user.token.value' },
      { ...base, id: 'B3', line: 42, evidence: 'the token is read without a null check' },
      { ...base, id: 'B4', line: 3, file: 'src/missing.js', evidence: 'anything at all here' },
      { ...base, id: 'B5', line: 3, file: '../etc/passwd', evidence: 'root:x:0:0' },
      { ...base, id: 'B6', line: 42, checkpoint: undefined, evidence: 'const token = session.user.token.value' },
      { id: 'V1', kind: 'cosmetic', blocks: false, checkpoint: 'visual', evidence_type: 'runtime', severity: 'low', screenshot: 'shot.png', steps: ['open page', 'look at pill'] },
      { id: 'V2', kind: 'cosmetic', blocks: false, checkpoint: 'visual', evidence_type: 'runtime', severity: 'low', screenshot: 'nope.png', steps: ['x'] },
      { id: 'V3', kind: 'cosmetic', blocks: false, checkpoint: 'visual', evidence_type: 'runtime', severity: 'low', screenshot: 'shot.png', steps: ['  '] },
    ],
    disputed: [{ ...base, id: 'D1', line: 43, blocks: false, evidence: 'return fetch(url, { headers: { auth: token } })' }],
  }
  const p = join(dir, 'findings.json')
  writeFileSync(p, JSON.stringify(findings))
  const out = execFileSync('node', [GATE, p], { encoding: 'utf8' })
  const g = JSON.parse(readFileSync(p, 'utf8'))
  const ids = arr => arr.map(f => f.id)
  assert.deepEqual(ids(g.confirmed), ['B1', 'B2', 'V1'])
  assert.deepEqual(ids(g.disputed), ['D1'])
  assert.deepEqual(ids(g.rejected_evidence).sort(), ['B3', 'B4', 'B5', 'B6', 'V2', 'V3'])
  const b2 = g.confirmed.find(f => f.id === 'B2')
  assert.equal(b2.line, 42); assert.equal(b2.evidence_check.line_corrected_from, 5)
  assert.match(g.rejected_evidence.find(f => f.id === 'B3').evidence_check.reason, /not found/)
  assert.match(g.rejected_evidence.find(f => f.id === 'B5').evidence_check.reason, /outside the project/)
  assert.match(g.rejected_evidence.find(f => f.id === 'B6').evidence_check.reason, /checkpoint/)
  assert.equal(g.evidence_gate.checked, 10); assert.equal(g.evidence_gate.passed, 4); assert.equal(g.evidence_gate.lines_corrected, 1)
  assert.equal(g.stats.blocking, 2)
  assert.equal(g.clean, false)
  assert.ok(out.includes('rejected B3'))
})

await test('gate: clean flips to true when the only blocking finding has no real evidence', async () => {
  const dir = mkdtempSync(join(tmpdir(), 'bughunt-gate-'))
  writeFileSync(join(dir, 'a.js'), 'let x = 1\n')
  const p = join(dir, 'findings.json')
  writeFileSync(p, JSON.stringify({ root: dir, clean: false, regressions: [], coverage: { complete: true }, confirmed: [{ id: 'B1', kind: 'bug', blocks: true, checkpoint: 'logic', evidence_type: 'code', severity: 'high', file: 'a.js', line: 1, evidence: 'made up code here' }], disputed: [] }))
  execFileSync('node', [GATE, p])
  assert.equal(JSON.parse(readFileSync(p, 'utf8')).clean, true)
})

// --- bugfix-propose ----------------------------------------------------------

const ok = { evidence_check: { ok: true, reason: 'found' } }
const bugs = [
  { id: 'B1', title: 'Null token', file: 'src/api/client.js', line: 42, severity: 'high', category: 'null-safety', description: 'd', trigger: 't', evidence: 'e', ...ok },
  { id: 'B2', title: 'Off by one', file: 'src/util/big.js', line: 12, severity: 'medium', category: 'logic', description: 'd', trigger: 't', evidence: 'e', ...ok },
  { id: 'B3', title: 'Patch unhandled', file: 'Src/Home.pa.yaml', line: 7, severity: 'medium', category: 'powerapps', description: 'd', trigger: 't', evidence: 'e', ...ok },
]
const proposeMock = (p, o) => {
  if (o.agentType === 'fix-planner') {
    const ids = [...p.matchAll(/^\[(B\d+)\]/gm)].map(m => m[1])
    return {
      proposals: ids.map(id => ({
        bug_id: id, still_reproduces: true, root_cause: 'rc',
        options: [{ summary: 'a', pros: 'p', cons: 'c' }, { summary: 'b', pros: 'p', cons: 'c' }],
        recommended: { summary: `fix ${id}`, why: 'w', edits: [{ file: 'f', location: 'l', change: 'c' }], files_touched: ['f'], verification: 'v' },
        side_effect_risks: 'none', apply_mode: id === 'B3' ? 'manual' : 'auto', manual_steps: id === 'B3' ? 'open Studio' : '', confidence: 'high',
      })),
    }
  }
  if (o.agentType === 'fix-critic' && o.label.startsWith('challenge')) return { verdict: 'sound', problems: [], new_bug_risks: [] }
  if (o.label.startsWith('end review')) {
    return {
      overall_assessment: 'ok', what_works: ['B1'], what_does_not_work: [], new_bug_risks: [], conflicts: [],
      items: [
        { bug_id: 'B1', decision: 'approve', final_change: 'fix B1', rationale: 'r', risk: 'low', expected_to_work: 'almost-certain' },
        { bug_id: 'B2', decision: 'hold', final_change: 'fix B2', rationale: 'needs product call', risk: 'medium', expected_to_work: 'uncertain' },
        { bug_id: 'B3', decision: 'approve', final_change: 'manual', rationale: 'r', risk: 'low', expected_to_work: 'likely' },
      ],
      apply_order: ['B1'],
    }
  }
  throw new Error('unexpected ' + o.label)
}

await test('propose: groups by file, 2 critic lenses for high, manual skips critics, end review merged', async () => {
  const { result: r, calls } = await runWorkflow(`${WF}/bugfix-propose.js`, { root: '/proj', bugs, powerapps: true, cycle: 1 }, proposeMock)
  assert.equal(r.ok, true, JSON.stringify(r))
  assert.equal(calls.filter(c => c.opts.agentType === 'fix-planner').length, 3)
  assert.equal(calls.filter(c => c.opts.label.startsWith('challenge B1')).length, 2)
  assert.equal(calls.filter(c => c.opts.label.startsWith('challenge B2')).length, 1)
  assert.equal(calls.filter(c => c.opts.label.startsWith('challenge B3')).length, 0)
  assert.deepEqual(r.recommended_ids, ['B1'])
  assert.deepEqual(r.manual_ids, ['B3'])
  assert.deepEqual(r.rejected_no_evidence, [])
})

await test('propose: findings without a passed evidence check are refused', async () => {
  const mixed = [bugs[0], { ...bugs[1], evidence_check: { ok: false, reason: 'quoted code not found' } }, { ...bugs[2], evidence_check: undefined }]
  const { result: r, calls } = await runWorkflow(`${WF}/bugfix-propose.js`, { root: '/proj', bugs: mixed }, proposeMock)
  assert.equal(r.ok, true)
  assert.deepEqual(r.rejected_no_evidence.map(x => x.id), ['B2', 'B3'])
  assert.ok(!calls.some(c => c.prompt.includes('[B2]') || c.prompt.includes('[B3]')))
  const none = await runWorkflow(`${WF}/bugfix-propose.js`, { root: '/proj', bugs: mixed.slice(1) }, proposeMock)
  assert.equal(none.result.ok, false)
  assert.match(none.result.error, /evidence check/)
})

await test('propose: history of failed attempts reaches the planner', async () => {
  const { calls } = await runWorkflow(`${WF}/bugfix-propose.js`, { root: '/proj', bugs: [bugs[0]], history: { B1: [{ attempt: 'added null check', outcome: 'still present' }] } }, proposeMock)
  assert.ok(calls[0].prompt.includes('did NOT work') && calls[0].prompt.includes('added null check'))
})

await test('propose: end review failure -> items held, not auto-recommended', async () => {
  const mock = (p, o) => (o.label.startsWith('end review') ? null : proposeMock(p, o))
  const { result: r } = await runWorkflow(`${WF}/bugfix-propose.js`, { root: '/proj', bugs }, mock)
  assert.equal(r.end_review, null)
  assert.deepEqual(r.recommended_ids, [])
  assert.ok(r.items.every(i => i.decision === 'hold'))
})

// --- bugfix-execute ----------------------------------------------------------

const items = [
  { bug_id: 'B1', title: 't1', file: 'a.js', line: 1, final_change: 'c', recommended: { edits: [{ file: 'a.js' }], files_touched: ['a.js', 'shared.js'] } },
  { bug_id: 'B2', title: 't2', file: 'b.js', line: 1, final_change: 'c', recommended: { edits: [{ file: 'b.js' }], files_touched: ['b.js', 'shared.js'] } },
  { bug_id: 'B3', title: 't3', file: 'c.js', line: 1, final_change: 'c', recommended: { edits: [{ file: 'c.js' }], files_touched: ['c.js'] } },
]
await test('execute: overlapping files grouped, disjoint run separately, checker flags problems', async () => {
  const mock = (p, o) => {
    const ids = [...new Set([...p.matchAll(/"bug_id": "(B\d)"/g)].map(m => m[1]))]
    if (o.agentType === 'bug-fixer') return { results: ids.map(id => ({ bug_id: id, status: 'applied', files_changed: [`${id}.js`], summary: 's' })) }
    if (o.agentType === 'fix-critic') return { checks: ids.map(id => ({ bug_id: id, verdict: id === 'B3' ? 'incorrect' : 'correct', problem: id === 'B3' ? 'wrong' : '' })) }
  }
  const { result: r, calls } = await runWorkflow(`${WF}/bugfix-execute.js`, { root: '/proj', items, order: ['B2', 'B1', 'B3'] }, mock)
  const fixers = calls.filter(c => c.opts.agentType === 'bug-fixer')
  assert.equal(fixers.length, 2)
  const g12 = fixers.find(c => c.prompt.includes('B1'))
  assert.ok(g12.prompt.indexOf('"B2"') < g12.prompt.indexOf('"B1"'), 'apply order respected')
  assert.equal(r.applied.length, 3)
  assert.equal(r.check_problems.length, 1)
})

await test('execute: fixer failure -> items reported skipped', async () => {
  const { result: r } = await runWorkflow(`${WF}/bugfix-execute.js`, { root: '/proj', items: [items[2]] }, () => null)
  assert.equal(r.skipped.length, 1)
  assert.equal(r.applied.length, 0)
})

console.log(failures ? `\n${failures} FAILED` : '\nALL PASSED')
process.exit(failures ? 1 : 0)
