#!/usr/bin/env python
# Wing v2 (hub-and-feather), built flat in the wing's own frame (u, v in the artwork plane, w out of the wing;
# w = 0 is the wing's middle plane, +w is the show side, -w faces the helmet):
#   * front + back medallion (4 mm each) clamp the two collars' hidden plates; the back medallion carries the
#     same dovetail key as before, so the helmet's mount blocks stay as they are
#   * upper + lower collar (6.4 mm, coloured both faces); each has a hidden half-disc plate that half-laps
#     with the other one between the medallions; lightening holes in the plates
#   * 9 feathers + 2 small tips (6.4 mm, coloured both faces); each has a tongue with two snap fingers that
#     clicks into a socket in its collar (the tips click into F4 / F9)
#   * colour: white solid 2.4 mm deep, gold 1.6 mm deep, from every show face; the rest navy
#   * 10 pegs on the front medallion go through both plates into blind sockets in the back medallion
# Writes helmet/out_v23/print_wing2/*.stl (one file per piece and colour) + a report.
import json, math, os, pickle
import numpy as np, trimesh, manifold3d as m3
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union
from shapely import affinity
exec(open('wing_build.py').read().split("if __name__ == '__main__':")[0])       # helpers, key_local(), PLACE, ...
OUT2 = 'helmet/out_v23/print_wing2/'; os.makedirs(OUT2, exist_ok=True)
rep = []
def say(*a):
    s = ' '.join(str(x) for x in a); print(s); rep.append(s)
H_ = pickle.load(open('ref2/hub_regions.pkl', 'rb')); REG, MEDP, Cc = H_['REG'], H_['MED'], np.array(H_['C'])
V = pickle.load(open('ref2/layered_concept.pkl', 'rb'))['V']
def main_part(g, a=30.0):
    g = g.buffer(-0.6, 8).buffer(0.6, 8)                 # drop hair-thin slivers left by the split
    keep = [q for q in getattr(g, 'geoms', [g]) if q.geom_type == 'Polygon' and q.area > a]
    return unary_union(keep)
REG = {k: main_part(v) for k, v in REG.items()}
# a feather region that falls apart keeps its biggest part; any other bit joins the nearest collar
for k in [k for k in REG if k[0] in 'PH']:
    parts = sorted(getattr(REG[k], 'geoms', [REG[k]]), key=lambda q: -q.area)
    REG[k] = parts[0]
    for q in parts[1:]:
        c = min(('CU', 'CL'), key=lambda c: REG[c].distance(q))
        REG[c] = unary_union([REG[c], q]).buffer(0.8, 8).buffer(-0.8, 8)
TH, HT = 6.4, 3.2                    # feathers and collars
GOLD_D, WHITE_D = 1.6, 2.4
MT = 4.0                             # each medallion
R_MED = 70.0
TT, ST = 2.2, 2.5                    # tongue / socket thickness (centred on w = 0)
T_DEP, S_DEP = 16.0, 16.6            # tongue length / socket depth
FW, SLIT, BUMP = 2.4, 0.8, 0.5       # snap finger width, slit beside it, bump height
PEG_D, PEG_R_C = 5.0, 56.0
FE = {'F1': 'P1', 'F2': 'P2', 'F3': 'P3', 'F4': 'P4', 'F5': 'H1', 'F6': 'H2', 'F7': 'H3', 'F8': 'H4', 'F9': 'H5', 'TA': 'P5', 'TB': 'H6'}
HOST = {n: ('CU' if FE[n][0] == 'P' else 'CL') for n in FE}
HOST['TA'], HOST['TB'] = 'F4', 'F9'          # may be re-pointed below to whichever neighbour the tip really touches
def clean(g, w=0.4): return g.buffer(-w, 8).buffer(w, 8).buffer(0) if not g.is_empty else g
# ---------- 2D outlines ----------
axis = np.array([REG['CU'].centroid.x - REG['CL'].centroid.x, REG['CU'].centroid.y - REG['CL'].centroid.y]); axis /= np.linalg.norm(axis)
perp = np.array([-axis[1], axis[0]])
disc = Point(*Cc).buffer(R_MED, 256)
LAP = 16.0
def half_disc(sign, extra):
    p0 = Cc - axis * sign * extra
    big = Polygon([p0 + perp * 400, p0 - perp * 400, p0 - perp * 400 + axis * sign * 400, p0 + perp * 400 + axis * sign * 400])
    return disc.intersection(big)
PLATE = {'CU': half_disc(+1, LAP / 2), 'CL': half_disc(-1, LAP / 2)}
LAPZ = PLATE['CU'].intersection(PLATE['CL'])
OUTL = {}
GAP2 = 0.15                          # every edge pulled in by this: pieces slide together without jamming
for n, r in FE.items(): OUTL[n] = REG[r].buffer(-GAP2, 8)
OUTL['CU'] = unary_union([REG['CU'], PLATE['CU']]).buffer(0.01).buffer(-0.01 - GAP2, 8)
OUTL['CL'] = unary_union([REG['CL'], PLATE['CL']]).buffer(0.01).buffer(-0.01 - GAP2, 8)
# pegs and lightening holes in the hub
PEGS = [Cc + PEG_R_C * np.array([math.cos(a), math.sin(a)]) for a in np.radians(np.arange(0, 360, 45) + 22.5)]
PEGS += [Cc + perp * 25, Cc - perp * 25]
LIGHT = []
for a in np.radians(np.arange(0, 360, 30)):
    hc = Point(*(Cc + 36 * np.array([math.cos(a), math.sin(a)]))).buffer(8, 48)
    if not hc.intersects(LAPZ.buffer(4)) and all(Point(*p).distance(hc.centroid) > 16 for p in PEGS): LIGHT.append(hc)
LIGHT = unary_union(LIGHT)
# ---------- tongues and sockets ----------
def joint(n):
    """tongue (2D, on piece n) and socket (2D, cut into its host) at their shared edge"""
    a, b = OUTL[n], (REG[HOST[n]] if HOST[n] in ('CU', 'CL') else OUTL[HOST[n]])
    shared = a.buffer(0.8).intersection(b.buffer(0.8))
    cs = np.array(shared.minimum_rotated_rectangle.exterior.coords)[:4]
    e1, e2 = cs[1] - cs[0], cs[2] - cs[1]
    edge = e1 if np.linalg.norm(e1) > np.linalg.norm(e2) else e2
    L = np.linalg.norm(edge); u = edge / L; nr = np.array([-u[1], u[0]])
    mid = np.array([shared.centroid.x, shared.centroid.y])
    if b.distance(Point(*(mid + 6 * nr))) > b.distance(Point(*(mid - 6 * nr))): nr = -nr     # point into the host
    w = float(np.clip(0.6 * L, 10.0, 26.0))
    def rect(x0, x1, y0, y1):                 # x across the edge (u), y into the host (nr)
        return Polygon([mid + u * x0 + nr * y0, mid + u * x1 + nr * y0, mid + u * x1 + nr * y1, mid + u * x0 + nr * y1])
    tongue = rect(-w / 2, w / 2, -3.0, T_DEP)
    # two snap fingers along the tongue's sides: slits free them, bumps catch in notches in the socket
    for s in (-1, 1):
        xs = s * (w / 2 - FW - SLIT / 2)
        tongue = tongue.difference(rect(xs - SLIT / 2, xs + SLIT / 2, 2.5, T_DEP + 1))
        bump = Polygon([mid + u * s * w / 2 + nr * 11.0, mid + u * s * (w / 2 + BUMP) + nr * 13.5, mid + u * s * w / 2 + nr * 15.0])
        tongue = tongue.union(bump)
    sock = rect(-w / 2 - 0.2, w / 2 + 0.2, -3.0, S_DEP)
    for s in (-1, 1):
        sock = sock.union(rect(s * (w / 2 + 0.2) - (0 if s > 0 else BUMP + 0.4), s * (w / 2 + 0.2) + (BUMP + 0.4 if s > 0 else 0), 10.6, 15.6))
    return tongue, sock, dict(width=round(w, 1), edge=round(L, 1))
for tip in ('TA', 'TB'):
    cands = {k: OUTL[k] for k in FE if k not in ('TA', 'TB')}
    cands.update({'CU': REG['CU'], 'CL': REG['CL']})
    edge = {k: OUTL[tip].buffer(0.8).intersection(g.buffer(0.8)).area for k, g in cands.items()}
    HOST[tip] = max(edge, key=edge.get)
    say(f'{tip} clicks into {HOST[tip]} (shared edge ~{edge[HOST[tip]] / 1.6:.0f} mm)')
JOINTS = {n: joint(n) for n in FE}
pickle.dump({n: (j[0], j[1]) for n, j in JOINTS.items()}, open('ref2/wing2_joints.pkl', 'wb'))
# ---------- 3D with colours ----------
def coloured(outline, w0, w1, top=True, bottom=True):
    """solid piece between w0 and w1, gold / white taken from the artwork down from the show faces"""
    solid = extrude(outline, w0, w1)
    gold2 = clean(V['gold'].intersection(outline)); white2 = clean(V['white'].intersection(outline))
    gold, white = [], []
    if top:
        gold.append(extrude(gold2, w1 - GOLD_D, w1 + 0.01)); white.append(extrude(white2, w1 - WHITE_D, w1 + 0.01))
    if bottom:
        gold.append(extrude(gold2, w0 - 0.01, w0 + GOLD_D)); white.append(extrude(white2, w0 - 0.01, w0 + WHITE_D))
    gold = union(gold) ^ solid; white = union(white) ^ solid
    navy = solid - gold - white
    return {'navy': navy, 'gold': gold, 'white': white}
def cut_all(parts, m):
    return {c: (p - m) for c, p in parts.items()}
def add_navy(parts, m):
    parts = cut_all(parts, m); parts['navy'] = parts['navy'] + m; return parts
PIECES = {}
# feathers and tips: body, tongue (navy, in the core), sockets for the tips in F4 / F9
for n in FE:
    p = coloured(OUTL[n], -HT, HT)
    tongue, _, info = JOINTS[n]
    host2 = REG[HOST[n]] if HOST[n] in ('CU', 'CL') else OUTL[HOST[n]]
    allowed = unary_union([host2.buffer(-1.5), OUTL[n]]).buffer(1.8, 8).buffer(-1.8, 8)       # closing bridges the strip between them
    t2 = tongue.intersection(allowed).difference(OUTL[n].buffer(-1.0))
    t2 = max(getattr(t2, 'geoms', [t2]), key=lambda q: q.area)
    tg = extrude(t2.buffer(0), -TT / 2, TT / 2)
    p = add_navy(p, tg)
    PIECES[n] = p
for tip in ('TA', 'TB'):
    _, sock, _ = JOINTS[tip]
    if HOST[tip] in PIECES: PIECES[HOST[tip]] = cut_all(PIECES[HOST[tip]], extrude(sock, -ST / 2, ST / 2))   # collar sockets are cut with the collars
# collars: body + hidden plate (navy), half-lap, sockets, peg holes, lightening holes
for c, sign in (('CU', +1), ('CL', -1)):
    vis = coloured(OUTL[c].intersection(REG[c]), -HT, HT)
    plate2 = OUTL[c].difference(REG[c].buffer(-0.01))
    plate = extrude(plate2, -HT, HT)
    lap_cut = extrude(LAPZ, 0.0, HT + 0.1) if sign < 0 else extrude(LAPZ, -HT - 0.1, 0.0)   # lower: keeps the bottom half of the lap
    p = add_navy(vis, plate - lap_cut)
    for n in FE:
        if HOST[n] == c:
            _, sock, _ = JOINTS[n]; p = cut_all(p, extrude(sock, -ST / 2, ST / 2))
    holes = union([cyl(q, (PEG_D + 0.3) / 2, -HT - 1, HT + 1, 40) for q in PEGS] + [extrude(LIGHT, -HT - 1, HT + 1)])
    PIECES[c] = cut_all(p, holes)
# medallions: art on the outer face only
fm = coloured(disc, HT, HT + MT, top=True, bottom=False)
bm = coloured(disc, -HT - MT, -HT, top=False, bottom=True)
pegs = []
for q in PEGS:
    pegs.append(peg(tuple(q), PEG_D, -HT - 2.0, HT + 0.2, up=False))     # down from the front medallion, 2 mm into the back one
fm = add_navy(fm, union(pegs))
bm = cut_all(bm, union([cyl(q, (PEG_D + 0.3) / 2, -HT - 2.3, -HT + 0.1, 40) for q in PEGS]))
# key: the old dovetail key, unchanged, on a boss that reaches the old key base (w = -12)
key = back_frame(key_local())
boss = union([cyl(MED_C, ROOT_R, -MID_T / 2 - ROOT_TOP - 0.05, -HT - MT + 0.05, 96), cyl(TWIST, 5.0, -MID_T / 2 - ROOT_TOP - 0.05, -HT - MT + 0.05, 48)])
bm = add_navy(bm, boss + key)
PIECES['MF'] = fm; PIECES['MB'] = bm
# ---------- checks ----------
say('--- wing v2 pieces (right wing; left wing = mirror) ---')
def fit(g):
    best = None
    for a in range(0, 180, 2):
        b = affinity.rotate(g, a, origin='centroid').bounds; e = (b[2] - b[0], b[3] - b[1])
        if best is None or max(e) < max(best[1]): best = (a, e)
    return best[1]
asm = {}
for n, parts in PIECES.items():
    whole = union([m for m in parts.values() if not m.is_empty()])
    bodies = len([q for q in whole.decompose() if q.volume() > 1])
    t = to_t(whole); e = fit(Polygon(t.vertices[:, :2]).convex_hull if False else unary_union([Point(*v) for v in t.vertices[::max(1, len(t.vertices) // 1500), :2]]).convex_hull)
    vol = {c: m.volume() / 1000 for c, m in parts.items()}
    asm[n] = whole
    say(f'{n:3s} bodies {bodies}  footprint {e[0]:5.0f} x {e[1]:5.0f} mm  height {t.bounds[1][2] - t.bounds[0][2]:5.1f}  cm3 navy {vol["navy"]:5.1f} gold {vol["gold"]:5.1f} white {vol["white"]:5.1f}' + ('  ' + str(JOINTS[n][2]) if n in JOINTS else ''))
# interference between pieces (should be ~0: pieces only touch)
names = list(asm)
for i in range(len(names)):
    for j in range(i + 1, len(names)):
        v = (asm[names[i]] ^ asm[names[j]]).volume()
        if v > 0.5: say(f'  overlap {names[i]} / {names[j]}: {v:.1f} mm3')
tot = sum(m.volume() for parts in PIECES.values() for m in parts.values()) / 1000
say(f'total solid volume one wing: {tot:.0f} cm3')
# ---------- save (print orientation: lying flat, z from 0) ----------
FLIP = {'MF', 'MB'}    # medallions turn over for printing: front prints art face down (pegs up), back prints art face up (key up)
TURN = np.array([[1, 0, 0, 0], [0, -1, 0, 0], [0, 0, -1, 0]], np.float32)     # 180 deg about x: a turn, not a mirror
def save(parts, name, mirror=False):
    whole = union([x for x in parts.values() if not x.is_empty()])
    if name in FLIP: whole = whole.transform(TURN)
    if mirror: whole = whole.mirror([1, 0, 0])
    z0 = to_t(whole).bounds[0][2]
    for c, m in parts.items():
        if m.is_empty() or m.volume() < 0.5: continue
        q = m.transform(TURN) if name in FLIP else m
        if mirror: q = q.mirror([1, 0, 0])
        t = to_t(q); t.apply_translation([0, 0, -z0])
        t.export(f'{OUT2}wing2_{name}{"_L" if mirror else ""}_{c}.stl')
for n, parts in PIECES.items():
    save(parts, n)
    if n in ('MF', 'MB'): save(parts, n, mirror=True)
# assembled (right wing, wing frame) for checks / pictures
pickle.dump({n: {c: to_t(m) for c, m in p.items() if not m.is_empty()} for n, p in PIECES.items()}, open('ref2/wing2_assembled.pkl', 'wb'))
open(OUT2 + 'build_report.txt', 'w').write('\n'.join(rep) + '\n')
