export const meta = {
  name: 'bugfix-propose',
  description: 'Read-only fix planning: design fixes for confirmed bugs, attack each fix, then review the whole plan before any approval',
  whenToUse: 'Launched by the /bugfix-plan and /bugloop skills with confirmed bugs from a bughunt report. Proposes only; never edits code.',
  phases: [
    { title: 'Propose', detail: 'read-only planners design root-cause fixes, one planner per file' },
    { title: 'Challenge', detail: 'independent critics try to break each proposed fix' },
    { title: 'End review', detail: 'whole-plan review: what works, what does not, what could cause new bugs' },
  ],
}

// ---------------------------------------------------------------------------
// Inputs (args):
//   root           absolute path of the project (required)
//   bugs           confirmed findings from findings.json after evidence-gate.mjs (required; each needs id, title, file, line,
//                  severity, description, trigger, evidence, and evidence_check.ok === true or it is refused)
//   cycle          loop cycle number (optional)
//   history        {bugId: [{attempt, outcome}]} earlier failed attempts for the same bug (optional)
//   app_context    1-3 sentences on what the app does (optional)
//   test_commands  commands that will be run after fixes are applied (optional)
//   powerapps      true when the project has Power Apps source (optional)
// ---------------------------------------------------------------------------

const A = args || {}
if (!A.root || !Array.isArray(A.bugs) || A.bugs.length === 0) {
  return { ok: false, error: 'bugfix-propose needs args {root, bugs: [...]}. Run it through the /bugfix-plan skill.' }
}

// Evidence gate: only findings that passed the script-based evidence check (evidence-gate.mjs) can enter a plan.
const rejected_no_evidence = A.bugs
  .filter(b => !(b.evidence_check && b.evidence_check.ok === true))
  .map(b => ({ id: b.id, reason: b.evidence_check ? b.evidence_check.reason : 'the evidence check has not run on this finding' }))
const bugs = A.bugs.filter(b => b.evidence_check && b.evidence_check.ok === true)
if (!bugs.length) {
  return { ok: false, error: 'None of the given findings passed the evidence check, so none can enter a fix plan. Run /bughunt (which runs evidence-gate.mjs) first.', rejected_no_evidence }
}

const SEV = ['critical', 'high', 'medium', 'low']
const sevRank = s => { const i = SEV.indexOf(s); return i < 0 ? 3 : i }
const clip = (s, n) => { s = String(s || ''); return s.length > n ? s.slice(0, n) + '…' : s }
const MAX_PER_PLANNER = 8
const errors = []
async function ask(prompt, opts) {
  try { return await agent(prompt, opts) } catch (e) { errors.push(`${opts.label}: ${clip(e && e.message ? e.message : e, 300)}`); return null }
}

// ---------------------------------------------------------------------------
// Schemas
// ---------------------------------------------------------------------------

const EDIT = {
  type: 'object',
  properties: {
    file: { type: 'string' },
    location: { type: 'string' },
    change: { type: 'string' },
    before: { type: 'string' },
    after: { type: 'string' },
  },
  required: ['file', 'location', 'change'],
}

const PLAN_SCHEMA = {
  type: 'object',
  properties: {
    proposals: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          bug_id: { type: 'string' },
          still_reproduces: { type: 'boolean' },
          root_cause: { type: 'string' },
          options: {
            type: 'array',
            items: {
              type: 'object',
              properties: { summary: { type: 'string' }, pros: { type: 'string' }, cons: { type: 'string' } },
              required: ['summary', 'pros', 'cons'],
            },
          },
          recommended: {
            type: 'object',
            properties: {
              summary: { type: 'string' },
              why: { type: 'string' },
              edits: { type: 'array', items: EDIT },
              files_touched: { type: 'array', items: { type: 'string' } },
              tests: { type: 'string' },
              verification: { type: 'string' },
            },
            required: ['summary', 'why', 'edits', 'files_touched', 'verification'],
          },
          callers_checked: { type: 'array', items: { type: 'string' } },
          side_effect_risks: { type: 'string' },
          apply_mode: { type: 'string', enum: ['auto', 'manual'] },
          manual_steps: { type: 'string' },
          confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
        },
        required: ['bug_id', 'still_reproduces', 'root_cause', 'options', 'recommended', 'side_effect_risks', 'apply_mode', 'confidence'],
      },
    },
  },
  required: ['proposals'],
}

const CRITIC_SCHEMA = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['sound', 'needs-changes', 'unsound'] },
    problems: { type: 'array', items: { type: 'string' } },
    required_amendments: { type: 'string' },
    new_bug_risks: { type: 'array', items: { type: 'string' } },
    simpler_alternative: { type: 'string' },
  },
  required: ['verdict', 'problems', 'new_bug_risks'],
}

const END_SCHEMA = {
  type: 'object',
  properties: {
    overall_assessment: { type: 'string' },
    what_works: { type: 'array', items: { type: 'string' } },
    what_does_not_work: { type: 'array', items: { type: 'string' } },
    new_bug_risks: { type: 'array', items: { type: 'string' } },
    conflicts: {
      type: 'array',
      items: {
        type: 'object',
        properties: { bug_ids: { type: 'array', items: { type: 'string' } }, issue: { type: 'string' }, resolution: { type: 'string' } },
        required: ['bug_ids', 'issue', 'resolution'],
      },
    },
    items: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          bug_id: { type: 'string' },
          decision: { type: 'string', enum: ['approve', 'approve-with-amendments', 'hold', 'reject'] },
          final_change: { type: 'string' },
          amendments: { type: 'string' },
          rationale: { type: 'string' },
          risk: { type: 'string', enum: ['low', 'medium', 'high'] },
          expected_to_work: { type: 'string', enum: ['almost-certain', 'likely', 'uncertain'] },
        },
        required: ['bug_id', 'decision', 'final_change', 'rationale', 'risk', 'expected_to_work'],
      },
    },
    apply_order: { type: 'array', items: { type: 'string' } },
  },
  required: ['overall_assessment', 'what_works', 'what_does_not_work', 'new_bug_risks', 'conflicts', 'items', 'apply_order'],
}

// ---------------------------------------------------------------------------
// Prompts
// ---------------------------------------------------------------------------

const fmtBug = b => [
  `[${b.id}] ${b.title}`,
  `Location: ${b.file}:${b.line}${b.end_line ? `-${b.end_line}` : ''} | severity: ${b.severity} | category: ${b.category || 'n/a'}`,
  `What is wrong: ${b.description}`,
  `Trigger and outcome: ${b.trigger}`,
  b.evidence ? `Evidence:\n${b.evidence}` : '',
  b.verification && b.verification.reproduction ? `Reproduction (from verifier): ${b.verification.reproduction}` : '',
].filter(Boolean).join('\n')

const history = A.history || {}
const fmtHistory = b => {
  const h = history[b.id] || history[b.title]
  if (!Array.isArray(h) || !h.length) return ''
  return `Earlier fix attempts for ${b.id} that did NOT work (use a different approach, or explain why this one is different):\n${h.map((x, i) => `${i + 1}. ${x.attempt || x.summary || ''} -> ${x.outcome || 'still present'}`).join('\n')}`
}

function plannerPrompt(group) {
  return [
    `Design fixes for confirmed bugs in the codebase at ${A.root}. You are read-only: you write a specification, someone else applies it after a person approves it.`,
    A.app_context ? `About the app: ${A.app_context}` : '',
    `Bugs (all in or around ${group.file}):\n\n${group.bugs.map(fmtBug).join('\n\n')}`,
    group.bugs.map(fmtHistory).filter(Boolean).join('\n\n'),
    `For EACH bug:
1. Re-read the code and confirm it still reproduces (still_reproduces). If not, say so and propose no edits.
2. Identify the root cause.
3. Grep for every caller or usage the fix could affect; list them in callers_checked.
4. Give at least two fix options with pros and cons.
5. Recommend one: the minimal change that fixes the root cause and matches the codebase's conventions. No refactors or unrelated cleanups.
6. Specify the edits precisely: file (relative to the project root), location (function or line), the change, and short before/after snippets. List every file touched, including any test file.
7. Describe side-effect risks and how to verify the fix${Array.isArray(A.test_commands) && A.test_commands.length ? ` (these commands will run afterwards: ${A.test_commands.join(', ')})` : ''}.
8. apply_mode: "auto" when the edits are ordinary code changes; "manual" when the change must be made in a designer tool, a platform setting or an external system, and then write manual_steps a person can follow.`,
    A.powerapps ? 'Power Apps note: Microsoft advises only minor direct edits to .pa.yaml source, and none in apps that use code components. For .pa.yaml files, use apply_mode "auto" only for small single-formula edits; otherwise use "manual" and write step-by-step Power Apps Studio instructions.' : '',
    'If several bugs here interact (same lines, same root cause), say so and make their edits consistent with each other.',
  ].filter(Boolean).join('\n\n')
}

const CRITIC_LENSES = {
  both: 'Check both root cause and correctness, and regressions and blast radius.',
  root: 'Lens: root cause and correctness. Does the fix remove the cause for every trigger path, including edge cases, or only the reported symptom?',
  blast: 'Lens: regressions and blast radius. Grep every caller and usage. What behavior changes for them? What new null path, race, unhandled error or security hole could this introduce?',
}

function criticPrompt(bug, proposal, lens) {
  return [
    `Try to break this proposed bug fix in the codebase at ${A.root}. You did not design it and have no reason to defend it. You are read-only.`,
    `The bug:\n${fmtBug(bug)}`,
    `The proposed fix:\n${JSON.stringify({ root_cause: proposal.root_cause, recommended: proposal.recommended, side_effect_risks: proposal.side_effect_risks, apply_mode: proposal.apply_mode }, null, 2)}`,
    CRITIC_LENSES[lens],
    'Verdict: "sound" if it fixes the root cause without new problems; "needs-changes" if it is the right idea but needs specific amendments (write them in required_amendments precisely); "unsound" if it is the wrong approach (say why, and give a simpler or safer alternative if you see one). Name the file and line for each problem. Do not invent problems to look thorough.',
  ].join('\n\n')
}

function endReviewPrompt(items) {
  return [
    `You are doing the end-of-plan review for a set of proposed bug fixes in the codebase at ${A.root}${A.cycle ? ` (fix cycle ${A.cycle})` : ''}. A person will approve or reject each item based on your review, and approved items are then applied automatically and the code re-tested. You are read-only.`,
    'Think about the plan as ONE change set, not as separate items. Read the code where you need to. Answer:',
    '- What works: which fixes are clearly right?\n- What does not work: which fixes are wrong, incomplete, or only treat symptoms?\n- What would cause more bugs: new failure modes, regressions for callers, risky assumptions?\n- Conflicts: fixes that touch the same lines, depend on each other, or must be applied in a specific order.\n- For each item, the cleanest solution that will almost certainly work: a final decision, the exact final change (merging in any critic amendments you agree with), its risk, and how sure you are it will work.',
    'Decisions: "approve" (apply as specified), "approve-with-amendments" (apply with the amendments you state), "hold" (needs a human decision or more information; say what), "reject" (the fix is worse than the bug or cannot work; say why). Recommend "approve" only for fixes you expect to almost certainly work without new bugs.',
    `Items (bug, proposal and critic reviews):\n${JSON.stringify(items, null, 1)}`,
    'Finally give apply_order: the bug IDs you recommend applying, in a safe order.',
  ].join('\n\n')
}

// ---------------------------------------------------------------------------
// Group bugs by primary file so fixes to the same file are designed together
// ---------------------------------------------------------------------------

const byFile = {}
for (const b of bugs) {
  const f = String(b.file || 'unknown')
  ;(byFile[f] = byFile[f] || []).push(b)
}
const groups = []
for (const [file, bugs] of Object.entries(byFile)) {
  bugs.sort((x, y) => sevRank(x.severity) - sevRank(y.severity))
  for (let i = 0; i < bugs.length; i += MAX_PER_PLANNER) groups.push({ file, bugs: bugs.slice(i, i + MAX_PER_PLANNER) })
}
const oversized = Object.entries(byFile).filter(([, b]) => b.length > MAX_PER_PLANNER)
if (oversized.length) log(`${oversized.map(([f, b]) => `${f} (${b.length})`).join(', ')}: more than ${MAX_PER_PLANNER} bugs in one file, so several planners share it; the end review checks them for conflicts.`)
log(`${bugs.length} bugs -> ${groups.length} planner(s).${rejected_no_evidence.length ? ` ${rejected_no_evidence.length} refused: no valid evidence.` : ''}`)

// ---------------------------------------------------------------------------
// Propose -> Challenge (pipelined per file group)
// ---------------------------------------------------------------------------

const failed = []
const bugById = Object.fromEntries(bugs.map(b => [b.id, b]))

phase('Propose')
const perGroup = await pipeline(groups,
  async (g) => {
    let plan = await ask(plannerPrompt(g), { label: `plan ${clip(g.file, 50)}`, phase: 'Propose', schema: PLAN_SCHEMA, agentType: 'fix-planner' })
    if (!plan) plan = await ask(plannerPrompt(g), { label: `plan ${clip(g.file, 50)} retry`, phase: 'Propose', schema: PLAN_SCHEMA, agentType: 'fix-planner' })
    if (!plan) { failed.push(...g.bugs.map(b => b.id)); return [] }
    const ids = new Set(g.bugs.map(b => b.id))
    const got = (plan.proposals || []).filter(p => ids.has(p.bug_id))
    const missingIds = g.bugs.filter(b => !got.some(p => p.bug_id === b.id)).map(b => b.id)
    if (missingIds.length) failed.push(...missingIds)
    return got
  },
  async (proposals) => parallel(proposals.map(p => async () => {
    const bug = bugById[p.bug_id]
    if (!p.still_reproduces || p.apply_mode === 'manual') return { bug, proposal: p, critiques: [] }
    const lenses = sevRank(bug.severity) <= 1 ? ['root', 'blast'] : ['both']
    const critiques = (await parallel(lenses.map(lens => () =>
      ask(criticPrompt(bug, p, lens), { label: `challenge ${p.bug_id}${lenses.length > 1 ? ` ${lens}` : ''}`, phase: 'Challenge', schema: CRITIC_SCHEMA, agentType: 'fix-critic' })
        .then(c => (c ? { lens, ...c } : null))))).filter(Boolean)
    return { bug, proposal: p, critiques }
  })),
)

const items = perGroup.filter(Boolean).flat().filter(Boolean)
if (!items.length) return { ok: false, error: 'No fix proposals were produced. If the read-only agent types are not loaded yet, restart the session so .claude/agents/ is picked up.', failed, rejected_no_evidence, errors }

// ---------------------------------------------------------------------------
// End review (needs the whole plan at once)
// ---------------------------------------------------------------------------

phase('End review')
const compact = items.map(({ bug, proposal, critiques }) => ({
  bug_id: bug.id,
  severity: bug.severity,
  title: bug.title,
  file: bug.file,
  line: bug.line,
  still_reproduces: proposal.still_reproduces,
  root_cause: proposal.root_cause,
  recommended: proposal.recommended,
  side_effect_risks: proposal.side_effect_risks,
  apply_mode: proposal.apply_mode,
  planner_confidence: proposal.confidence,
  critiques: critiques.map(c => ({ lens: c.lens, verdict: c.verdict, problems: c.problems, amendments: c.required_amendments, new_bug_risks: c.new_bug_risks, simpler_alternative: c.simpler_alternative })),
}))
let review = await ask(endReviewPrompt(compact), { label: 'end review', phase: 'End review', schema: END_SCHEMA, agentType: 'fix-critic' })
if (!review) review = await ask(endReviewPrompt(compact), { label: 'end review retry', phase: 'End review', schema: END_SCHEMA, agentType: 'fix-critic' })

const decisionOf = id => (review && (review.items || []).find(i => i.bug_id === id)) || null
const plan = items.map(({ bug, proposal, critiques }) => {
  const d = decisionOf(bug.id)
  return {
    bug_id: bug.id,
    severity: bug.severity,
    title: bug.title,
    file: bug.file,
    line: bug.line,
    still_reproduces: proposal.still_reproduces,
    root_cause: proposal.root_cause,
    options: proposal.options,
    recommended: proposal.recommended,
    callers_checked: proposal.callers_checked,
    side_effect_risks: proposal.side_effect_risks,
    apply_mode: proposal.apply_mode,
    manual_steps: proposal.manual_steps,
    planner_confidence: proposal.confidence,
    critiques,
    decision: d ? d.decision : (proposal.still_reproduces ? 'hold' : 'reject'),
    final_change: d ? d.final_change : proposal.recommended.summary,
    amendments: d ? d.amendments : '',
    rationale: d ? d.rationale : 'End review did not complete; decide manually.',
    risk: d ? d.risk : 'medium',
    expected_to_work: d ? d.expected_to_work : 'uncertain',
  }
}).sort((x, y) => sevRank(x.severity) - sevRank(y.severity))

return {
  ok: true,
  cycle: A.cycle || null,
  items: plan,
  end_review: review ? {
    overall_assessment: review.overall_assessment,
    what_works: review.what_works,
    what_does_not_work: review.what_does_not_work,
    new_bug_risks: review.new_bug_risks,
    conflicts: review.conflicts,
    apply_order: review.apply_order,
  } : null,
  recommended_ids: plan.filter(p => p.apply_mode === 'auto' && (p.decision === 'approve' || p.decision === 'approve-with-amendments')).map(p => p.bug_id),
  manual_ids: plan.filter(p => p.apply_mode === 'manual').map(p => p.bug_id),
  failed,
  rejected_no_evidence,
  errors,
}
