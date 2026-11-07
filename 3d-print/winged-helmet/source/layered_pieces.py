# split the three single-colour layers of one wing into printable pieces, seams staggered between layers
import pickle, numpy as np, math
from shapely.ops import unary_union
from shapely import affinity
from shapely.geometry import Polygon
d = pickle.load(open('ref2/layered_concept.pkl', 'rb')); plate, V = d['plate'], d['V']
PIECES = pickle.load(open('ref2/wing_pieces.pkl', 'rb'))['PIECES']
P = [g.buffer(0) for _, g in PIECES]
def parts(g, a=4.0): return [q for q in getattr(g, 'geoms', [g]) if q.geom_type == 'Polygon' and q.area > a]
def fit(g):
    best = None
    for a in range(0, 180, 3):
        b = affinity.rotate(g, a, origin='centroid').bounds; e = (b[2] - b[0], b[3] - b[1])
        if best is None or max(e) < max(best[1]): best = (a, e)
    return best[1]
# non-overlapping sections: shoulder | front edge + top feathers | lower feathers | hanging feathers
S, used = [], Polygon()
for i, g in enumerate(P):
    S.append(g.difference(used)); used = used.union(g)
SECT = [S[0], unary_union([S[1], S[2]]), S[3], S[4]]
def regions(shift):
    """the section map moved by 'shift' mm so each layer's seams fall somewhere else"""
    out, used = [], Polygon()
    for k, g in enumerate(SECT):
        r = affinity.translate(g, *shift).buffer(0) if k else g
        r = r.difference(used); used = used.union(r); out.append(r)
    out[0] = out[0].union(plate.difference(used))            # whatever is left over goes to the shoulder piece
    return out
WHITE_BASE = plate
GOLD = plate.difference(V['white']).buffer(-0.01).buffer(0.01)
NAVY = plate.difference(V['gold'].union(V['white'])).buffer(-0.01).buffer(0.01)
layers = {}
for name, g, shift in (('white', WHITE_BASE, (0, 0)), ('gold', GOLD, (14, -12)), ('navy', NAVY, (-12, 14))):
    pcs = []
    for r in regions(shift):
        pcs += parts(g.intersection(r).buffer(0))
    big = [p for p in pcs if max(fit(p)) > 210]
    layers[name] = pcs
    print(f'{name:6s} {len(pcs):3d} pieces  (>= 20 cm2: {sum(p.area >= 2000 for p in pcs)}, small: {sum(p.area < 2000 for p in pcs)})  too big for the bed: {len(big)}')
pickle.dump(dict(layers=layers, SECT=SECT, plate=plate, V=V, d=d), open('ref2/layered_pieces.pkl', 'wb'))
