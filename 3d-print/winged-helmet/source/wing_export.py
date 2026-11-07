"""Export the gold-tipped wing (scheme B) as layered colour regions for OpenSCAD.
Levels (raised above the navy wing plate):
  L1 long + hanging feathers, L2 outer scallop row, L3 inner scallop row, L4 eagle medallion.
Writes helmet/wing_geom.scad (full-size mm, u = back, v = up)."""
import pickle, re, math
import numpy as np
from shapely.geometry import Polygon, Point, MultiPolygon
from shapely.ops import unary_union
from shapely import affinity
D = pickle.load(open('ref2/wing_feathers.pkl', 'rb'))
C = D['C']; WING = D['WING']
def U(gs): return unary_union([g for g in gs if g is not None and not g.is_empty]).buffer(0)
# ---- L1: long + hanging feathers: navy, gold tips, white shafts
feathers = [f for f in D['PRIM'] + D['HANG'] if f is not None]
l1_all = U([f['full'] for f in feathers])
l1_white = U([f['shaft'] for f in feathers if f['shaft'] is not None])
l1_gold = U([f['tipzone'] for f in feathers]).difference(l1_white)
l1_navy = l1_all.difference(l1_gold).difference(l1_white)
# ---- L2: outer scallops: gold body, white rim
cov2 = U(D['COV2']); cov2_body = U([g.buffer(-3.5, join_style=1) for g in D['COV2']])
l2_gold = cov2_body; l2_white = cov2.difference(cov2_body)
# ---- L3: inner scallops: navy body, gold rim
cov1 = U(D['COV1']); cov1_body = U([g.buffer(-4.5, join_style=1) for g in D['COV1']])
l3_navy = cov1_body; l3_gold = cov1.difference(cov1_body)
# ---- L4: eagle medallion: gold ring, navy field; logo placed in the SCAD file
med = D['EAGLE']
R_MED = 42.0; RING = 3.5
# logo fit: largest logo (with its navy halo) that fits inside the ring, with the best offset
s = open('helmet/eagle_logo.scad').read()
def sets(name):
    block = s.split(name + ' = [')[1].split('];')[0]
    return [np.array([[float(a) for a in q.split(',')] for q in re.findall(r'\[([-\d.]+,[-\d.]+)\]', p)])
            for p in re.findall(r'\[(\[[-\d.]+,[-\d.]+\](?:,\[[-\d.]+,[-\d.]+\])*)\]', block)]
sil = unary_union([Polygon(p).buffer(0) for p in sets('LOGO_SIL')])
best = None
inner = Point(0, 0).buffer(R_MED - RING - 1.0, 128)
for w in np.arange(40, 80, 0.5):
    g = affinity.scale(sil, w, w, origin=(0, 0)).buffer(1.5)
    ok = None
    for dx in np.arange(-8, 8.1, 1):
        for dy in np.arange(-8, 8.1, 1):
            if inner.contains(affinity.translate(g, dx, dy)): ok = (dx, dy); break
        if ok: break
    if ok: best = (w, ok)
print('logo fits at width %.1f mm, offset %s' % (best[0], best[1]))
def ringset(geom):
    out = []
    for g in getattr(geom, 'geoms', [geom]):
        if g.geom_type != 'Polygon' or g.area < 0.5: continue
        for r in [g.exterior] + list(g.interiors):
            a = np.array(r.coords)[:-1]
            if len(a) >= 3: out.append(a)
    return out
def fmt(name, geom):
    rs = ringset(geom.simplify(0.05))
    return f"{name} = [\n" + ",\n".join("  [" + ",".join(f"[{x:.2f},{y:.2f}]" for x, y in r) + "]" for r in rs) + "\n];\n"
with open('helmet/wing_geom.scad', 'w') as f:
    f.write('// Gold-tipped wing, layered colour regions (full-size mm, u = back, v = up).\n')
    f.write('// Each set is a list of rings, nested rings are holes (even-odd).\n')
    f.write(fmt('WG_PLATE', WING))
    for n, g in (('WG_L1_NAVY', l1_navy), ('WG_L1_GOLD', l1_gold), ('WG_L1_WHITE', l1_white),
                 ('WG_L2_GOLD', l2_gold), ('WG_L2_WHITE', l2_white), ('WG_L3_NAVY', l3_navy), ('WG_L3_GOLD', l3_gold)):
        f.write(fmt(n, g))
    f.write(f'WG_MED_C = [{C[0]:.2f}, {C[1]:.2f}];\nWG_MED_R = {R_MED};\nWG_MED_RING = {RING};\n')
    f.write(f'WG_LOGO_W = {best[0]:.1f};\nWG_LOGO_OFF = [{best[1][0]:.1f}, {best[1][1]:.1f}];\n')
    f.write('''module wg_set(set) {
    pts   = [for (p = set) each p];
    start = [for (i = [0:len(set)-1]) i == 0 ? 0 : len([for (j = [0:i-1]) each set[j]])];
    polygon(pts, [for (i = [0:len(set)-1]) [for (k = [0:len(set[i])-1]) start[i] + k]]);
}
''')
print('areas mm2: L1 navy %.0f gold %.0f white %.0f | L2 gold %.0f white %.0f | L3 navy %.0f gold %.0f' %
      (l1_navy.area, l1_gold.area, l1_white.area, l2_gold.area, l2_white.area, l3_navy.area, l3_gold.area))
