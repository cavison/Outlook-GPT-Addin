---
name: bugfix-apply
description: Apply only the fix-plan items the user explicitly approved, on a safety branch with a checkpoint commit, then run the project's own checks and report. Refuses to run without a recorded approval. Use after /bugfix-plan.
argument-hint: "[run dir]"
disable-model-invocation: true
---

# Apply approved fixes

This is the only step in the kit that changes app code, and only the changes the user approved.

## 1. Load and check the approval

- Use the run directory given as an argument, or the newest `.bughunt/runs/*` that has a `fix-plan.json`. When called from `/bugloop`, use the current cycle directory.
- Read `fix-plan.json` and `approval.json`. If `approval.json` is missing or `approved_ids` is empty, stop and tell the user to run `/bugfix-plan` first.
- Approved items with `apply_mode: "manual"` are not applied. List their `manual_steps` for the user to do themselves.
- Approved items the end review marked `reject` or `hold`: confirm with the user once before including them.

## 2. Safety net

In a git repository:
- Run `git status --porcelain`. If anything outside `.bughunt/` is uncommitted, stop and ask the user whether to commit or stash it themselves first, or to continue anyway.
- If the current branch does not start with `bugfix/` or `bugloop/`, create and switch to `bugfix/<run id>` (in a loop, `bugloop/<run id>`) from the current HEAD. Record the base commit.

Outside git: ask the user for permission first, then copy every file listed in the approved items' `files_touched` to `<run dir>/backup/<same relative path>` before changing anything.

## 3. Launch

Call the Workflow tool with `name: "bugfix-execute"` and `args` as a JSON object:

```json
{
  "root": "<scope.root>",
  "items": "<the full approved auto items from fix-plan.json, as-is>",
  "order": "<fix-plan end_review.apply_order, if present>",
  "cycle": "<cycle number>"
}
```

Wait for the completion notification instead of polling.

## 4. Run the project's checks

Run the verification commands recorded in the plan (tests, lint, typecheck, build) that exist in the project. If dependencies are not installed, ask before installing them. Capture pass/fail and the relevant failure output.

## 5. Record and commit

- Save the workflow result plus check results as `apply-result.json` in the run directory, and append an "Applied changes" section to `fix-plan.md`: what was applied, deviations, skipped items, checker problems and check results.
- In git: stage only `files_changed` from the result plus the run directory, then commit with a message like `bughunt: apply approved fixes B1, B4 (cycle 2)`. Never push unless the user asks.

## 6. Report

Tell the user:
- what was applied, skipped or deviated;
- the reviewer's `check_problems` and any failing check, stated plainly. If there are problems, offer to revert this commit; revert only if they say so;
- `git diff --stat <base>..HEAD`;
- next step: `/bughunt` to re-test (or `/bugloop` continues automatically).
