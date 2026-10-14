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

**"Clean"** means no confirmed bugs at or above the threshold (default **medium**), no fix that failed to hold, and complete coverage. Low-severity items are still reported, but they do not keep the loop running.

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

| Tier (auto by size) | Lines per slice | Hunters (cap) | Skeptics per finding | Rounds |
|---|---|---|---|---|
| small (< 3k lines) | 1,500 | ≤ 6 + 1 cross-cutting | 1 | 1 |
| medium (< 30k) | 2,500 | ≤ 24 + 3 | 3 for critical/high, else 1 | ≤ 2 |
| large (≥ 30k) | 3,000 | ≤ 48 + 4 | 3, majority vote | ≤ 3 |
| lean / max | 4,000 / 1,500 | ≤ 8 / ≤ 80 | 1 / 3 to 5 | 1 / ≤ 3 |

Each extra round re-hunts every slice through a new lens (edge cases, then security) and stops as soon as a round confirms nothing new. One run never uses more than 900 agents. Tune the tiers in the `TIERS` table at the top of `workflows/bughunt-scan.js`.

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

`node .claude/bughunt-tests/test.mjs` runs the three workflows against simulated agents. It needs no tokens and checks the logic: slicing, full file coverage, deduplication, skeptic voting, clean/not-clean decisions, regression checks, approval-safe fallbacks and fix grouping. Run it after editing a workflow.
