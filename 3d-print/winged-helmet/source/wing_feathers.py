"""Feather layout inside the traced wing outline (full-size mm, u = back, v = up).
Builds each feather as its own shape so colour schemes can be applied per feather part:
  - primaries: long upper feathers between the outline's notches, running parallel to the wing
  - hanging feathers: fan down from the shoulder, each with its own tip notch
  - coverts: two rows of small scalloped feathers round the shoulder
  - eagle: round spot at the shoulder kept free for the eagle-head logo
All lines are >= 3 mm at full size so they survive at the 5-inch scale (~0.31)."""
import re, json, math
import numpy as np
from shapely.geometry import Polygon, LineString, Point, MultiPolygon
from shapely.ops import unary_union, split
from shapely import affinity

s = open('helmet/wing_outline.scad').read()
P = np.array([[float(a), float(b)] for a, b in re.findall(r'\[([-\d.]+), ([-\d.]+)\]', s)])
WING = Polygon(P).buffer(0)
C = np.array([14.0, 38.0])            # shoulder / eagle centre
EAGLE_R = 42.0
RING_R = 64.0                         # inner scallop ring: a true circle round the eagle
# the medallion and its ring are a full circle; the wing outline bulges just enough to hold it
WING = WING.union(Point(*C).buffer(RING_R + 7, 128)).buffer(0)
GROOVE = 3.2                          # gap between feathers
SHAFT = 3.0                           # centre shaft width
MARGIN = 6.0                          # feather edge band width

def ray(p, d, L=600): return LineString([tuple(p), tuple(np.array(p) + np.array(d) / np.linalg.norm(d) * L)])
def ang(a): return np.array([math.cos(math.radians(a)), math.sin(math.radians(a))])
def pieces(geom):
    return [g for g in (geom.geoms if hasattr(geom, 'geoms') else [geom]) if g.area > 1]

# ---------------- coverts and eagle ----------------
eagle = Point(*C).buffer(EAGLE_R, 96)
WING_DIR = 32                         # the upper wing runs this way (degrees)
def along(g, k):                      # stretch along the wing direction, about the shoulder
    g = affinity.rotate(g, -WING_DIR, origin=tuple(C)); g = affinity.scale(g, k, 1, origin=tuple(C))
    return affinity.rotate(g, WING_DIR, origin=tuple(C))
def lobe_row(r_in, r_out, a0, a1, n, k):
    """a row of n separate rounded scallop feathers between angles a0..a1 (before stretching)"""
    w = (a1 - a0) / n; out = []
    for i in range(n):
        lo, hi = a0 + w * i, a0 + w * (i + 1); a = (lo + hi) / 2
        lobe = affinity.scale(Point(0, 0).buffer(1, 48), (r_out - r_in) * 0.62, r_out * math.radians(w) * 0.62)
        lobe = affinity.translate(affinity.rotate(lobe, a, origin=(0, 0)), *(C + ang(a) * (r_in + (r_out - r_in) * 0.6)))
        wedge = Polygon([tuple(C)] + [tuple(C + ang(lo + (hi - lo) * j / 12) * 400) for j in range(13)])
        body = Point(*C).buffer(r_in + (r_out - r_in) * 0.45, 96).union(lobe).intersection(wedge)
        out.append(along(body, k))
    return out
COV1_RAW = lobe_row(EAGLE_R, RING_R, -180, 180, 12, 1.0)   # 12 equal scallops, no stretch
COV2_RAW = lobe_row(EAGLE_R, 88, -125, 100, 9, 1.3)
# two more scallops carry the outer row up to the top edge, over the joint between the shoulder
# section and the top long feathers, so that joint hides under them like the others
SEAM = [(95.0, 158.5), (121.2, 116.6)]
_sd = ang(32); _sa, _sb = np.array(SEAM[0]), np.array(SEAM[1]); SEAM_LOBES = []
for t in (0.27, 0.76):
    c0 = _sa + (_sb - _sa) * t + _sd * 6
    lobe = affinity.rotate(affinity.scale(Point(0, 0).buffer(1, 48), 24, 17), WING_DIR, origin=(0, 0))
    lobe = affinity.translate(lobe, *c0).union(Point(*(c0 - _sd * 14)).buffer(17, 48)).difference(unary_union(COV2_RAW))
    COV2_RAW.append(lobe); SEAM_LOBES.append(lobe)
cov1 = unary_union(COV1_RAW).intersection(WING)
cov2 = unary_union(COV2_RAW).intersection(WING)
coverts_zone = cov2.union(cov1).union(eagle).intersection(WING)

# ---------------- primaries: separators from the upper notches, parallel to the wing ----------------
NOTCH_UP = [(187.0, 213.0), (110.9, 110.4), (105.3, 84.7), (87.5, 56.1), (84.6, 34.9)]
SEP_BACK = 30                         # separators start this far behind each notch (inside or not)
FLOW = ang(212)                       # down-and-forward along the wing
upper_region = WING.difference(Point(*C).buffer(1, 4))   # placeholder
# split line between the upper wing and the hanging feathers: from the notch at the back corner to the shoulder
SPLIT_UL = LineString([(78.4, 13.7), tuple(C)])
# primaries are the parts of the wing above SPLIT_UL, outside the coverts
cut_poly = Polygon([(78.4, 13.7), (400, 13.7 - 40), (400, 600), (-300, 600), (-300, C[1] + 60), tuple(C)])
upper = WING.intersection(cut_poly)
lower = WING.difference(cut_poly)
# top separator: from its notch down to the coverts, splitting the big leading feather in two
seps_up = [LineString([(187.0 + 20, 213.0 + 12), (187.0, 213.0), (100, 150), tuple(np.array((100, 150)) + FLOW * 300)])]
seps_up += [ray(np.array(n) - FLOW * SEP_BACK, FLOW, 700) for n in NOTCH_UP[1:]]
prim = [upper]
for sp in seps_up:
    nxt = []
    for g in prim:
        nxt += pieces(split(g, sp)) if g.intersects(sp) else [g]
    prim = nxt
def merge_small(gs, min_area=700):
    gs = [g for g in gs if g.area > 5]
    while True:
        small = [g for g in gs if g.area < min_area]
        if not small: return gs
        g = min(small, key=lambda q: q.area); gs.remove(g)
        nb = max(gs, key=lambda q: q.buffer(0.5).intersection(g.buffer(0.5)).area)
        gs.remove(nb); gs.append(unary_union([nb, g.buffer(0.01)]).buffer(0))
prim = sorted(merge_small(prim), key=lambda g: -g.centroid.y)

# ---------------- hanging feathers: fan from the shoulder ----------------
HANG_A = np.linspace(-123, -36, 8)    # separator angles (7 feathers)
hang = [lower]
for a in HANG_A[1:-1]:
    sp = ray(C, ang(a))
    nxt = []
    for g in hang:
        nxt += pieces(split(g, sp)) if g.intersects(sp) else [g]
    hang = nxt
hang = sorted(merge_small(hang), key=lambda g: math.atan2(g.centroid.y - C[1], g.centroid.x - C[0]))
# a small V notch at the outline end of each hanging separator, so each feather gets its own tip
notches = []
for a in HANG_A[1:-1]:
    r = ray(C, ang(a)); hit = r.intersection(WING.exterior)
    pts = [hit] if hit.geom_type == 'Point' else list(getattr(hit, 'geoms', []))
    if not pts: continue
    q = max(pts, key=lambda p: Point(*C).distance(p))
    q = np.array(q.coords[0]); d = ang(a); n = np.array([-d[1], d[0]])
    notches.append(Polygon([tuple(q + d * 2), tuple(q - d * 16 + n * 0.01), tuple(q + n * 5.5), tuple(q - n * 5.5)]).convex_hull)
NOTCH = unary_union(notches)

def feather_parts(g, axis_dir, tip_first=False):
    """vane, outer margin band, shaft for one feather polygon"""
    g = g.difference(NOTCH).buffer(-GROOVE / 2, join_style=1).buffer(0)
    if g.is_empty: return None
    # shaft: line through the feather along axis_dir, through its centroid
    c = np.array(g.centroid.coords[0])
    sh = LineString([tuple(c - axis_dir * 400), tuple(c + axis_dir * 400)]).buffer(SHAFT / 2, cap_style=2).intersection(g.buffer(-4))
    margin = g.difference(g.buffer(-MARGIN, join_style=1))
    return dict(full=g, margin=margin, shaft=sh, inner=g.buffer(-MARGIN, join_style=1))

PRIM = [feather_parts(g.difference(coverts_zone), -FLOW) for g in prim]
HANG = []
for g in hang:
    c = np.array(g.centroid.coords[0]); d = (c - C) / np.linalg.norm(c - C)
    HANG.append(feather_parts(g.difference(coverts_zone), d))
COV1 = [g.intersection(WING).difference(eagle).buffer(-GROOVE / 2, join_style=1) for g in COV1_RAW]
COV2 = [g.intersection(WING).difference(cov1).difference(eagle).buffer(-GROOVE / 2, join_style=1) for g in COV2_RAW]
COV1 = [g for g in COV1 if not g.is_empty and g.area > 20]; COV2 = [g for g in COV2 if not g.is_empty and g.area > 20]
EAGLE = eagle.intersection(WING)
import pickle
pickle.dump(dict(WING=WING, PRIM=PRIM, HANG=HANG, COV1=COV1, COV2=COV2, EAGLE=EAGLE, C=C, cov1=cov1, cov2=cov2, SEAM_LOBES=SEAM_LOBES),
            open('ref2/wing_feathers.pkl', 'wb'))
print('primaries', len(PRIM), 'hanging', len(HANG), 'coverts', len(COV1), len(COV2))

# ---------------- per-feather helpers for colour schemes ----------------
def centre_line(g, d, n=40):
    """mid-line of a feather polygon along direction d (smoothed polyline)"""
    d = np.array(d) / np.linalg.norm(d); nrm = np.array([-d[1], d[0]])
    xy = np.array(g.exterior.coords); t = xy @ d; t0, t1 = t.min(), t.max()
    pts = []
    for k in range(1, n):
        tt = t0 + (t1 - t0) * k / n
        c0 = d * tt
        seg = LineString([tuple(c0 - nrm * 500), tuple(c0 + nrm * 500)]).intersection(g)
        if seg.is_empty: continue
        segs = list(getattr(seg, 'geoms', [seg]))
        s0 = max(segs, key=lambda q: q.length)
        pts.append(np.array(s0.interpolate(0.5, normalized=True).coords[0]))
    pts = np.array(pts)
    if len(pts) > 4:
        from scipy.ndimage import gaussian_filter1d
        pts = np.stack([gaussian_filter1d(pts[:, 0], 2, mode='nearest'), gaussian_filter1d(pts[:, 1], 2, mode='nearest')], 1)
    return pts
def tip_part(g, d, frac):
    """the part of the feather beyond frac of its length along d"""
    d = np.array(d) / np.linalg.norm(d); nrm = np.array([-d[1], d[0]])
    t = np.vstack([np.array(q.exterior.coords) for q in getattr(g, 'geoms', [g])]) @ d; tc = t.min() + (t.max() - t.min()) * frac
    c = d * tc
    hp = Polygon([tuple(c - nrm * 600), tuple(c + nrm * 600), tuple(c + nrm * 600 + d * 900), tuple(c - nrm * 600 + d * 900)])
    return g.intersection(hp)
def side_part(g, line, side):
    """the part of a feather on one side (+1 / -1) of its centre line"""
    if len(line) < 2: return g
    a, b = line[0], line[-1]; d = (b - a) / np.linalg.norm(b - a); nrm = np.array([-d[1], d[0]]) * side
    poly = [tuple(p) for p in [a - d * 400] + list(line) + [b + d * 400]]
    poly += [tuple(b + d * 400 + nrm * 600), tuple(a - d * 400 + nrm * 600)]
    return g.intersection(Polygon(poly).buffer(0))
for kind, dirs in (('PRIM', None), ('HANG', None)):
    pass
for i, f in enumerate(PRIM):
    if f is None: continue
    f['axis'] = -FLOW
for f in HANG:
    if f is None: continue
    c = np.array(f['full'].centroid.coords[0]); f['axis'] = (c - C) / np.linalg.norm(c - C)
for f in PRIM + HANG:
    if f is None: continue
    g = f['full'] if f['full'].geom_type == 'Polygon' else max(f['full'].geoms, key=lambda q: q.area)
    f['line'] = centre_line(g, f['axis'])
    f['shaft'] = LineString([tuple(p) for p in f['line']]).buffer(SHAFT / 2, cap_style=1).intersection(f['full'].buffer(-3.5)) if len(f['line']) > 1 else None
    f['tip40'] = tip_part(f['full'], f['axis'], 0.60)
    f['tip25'] = tip_part(f['full'], f['axis'], 0.75)
    f['upper'] = side_part(f['full'], f['line'], +1)
    f['lower'] = side_part(f['full'], f['line'], -1)
    nrm = np.array([-f['axis'][1], f['axis'][0]])
    f['edge_lo'] = f['full'].difference(affinity.translate(f['full'], *(nrm * MARGIN)))     # band along the lower / trailing side
pickle.dump(dict(WING=WING, PRIM=PRIM, HANG=HANG, COV1=COV1, COV2=COV2, EAGLE=EAGLE, C=C, cov1=cov1, cov2=cov2, SEAM_LOBES=SEAM_LOBES),
            open('ref2/wing_feathers.pkl', 'wb'))
print('helpers added')

# smooth tip zones: everything beyond a scaled copy of the wing outline (about the shoulder)
from shapely import affinity as _aff
for k, frac in (('tipzone', 0.80),):
    inner = _aff.scale(WING, frac, frac, origin=tuple(C))
    for f in PRIM + HANG:
        if f is None: continue
        f[k] = f['full'].difference(inner)
pickle.dump(dict(WING=WING, PRIM=PRIM, HANG=HANG, COV1=COV1, COV2=COV2, EAGLE=EAGLE, C=C, cov1=cov1, cov2=cov2, SEAM_LOBES=SEAM_LOBES),
            open('ref2/wing_feathers.pkl', 'wb'))
