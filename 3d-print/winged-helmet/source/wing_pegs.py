"""Snap pegs for the wing: 3 per section joining the three layers, 2 per section joint (tuck strips)."""
import pickle, numpy as np
from shapely.ops import unary_union, polylabel
from shapely.geometry import Point
exec(open('wing_pieces.py').read().split("if __name__ == '__main__':")[0].replace("print(", "(lambda *a, **k: None)("))
F = pickle.load(open('ref2/wing_feathers.pkl', 'rb'))
raised = unary_union([f['full'] for f in F['PRIM'] + F['HANG'] if f] + [F['cov1'], F['cov2'], F['EAGLE']]).buffer(-5)
def spread(region, n, min_gap=22):
    """n points well inside region, spread apart (farthest-point sampling on an inner grid)"""
    inner = region.buffer(-4)
    if inner.is_empty: inner = region
    x0, y0, x1, y1 = inner.bounds
    grid = [(x, y) for x in np.arange(x0, x1, 2) for y in np.arange(y0, y1, 2) if inner.contains(Point(x, y))]
    if not grid: return []
    g = np.array(grid)
    d_edge = np.array([inner.exterior.distance(Point(*p)) if inner.geom_type == 'Polygon' else 0 for p in g])
    pts = [g[np.argmax(d_edge)]]
    while len(pts) < n:
        dmin = np.min([np.linalg.norm(g - p, axis=1) for p in pts], axis=0)
        score = dmin + 0.5 * d_edge
        i = np.argmax(score)
        if dmin[i] < min_gap: break
        pts.append(g[i])
    return pts
LAYER, JOINT = [], []
for i, (k, g) in enumerate(PIECES):
    reg = g.buffer(-6).intersection(raised)
    regs = sorted(getattr(reg, 'geoms', [reg]), key=lambda q: -q.area)
    LAYER += spread(regs[0], 3, 14)
    if i > 0:                                   # feather sections: pegs in the strip under the scallops
        tuck = g.intersection(cov.difference(seam_lobes) if i != 1 else cov.difference(seam_lobes))
        tr = sorted(getattr(tuck, 'geoms', [tuck]), key=lambda q: -q.area) if not tuck.is_empty else []
        if tr: JOINT += spread(tr[0], 2, 15)
    if i == 2:                                  # top long feathers tuck under the seam scallops of section 2
        t2 = g.intersection(seam_lobes)
        if not t2.is_empty: JOINT += spread(max(getattr(t2, 'geoms', [t2]), key=lambda q: q.area), 2, 12)
with open('helmet/wing_pegs.scad', 'w') as f:
    f.write('// Wing snap pegs (full-size mm, u, v): 3 per section join the front half, white middle and back half;\n')
    f.write('// 2 per section joint, in the strip that tucks under the scallops.\n')
    f.write('WG_PEGS = [' + ', '.join(f'[{p[0]:.1f}, {p[1]:.1f}]' for p in LAYER) + '];\n')
    f.write('WG_JOINT_PEGS = [' + ', '.join(f'[{p[0]:.1f}, {p[1]:.1f}]' for p in JOINT) + '];\n')
pickle.dump(dict(LAYER=LAYER, JOINT=JOINT), open('ref2/wing_pegs.pkl', 'wb'))
print('layer pegs', len(LAYER), 'joint pegs', len(JOINT))
