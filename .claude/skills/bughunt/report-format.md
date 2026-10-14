# Report formats

Shared by `/bughunt`, `/bugfix-plan`, `/bugfix-apply` and `/bugloop`. Write plain Markdown. Quote code exactly as it appears in the results; never invent details the workflow did not return.

## report.md (hunt result)

```markdown
# Bug hunt: <project folder name>, <YYYY-MM-DD HH:MM>

**Verdict:** CLEAN | NOT CLEAN. Blocking: bugs of severity <threshold> and above. Warnings, code health, accessibility and cosmetic findings are reported but never block.
**Scope:** <files> files, <lines> lines · tier <tier> · <slices> slices of ~<slice_lines> lines · <required_slice_passes> required slice passes + <whole_codebase_passes> whole-codebase · <rounds_run - 1> extra sweep(s)
**Agents:** <hunters_run> hunters, <skeptics_run> skeptics (<agents_used> total)
**Evidence check:** <passed>/<checked> findings passed; <rejected> rejected; <lines_corrected> line numbers corrected

## Summary

| Bugs by severity | Count |
|---|---|
| Critical | n |
| High | n |
| Medium | n |
| Low | n |

Warnings: n · Code health: n · Accessibility: n · Cosmetic: n (only kinds that occurred)
Disputed (skeptics split): n · False alarms removed by skeptics: n · Rejected for missing evidence: n · Duplicate reports merged: n

## Coverage grid

Every slice must be checked against every checkpoint that applies to it. ✓ checked · – not applicable · off = turned off for this run · ✗ failed (agent did not complete) · ? not signed off.

| Slice | Files | <checkpoint name> | <checkpoint name> | … |
|---|---|---|---|---|
| S1 | <first file> (+n more) | ✓ | ✓ | – |

Whole codebase: <checkpoint name> ✓ · <checkpoint name> ✓ · … (same symbols)

Gaps: <coverage.gaps, or "none">. Any ✗ or ? means the run cannot be called clean.
(For more than 30 slices, show the per-checkpoint totals from coverage.summary instead of every row, and list only the rows that have a gap.)

## Blocking bugs

### B1 · HIGH · <title>
- **Where:** `<file>:<line>` (line corrected from <n>, if the evidence gate corrected it)
- **Checkpoint:** <checkpoint_name>
- **What is wrong:** <description>
- **Trigger and outcome:** <trigger>
- **Evidence:**
  ```
  <evidence>
  ```
- **Verification:** <votes>. <reproduction, if any>
- **Found by:** <found_by><, also_found_by if any>
- **Severity:** <severity> (hunter said <hunter_severity>, if different)

## Other bugs (below the threshold)
<same layout>

## Warnings (do not block)
<same layout for each W-item; then sections for code health (H), accessibility (A) and cosmetic (V) findings if any>

## Disputed: needs your judgment
<same layout for each D-item, plus each skeptic's reason>

## Regression check of previous fixes
<only in loop cycles 2+: table of bug ID, status, evidence, new_problem>

## Selection map
<from maps.scoping. If found is false: one line saying no selection concept was found, and why.>
- Levels: <levels>
- Hierarchy lives in: <hierarchy>
- Current selection stored in: <selection_state>
- Switching handled by: <change_handlers>
- Places that depend on the selection: <consumers> (checked in <batches> batches). List them in a collapsed <details> block.

## Large images (from the scope scan)
<scope.json large_images: path and size in KB, as performance warnings. Omit the section if none.>

## Coverage details
- Files hunters reported they could not review: <list, or none>
- Agents dropped by caps: <list, or none>
- Errors: <list, or none>

<details><summary>Rejected: no valid evidence (n)</summary>

These findings were removed by the evidence-gate script and cannot enter a fix plan.

| Claim | Where | Why rejected |
|---|---|---|

</details>

<details><summary>False alarms removed by skeptics (n)</summary>

| Claim | Where | Why refuted |
|---|---|---|

</details>
```

## ux-report.md (browser check result, from /uxcheck)

```markdown
# UX check: <project folder name>, <YYYY-MM-DD HH:MM>

**Verdict:** CLEAN | NOT CLEAN. Blocking: bugs of severity <threshold> and above. Cosmetic, accessibility and warning findings are reported but never block.
**App:** <base_url> · signed in: yes/no · test selection: "<test_selection>" selected | not found (add one!) | no selection control
**Screens:** <screens_tested> at <viewports> · **Agents:** <agents_used> · **Evidence check:** <passed>/<checked> passed

## Side effects
- Not clicked (reach real people or systems): <avoided_by_rule, or "none found">
- Found by the code scan: table of action, screen, effect, target, file:line
- Risks testers noticed while testing: <list>
- Test records created in "<test_selection>": <list> (safe to delete)

## Summary
<bugs by severity, then counts for cosmetic, accessibility, warning; disputed, refuted, evidence-rejected, duplicates merged>

## Coverage grid

| Screen | Visual and layout | Functional and interaction | Accessibility |
|---|---|---|---|
| P1 <screen> | ✓ | ✓ | ✓ |

✓ checked · – not applicable · limited (could not fully test; for example no test property) · unreached · ✗ failed · ? not signed off · off
Selection switching: <status>. Gaps: <coverage.gaps or "none">.

## Blocking bugs

### UB1 · HIGH · <title>
- **Screen / viewport:** <screen> · <viewport> · <url>
- **Steps:** numbered list
- **Expected / actual:** <expected> / <actual>
- **Screenshot:** ![<title>](<path relative to this report>) and replay: ![replay](<replay_screenshot>)
- **Verification:** <votes>. <reasons>
- **Suspected code:** <file:line, if given>

## Cosmetic (UV), accessibility (UA) and other findings
<same layout, grouped by kind>

## Disputed: needs your judgment
## Regression check of previous fixes
<details> blocks: rejected for missing evidence; false alarms removed by replay
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
