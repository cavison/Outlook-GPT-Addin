# Winged helmet - AD5X print guide

## Update (November 6): thicker band

The band's navy layer is now 2.0 mm (was 1.0) and its gold layer 1.2 mm (was 1.0), so the scroll pieces no longer snap when you remove supports. Every peg is in its old place, so the pieces fit the shell you already printed. The nose clip moved out 1.2 mm to sit on the thicker band; its tongue and snap bumps are unchanged.

- Already printed plates 1 and 2? Do not reprint them. Print **band_reprint_AD5X.3mf** (one navy plate, about 4 h): Band navy F, Band navy L and Back V navy.
- All other band, crest, cheek-frame and nose pieces in this project are already the new versions. The plates and their numbers are unchanged.

## Opening it in Orca Slicer

1. File > Open Project (or drag the file in and choose **Open as project**). Do not use Import - that brings in the parts without the plates.
2. Orca switches to the presets stored in the project: printer **Flashforge AD5X 0.4 nozzle**, process **0.20mm Standard @FF AD5X**, and three filaments **Flashforge PLA Basic @FF AD5X** coloured **1 navy, 2 white, 3 gold**. If you use a different PLA preset, pick it for each filament - the colours and slots stay.
3. You should see 14 separate plates (a grid in the 3D view, and plate tabs down the left). Plate type is set to Textured PEI Plate; change it in the plate type box if your sheet is different (it sets the bed temperature).
4. Each piece already has its own settings (walls, low infill, supports from the bed, brims where needed). Slice one plate at a time and check the preview.
5. When sending, map the filaments to the IFS slots: 1 navy, 2 white, 3 gold (slot 4 spare). The prime tower sits in the back-left corner on the multi-colour plates; that corner is kept clear.
6. Use glue stick on the shell plates (01, 02) - the shells are big and the back shell starts on its rim and supports.

| Plate | Colours | Pieces | Swaps | Est. time | Filament |
|---|---|---|---|---|---|
| 01 navy only - Shell front + 9 more | navy | 10 | - | ~15.0 h | ~479 g |
| 02 navy only - Shell back + 3 more | navy | 4 | - | ~21.3 h | ~730 g |
| 03 navy only - Neck plate + 5 more | navy | 6 | - | ~9.0 h | ~273 g |
| 04 navy only - wing mount L | navy | 1 | - | ~1.1 h | ~39 g |
| 05 white only - Band white F + 10 more | white | 11 | - | ~7.3 h | ~211 g |
| 06 gold only - Crest gold back + 6 more | gold | 7 | - | ~6.2 h | ~176 g |
| 07 gold only - Cheek frame L + 3 more | gold | 4 | - | ~6.9 h | ~142 g |
| 08 multi-colour - wing upper collar + 6 more | navy, white, gold | 7 | 58 | ~7.0 h | ~200 g |
| 09 multi-colour - wing upper collar + 6 more | navy, white, gold | 7 | 58 | ~7.1 h | ~203 g |
| 10 multi-colour - wing front medallion R + 4 more | navy, white, gold | 5 | 43 | ~5.7 h | ~190 g |
| 11 multi-colour - wing back medallion R (key) + 6 more | navy, white, gold | 7 | 59 | ~6.3 h | ~195 g |
| 12 multi-colour - wing lower collar + 1 more | navy, white, gold | 2 | 42 | ~6.1 h | ~178 g |
| 13 multi-colour - wing front medallion L + 1 more | navy, white, gold | 2 | 22 | ~6.7 h | ~219 g |
| 14 multi-colour - wing back medallion L (key) | navy, white, gold | 1 | 23 | ~2.5 h | ~86 g |

**Total:** about 108 h of printing over 14 plates; 305 filament swaps (~6.6 h of that is swapping, all on the multi-colour wing plates).
Filament (including supports, before purge waste): navy ~2.52 kg, white ~0.31 kg, gold ~0.49 kg.

## Plate contents

**01 navy only - Shell front + 9 more** - Shell front; Band navy F; Back V navy; Seam dowel pin x7

**02 navy only - Shell back + 3 more** - Shell back; Cheek guard L; Wing mount R; Band navy L

**03 navy only - Neck plate + 5 more** - Neck plate; Cheek guard R; Band navy BL; Band navy BR; Band navy R; Nose panel

**04 navy only - wing mount L** - Wing mount L

**05 white only - Band white F + 10 more** - Crest white back; Band white F; Band white B; Band white L; Band white R; Crest white front; Cheek H R; Cheek H L; Nose rivet pin; Cheek rivet R; Cheek rivet L

**06 gold only - Crest gold back + 6 more** - Crest gold back; Band gold F; Crest gold front; Band gold L; Band gold R; Nose clip; Back V gold

**07 gold only - Cheek frame L + 3 more** - Cheek frame L; Cheek frame R; Band gold BR; Band gold BL

**08 multi-colour - wing upper collar + 6 more** - Wing upper collar; Wing feather F2 L; Wing feather F3 L; Wing feather F3 R; Wing tip B R; Wing feather F6 R; Wing tip A R

**09 multi-colour - wing upper collar + 6 more** - Wing upper collar; Wing feather F2 R; Wing feather F4 L; Wing feather F4 R; Wing feather F7 L; Wing feather F5 R; Wing tip A L

**10 multi-colour - wing front medallion R + 4 more** - Wing front medallion R; Wing feather F1 R; Wing feather F9 L; Wing feather F7 R; Wing feather F9 R

**11 multi-colour - wing back medallion R (key) + 6 more** - Wing back medallion R (key); Wing feather F1 L; Wing feather F8 R; Wing tip B L; Wing feather F8 L; Wing feather F5 L; Wing feather F6 L

**12 multi-colour - wing lower collar + 1 more** - Wing lower collar x2

**13 multi-colour - wing front medallion L + 1 more** - Wing front medallion L; Front H badge

**14 multi-colour - wing back medallion L (key)** - Wing back medallion L (key)

## Wing assembly (each side)

- Pieces per wing: feathers F1-F9 and tips A and B for that side (names end in R or L - the left set is the mirror image), one upper and one lower collar (the same print serves both wings; turn it over for the left), and that side's front and back medallion.
- Feathers and tips print show face down, so the tab lies on the bed. Tip B is the only wing piece with supports: a small pad under its tab. Peel it off and scrape the tab underside smooth before fitting.
- 1. Click tip A into the lower collar and tip B into F9: push the tab straight in until both snap fingers click.
- 2. Click F1-F4 into the upper collar and F5-F9 into the lower collar the same way. Each tab goes 18-26 mm into its collar.
- 3. Lay the two collars' hidden plates into each other (the half-lap in the middle) so the hub is one flat disc.
- 4. Push the front medallion's pegs through both plates into the back medallion. That clamps the whole hub.
- 5. Slide the back medallion's key into the wing mount on the helmet.
- Glue is optional on top of the snaps (a drop on each tab before it goes in); nothing relies on it.

