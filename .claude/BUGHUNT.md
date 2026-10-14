# Bughunt kit

A reusable Claude Code kit that hunts bugs with a **dynamic workflow** instead of a single agent, then repairs them in an approval-gated loop.

**Why a workflow:** a single agent reviewing a big codebase carries everything in one context. As that context fills, it summarizes and loses detail. It also judges its own findings and tends to stop early. Anthropic's test hid 70 bugs in about 116,000 lines: a single agent found 14 to 27, and a workflow found 66 on each of three runs. The workflow's design, which this kit follows:

1. **Split the code into slices and give each slice a fresh agent with an empty context.**
2. **Hand every reported bug to a separate skeptic whose only job is to disprove it.** The skeptic did not write the claim, so it has no reason to defend it.
3. **Keep the plan in a program, not in an agent's memory**, so it never gets summarized away.

## Commands

| Command | What it does | Changes code? |
|---|---|---|
| `/bughunt [path]` | Multi-agent hunt with skeptic verification. Writes `report.md`. | **No**. Hunters and skeptics have no edit tools. |
| `/bugfix-plan` | Planners design root-cause fixes, critics try to break each fix, then an end-of-plan review covers what works, what does not, and what could cause new bugs. Ends by asking for your approval. | **No** |
| `/bugfix-apply` | Applies only the approved items on a `bugfix/…` branch, runs your tests, and makes a checkpoint commit. | Yes, approved items only |
| `/bugloop [path]` | Hunt → plan → **your approval** → apply → re-hunt with regression checks, repeated until clean. | Yes, approved items only |

Useful options: `--mode lean|small|medium|large|max` (default `auto` scales with code size), `--focus "payments and auth"`, `--threshold high`, and `--max-cycles 5` (loop only). Loop sub-commands: `/bugloop status`, `/bugloop resume`, `/bugloop stop`.

## The loop

```
          ┌──────────────────────────────────────────────────────────────┐
          ▼                                                              │
  HUNT (read-only) ──clean?──yes──► DONE: summary, branch, offer to push │
  slices → hunters → skeptics        │                                   │
          │ no                       │                                   │
          ▼                                                              │
  PLAN (read-only)                                                       │
  planners → critics → end-of-plan review                                │
          ▼                                                              │
  YOU APPROVE items (every cycle; nothing approved = stop)               │
          ▼                                                              │
  APPLY approved items → reviewer checks each edit → your tests → commit │
          └──────────── re-hunt + "did each fix hold?" check ────────────┘
```

**"Clean"** means all three of these:
- no confirmed **bugs** at or above the threshold (default **medium**);
- no fix that failed to hold;
- no gap in the coverage grid.

Low-severity bugs and non-blocking findings are still reported, but they do not keep the loop running.

## Checkpoints, coverage grid and finding kinds

The hunt checks the code against a fixed list of **checkpoints**. Each checkpoint is one self-contained entry in the `CHECKPOINTS` list at the top of `workflows/bughunt-scan.js`. Adding a layer means adding an entry; the engine does not change.

| Checkpoint | Checked on | Produces |
|---|---|---|
| Core logic and error handling | every slice | bugs |
| Edge cases and failure paths | every slice | bugs |
| Security and data integrity | every slice | bugs |
| Contracts and assumptions | every slice | bugs |
| Power Apps (Power Fx) | slices with `.pa.yaml`/`.fx.yaml` | bugs; delegation limits become warnings |
| Cross-file contracts | whole codebase | bugs |
| Cross-file security | whole codebase | bugs |
| Shared state, lifecycle and async | whole codebase | bugs |
| Build, configuration and deployment | whole codebase | bugs |
| Power Apps, app-wide | whole codebase, Power Apps apps only | bugs; delegation limits become warnings |

- **Every checkpoint is a required pass.** It runs whether or not earlier passes found anything. Each agent must sign off every checkpoint it was given as "checked" or "not applicable (why)". A missing sign-off triggers a follow-up agent for just that checkpoint.
- **Coverage grid.** Every report shows slices × checkpoints: ✓ checked, – not applicable, off, ✗ failed, ? not signed off. Any ✗ or ? blocks "clean".
- **Finding kinds.** `bug` is the only kind that can block "clean". `warning`, `code-health`, `accessibility` and `cosmetic` are reported with IDs W, H, A and V, but never block. A fixed rule in code, not the AI, turns Power Apps delegation-limit findings into warnings.
- **Selections.** Security checkpoints are told that switching between selections (property, regional, region…) is intended and is not a security issue.
- **Turning a checkpoint off** for one app: ask `/bughunt` to skip it (for example "skip contracts"). It shows as "off" in the grid.

## Evidence gate

Every finding must carry a checkpoint, an evidence type (`code` or `runtime`), a severity and its evidence.

After every hunt, `skills/bughunt/evidence-gate.mjs`, a plain script with no AI, checks the evidence:
- **Code evidence:** the cited file must exist inside the project, and the quoted code must appear within 10 lines of the cited line. If the quote is found elsewhere in the same file, the line number is corrected and the correction is noted.
- **Runtime evidence** (for the future browser engine): the screenshot file must exist and the reproduction steps must be non-empty.

Findings that fail move to "Rejected: no valid evidence" and **cannot enter a fix plan**. The planning workflow refuses any finding without a passed check, even if someone passes one in by hand. The gate needs Node.js.

The loop also stops, and tells you why, when any of these happens:
- it reaches the cycle limit (default 5);
- the bug count has not dropped for two cycles;
- only manual or "stubborn" bugs remain (a stubborn bug has failed two fix attempts);
- you approve nothing.

## Safety

- **Read-only is enforced, not just requested.** `bug-hunter`, `bug-skeptic`, `fix-planner` and `fix-critic` are defined with only `Read, Grep, Glob`. `bug-fixer` is the only agent with edit tools, and it runs only from `/bugfix-apply` with a recorded approval.
- `/bugfix-apply` and `/bugloop` can only be started by you typing them (`disable-model-invocation`).
- Fixes land on a dedicated `bugfix/…` or `bugloop/…` branch with one commit per cycle, so every cycle can be reverted. Nothing is ever pushed unless you ask.
- A failed or skipped agent is reported as a coverage gap and blocks "clean". The kit never reports silence as success.
- Findings whose quoted evidence a script cannot find in the code are rejected and can never become fixes.

## Install in another project

Copy these into the other repo's `.claude/` folder, merging with what is there:

```
.claude/agents/{bug-hunter,bug-skeptic,fix-planner,fix-critic,bug-fixer}.md
.claude/workflows/{bughunt-scan,bugfix-propose,bugfix-execute}.js
.claude/skills/{bughunt,bugfix-plan,bugfix-apply,bugloop}/
.claude/BUGHUNT.md
.claude/bughunt-tests/   (optional)
```

For example: `cp -r .claude/agents .claude/workflows .claude/skills .claude/BUGHUNT.md /path/to/other-app/.claude/`

To make the kit available in **every** project on one computer (local CLI), copy the same folders into `~/.claude/` instead. Cloud sessions start from the repository, so for apps you work on in the cloud, keep the kit inside each repo.

**Start a new Claude Code session after installing.** Agents, skills and workflows load at session start.

## Cost

Every agent spends tokens. Expect roughly 50k to 100k per agent; Anthropic's demo spent about 1.3M tokens on 15 agents. `/bughunt` shows the estimate and asks before medium, large or max runs. Each loop cycle is another full hunt plus planning.

| Tier (auto by size) | Lines per slice | Slices (cap) | Agents per slice | Whole-codebase agents | Skeptics per bug | Extra sweeps |
|---|---|---|---|---|---|---|
| small (< 3k lines) | 1,500 | ≤ 6 | 2 | 1 (all together) | 1 | none |
| medium (< 30k) | 2,500 | ≤ 24 | 2 | 4 | 3 for critical/high, else 1 | ≤ 1 |
| large (≥ 30k) | 3,000 | ≤ 48 | 2 | 4 | 3, majority vote | ≤ 2 |
| lean / max | 4,000 / 1,500 | ≤ 8 / ≤ 80 | 1 / 4 | 1 / 4 | 1 / 3 to 5 | none / ≤ 2 |

Notes:
- Power Apps slices get one more agent, and Power Apps apps one more whole-codebase agent.
- Non-bug findings get one skeptic.
- Extra sweeps re-check every slice with fresh eyes and stop as soon as one confirms nothing new.
- Required checkpoint passes cost about 2× more agents than the first version of the kit on larger apps, and about 3× on small ones.
- One run never uses more than 900 agents.
- Tune the tiers in the `TIERS` table in `workflows/bughunt-scan.js`.

## Power Apps

- Hunters get a Power Fx checklist whenever a slice contains `.pa.yaml` or `.fx.yaml` source. It covers delegation limits, unhandled Patch/SubmitForm errors, ForAll and Concurrent ordering, variable scope, Blank handling, Choice columns, client-side-only security and hard-coded environment values. One extra cross-cutting hunter reviews the app as a whole.
- A `.msapp` file is a packed zip, so the kit cannot read it as-is. Unzip it and point the hunt at `Src/*.pa.yaml`, or use Power Platform Git integration, which keeps `.pa.yaml` source in the repo.
- Microsoft advises only minor direct edits to `.pa.yaml`. Fix plans therefore mark larger Power Apps changes **manual** and give step-by-step Power Apps Studio instructions instead of auto-applying them.
- Nothing runs Power Apps locally, so verification relies on the re-hunt and your own testing in Studio.

## Output

```
.bughunt/
  ACTIVE_LOOP                       path of the running loop (for /bugloop resume)
  runs/<YYYYMMDD-HHMM>-hunt/        scope.json, findings.json, report.md, then fix-plan.*, approval.json, apply-result.json
  runs/<YYYYMMDD-HHMM>-loop/        state.json, SUMMARY.md, cycle-01/, cycle-02/, …
```

## Limits

- Agents read code; they do not run the app. Your test suite runs after fixes are applied, and the re-hunt checks that each fix held.
- Results vary between runs. A clean run means the hunters and skeptics found nothing at the threshold, not that the code is proven correct.
- Files over 512 KB are skipped as likely generated (raise `BUGHUNT_MAX_BYTES`). For very large codebases (more than about 150k lines), slices get big; hunt one folder at a time or use `--mode max`.

## Maintaining the kit

`node .claude/bughunt-tests/test.mjs` runs the three workflows against simulated agents and the evidence gate against sample files. It needs no tokens and checks:
- slicing, required checkpoint passes and full file coverage;
- sign-offs and follow-ups, the coverage grid and finding kinds;
- deduplication, skeptic voting and clean/not-clean decisions;
- regression checks and evidence rejection;
- that the plan step refuses unchecked findings;
- fix grouping.

Run it after editing a workflow or the gate.
