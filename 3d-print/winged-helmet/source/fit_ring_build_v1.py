#!/usr/bin/env python
# Fit-test rings for the full-size helmet (7 1/4 = 579 mm head):
#   * HELMET RING: the helmet's own inside at the brow line, 15 mm tall (brow line up to 15 mm above it), with
#     everything that reaches inside there (the front/back seam ribs at the sides, the nose-guard clip, the tops
#     of the cheek-guard tongues). Wear it with padding to test the fit. Four pieces (front, back, two sides) that
#     slide together with vertical dovetails; front and back carry the tongues, the sides the sockets.
#   * HEAD RING: the head shape the helmet was sized from (579 mm round, 1.24 long / wide), 15 mm tall, one piece.
#     Worn bare it should feel like a snug hat band; it checks the measurement and the head shape.
# Writes helmet/out_v23/fit_test/*.stl, pkg/fit_test_AD5X.3mf and a picture.
import math, os, io, json, uuid, zipfile, subprocess
import numpy as np, trimesh, manifold3d as m3
from shapely.geometry import Polygon, Point
exec(open('wing_build.py').read().split("if __name__ == '__main__':")[0])      # to_m, to_t, union, extrude, ...

OUT = 'helmet/out_v23/fit_test/'; os.makedirs(OUT, exist_ok=True)
PR = 'helmet/out_v23/print/'
# ---------- the helmet's sizing (same formulas as winged_helmet_v23.scad) ----------
C, Q = 579.0, 1.24
SIDE_PAD, FB_PAD, TOP_PAD, BROW_TO_CROWN, P = 23.0, 28.0, 20.0, 120.0, 2.2
hh = ((Q - 1) / (Q + 1)) ** 2
HEAD_A = C / (math.pi * (1 + Q) * (1 + 3 * hh / (10 + math.sqrt(4 - 3 * hh))))   # head half-width (Ramanujan)
RI = HEAD_A + SIDE_PAD
K = (HEAD_A * Q + FB_PAD) / RI
HI = BROW_TO_CROWN + TOP_PAD
def r_in(z): return RI * (1 - min(z / HI, 1) ** P) ** (1 / P)          # interior radius (circular frame) above the brow
H, T = 15.0, 2.4                                                       # ring height (brow line up), wall (same as the shell)
SEG = 360

def revolve(pts):                       # (r, z) polygon -> solid about z (circular frame)
    return m3.Manifold.revolve(m3.CrossSection([pts]), SEG)
def stretch(m): return m.scale([1, K, 1])
zs = np.linspace(0, H, 41)
ring = stretch(revolve([(r_in(z) + T, z) for z in zs] + [(r_in(z), z) for z in zs[::-1]]))     # counter-clockwise
cavity = stretch(revolve([(0, 0), *[(r_in(z) + 0.4, z) for z in zs], (0, H)]))
# ---------- what reaches inside the helmet at the brow (real parts, cut to the ring height) ----------
inside = []
import glob
SKIP = ('wing', 'seam_dowel_pin', 'nose_pin')         # wings sit outside; loose pins are stored in print position
for f in sorted(glob.glob(PR + '*.stl')):
    if any(k in f for k in SKIP) and 'wing_mount' not in f: continue
    m = to_m(trimesh.load(f)) ^ cavity
    if m.volume() > 0.5: inside.append(m)
inside = union(inside)
# printed upright, so anything that starts above the bed (the seam ribs begin ~8 mm up) gets a 45 deg slope under it
DZ = 0.5
lay, prev = [], None
for z in np.arange(H - DZ / 2, 0, -DZ)[::1]:
    cur = inside.slice(z) + ring.slice(z)
    if prev is not None: cur = cur + prev.offset(-DZ, m3.JoinType.Miter)
    prev = cur
    lay.append(cur.extrude(DZ).translate([0, 0, z - DZ / 2]))
inside = inside + union(lay)
# ---------- joints: bosses outside the wall, vertical dovetails ----------
SPLITS = {45: -1, 135: +1, 225: -1, 315: +1}       # split angle (circular frame) -> side the female piece is on (-1 = smaller angle)
U0, WN, WH, L, CL = RI + 7.0, 4.5, 7.5, 8.0, 0.15
def polar(u, t, phi, s):                            # radial u, tangential t (toward the female piece)
    c, sn = math.cos(math.radians(phi)), math.sin(math.radians(phi))
    return (u * c - s * t * sn, u * sn + s * t * c)
def tongue2d(phi, s, grow=0.0):
    pts = [(U0 - WN / 2, -2), (U0 + WN / 2, -2), (U0 + WN / 2, 0), (U0 + WH / 2, L), (U0 - WH / 2, L), (U0 - WN / 2, 0)]
    g = Polygon([polar(u, t, phi, s) for u, t in pts])
    return g.buffer(grow, join_style=2) if grow else g
def ext2d(g, z0, z1): return stretch(extrude(g, z0, z1))
bosses, tongues, sockets = [], [], []
for phi, s in SPLITS.items():
    d = math.degrees(16.0 / RI)
    arc = [(r * math.cos(math.radians(a)), r * math.sin(math.radians(a))) for r, a in
           [(RI + 0.5, phi - d + i * 2 * d / 24) for i in range(25)] + [(RI + 13.0, phi + d - i * 2 * d / 24) for i in range(25)]]
    bosses.append(ext2d(Polygon(arc), 0, H))
    tongues.append(ext2d(tongue2d(phi, s), 0, H - 1.5))
    sockets.append(ext2d(tongue2d(phi, s, CL), -1.0, H - 1.2))     # 1.2 mm roof on top: the tongue slides up from below
body = ring + inside + union(bosses)
def wedge(a0, a1):
    pts = [(0, 0)] + [(400 * math.cos(math.radians(a)), 400 * math.sin(math.radians(a))) for a in np.linspace(a0, a1, 64)]
    return ext2d(Polygon(pts), -5, H + 5)
# ---------- labels (OpenSCAD text wrapped on the outside) ----------
def label(text, phi, size=8.0):
    zc, r0 = H / 2, r_in(H / 2) + T
    step = math.degrees(6.2 / r0)
    scad = 'union() {\n' + ''.join(
        f' rotate([0,0,{phi + (i - (len(text) - 1) / 2) * step}]) translate([{r0 - 0.7},0,{zc}]) rotate([90,0,90]) '
        f'linear_extrude(1.5) text("{ch}", size={size}, font="Liberation Mono:style=Bold", halign="center", valign="center");\n'
        for i, ch in enumerate(text) if ch != ' ') + '}\n'
    fn = OUT + f'_label_{text.replace(" ", "_")}.scad'; open(fn, 'w').write(scad)
    subprocess.run(['openscad', '-o', fn[:-5] + '.stl', fn], capture_output=True, timeout=300)
    return stretch(to_m(trimesh.load(fn[:-5] + '.stl')))
PIECES = {'front': (225, 315, 'male', 'FRONT', 270), 'back': (45, 135, 'male', 'BACK', 90),
          'side_R': (-45, 45, 'female', 'R', 0), 'side_L': (135, 225, 'female', 'L', 180)}
rep = []
def say(*a):
    s = ' '.join(str(x) for x in a); print(s); rep.append(s)
say(f'helmet inside at the brow: {2 * RI:.0f} wide x {2 * RI * K:.0f} long; head {2 * HEAD_A:.0f} x {2 * HEAD_A * Q:.0f}')
parts = {}
for name, (a0, a1, kind, text, lphi) in PIECES.items():
    p = (body ^ wedge(a0, a1)) + label(text, lphi)
    if kind == 'male': p = p + union(tongues)                   # each male piece only touches its own two tongues
    else: p = p - union(sockets)
    p = max(p.decompose(), key=lambda q: q.volume())            # drop the other pieces' tongues
    parts[name] = p
# tongues belong to the male piece they touch: rebuild male pieces with only the tongues that overlap their wedge
for name, (a0, a1, kind, text, lphi) in PIECES.items():
    if kind != 'male': continue
    own = [t for t in tongues if (t ^ (body ^ wedge(a0, a1))).volume() > 1]
    parts[name] = max(((body ^ wedge(a0, a1)) + label(text, lphi) + union(own)).decompose(), key=lambda q: q.volume())
# ---------- head ring ----------
HW = 2.4
head = revolve([(HEAD_A, 0), (HEAD_A + HW, 0), (HEAD_A + HW, H), (HEAD_A, H)]).scale([1, Q, 1])
def head_label(text, phi):
    zc, r0 = H / 2, HEAD_A + HW
    step = math.degrees(6.2 / r0)
    scad = 'union() {\n' + ''.join(
        f' rotate([0,0,{phi + (i - (len(text) - 1) / 2) * step}]) translate([{r0 - 0.8},0,{zc}]) rotate([90,0,90]) '
        f'linear_extrude(1.5) text("{ch}", size=7, font="Liberation Mono:style=Bold", halign="center", valign="center");\n'
        for i, ch in enumerate(text) if ch != ' ') + '}\n'
    fn = OUT + f'_hlabel_{text.replace(" ", "_")}.scad'; open(fn, 'w').write(scad)
    subprocess.run(['openscad', '-o', fn[:-5] + '.stl', fn], capture_output=True, timeout=300)
    return to_m(trimesh.load(fn[:-5] + '.stl')).scale([1, Q, 1])
parts['head_ring'] = head - head_label('FRONT', 270) - head_label('HEAD 579', 90)      # cut 0.8 mm in: keeps it under 210 mm
# ---------- checks + export ----------
for name, p in parts.items():
    t = to_t(p); e = t.extents
    bodies = len([q for q in p.decompose() if q.volume() > 1])
    say(f'{name:9s} bodies {bodies}  {e[0]:5.0f} x {e[1]:5.0f} x {e[2]:4.1f} mm  {p.volume() / 1000:5.1f} cm3')
    t.apply_translation([0, 0, -t.bounds[0][2]]); t.export(OUT + f'fit_{name}.stl')
for a, b in (('front', 'side_R'), ('front', 'side_L'), ('back', 'side_R'), ('back', 'side_L')):
    say(f'  {a} / {b} overlap {(parts[a] ^ parts[b]).volume():.2f} mm3 (should be 0)')
say(f'  seam ribs, clip and tongues inside the ring: {(inside - ring).volume() / 1000:.1f} cm3')
open(OUT + 'report.txt', 'w').write('\n'.join(rep) + '\n')
pickle_out = {n: to_t(p) for n, p in parts.items()}
import pickle; pickle.dump(pickle_out, open('ref2/fit_ring.pkl', 'wb'))
