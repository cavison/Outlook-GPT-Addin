export const meta = {
  name: 'bugfix-execute',
  description: 'Apply user-approved bug fixes exactly as approved, then have a read-only reviewer check each applied change',
  whenToUse: 'Launched by the /bugfix-apply and /bugloop skills only after the user has approved specific fix-plan items. Edits code.',
  phases: [
    { title: 'Apply', detail: 'one fixer per group of fixes that share files; groups never share a file' },
    { title: 'Check', detail: 'read-only reviewer compares each applied change with its approved spec' },
  ],
}

// ---------------------------------------------------------------------------
// Inputs (args):
//   root      absolute path of the project (required)
//   items     approved fix-plan items (required): {bug_id, title, severity, file, line, root_cause,
//             final_change, amendments, recommended: {edits, files_touched, tests, verification}}
//   order     bug IDs in the order to apply (optional; from the end review's apply_order)
//   cycle     loop cycle number (optional)
// ---------------------------------------------------------------------------

const A = args || {}
if (!A.root || !Array.isArray(A.items) || A.items.length === 0) {
  return { ok: false, error: 'bugfix-execute needs args {root, items: [...approved fix-plan items]}. Run it through the /bugfix-apply skill after approving a plan.' }
}

const clip = (s, n) => { s = String(s || ''); return s.length > n ? s.slice(0, n) + '…' : s }
const errors = []
async function ask(prompt, opts) {
  try { return await agent(prompt, opts) } catch (e) { errors.push(`${opts.label}: ${clip(e && e.message ? e.message : e, 300)}`); return null }
}

const FIX_SCHEMA = {
  type: 'object',
  properties: {
    results: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          bug_id: { type: 'string' },
          status: { type: 'string', enum: ['applied', 'applied-with-deviation', 'skipped'] },
          files_changed: { type: 'array', items: { type: 'string' } },
          summary: { type: 'string' },
          deviation: { type: 'string' },
        },
        required: ['bug_id', 'status', 'files_changed', 'summary'],
      },
    },
  },
  required: ['results'],
}

const CHECK_SCHEMA = {
  type: 'object',
  properties: {
    checks: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          bug_id: { type: 'string' },
          verdict: { type: 'string', enum: ['correct', 'incorrect', 'incomplete'] },
          problem: { type: 'string' },
        },
        required: ['bug_id', 'verdict'],
      },
    },
  },
  required: ['checks'],
}

// ---------------------------------------------------------------------------
// Group items so that no two groups touch the same file (union-find on files).
// Groups can then run concurrently in the same working tree without conflicts.
// ---------------------------------------------------------------------------

const order = Array.isArray(A.order) ? A.order : []
const rank = id => { const i = order.indexOf(id); return i < 0 ? order.length + A.items.indexOf(A.items.find(x => x.bug_id === id)) : i }
const items = [...A.items].sort((x, y) => rank(x.bug_id) - rank(y.bug_id))
const filesOf = it => {
  const r = it.recommended || {}
  const fs = new Set([...(r.files_touched || []), ...((r.edits || []).map(e => e.file)), it.file].filter(Boolean).map(String))
  return [...fs]
}

const parent = {}
const find = x => { while (parent[x] !== x) { parent[x] = parent[parent[x]]; x = parent[x] } return x }
const union = (a, b) => { parent[find(a)] = find(b) }
for (const it of items) {
  const key = `item:${it.bug_id}`
  parent[key] = parent[key] || key
  for (const f of filesOf(it)) {
    const fk = `file:${f}`
    parent[fk] = parent[fk] || fk
    union(key, fk)
  }
}
const groupMap = {}
for (const it of items) {
  const g = find(`item:${it.bug_id}`)
  ;(groupMap[g] = groupMap[g] || []).push(it)
}
const groups = Object.values(groupMap).map((its, i) => ({ id: `G${i + 1}`, items: its, files: [...new Set(its.flatMap(filesOf))] }))
log(`${items.length} approved fixes -> ${groups.length} independent group(s) (groups never share a file).`)

const spec = it => JSON.stringify({
  bug_id: it.bug_id,
  title: it.title,
  severity: it.severity,
  where: `${it.file}:${it.line}`,
  root_cause: it.root_cause,
  approved_change: it.final_change,
  amendments: it.amendments || '',
  edits: (it.recommended || {}).edits,
  files_touched: filesOf(it),
  tests: (it.recommended || {}).tests,
}, null, 1)

function fixerPrompt(g) {
  return [
    `Apply these user-approved bug fixes in the project at ${A.root}${A.cycle ? ` (fix cycle ${A.cycle})` : ''}. Paths are relative to that root.`,
    `Apply them in this order. Where an item has amendments, the amendments override the original edits.\n\n${g.items.map(spec).join('\n\n')}`,
    `You may change only these files: ${g.files.join(', ')}. Make the smallest edit that implements each approved change. No refactors, renames, reformatting or extra fixes.`,
    'Read the current code before each edit. If it no longer matches the spec, adapt only when the intent is unambiguous and report it as applied-with-deviation; if the intent is ambiguous, skip the item and explain why.',
    'Report one result per item.',
  ].join('\n\n')
}

function checkPrompt(g, results) {
  return [
    `Check that these approved bug fixes were applied correctly in the project at ${A.root}. You are read-only. Read the changed files.`,
    `Approved specifications:\n\n${g.items.map(spec).join('\n\n')}`,
    `What the fixer reported:\n${JSON.stringify(results, null, 1)}`,
    'For each item: "correct" if the code now implements the approved change and nothing unrelated changed nearby; "incomplete" if part of it is missing; "incorrect" if the change is wrong or introduces a new problem. Name the file and line of any problem.',
  ].join('\n\n')
}

// ---------------------------------------------------------------------------
// Apply -> Check (pipelined per group)
// ---------------------------------------------------------------------------

phase('Apply')
const out = await pipeline(groups,
  async (g) => {
    const r = await ask(fixerPrompt(g), { label: `apply ${g.id}: ${g.items.map(i => i.bug_id).join(',')}`, phase: 'Apply', schema: FIX_SCHEMA, agentType: 'bug-fixer' })
    return { g, results: r ? r.results || [] : null }
  },
  async ({ g, results }) => {
    if (!results) return { g, results: g.items.map(i => ({ bug_id: i.bug_id, status: 'skipped', files_changed: [], summary: 'fixer did not complete' })), checks: [] }
    if (!results.some(r => r.status !== 'skipped')) return { g, results, checks: [] }
    const c = await ask(checkPrompt(g, results), { label: `check ${g.id}`, phase: 'Check', schema: CHECK_SCHEMA, agentType: 'fix-critic' })
    return { g, results, checks: c ? c.checks || [] : [{ bug_id: '*', verdict: 'incomplete', problem: 'checker did not complete' }] }
  },
)

const all = out.filter(Boolean)
const results = all.flatMap(o => o.results)
const checks = all.flatMap(o => o.checks)
const applied = results.filter(r => r.status !== 'skipped')
const skipped = results.filter(r => r.status === 'skipped')
const problems = checks.filter(c => c.verdict !== 'correct')

return {
  ok: true,
  cycle: A.cycle || null,
  applied,
  skipped,
  check_problems: problems,
  files_changed: [...new Set(applied.flatMap(r => r.files_changed || []))],
  errors,
}
