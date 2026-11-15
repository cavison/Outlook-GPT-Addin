# Curtis' Manual — 90 Days Without Power

A grid-down field manual for west Michigan households, kept as small editable files and built into PDFs.

## The finished books (in `output/`)
| File | Use |
|---|---|
| `Curtis-Manual-PRINT-8.5x11.pdf` | Print at home or a print shop; binder-friendly, readable in black & white |
| `Curtis-Manual-PHONE.pdf` | Narrow pages, big text — open on iPhone in **Books** (Share → Books) |
| `Curtis-Manual-CARDS-half-letter.pdf` | Cut-out emergency cards (Quick Start, bleach, bleeding, CPR, radio card…) |

## How it's organized
- `book.yaml` — the table of contents: chapter order, module codes and titles.
- `timeline/` — **Book A**, chapters by phase (Before → 72 hours → Weeks → Months → After).
- `modules/<category>/` — **Book B**, one short how-to per file (W = water, H = heat, M = medical…).
- `diagrams/` — one drawing per module (`W-04.svg` goes with module W-04).
- `STYLE-GUIDE.md` — the format every page follows, plus safety-number rules.
- `build/` — the generator.

## To add or change something
Easiest: open Claude (on your laptop or claude.ai/code) in this folder and say, e.g.
*"Add a module G-30 on smoking fish in a cardboard box smoker, then rebuild."*

By hand:
1. Edit the text file (or copy an existing module as a template).
2. New module? Add one line to `book.yaml` under `modules:` (e.g. `G-30: Cardboard Box Smoker`).
3. Rebuild (needs Node.js once: `cd build && npm install`):
   `node build/build.js` — makes all three PDFs. Contents, links and the topic index update automatically.
4. Check `output/build-warnings.txt` for typos in codes or missing diagrams.

## Before you rely on it
Phone numbers, radio frequencies and regulations are marked "✔ checked <date>". Re-verify them yearly. This is preparedness information, not medical or legal advice.
