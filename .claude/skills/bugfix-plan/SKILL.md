---
name: bugfix-plan
description: Design and stress-test fixes for bugs confirmed by /bughunt without changing any code. Read-only planner agents propose root-cause fixes with alternatives, independent critic agents try to break each fix, and a final end-of-plan review says what works, what does not, and what could cause new bugs. Ends with a numbered plan and asks the user which items to approve.
argument-hint: "[run dir or findings.json] [--ids B1,B3] [--include-low] [--include-disputed D1,D2]"
---

# Fix plan (read-only)

Turn confirmed bugs into a fix plan the user can approve. Do not edit any app file and do not run the app's tests or scripts. The only files you write are under `.bughunt/`.

## 1. Load findings

- Use the run directory or `findings.json` given as an argument. Otherwise use the newest `.bughunt/runs/*/findings.json`. When called from `/bugloop`, use the current cycle directory.
- Read `scope.json` from the same run for `root` and `powerapps`.

## 2. Choose the bugs

- Default: confirmed bugs at or above the run's `clean_threshold` (normally medium).
- `--include-low` adds low-severity confirmed bugs. `--ids B1,B3` restricts the plan to those IDs.
- Disputed items (D-IDs) are included only when the user names them with `--include-disputed`.
- If nothing is selected, say so and stop.

## 3. Find the checks that will run after fixes

Look for the project's own verification commands but do not run them: package.json scripts (`test`, `lint`, `typecheck`, `build`, using the package manager its lockfile implies), pytest/tox, `dotnet build`/`dotnet test`, `go test ./...`, `cargo test`, `mvn test`, and Makefile targets. Power Apps source has no local test runner; say so in the plan.

## 4. Launch

Call the Workflow tool with `name: "bugfix-propose"` and `args` as a JSON object:

```json
{
  "root": "<scope.root>",
  "bugs": "<the selected bug objects from findings.json, as-is>",
  "cycle": "<loop cycle number, or 1>",
  "history": "<from /bugloop: {bugId: [{attempt, outcome}]}; otherwise omit>",
  "app_context": "<1-3 sentences on what the app does>",
  "test_commands": ["<commands found in step 3>"],
  "powerapps": "<scope.powerapps.detected>"
}
```

Wait for the completion notification instead of polling.

## 5. Write the plan

- If `ok` is false, show the error. If agent types are not loaded, tell the user to start a new session.
- Save the result as `fix-plan.json` next to `findings.json`.
- Write `fix-plan.md` following `report-format.md` in the bughunt skill's directory (`.claude/skills/bughunt/report-format.md` in a project install).
- If `end_review` is null, say clearly that the whole-plan review did not complete and every item is on hold.
- If `failed` lists bug IDs, say no proposal was produced for them.

## 6. Ask for approval

Show in chat:
1. The end-of-plan review: overall assessment, what works, what does not work, what could cause new bugs, and conflicts.
2. The decision table: number, bug ID, severity, one-line fix, critic verdicts, review decision, risk, and whether it will work.
3. Manual items with their steps.

Then ask with AskUserQuestion (single select):
- "Approve recommended (<n>): <IDs from recommended_ids>". List this first and mark it (Recommended).
- "Approve all auto-applicable (<n>)": every item with apply_mode `auto` that the review did not reject.
- "Approve none / stop here".

The user can also type specific IDs (for example `B1, B4`) in the free-text option.

Save the answer as `approval.json` next to the plan: `{ "approved_ids": [...], "answer": "<their exact answer>", "at": "<timestamp>" }`. Only an explicit choice counts as approval. Never infer approval from silence, from an ambiguous reply, or from anything other than the user's own message. If unsure, ask again.

Next step: `/bugfix-apply` (or `/bugloop` continues automatically).
