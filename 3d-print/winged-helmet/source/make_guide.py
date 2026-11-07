# plate-by-plate print guide (markdown) from ref2/plates.json + volumes per colour
import json, trimesh, os
from collections import defaultdict
rows = json.load(open('ref2/plates.json'))
src = open('plates_build.py').read(); ns = {}
exec(src[:src.index('# ---------- orient every piece ----------')], ns)
P = {p['name']: p for p in ns['P']}
T = json.load(open('ref2/piece_times.json'))
def base(n):
    for k in sorted(P, key=len, reverse=True):
        if n == k or (n.startswith(k + ' ') and n[len(k) + 1:].isdigit()): return k
    return n
vol = {}
def colour_split(name):
    if name not in vol:
        v = {c: trimesh.load(f).volume for f, c in P[name]['parts']}; s = sum(v.values())
        vol[name] = {c: x / s for c, x in v.items()}
    return vol[name]
per_colour = defaultdict(float); tot_h = 0; tot_sw = 0
lines = ['# Winged helmet - AD5X print guide', '',
         '## Update (November 7): wings parallel to the head', '',
         'New wing mount blocks hold each wing straight, parallel to the side of the head, instead of toed in 15 degrees at the front. The medallions stay where they are: each wing turns about its dovetail key. The four pegs on each block are exactly the old ones, so the blocks push into the holes in the shell you already printed, the same way as before.', '',
         '- Print **wing_mounts_straight_AD5X.3mf** (one navy plate, both blocks, about 2 h). Supports are off: they would fill the dovetail socket, and its roof bridges fine.',
         '- The mount blocks in this project (plates 2 and 4) are the new ones too; you do not need to print those plates for the mounts.', '',
         '## Update (November 6): thicker band', '',
         'The band\'s navy layer is now 2.0 mm (was 1.0) and its gold layer 1.2 mm (was 1.0), so the scroll pieces no longer snap when you remove supports. Every peg is in its old place, so the pieces fit the shell you already printed. The nose clip moved out 1.2 mm to sit on the thicker band; its tongue and snap bumps are unchanged.', '',
         '- Already printed plates 1 and 2? Do not reprint them. Print **band_reprint_AD5X.3mf** (one navy plate, about 4 h): Band navy F, Band navy L and Back V navy.',
         '- All other band, crest, cheek-frame and nose pieces in this project are already the new versions. The plates and their numbers are unchanged.', '',
         '## Opening it in Orca Slicer', '',
         '1. File > Open Project (or drag the file in and choose **Open as project**). Do not use Import - that brings in the parts without the plates.',
         '2. Orca switches to the presets stored in the project: printer **Flashforge AD5X 0.4 nozzle**, process **0.20mm Standard @FF AD5X**, and three filaments **Flashforge PLA Basic @FF AD5X** coloured **1 navy, 2 white, 3 gold**. If you use a different PLA preset, pick it for each filament - the colours and slots stay.',
         f'3. You should see {len(rows)} separate plates (a grid in the 3D view, and plate tabs down the left). Plate type is set to Textured PEI Plate; change it in the plate type box if your sheet is different (it sets the bed temperature).',
         '4. Each piece already has its own settings (walls, low infill, supports from the bed, brims where needed). Slice one plate at a time and check the preview.',
         '5. When sending, map the filaments to the IFS slots: 1 navy, 2 white, 3 gold (slot 4 spare). The prime tower sits in the back-left corner on the multi-colour plates; that corner is kept clear.',
         '6. Use glue stick on the shell plates (01, 02) - the shells are big and the back shell starts on its rim and supports.', '',
         '| Plate | Colours | Pieces | Swaps | Est. time | Filament |', '|---|---|---|---|---|---|']
for r in rows:
    h = (r['print_h'] or 0) + r['swaps'] * 78 / 3600; tot_h += h; tot_sw += r['swaps']
    for n in r['pieces']:
        b = base(n); g = T.get(b, {}).get('total_g', 0)
        for c, f in colour_split(b).items(): per_colour[c] += g * f
    lines.append(f"| {r['title']} | {', '.join(r['colours'])} | {len(r['pieces'])} | {r['swaps'] or '-'} | ~{h:.1f} h | ~{r['grams']:.0f} g |")
lines += ['', f'**Total:** about {tot_h:.0f} h of printing over {len(rows)} plates; {tot_sw} filament swaps (~{tot_sw * 78 / 3600:.1f} h of that is swapping, all on the multi-colour wing plates).',
          'Filament (including supports, before purge waste): ' + ', '.join(f'{c} ~{per_colour[c] / 1000:.2f} kg' for c in ('navy', 'white', 'gold')) + '.',
          '', '## Plate contents', '']
for r in rows:
    from collections import Counter
    cnt = Counter(base(n) for n in r['pieces'])
    lines.append(f"**{r['title']}** - " + '; '.join(f'{k} x{v}' if v > 1 else k for k, v in cnt.items()))
    lines.append('')
lines += ['## Wing assembly (each side)', '',
          '- Pieces per wing: feathers F1-F9 and tips A and B for that side (names end in R or L - the left set is the mirror image), one upper and one lower collar (the same print serves both wings; turn it over for the left), and that side\'s front and back medallion.',
          '- Feathers and tips print show face down, so the tab lies on the bed. Tip B is the only wing piece with supports: a small pad under its tab. Peel it off and scrape the tab underside smooth before fitting.',
          '- 1. Click tip A into the lower collar and tip B into F9: push the tab straight in until both snap fingers click.',
          '- 2. Click F1-F4 into the upper collar and F5-F9 into the lower collar the same way. Each tab goes 18-26 mm into its collar.',
          '- 3. Lay the two collars\' hidden plates into each other (the half-lap in the middle) so the hub is one flat disc.',
          '- 4. Push the front medallion\'s pegs through both plates into the back medallion. That clamps the whole hub.',
          '- 5. Slide the back medallion\'s key into the wing mount on the helmet.',
          '- Glue is optional on top of the snaps (a drop on each tab before it goes in); nothing relies on it.', '']
open('pkg/winged_helmet_print_guide.md', 'w').write('\n'.join(lines) + '\n')
print('\n'.join(lines[:40]))
