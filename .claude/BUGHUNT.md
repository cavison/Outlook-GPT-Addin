# Bughunt kit

A reusable Claude Code kit that audits apps with **dynamic workflows** instead of a single agent, then repairs what it finds in an approval-gated loop. It works the same way for web apps and Power Apps.

**Why a workflow:** a single agent reviewing a big codebase carries everything in one context. As that context fills, it summarizes and loses detail. It also judges its own findings and tends to stop early. Anthropic's test hid 70 bugs in about 116,000 lines: a single agent found 14 to 27, and a workflow found 66 on each of three runs. The kit follows the same design:

1. **Give each piece of code a fresh agent with an empty context.**
2. **Hand every finding to a separate skeptic whose only job is to disprove it.**
3. **Keep the plan in a program**, so it never gets summarized away.

## Commands

| Command | What it does | Changes code? |
|---|---|---|
| `/bughunt [path]` | Code-reading audit: every checkpoint is a required pass on every slice of code, skeptics try to refute each finding, and a script verifies every quoted piece of evidence. Writes `report.md` with a coverage grid. | **No**. These agents have no edit tools. |
| `/uxcheck [url]` | Browser audit of the running app: layout at phone, tablet, desktop and zoom widths; buttons, forms, back/refresh; keyboard and accessibility; selection switching. Every finding has a screenshot and steps that an independent agent replays. | **No**. Browser agents have no edit tools and cannot run scripts in the app. |
| `/bugfix-plan` | Planners design root-cause fixes, critics try to break each fix, then an end-of-plan review covers what works, what doesn't, and what could cause new bugs. Ends by asking for your approval. | **No** |
| `/bugfix-apply` | Applies only the approved items on a `bugfix/…` branch, has each edit reviewed, runs your tests, and makes a checkpoint commit. | Approved items only |
| `/bugloop [path] [--ux]` | Audit → plan → **your approval** → apply → re-audit with "did each fix hold?" checks, repeated until clean. `--ux` adds the browser check to every cycle. | Approved items only |

**Options:**
- `--mode lean|small|medium|large|max`; the default `auto` scales with code size.
- `--focus "payments and auth"`.
- `--threshold high`.
- `--max-cycles 5` (loop only).

**Loop sub-commands:** `/bugloop status`, `/bugloop resume`, `/bugloop stop`.

## The loop

```
          ┌───────────────────────────────────────────────────────────────┐
          ▼                                                               │
  AUDIT (read-only) ──clean?──yes──► DONE: summary, branch, offer to push │
  code: slices × checkpoints → skeptics → evidence script                 │
  browser (--ux): screens → replays → evidence script                     │
          │ no                                                            │
          ▼                                                               │
  PLAN (read-only): planners → critics → end-of-plan review               │
          ▼                                                               │
  YOU APPROVE items (every cycle; nothing approved = stop)                │
          ▼                                                               │
  APPLY approved items → reviewer checks each edit → your tests → commit  │
          └──────────── re-audit + "did each fix hold?" checks ───────────┘
```

**"Clean"** means all three of these:
- no confirmed **bugs** at or above the threshold (default **medium**);
- no fix that failed to hold;
- no gap in the coverage grid.

Only bugs block. Warnings (including Power Apps delegation limits and performance), code health, accessibility and cosmetic findings are reported but never block.

**The loop stops and says why** when any of these happens:
- it is clean;
- it reaches the cycle limit (default 5);
- the bug count has not dropped for two cycles;
- only manual or "stubborn" bugs remain (a stubborn bug has failed two fix attempts);
- you approve nothing.

## Code checkpoints (`/bughunt`)

Each checkpoint is one self-contained entry in the `CHECKPOINTS` list in `workflows/bughunt-scan.js`. Adding a layer means adding an entry; the engine does not change.

| Checkpoint | Checked on | Produces |
|---|---|---|
| Core logic and error handling (incl. swallowed errors, "success" after failure, dates and time zones) | every slice | bugs |
| Edge cases and failure paths (incl. zero/negative/long/special-character input, two users saving one record) | every slice | bugs |
| Performance (N+1 calls, unbounded loads, re-renders, heavy imports) | every slice | warnings |
| Security and data integrity | every slice | bugs |
| Contracts and assumptions | every slice | bugs |
| Code health (dead code, duplicated logic, hard-coded values) | every slice | code health |
| Interaction and response handling (double-submit, lost form input, unconfirmed deletes, back/refresh/session expiry, error/empty/slow responses) | slices with screen code | bugs |
| UI feedback and layout hints (spinners, empty states, likely overflow, scroll issues) | slices with screen code | cosmetic |
| Accessibility, measured against WCAG 2.2 AA | slices with screen code | accessibility |
| Power Apps (Power Fx) | slices with `.pa.yaml`/`.fx.yaml` | bugs; delegation limits are warnings |
| Cross-file contracts | whole codebase | bugs |
| Data and API contracts (payloads, server-side validation, indexes, constraints, orphaned records) | whole codebase | bugs; missing indexes are warnings |
| Cross-file security | whole codebase | bugs |
| Shared state, lifecycle and async | whole codebase | bugs |
| Build, configuration and deployment | whole codebase | bugs |
| Power Apps, app-wide | whole codebase (Power Apps apps) | bugs; delegation limits are warnings |
| Selection scoping: a mapping agent finds every place a selection is used, checkers verify each returns exactly the right items (no leaks, no gaps), plus a switching check | whole codebase (n/a without a selection concept) | bugs, rated as correctness, not privacy |

How the checkpoints run:
- **Every checkpoint is a required pass.** It runs whether or not earlier passes found anything.
- **Sign-offs.** Agents must sign off each checkpoint as "checked" or "not applicable (why)". A missing sign-off triggers a follow-up agent for just that checkpoint.
- **Coverage grid.** Every report shows slices × checkpoints: ✓ checked, – not applicable, off, ✗ failed, ? not signed off. Any ✗ or ? blocks "clean".
- **Screen code** is detected by the scope script: HTML, CSS, JSX/TSX, Vue, Svelte, Razor and Power Apps screens, plus JavaScript/TypeScript that touches the page.
- **Accessibility** is a review standard only. Nothing is ever added to the app to measure it, and fixes may only be plain label or property changes.
- **Selections.** Switching between selections (property, regional, region…) is treated as intended, never as a security issue.
- **Fixed rules, in code:** Power Apps delegation limits and performance findings are always warnings. The AI's opinion doesn't decide this.

## Browser checks (`/uxcheck`)

| Check | Covers | Produces |
|---|---|---|
| Visual and layout | overflow and cut-off text in pills, buttons, cards and cells; double scrollbars; sticky headers; phone 375, tablet 768, desktop 1440 and 200% zoom (simulated as a 720 px window, the WCAG reflow method); empty and loading states | cosmetic |
| Functional and interaction | every button gives feedback, double-clicks, invalid input kept and explained, back/refresh mid-flow, delete confirmations (opened, then cancelled), console errors, failed requests behind a "success" | bugs |
| Accessibility (WCAG 2.2 AA review) | keyboard-only navigation with visible focus, accessible names, tap targets ≥ 24 px, clear contrast problems | accessibility |
| Selection switching | everything refreshes after switching, with nothing carried over | bugs |

**Rules the browser agents follow:**
- **ZZ-test by default.** Whenever there's a property selection, "ZZ-test" is selected automatically, without asking. All test data goes there, marked "BUGHUNT TEST". If an app has no ZZ-test option, the run flags it and does look-only checks.
- **No code access.** Browser agents only have look-and-click tools. They have no editing, shell, file-upload or run-code-in-page tools.
- **No contact with real people or systems.** A code scan first lists every action that emails, notifies, texts, pays, posts or triggers flows. Those are never clicked and are listed in the report, along with the test records created.
- **Credentials stay hidden.** Agents type the secret *names* (`BUGHUNT_UX_USER`, `BUGHUNT_UX_PASSWORD`); the browser server swaps in the values and blanks them out of everything the AI reads.
- **One browser, one tester at a time.** A 10-screen app takes roughly an hour.

**Setup per app:**
1. Install with `--with-ux` (below).
2. Set `BUGHUNT_UX_USER`/`BUGHUNT_UX_PASSWORD` as environment secrets if the app needs sign-in. For single sign-on with MFA (Power Apps, Microsoft 365), save a signed-in session on your computer with `npx playwright open --save-storage=storage-state.json <app URL>` and store its contents as `BUGHUNT_UX_STORAGE_STATE`. Sessions expire, so redo this now and then.
3. Run `/uxcheck`. The first run asks where the app runs and saves the answer in `.bughunt/ux.json`; no secrets are stored there.

## Evidence and severity

- Every finding must carry a checkpoint, an evidence type (`code` or `runtime`), a severity, and evidence.
- After every run, `skills/bughunt/evidence-gate.mjs`, a plain script with no AI, checks the evidence:
  - **Code findings:** the file must exist inside the project, and the quoted code must appear within 10 lines of the cited line. If it is found elsewhere in the file, the line number is corrected and noted.
  - **Browser findings:** the screenshot must exist inside the project and be a real image, and the steps must be non-empty.
- Failing findings are listed as "Rejected: no valid evidence" and **cannot enter a fix plan**. The planning workflow itself refuses unchecked findings.
- Severity follows one shared rubric (critical, high, medium, low). Skeptics and replays re-rate it, and reports show both the original and the verified rating.

## Safety

- **Read-only is enforced, not just requested.** Audit, skeptic, planner and critic agents only have `Read, Grep, Glob`; browser agents add only look-and-click browser tools. `bug-fixer` is the only agent that can edit, and it runs only from `/bugfix-apply` with a recorded approval.
- **You start the risky commands.** `/bugfix-apply`, `/bugloop` and `/uxcheck` only run when you type them.
- **Every cycle can be undone.** Fixes land on a `bugfix/…` or `bugloop/…` branch with one commit per cycle. Nothing is pushed unless you ask.
- **Silence is never success.** A failed or skipped agent is a coverage gap and blocks "clean".

## Install in another project

From a repo that has the kit:

```
node .claude/bughunt-install.mjs /path/to/your-app            # code audit + fix loop
node .claude/bughunt-install.mjs /path/to/your-app --with-ux  # also the browser check
node .claude/bughunt-install.mjs /path/to/your-app --force    # upgrade to this kit version
node .claude/bughunt-install.mjs --user                       # every project on this computer (local CLI)
```

What the installer does:
- copies the kit into the app's `.claude/` folder;
- keeps any kit file you have changed, unless you use `--force`;
- git-ignores `.bughunt/.auth/` and `.bughunt/.mcp-output/`;
- with `--with-ux`, registers and enables the `bughunt-browser` server in `.mcp.json` and `.claude/settings.json`.

Add `--dry-run` to preview. Cloud sessions start from the repository, so install into each repo you work on in the cloud, then commit the result.

**Start a new Claude Code session after installing.** Agents, skills, workflows and the browser server load at session start.

**Requirements:**
- Claude Code with workflows;
- Node.js 18+ (evidence gate, installer, browser server);
- bash and git (scope script and fix branches);
- for `/uxcheck`: network access to the npm registry (the browser server is fetched with npx, pinned to `@playwright/mcp@0.0.82`), and Chrome/Edge locally or the preinstalled Chromium in cloud sessions. `BUGHUNT_UX_BROWSER` and `BUGHUNT_UX_EXECUTABLE` override the browser choice.

## Cost

Every agent spends tokens: expect roughly 50k to 100k per agent (Anthropic's demo spent about 1.3M tokens on 15 agents). `/bughunt` shows an estimate and asks before medium, large or max runs. Each loop cycle repeats the audit.

| Tier (auto by size) | Lines per slice | Slices (cap) | Agents per slice | Whole-codebase agents | Skeptics per bug | Extra sweeps |
|---|---|---|---|---|---|---|
| small (< 3k lines) | 1,500 | ≤ 6 | 2, or 3 with screen code | 1 (all together) | 1 | none |
| medium (< 30k) | 2,500 | ≤ 24 | 2, or 3 with screen code | 5 | 3 for critical/high, else 1 | ≤ 1 |
| large (≥ 30k) | 3,000 | ≤ 48 | 2, or 3 with screen code | 5 | 3, majority vote | ≤ 2 |
| lean / max | 4,000 / 1,500 | ≤ 8 / ≤ 80 | 1 / one per checkpoint | 1 / 5 | 1 / 3 to 5 | none / ≤ 2 |

Notes:
- **Selection scoping** adds one mapping agent, plus one checker per 8 places that use a selection (at most 30), plus a switching check.
- **Power Apps** adds one agent per Power Apps slice and one app-wide agent.
- **Non-bug findings** get one skeptic.
- **Caps:** a code audit never uses more than 900 agents.
- **`/uxcheck`** uses about 3 agents plus one per screen (20 screens by default) and one replay per finding (60 at most). Screenshots make browser agents more expensive than code agents.
- **Tuning:** change the tiers in the `TIERS` table in `workflows/bughunt-scan.js`.

## Power Apps

- Hunters get a Power Fx checklist on `.pa.yaml`/`.fx.yaml` source:
  - delegation limits;
  - unhandled Patch/SubmitForm errors;
  - ForAll/Concurrent ordering;
  - variable scope;
  - Blank handling;
  - Choice columns;
  - client-side-only security;
  - hard-coded environment values.
- A `.msapp` file is a packed zip. Unzip it and point the hunt at `Src/*.pa.yaml`, or use Power Platform Git integration, which keeps `.pa.yaml` source in the repo.
- Microsoft advises only minor direct edits to `.pa.yaml`, so fix plans mark larger Power Apps changes **manual**, with step-by-step Power Apps Studio instructions.
- Browser checks of Power Apps need a saved signed-in session (see above). Some tenants block automated browsers. If that happens, rely on the code audit and test in Studio.

## Output

```
.bughunt/
  ux.json                           /uxcheck settings for this app (no secrets)
  ACTIVE_LOOP                       path of the running loop (for /bugloop resume)
  runs/<YYYYMMDD-HHMM>-hunt/        scope.json, findings.json, report.md, then fix-plan.*, approval.json, apply-result.json
  runs/<YYYYMMDD-HHMM>-ux/          findings.json, ux-report.md, ux-evidence/*.png
  runs/<YYYYMMDD-HHMM>-loop/        state.json, SUMMARY.md, cycle-01/ (with ux/ when --ux), cycle-02/, …
  .auth/, .mcp-output/              credentials and browser scratch files, git-ignored
```

## Limits

- **Results vary between runs.** A clean run means nothing was found at the threshold. It does not prove the code is correct.
- **Some things can't be tested in a browser.** It can't throttle the network, force a session to expire, or load production-size data. Those are covered by the code checkpoints only.
- **Contrast is approximate in the browser check.** It is judged from screenshots, because nothing is injected into the app.
- **Large and very large codebases need care.** Files over 512 KB are skipped as likely generated (raise `BUGHUNT_MAX_BYTES`). Above about 150k lines, slices get big: hunt one folder at a time or use `--mode max`.

## Maintaining the kit

- `node .claude/bughunt-tests/test.mjs` runs offline tests with no tokens. It runs the four workflows against simulated agents, the evidence gate against sample files, and the installer against temporary repos.
- `node .claude/bughunt-tests/browser-smoke.mjs` is the browser self-test, also with no AI. It:
  - starts a practice app;
  - launches the real browser server;
  - signs in with secret names and checks the password never appears;
  - selects ZZ-test and saves a screenshot;
  - confirms every browser tool named in the agent files exists in the pinned server version.

  Run it after changing the browser server version.

The version is recorded in `bughunt-kit.json`; its `files` list is what the installer copies.
