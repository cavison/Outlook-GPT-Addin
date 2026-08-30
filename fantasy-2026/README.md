# 2026 Fantasy Football — Aggregated Top 500

A consensus draft board for the 2026/27 NFL season, built 2026-08-27.

## Files
| File | What it is |
|---|---|
| `rankings_2026_top500.csv` | The board: rank, player, position, position rank, team, target round (12-team), confidence band, note |
| `rankings_2026_top500.json` | Same data as JSON |
| `draft-board-500.html` | Filterable web board (overall, per-position and sleeper views, tier strategy, status flags) |
| `top150.py` / `tail.py` / `notes.py` / `sleepers.py` / `rush.py` / `build.py` | Source data and the script that assembles the board |

## Method
Ranks 1–150 reconcile the expert boards that were live on 2026-08-27: ESPN (Mike Clay 8/19, Field Yates 8/24,
staff tiers), 4for4 via Bleacher Nation 8/25, PFF, NFL.com, Yahoo, The Big Lead 8/24, RotoBaller and FantasyPros,
plus camp and injury reporting.

Ranks 151–300 are role-based inference anchored to those same sources. Ranks 301–500 are deep-league and dynasty
stash territory — team assignments there are a research starting point, not a verified depth chart.

The `confidence` column encodes exactly that: `High` (1–150), `Medium` (151–300), `Low` (301–500).

## Sleepers
`sleepers.py` holds 30 undervalued players grouped by *why* the market is missing them — post-hype, role
changed but price didn't, second-year leap, somebody else's injury, buried by a bigger name, free in the last
two rounds — plus a short list of cheap players that are traps rather than values. The CSV carries these as the
`sleeper`, `cost` and `case` columns.

## Rushing badge
`rush.py` grades quarterbacks with real ground production on a 1-3 scale, from 2025 rushing yards per start
(Warren Sharp's per-start table) plus rushing-touchdown equity. Level 3 means rushing carries the weekly floor,
2 means a real rushing floor, 1 means goal-line or occasional. The CSV carries `rush` and `rushnote`.

## Regenerating
```
cd fantasy-2026 && python3 build.py
```

## Known gaps
- reddit.com and video-transcript hosts were unreachable from the build environment, so community consensus
  enters only second-hand via aggregators that survey it.
- Preseason moves fast. Anything with a status flag (Jeanty, Nabers, Mahomes, Kittle, Jayden Higgins,
  the Cleveland QB job) should be re-checked on draft day.
