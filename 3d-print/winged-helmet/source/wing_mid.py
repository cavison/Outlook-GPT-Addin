"""Second (middle) feather layer: one feather in every gap of the traced outline, with a pointed tip.
The middle layer is a full core between the wing's front and back halves; only the gap feathers show."""
import pickle, numpy as np, math
from shapely.geometry import Point, Polygon, MultiPoint
from shapely.ops import unary_union
from shapely import affinity
D = pickle.load(open('ref2/wing_feathers.pkl', 'rb')); W = D['WING']; C = np.array(D['C'])
ENV = W.buffer(30, join_style=1).buffer(-30, join_style=1)
gaps = [g for g in getattr(ENV.difference(W), 'geoms', [ENV.difference(W)]) if g.area > 30]
FILL = []
for g in gaps:
    xy = np.array(g.exterior.coords)
    if g.centroid.x < 0: continue                       # front edge (faces the helmet): keep as traced
    if Point(187, 213).distance(g) < 25: continue        # step in the top edge: keep the traced silhouette
    r = np.linalg.norm(xy - C, axis=1)
    E = xy[np.argmin(r)]; T = xy[np.argmax(r)]           # deep end of the slot, outer middle
    L = np.linalg.norm(T - E)
    if L < 8: continue
    d = (T - E) / L
    w = max(4.0, 2.2 * g.area / L)                       # roughly the slot width
    P1 = E - d * 30                                      # carry on under the upper feathers (hidden)
    P2 = E + d * L * 0.62
    blade = MultiPoint([tuple(P1)]).buffer(w + 6).union(Point(*P2).buffer(w + 4)).convex_hull
    blade = unary_union([blade, Polygon([tuple(P2 + np.array([-d[1], d[0]]) * (w + 4)), tuple(T + d * 2), tuple(P2 - np.array([-d[1], d[0]]) * (w + 4))])]).convex_hull
    FILL.append(blade.intersection(ENV.buffer(2)))
MID = unary_union([W] + FILL).buffer(0)
VIS = MID.difference(W)
# colours: navy feathers with gold tips (same sweep as the outer feathers), visible right through
TIP = affinity.scale(W, 0.80, 0.80, origin=tuple(C))
MID_GOLD = MID.difference(TIP).intersection(unary_union(FILL)).difference(W.buffer(-3))
MID_NAVY = MID.difference(MID_GOLD)
def ringset(geom):
    out = []
    for q in getattr(geom, 'geoms', [geom]):
        if q.geom_type != 'Polygon' or q.area < 0.5: continue
        for r in [q.exterior] + list(q.interiors):
            a = np.array(r.coords)[:-1]
            if len(a) >= 3: out.append(a)
    return out
with open('helmet/wing_mid.scad', 'w') as f:
    f.write('// Middle feather layer (full-size mm): a core between the wing halves; its gap feathers fill the slots.\n')
    rs = ringset(MID.simplify(0.05))
    f.write('WG_MID = [\n' + ',\n'.join('  [' + ','.join(f'[{x:.2f},{y:.2f}]' for x, y in r) + ']' for r in rs) + '\n];\n')
pickle.dump(dict(MID=MID, VIS=VIS, MID_GOLD=MID_GOLD, MID_NAVY=MID_NAVY, FILL=FILL), open('ref2/wing_mid.pkl', 'wb'))
print('gap feathers', len(FILL), 'visible area %.0f mm2' % VIS.area)
