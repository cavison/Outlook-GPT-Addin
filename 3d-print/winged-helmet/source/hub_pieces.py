# final concept pieces: feathers with hidden roots, collars reaching under the medallion rim, medallions
import pickle, numpy as np, math
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union
from shapely import affinity
h = pickle.load(open('ref2/hub_regions.pkl', 'rb')); REG, MED, C, plate = h['REG'], h['MED'], h['C'], h['plate']
FEATHERS = [n for n in REG if n[0] in 'PH']; COLLARS = ['CU', 'CL']
ROOT = 22.0                                   # how far each feather tucks under the collars / medallion rim
RIM_IN = 50.0                                 # collars and roots reach in to this radius, under the medallion rim
hub_zone = unary_union([REG['CU'], REG['CL'], MED.difference(Point(*C).buffer(RIM_IN, 256))])
# share the hidden zone out: every point goes to the nearest feather, so roots never overlap
grid = []
pieces = {}
for n in FEATHERS:
    others = unary_union([REG[m] for m in FEATHERS if m != n])
    near = REG[n].buffer(ROOT, 16).intersection(hub_zone)
    # keep only the part closer to this feather than to any other (approximate Voronoi by sampling)
    xs = np.linspace(near.bounds[0], near.bounds[2], 60); ys = np.linspace(near.bounds[1], near.bounds[3], 60)
    keep = []
    for x in xs:
        for y in ys:
            p = Point(x, y)
            if near.contains(p) and REG[n].distance(p) <= others.distance(p): keep.append(p.buffer(0.8 * math.hypot(xs[1] - xs[0], ys[1] - ys[0]), 4))
    root = unary_union(keep).intersection(near).buffer(-1.0).buffer(1.0) if keep else Polygon()
    pieces[n] = unary_union([REG[n], root]).buffer(0.01).buffer(-0.01)
    pieces[n + '_root'] = root
for n in COLLARS:
    reg = REG[n]
    # angular span of the collar, extended under the medallion rim
    angs = [math.atan2(y - C[1], x - C[0]) for x, y in reg.exterior.coords if Point(x, y).distance(Point(*C)) < 80]
    a = np.unwrap(sorted(angs)); a0, a1 = min(a), max(a)
    wedge = Polygon([tuple(C)] + [(C[0] + 200 * math.cos(t), C[1] + 200 * math.sin(t)) for t in np.linspace(a0, a1, 60)])
    rim = MED.difference(Point(*C).buffer(RIM_IN, 256)).intersection(wedge)
    pieces[n] = unary_union([reg, rim]).buffer(0.01).buffer(-0.01)
pieces['MED'] = MED
def fit(g):
    best = None
    for a in range(0, 180, 2):
        b = affinity.rotate(g, a, origin='centroid').bounds; e = (b[2] - b[0], b[3] - b[1])
        if best is None or max(e) < max(best[1]): best = (a, e)
    return best[1]
rows = []
for n in FEATHERS + COLLARS + ['MED']:
    g = pieces[n]; e = fit(g)
    # straight length along the piece (longest extent at its best turn)
    L = max(max(affinity.rotate(g, a, origin='centroid').bounds[2] - affinity.rotate(g, a, origin='centroid').bounds[0] for a in range(0, 180, 2)), 0)
    rows.append((n, g.area / 100, e, L))
    print(f'{n:4s} area {g.area/100:6.1f} cm2   longest {L:5.0f} mm   fits in {e[0]:4.0f} x {e[1]:4.0f} mm   {"OK for 210" if max(e) <= 205 else "NEEDS A SPLIT"}')
pickle.dump(dict(pieces=pieces, REG=REG, MED=MED, C=C, plate=plate, rows=rows, FEATHERS=FEATHERS, COLLARS=COLLARS, RIM_IN=RIM_IN), open('ref2/hub_pieces.pkl', 'wb'))
