export const meta = {
  name: 'bughunt-scan',
  description: 'Read-only bug hunt: fresh-context hunters per code slice, then independent skeptics try to refute every finding',
  whenToUse: 'Launched by the /bughunt and /bugloop skills, which build the file list it needs. Read-only: never edits code.',
  phases: [
    { title: 'Hunt', detail: 'one fresh read-only agent per code slice, plus cross-cutting lenses' },
    { title: 'Verify', detail: 'independent skeptics try to disprove each finding' },
    { title: 'Regression check', detail: 'did bugs fixed in the previous cycle stay fixed?' },
  ],
}

// ---------------------------------------------------------------------------
// Inputs (args):
//   root            absolute path of the project (required)
//   files           [[relativePath, lineCount], ...] from scope.sh (required)
//   mode            'auto' | 'lean' | 'small' | 'medium' | 'large' | 'max' (default 'auto')
//   focus           optional text: what the user wants extra attention on
//   app_context     optional 1-3 sentences on what the app does
//   powerapps       {detected: bool} from scope.sh
//   clean_threshold lowest severity that blocks "clean" (default 'medium')
//   previous_bugs   [{id, title, file, line, description, fix_summary}] fixed last cycle
//   max_agents      hard ceiling on agents for this run (default 900; runtime cap is 1000)
// ---------------------------------------------------------------------------

const A = args || {}
if (!A.root || !Array.isArray(A.files) || A.files.length === 0) {
  return {
    ok: false,
    error: 'bughunt-scan needs args {root, files: [[path, lines], ...]}. Run it through the /bughunt skill, which builds the file list.',
  }
}

const SEV = ['critical', 'high', 'medium', 'low']
const sevRank = s => { const i = SEV.indexOf(s); return i < 0 ? 3 : i }
const threshold = SEV.includes(A.clean_threshold) ? A.clean_threshold : 'medium'

const TIERS = {
  lean:   { chunkLines: 4000, maxHunters: 8,  cross: ['general'], skeptics: () => 1, rounds: 1 },
  small:  { chunkLines: 1500, maxHunters: 6,  cross: ['general'], skeptics: () => 1, rounds: 1 },
  medium: { chunkLines: 2500, maxHunters: 24, cross: ['integration', 'security', 'state'], skeptics: s => (sevRank(s) <= 1 ? 3 : 1), rounds: 2 },
  large:  { chunkLines: 3000, maxHunters: 48, cross: ['integration', 'security', 'state', 'config'], skeptics: () => 3, rounds: 3 },
  max:    { chunkLines: 1500, maxHunters: 80, cross: ['integration', 'security', 'state', 'config'], skeptics: s => (sevRank(s) <= 1 ? 5 : 3), rounds: 3 },
}

const totalLines = A.files.reduce((n, f) => n + (Number(f[1]) || 0), 0)
const requested = String(A.mode || 'auto').toLowerCase()
const tierName = requested !== 'auto' ? requested
  : totalLines < 3000 ? 'small' : totalLines < 30000 ? 'medium' : 'large'
const cfg = TIERS[tierName]
if (!cfg) return { ok: false, error: `Unknown mode "${A.mode}". Use auto, lean, small, medium, large or max.` }

const AGENT_CAP = Math.min(Number(A.max_agents) || 900, 990)
const powerapps = !!(A.powerapps && A.powerapps.detected)

// ---------------------------------------------------------------------------
// Shared prompt text
// ---------------------------------------------------------------------------

const SEVERITY_RUBRIC = `Severity rubric (use exactly these levels):
- critical: data loss or corruption, a security breach (auth bypass, injection, secret exposure), or a crash/total failure on a main path most users hit.
- high: a core feature gives wrong results or fails on a common path, with no reasonable workaround.
- medium: wrong behavior on a realistic edge case or error path (bad input, network failure, empty data, concurrency) that real users will eventually hit.
- low: minor or unlikely: cosmetic, rare edge case, small leak, misleading message.`

const WHAT_COUNTS = `What counts as a bug: code that, for some reachable input or state, gives a wrong result, crashes, hangs, leaks, loses or corrupts data, or opens a security hole. You must be able to name the triggering input/state and the wrong outcome.
Do NOT report: style, naming, formatting, missing comments or tests, refactoring ideas, hypothetical future misuse, missing features, or best-practice advice without a concrete failure.`

const EVIDENCE_RULES = `For every bug give: the file path relative to the project root, the 1-based line of the faulty code, a short verbatim quote of that code (at most 6 lines) as evidence, the concrete trigger (input, state or sequence) and the wrong outcome.
If you suspect a bug but cannot fully prove it, still report it with confidence "low": an independent skeptic checks every finding.`

const POWERAPPS_CHECKLIST = `This slice contains Power Apps source (Power Fx in .pa.yaml / .fx.yaml). Check in particular:
- Delegation: Filter/Search/LookUp/Sort/CountRows (and ClearCollect from a data source) using non-delegable functions or operators against SharePoint, Dataverse or SQL silently process only the first rows up to the app's data row limit (500 by default, 2000 max), so results are wrong on larger tables.
- Writes without error handling: Patch, SubmitForm, Remove and flow .Run() calls whose failures are not handled (IfError, Errors(), OnFailure), and navigation that happens before a submit has succeeded.
- ForAll evaluates records in no guaranteed order and possibly in parallel; Concurrent() runs its formulas in parallel. Flag logic that depends on ordering or on side effects between them.
- Variable scope: context variables (UpdateContext) are screen-local; global variables (Set) are global; reading the wrong one gives Blank. App.OnStart work that screens read before it finishes.
- Blank handling: LookUp/First returning Blank then dereferenced; IsBlank vs IsEmpty on tables; comparing to "" vs Blank().
- Types and data shapes: Choice/Lookup columns compared to text without .Value; Text vs Number comparisons; Value()/DateValue() locale issues; UTC vs local time zones.
- Security: permissions enforced only through Visible/DisplayMode (client-side only); data cached in collections the user should not see; case-sensitive User().Email comparisons.
- Environment coupling: hard-coded URLs, GUIDs, list names, emails or environment IDs that break when the app moves between environments.
- Controls: Gallery.Selected when nothing is selected; forms not Reset after submit; timers that repeat writes; names that collide with column names without disambiguation.`

const ROUND_LENSES = [
  'Everything. Any kind of defect: logic errors, wrong conditions, off-by-one, null/undefined, wrong types or units, API misuse, broken state updates, error handling, async ordering, security.',
  'Edge cases and failure paths: empty, huge, malformed or unicode input; missing or extra fields; network/IO failures, timeouts and retries; partial failure and cleanup; resource leaks; concurrency, ordering and re-entrancy; time zones and locale.',
  'Security and data integrity: injection (SQL, HTML, command, formula), XSS, authentication and authorization gaps, exposed secrets or tokens, unsafe eval or deserialization, trusting client-side data, data loss or corruption, sensitive data in logs.',
  'Contracts and assumptions: how this code is called and what it calls: argument order, units, nullability, unhandled return values, error propagation, version or platform quirks, config and environment assumptions.',
]

const CROSS_LENSES = {
  general: 'Cross-file integration and security across the whole codebase: mismatched contracts between modules (function signatures vs callers, API client vs server routes, shared constants, event names, config keys), secrets committed in code, injection, missing auth checks, unsafe handling of external data.',
  integration: 'Cross-file contracts: function signatures vs their callers, API clients vs server routes and payload shapes, shared types and constants, event/message names, config keys and environment variables used vs defined, schema vs code.',
  security: 'Security across the whole codebase: secrets or tokens committed in code, injection (SQL, HTML, command, formula), XSS, authentication and authorization gaps, insecure CORS/CSP, unsafe eval or deserialization, trusting client-side data, sensitive data in logs or storage.',
  state: 'Shared state, lifecycle and async behavior across modules: global or cached state that goes stale, initialization order, teardown and cleanup, races between concurrent operations, retries that duplicate side effects, unhandled promise rejections.',
  config: 'Build, configuration and deployment: manifests (e.g. Office add-in manifest.xml), package scripts, environment variables, permissions declared vs used, version and platform compatibility assumptions, feature flags, production vs development settings.',
  powerapps: `App-level Power Apps review across all screens and components.\n${POWERAPPS_CHECKLIST}`,
}

const SKEPTIC_LENSES = [
  'Concentrate on reachability: can real callers and real inputs actually trigger this?',
  'Concentrate on guards and intent: is it already handled elsewhere, or is the behavior intended?',
  'Concentrate on the outcome: walk through the trigger step by step. Does the wrong outcome really happen, and how bad is it?',
  'Concentrate on the evidence: does the quoted code match the file, and does the claim describe it accurately?',
  'Concentrate on the severity: given who hits this and how often, which rubric level is right?',
]

// ---------------------------------------------------------------------------
// Schemas
// ---------------------------------------------------------------------------

const BUG_ITEM = {
  type: 'object',
  properties: {
    title: { type: 'string' },
    file: { type: 'string' },
    line: { type: 'integer' },
    end_line: { type: 'integer' },
    severity: { type: 'string', enum: SEV },
    category: { type: 'string', enum: ['logic', 'null-safety', 'error-handling', 'async-race', 'security', 'data-integrity', 'performance', 'resource-leak', 'api-contract', 'config', 'powerapps', 'other'] },
    description: { type: 'string' },
    trigger: { type: 'string' },
    evidence: { type: 'string' },
    confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
  },
  required: ['title', 'file', 'line', 'severity', 'category', 'description', 'trigger', 'evidence', 'confidence'],
}

const HUNT_SCHEMA = {
  type: 'object',
  properties: {
    bugs: { type: 'array', items: BUG_ITEM },
    files_reviewed: { type: 'array', items: { type: 'string' } },
    files_not_reviewed: { type: 'array', items: { type: 'string' } },
    notes: { type: 'string' },
  },
  required: ['bugs', 'files_reviewed'],
}

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['confirmed', 'refuted', 'uncertain'] },
    reasoning: { type: 'string' },
    severity: { type: 'string', enum: SEV },
    reproduction: { type: 'string' },
  },
  required: ['verdict', 'reasoning', 'severity'],
}

const REGRESSION_SCHEMA = {
  type: 'object',
  properties: {
    status: { type: 'string', enum: ['fixed', 'still-present', 'partially-fixed', 'unknown'] },
    evidence: { type: 'string' },
    new_problem: { type: 'string' },
  },
  required: ['status', 'evidence'],
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const rootPrefix = String(A.root).replace(/\/+$/, '') + '/'
const normPath = p => {
  let s = String(p || '').replace(/\\/g, '/')
  if (s.startsWith(rootPrefix)) s = s.slice(rootPrefix.length)
  return s.replace(/^\.\//, '')
}
const dirOf = p => { const i = p.lastIndexOf('/'); return i < 0 ? '' : p.slice(0, i) }
const words = s => new Set(String(s).toLowerCase().match(/[a-z0-9]+/g) || [])
const isPowerAppsFile = p => /\.(pa|fx)\.yaml$/i.test(p)
const clip = (s, n) => { s = String(s || ''); return s.length > n ? s.slice(0, n) + '…' : s }

function makeChunks(files, target) {
  const sorted = files.map(f => [normPath(f[0]), Math.max(1, Number(f[1]) || 1)])
    .sort((a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0))
  const chunks = []
  let cur = null
  const flush = () => { if (cur && cur.parts.length) chunks.push(cur); cur = null }
  for (const [path, n] of sorted) {
    if (n > target * 1.5) {
      // One big file: split it into line ranges, one slice each.
      flush()
      const pieces = Math.ceil(n / target)
      const step = Math.ceil(n / pieces)
      for (let s = 1; s <= n; s += step) {
        const to = Math.min(n, s + step - 1)
        chunks.push({ parts: [{ path, from: s, to, total: n }], lines: to - s + 1 })
      }
      continue
    }
    // Keep a directory together; start a new slice when full, or when the directory changes and the slice is mostly full.
    if (cur && (cur.lines + n > target || (dirOf(cur.parts[cur.parts.length - 1].path) !== dirOf(path) && cur.lines >= target * 0.6))) flush()
    if (!cur) cur = { parts: [], lines: 0 }
    cur.parts.push({ path, from: 1, to: n, total: n })
    cur.lines += n
  }
  flush()
  return chunks.map((c, i) => ({ ...c, id: `S${i + 1}`, powerapps: c.parts.some(p => isPowerAppsFile(p.path)) }))
}

function inChunk(bug, chunk) {
  const f = normPath(bug.file)
  return chunk.parts.some(p => p.path === f && (bug.line || 0) >= p.from - 5 && (bug.line || 0) <= p.to + 5)
}

function similar(a, b) {
  if (normPath(a.file) !== normPath(b.file)) return false
  if (Math.abs((a.line || 0) - (b.line || 0)) > 3) return false
  if (a.category === b.category) return true
  const wa = words(a.title), wb = words(b.title)
  let inter = 0
  for (const w of wa) if (wb.has(w)) inter++
  return inter / Math.max(1, Math.min(wa.size, wb.size)) >= 0.5
}

const fmtBug = b => [
  `Title: ${b.title}`,
  `Location: ${normPath(b.file)}:${b.line}${b.end_line ? `-${b.end_line}` : ''}`,
  `Claimed severity: ${b.severity} | category: ${b.category} | hunter confidence: ${b.confidence}`,
  `What is wrong: ${b.description}`,
  `Trigger and outcome: ${b.trigger}`,
  `Evidence quoted by the hunter:\n${b.evidence}`,
].join('\n')

let agentsUsed = 0
const dropped = []
const errors = []
async function spawn(prompt, opts) {
  if (agentsUsed >= AGENT_CAP) { dropped.push(opts.label); return null }
  agentsUsed++
  try {
    return await agent(prompt, opts)
  } catch (e) {
    errors.push(`${opts.label}: ${clip(e && e.message ? e.message : e, 300)}`)
    return null
  }
}

async function runHunter(prompt, label) {
  let r = await spawn(prompt, { label, phase: 'Hunt', schema: HUNT_SCHEMA, agentType: 'bug-hunter' })
  if (!r) {
    log(`${label} returned nothing; retrying once`)
    r = await spawn(prompt, { label: `${label} retry`, phase: 'Hunt', schema: HUNT_SCHEMA, agentType: 'bug-hunter' })
  }
  return r
}

// ---------------------------------------------------------------------------
// Prompts
// ---------------------------------------------------------------------------

function slicePrompt(chunk, round, known) {
  const fileList = chunk.parts.map(p => (p.from === 1 && p.to === p.total)
    ? `- ${p.path} (${p.total} lines)`
    : `- ${p.path} lines ${p.from}-${p.to} of ${p.total} (read nearby code as needed for context)`).join('\n')
  return [
    `You are hunting bugs in one slice of the codebase at ${A.root}. You are read-only.`,
    A.app_context ? `About the app: ${A.app_context}` : '',
    `Your slice ${chunk.id} (${chunk.lines} lines). Read ALL of it, top to bottom:\n${fileList}`,
    `Paths are relative to ${A.root}. You may open any other file to check callers, definitions or contracts, but report only bugs whose faulty code is inside your slice.`,
    `Focus for this pass: ${ROUND_LENSES[(round - 1) % ROUND_LENSES.length]}`,
    known.length ? `Already reported for this slice (do NOT report these again; look for different ones):\n${known.map(k => `- ${normPath(k.file)}:${k.line} ${k.title}`).join('\n')}` : '',
    chunk.powerapps ? POWERAPPS_CHECKLIST : '',
    A.focus ? `The user asked for extra attention on: ${A.focus}` : '',
    WHAT_COUNTS,
    SEVERITY_RUBRIC,
    EVIDENCE_RULES,
    'There is no quota and no reward for finishing early. When you think you are done, go through each file once more for the kinds of defect you have not yet considered. Then report every bug you can substantiate, and list the files you fully reviewed and any you could not.',
  ].filter(Boolean).join('\n\n')
}

const fileMap = (() => {
  const all = A.files.map(f => `${normPath(f[0])} (${f[1]})`)
  if (all.length <= 1500) return all.join('\n')
  log(`File map for cross-cutting hunters truncated to 1500 of ${all.length} paths; they can still Glob/Grep the rest.`)
  return all.slice(0, 1500).join('\n') + `\n… and ${all.length - 1500} more (use Glob/Grep)`
})()

function crossPrompt(lens) {
  return [
    `You are a cross-cutting bug hunter for the codebase at ${A.root}. You are read-only. Other hunters review individual files; your job is bugs that only show up ACROSS files, through one lens.`,
    A.app_context ? `About the app: ${A.app_context}` : '',
    `Your lens: ${CROSS_LENSES[lens]}`,
    `Use Grep and Glob to trace the relevant connections, then Read the code involved. Report bugs anywhere in the codebase that fall under your lens.`,
    `Files in scope (path and line count):\n${fileMap}`,
    A.focus ? `The user asked for extra attention on: ${A.focus}` : '',
    WHAT_COUNTS,
    SEVERITY_RUBRIC,
    EVIDENCE_RULES,
    'There is no quota and no reward for finishing early. Report every bug you can substantiate under your lens.',
  ].filter(Boolean).join('\n\n')
}

function skepticPrompt(b, k, n) {
  return [
    `An independent hunter claims there is a bug in the codebase at ${A.root}. You did not write this claim and have no reason to defend it. Try to prove it WRONG by reading the actual code.`,
    A.app_context ? `About the app: ${A.app_context}` : '',
    `The claim:\n${fmtBug(b)}`,
    'Check, with the code in front of you: (1) does the quoted code exist at that location (or nearby)? (2) is the trigger reachable? Trace real callers and inputs. (3) is it already guarded elsewhere (caller validation, framework behavior, types, an upstream try/catch)? (4) is the "wrong outcome" actually wrong, or intended or harmless? (5) is the severity right?',
    n > 1 ? `You are skeptic ${k + 1} of ${n} and work independently. ${SKEPTIC_LENSES[k % SKEPTIC_LENSES.length]}` : '',
    'Verdict: "refuted" if any check shows the bug is not real as described; "confirmed" only if you can point to code proving the trigger is reachable and the outcome is wrong; "uncertain" if the code does not let you decide. Truth matters more than winning: do not refute a bug that is clearly real. Also give the severity you believe is correct.',
    SEVERITY_RUBRIC,
  ].filter(Boolean).join('\n\n')
}

function regressionPrompt(pb) {
  return [
    `In the previous cycle a bug was reported in the codebase at ${A.root} and a fix was applied. Check, by reading the current code, whether the bug is really gone. You are read-only.`,
    `Bug ${pb.id}: ${pb.title}`,
    `Where it was: ${normPath(pb.file)}:${pb.line} (lines may have moved since)`,
    pb.description ? `What was wrong: ${pb.description}` : '',
    pb.fix_summary ? `What the fix was supposed to do: ${pb.fix_summary}` : '',
    'Status: "fixed" if the trigger no longer produces the wrong outcome; "still-present" if it does; "partially-fixed" if only some paths are fixed; "unknown" if you cannot tell. Quote the current code as evidence. If the fix itself introduced a new problem, describe it in new_problem.',
  ].filter(Boolean).join('\n\n')
}

// ---------------------------------------------------------------------------
// Verification
// ---------------------------------------------------------------------------

function tally(b, votes) {
  const vs = votes.filter(Boolean)
  const n = vs.length
  if (!n) return { status: 'unverified', severity: b.severity, votes: '0 skeptics completed', reasons: [] }
  const c = vs.filter(v => v.verdict === 'confirmed').length
  const r = vs.filter(v => v.verdict === 'refuted').length
  const status = c * 2 > n ? 'confirmed' : r * 2 > n ? 'refuted' : 'disputed'
  // Severity: median of the confirming skeptics' calibrated severity (ties go to the more severe).
  const ranks = vs.filter(v => v.verdict === 'confirmed').map(v => sevRank(v.severity)).sort((x, y) => x - y)
  const severity = ranks.length ? SEV[ranks[Math.floor((ranks.length - 1) / 2)]] : b.severity
  return {
    status,
    severity,
    votes: `${c}/${n} confirmed, ${r}/${n} refuted`,
    reasons: vs.map(v => `${v.verdict}: ${clip(v.reasoning, 500)}`),
    reproduction: (vs.find(v => v.verdict === 'confirmed' && v.reproduction) || {}).reproduction,
  }
}

const seen = []
const confirmed = []
const disputed = []
const refuted = []
let skepticsRun = 0

async function verify(b) {
  const n = cfg.skeptics(b.severity)
  const votes = await parallel(Array.from({ length: n }, (_, k) => () => {
    skepticsRun++
    return spawn(skepticPrompt(b, k, n), {
      label: `verify ${normPath(b.file)}:${b.line}${n > 1 ? ` #${k + 1}` : ''}`,
      phase: 'Verify',
      schema: VERDICT_SCHEMA,
      agentType: 'bug-skeptic',
    })
  }))
  const t = tally(b, votes)
  const rec = {
    title: b.title,
    file: normPath(b.file),
    line: b.line,
    end_line: b.end_line,
    severity: t.severity,
    hunter_severity: b.severity,
    category: b.category,
    description: b.description,
    trigger: b.trigger,
    evidence: b.evidence,
    hunter_confidence: b.confidence,
    found_by: b.found_by,
    also_found_by: b.also_found_by,
    verification: { status: t.status, votes: t.votes, reasons: t.reasons, reproduction: t.reproduction },
  }
  if (t.status === 'confirmed') confirmed.push(rec)
  else if (t.status === 'refuted') refuted.push({ title: rec.title, file: rec.file, line: rec.line, severity: b.severity, found_by: b.found_by, reason: clip(t.reasons.find(x => x.startsWith('refuted')) || t.reasons[0], 400) })
  else disputed.push(rec)
  return t.status
}

// ---------------------------------------------------------------------------
// Plan the slices
// ---------------------------------------------------------------------------

let chunkLines = cfg.chunkLines
let chunks = makeChunks(A.files, chunkLines)
while (chunks.length > cfg.maxHunters) {
  chunkLines = Math.ceil(chunkLines * 1.25)
  chunks = makeChunks(A.files, chunkLines)
}
if (chunkLines !== cfg.chunkLines) {
  log(`Slice size raised from ${cfg.chunkLines} to ~${chunkLines} lines so ${chunks.length} hunters (cap ${cfg.maxHunters}) cover every file.`)
  if (chunkLines > 8000) log('Warning: slices above ~8000 lines are too big for one agent to read closely. Consider --mode max or hunting one sub-folder at a time.')
}
const crossLenses = [...cfg.cross, ...(powerapps ? ['powerapps'] : [])]
log(`Tier "${tierName}": ${A.files.length} files, ${totalLines} lines -> ${chunks.length} slices + ${crossLenses.length} cross-cutting hunters, up to ${cfg.rounds} round(s).`)

// Regression checks for bugs fixed in the previous cycle run alongside the hunt.
const previous = Array.isArray(A.previous_bugs) ? A.previous_bugs : []
const regressionP = parallel(previous.map(pb => () =>
  spawn(regressionPrompt(pb), { label: `recheck ${pb.id}`, phase: 'Regression check', schema: REGRESSION_SCHEMA, agentType: 'bug-skeptic' })
    .then(v => ({ id: pb.id, title: pb.title, file: normPath(pb.file), ...(v || { status: 'unknown', evidence: 'checker did not complete' }) }))))

// ---------------------------------------------------------------------------
// Hunt rounds (loop until a round adds no new confirmed bug)
// ---------------------------------------------------------------------------

const reviewed = new Set()
const notReviewed = new Set()
const failedSlices = []
let huntersRun = 0
let huntersOk = 0
let candidates = 0
let duplicates = 0
let roundsRun = 0

phase('Hunt')
for (let round = 1; round <= cfg.rounds; round++) {
  roundsRun = round
  let freshConfirmed = 0
  const tasks = chunks.map(c => ({ kind: 'slice', chunk: c }))
  if (round === 1) for (const lens of crossLenses) tasks.push({ kind: 'cross', lens })

  await pipeline(tasks,
    async (t) => {
      huntersRun++
      if (t.kind === 'slice') {
        const known = seen.filter(b => inChunk(b, t.chunk))
        const label = `hunt ${t.chunk.id}${round > 1 ? ` r${round}` : ''} ${clip(t.chunk.parts[0].path, 40)}${t.chunk.parts.length > 1 ? ` +${t.chunk.parts.length - 1}` : ''}`
        return { t, res: await runHunter(slicePrompt(t.chunk, round, known), label) }
      }
      return { t, res: await runHunter(crossPrompt(t.lens), `hunt cross:${t.lens}`) }
    },
    async ({ t, res }) => {
      if (!res) {
        if (t.kind === 'slice') failedSlices.push({ id: t.chunk.id, round, files: t.chunk.parts.map(p => p.path) })
        else failedSlices.push({ id: `cross:${t.lens}`, round, files: [] })
        return []
      }
      huntersOk++
      for (const f of res.files_reviewed || []) reviewed.add(normPath(f))
      for (const f of res.files_not_reviewed || []) notReviewed.add(normPath(f))
      const finder = t.kind === 'slice' ? `${t.chunk.id}${round > 1 ? `/r${round}` : ''}` : `cross:${t.lens}`
      const fresh = []
      for (const b of res.bugs || []) {
        candidates++
        const dup = seen.find(s => similar(s, b))
        if (dup) { duplicates++; dup.also_found_by = [...(dup.also_found_by || []), finder]; continue }
        const rec = { ...b, file: normPath(b.file), found_by: finder }
        seen.push(rec)
        fresh.push(rec)
      }
      return fresh
    },
    async (fresh) => {
      const statuses = await parallel(fresh.map(b => () => verify(b)))
      freshConfirmed += statuses.filter(s => s === 'confirmed').length
      return statuses
    },
  )

  log(`Round ${round}: ${confirmed.length} confirmed, ${disputed.length} disputed, ${refuted.length} refuted so far (${freshConfirmed} new confirmed this round).`)
  if (freshConfirmed === 0) break
  if (agentsUsed >= AGENT_CAP) { log('Agent cap reached; stopping further rounds.'); break }
}

const regressions = await regressionP

// ---------------------------------------------------------------------------
// Result
// ---------------------------------------------------------------------------

if (huntersOk === 0) {
  return {
    ok: false,
    error: 'No hunter completed. The read-only agent types (bug-hunter, bug-skeptic) may not be loaded yet; restart the Claude Code session so .claude/agents/ is picked up, then run again.',
    errors: errors.slice(0, 20),
  }
}

const bySev = (x, y) => sevRank(x.severity) - sevRank(y.severity) || String(x.file).localeCompare(String(y.file)) || (x.line || 0) - (y.line || 0)
confirmed.sort(bySev).forEach((b, i) => { b.id = `B${i + 1}` })
disputed.sort(bySev).forEach((b, i) => { b.id = `D${i + 1}` })
refuted.sort(bySev)

const count = arr => SEV.reduce((o, s) => ({ ...o, [s]: arr.filter(b => b.severity === s).length }), {})
const blocking = confirmed.filter(b => sevRank(b.severity) <= sevRank(threshold))
const openRegressions = regressions.filter(r => r.status === 'still-present' || r.status === 'partially-fixed')
const allFiles = A.files.map(f => normPath(f[0]))
const missing = allFiles.filter(f => !reviewed.has(f))
const coverageComplete = failedSlices.filter(s => s.round === 1).length === 0 && dropped.length === 0

return {
  ok: true,
  clean: blocking.length === 0 && openRegressions.length === 0 && coverageComplete,
  clean_threshold: threshold,
  tier: tierName,
  stats: {
    files: A.files.length,
    lines: totalLines,
    slices: chunks.length,
    slice_lines: chunkLines,
    cross_lenses: crossLenses,
    rounds_run: roundsRun,
    hunters_run: huntersRun,
    hunters_ok: huntersOk,
    skeptics_run: skepticsRun,
    agents_used: agentsUsed,
    candidates,
    duplicates_merged: duplicates,
    confirmed: confirmed.length,
    disputed: disputed.length,
    refuted: refuted.length,
    confirmed_by_severity: count(confirmed),
    blocking: blocking.length,
  },
  confirmed,
  disputed,
  refuted,
  regressions,
  coverage: {
    complete: coverageComplete,
    failed_slices: failedSlices,
    files_reported_not_reviewed: [...notReviewed],
    files_not_listed_as_reviewed: missing.length > 200 ? [...missing.slice(0, 200), `… and ${missing.length - 200} more`] : missing,
    dropped_agents: dropped,
    errors: errors.slice(0, 20),
  },
}
