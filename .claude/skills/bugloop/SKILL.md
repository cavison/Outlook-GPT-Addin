---
name: bugloop
description: Full repair loop until clean. Read-only multi-agent bug hunt, then a fix plan with critics and an end-of-plan review, then the user's approval, then apply approved fixes, then re-hunt with regression checks. Repeats until no bugs at or above the threshold (default medium) remain. Pauses for the user's approval every cycle.
argument-hint: "[path] [--max-cycles 5] [--mode auto|lean|...] [--threshold medium] [--focus \"text\"] | resume | status | stop"
disable-model-invocation: true
---

# Bug loop: hunt → plan → approve → apply → re-hunt, until clean

You orchestrate the cycle using the other kit skills' instructions. Read each one's `SKILL.md` when you reach its step (in a project install they are in `.claude/skills/`):
`bughunt` (hunt and report), `bugfix-plan` (plan and approval), `bugfix-apply` (apply and checks).

## Sub-commands

- `status`: print `SUMMARY.md` of the active loop.
- `stop`: set the active loop's status to `stopped (user)`, update SUMMARY.md, and stop.
- `resume`: read `.bughunt/ACTIVE_LOOP` and that loop's `state.json`, then continue from `stage`.
- Anything else starts a new loop. If `.bughunt/ACTIVE_LOOP` points to a loop that is still running, ask whether to resume it or start fresh.

## State

The loop directory is `<root>/.bughunt/runs/<YYYYMMDD-HHMM>-loop/`. Write its path to `<root>/.bughunt/ACTIVE_LOOP`. Keep `state.json` there, updating it after every stage so the loop can resume in a later session:

```json
{
  "target": "<path>", "root": "<abs root>", "branch": "bugloop/<run id>", "base_commit": "<sha>",
  "threshold": "medium", "mode": "auto", "max_cycles": 5, "focus": null,
  "cycle": 1, "stage": "hunt | plan | approve | apply | done",
  "status": "running | clean | stopped (<reason>)",
  "attempts": { "<bug signature>": [{ "cycle": 1, "bug_id": "B2", "attempt": "<final_change>", "outcome": "still-present" }] },
  "history": [{ "cycle": 1, "blocking": 7, "by_severity": {}, "approved": [], "applied": [], "checks": "pass | fail | none", "new": 0, "still_present": 0 }]
}
```

A bug signature is `<file>::<title in lower case>`. Use it to recognize the same bug across cycles; line numbers move.

Each cycle uses its own subdirectory `cycle-NN/` for `scope.json`, `findings.json`, `report.md`, `fix-plan.json`, `fix-plan.md`, `approval.json` and `apply-result.json`. Keep `SUMMARY.md` (format in the bughunt skill's `report-format.md`) up to date at the loop root.

## Start

1. Record `root`, the git `base_commit`, and the settings. Defaults: threshold medium, mode auto, max 5 cycles.
2. Git safety comes from the `bugfix-apply` rules: clean working tree, then branch `bugloop/<run id>`. Do this before cycle 1's apply step, not before the hunt; hunts are read-only.
3. Tell the user, in one short message, how the loop works: it hunts, plans and then **pauses for your approval every cycle**; it never pushes; and it stops when clean, after max cycles, or when it stops making progress.

## Each cycle

**A. Hunt.** Follow the bughunt skill, steps 1 to 4, writing into `cycle-NN/`. Ask for cost confirmation in cycle 1 only. Later cycles reuse the approval unless the tier went up. From cycle 2 on, pass `previous_bugs`: every bug applied in the previous cycle, as `{id, title, file, line, description, fix_summary: <final_change>}`.

**B. Evaluate** (update state and SUMMARY.md):
- Regressions with status `still-present` or `partially-fixed`: add a failed attempt under the bug's signature in `attempts`.
- New bugs whose file was changed in the previous cycle: mark them "possibly introduced by the last fix" in the report and the chat summary.
- **Stubborn bugs:** a signature with 2 or more failed attempts is excluded from automatic planning. List it for the user with its attempt history, and ask whether to try again with a different approach, accept it, or fix it themselves.
- Stop if any of these holds:
  - `clean` is true: status `clean`. Go to Finish.
  - `cycle` is at least `max_cycles`: status `stopped (cycle limit)`.
  - The blocking count has not gone down for 2 cycles in a row: status `stopped (not converging)`. Tell the user the loop is not making progress and show what keeps coming back.
  - Every remaining blocking bug is manual, stubborn or on hold: status `stopped (needs you)`, with the list.
  - Coverage was incomplete twice in a row: status `stopped (coverage)`, with the failed slices.

**C. Plan.** Follow the bugfix-plan skill, steps 1 to 5, for the blocking confirmed bugs that are not stubborn. Pass `history` from `attempts`, keyed by bug ID, so planners do not repeat failed approaches.

**D. Approve.** Follow the bugfix-plan skill, step 6. This gate is mandatory every cycle. Never skip it, never pre-approve, and never infer approval. If the user approves nothing, status `stopped (nothing approved)`.

**E. Apply.** Follow the bugfix-apply skill. If the reviewer reports `check_problems`, or the project's checks fail, pause and ask the user: "revert this cycle's commit", "continue to re-hunt anyway", or "stop". Do what they choose.

**F.** Increment `cycle`, set `stage` to `hunt`, and go to A.

## Finish

1. Update SUMMARY.md with the final status and the cycle table.
2. Remove `.bughunt/ACTIVE_LOOP` if the status is `clean` or `stopped (user)`; keep it for other stops so `resume` works.
3. Commit the loop directory on the loop branch.
4. Tell the user:
   - the outcome and why the loop stopped;
   - the branch name and its commits (`git log --oneline <base_commit>..HEAD`);
   - bugs fixed per cycle;
   - what remains (low-severity, disputed, manual, stubborn);
   - an offer to push the branch or open a pull request. Do neither unless asked.

Reports live in the working tree. In a cloud session, unpushed work is lost when the session ends, so mention pushing if the loop ran in the cloud.
