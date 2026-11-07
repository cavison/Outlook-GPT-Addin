#!/usr/bin/env python
# Wing print pieces: 5 sections x (front half, white middle, back half), built flat in the wing's own
# frame (u back, v up, w out of the wing; w = 0 is the middle of the white core).
#   * halves are multi-colour (navy / gold / white parts of one piece), decorated face up when printed
#   * where a feather section tucks under the shoulder's scallops, the lower piece owns the plate and
#     the upper piece's scallops lie on it as a lip; the white core splits at the visible scallop edge,
#     so core joints and plate joints never line up
#   * 3 pegs per section join core and halves; 2 pegs per tuck joint go from the lip through the plate
#   * the right wing's back half carries a dovetail key behind the eagle; it slides down into a mount
#     block that is pegged into both shell halves across the seam
# Writes STLs to helmet/out_v23/print_wing/ and a placement file for the assembled views.
import json, os, pickle, re
import numpy as np, trimesh, manifold3d as m3
from shapely.geometry import Polygon, MultiPolygon, Point, box
from shapely.ops import unary_union
from shapely import affinity

OUT = 'helmet/out_v23/print_wing/'; os.makedirs(OUT, exist_ok=True)
T, MID_T = 2.5, 4.0                          # half plate, white core
H = [2.0, 3.4, 4.8, 5.6, 6.6]                 # decoration heights above the plate
CLR = 0.2
report = []
def log(*a):
    s = ' '.join(str(x) for x in a); print(s); report.append(s)

# ---------- 2D data ----------
def rings(name, path):
    return json.loads(re.search(name + r' = (\[.*?\]);', open(path).read(), re.S).group(1))
def eo(rs, scale=1.0, off=(0, 0)):
    g = Polygon()
    for r in rs:
        p = Polygon([(x * scale + off[0], y * scale + off[1]) for x, y in r]).buffer(0)
        g = g.symmetric_difference(p)
    return g.buffer(0)
G = 'helmet/wing_geom.scad'
WG = {n: eo(rings(n, G)) for n in ('WG_PLATE', 'WG_L1_NAVY', 'WG_L1_GOLD', 'WG_L1_WHITE', 'WG_L2_GOLD', 'WG_L2_WHITE', 'WG_L3_NAVY', 'WG_L3_GOLD')}
MID = eo(rings('WG_MID', 'helmet/wing_mid.scad'))
MED_C, MED_R, MED_RING, LOGO_W, LOGO_OFF = np.array([14.0, 38.0]), 42.0, 3.5, 64.5, np.array([-2.0, -6.0])
lo = np.array(MED_C + LOGO_OFF)
LOGO = {n: eo(rings(n, 'helmet/eagle_logo.scad'), LOGO_W, lo) for n in ('LOGO_SIL', 'LOGO_WHITE', 'LOGO_GOLD')}
halo = LOGO['LOGO_SIL'].buffer(1.5)
disc = Point(*MED_C).buffer(MED_R - MED_RING, 192); ring = Point(*MED_C).buffer(MED_R, 192).difference(disc)
med = Point(*MED_C).buffer(MED_R, 192)

# column claims: each feature owns its column from the plate up to its top; higher features win
L1 = unary_union([WG['WG_L1_NAVY'], WG['WG_L1_GOLD'], WG['WG_L1_WHITE']])
L2 = unary_union([WG['WG_L2_GOLD'], WG['WG_L2_WHITE']])
L3 = unary_union([WG['WG_L3_NAVY'], WG['WG_L3_GOLD']])
c3 = L3.difference(med); c2 = L2.difference(L3).difference(med); c1 = L1.difference(L2).difference(L3).difference(med)
FEAT = {   # colour: list of (2D region, w0, w1) relative to the half's base (w = 0 on the core)
    'navy': [(WG['WG_PLATE'], 0, T), (WG['WG_L1_NAVY'].intersection(c1), T, T + H[0]), (WG['WG_L3_NAVY'].intersection(c3), T, T + H[2]),
             (disc, T, T + H[3]), (halo.difference(LOGO['LOGO_WHITE']).difference(LOGO['LOGO_GOLD']).intersection(disc), T + H[3], T + H[4])],
    'gold': [(WG['WG_L1_GOLD'].intersection(c1), T, T + H[0]), (WG['WG_L2_GOLD'].intersection(c2), T, T + H[1]),
             (WG['WG_L3_GOLD'].intersection(c3), T, T + H[2]), (ring, T, T + H[3]), (LOGO['LOGO_GOLD'], T + H[3], T + H[4])],
    'white': [(WG['WG_L1_WHITE'].intersection(c1), T, T + H[0]), (WG['WG_L2_WHITE'].intersection(c2), T, T + H[1]),
              (LOGO['LOGO_WHITE'], T + H[3], T + H[4])],
}
def top_height():
    """2D map of decoration height above the plate, as (region, height) list, highest first"""
    return [(med, H[3]), (c3, H[2]), (c2, H[1]), (c1, H[0])]

# ---------- sections ----------
PIECES = pickle.load(open('ref2/wing_pieces.pkl', 'rb'))['PIECES']
NAMES = ['shoulder', 'front_edge', 'top_feathers', 'lower_feathers', 'hanging_feathers']
P = [g.buffer(0) for _, g in PIECES]
N = len(P)
# a scallop lobe lying wholly over a tuck strip has nothing of its own piece under it (the lobes do not
# touch each other or the inner row): give the upper piece a pad of plate under the lobe's inner end and
# across the little gap to the inner row, until every upper piece is one connected part again
_deco = unary_union([eo(rings(n, G)) for n in ('WG_L1_NAVY', 'WG_L1_GOLD', 'WG_L1_WHITE', 'WG_L2_GOLD', 'WG_L2_WHITE', 'WG_L3_NAVY', 'WG_L3_GOLD')]
                    + [Point(*MED_C).buffer(MED_R, 192)])
def _parts(g): return [q for q in getattr(g, 'geoms', [g]) if q.geom_type == 'Polygon' and q.area > 2]
for it in range(4):
    changed = False
    for i in range(N - 1):
        below = [j for j in range(i + 1, N) if P[i].intersection(P[j]).area > 50]
        if not below: continue
        strips = unary_union([P[i].intersection(P[j]) for j in below])
        plate_i = P[i].difference(unary_union([P[j] for j in range(i + 1, N)]))
        mat = unary_union([plate_i, _deco.intersection(P[i].difference(unary_union(P[:i])) if i else P[i])]).buffer(0)
        comps = sorted(_parts(mat), key=lambda q: -q.area)
        if len(comps) < 2: continue
        for c in comps[1:]:
            for j in below:
                vis = P[j].difference(unary_union(P[:j]))
                for lobe in _parts(_deco.intersection(c)):
                    if lobe.intersection(P[j]).area < 2: continue
                    dmax = max(vis.distance(Point(q)) for q in lobe.exterior.coords)
                    pad = P[j].intersection(P[i]).intersection(lobe.buffer(3.0)).difference(vis.buffer(max(dmax - 5.0, 6.0)))
                    if pad.area > 1: P[j] = P[j].difference(pad).buffer(0); changed = True
    if not changed: break
upper = [unary_union([P[j] for j in range(i)]) if i else Polygon() for i in range(N)]       # pieces above i (lower index)
lower = [unary_union([P[j] for j in range(i + 1, N)]) if i < N - 1 else Polygon() for i in range(N)]
# lap joint: in an overlap the lower piece's plate tucks under, the upper piece's scallops lie on it as a lip;
# the white core there belongs to the upper piece, so the core joint (scallop edge) is not the plate joint
PLATE_OWN = [P[i].difference(lower[i]) for i in range(N)]
DEC_OWN = [P[i].difference(upper[i]) for i in range(N)]
HALF_OWN = DEC_OWN
CORE_REG = DEC_OWN
# the white core also fills the slots between feathers: split each slot between the sections around it
# by distance (grow every section outwards 1 mm at a time and let it claim what it reaches first)
gaps = MID.difference(unary_union(P))
CORE_OWN = [MID.intersection(CORE_REG[i]) for i in range(N)]
left = gaps
for r in np.arange(1.0, 120.0, 1.0):
    if left.is_empty or left.area < 0.5: break
    for i in range(N):
        got = CORE_REG[i].buffer(r).intersection(left)
        if got.area > 0:
            CORE_OWN[i] = CORE_OWN[i].union(got); left = left.difference(got)
CORE_OWN = [c.buffer(0.01).buffer(-0.01) for c in CORE_OWN]

# ---------- mesh helpers ----------
def to_t(m): g = m.to_mesh(); return trimesh.Trimesh(np.asarray(g.vert_properties)[:, :3], np.asarray(g.tri_verts), process=False)
def to_m(t): return m3.Manifold(m3.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))
def union(ms):
    ms = [m for m in ms if m is not None and not m.is_empty()]
    return m3.Manifold.batch_boolean(ms, m3.OpType.Add) if ms else m3.Manifold()
def polys(g):
    if g.is_empty: return []
    return [q for q in getattr(g, 'geoms', [g]) if q.geom_type == 'Polygon' and q.area > 0.05]
def extrude(g, w0, w1):
    """2D region (u, v) extruded between w0 and w1"""
    out = []
    for q in polys(g.buffer(0)):
        cs = m3.CrossSection([np.asarray(q.exterior.coords)[:-1]] + [np.asarray(h.coords)[:-1] for h in q.interiors], m3.FillRule.EvenOdd)
        out.append(cs.extrude(w1 - w0).translate([0, 0, w0]))
    return union(out)
def cyl(p, r, w0, w1, seg=32): return m3.Manifold.cylinder(w1 - w0, r, r, seg).translate([p[0], p[1], w0])
def peg(p, d, w0, w1, up=True):
    """press-fit peg along w (up) or -w, with 3 crush ribs and a chamfered tip"""
    r = d / 2
    if up:
        b = cyl(p, r, w0, w1 - 0.5) + m3.Manifold.cylinder(0.52, r, r - 0.3, 32).translate([p[0], p[1], w1 - 0.52])
        ribs = [cyl((p[0] + r * np.cos(a), p[1] + r * np.sin(a)), 0.3, w0, w1 - 0.8, 8) for a in (0, 2.0944, 4.1888)]
    else:
        b = cyl(p, r, w0 + 0.5, w1) + m3.Manifold.cylinder(0.52, r - 0.3, r, 32).translate([p[0], p[1], w0])
        ribs = [cyl((p[0] + r * np.cos(a), p[1] + r * np.sin(a)), 0.3, w0 + 0.8, w1, 8) for a in (0, 2.0944, 4.1888)]
    return union([b] + ribs)
def hole(p, d, w0, w1): return cyl(p, (d + CLR) / 2, w0, w1)

# ---------- peg spots ----------
def spread(region, n, min_gap, taken=(), inset=4.0):
    inner = region.buffer(-inset)
    if inner.is_empty: return []
    x0, y0, x1, y1 = inner.bounds
    pts = np.array([(x, y) for x in np.arange(x0, x1, 1.5) for y in np.arange(y0, y1, 1.5) if inner.contains(Point(x, y))])
    if len(pts) == 0: return []
    de = np.array([inner.boundary.distance(Point(*p)) for p in pts])
    out = []
    while len(out) < n:
        if out:
            dmin = np.min([np.linalg.norm(pts - q, axis=1) for q in out + list(taken)], axis=0)
        else:
            dmin = np.min([np.linalg.norm(pts - q, axis=1) for q in taken], axis=0) if len(taken) else np.full(len(pts), 99.)
        score = np.minimum(dmin, 60) + 0.6 * de
        score[dmin < min_gap] = -1
        i = int(np.argmax(score))
        if score[i] < 0: break
        out.append(pts[i])
    return out
deco_any = unary_union([c1, c2, c3, med])
LAYER_PEGS, JOINT_PEGS = {}, {}
taken = []
# a half can fall into separate parts (a feather that only joined its section through a strip now padded
# for the scallops): each part becomes its own print piece with its own pegs into the section's core
HALF_PARTS = {}
for i in range(N):
    mat = unary_union([PLATE_OWN[i], deco_any.intersection(DEC_OWN[i])]).buffer(0)
    HALF_PARTS[i] = sorted([q for q in polys(mat) if q.area > 50], key=lambda q: -q.area)
for i in range(N):
    spots_all = []
    for k, part in enumerate(HALF_PARTS[i]):
        reg = part.intersection(DEC_OWN[i]).intersection(PLATE_OWN[i]).intersection(CORE_OWN[i]).intersection(deco_any)
        reg = reg.buffer(-1.5) if k == 0 else reg
        regs = sorted(polys(reg), key=lambda q: -q.area)
        want = 3 if k == 0 else 2
        spots = spread(regs[0], want, (18 if P[i].area > 6000 else 11) if k == 0 else 12, taken, inset=4.0 if k == 0 else 3.1) if regs else []
        taken += spots; spots_all += spots
        if len(spots) < want: log(f'WARNING section {NAMES[i]} part {k}: {len(spots)} layer pegs')
    LAYER_PEGS[i] = spots_all
for i in range(N):
    for j in range(i + 1, N):
        ov = P[i].intersection(P[j])
        if ov.area < 50: continue
        # upper piece i: core + lip; lower piece j: the plate tucked between them. Pegs go from core i
        # through the plate of j into the lip of i
        reg = ov.intersection(deco_any).intersection(PLATE_OWN[j]).intersection(CORE_OWN[i]).intersection(DEC_OWN[i])
        regs = sorted(polys(reg), key=lambda q: -q.area)
        spots = spread(regs[0], 2, 14, taken) if regs else []
        JOINT_PEGS[(i, j)] = spots; taken += spots
        if len(spots) < 2: log(f'WARNING joint {NAMES[i]}/{NAMES[j]}: {len(spots)} pegs')
log('layer pegs per section:', {NAMES[i]: len(v) for i, v in LAYER_PEGS.items()})
log('tuck-joint pegs:', {f'{NAMES[i]}/{NAMES[j]}': len(v) for (i, j), v in JOINT_PEGS.items()})

LP_D, LP_LEN = 5.0, 3.0            # core -> half pegs (blind holes in the half's plate + decoration)
JP_LEN = T + 1.6                   # joint pegs: through the tucked plate, 1.6 into the lip above
def joint(i, role): return [p for (a, b), sp in JOINT_PEGS.items() if (a if role == 'upper' else b) == i for p in sp]
def half_piece(i):
    """front half of section i, flat: base on w = 0 (the core face), decoration up. Returns {colour: Manifold}."""
    cut = union([hole(p, LP_D, -0.1, LP_LEN + 0.2) for p in LAYER_PEGS[i]]
                + [hole(p, LP_D, T - 0.1, JP_LEN + 0.2) for p in joint(i, 'upper')]      # blind, from under the lip
                + [hole(p, LP_D, -0.1, T + 0.1) for p in joint(i, 'lower')])             # through the tucked plate
    out = {}
    for colour, feats in FEAT.items():
        parts = [extrude(reg.intersection(PLATE_OWN[i] if w0 == 0 else DEC_OWN[i]), w0, w1) for reg, w0, w1 in feats]
        m = union(parts)
        out[colour] = m - cut if not m.is_empty() and not cut.is_empty() else m
    # colours must not overlap in a multi-colour piece: the visible top colour wins the slivers
    if not out['white'].is_empty(): out['gold'] = out['gold'] - out['white']
    out['navy'] = out['navy'] - union([out['gold'], out['white']])
    return out
def core_piece(i):
    """the white middle: flat both sides (it prints flat), with through-holes for separate pins that reach
    into both halves - 10 mm pins at the layer spots, 12.2 mm pins at the tuck joints"""
    m = extrude(CORE_OWN[i], -MID_T / 2, MID_T / 2)
    holes = [hole(p, LP_D, -MID_T / 2 - 0.1, MID_T / 2 + 0.1) for p in LAYER_PEGS[i] + joint(i, 'upper')]
    return m - union(holes)
PIN_LAYER = MID_T + 2 * LP_LEN            # 10.0
PIN_JOINT = MID_T + 2 * JP_LEN            # 12.2
def pin(length):
    """round pin with crush ribs and chamfers both ends, standing on its end"""
    r = LP_D / 2
    b = m3.Manifold.cylinder(length - 1.0, r, r, 32).translate([0, 0, 0.5])
    b = b + m3.Manifold.cylinder(0.52, r - 0.4, r, 32) + m3.Manifold.cylinder(0.52, r, r - 0.4, 32).translate([0, 0, length - 0.52])
    for a in (0, 2.0944, 4.1888):
        b = b + m3.Manifold.cylinder(length - 1.6, 0.3, 0.3, 8).translate([r * np.cos(a), r * np.sin(a), 0.8])
    return b

# ---------- placement: flat wing frame -> helmet (right wing) ----------
WPX, PY_, YAW, LEAN, ZB = 103.942, -60.0, 15.0, 4.0, -135.0
def Rz(a): a = np.radians(a); c, s = np.cos(a), np.sin(a); return np.array([[c, -s, 0, 0], [s, c, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])
def Ry(a): a = np.radians(a); c, s = np.cos(a), np.sin(a); return np.array([[c, 0, s, 0], [0, 1, 0, 0], [-s, 0, c, 0], [0, 0, 0, 1]])
def Tr(x, y, z): M = np.eye(4); M[:3, 3] = [x, y, z]; return M
SIDE = np.array([[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1]], float)     # (u, v, w) -> (w, u, v)
PLACE = Tr(WPX, PY_, 0) @ Rz(-YAW) @ Tr(0, -PY_, 0) @ Tr(0, 0, ZB) @ Ry(LEAN) @ Tr(0, 0, -ZB) @ SIDE
def placed(m, M=PLACE): return m.transform(M[:3, :].astype(np.float32))
def front_frame(m): return m.translate([0, 0, MID_T / 2])                                # front half sits on the core's +w face
def back_frame(m): return m.mirror([0, 0, 1]).translate([0, 0, -MID_T / 2])               # back half: mirror through the core

# ---------- mount: dovetail key on the back half's eagle + block on the helmet ----------
K_U, K_V = MED_C
KEY_LEN, KEY_N, KEY_W, KEY_D = 30.0, 12.0, 17.0, 6.5        # length along v, neck width, tip width, depth
ROOT_R, ROOT_TOP = 15.0, T + H[4] + 0.9                   # root disc on the eagle (height above the half's base)
BLOCK_FACE = ROOT_TOP + 0.3
TWIST = np.array([K_U - 24, K_V])
def key_local():
    """on the back half, in its own flat frame (base on the core face, decoration up): root disc + dovetail key + anti-twist peg"""
    root = extrude(Point(*MED_C).buffer(ROOT_R, 96), T + H[3] - 0.3, ROOT_TOP)
    tw_root = extrude(Point(*TWIST).buffer(5, 48), T + H[3] - 0.3, ROOT_TOP)
    w0, w1 = ROOT_TOP - 0.1, ROOT_TOP + KEY_D
    tr = Polygon([(K_U - KEY_N / 2, w0), (K_U + KEY_N / 2, w0), (K_U + KEY_W / 2, w1), (K_U - KEY_W / 2, w1)])
    cs = m3.CrossSection([np.asarray(tr.exterior.coords)[:-1]])
    key = cs.extrude(KEY_LEN).translate([0, 0, K_V - KEY_LEN / 2])                      # (u, w) extruded along "z" = v
    key = key.transform(np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0]], np.float32))  # swap: (u, w, v) -> (u, v, w)
    bump = m3.Manifold.sphere(1.3, 24).translate([K_U, K_V - KEY_LEN / 2 + 5, w1 - 0.8]) ^ cyl((K_U, K_V - KEY_LEN / 2 + 5), 2, w1 - 0.1, w1 + 1)
    twist = cyl(TWIST, 3.0, ROOT_TOP - 0.1, ROOT_TOP + KEY_D)
    return union([root, tw_root, key, bump, twist])
def socket_local():
    """the cut-outs in the block, in the same frame (slides down along -v into place)"""
    w0, w1 = BLOCK_FACE - 0.5, ROOT_TOP + KEY_D + 0.35
    c = 0.3
    tr = Polygon([(K_U - KEY_N / 2 - c, w0), (K_U + KEY_N / 2 + c, w0), (K_U + KEY_W / 2 + c, w1), (K_U - KEY_W / 2 - c, w1)])
    cs = m3.CrossSection([np.asarray(tr.exterior.coords)[:-1]])
    slot = cs.extrude(200).translate([0, 0, K_V - KEY_LEN / 2 - c])
    slot = slot.transform(np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0]], np.float32))
    dimple = m3.Manifold.sphere(1.5, 24).translate([K_U, K_V - KEY_LEN / 2 + 5, w1 - 0.6])
    tslot = union([cyl(TWIST, 3.3, BLOCK_FACE - 0.5, ROOT_TOP + KEY_D + 0.4),
                   m3.Manifold.cube([6.6, 200, ROOT_TOP + KEY_D + 0.9 - BLOCK_FACE]).translate([TWIST[0] - 3.3, TWIST[1], BLOCK_FACE - 0.5])])
    return union([slot, dimple, tslot])

if __name__ == '__main__':
    log('--- wing print pieces (right wing frame) ---')
    halves = {i: half_piece(i) for i in range(N)}
    cores = {i: core_piece(i) for i in range(N)}
    key = key_local()
    def save(m, name):
        comps = sorted([q for q in m.decompose() if q.volume() > 1.0], key=lambda q: -q.volume())
        m = union(comps)
        if len(comps) > 1:
            small = [round(q.volume(), 2) for q in comps[1:]]
            log(f'  !! {name}: {len(comps)} bodies, extra volumes {small[:6]}')
        t = to_t(m); t.export(OUT + name + '.stl')
        return t
    sizes = {}
    for i in range(N):
        nm = NAMES[i]
        for side, flip in (('A', False), ('B', True)):            # A = right front / left back, B = right back / left front
            for k, part in enumerate(HALF_PARTS[i]):
                mask = extrude(part.buffer(0.3), -2, 40)
                pnm = nm if k == 0 else f'{nm}{k + 1}'
                for colour, m in halves[i].items():
                    if m.is_empty(): continue
                    mp = m ^ mask if len(HALF_PARTS[i]) > 1 else m
                    if mp.is_empty() or mp.volume() < 1: continue
                    save(mp.mirror([1, 0, 0]) if flip else mp, f'wing_{pnm}_{side}_{colour}')
            if i == 0:   # keyed versions of the shoulder halves (the side that faces the helmet): the key's
                         # base covers the middle of the eagle, so the gold / white there give way to it
                mk = halves[i]['navy'] + key
                save(mk.mirror([1, 0, 0]) if flip else mk, f'wing_{nm}_{side}key_navy')
                for colour in ('gold', 'white'):
                    mc = halves[i][colour] - key
                    save(mc.mirror([1, 0, 0]) if flip else mc, f'wing_{nm}_{side}key_{colour}')
        save(cores[i].translate([0, 0, MID_T / 2]), f'wing_{nm}_core_white')        # base on z = 0 for printing
        allm = union(list(halves[i].values()))
        bb = np.array(allm.bounding_box()).reshape(2, 3); cb = np.array(cores[i].bounding_box()).reshape(2, 3)
        sizes[nm] = ((bb[1] - bb[0]).round(1).tolist(), (cb[1] - cb[0]).round(1).tolist())
        log(f'  {nm}: half {sizes[nm][0]} mm, core {sizes[nm][1]} mm')
    save(pin(PIN_LAYER), 'wing_pin_layer_white'); save(pin(PIN_JOINT), 'wing_pin_joint_white')
    n_layer = sum(len(v) for v in LAYER_PEGS.values()); n_joint = sum(len(v) for v in JOINT_PEGS.values())
    log(f'  pins per wing: {n_layer} x {PIN_LAYER:.1f} mm, {n_joint} x {PIN_JOINT:.1f} mm')
    pickle.dump(dict(N_PIN_LAYER=n_layer, N_PIN_JOINT=n_joint, LAYER_PEGS=LAYER_PEGS, JOINT_PEGS=JOINT_PEGS, PLATE_OWN=PLATE_OWN, DEC_OWN=DEC_OWN, CORE_OWN=CORE_OWN, PLACE=PLACE),
                open('ref2/wing_build.pkl', 'wb'))
    open(OUT + 'build_report.txt', 'w').write('\n'.join(report) + '\n')
