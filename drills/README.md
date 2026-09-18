# Cottage service drills

`drills.html` is the published drills artifact: a teach-then-test walkthrough of the
cottage/villa service benchmark. It is self-contained — no build step, no network
calls except the Google Fonts stylesheet and the outbound verification links.

## What it covers

15 chapters. Two set up the market shape, nine cover operators one at a time, four
cover money, tiers, what our own leaders committed to on the 17 September call, and
what not to say in the room. 69 learn/drill pairs and a boss round per chapter.

A DOSSIERS mode holds a browsable profile per operator: the communities, the unit
counts, and function-by-function what that operator actually lists, with the phrases
and which communities they came from.

## Sources

Every card carries the sources behind it, graded:

- `OPERATOR` — the operator's own published words, exact-phrase verified
- `INTERNAL` — one of the four internal source documents, as reported to us
- `OUR MATH` — our own arithmetic over an internal source
- `THE CALL` — the 17 September call, by speaker and timestamp

Links marked OPEN PAGE go to the page itself. Links marked RUN SEARCH run the
exact-phrase query that confirms the quote, which is the check that was actually
run. Where no public page was captured — which is the case for the Trilogy, Five
Star, Arrow and Life Care Services aggregations, all of which rest on the October
2023 listing research — the panel says so instead of guessing a URL.

## Rebuilding

Counts and community lists in the dossiers are generated, not typed:

    python3 build/gen_doss.py        # dossiers.json -> doss.js

`build/patch_drills.py` and `build/patch2.py` apply the operator chapters, the
source panel and the dossier mode to the previous version of the page. They are
kept for provenance; the published page is `drills.html`.
