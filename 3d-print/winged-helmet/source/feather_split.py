# find the individual feathers in the wing artwork
import pickle, numpy as np, math, json, re
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union
from shapely import affinity
report = []; log = print
src = open('wing_build.py').read()
exec(src[src.index('T, MID_T = '):src.index('# ---------- sections ----------')])
plate = WG['WG_PLATE']
def comps(g, a=20): return [q for q in getattr(g, 'geoms', [g]) if q.geom_type == 'Polygon' and q.area > a]
def fit(g):
    best = None
    for a in range(0, 180, 2):
        b = affinity.rotate(g, a, origin='centroid').bounds; e = (b[2] - b[0], b[3] - b[1])
        if best is None or max(e) < max(best[1]): best = (a, e)
    return best[1]
L1 = unary_union([WG['WG_L1_NAVY'], WG['WG_L1_GOLD'], WG['WG_L1_WHITE']])
L2 = unary_union([WG['WG_L2_GOLD'], WG['WG_L2_WHITE']])
L3 = unary_union([WG['WG_L3_NAVY'], WG['WG_L3_GOLD']])
for name, g in (('L1 feathers', L1), ('L2 scallops', L2), ('L3 cell ring', L3)):
    cs = comps(g.buffer(0.6).buffer(-0.6))
    print(name, len(cs))
    for c in sorted(cs, key=lambda c: -c.area):
        e = fit(c); r0 = min(Point(MED_C).distance(Point(x)) for x in c.exterior.coords)
        print(f'   area {c.area/100:6.1f} cm2   fits {e[0]:4.0f} x {e[1]:4.0f} mm   starts {r0:4.0f} mm from centre')
pickle.dump(dict(L1=L1, L2=L2, L3=L3, plate=plate, MED_C=MED_C, MED_R=MED_R, WG=WG, LOGO=LOGO, disc=disc, ring=ring), open('ref2/feather_split.pkl', 'wb'))
