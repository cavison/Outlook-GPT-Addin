---
name: bughunt
description: Read-only, multi-agent bug hunt of an app or codebase using a dynamic workflow, the method Anthropic used to find 66 of 70 planted bugs where a single agent found 14-27. Fresh-context hunter agents each review one slice of the code, then independent skeptic agents try to disprove every finding, and only the survivors are reported. Writes a report under .bughunt/ and never edits code. Use when the user asks to check, scan, audit or analyze an app or codebase for bugs.
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

Tier comes from `total_lines` unless `--mode` is given: small < 3,000 lines, medium < 30,000, large otherwise.

| tier | lines per slice | hunter cap | cross-cutting hunters | skeptics per finding | rounds |
|---|---|---|---|---|---|
| lean | 4,000 | 8 | 1 | 1 | 1 |
| small | 1,500 | 6 | 1 | 1 | 1 |
| medium | 2,500 | 24 | 3 | 3 for critical/high, else 1 | up to 2 |
| large | 3,000 | 48 | 4 | 3 (majority vote) | up to 3 |
| max | 1,500 | 80 | 4 | 5 for critical/high, else 3 | up to 3 |

One extra cross-cutting hunter is added when Power Apps source is detected. Extra rounds re-hunt each slice through a different lens (edge cases, then security) and stop as soon as a round confirms nothing new.

Estimate hunters as ceil(lines / slice size) + cross-cutting, per round, and skeptics as 1 to 3 per finding. A rough cost is 50k to 100k tokens per agent (Anthropic's demo used about 1.3M tokens for 15 agents).

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
  "clean_threshold": "<--threshold or medium>"
}
```

From `/bugloop` also pass `previous_bugs` as the loop instructs. The workflow runs in the background: tell the user it has started and that `/workflows` shows live progress, then wait for the completion notification instead of polling.

## 4. Report

When the workflow completes:

1. If `ok` is false, show the error. If it says the agent types are not loaded, tell the user to start a new Claude Code session (agents in `.claude/agents/` load at session start) and run `/bughunt` again.
2. Save the full result as `findings.json` in the run directory.
3. Write `report.md` in the run directory following `report-format.md` in this skill's directory.
4. Reply in chat with:
   - the verdict (CLEAN or NOT CLEAN at the threshold) and counts by severity, plus disputed and refuted counts;
   - a table of the confirmed bugs (ID, severity, `file:line`, one-line title);
   - any coverage gap (failed slices, files not reviewed, dropped agents). A run with gaps is never called clean;
   - the report path;
   - next step: `/bugfix-plan` to design fixes (nothing is changed until you approve), or `/bugloop` for the full repair loop.
