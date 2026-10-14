export const meta = {
  name: 'uxcheck-run',
  description: 'Runtime check of a running app in a real browser: side-effect scan, sign-in and test-property selection, screen-by-screen testing, independent replays',
  whenToUse: 'Launched by the /uxcheck skill, which supplies the app URL and settings. Never edits code; enters only marked test data in the test property.',
  phases: [
    { title: 'Side effects', detail: 'read-only code scan for emails, notifications, flows and record changes' },
    { title: 'Preflight', detail: 'open the app, sign in, select the test property, list screens' },
    { title: 'Test', detail: 'one browser agent per screen, one at a time (single shared browser)' },
    { title: 'Replay', detail: 'independent agents reproduce each finding from a fresh page load' },
  ],
}

// ---------------------------------------------------------------------------
// Inputs (args):
//   root                         absolute path of the project (required)
//   run_dir                      run directory relative to root, e.g. ".bughunt/runs/20261014-1600-ux" (required)
//   base_url                     where the running app is reachable (required)
//   app_context                  1-3 sentences on what the app does
//   login                        {required, user_secret, password_secret, notes}; secrets are env var NAMES
//   test_selection               option to select whenever a property selection exists (default "ZZ-test")
//   viewports                    [{name, width, height}] (default phone, tablet, desktop, zoom-200)
//   screens                      optional hints [{name, how_to_reach}]
//   files                        optional [[path, lines, tags]] from scope.sh, to help the side-effect scan
//   max_screens                  default 20
//   max_replays                  default 60
//   allow_external_side_effects  default false: actions that email/notify/text/pay/post are never clicked
//   previous_findings            runtime findings fixed last cycle: [{id, title, screen, steps, viewport, expected, actual}]
//   clean_threshold              lowest bug severity that blocks "clean" (default "medium")
//   disable_checkpoints          ids to skip: ux-visual, ux-interaction, ux-accessibility, ux-scoping
// ---------------------------------------------------------------------------

const A = args || {}
if (!A.root || !A.run_dir || !A.base_url) {
  return { ok: false, error: 'uxcheck-run needs args {root, run_dir, base_url}. Run it through the /uxcheck skill.' }
}

const SEV = ['critical', 'high', 'medium', 'low']
const sevRank = s => { const i = SEV.indexOf(s); return i < 0 ? 3 : i }
const threshold = SEV.includes(A.clean_threshold) ? A.clean_threshold : 'medium'
const KINDS = ['bug', 'warning', 'code-health', 'accessibility', 'cosmetic']
const BLOCKING_KINDS = ['bug']
const KIND_PREFIX = { bug: 'UB', warning: 'UW', 'code-health': 'UH', accessibility: 'UA', cosmetic: 'UV' }
const KIND_RULES = [
  { why: 'Slow pages and other performance observations are warnings', test: f => f.category === 'performance', kind: 'warning' },
]
const TEST = A.test_selection || 'ZZ-test'
const VIEWPORTS = Array.isArray(A.viewports) && A.viewports.length ? A.viewports : [
  { name: 'phone', width: 375, height: 812 },
  { name: 'tablet', width: 768, height: 1024 },
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'zoom-200', width: 720, height: 900 },
]
const MAX_SCREENS = Number(A.max_screens) || 20
const MAX_REPLAYS = Number(A.max_replays) || 60
const disabled = new Set(Array.isArray(A.disable_checkpoints) ? A.disable_checkpoints : [])
const clip = (s, n) => { s = String(s || ''); return s.length > n ? s.slice(0, n) + '…' : s }
const slug = s => String(s || 'screen').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 30) || 'screen'
const evidence = name => `${A.run_dir}/ux-evidence/${name}`

// ---------------------------------------------------------------------------
// Runtime checkpoints (same idea as the static registry: one self-contained entry per layer)
// ---------------------------------------------------------------------------

const CHECKS = [
  {
    id: 'ux-visual', name: 'Visual and layout', kind: 'cosmetic',
    checklist: `At EVERY viewport size listed: text overflowing or cut off in pills, buttons, cards, table cells and headers (compare text length with the [box=x,y,width,height] sizes in snapshots, and look at screenshots); long names; double scrollbars, content cut off, sticky headers covering rows; horizontal scrolling at phone width; layout breaking at the zoom size (zoom is simulated by a narrower window, the standard WCAG reflow method); empty and loading states that look broken or are missing.`,
  },
  {
    id: 'ux-interaction', name: 'Functional and interaction', kind: 'bug',
    checklist: `Every button and link does something and gives feedback (spinner, message, disabled while saving). Double-click save/submit buttons (doubleClick) and check for duplicates. Submit forms with invalid input (empty required fields, too-long text, special characters like O'Brien): is the input kept and is the fix explained? Use the browser back button and refresh the page in the middle of a flow: is work lost or the screen broken? Destructive actions (delete, remove, archive) must ask for confirmation: open it, then cancel. Watch for console errors (browser_console_messages) and failed requests (browser_network_requests, 4xx/5xx) during normal use; a request that fails while the screen shows success is a bug.`,
  },
  {
    id: 'ux-accessibility', name: 'Accessibility (WCAG 2.2 AA review)', kind: 'accessibility',
    checklist: `Keyboard only: press Tab through the screen; every interactive element must be reachable in a sensible order with a visible focus indicator (take a screenshot while an element is focused), no keyboard traps, Enter/Space activate buttons. Labels: in the snapshot, every icon button, image and input must have a meaningful accessible name. Tap targets at phone width: interactive elements at least 24x24 CSS pixels (use [box=...]). Color contrast and text size: judge from screenshots and report only clear problems, noting that contrast judged from a screenshot is approximate. Never inject scripts or tools into the page to measure anything.`,
  },
]
const SWITCH = {
  id: 'ux-scoping', name: 'Selection switching', kind: 'bug',
  checklist: `With "${TEST}" selected, note what the main screens show (lists, totals, charts, filters). Switch to a different option at the same level, then back to "${TEST}". Under other selections LOOK ONLY: change nothing. After each switch, everything (lists, totals, charts, filters, open forms) must refresh to the new selection with nothing left over from the previous one, and switching back must show the same data as before. Rate as correctness, not privacy: switching is allowed by design.`,
}
const ALL_IDS = [...CHECKS.map(c => c.id), SWITCH.id]
const checkById = Object.fromEntries([...CHECKS, SWITCH].map(c => [c.id, c]))
const activeChecks = CHECKS.filter(c => !disabled.has(c.id))

const SEVERITY_RUBRIC = `Severity rubric (use exactly these levels):
- critical: data loss or corruption, a security breach, or a crash/total failure on a main path most users hit.
- high: a core feature gives wrong results or fails on a common path, with no reasonable workaround.
- medium: wrong behavior on a realistic edge case or error path that real users will eventually hit.
- low: minor or unlikely: cosmetic, rare edge case, misleading message.`

// ---------------------------------------------------------------------------
// Schemas
// ---------------------------------------------------------------------------

const SIDE_SCHEMA = {
  type: 'object',
  properties: {
    screens: { type: 'array', items: { type: 'object', properties: { name: { type: 'string' }, how_to_reach: { type: 'string' }, file: { type: 'string' } }, required: ['name', 'how_to_reach'] } },
    external_side_effects: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          action: { type: 'string' },
          screen: { type: 'string' },
          effect: { type: 'string', enum: ['email', 'notification', 'sms', 'external-post', 'payment', 'flow', 'webhook', 'other'] },
          target: { type: 'string' },
          file: { type: 'string' },
          line: { type: 'integer' },
        },
        required: ['action', 'effect'],
      },
    },
    record_changes: {
      type: 'array',
      items: {
        type: 'object',
        properties: { action: { type: 'string' }, screen: { type: 'string' }, change: { type: 'string', enum: ['create', 'update', 'delete'] }, data_store: { type: 'string' }, file: { type: 'string' }, line: { type: 'integer' } },
        required: ['action', 'change'],
      },
    },
    notes: { type: 'string' },
  },
  required: ['screens', 'external_side_effects', 'record_changes'],
}

const PREFLIGHT_SCHEMA = {
  type: 'object',
  properties: {
    reachable: { type: 'boolean' },
    signed_in: { type: 'boolean' },
    sign_in_notes: { type: 'string' },
    selection: {
      type: 'object',
      properties: {
        exists: { type: 'boolean' },
        control: { type: 'string' },
        levels: { type: 'array', items: { type: 'string' } },
        test_option_found: { type: 'boolean' },
        selected: { type: 'boolean' },
        notes: { type: 'string' },
      },
      required: ['exists', 'test_option_found', 'selected'],
    },
    screens: { type: 'array', items: { type: 'object', properties: { name: { type: 'string' }, how_to_reach: { type: 'string' }, url: { type: 'string' } }, required: ['name', 'how_to_reach'] } },
    console_errors: { type: 'array', items: { type: 'string' } },
    notes: { type: 'string' },
  },
  required: ['reachable', 'signed_in', 'selection', 'screens'],
}

const CATEGORIES = ['visual', 'layout', 'interaction', 'error-handling', 'navigation', 'data-integrity', 'accessibility', 'performance', 'scoping', 'other']

function testSchema(ids) {
  return {
    type: 'object',
    properties: {
      reached: { type: 'boolean' },
      findings: {
        type: 'array',
        items: {
          type: 'object',
          properties: {
            title: { type: 'string' },
            checkpoint: { type: 'string', enum: ids },
            severity: { type: 'string', enum: SEV },
            category: { type: 'string', enum: CATEGORIES },
            screen: { type: 'string' },
            url: { type: 'string' },
            viewport: { type: 'string' },
            steps: { type: 'array', items: { type: 'string' } },
            expected: { type: 'string' },
            actual: { type: 'string' },
            screenshot: { type: 'string' },
            evidence_type: { type: 'string', enum: ['runtime'] },
            file: { type: 'string' },
            line: { type: 'integer' },
          },
          required: ['title', 'checkpoint', 'severity', 'category', 'screen', 'viewport', 'steps', 'expected', 'actual', 'screenshot', 'evidence_type'],
        },
      },
      checks: {
        type: 'array',
        items: {
          type: 'object',
          properties: {
            id: { type: 'string', enum: ids },
            status: { type: 'string', enum: ['checked', 'not-applicable', 'limited'] },
            viewports: { type: 'array', items: { type: 'string' } },
            note: { type: 'string' },
          },
          required: ['id', 'status'],
        },
      },
      side_effect_risks: { type: 'array', items: { type: 'object', properties: { action: { type: 'string' }, why: { type: 'string' } }, required: ['action', 'why'] } },
      test_records_created: { type: 'array', items: { type: 'string' } },
      notes: { type: 'string' },
    },
    required: ['reached', 'findings', 'checks'],
  }
}

const REPLAY_SCHEMA = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['confirmed', 'refuted', 'uncertain'] },
    reasoning: { type: 'string' },
    severity: { type: 'string', enum: SEV },
    screenshot: { type: 'string' },
  },
  required: ['verdict', 'reasoning', 'severity'],
}

const REGRESSION_SCHEMA = {
  type: 'object',
  properties: {
    status: { type: 'string', enum: ['fixed', 'still-present', 'partially-fixed', 'unknown'] },
    evidence: { type: 'string' },
    screenshot: { type: 'string' },
  },
  required: ['status', 'evidence'],
}

// ---------------------------------------------------------------------------
// Agents. Browser agents share ONE browser, so they always run one at a time.
// ---------------------------------------------------------------------------

let agentsUsed = 0
const errors = []
async function ask(prompt, opts) {
  agentsUsed++
  try { return await agent(prompt, opts) } catch (e) { errors.push(`${opts.label}: ${clip(e && e.message ? e.message : e, 300)}`); return null }
}
async function browserAgent(prompt, opts) {
  let r = await ask(prompt, opts)
  if (!r) { log(`${opts.label} returned nothing; retrying once`); r = await ask(prompt, { ...opts, label: `${opts.label} retry` }) }
  return r
}

const signIn = () => {
  const l = A.login || {}
  if (!l.required) return 'If a sign-in page appears unexpectedly, report it in notes.'
  return `If you are not signed in: on the sign-in page type the text ${l.user_secret || 'BUGHUNT_UX_USER'} into the username/email field and ${l.password_secret || 'BUGHUNT_UX_PASSWORD'} into the password field, exactly as written (the browser replaces these names with the real values). ${l.notes || ''}`
}
const viewportText = VIEWPORTS.map(v => `${v.name} ${v.width}x${v.height}`).join(', ')

function sideEffectsPrompt() {
  const files = Array.isArray(A.files) ? A.files.map(f => f[0]) : []
  return [
    `Before a browser test of the running app, scan the codebase at ${A.root} (read-only) and list:`,
    '1. Every user action (button, link, form submit, page load, timer) that causes an EXTERNAL side effect: sends email, a notification to other people, SMS, a post to an external service or webhook, a payment, or triggers an automation (for example a Power Automate flow) that messages people. Say who or what it reaches.',
    '2. Every action that creates, updates or deletes records, and in which data store.',
    '3. The app\'s screens or pages and how a user reaches each (router configuration, navigation menus, Power Apps screens).',
    'Give file and line for each item. Completeness matters: anything you miss could be clicked during testing.',
    A.app_context ? `About the app: ${A.app_context}` : '',
    files.length ? `Source files (from the scope scan):\n${files.slice(0, 1500).join('\n')}` : 'Use Glob and Grep to find the source files.',
  ].filter(Boolean).join('\n\n')
}

function preflightPrompt() {
  return [
    `Open the running app at ${A.base_url} in the browser (resize to ${(() => { const d = VIEWPORTS.find(v => v.name === 'desktop') || VIEWPORTS[VIEWPORTS.length - 1]; return `${d.width}x${d.height}` })()} first).`,
    A.app_context ? `About the app: ${A.app_context}` : '',
    signIn(),
    `Find out whether the app has a selection control: an organizational level the user picks to decide which data is shown (property, regional, region or similar). If a property-level (or lowest-level) selection exists, select the option named "${TEST}" now, matching case-insensitively, without asking anyone. Report whether the control exists, whether "${TEST}" exists, and whether it is now selected.`,
    'Then list every screen or page reachable from the navigation (name, how to reach it, URL).',
    `In this step click ONLY sign-in, the selection control and navigation links; do not press action buttons or enter data. Save one screenshot of the starting screen as ${evidence('preflight-home.png')}. Report console errors you see while loading.`,
  ].filter(Boolean).join('\n\n')
}

function screenPrompt(screen, i, ctx) {
  const shotPrefix = evidence(`p${i + 1}-${slug(screen.name)}-`)
  return [
    `Test ONE screen of the running app at ${A.base_url}: "${screen.name}" (how to reach it: ${screen.how_to_reach || 'from the navigation'}).`,
    A.app_context ? `About the app: ${A.app_context}` : '',
    `Session: ${signIn()} ${ctx.selectionExists ? `Make sure "${TEST}" is selected in the selection control before entering any data.` : ''}`,
    ctx.dataEntryAllowed
      ? `Data entry: allowed in the test property "${TEST}" (or anywhere if the app has no selection control). Make test data obviously fake and start text with "BUGHUNT TEST". List what you create under test_records_created.`
      : `Data entry: NOT allowed in this run because the app has a property selection but no "${TEST}" option. Do look-only checks; report ux-interaction as "limited".`,
    `Do-not-click list (actions that reach real people or systems): ${ctx.avoid.length ? ctx.avoid.map(a => `"${a.action}"${a.screen ? ` on ${a.screen}` : ''} (${a.effect}${a.target ? ` to ${a.target}` : ''})`).join('; ') : 'none found by the code scan'}. Also do not click anything else that looks like it emails, notifies, texts, pays or posts outside the app; report it under side_effect_risks instead.`,
    ctx.recordChanges.length ? `Record-changing actions found by the code scan: ${ctx.recordChanges.map(r => `${r.change} via "${r.action}"`).join('; ')}. Delete only records you created; cancel at confirmation steps.` : '',
    `Viewports to check: ${viewportText}. Use browser_resize for each, and resize back to desktop at the end.`,
    `Checks. Do EVERY one and sign each off under "checks" as "checked", "not-applicable" (say why) or "limited" (say what you could not do), with the viewports you covered:\n\n${activeChecks.map(c => `[${c.id}] ${c.name} (findings reported as: ${c.kind})\n${c.checklist}`).join('\n\n')}`,
    `Evidence for every finding: save a screenshot whose file name starts with ${shotPrefix} and ends with .png (for example ${shotPrefix}phone-pill-overflow.png); give numbered steps from a fresh page load (include signing in and selecting "${TEST}" when needed), the viewport, what you expected and what actually happened, and evidence_type "runtime". If you can find the responsible code with Grep/Read, add file and line (optional).`,
    'If the screen cannot be reached, set reached to false and explain in notes.',
    SEVERITY_RUBRIC,
  ].filter(Boolean).join('\n\n')
}

function switchPrompt() {
  return [
    `Check selection switching in the running app at ${A.base_url}.`,
    signIn(),
    SWITCH.checklist,
    `Save screenshots whose file names start with ${evidence('switch-')} and end with .png. Every finding needs numbered steps, the viewport, expected vs actual, and evidence_type "runtime". Sign off "${SWITCH.id}" under "checks" when done.`,
    SEVERITY_RUBRIC,
  ].join('\n\n')
}

const fmtFinding = f => [
  `Title: ${f.title}`,
  `Screen: ${f.screen} | viewport: ${f.viewport} | URL: ${f.url || 'n/a'}`,
  `Steps:\n${(f.steps || []).map((s, i) => `${i + 1}. ${s}`).join('\n')}`,
  `Expected: ${f.expected}`,
  `Actual: ${f.actual}`,
].join('\n')

function replayPrompt(f, ctx) {
  return [
    `Another tester reported this problem in the running app at ${A.base_url}. Reproduce it yourself from a fresh page load.`,
    signIn(),
    `The finding (${checkById[f.checkpoint] ? checkById[f.checkpoint].name : f.checkpoint}):\n${fmtFinding(f)}`,
    `Do-not-click list: ${ctx.avoid.length ? ctx.avoid.map(a => `"${a.action}"`).join('; ') : 'none found'}.`,
    `Save your own screenshot as ${evidence(`replay-${f.tmp}.png`)}. Verdict "confirmed" only if you saw the problem yourself; "refuted" if the steps do not lead to it; "uncertain" if you could not complete the steps. Also give the severity you believe is right.`,
    SEVERITY_RUBRIC,
  ].join('\n\n')
}

function regressionPrompt(pf) {
  return [
    `In the previous cycle this problem was found in the running app at ${A.base_url} and a fix was applied. Check whether it is really gone, from a fresh page load.`,
    signIn(),
    fmtFinding(pf),
    `Save a screenshot as ${evidence(`recheck-${slug(pf.id)}.png`)}. Status "fixed", "still-present", "partially-fixed" or "unknown", with what you saw as evidence.`,
  ].join('\n\n')
}

// ---------------------------------------------------------------------------
// Run
// ---------------------------------------------------------------------------

phase('Side effects')
const sideP = ask(sideEffectsPrompt(), { label: 'scan side effects', phase: 'Side effects', schema: SIDE_SCHEMA, agentType: 'bug-hunter' })

phase('Preflight')
const pre = await browserAgent(preflightPrompt(), { label: 'preflight', phase: 'Preflight', schema: PREFLIGHT_SCHEMA, agentType: 'ux-tester' })
const side = (await sideP) || { screens: [], external_side_effects: [], record_changes: [], notes: 'side-effect scan did not complete' }
const sideScanOk = !!(side && side.notes !== 'side-effect scan did not complete')

if (!pre || !pre.reachable) {
  return {
    ok: false,
    error: pre ? `The app at ${A.base_url} was not reachable: ${pre.notes || 'no details'}` : 'The preflight browser agent did not complete. Check that the bughunt-browser tools are available (restart the session after installing) and that the app is running.',
    side_effects: side,
    errors,
  }
}
if ((A.login || {}).required && !pre.signed_in) {
  return { ok: false, error: `Sign-in failed: ${pre.sign_in_notes || 'no details'}. Check the BUGHUNT_UX_* secrets and the login notes in .bughunt/ux.json.`, preflight: pre, side_effects: side, errors }
}

const sel = pre.selection || { exists: false, test_option_found: false, selected: false }
const needsTestSelection = !!(sel.exists && !sel.test_option_found)
const dataEntryAllowed = !sel.exists || !!(sel.test_option_found && sel.selected)
if (needsTestSelection) log(`No "${TEST}" option found in the selection control: data entry is off for this run; please add a "${TEST}" property.`)
if (!sideScanOk) log('The side-effect scan did not complete: testers are told to avoid anything that looks external, but the do-not-click list is empty.')
const avoid = A.allow_external_side_effects ? [] : (side.external_side_effects || [])
const ctx = { selectionExists: !!sel.exists, dataEntryAllowed, avoid, recordChanges: side.record_changes || [] }

// Screens: from the preflight navigation, the code scan, and any hints; de-duplicated by name.
const byName = new Map()
for (const s of [...(pre.screens || []), ...(A.screens || []), ...(side.screens || [])]) {
  const key = slug(s.name)
  if (!byName.has(key)) byName.set(key, { name: s.name, how_to_reach: s.how_to_reach || s.url || '' })
}
const allScreens = [...byName.values()]
const screens = allScreens.slice(0, MAX_SCREENS)
const droppedScreens = allScreens.slice(MAX_SCREENS).map(s => s.name)
if (droppedScreens.length) log(`${droppedScreens.length} screen(s) beyond the limit of ${MAX_SCREENS} were not tested: ${droppedScreens.join(', ')}`)
log(`${screens.length} screen(s) to test, one at a time; selection control: ${sel.exists ? (sel.selected ? `"${TEST}" selected` : `no "${TEST}"`) : 'none'}; do-not-click actions: ${avoid.length}.`)

phase('Test')
const candidates = []
const grid = []
const sideRisks = []
const testRecords = []
let tmpId = 0
const collect = (r, screenName) => {
  for (const f of r.findings || []) candidates.push({ ...f, screen: f.screen || screenName, evidence_type: 'runtime', tmp: `F${++tmpId}` })
  for (const x of r.side_effect_risks || []) sideRisks.push({ ...x, screen: screenName })
  for (const x of r.test_records_created || []) testRecords.push(`${screenName}: ${x}`)
}
for (let i = 0; i < screens.length; i++) {
  const screen = screens[i]
  const ids = activeChecks.map(c => c.id)
  const r = await browserAgent(screenPrompt(screen, i, ctx), { label: `test ${clip(screen.name, 40)}`, phase: 'Test', schema: testSchema(ids), agentType: 'ux-tester' })
  const row = { row: `P${i + 1}`, screen: screen.name, cells: {}, notes: {} }
  for (const c of CHECKS) {
    if (disabled.has(c.id)) { row.cells[c.id] = 'off'; continue }
    if (!r) { row.cells[c.id] = 'failed'; continue }
    if (!r.reached) { row.cells[c.id] = 'unreached'; continue }
    const a = (r.checks || []).find(x => x.id === c.id)
    row.cells[c.id] = !a ? 'unattested' : a.status === 'checked' ? 'checked' : a.status === 'limited' ? 'limited' : 'n/a'
    if (a && (a.note || (a.viewports || []).length)) row.notes[c.id] = clip(`${(a.viewports || []).join(', ')}${a.note ? ` ${a.note}` : ''}`.trim(), 200)
  }
  if (r && !r.reached) row.notes.reached = clip(r.notes || 'screen could not be reached', 200)
  grid.push(row)
  if (r) collect(r, screen.name)
}

let switchStatus = disabled.has(SWITCH.id) ? 'off' : sel.exists ? 'pending' : 'n/a'
if (switchStatus === 'pending') {
  const r = await browserAgent(switchPrompt(), { label: 'test selection switching', phase: 'Test', schema: testSchema([SWITCH.id]), agentType: 'ux-tester' })
  const a = r && (r.checks || []).find(x => x.id === SWITCH.id)
  switchStatus = !r ? 'failed' : !a ? 'unattested' : a.status === 'checked' ? 'checked' : a.status === 'limited' ? 'limited' : 'n/a'
  if (r) collect(r, 'selection switching')
}

// ---------------------------------------------------------------------------
// De-duplicate (same screen + check + similar title; different viewports are merged), then replay
// ---------------------------------------------------------------------------

const words = s => new Set(String(s).toLowerCase().match(/[a-z0-9]+/g) || [])
const similar = (a, b) => {
  if (slug(a.screen) !== slug(b.screen) || a.checkpoint !== b.checkpoint) return false
  const wa = words(a.title), wb = words(b.title)
  let inter = 0
  for (const w of wa) if (wb.has(w)) inter++
  return inter / Math.max(1, Math.min(wa.size, wb.size)) >= 0.6
}
const unique = []
let duplicates = 0
for (const f of candidates) {
  const d = unique.find(u => similar(u, f))
  if (d) {
    duplicates++
    if (f.viewport && !String(d.viewport).includes(f.viewport)) d.viewport = `${d.viewport}, ${f.viewport}`
    continue
  }
  unique.push(f)
}
const kindOf = f => {
  for (const rule of KIND_RULES) if (rule.test(f)) return rule.kind
  return (checkById[f.checkpoint] || {}).kind || 'bug'
}
for (const f of unique) f.kind = kindOf(f)
unique.sort((x, y) => KINDS.indexOf(x.kind) - KINDS.indexOf(y.kind) || sevRank(x.severity) - sevRank(y.severity))
const toReplay = unique.slice(0, MAX_REPLAYS)
const notReplayed = unique.slice(MAX_REPLAYS)
if (notReplayed.length) log(`${notReplayed.length} lower-priority finding(s) beyond the replay limit of ${MAX_REPLAYS} were not replayed; they are reported as disputed.`)

phase('Replay')
const regressions = []
for (const pf of Array.isArray(A.previous_findings) ? A.previous_findings : []) {
  const v = await browserAgent(regressionPrompt(pf), { label: `recheck ${pf.id}`, phase: 'Replay', schema: REGRESSION_SCHEMA, agentType: 'ux-skeptic' })
  regressions.push({ id: pf.id, title: pf.title, screen: pf.screen, ...(v || { status: 'unknown', evidence: 'checker did not complete' }) })
}

const confirmed = []
const disputed = []
const refuted = []
for (const f of toReplay) {
  const v = await browserAgent(replayPrompt(f, ctx), { label: `replay ${f.tmp} ${clip(f.title, 30)}`, phase: 'Replay', schema: REPLAY_SCHEMA, agentType: 'ux-skeptic' })
  const rec = {
    ...f,
    checkpoint_name: (checkById[f.checkpoint] || {}).name || f.checkpoint,
    hunter_severity: f.severity,
    severity: v && v.verdict === 'confirmed' && SEV.includes(v.severity) ? v.severity : f.severity,
    verification: { status: v ? v.verdict : 'unverified', votes: v ? `replay ${v.verdict}` : 'replay did not complete', reasons: v ? [clip(v.reasoning, 500)] : [], replay_screenshot: v && v.screenshot },
  }
  if (v && v.verdict === 'confirmed') confirmed.push(rec)
  else if (v && v.verdict === 'refuted') refuted.push({ title: rec.title, kind: rec.kind, checkpoint: rec.checkpoint, screen: rec.screen, viewport: rec.viewport, severity: rec.severity, reason: clip(v.reasoning, 400) })
  else disputed.push(rec)
}
for (const f of notReplayed) disputed.push({ ...f, checkpoint_name: (checkById[f.checkpoint] || {}).name || f.checkpoint, verification: { status: 'not replayed', votes: 'over the replay limit', reasons: [] } })

// ---------------------------------------------------------------------------
// Result
// ---------------------------------------------------------------------------

for (const kind of KINDS) confirmed.filter(b => b.kind === kind).forEach((b, i) => { b.id = `${KIND_PREFIX[kind]}${i + 1}` })
disputed.forEach((b, i) => { b.id = `UD${i + 1}` })
for (const b of [...confirmed, ...disputed]) { b.blocks = BLOCKING_KINDS.includes(b.kind) && sevRank(b.severity) <= sevRank(threshold); delete b.tmp }

const gapStatuses = ['failed', 'unattested', 'unreached', 'limited']
const gaps = [
  ...grid.flatMap(g => Object.entries(g.cells).filter(([, s]) => gapStatuses.includes(s)).map(([id, s]) => `${g.row} ${g.screen} / ${id}: ${s}`)),
  ...(gapStatuses.includes(switchStatus) ? [`${SWITCH.id}: ${switchStatus}`] : []),
  ...(droppedScreens.length ? [`${droppedScreens.length} screen(s) not tested (limit ${MAX_SCREENS})`] : []),
  ...(needsTestSelection ? [`no "${TEST}" option in the selection control`] : []),
  ...(!sideScanOk ? ['side-effect scan did not complete'] : []),
]
const coverageComplete = gaps.length === 0 && screens.length > 0
const blocking = confirmed.filter(b => b.blocks)
const openRegressions = regressions.filter(r => r.status === 'still-present' || r.status === 'partially-fixed')
const countBy = (arr, key, values) => values.reduce((o, v) => ({ ...o, [v]: arr.filter(b => b[key] === v).length }), {})

return {
  ok: true,
  kind: 'uxcheck',
  root: A.root,
  run_dir: A.run_dir,
  base_url: A.base_url,
  clean: blocking.length === 0 && openRegressions.length === 0 && coverageComplete,
  clean_threshold: threshold,
  blocking_kinds: BLOCKING_KINDS,
  needs_test_selection: needsTestSelection,
  data_entry_allowed: dataEntryAllowed,
  preflight: { signed_in: pre.signed_in, selection: sel, console_errors: pre.console_errors || [], notes: pre.notes },
  side_effects: {
    scan_completed: sideScanOk,
    external: side.external_side_effects || [],
    record_changes: side.record_changes || [],
    avoided_by_rule: avoid.map(a => a.action),
    risks_seen_while_testing: sideRisks,
    test_records_created: testRecords,
  },
  stats: {
    screens_tested: screens.length,
    viewports: VIEWPORTS.map(v => `${v.name} ${v.width}x${v.height}`),
    agents_used: agentsUsed,
    candidates: candidates.length,
    duplicates_merged: duplicates,
    confirmed: confirmed.length,
    disputed: disputed.length,
    refuted: refuted.length,
    confirmed_by_kind: countBy(confirmed, 'kind', KINDS),
    bugs_by_severity: countBy(confirmed.filter(b => b.kind === 'bug'), 'severity', SEV),
    blocking: blocking.length,
  },
  confirmed,
  disputed,
  refuted,
  regressions,
  coverage: {
    complete: coverageComplete,
    checkpoints: ALL_IDS.map(id => ({ id, name: checkById[id].name, kind: checkById[id].kind, enabled: !disabled.has(id) })),
    grid,
    whole_app: { [SWITCH.id]: { status: switchStatus } },
    gaps,
    dropped_screens: droppedScreens,
    errors: errors.slice(0, 20),
  },
  kind_rules: KIND_RULES.map(r => r.why),
}
