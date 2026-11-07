#!/usr/bin/env python
# The thicker band gives way, nothing else changes:
#   * navy and gold layers get their white-dot holes along each dot post's own axis (the post leans with the shell),
#     so the longer posts slide through without rubbing;
#   (the snap-on nose clip is regenerated from the model with the thicker band, so the band stays whole under it)
import numpy as np, trimesh, manifold3d as m3
src = open('conn_build.py').read()
exec(src[:src.index('# ---------- shell bosses / holes bookkeeping ----------')])     # helpers, surf(), DOTS
D = 'helmet/out_v23/print_band2/'
LAYER2 = {'white': (0.0, 1.2), 'gold': (1.2, 2.4), 'navy': (2.4, 4.4)}
dot_holes = []
for th, z, r in DOTS:
    for s in (1, -1):
        p, n = surf(s * th, z)
        dot_holes.append(place(cyl(r + 0.05, r + 0.05, LAYER2['white'][1] - 0.2, LAYER2['navy'][1] + 1.0), p, n))
dot_holes = m3.Manifold.batch_boolean(dot_holes, m3.OpType.Add)
for name in ('band_navy_F', 'band_navy_R', 'band_navy_L', 'band_navy_BL', 'band_navy_BR',
             'band_gold_F', 'band_gold_R', 'band_gold_L', 'band_gold_BL', 'band_gold_BR'):
    m = load(name, D); v0 = m.volume()
    m = m - dot_holes
    comps = sorted(m.decompose(), key=lambda q: -q.volume())
    keep = [q for q in comps if q.volume() > 140]
    m = m3.Manifold.batch_boolean(keep, m3.OpType.Add)
    to_t(m).export(D + name + '.stl')
    print(f'{name:14s} {v0 / 1000:6.2f} -> {m.volume() / 1000:6.2f} cm3, {len(keep)} body (dropped {len(comps) - len(keep)} slivers)')
