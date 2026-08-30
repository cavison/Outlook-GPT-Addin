# 2026 Fantasy Football — Aggregated Top 500

A consensus draft board for the 2026/27 NFL season, built 2026-08-27.

## Files
| File | What it is |
|---|---|
| `rankings_2026_top500.csv` | The board: rank, player, position, position rank, team, target round (12-team), confidence band, note |
| `rankings_2026_top500.json` | Same data as JSON |
| `draft-board-500.html` | Filterable web board (overall, per-position and sleeper views, tier strategy, status flags) |
| `on-the-clock.html` | Live draft assistant — log picks, get the position call, round plan and remaining path |
| `fantasy-draft.py` | **Local server** — serves the assistant and writes every pick to a folder. Start here. |
| `Start Draft.bat` | Windows launcher — double-click instead of using a terminal |
| `on-the-clock-local.html` | Standalone offline copy (no server; uses the File System Access API) |
| `on-the-clock-server.html` | The page the server embeds |
| `clock_js.js` / `clock_local.js` | The assistant's engine (hosted and local builds) |
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

## Dual-threat badge
`rush.py` grades quarterbacks on **absolute 2025 standing across all QBs**, not year-over-year change.
Two gates, both required for the `dual` badge:

- **Rushing** — top five among quarterbacks in rushing attempts, rushing yards, or rushing yards per game
  (min. 30 carries)
- **Passing** — a genuine, repeatable passing workload alongside it (~3,200+ yards over a full season, or the
  per-game rate of one)

Clearing the rushing gate but not the passing one earns the `run` badge instead: a runner, not a dual threat.
The CSV carries `rush` (`dual` / `run` / empty), `rushstat` (the numbers behind the grade) and `rushnote`.

The page shows the four 2025 leaderboards the test reads from, so the grade is auditable rather than asserted.

## On the Clock (draft assistant)
A live tool for draft day. Set league size and slot, mark each pick `Gone` or `Mine`, and it recomputes:

- **The call** — which position to take now and the two or three players to take, chosen by *dropoff*: how much
  worse your best option at that position gets by the time you pick again
- **Round plan** — a 16-round strip, forward-simulated from the current board state, updating after every pick
- **Roster** — starters and bench filling in, with empty mandatory slots flagged
- **Alerts** — positional runs, tier cliffs, and the must-fill window for QB/TE/K/D-ST

Scoring is `weight x (log(1 + dropoff) + surplus)`, where `surplus` is how far the best available player has
fallen past the current pick, in rounds. That second term is what stops it recommending a scarce position over
a clearly better player. When your remaining picks equal your empty starting slots it switches to must-fill mode
and only offers positions that complete a legal lineup.

Click any player name — in the call, the available list, or your roster — for a read-only detail card:
board rank, position rank, target round, confidence band, whether he survives to your next pick, the written
case, and the next three at his position with the rank gap. `openCard`/`closeCard` only read state; a static
check in the build asserts neither contains a write, so opening a card cannot disturb the draft.

### Persistence
State persists in `localStorage` on every mutation, so refreshing, closing the tab or opening a card is safe.
There is no per-viewer server storage in the artifact runtime — the available capabilities are `artifact`
(publishes a new version of the page *for everyone*, wrong for a private draft), `downloads`, `mcp` and `self`.
So portability is handled two ways instead:

- a base64 **save code** to copy into another browser or device, restored by pasting it back
- a **Download backup** button (JSON) when the `downloads` capability resolves; hidden when it does not

### Local server (`fantasy-draft.py`) — the recommended way
On Windows, double-click **Start Draft.bat** (it finds Python, checks the version, and starts the server).
Otherwise:

```
python3 fantasy-draft.py              # opens http://127.0.0.1:8712
python3 fantasy-draft.py --dir ~/Documents/fantasy --port 9000 --no-browser
```
Python 3.8+, standard library only. The page is embedded in the script, so it is one file and needs no network.
Every pick is POSTed to `/api/draft` and written atomically to `fantasy-draft-2026.json` in the data folder, with
a rotating snapshot in `history/` at most once a minute (last 60 kept).

Because the draft lives on disk rather than in a browser, any browser on the machine sees the same draft, and
clearing site data or switching browsers loses nothing.

Hardening: binds to `127.0.0.1` only; rejects requests whose `Host` or `Origin` is not local (DNS-rebinding
defence); serves only `/`, `/favicon.ico` and `/api/draft`, so there is no path to the rest of the filesystem;
caps request bodies at 1 MiB; validates the payload shape before writing; writes via a temp file plus
`os.replace` so a crash can never leave a half-written draft.

### Standalone copy (`on-the-clock-local.html`)
A standalone single file with no hosted dependencies. Opened from `file://` in Chrome, Edge or Opera it uses the
File System Access API: pick a folder once and it writes `fantasy-draft-2026.json` there after every pick
(debounced 400 ms) and reads it back on reopen. The directory handle is persisted in IndexedDB where the browser
allows it, so reconnecting is one click; where it is not, the folder is re-picked each session.

A hosted artifact cannot do this — the viewer frame is sandboxed away from the filesystem — which is why this
build exists separately.

Safari and Firefox have no `showDirectoryPicker`; there the folder button is disabled and **Save a copy** /
**Open a draft** cover the same ground through ordinary file download and `<input type=file>`. Those two paths
work in every browser.

## Regenerating
```
cd fantasy-2026 && python3 build.py
```

## Known gaps
- reddit.com and video-transcript hosts were unreachable from the build environment, so community consensus
  enters only second-hand via aggregators that survey it.
- Preseason moves fast. Anything with a status flag (Jeanty, Nabers, Mahomes, Kittle, Jayden Higgins,
  the Cleveland QB job) should be re-checked on draft day.
