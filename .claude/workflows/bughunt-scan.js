export const meta = {
  name: 'bughunt-scan',
  description: 'Read-only bug hunt: every checkpoint is a required pass on every code slice, independent skeptics try to refute each finding, coverage grid in the result',
  whenToUse: 'Launched by the /bughunt and /bugloop skills, which build the file list it needs. Read-only: never edits code.',
  phases: [
    { title: 'Hunt', detail: 'required checkpoint passes per code slice, plus whole-codebase checkpoints' },
    { title: 'Verify', detail: 'independent skeptics try to disprove each finding' },
    { title: 'Regression check', detail: 'did bugs fixed in the previous cycle stay fixed?' },
  ],
}

// ---------------------------------------------------------------------------
// Inputs (args):
//   root                 absolute path of the project (required)
//   files                [[relativePath, lineCount], ...] from scope.sh (required)
//   mode                 'auto' | 'lean' | 'small' | 'medium' | 'large' | 'max' (default 'auto')
//   focus                optional text: what the user wants extra attention on
//   app_context          optional 1-3 sentences on what the app does
//   powerapps            {detected: bool} from scope.sh
//   clean_threshold      lowest bug severity that blocks "clean" (default 'medium')
//   previous_bugs        [{id, title, file, line, description, fix_summary}] fixed last cycle
//   disable_checkpoints  checkpoint ids to skip for this run (they show as "off" in the grid)
//   max_agents           hard ceiling on agents for this run (default 900; runtime cap is 1000)
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
const isPowerAppsFile = p => /\.(pa|fx)\.yaml$/i.test(String(p))
const UI_EXT = /\.(html?|jsx|tsx|vue|svelte|astro|css|scss|sass|less|cshtml|razor|hbs|ejs|pug|xaml)$|\.(pa|fx)\.yaml$/i
const tagsOf = f => String(f[2] || '').split(',').filter(Boolean)
const isUiFile = (path, tags) => tags.includes('ui') || UI_EXT.test(String(path))

// ---------------------------------------------------------------------------
// Finding kinds. Only kinds listed in BLOCKING_KINDS can stop a run from being "clean".
// ---------------------------------------------------------------------------

const KINDS = ['bug', 'warning', 'code-health', 'accessibility', 'cosmetic']
const BLOCKING_KINDS = ['bug']
const KIND_PREFIX = { bug: 'B', warning: 'W', 'code-health': 'H', accessibility: 'A', cosmetic: 'V' }

// Fixed rules that override a finding's kind, applied by code (not by an agent's judgment).
const KIND_RULES = [
  {
    why: 'Performance findings are reported as warnings: reading code cannot measure real load',
    test: f => f.category === 'performance',
    kind: 'warning',
  },
  {
    why: 'Power Apps delegation limits are reported as warnings, never blockers',
    test: f => f.category === 'delegation' || (isPowerAppsFile(f.file) && /delegat/i.test(`${f.title} ${f.description}`)),
    kind: 'warning',
  },
]

// ---------------------------------------------------------------------------
// Shared prompt text
// ---------------------------------------------------------------------------

const SEVERITY_RUBRIC = `Severity rubric (use exactly these levels):
- critical: data loss or corruption, a security breach (auth bypass, injection, secret exposure), or a crash/total failure on a main path most users hit.
- high: a core feature gives wrong results or fails on a common path, with no reasonable workaround.
- medium: wrong behavior on a realistic edge case or error path (bad input, network failure, empty data, concurrency) that real users will eventually hit.
- low: minor or unlikely: cosmetic, rare edge case, small leak, misleading message.`

const WHAT_COUNTS = `What counts as a bug: code that, for some reachable input or state, gives a wrong result, crashes, hangs, leaks, loses or corrupts data, or opens a security hole. You must be able to name the triggering input/state and the wrong outcome.
Do NOT report: style, naming, formatting, missing comments or tests, refactoring ideas, hypothetical future misuse, missing features, or best-practice advice without a concrete failure (unless a checkpoint below explicitly asks for that kind of finding).`

const EVIDENCE_RULES = `For every finding give: the file path relative to the project root, the 1-based line of the faulty code, a short verbatim quote of that code (at most 6 lines, copied exactly from the file, no paraphrasing; a script checks it), the concrete trigger (input, state or sequence) and the wrong outcome, the checkpoint id it falls under, and evidence_type "code".
If you suspect a bug but cannot fully prove it, still report it with confidence "low": an independent skeptic checks every finding.`

const SELECTION_NOTE = 'Out of scope for security: users being able to see or switch to other selections (property, regional, region or any similar level). Switching freely between selections is intended in these apps. Whether a selection returns exactly the right items is a correctness question, not a security one.'

const POWERAPPS_CHECKLIST = `Power Apps source (Power Fx in .pa.yaml / .fx.yaml). Check in particular:
- Delegation: Filter/Search/LookUp/Sort/CountRows (and ClearCollect from a data source) using non-delegable functions or operators against SharePoint, Dataverse or SQL silently process only the first rows up to the app's data row limit (500 by default, 2000 max). Report these with category "delegation"; they are reported as warnings.
- Writes without error handling: Patch, SubmitForm, Remove and flow .Run() calls whose failures are not handled (IfError, Errors(), OnFailure), and navigation that happens before a submit has succeeded.
- ForAll evaluates records in no guaranteed order and possibly in parallel; Concurrent() runs its formulas in parallel. Flag logic that depends on ordering or on side effects between them.
- Variable scope: context variables (UpdateContext) are screen-local; global variables (Set) are global; reading the wrong one gives Blank. App.OnStart work that screens read before it finishes.
- Blank handling: LookUp/First returning Blank then dereferenced; IsBlank vs IsEmpty on tables; comparing to "" vs Blank().
- Types and data shapes: Choice/Lookup columns compared to text without .Value; Text vs Number comparisons; Value()/DateValue() locale issues; UTC vs local time zones.
- Security: permissions enforced only through Visible/DisplayMode (client-side only); case-sensitive User().Email comparisons.
- Environment coupling: hard-coded URLs, GUIDs, list names, emails or environment IDs that break when the app moves between environments.
- Controls: Gallery.Selected when nothing is selected; forms not Reset after submit; timers that repeat writes; names that collide with column names without disambiguation.`

// ---------------------------------------------------------------------------
// CHECKPOINT REGISTRY. Each entry is one self-contained layer.
//   id         stable id used in findings ("checkpoint") and in the coverage grid
//   name       human name for reports
//   scope      'slice' = checked on every code slice it applies to; 'cross' = checked once across the codebase;
//              'mapped' = one agent maps the targets (mapTask), then checker agents verify them in batches (checklist),
//              plus one agent for selection switching (switchTask)
//   pass       slice checkpoints with the same pass name are checked by the same agent (tiers may merge or split passes)
//   appliesTo  'all' | 'ui' (slices with screen code) | 'powerapps'
//   kind       kind of finding this checkpoint produces by default (see KINDS; only 'bug' can block "clean")
//   checklist  what the agent must check
//   verifyHint optional extra instruction for the skeptics
// To add a layer, add an entry here. To skip one for a run, pass its id in args.disable_checkpoints.
// ---------------------------------------------------------------------------

const CHECKPOINTS = [
  // --- Checked on every slice -------------------------------------------------
  {
    id: 'logic', name: 'Core logic and error handling', scope: 'slice', pass: 'correctness', appliesTo: 'all', kind: 'bug',
    checklist: `Logic errors and wrong conditions, off-by-one, null/undefined, wrong types or units, API misuse, broken state updates, async ordering.
Errors that are swallowed (caught and ignored, or only logged) and failures that still report success (returning true/"saved"/HTTP 200 or showing a success message after something failed).
Date and time bugs: time zones (UTC vs local), daylight saving, inclusive vs exclusive date ranges, off-by-one days, month/year boundaries, locale date formats.`,
  },
  {
    id: 'edge-cases', name: 'Edge cases and failure paths', scope: 'slice', pass: 'correctness', appliesTo: 'all', kind: 'bug',
    checklist: `Null, empty and unusual inputs: zero, negative numbers, very large numbers, empty strings and lists, very long strings, special characters (apostrophes as in O'Brien, quotes, emoji, accents, HTML or formula characters), missing or extra fields, malformed data.
Network/IO failures, timeouts and retries; partial failure and cleanup; resource leaks.
Concurrency: two users saving the same record at the same time (lost updates, last write silently wins, no version or concurrency check), double processing, ordering and re-entrancy.`,
  },
  {
    id: 'performance', name: 'Performance', scope: 'slice', pass: 'correctness', appliesTo: 'all', kind: 'warning',
    checklist: `N+1 patterns: a query, request or LookUp inside a loop or once per row (Power Apps: ForAll with LookUp/Patch per record). Unbounded queries (no paging or limit, selecting every column), loading whole tables at startup (App.OnStart), repeated identical requests with no caching. Heavy work on every render or re-render (expensive computation in render, effects with missing or wrong dependencies, new objects or functions passed as props on every render). Large libraries imported for a small use. Heavy synchronous work on the UI thread.
Use category "performance". These are reported as warnings: reading code cannot measure real load.`,
    verifyHint: 'Confirm the pattern is really there (for example, the call really runs once per item). Do not judge whether it is slow today.',
  },
  {
    id: 'security', name: 'Security and data integrity', scope: 'slice', pass: 'safety', appliesTo: 'all', kind: 'bug',
    checklist: `Injection (SQL, HTML, command, formula), XSS, authentication and authorization gaps, exposed secrets, keys, passwords or tokens, unsafe eval or deserialization, trusting client-side data, data loss or corruption, sensitive data in logs, resource leaks.\n${SELECTION_NOTE}`,
  },
  {
    id: 'contracts', name: 'Contracts and assumptions', scope: 'slice', pass: 'safety', appliesTo: 'all', kind: 'bug',
    checklist: 'How this code is called and what it calls: argument order, units, nullability, unhandled return values, error propagation, version or platform quirks, config and environment assumptions.',
  },
  {
    id: 'code-health', name: 'Code health', scope: 'slice', pass: 'safety', appliesTo: 'all', kind: 'code-health',
    checklist: `Dead code: functions, variables, exports, screens, controls or branches that are never used or can never run (search for references first; consider dynamic use, public APIs, and Power Apps controls referenced by name).
Duplicated logic: the same non-trivial logic or business rule implemented in two or more places that can drift apart (not trivial one-liners).
Hard-coded values that should be configuration: URLs, hostnames, IDs/GUIDs, email addresses, environment or tenant names, list/table names, business thresholds, prices or rates (secrets also go under security). Not loop counters, 0/1, obvious constants or test fixtures.
These are reported as code health and never block.`,
    verifyHint: 'Confirm by searching for references: is it really unused or unreachable, really duplicated, really a hard-coded value that varies by environment or business rule?',
  },
  // --- Checked on slices that contain screen code (tag "ui") --------------------
  {
    id: 'interaction', name: 'Interaction and response handling', scope: 'slice', pass: 'ui', appliesTo: 'ui', kind: 'bug',
    checklist: `Buttons and actions that do nothing (missing or broken handler). Double submission: a save or submit that can run twice (double-click, repeated Enter) because nothing blocks it while in progress, creating duplicates. Forms that lose the user's input after an error. Destructive actions (delete, remove, cancel, archive, overwrite) that happen without a confirmation step. Navigation: browser back button, page refresh mid-flow or deep links that break state or lose work. Expired sessions (401/403, token expiry) not handled: silent failure, endless spinner, lost data.
Every data call's handling on screen: success, error, empty result and slow or timed-out responses (a spinner that never ends, a blank screen on error, an error shown as success).`,
  },
  {
    id: 'ui-states', name: 'UI feedback and layout hints', scope: 'slice', pass: 'ui', appliesTo: 'ui', kind: 'cosmetic',
    checklist: `Missing loading indicators; missing empty states where a list or table can be empty; no success or failure message after an action; validation messages that do not say how to fix the problem; save buttons not disabled while saving.
Text likely to overflow or be cut off in fixed-size elements (pills, buttons, cards, table cells), e.g. a fixed width with white-space: nowrap and overflow hidden and no ellipsis or tooltip, or long names. Nested scroll containers (double scrollbars), fixed heights that cut content off, sticky headers that can cover rows, fixed pixel widths with no rules for phone or tablet widths.
Power Apps: fixed Width/Height on labels that hold long text, AutoHeight off, containers without responsive layout.
These are reported as cosmetic and never block. Static reading only flags likely problems; the /uxcheck browser run confirms them on screen.`,
    verifyHint: 'Confirm the state or style problem is really there (check for loading or empty handling in a parent component or shared wrapper before confirming).',
  },
  {
    id: 'accessibility', name: 'Accessibility (WCAG 2.2 AA)', scope: 'slice', pass: 'ui', appliesTo: 'ui', kind: 'accessibility',
    checklist: `Measured against WCAG 2.2 AA as a review standard: images without text alternatives; icon-only buttons and links without an accessible name (aria-label, title, visible text); form inputs without an associated label; click handlers on non-interactive elements (div, span) without role, tabindex and keyboard handling; focus indicators removed (outline: none or 0) with no visible replacement; positive tabindex or focus traps; color pairs defined in code with low contrast (normal text below 4.5:1, large text below 3:1) when both colors are visible in code; body text below about 12px; interactive targets smaller than 24x24 CSS pixels; information conveyed by color alone; missing page language or title.
Power Apps: empty AccessibleLabel on icons, images and buttons; TabIndex misuse; FocusedBorderThickness 0; status messages not announced (Live property).
These are reported as accessibility findings and never block. Never suggest adding accessibility tools, scripts or runtime checks to the app.`,
    verifyHint: 'Confirm against WCAG 2.2 AA, and check whether a name, label or focus style is provided some other way (aria-labelledby, visible text, a global stylesheet) before confirming.',
  },
  {
    id: 'powerapps', name: 'Power Apps (Power Fx)', scope: 'slice', pass: 'powerapps', appliesTo: 'powerapps', kind: 'bug',
    checklist: POWERAPPS_CHECKLIST,
  },
  // --- Checked once across the whole codebase ----------------------------------
  {
    id: 'x-integration', name: 'Cross-file contracts', scope: 'cross', appliesTo: 'all', kind: 'bug',
    checklist: 'Function signatures vs their callers, shared types and constants, event/message names, config keys and environment variables used vs defined.',
  },
  {
    id: 'x-data', name: 'Data and API contracts', scope: 'cross', appliesTo: 'all', kind: 'bug',
    checklist: `Front end to back end: every request the UI sends matches what the back end expects (field names, casing, types, required fields, date formats, enum values), and every response field the UI reads exists. API, flow or connector changes not reflected in callers (Power Automate flow inputs/outputs, custom connectors).
Validation: every rule enforced in a form (required, length, range, format, uniqueness, permissions) is also enforced on the server or in the data source; client-only validation can be bypassed.
Database / data source: fields used in filters, joins and lookups without indexes (category "performance"; reported as warnings); NOT NULL, UNIQUE, FOREIGN KEY or CHECK constraints the code relies on but the schema lacks; delete or update paths that leave orphaned child records (no cascade, no cleanup); schema or migrations that do not match the code's model; SharePoint/Dataverse columns the app writes that are missing, renamed or of another type.`,
  },
  {
    id: 'x-security', name: 'Cross-file security', scope: 'cross', appliesTo: 'all', kind: 'bug',
    checklist: `Secrets or tokens committed in code, injection, XSS, authentication and authorization gaps, insecure CORS/CSP, unsafe eval or deserialization, trusting client-side data, sensitive data in logs or storage.\n${SELECTION_NOTE}`,
  },
  {
    id: 'x-state', name: 'Shared state, lifecycle and async', scope: 'cross', appliesTo: 'all', kind: 'bug',
    checklist: 'Global or cached state that goes stale, initialization order, teardown and cleanup, races between concurrent operations, retries that duplicate side effects, unhandled promise rejections.',
  },
  {
    id: 'x-config', name: 'Build, configuration and deployment', scope: 'cross', appliesTo: 'all', kind: 'bug',
    checklist: 'Manifests (e.g. Office add-in manifest.xml), package scripts, environment variables, permissions declared vs used, version and platform compatibility assumptions, feature flags, production vs development settings.',
  },
  {
    id: 'x-powerapps', name: 'Power Apps, app-wide', scope: 'cross', appliesTo: 'powerapps', kind: 'bug',
    checklist: `App-level review across all screens and components.\n${POWERAPPS_CHECKLIST}`,
  },
  // --- Mapped: one agent maps the targets, then checker agents verify each batch ----
  {
    id: 'scoping', name: 'Selection scoping', scope: 'mapped', appliesTo: 'all', kind: 'bug', batchSize: 8,
    mapTask: `Map how this app scopes data by a user-chosen selection: an organizational level the user picks to decide which data the app shows, such as property, regional, region, site, portfolio, account or any similar level.
Find: (1) the selection levels and how each is identified; (2) where the hierarchy relationships live (which table, list, column, API or config says which properties belong to which regional or region); (3) where the current selection is stored (state, variables, URL, context, global variable, collection); (4) the handlers that run when the user switches selection; (5) EVERY consumer of the selection: each query, data call, screen, component, chart, total, export, cache or Power Fx formula whose results should depend on the current selection, with file and line.
If the app has no such selection concept, set found to false and say why.`,
    checklist: `For each consumer, check with the real code that it returns exactly the items the current selection should include, and nothing outside it:
- Leaks (too much shown): a missing filter, filtering on the wrong field or level, OR where AND is needed, a filter applied on only some code paths, defaulting to "all" when the selection is empty or loading.
- Gaps (items missing): the wrong relationship or join, only direct children instead of every property under a regional or region, hard-coded or stale lists of properties, inactive or renamed records dropped by accident, case or whitespace mismatches, pagination or row limits cutting results (Power Apps delegation limits: report with category "delegation"; they are reported as warnings).
- Filtering that only hides rows on screen after an unfiltered or capped fetch.
- Totals, counts, charts and exports that use a different scope than the list they summarize.
- Caches or state not keyed by the selection.
This is a correctness check, not a privacy one: users may switch selections freely by design. Rate severity by correctness impact: wrong or missing items on a main screen or in totals = high; on a secondary screen or an edge path = medium; labels only = low.`,
    switchTask: `Check what happens when the user switches selection: every query, screen, total, chart, filter, form, cached collection and variable must refresh to the new selection, with nothing carried over from the previous one. Look for state that is appended to instead of replaced, caches keyed without the selection, forms that keep the old selection's values, and slow responses for the old selection arriving after the new selection and overwriting it.`,
    verifyHint: 'Judge correctness only: switching between selections is intended. The question is whether the selected scope shows exactly the items it should.',
  },
]

// ---------------------------------------------------------------------------
// Tiers. slicePasses: 'all' = one agent checks every slice checkpoint; 'group' = one agent per pass group;
// 'each' = one agent per checkpoint. crossMerge: one agent covers all whole-codebase checkpoints.
// rounds: 1 required round, then extra "fresh eyes" sweeps while each sweep still confirms something new.
// ---------------------------------------------------------------------------

const TIERS = {
  lean:   { chunkLines: 4000, maxHunters: 8,  slicePasses: 'all',   crossMerge: true,  skeptics: () => 1, rounds: 1 },
  small:  { chunkLines: 1500, maxHunters: 6,  slicePasses: 'group', crossMerge: true,  skeptics: () => 1, rounds: 1 },
  medium: { chunkLines: 2500, maxHunters: 24, slicePasses: 'group', crossMerge: false, skeptics: s => (sevRank(s) <= 1 ? 3 : 1), rounds: 2 },
  large:  { chunkLines: 3000, maxHunters: 48, slicePasses: 'group', crossMerge: false, skeptics: () => 3, rounds: 3 },
  max:    { chunkLines: 1500, maxHunters: 80, slicePasses: 'each',  crossMerge: false, skeptics: s => (sevRank(s) <= 1 ? 5 : 3), rounds: 3 },
}

const totalLines = A.files.reduce((n, f) => n + (Number(f[1]) || 0), 0)
const requested = String(A.mode || 'auto').toLowerCase()
const tierName = requested !== 'auto' ? requested
  : totalLines < 3000 ? 'small' : totalLines < 30000 ? 'medium' : 'large'
const cfg = TIERS[tierName]
if (!cfg) return { ok: false, error: `Unknown mode "${A.mode}". Use auto, lean, small, medium, large or max.` }

const AGENT_CAP = Math.min(Number(A.max_agents) || 900, 990)
const powerapps = !!(A.powerapps && A.powerapps.detected) || A.files.some(f => isPowerAppsFile(f[0]))
const disabled = new Set(Array.isArray(A.disable_checkpoints) ? A.disable_checkpoints : [])
const enabledCps = CHECKPOINTS.filter(cp => !disabled.has(cp.id))
const cpById = Object.fromEntries(CHECKPOINTS.map(cp => [cp.id, cp]))

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

const CATEGORIES = ['logic', 'null-safety', 'error-handling', 'async-race', 'security', 'data-integrity', 'performance', 'resource-leak', 'api-contract', 'config', 'powerapps', 'delegation', 'other']

function huntSchema(ids) {
  return {
    type: 'object',
    properties: {
      bugs: {
        type: 'array',
        items: {
          type: 'object',
          properties: {
            title: { type: 'string' },
            file: { type: 'string' },
            line: { type: 'integer' },
            end_line: { type: 'integer' },
            severity: { type: 'string', enum: SEV },
            category: { type: 'string', enum: CATEGORIES },
            checkpoint: { type: 'string', enum: ids },
            evidence_type: { type: 'string', enum: ['code'] },
            description: { type: 'string' },
            trigger: { type: 'string' },
            evidence: { type: 'string' },
            confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
          },
          required: ['title', 'file', 'line', 'severity', 'category', 'checkpoint', 'evidence_type', 'description', 'trigger', 'evidence', 'confidence'],
        },
      },
      checkpoints: {
        type: 'array',
        items: {
          type: 'object',
          properties: {
            id: { type: 'string', enum: ids },
            status: { type: 'string', enum: ['checked', 'not-applicable'] },
            note: { type: 'string' },
          },
          required: ['id', 'status'],
        },
      },
      files_reviewed: { type: 'array', items: { type: 'string' } },
      files_not_reviewed: { type: 'array', items: { type: 'string' } },
      notes: { type: 'string' },
    },
    required: ['bugs', 'checkpoints', 'files_reviewed'],
  }
}

const MAP_SCHEMA = {
  type: 'object',
  properties: {
    found: { type: 'boolean' },
    reason: { type: 'string' },
    levels: { type: 'array', items: { type: 'object', properties: { name: { type: 'string' }, how_identified: { type: 'string' } }, required: ['name'] } },
    hierarchy: { type: 'array', items: { type: 'object', properties: { relationship: { type: 'string' }, where: { type: 'string' } }, required: ['relationship', 'where'] } },
    selection_state: { type: 'array', items: { type: 'object', properties: { where: { type: 'string' }, file: { type: 'string' }, line: { type: 'integer' } }, required: ['where'] } },
    change_handlers: { type: 'array', items: { type: 'object', properties: { description: { type: 'string' }, file: { type: 'string' }, line: { type: 'integer' } }, required: ['description', 'file'] } },
    consumers: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          kind: { type: 'string', enum: ['query', 'screen', 'component', 'chart', 'total', 'export', 'cache', 'api', 'formula', 'other'] },
          file: { type: 'string' },
          line: { type: 'integer' },
          description: { type: 'string' },
          expected_scope: { type: 'string' },
        },
        required: ['kind', 'file', 'line', 'description'],
      },
    },
  },
  required: ['found', 'reason', 'consumers'],
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
const clip = (s, n) => { s = String(s || ''); return s.length > n ? s.slice(0, n) + '…' : s }

function makeChunks(files, target) {
  const sorted = files.map(f => [normPath(f[0]), Math.max(1, Number(f[1]) || 1), tagsOf(f)])
    .sort((a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0))
  const chunks = []
  let cur = null
  const flush = () => { if (cur && cur.parts.length) chunks.push(cur); cur = null }
  for (const [path, n, tags] of sorted) {
    if (n > target * 1.5) {
      // One big file: split it into line ranges, one slice each.
      flush()
      const pieces = Math.ceil(n / target)
      const step = Math.ceil(n / pieces)
      for (let s = 1; s <= n; s += step) {
        const to = Math.min(n, s + step - 1)
        chunks.push({ parts: [{ path, from: s, to, total: n, tags }], lines: to - s + 1 })
      }
      continue
    }
    // Keep a directory together; start a new slice when full, or when the directory changes and the slice is mostly full.
    if (cur && (cur.lines + n > target || (dirOf(cur.parts[cur.parts.length - 1].path) !== dirOf(path) && cur.lines >= target * 0.6))) flush()
    if (!cur) cur = { parts: [], lines: 0 }
    cur.parts.push({ path, from: 1, to: n, total: n, tags })
    cur.lines += n
  }
  flush()
  return chunks.map((c, i) => ({
    ...c,
    id: `S${i + 1}`,
    powerapps: c.parts.some(p => isPowerAppsFile(p.path)),
    ui: c.parts.some(p => isUiFile(p.path, p.tags)),
  }))
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

const appliesToSlice = (cp, chunk) => cp.appliesTo === 'all' || (cp.appliesTo === 'powerapps' && chunk.powerapps) || (cp.appliesTo === 'ui' && chunk.ui)
const appliesToApp = cp => cp.appliesTo === 'all' || (cp.appliesTo === 'powerapps' && powerapps)

function groupPasses(cps, mode) {
  if (!cps.length) return []
  if (mode === 'all') return [{ name: 'all', cps }]
  if (mode === 'each') return cps.map(cp => ({ name: cp.id, cps: [cp] }))
  const by = {}
  for (const cp of cps) (by[cp.pass] = by[cp.pass] || []).push(cp)
  return Object.entries(by).map(([name, list]) => ({ name, cps: list }))
}

function kindOf(f) {
  for (const rule of KIND_RULES) if (rule.test(f)) return rule.kind
  const cp = cpById[f.checkpoint]
  return cp && KINDS.includes(cp.kind) ? cp.kind : 'bug'
}

const fmtBug = b => [
  `Title: ${b.title}`,
  `Location: ${normPath(b.file)}:${b.line}${b.end_line ? `-${b.end_line}` : ''}`,
  `Checkpoint: ${(cpById[b.checkpoint] || {}).name || b.checkpoint} | reported as: ${b.kind}`,
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

async function runHunter(prompt, label, schema) {
  let r = await spawn(prompt, { label, phase: 'Hunt', schema, agentType: 'bug-hunter' })
  if (!r) {
    log(`${label} returned nothing; retrying once`)
    r = await spawn(prompt, { label: `${label} retry`, phase: 'Hunt', schema, agentType: 'bug-hunter' })
  }
  return r
}

// ---------------------------------------------------------------------------
// Prompts
// ---------------------------------------------------------------------------

function checkpointBlock(cps) {
  return [
    `Checkpoints for this pass. Check EVERY one of them against everything you were assigned; none is optional:\n\n${cps.map(cp => `[${cp.id}] ${cp.name} (findings reported as: ${cp.kind})\n${cp.checklist}`).join('\n\n')}`,
    `For each finding, set "checkpoint" to the id it falls under; the checkpoint decides how the finding is classified, so report a real bug (wrong result, crash, data loss) under a checkpoint reported as "bug" when your pass has one. When you finish, list every checkpoint id above under "checkpoints" with status "checked" (you went through all your code for it) or "not-applicable" (nothing in your code it could apply to; say why in note).`,
  ].join('\n\n')
}

function slicePrompt(chunk, pass, round, known) {
  const fileList = chunk.parts.map(p => (p.from === 1 && p.to === p.total)
    ? `- ${p.path} (${p.total} lines)`
    : `- ${p.path} lines ${p.from}-${p.to} of ${p.total} (read nearby code as needed for context)`).join('\n')
  return [
    `You are hunting bugs in one slice of the codebase at ${A.root}. You are read-only.`,
    A.app_context ? `About the app: ${A.app_context}` : '',
    `Your slice ${chunk.id} (${chunk.lines} lines). Read ALL of it, top to bottom:\n${fileList}`,
    `Paths are relative to ${A.root}. You may open any other file to check callers, definitions or contracts, but report only findings whose faulty code is inside your slice.`,
    round > 1 ? 'This is an extra sweep with fresh eyes over the same checkpoints. Earlier hunters already covered this slice; look for what they missed.' : '',
    known.length ? `Already reported for this slice (do NOT report these again; look for different ones):\n${known.map(k => `- ${normPath(k.file)}:${k.line} ${k.title}`).join('\n')}` : '',
    checkpointBlock(pass.cps),
    A.focus ? `The user asked for extra attention on: ${A.focus}` : '',
    WHAT_COUNTS,
    SEVERITY_RUBRIC,
    EVIDENCE_RULES,
    'There is no quota and no reward for finishing early. When you think you are done, go through each file once more for every checkpoint. Then report every finding you can substantiate, and list the files you fully reviewed and any you could not.',
  ].filter(Boolean).join('\n\n')
}

const dataFiles = A.files.filter(f => tagsOf(f).includes('data')).map(f => normPath(f[0]))

const fileMap = (() => {
  const all = A.files.map(f => `${normPath(f[0])} (${f[1]})`)
  if (all.length <= 1500) return all.join('\n')
  log(`File map for whole-codebase hunters truncated to 1500 of ${all.length} paths; they can still Glob/Grep the rest.`)
  return all.slice(0, 1500).join('\n') + `\n… and ${all.length - 1500} more (use Glob/Grep)`
})()

function crossPrompt(pass) {
  return [
    `You are a whole-codebase bug hunter for the codebase at ${A.root}. You are read-only. Other hunters review individual slices; your job is bugs that only show up ACROSS files.`,
    A.app_context ? `About the app: ${A.app_context}` : '',
    checkpointBlock(pass.cps),
    'Use Grep and Glob to trace the relevant connections, then Read the code involved. Report findings anywhere in the codebase that fall under your checkpoints.',
    pass.cps.some(cp => cp.id === 'x-data') && dataFiles.length ? `Database and schema files found by the scope scan:\n${dataFiles.slice(0, 200).join('\n')}` : '',
    `Files in scope (path and line count):\n${fileMap}`,
    A.focus ? `The user asked for extra attention on: ${A.focus}` : '',
    WHAT_COUNTS,
    SEVERITY_RUBRIC,
    EVIDENCE_RULES,
    'There is no quota and no reward for finishing early. Report every finding you can substantiate under your checkpoints.',
  ].filter(Boolean).join('\n\n')
}

const fmtMap = map => [
  `Selection levels: ${(map.levels || []).map(l => `${l.name}${l.how_identified ? ` (${l.how_identified})` : ''}`).join('; ') || 'not stated'}`,
  `Hierarchy relationships: ${(map.hierarchy || []).map(h => `${h.relationship} [${h.where}]`).join('; ') || 'not stated'}`,
  `Where the current selection is stored: ${(map.selection_state || []).map(x => `${x.where}${x.file ? ` (${normPath(x.file)}${x.line ? `:${x.line}` : ''})` : ''}`).join('; ') || 'not stated'}`,
  `Selection change handlers: ${(map.change_handlers || []).map(x => `${x.description} (${normPath(x.file)}${x.line ? `:${x.line}` : ''})`).join('; ') || 'none found'}`,
].join('\n')
const fmtConsumer = c => `- [${c.kind}] ${normPath(c.file)}:${c.line} ${c.description}${c.expected_scope ? ` (should include: ${c.expected_scope})` : ''}`

function mapPrompt(cp) {
  return [
    `You are mapping part of the codebase at ${A.root} so that other agents can check it. You are read-only.`,
    A.app_context ? `About the app: ${A.app_context}` : '',
    cp.mapTask,
    'Search widely with Grep and Glob (for the app\'s own names for these levels and for words like selected, selection, filter, scope), then Read the code. Give file paths relative to the project root and 1-based lines. Completeness matters more than speed: a consumer you miss is a consumer nobody checks.',
    `Files in scope (path and line count):\n${fileMap}`,
  ].filter(Boolean).join('\n\n')
}

function mappedCheckPrompt(cp, map, batch, i, n) {
  return [
    `You are checking "${cp.name}" in the codebase at ${A.root}. You are read-only.`,
    A.app_context ? `About the app: ${A.app_context}` : '',
    `The map produced by a mapping agent:\n${fmtMap(map)}`,
    `Your consumers to check (batch ${i + 1} of ${n}). Check EVERY one; open the code around each:\n${batch.map(fmtConsumer).join('\n')}`,
    cp.checklist,
    `Report each finding with checkpoint "${cp.id}". When you finish, sign off "${cp.id}" under "checkpoints" as "checked".`,
    WHAT_COUNTS,
    SEVERITY_RUBRIC,
    EVIDENCE_RULES,
  ].filter(Boolean).join('\n\n')
}

function mappedSwitchPrompt(cp, map) {
  const consumers = (map.consumers || []).slice(0, 300)
  return [
    `You are checking "${cp.name}" in the codebase at ${A.root}. You are read-only.`,
    A.app_context ? `About the app: ${A.app_context}` : '',
    `The map produced by a mapping agent:\n${fmtMap(map)}`,
    `Everything that depends on the selection (${(map.consumers || []).length} items${consumers.length < (map.consumers || []).length ? ', first 300 shown' : ''}):\n${consumers.map(fmtConsumer).join('\n')}`,
    cp.switchTask,
    `Report each finding with checkpoint "${cp.id}". When you finish, sign off "${cp.id}" under "checkpoints" as "checked".`,
    WHAT_COUNTS,
    SEVERITY_RUBRIC,
    EVIDENCE_RULES,
  ].filter(Boolean).join('\n\n')
}

function skepticPrompt(b, k, n) {
  return [
    `An independent hunter claims there is a problem in the codebase at ${A.root}. You did not write this claim and have no reason to defend it. Try to prove it WRONG by reading the actual code.`,
    A.app_context ? `About the app: ${A.app_context}` : '',
    `The claim:\n${fmtBug(b)}`,
    b.kind === 'bug'
      ? 'Check, with the code in front of you: (1) does the quoted code exist at that location (or nearby)? (2) is the trigger reachable? Trace real callers and inputs. (3) is it already guarded elsewhere (caller validation, framework behavior, types, an upstream try/catch)? (4) is the "wrong outcome" actually wrong, or intended or harmless? (5) is the severity right?'
      : `This is reported as a ${b.kind}, not a bug. Check, with the code in front of you: (1) does the quoted code exist at that location (or nearby)? (2) is the described pattern really present and accurately described? (3) is the severity right for its potential impact?`,
    b.checkpoint && /security/.test(b.checkpoint) ? SELECTION_NOTE : '',
    cpById[b.checkpoint] && cpById[b.checkpoint].verifyHint ? cpById[b.checkpoint].verifyHint : '',
    n > 1 ? `You are skeptic ${k + 1} of ${n} and work independently. ${SKEPTIC_LENSES[k % SKEPTIC_LENSES.length]}` : '',
    'Verdict: "refuted" if any check shows the claim is not real as described; "confirmed" only if you can point to code proving it; "uncertain" if the code does not let you decide. Truth matters more than winning: do not refute a claim that is clearly real. Also give the severity you believe is correct.',
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
  const n = b.kind === 'bug' ? cfg.skeptics(b.severity) : 1
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
    kind: b.kind,
    checkpoint: b.checkpoint,
    checkpoint_name: (cpById[b.checkpoint] || {}).name || b.checkpoint,
    evidence_type: b.evidence_type || 'code',
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
  else if (t.status === 'refuted') refuted.push({ title: rec.title, kind: rec.kind, checkpoint: rec.checkpoint, file: rec.file, line: rec.line, severity: b.severity, found_by: b.found_by, reason: clip(t.reasons.find(x => x.startsWith('refuted')) || t.reasons[0], 400) })
  else disputed.push(rec)
  return t.status
}

// ---------------------------------------------------------------------------
// Plan the slices and the required passes
// ---------------------------------------------------------------------------

let chunkLines = cfg.chunkLines
let chunks = makeChunks(A.files, chunkLines)
while (chunks.length > cfg.maxHunters) {
  chunkLines = Math.ceil(chunkLines * 1.25)
  chunks = makeChunks(A.files, chunkLines)
}
if (chunkLines !== cfg.chunkLines) {
  log(`Slice size raised from ${cfg.chunkLines} to ~${chunkLines} lines so ${chunks.length} slices (cap ${cfg.maxHunters}) cover every file.`)
  if (chunkLines > 8000) log('Warning: slices above ~8000 lines are too big for one agent to read closely. Consider --mode max or hunting one sub-folder at a time.')
}

const sliceCps = enabledCps.filter(cp => cp.scope === 'slice')
const crossCps = enabledCps.filter(cp => cp.scope === 'cross' && appliesToApp(cp))
const passesFor = chunk => groupPasses(sliceCps.filter(cp => appliesToSlice(cp, chunk)), cfg.slicePasses)
const crossPasses = cfg.crossMerge ? groupPasses(crossCps, 'all') : groupPasses(crossCps, 'each')
const mappedCps = enabledCps.filter(cp => cp.scope === 'mapped' && appliesToApp(cp))
const MAX_MAPPED_BATCHES = 30
const requiredSlicePasses = chunks.reduce((n, c) => n + passesFor(c).length, 0)
if (disabled.size) log(`Checkpoints turned off for this run: ${[...disabled].join(', ')}.`)
log(`Tier "${tierName}": ${A.files.length} files, ${totalLines} lines -> ${chunks.length} slices, ${requiredSlicePasses} required slice passes + ${crossPasses.length} whole-codebase pass(es) + ${mappedCps.length} mapped check(s); up to ${cfg.rounds - 1} extra sweep(s).`)

// Coverage grid: one row per slice, one column per slice checkpoint; plus one status per whole-codebase checkpoint.
const grid = chunks.map(c => ({
  row: c.id,
  files: c.parts.map(p => (p.from === 1 && p.to === p.total ? p.path : `${p.path}:${p.from}-${p.to}`)),
  cells: Object.fromEntries(CHECKPOINTS.filter(cp => cp.scope === 'slice').map(cp => [cp.id,
    disabled.has(cp.id) ? 'off' : appliesToSlice(cp, c) ? 'pending' : 'n/a'])),
  notes: {},
}))
const gridRow = Object.fromEntries(grid.map(g => [g.row, g]))
const crossStatus = Object.fromEntries(CHECKPOINTS.filter(cp => cp.scope !== 'slice').map(cp => [cp.id, {
  status: disabled.has(cp.id) ? 'off' : appliesToApp(cp) ? 'pending' : 'n/a',
  note: '',
}]))

function recordAttestation(task, attested, forceStatus) {
  for (const cp of task.pass.cps) {
    const a = attested ? attested.get(cp.id) : null
    const status = forceStatus || (!attested ? 'failed' : !a ? 'unattested' : a.status === 'checked' ? 'checked' : 'n/a')
    if (task.kind === 'slice') {
      gridRow[task.chunk.id].cells[cp.id] = status
      if (a && a.note) gridRow[task.chunk.id].notes[cp.id] = clip(a.note, 200)
    } else {
      crossStatus[cp.id] = { status, note: a && a.note ? clip(a.note, 200) : '' }
    }
  }
}

// Regression checks for bugs fixed in the previous cycle run alongside the hunt.
const previous = Array.isArray(A.previous_bugs) ? A.previous_bugs : []
const regressionP = parallel(previous.map(pb => () =>
  spawn(regressionPrompt(pb), { label: `recheck ${pb.id}`, phase: 'Regression check', schema: REGRESSION_SCHEMA, agentType: 'bug-skeptic' })
    .then(v => ({ id: pb.id, title: pb.title, file: normPath(pb.file), ...(v || { status: 'unknown', evidence: 'checker did not complete' }) }))))

// ---------------------------------------------------------------------------
// Hunt: round 1 = every required pass; later rounds = extra sweeps while they still confirm something new
// ---------------------------------------------------------------------------

const reviewed = new Set()
const notReviewed = new Set()
const failedPasses = []
let huntersRun = 0
let huntersOk = 0
let candidates = 0
let duplicates = 0
let roundsRun = 0

async function runPass(t, round) {
  const ids = t.pass.cps.map(cp => cp.id)
  const where = t.kind === 'slice'
    ? `${t.chunk.id}${round > 1 ? ` r${round}` : ''} ${clip(t.chunk.parts[0].path, 40)}${t.chunk.parts.length > 1 ? ` +${t.chunk.parts.length - 1}` : ''}`
    : 'whole-codebase'
  const label = `hunt ${where} [${t.pass.name}]`
  const prompt = p => (t.kind === 'slice' ? slicePrompt(t.chunk, p, round, seen.filter(b => inChunk(b, t.chunk))) : crossPrompt(p))
  huntersRun++
  const res = await runHunter(prompt(t.pass), label, huntSchema(ids))
  if (!res) return { t, res: null, attested: null }
  const attested = new Map((res.checkpoints || []).filter(c => ids.includes(c.id)).map(c => [c.id, c]))
  const missing = t.pass.cps.filter(cp => !attested.has(cp.id))
  if (missing.length && round === 1) {
    // A required checkpoint was not signed off: send a follow-up agent for just those checkpoints.
    log(`${label} did not sign off ${missing.map(cp => cp.id).join(', ')}; sending a follow-up pass`)
    const sub = { name: `${t.pass.name}-recheck`, cps: missing }
    huntersRun++
    const more = await runHunter(prompt(sub), `${label} recheck`, huntSchema(missing.map(cp => cp.id)))
    if (more) {
      res.bugs = [...(res.bugs || []), ...(more.bugs || [])]
      res.files_reviewed = [...(res.files_reviewed || []), ...(more.files_reviewed || [])]
      for (const c of more.checkpoints || []) if (missing.some(cp => cp.id === c.id)) attested.set(c.id, c)
    }
  }
  return { t, res, attested }
}

// Mapped checkpoint: one agent maps the targets, then checker agents verify them in batches, plus a switching check.
const maps = {}
async function runMapped(t) {
  const cp = t.cp
  const ids = [cp.id]
  huntersRun++
  const map = await runHunter(mapPrompt(cp), `map ${cp.id}`, MAP_SCHEMA)
  if (!map) return { t, res: null, attested: null }
  const consumers = Array.isArray(map.consumers) ? map.consumers : []
  maps[cp.id] = {
    found: !!map.found,
    reason: map.reason,
    levels: map.levels || [],
    hierarchy: map.hierarchy || [],
    selection_state: map.selection_state || [],
    change_handlers: map.change_handlers || [],
    consumers: consumers.length,
    consumer_list: consumers.slice(0, 200).map(c => ({ kind: c.kind, file: normPath(c.file), line: c.line, description: clip(c.description, 160) })),
  }
  if (!map.found || !consumers.length) {
    return { t, res: { bugs: [], files_reviewed: [] }, attested: new Map([[cp.id, { id: cp.id, status: 'not-applicable', note: clip(map.reason || 'nothing to check was found', 200) }]]) }
  }
  let size = cp.batchSize || 8
  while (Math.ceil(consumers.length / size) > MAX_MAPPED_BATCHES) size++
  const batches = []
  for (let i = 0; i < consumers.length; i += size) batches.push(consumers.slice(i, i + size))
  maps[cp.id].batches = batches.length
  const jobs = batches.map((b, i) => () => {
    huntersRun++
    return runHunter(mappedCheckPrompt(cp, map, b, i, batches.length), `check ${cp.id} ${i + 1}/${batches.length}`, huntSchema(ids))
  })
  if (cp.switchTask) jobs.push(() => { huntersRun++; return runHunter(mappedSwitchPrompt(cp, map), `check ${cp.id} switching`, huntSchema(ids)) })
  const results = await parallel(jobs)
  const done = results.filter(Boolean)
  const res = { bugs: done.flatMap(r => r.bugs || []), files_reviewed: done.flatMap(r => r.files_reviewed || []), files_not_reviewed: done.flatMap(r => r.files_not_reviewed || []) }
  if (done.length < results.length) return { t, res, attested: new Map(), forceStatus: 'failed' }
  const signed = done.every(r => (r.checkpoints || []).some(c => c.id === cp.id && c.status === 'checked'))
  return { t, res, attested: signed ? new Map([[cp.id, { id: cp.id, status: 'checked', note: `${consumers.length} consumers in ${batches.length} batch(es)` }]]) : new Map() }
}

phase('Hunt')
for (let round = 1; round <= cfg.rounds; round++) {
  roundsRun = round
  let freshConfirmed = 0
  const tasks = []
  for (const chunk of chunks) for (const pass of passesFor(chunk)) tasks.push({ kind: 'slice', chunk, pass })
  if (round === 1) for (const pass of crossPasses) tasks.push({ kind: 'cross', pass })
  if (round === 1) for (const cp of mappedCps) tasks.push({ kind: 'mapped', cp, pass: { name: cp.id, cps: [cp] } })

  await pipeline(tasks,
    async (t) => (t.kind === 'mapped' ? runMapped(t) : runPass(t, round)),
    async ({ t, res, attested, forceStatus }) => {
      const where = t.kind === 'slice' ? t.chunk.id : t.kind === 'mapped' ? 'mapped' : 'whole-codebase'
      if (round === 1) recordAttestation(t, res ? attested : null, forceStatus)
      if (forceStatus === 'failed') failedPasses.push({ id: where, pass: t.pass.name, round, files: [] })
      if (!res) {
        failedPasses.push({ id: where, pass: t.pass.name, round, files: t.kind === 'slice' ? t.chunk.parts.map(p => p.path) : [] })
        return []
      }
      huntersOk++
      for (const f of res.files_reviewed || []) reviewed.add(normPath(f))
      for (const f of res.files_not_reviewed || []) notReviewed.add(normPath(f))
      const finder = `${where}:${t.pass.name}${round > 1 ? `/r${round}` : ''}`
      const allowed = t.pass.cps.map(cp => cp.id)
      const fresh = []
      for (const b of res.bugs || []) {
        candidates++
        const dup = seen.find(s => similar(s, b))
        if (dup) { duplicates++; dup.also_found_by = [...(dup.also_found_by || []), finder]; continue }
        const rec = {
          ...b,
          file: normPath(b.file),
          checkpoint: allowed.includes(b.checkpoint) ? b.checkpoint : allowed[0],
          evidence_type: 'code',
          found_by: finder,
        }
        rec.kind = kindOf(rec)
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
  if (agentsUsed >= AGENT_CAP) { log('Agent cap reached; stopping further sweeps.'); break }
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

for (const g of grid) for (const id of Object.keys(g.cells)) if (g.cells[id] === 'pending') g.cells[id] = 'failed'
for (const id of Object.keys(crossStatus)) if (crossStatus[id].status === 'pending') crossStatus[id].status = 'failed'

const bySev = (x, y) => sevRank(x.severity) - sevRank(y.severity) || String(x.file).localeCompare(String(y.file)) || (x.line || 0) - (y.line || 0)
const byKindThenSev = (x, y) => KINDS.indexOf(x.kind) - KINDS.indexOf(y.kind) || bySev(x, y)
for (const kind of KINDS) confirmed.filter(b => b.kind === kind).sort(bySev).forEach((b, i) => { b.id = `${KIND_PREFIX[kind]}${i + 1}` })
confirmed.sort(byKindThenSev)
disputed.sort(byKindThenSev).forEach((b, i) => { b.id = `D${i + 1}` })
refuted.sort(bySev)
for (const b of [...confirmed, ...disputed]) b.blocks = BLOCKING_KINDS.includes(b.kind) && sevRank(b.severity) <= sevRank(threshold)

const countBy = (arr, key, values) => values.reduce((o, v) => ({ ...o, [v]: arr.filter(b => b[key] === v).length }), {})
const blocking = confirmed.filter(b => b.blocks)
const openRegressions = regressions.filter(r => r.status === 'still-present' || r.status === 'partially-fixed')
const gapCells = grid.flatMap(g => Object.entries(g.cells).filter(([, s]) => s === 'failed' || s === 'unattested').map(([id, s]) => `${g.row}/${id}: ${s}`))
const gapCross = Object.entries(crossStatus).filter(([, v]) => v.status === 'failed' || v.status === 'unattested').map(([id, v]) => `${id}: ${v.status}`)
const coverageComplete = gapCells.length === 0 && gapCross.length === 0 && dropped.length === 0
const allFiles = A.files.map(f => normPath(f[0]))
const missing = allFiles.filter(f => !reviewed.has(f))
const summary = Object.fromEntries(CHECKPOINTS.map(cp => {
  if (cp.scope !== 'slice') return [cp.id, { status: crossStatus[cp.id].status }]
  const cells = grid.map(g => g.cells[cp.id])
  return [cp.id, ['checked', 'n/a', 'failed', 'unattested', 'off'].reduce((o, s) => ({ ...o, [s]: cells.filter(c => c === s).length }), {})]
}))

return {
  ok: true,
  root: A.root,
  clean: blocking.length === 0 && openRegressions.length === 0 && coverageComplete,
  clean_threshold: threshold,
  blocking_kinds: BLOCKING_KINDS,
  tier: tierName,
  stats: {
    files: A.files.length,
    lines: totalLines,
    slices: chunks.length,
    slice_lines: chunkLines,
    required_slice_passes: requiredSlicePasses,
    whole_codebase_passes: crossPasses.length,
    mapped_checks: mappedCps.length,
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
    confirmed_by_kind: countBy(confirmed, 'kind', KINDS),
    bugs_by_severity: countBy(confirmed.filter(b => b.kind === 'bug'), 'severity', SEV),
    confirmed_by_checkpoint: countBy(confirmed, 'checkpoint', CHECKPOINTS.map(cp => cp.id)),
    blocking: blocking.length,
  },
  confirmed,
  disputed,
  refuted,
  regressions,
  coverage: {
    complete: coverageComplete,
    checkpoints: CHECKPOINTS.map(cp => ({ id: cp.id, name: cp.name, scope: cp.scope, kind: cp.kind, enabled: !disabled.has(cp.id) })),
    grid,
    whole_codebase: crossStatus,
    summary,
    gaps: [...gapCells, ...gapCross],
    failed_passes: failedPasses,
    files_reported_not_reviewed: [...notReviewed],
    files_not_listed_as_reviewed: missing.length > 200 ? [...missing.slice(0, 200), `… and ${missing.length - 200} more`] : missing,
    dropped_agents: dropped,
    errors: errors.slice(0, 20),
  },
  maps,
  kind_rules: KIND_RULES.map(r => r.why),
}
