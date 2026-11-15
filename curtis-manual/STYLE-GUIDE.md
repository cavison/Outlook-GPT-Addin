# Curtis' Manual — Content & Diagram Spec

Audience: household of 2–6, suburban/small-town, west Michigan (Hudsonville / Ottawa County), USA. Cold winters (zone 6a), lake-effect snow, ice storms, summer heat waves. Plain language a stressed 14-year-old could follow. US units first (metric in parentheses where useful).

## Module file: `modules/<category>/<ID>-<slug>.md`

```
---
id: W-04
title: Disinfect Water with Bleach
category: water
phases: [72h, wk, mo]        # any of: before, 72h, wk, mo, after
time: 5 min + 30 min wait
difficulty: easy              # easy | moderate | skilled
diagram: W-04.svg             # file in diagrams/ (omit if none)
---
One sentence: what this is for and when to use it.

## You need
- items; household things first, then bought gear

## Steps
1. Short imperative step. Number matches callouts in the diagram.
2. ...  (3–8 steps)

## Caution
The mistake that actually hurts people. 1–3 sentences.

## Field note
A lesser-known, verified tip most books skip. Michigan-specific where it helps.

## See also
[[W-05]] [[W-06]]

## Sources
CDC; EPA; MSU Extension   (short names, comma/semicolon list)
```
Optional extra sections (use only when needed): `## Table` (markdown table), `## Michigan notes`, `## Signs` (symptom lists).
Cross-reference any module or chapter with `[[ID]]` — the build turns it into a link with the title.

## Accuracy rules (safety-critical — do not guess)
- Bleach: unscented 6% or 8.25% sodium hypochlorite. EPA: 6% → 8 drops/gal clear water (16 if cloudy); 8.25% → 6 drops/gal (12 cloudy). Wait 30 min; faint chlorine smell.
- Boil: rolling boil 1 minute (3 minutes above 6,500 ft).
- Generator: outdoors, 20+ ft from house (CDC), exhaust away from openings; never in garage.
- Fridge ~4 h closed; full freezer ~48 h, half ~24 h (USDA). Discard perishables above 40°F for 2+ hours.
- Water need: 1 gal/person/day minimum (FEMA); more for heat, nursing, sick.
- Canning: follow USDA Complete Guide only; low-acid foods need pressure canning.
- Michigan: fishing license required for 17+ (Michigan DNR); follow "Eat Safe Fish" guides (MDHHS); hunting/trapping seasons and licenses per DNR.
- Radio: Technician license required to transmit on ham bands (FCC Part 97); emergency exception §97.403. Baofeng UV-5R-type radios are not FCC-certified for FRS/GMRS use.
- If unsure of a number, cite a range and the authority, or tell the reader to check that authority. Never invent statistics.

## Diagram file: `diagrams/<ID>.svg`
- `viewBox="0 0 800 500"`, no width/height attributes, no external fonts/images/scripts. font-family="Arial, Helvetica, sans-serif".
- Black line art, stroke-width 3–4 for objects. Readable in black & white; color only as accent:
  - danger red `#c0392b`, safe/tip green `#2e7d32`, water blue `#2b7bb9` (light fill `#d6eaf8`), heat/fuel orange `#e67e22`, neutral gray `#888`.
- Numbered circle callouts (white circle, black stroke, bold number) matching the Steps; arrows show motion/flow.
- Labels ≥ 16px, minimal words. Show ✔ correct / ✘ wrong side by side when a common mistake exists.
- Draw simple recognizable shapes (buckets, jugs, house, stove, pipes). Accuracy over art.

## Timeline chapter file: `timeline/<ID>-<slug>.md`
```
---
id: A08
title: Water
part: III
---
```
Body: short intro ("What's happening now"), `## Priorities` (ordered list), `## What goes wrong`, `## Gear tiers` (table: Minimum / Better / Serious), `## Day-90 check`, `## Modules to use now` (list of [[ID]]), `## Checklist` (- [ ] items). 600–1200 words. Narrative + decisions; how-to detail lives in modules.
