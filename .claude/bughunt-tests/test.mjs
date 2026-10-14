// Offline tests for the bughunt kit workflows (no agents, no tokens). Run: node .claude/bughunt-tests/test.mjs
import assert from 'node:assert/strict'
import { runWorkflow } from './harness.mjs'

import { fileURLToPath } from 'node:url'
const WF = fileURLToPath(new URL('../workflows', import.meta.url))
let failures = 0
async function test(name, fn) {
  try { await fn(); console.log('PASS', name) } catch (e) { failures++; console.log('FAIL', name, '\n   ', e.message) }
}

// --- bughunt-scan -----------------------------------------------------------

const files = [
  ['src/api/client.js', 400], ['src/api/server.js', 900], ['src/ui/app.js', 1200],
  ['src/ui/form.js', 300], ['src/util/big.js', 5000], ['Src/Home.pa.yaml', 200],
]

// Hunters: every slice reports the same "real" bug in client.js plus a fake one; cross hunters report a duplicate.
const hunterMock = (prompt, opts) => {
  if (opts.agentType === 'bug-hunter') {
    const bugs = []
    if (prompt.includes('src/api/client.js') || opts.label.includes('cross')) {
      bugs.push({ title: 'Null token crash in request', file: 'src/api/client.js', line: 42, severity: 'high', category: 'null-safety', description: 'd', trigger: 't', evidence: 'e', confidence: 'high' })
    }
    if (prompt.includes('src/ui/app.js') && !prompt.includes('Already reported')) {
      bugs.push({ title: 'Imaginary bug', file: 'src/ui/app.js', line: 10, severity: 'medium', category: 'logic', description: 'd', trigger: 't', evidence: 'e', confidence: 'low' })
      bugs.push({ title: 'Disputed race', file: 'src/ui/app.js', line: 99, severity: 'critical', category: 'async-race', description: 'd', trigger: 't', evidence: 'e', confidence: 'medium' })
    }
    if (prompt.includes('src/util/big.js lines 1-')) {
      bugs.push({ title: 'Off by one', file: '/proj/src/util/big.js', line: 12, severity: 'low', category: 'logic', description: 'd', trigger: 't', evidence: 'e', confidence: 'high' })
    }
    const listed = [...prompt.matchAll(/^- (\S+)/gm)].map(m => m[1])
    return { bugs, files_reviewed: listed }
  }
  if (opts.agentType === 'bug-skeptic') {
    if (prompt.includes('Imaginary bug')) return { verdict: 'refuted', reasoning: 'guarded upstream', severity: 'low' }
    if (prompt.includes('Disputed race')) {
      const k = Number((prompt.match(/skeptic (\d) of/) || [])[1] || 1)
      return { verdict: k === 1 ? 'confirmed' : k === 2 ? 'refuted' : 'uncertain', reasoning: 'split', severity: 'high' }
    }
    if (prompt.includes('previous cycle')) return { status: 'still-present', evidence: 'same code' }
    return { verdict: 'confirmed', reasoning: 'real', severity: prompt.includes('Null token') ? 'high' : 'low', reproduction: 'call with no token' }
  }
  throw new Error('unexpected agent type ' + opts.agentType)
}

await test('scan: medium tier, chunking, dedup, voting, Power Apps lens', async () => {
  const lines = files.reduce((n, f) => n + f[1], 0)
  const { result: r, calls, logs } = await runWorkflow(`${WF}/bughunt-scan.js`, { root: '/proj', files, mode: 'auto', powerapps: { detected: true } }, hunterMock)
  assert.equal(r.ok, true, JSON.stringify(r))
  assert.equal(r.tier, 'small'.length && lines < 3000 ? 'small' : 'medium')
  // big.js (5000 lines) must be split into ranges
  const huntPrompts = calls.filter(c => c.opts.agentType === 'bug-hunter').map(c => c.prompt)
  assert.ok(huntPrompts.some(p => /src\/util\/big\.js lines 1-\d+ of 5000/.test(p)), 'big file split')
  // Power Apps checklist injected for the .pa.yaml slice, and a powerapps cross lens added
  assert.ok(huntPrompts.some(p => p.includes('Src/Home.pa.yaml') && p.includes('Delegation:')), 'PA checklist in slice')
  assert.ok(calls.some(c => c.opts.label === 'hunt cross:powerapps'), 'PA cross lens')
  // Duplicate (slice + 3 cross hunters report the same client.js bug) merged
  assert.equal(r.confirmed.filter(b => b.title === 'Null token crash in request').length, 1)
  assert.ok(r.stats.duplicates_merged >= 1)
  // High-severity bug gets 3 skeptics in medium tier; refuted one dropped; split vote -> disputed
  assert.equal(calls.filter(c => c.opts.agentType === 'bug-skeptic' && c.prompt.includes('Null token')).length, 3)
  assert.equal(r.refuted.length, 1)
  assert.equal(r.disputed.length, 1)
  assert.equal(r.disputed[0].id, 'D1')
  // Absolute path normalized; IDs sorted by severity
  assert.ok(r.confirmed.some(b => b.file === 'src/util/big.js'))
  assert.equal(r.confirmed[0].id, 'B1'); assert.equal(r.confirmed[0].severity, 'high')
  // Not clean: a confirmed high bug blocks
  assert.equal(r.clean, false)
  assert.equal(r.stats.blocking, 1)
  console.log('    tier', r.tier, '| agents', r.stats.agents_used, '| logs:', logs.join(' || '))
})

await test('scan: clean when only low bugs remain and coverage complete', async () => {
  const mock = (p, o) => o.agentType === 'bug-hunter'
    ? { bugs: [{ title: 'Typo in message', file: 'a.js', line: 3, severity: 'low', category: 'other', description: 'd', trigger: 't', evidence: 'e', confidence: 'high' }], files_reviewed: ['a.js'] }
    : { verdict: 'confirmed', reasoning: 'ok', severity: 'low' }
  const { result: r } = await runWorkflow(`${WF}/bughunt-scan.js`, { root: '/proj', files: [['a.js', 50]] }, mock)
  assert.equal(r.ok, true)
  assert.equal(r.tier, 'small')
  assert.equal(r.confirmed.length, 1)
  assert.equal(r.clean, true)
})

await test('scan: failed slice -> retried; double failure blocks clean', async () => {
  const mock = (p, o) => {
    if (o.agentType === 'bug-hunter' && p.includes('b.js')) return null
    if (o.agentType === 'bug-hunter') return { bugs: [], files_reviewed: ['a.js'] }
    return { verdict: 'confirmed', reasoning: 'ok', severity: 'low' }
  }
  const { result: r, calls } = await runWorkflow(`${WF}/bughunt-scan.js`, { root: '/proj', files: [['a.js', 1400], ['z/b.js', 1400]] }, mock)
  assert.equal(r.ok, true)
  assert.ok(calls.some(c => c.opts.label.includes('retry')), 'retried')
  assert.equal(r.coverage.complete, false)
  assert.equal(r.clean, false)
})

await test('scan: unknown agent type -> ok:false (never a false "clean")', async () => {
  const mock = () => { throw new Error("Agent type 'bug-hunter' not found") }
  const { result: r } = await runWorkflow(`${WF}/bughunt-scan.js`, { root: '/proj', files: [['a.js', 50]] }, mock)
  assert.equal(r.ok, false)
  assert.match(r.error, /restart/)
  assert.ok(r.errors.length > 0)
})

await test('scan: regression check of previous bugs', async () => {
  const mock = (p, o) => {
    if (o.agentType === 'bug-hunter') return { bugs: [], files_reviewed: ['a.js'] }
    return hunterMock(p, o)
  }
  const { result: r } = await runWorkflow(`${WF}/bughunt-scan.js`, { root: '/proj', files: [['a.js', 50]], previous_bugs: [{ id: 'C1-B1', title: 'x', file: 'a.js', line: 3 }] }, mock)
  assert.equal(r.regressions.length, 1)
  assert.equal(r.regressions[0].status, 'still-present')
  assert.equal(r.clean, false, 'open regression blocks clean')
})

await test('scan: loop-until-dry stops after a round with nothing new (large tier)', async () => {
  let n = 0
  const mock = (p, o) => {
    if (o.agentType === 'bug-hunter') {
      n++
      // round 1 finds one bug per slice; later rounds find nothing new
      const isR1 = !o.label.includes(' r2') && !o.label.includes(' r3')
      return { bugs: isR1 && !o.label.includes('cross') ? [{ title: `bug ${o.label}`, file: o.label.split(' ')[2], line: 5, severity: 'medium', category: 'logic', description: 'd', trigger: 't', evidence: 'e', confidence: 'high' }] : [], files_reviewed: [] }
    }
    return { verdict: 'confirmed', reasoning: 'ok', severity: 'medium' }
  }
  const big = Array.from({ length: 30 }, (_, i) => [`m${i}/f.js`, 1500])
  const { result: r } = await runWorkflow(`${WF}/bughunt-scan.js`, { root: '/proj', files: big }, mock)
  assert.equal(r.tier, 'large')
  assert.equal(r.stats.rounds_run, 2, 'round 2 was dry, so no round 3')
  assert.ok(r.stats.slices <= 48)
})

await test('scan: hunter cap raises slice size instead of dropping files', async () => {
  const many = Array.from({ length: 200 }, (_, i) => [`d${i}/x.js`, 1000])   // 200k lines
  const mock = (p, o) => (o.agentType === 'bug-hunter' ? { bugs: [], files_reviewed: [] } : null)
  const { result: r, logs, calls } = await runWorkflow(`${WF}/bughunt-scan.js`, { root: '/proj', files: many }, mock)
  assert.ok(r.stats.slices <= 48)
  assert.ok(logs.some(l => l.includes('Slice size raised')))
  const slicePrompts = calls.filter(c => c.opts.agentType === 'bug-hunter' && !c.opts.label.includes('cross')).map(c => c.prompt).join('\n')
  const uncovered = many.filter(([f]) => !slicePrompts.includes(`- ${f} (`))
  assert.equal(uncovered.length, 0, `files never assigned to a hunter: ${uncovered.length}`)
})

await test('scan: missing args -> helpful error', async () => {
  const { result: r } = await runWorkflow(`${WF}/bughunt-scan.js`, undefined, () => null)
  assert.equal(r.ok, false)
  assert.match(r.error, /\/bughunt/)
})

// --- bugfix-propose ----------------------------------------------------------

const bugs = [
  { id: 'B1', title: 'Null token', file: 'src/api/client.js', line: 42, severity: 'high', category: 'null-safety', description: 'd', trigger: 't', evidence: 'e' },
  { id: 'B2', title: 'Off by one', file: 'src/util/big.js', line: 12, severity: 'medium', category: 'logic', description: 'd', trigger: 't', evidence: 'e' },
  { id: 'B3', title: 'Delegation', file: 'Src/Home.pa.yaml', line: 7, severity: 'medium', category: 'powerapps', description: 'd', trigger: 't', evidence: 'e' },
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
    assert.ok(p.includes('B1') && p.includes('B2'))
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
  assert.ok(calls.find(c => c.opts.agentType === 'fix-planner' && c.prompt.includes('.pa.yaml')).prompt.includes('Power Apps note'))
  assert.deepEqual(r.recommended_ids, ['B1'])
  assert.deepEqual(r.manual_ids, ['B3'])
  assert.equal(r.items[0].bug_id, 'B1')
  assert.ok(r.end_review)
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
    if (o.agentType === 'bug-fixer') {
      const ids = [...p.matchAll(/"bug_id": "(B\d)"/g)].map(m => m[1])
      return { results: ids.map(id => ({ bug_id: id, status: 'applied', files_changed: [`${id}.js`], summary: 's' })) }
    }
    if (o.agentType === 'fix-critic') {
      const ids = [...p.matchAll(/"bug_id": "(B\d)"/g)].map(m => m[1])
      return { checks: [...new Set(ids)].map(id => ({ bug_id: id, verdict: id === 'B3' ? 'incorrect' : 'correct', problem: id === 'B3' ? 'wrong' : '' })) }
    }
  }
  const { result: r, calls } = await runWorkflow(`${WF}/bugfix-execute.js`, { root: '/proj', items, order: ['B2', 'B1', 'B3'] }, mock)
  const fixers = calls.filter(c => c.opts.agentType === 'bug-fixer')
  assert.equal(fixers.length, 2, 'B1+B2 share shared.js -> one group; B3 alone')
  const g12 = fixers.find(c => c.prompt.includes('B1'))
  assert.ok(g12.prompt.indexOf('"B2"') < g12.prompt.indexOf('"B1"'), 'apply order respected')
  assert.ok(g12.prompt.includes('shared.js'))
  assert.equal(r.applied.length, 3)
  assert.equal(r.check_problems.length, 1)
  assert.equal(r.check_problems[0].bug_id, 'B3')
})

await test('execute: fixer failure -> items reported skipped', async () => {
  const { result: r } = await runWorkflow(`${WF}/bugfix-execute.js`, { root: '/proj', items: [items[2]] }, () => null)
  assert.equal(r.skipped.length, 1)
  assert.equal(r.applied.length, 0)
})

console.log(failures ? `\n${failures} FAILED` : '\nALL PASSED')
process.exit(failures ? 1 : 0)
