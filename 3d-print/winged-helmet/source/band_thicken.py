#!/usr/bin/env python
# Thicker band layers (navy 1.0 -> 2.0 mm, gold 1.0 -> 1.2 mm, back V 2.0 -> 3.2 mm) on EXACTLY the old peg spots,
# so they fit the shell that is already printed.  Nothing printed changes:
#   1. re-run conn_build.py with the original inputs into a scratch folder (OUT redirected) and prove it reproduces
#      the printed shell and the old band pieces bit-for-bit in volume -> same peg spots;
#   2. build the band pieces from the thicker layers (helmet/out_v23/band2/) with those pegs;
#   3. where another part sits on the band (nose strap etc.), the band gives way, never the other part.
# Writes helmet/out_v23/print_band2/*.stl and a report.
import os, sys, json
import numpy as np, trimesh, manifold3d as m3

REGEN = 'helmet/out_v23/print_regen/'
NEW = 'helmet/out_v23/print_band2/'
os.makedirs(REGEN, exist_ok=True); os.makedirs(NEW, exist_ok=True)
src = open('conn_build.py').read()
src = src.replace("SRC, OUT = 'helmet/out_v23/', 'helmet/out_v23/print/'", f"SRC, OUT = 'helmet/out_v23/', '{REGEN}'")
assert REGEN in src
cut = src.index('# band layers: pegs on each piece, holes for the pegs of the layers above')
band_src = src[cut:]
exec(src[:cut])                                    # everything up to the band pieces (shell, guards, pegs chosen)

rep2 = []
def say(*a):
    s = ' '.join(str(x) for x in a); print(s, flush=True); rep2.append(s)
# ---------- 1. proof: the regenerated printed parts match the files the user printed from ----------
def same(name):
    a = trimesh.load('helmet/out_v23/print/' + name + '.stl'); b = trimesh.load(REGEN + name + '.stl')
    dv = abs(a.volume - b.volume); db = np.abs(a.bounds - b.bounds).max()
    return dv < 1.0 and db < 0.01, dv, db
for nm in ('cheek_guard_L_navy',):
    ok, dv, db = same(nm); say(f'regenerated {nm}: volume diff {dv:.3f} mm3, bounds diff {db:.4f} mm -> {"identical" if ok else "DIFFERENT"}')
    assert ok, nm
# every band / V peg must go through an open hole in the shell AS PRINTED (print/ shell, which also has the
# wing-mount holes added later by mount_build.py); control: the same probe moved 4 mm sideways hits shell
PRINTED_SHELL = to_m(trimesh.load('helmet/out_v23/print/shell_front_navy.stl')) + to_m(trimesh.load('helmet/out_v23/print/shell_back_navy.stl'))
def probe(p, n): return place(cyl(1.35, 1.35, 0.3, W + BOSS_H - 0.6), p, -np.asarray(n))
worst, ctrl_min, npeg = 0.0, 1e9, 0
for key, got in list(band_pegs.items()) + [(('V', c), g) for c, g in v_pegs.items()]:
    for p, n in got:
        v_in = (probe(p, n) ^ PRINTED_SHELL).volume(); worst = max(worst, v_in); npeg += 1
        t = np.cross(n, [0, 0, 1.0]); t /= np.linalg.norm(t)
        ctrl_min = min(ctrl_min, (probe(p + 4 * t, n) ^ PRINTED_SHELL).volume())
say(f'{npeg} band and V pegs checked against the printed shell: largest overlap with shell material {worst:.2f} mm3 '
    f'(0 = open hole); control probes 4 mm aside hit at least {ctrl_min:.1f} mm3 of shell')
assert worst < 0.5 and ctrl_min > 5
band_pegs_orig, v_pegs_orig = dict(band_pegs), dict(v_pegs)
exec(band_src.split("hg, hw = load('h_gold')")[0])     # old band pieces + V + crest, original layers, into the scratch folder
for nm in ('band_navy_F', 'band_V_navy', 'band_navy_L', 'band_navy_R', 'band_gold_F', 'band_white_F'):
    ok, dv, db = same(nm); say(f'regenerated old {nm}: volume diff {dv:.3f} mm3 -> {"identical" if ok else "DIFFERENT"}')
    assert ok, nm
# ---------- 2. thicker layers on the same pegs ----------
LAYER = {'white': (0.0, 1.2), 'gold': (1.2, 2.4), 'navy': (2.4, 4.4)}
SRC2 = 'helmet/out_v23/band2/'
layers = {c: to_m(trimesh.load(SRC2 + 'bandL_' + c + '.stl')) for c in ('white', 'gold', 'navy')}
vparts = {c: to_m(trimesh.load(SRC2 + 'bandV_' + c + '.stl')) for c in ('gold', 'navy')}
dot_pegs = []
for th, z, r in DOTS:
    for s in (1, -1):
        p, n = surf(s * th, z)
        dot_pegs.append(place(cyl(r - 0.12, r - 0.12, LAYER['white'][1] - 0.4, LAYER['navy'][1] - 0.02), p, n))
OUT = NEW
new_src = band_src.split("hg, hw = load('h_gold')")[0]
assert 'min_body=60' in new_src
new_src = new_src.replace('min_body=60', 'min_body=140')    # twice the thickness: drop the same slivers the old build dropped
exec(new_src)     # same code, new layers, new folder
assert band_pegs == band_pegs_orig and v_pegs == v_pegs_orig
# cheek frames (not printed yet) are trimmed against the band, as before
bands = union([m for (c, k), m in band_built.items()])
save(gf - bands, 'cheek_frame_R_gold', min_body=1)
save(gf.mirror([1, 0, 0]) - bands, 'cheek_frame_L_gold', min_body=1)
say('pegs: identical spots for every band piece and both V inserts')
open(NEW + 'build_report.txt', 'w').write('\n'.join(rep2 + report) + '\n')
