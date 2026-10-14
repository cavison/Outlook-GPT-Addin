# Report formats

Shared by `/bughunt`, `/bugfix-plan`, `/bugfix-apply` and `/bugloop`. Write plain Markdown. Quote code exactly as it appears in the results; never invent details the workflow did not return.

## report.md (hunt result)

```markdown
# Bug hunt: <project folder name>, <YYYY-MM-DD HH:MM>

**Verdict:** CLEAN | NOT CLEAN (blocking threshold: <threshold> and above)
**Scope:** <files> files, <lines> lines · tier <tier> · <slices> slices of ~<slice_lines> lines · <rounds_run> round(s)
**Agents:** <hunters_run> hunters, <skeptics_run> skeptics (<agents_used> total)

## Summary

| Severity | Confirmed |
|---|---|
| Critical | n |
| High | n |
| Medium | n |
| Low | n |

Disputed (skeptics split): n · False alarms removed by skeptics: n · Duplicate reports merged: n

## Confirmed bugs

### B1 · HIGH · <title>
- **Where:** `<file>:<line>`
- **What is wrong:** <description>
- **Trigger and outcome:** <trigger>
- **Evidence:**
  ```
  <evidence>
  ```
- **Verification:** <votes>. <reproduction, if any>
- **Found by:** <found_by><, also_found_by if any>
- **Severity:** <severity> (hunter said <hunter_severity>, if different)

## Disputed: needs your judgment
<same layout for each D-item, plus each skeptic's reason>

## Regression check of previous fixes
<only in loop cycles 2+: table of bug ID, status, evidence, new_problem>

## Coverage
- Complete: yes/no
- Failed slices: <list, or none>
- Files hunters reported they could not review: <list, or none>
- Agents dropped by caps: <list, or none>
- Errors: <list, or none>

<details><summary>False alarms removed (n)</summary>

| Claim | Where | Why refuted |
|---|---|---|

</details>
```

## fix-plan.md (plan result)

```markdown
# Fix plan: <project>, cycle <n>, <YYYY-MM-DD HH:MM>

## End-of-plan review
**Overall:** <overall_assessment>
**What works:** bullets
**What does not work:** bullets
**What could cause new bugs:** bullets
**Conflicts and ordering:** bullets (bug IDs, issue, resolution)
**Recommended apply order:** B3 → B1 → …

## Decision table

| # | Bug | Severity | Proposed fix (one line) | Critics | Review decision | Risk | Will it work? |
|---|---|---|---|---|---|---|---|

## Details

### B1 · <title>
- **Root cause:** …
- **Options considered:** table of option / pros / cons
- **Recommended change:** summary, why, then each edit with file, location, before/after
- **Callers checked:** …
- **Side-effect risks:** …
- **Critics:** verdict per lens, problems, amendments
- **End review:** decision, final change, amendments, rationale

## Manual items (do these yourself)
<apply_mode "manual" items with their manual_steps; for Power Apps, steps in Power Apps Studio>
```

## SUMMARY.md (loop progress, `/bugloop` only)

```markdown
# Bug loop: <project>, started <date>
Branch: `<branch>` · Threshold: <threshold> · Max cycles: <n> · Status: running | clean | stopped (<reason>)

| Cycle | Blocking bugs found | Approved | Applied | Checks | New since last cycle | Still present after fix |
|---|---|---|---|---|---|---|
```
