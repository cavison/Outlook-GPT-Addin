---
name: bughunt
description: Read-only, multi-agent bug hunt of an app or codebase using a dynamic workflow, the method Anthropic used to find 66 of 70 planted bugs where a single agent found 14-27. Fresh-context hunter agents check every slice of the code against every required checkpoint, independent skeptic agents try to disprove every finding, and a script verifies every quoted piece of evidence. Only the survivors are reported, with a coverage grid. Writes a report under .bughunt/ and never edits code. Use when the user asks to check, scan, audit or analyze an app or codebase for bugs.
argument-hint: "[path] [--mode auto|lean|small|medium|large|max] [--focus \"text\"] [--threshold critical|high|medium|low]"
---

# Bug hunt (read-only)

Run the `bughunt-scan` workflow and report what survives verification.

This skill is strictly read-only. Do not edit, create or delete any file of the app, and do not run the app's tests, builds or scripts. The only files you write are the report files under `.bughunt/`. Do not propose fixes here; that is `/bugfix-plan`.

## 1. Scope

1. Target: the path argument, or the current project root.
2. Run the read-only scope script from this skill's directory: `bash <this skill's directory>/scope.sh <target>` (project install: `.claude/skills/bughunt/scope.sh`; user install: `~/.claude/skills/bughunt/scope.sh`). It prints JSON: `root`, `total_files`, `total_lines`, `files` ([path, lines] pairs), `powerapps`, `skipped_counts` and `skipped_large`.
3. Create the run directory `<root>/.bughunt/runs/<YYYYMMDD-HHMM>-hunt/` and save the scope JSON there as `scope.json`. (When called from `/bugloop`, use the cycle directory it gives you instead.)
4. If `total_files` is 0, stop and tell the user nothing analyzable was found, with the skipped counts.
5. If `powerapps.packed_msapp` lists files, tell the user once: a `.msapp` is a packed zip that cannot be analyzed as-is. They can unzip it and point the hunt at its `Src/*.pa.yaml` files, or use Power Platform Git integration, which keeps `.pa.yaml` source in the repo. Continue with whatever source is present.
6. If `skipped_large` lists files, mention they were excluded as likely generated (over 512 KB; `BUGHUNT_MAX_BYTES` raises the limit).

## 2. Size and cost check

Every checkpoint in the workflow's checkpoint list is a required pass:
- **Every slice:** core logic, edge cases, performance, security, contracts and code health.
- **Slices with screen code** (tagged `ui` by the scope script): interaction, UI feedback and layout hints, and accessibility.
- **Slices with Power Apps source:** the Power Apps checks.
- **Once across the whole codebase:** cross-file contracts, data and API contracts, cross-file security, shared state, and config, plus Power Apps app-wide.
- **Selection scoping:** one agent maps the selection levels and every query or screen that uses them, then checker agents verify each in batches, plus one check of what happens when the selection is switched.

Related checkpoints share an agent to hold cost down.

Tier comes from `total_lines` unless `--mode` is given: small < 3,000 lines, medium < 30,000, large otherwise.

| tier | lines per slice | slice cap | agents per slice | whole-codebase agents | skeptics per bug | extra sweeps |
|---|---|---|---|---|---|---|
| lean | 4,000 | 8 | 1 (all checkpoints together) | 1 (all together) | 1 | none |
| small | 1,500 | 6 | 2, or 3 with screen code | 1 (all together) | 1 | none |
| medium | 2,500 | 24 | 2, or 3 with screen code | 5 (one each) | 3 for critical/high, else 1 | up to 1 |
| large | 3,000 | 48 | 2, or 3 with screen code | 5 | 3 (majority vote) | up to 2 |
| max | 1,500 | 80 | 6, or 9 with screen code (one per checkpoint) | 5 | 5 for critical/high, else 3 | up to 2 |

The per-slice agents are:
- **correctness:** core logic, edge cases and performance;
- **safety:** security, contracts and code health;
- **screen code:** interaction, UI feedback and layout hints, and accessibility.

Other notes:
- Slices with Power Apps source get one more agent, and Power Apps apps get one more whole-codebase agent.
- Selection scoping adds one mapping agent, plus one checker per 8 places that use a selection (at most 30 checkers), plus one switching check. Apps with no selection concept only pay for the mapping agent.
- Warnings and other non-bug findings get one skeptic.
- Extra sweeps re-check every slice with fresh eyes and stop as soon as a sweep confirms nothing new.

**Estimate:** (slices × agents per slice) + whole-codebase agents + scoping agents, plus 1 to 3 skeptics per finding, plus extra sweeps on medium and larger apps. A rough cost is 50k to 100k tokens per agent (Anthropic's demo used about 1.3M tokens for 15 agents).

- small or lean: proceed without asking.
- medium, large or max: show the tier, estimated agent count and rough token range, and ask the user to confirm before launching. Offer `lean` as the cheaper option.

## 3. Launch

Write one to three sentences of app context (what the app does and its main stack) from the README, CLAUDE.md, package.json or manifest. This helps hunters tell intended behavior from bugs.

Call the Workflow tool with `name: "bughunt-scan"` and `args` as a JSON object (not a string):

```json
{
  "root": "<scope.root>",
  "files": "<scope.files, the array as-is>",
  "mode": "<--mode or auto>",
  "focus": "<--focus text, if any>",
  "app_context": "<your 1-3 sentences>",
  "powerapps": "<scope.powerapps>",
  "clean_threshold": "<--threshold or medium>",
  "disable_checkpoints": ["<only if the user asked to skip specific checkpoint ids>"]
}
```

From `/bugloop` also pass `previous_bugs` as the loop instructs. The workflow runs in the background: tell the user it has started and that `/workflows` shows live progress, then wait for the completion notification instead of polling.

## 4. Report

When the workflow completes:

1. If `ok` is false, show the error. If it says the agent types are not loaded, tell the user to start a new Claude Code session (agents in `.claude/agents/` load at session start) and run `/bughunt` again.
2. Save the full result, exactly as returned, as `findings.json` in the run directory.
3. **Run the evidence gate:** `node <this skill's directory>/evidence-gate.mjs <run dir>/findings.json`. This plain script (no AI):
   - checks that each finding's quoted code really appears in the cited file near the cited line (or, for runtime findings, that the screenshot exists and the steps are non-empty);
   - moves failures to `rejected_evidence`;
   - corrects line numbers when the quote is found elsewhere in the same file;
   - recomputes `clean`.

   If `node` is not available, tell the user the evidence could not be checked. Nothing from this run can then enter a fix plan, because the plan step refuses unchecked findings.
4. Write `report.md` in the run directory from the gated `findings.json`, following `report-format.md` in this skill's directory. Include the coverage grid.
5. Reply in chat with:
   - the verdict (CLEAN or NOT CLEAN). Only `bug` findings at or above the threshold block; warnings (such as Power Apps delegation limits) and other non-bug kinds are reported but never block;
   - counts of bugs by severity, warnings and other kinds, plus disputed, refuted and evidence-rejected counts;
   - a table of the blocking bugs (ID, severity, checkpoint, `file:line`, one-line title), then a shorter list of non-blocking findings;
   - coverage: for each checkpoint, how many slices were checked, plus any gaps (failed or unsigned cells). A run with gaps is never called clean;
   - the report path;
   - next step: `/bugfix-plan` to design fixes (nothing is changed until you approve), or `/bugloop` for the full repair loop.
