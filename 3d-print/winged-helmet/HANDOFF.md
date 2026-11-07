# Winged varsity helmet: handoff

A full-size, wearable winged varsity helmet (navy / gold / white) printed on a **Flashforge AD5X** with **Orca Slicer**. This document brings a new Claude session up to speed. It was written at the end of a cloud session (November 7, 2026). Read all of it before changing anything.

Everything lives in this folder, `3d-print/winged-helmet/`, on branch `claude/3d-print-stl-dev-tw1umg` of `cavison/Outlook-GPT-Addin`:

| Path | What it is |
|---|---|
| `winged_helmet_AD5X.3mf` | **Main Orca project**: the whole helmet on 14 plates, with the thicker band and the straight wing mounts already swapped in. |
| `band_reprint_AD5X.3mf` | One navy plate: the three thicker band pieces to print again (about 4 h). |
| `wing_mounts_straight_AD5X.3mf` | One navy plate: both new wing mount blocks (about 2 h). |
| `winged_helmet_print_guide.md` | Print guide: plate table, update notes, wing assembly. |
| `thicker_band.jpg`, `straight_wings.jpg` | Pictures of the two latest changes. |
| `source/` | **Everything needed to rebuild or change parts**: scripts, the OpenSCAD model, every generated part, and the data the scripts read (details below). |

## 1. Hard rule: these parts are already printed and must not change

The user has printed these parts. Any change must keep every hole, peg, key and mating surface they use exactly where it is.

- **Shell front and shell back** (plates 1 and 2): this is the most expensive part. Its peg holes are fixed and include the holes for the band pegs, the seam dowels, the wing-mount pegs, the cheek-guard and neck snap windows, and the nose-clip windows.
- **The 7 seam dowel pins.**
- **Cheek guard L** (plate 2).
- **Front H badge.**
- **The round wing medallions** ("the circular left and right medallions"). Treat all four as frozen: front R/L with the eagle, back R/L with the dovetail key and anti-twist peg. The back medallion's key decides where the mount socket goes.
- **Band navy F, Back V navy, Band navy L** (old 1 mm versions) were printed but snapped or printed badly. They are replaced by `band_reprint_AD5X.3mf`.
- **Wing mount R** (old, toed-in version) was printed and is replaced by `wing_mounts_straight_AD5X.3mf`.
- The fit-test rings were printed; the user said **the size is OK**.

Ask the user which other plates they have printed before touching anything else. Plates 3 to 14 should be assumed not printed unless they say otherwise.

How the last two changes respected this: both proved compatibility by rebuilding the old part and comparing it with the printed file before building the new one. Do the same for any future change.
- **Thicker band:** `band_thicken.py` checks all 44 band and V pegs against open holes in the printed shell.
- **Straight mounts:** `mount2_build.py` reproduces the printed mount 100% and reuses its pegs unchanged.

## 2. Current design (numbers that matter)

- **Head and fit:**
  - 579 mm round (hat size 7 1/4), shape ratio 1.24, brow to crown 120 mm.
  - Padding room: 23 mm at the sides, 28 mm front and back, 20 mm on top.
  - Inside of the helmet: 210 x 259 mm at the brow line, 140 mm high.
- **Shell:** 2.4 mm wall, outside 215 x 265 mm. Each half is about 216 mm wide on the bed, so plates 1 and 2 have no brim (glue stick).
- **Band:** three stacked layers on the shell: white 1.2 mm, gold 1.2 mm, navy 2.0 mm (it was 1.2 / 1.0 / 1.0; it changed on Nov 6). Each piece has 3 mm press-fit pegs into the shell. The nose clip sits on the band, so it moved out 1.2 mm with it; its tongue and snap bumps are unchanged.
- **Wings (v2, hub and feathers):**
  - Feathers F1 to F9 and tips A and B snap into an upper and a lower collar.
  - The collars' hidden plates half-lap into one disc, which is clamped between a front medallion (with pegs) and a back medallion.
  - The back medallion's dovetail key slides down into a mount block pegged to the shell.
  - Feathers are 6.4 mm and print show face down, with the tab on the bed. Collars are 8 mm; medallions 4 mm each.
  - Tabs are 3.6 mm thick and 14 to 26 mm deep. Snap fingers have a long lead-in and a steep catch.
  - Tip B is the only wing piece with supports.
  - Colour goes 2.4 mm deep for white and 1.6 mm for gold on both faces. The user says 1 mm is not enough: navy shows through.
  - Feathers, tips and medallions are separate R and L prints; the collars are shared (turned over for the left).
- **Wing angle:** since Nov 7 the wings run **parallel to the side of the head** (yaw 0, was 15 deg toe-in). Each wing turned about its dovetail key, so the medallions did not move. The **4 deg outward lean is unchanged** (see open items). The straight placement matrix is in `source/ref2/place_straight.npy`.
- **Printer and slicer:**
  - Bed 220 x 220 mm, but keep pieces within **210 x 210**.
  - Purge line at the back edge (keep 3.5 mm clear). Prime tower in the back-left corner (x 10 to 66, depth 28) on multi-colour plates.
  - IFS slots: **1 navy, 2 white, 3 gold, 4 spare**.
  - Orca profiles: printer "Flashforge AD5X 0.4 nozzle", process "0.20mm Standard @FF AD5X", filament "Flashforge PLA Basic @FF AD5X".
- **Plates in the main project** (do not renumber; the user tracks prints by plate number):
  01 navy, shell front + 9 more · 02 navy, shell back + 3 more · 03 navy, neck plate + 5 more · 04 navy, wing mount L · 05 white, band white F + 10 more · 06 gold, crest gold back + 6 more · 07 gold, cheek frame L + 3 more · 08 to 14 multi-colour, wing collars, feathers, tips and medallions.

## 3. How the work is done (the user's preferences)

- **Talking to the user:**
  - When something is unclear, ask before building; don't produce big outputs that may need redoing.
  - Show a picture before a visible design change, and give a short picture of the result after.
  - The user likes a question weighed from several angles (analysis, risks, practicality, the human side, precedent, long term) before getting one clear recommendation.
- **Design rules:**
  - Every joint is pegged or snapped, never glue alone (glue may be added on top).
  - Single-colour items go on single-colour plates; keep colour swaps down.
- **Handing over files:**
  - The user opens files in Orca with **File > Open Project** (not Import, which loses the plates).
  - Always give the **full local path** of every file they need to open. They are on Windows.
- **Reprints:** for a change to an already-printed plate, build a **small separate reprint project** and also swap the piece into the main project **in place**: same plate, same spot, same settings. Never repack the main project.

## 4. Setting up `source/` on this computer

All scripts expect **`source/` to be the working directory**; paths inside them are relative to it.

1. Python 3.12 or newer. Create a virtual environment inside `source/` (it is git-ignored) and install `source/requirements.txt`. The libraries are numpy, trimesh, manifold3d, shapely, scipy, pillow, scikit-image, rtree, networkx and reportlab; all have Windows wheels.
2. **OpenSCAD** (2021.01 was used; newer is fine) is needed only to regenerate base parts from `helmet/winged_helmet_v23.scad` and for pictures. Example (PowerShell):
   `openscad -D 'build="full"' -D 'part="bandL_navy"' -D 'BL_T=[1.2,1.2,2.0]' -o helmet/out_v23/band2/bandL_navy.stl helmet/winged_helmet_v23.scad`
   On Linux the cloud session wrapped renders in `xvfb-run -a`; Windows doesn't need that.
3. **PrusaSlicer** (optional) is used only for print-time estimates with `ps/base.ini`.
4. Orca's Flashforge profiles are bundled in `source/orca_profiles/` (`make_project_config.py` reads them; override with the `ORCA_FF_PROFILES` environment variable).
5. **Sanity check:** `python validate_3mf.py pkg/winged_helmet_AD5X.3mf` should print `errors: 0` and `spacing problems: 0`. `python mount2_build.py` takes about a minute. It should print `old right mount rebuilt ... shared 100.000%` and `pegs vs printed shell: old 7.75 mm3, new 7.75 mm3`. It rewrites `helmet/out_v23/print_mount2/` with identical parts.

## 5. Where the geometry lives (`source/helmet/out_v23/`)

| Folder | Contents | Status |
|---|---|---|
| `print/` | Shell halves, seam dowel, cheek guards, cheek H and rivets, neck plate, H badge, original band, crest, cheek frames, nose, old wing mounts | **Shell, dowel, cheek guard L and H badge here are the printed truth.** Band, crest, cheek frame, nose and mount files here are superseded. |
| `print_band2/` | Thicker band pieces, back V inserts, crest, cheek frames, nose clip, panel and pin | Current |
| `print_mount2/` | Straight wing mounts R and L, plus `oriented/` (as placed on the bed) | Current |
| `print_wing2/` | v2 wing pieces: `wing2_<piece>[_L]_<colour>.stl`, already in print orientation | Current |
| `band2/` | Raw thick band layers exported from the OpenSCAD model | Input to `band_thicken.py` |
| `*.stl` in `out_v23/` | Base pieces exported from the OpenSCAD model, plus `solid_out.stl` (the helmet's outer solid) | Inputs |
| `../out_v22/shell_nose.stl` | Plain shell used for surface lookups | Input |

`source/pkg/` holds copies of the projects and all the picture sheets (`step*.jpg`). The newest sheets are `step16_feather_tabs.jpg`, `step17_fit_rings.jpg`, `step18_thicker_band.jpg` and `step19_straight_wings.jpg`. `source/ref2/` holds data the scripts read: wing regions and artwork (`hub_regions.pkl`, `layered_concept.pkl`), orientations, print times, the plate list (`plates.json`), the packing cache, the joint order and the straight placement.

## 6. Scripts: what to run and what NOT to run

**Do not run these as they are.** They would overwrite printed-part files or repack the main project:
- `mount_build.py`: the original mount builder. It **cuts new holes into `print/shell_*.stl`**.
- `conn_build.py` with its normal output folder: it regenerates every piece in `print/`, including the shell. `band_thicken.py` shows the safe way: it runs it redirected into `print_regen/` and compares the result with the printed files.
- `plates_build.py`: it repacks all 14 plates from `print/`, which still holds the old band and old mounts. That would undo the swaps and renumber plates. It is kept for reference; `make_project_config.py` (project settings) is still used by the small-project builders.

**Current pipeline:**
- `wing2_build.py`: v2 wing pieces into `print_wing2/`. It is safe, but the medallion geometry must not change.
- `band_thicken.py` then `band_yield.py`: thicker band into `print_band2/`, with proofs against the printed shell.
- `mount2_build.py`: straight mounts into `print_mount2/`.
- `patch_band_3mf.py`: swaps changed pieces into the main project in place, using the same rigid move as the old piece. The mount swap was done the same way with the orientation recomputed.
- `make_band_reprint.py`, `make_mount_plate.py`: small one-plate reprint projects. Copy one of these for the next reprint.
- `validate_3mf.py <file>`: XML, objects, plates, bed bounds and spacing check. Run it on every project before handing it over.
- **Checks:**
  - `band_collide.py`: band against every other part.
  - `wing_parallel_check.py`: wing clearance to the helmet.
  - `wing2_overhang.py <folder> <prefix>`: unsupported areas when printed.
  - `wing2_fit2.py`: wing clearance per piece. It still uses the old toed-in placement; switch it to `ref2/place_straight.npy`.
- **Guide and sheets:** `make_guide.py` (print guide), `make_plate_sheet.py`, `make_wing2_sheet.py`, `wing2_tab_sheet.py`, `fit_ring_sheet.py`.
- **Wing views:** `wing2_views.py` with `helmet/full_view2.scad`. These also still use the old toed-in placement.
- Most other `.py` files are earlier experiments and can be ignored. The early tracing scripts (`trace_*.py`, `make_step1*.py`, `overlay.py` and similar) read the user's original reference photos from the cloud session's upload folder, which is not included, so they won't run here. Nothing current depends on them.

## 7. Open items

1. **Waiting on the user:** should the 4 deg outward lean also go, so the wings stand straight up? From above, the wing backs are still 14 mm wider than the fronts because of the lean. If yes, use the same method as `mount2_build.py`: turn about the key, keep the pegs, check clearance, rebuild both mounts.
2. The user said the wing mounts were "first up". **More tweaks are coming**; ask for the next one.
3. Only the wing assembly is written up. A **full helmet assembly guide** (shell halves and dowels, band layers, crest, cheek guards with frames, H and rivets, neck plate, H badge, nose clip, mounts) was offered and not yet made.
4. **To print next:** `band_reprint_AD5X.3mf` and `wing_mounts_straight_AD5X.3mf`, then whichever plates are left. Suggest a joint test early: feather F5 with the lower collar.
5. The pictures and wing views still show the old toed-in wings; update them when convenient.
