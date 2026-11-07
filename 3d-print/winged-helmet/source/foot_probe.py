import numpy as np, trimesh, math
src = open('plates_build.py').read()
exec(src[:src.index('# ---------- packing ----------')])
from shapely.geometry import Polygon
from shapely.ops import unary_union
def sec_area(m, z):
    s = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    if s is None: return 0.0
    pl, _ = s.to_planar()
    return float(sum(p.area for p in pl.polygons_full))
for p in P:
    if p['group'] == 'multi' or p['settings'] == 'pin': continue
    parts = oriented(p)
    m = trimesh.util.concatenate([q for q, _ in parts])
    zs = (0.1, 0.25, 0.5, 1.0, 2.0, 5.0)
    print('%-28s %s' % (p['name'], '  '.join('z%.2g:%6.0f' % (z, sec_area(m, z)) for z in zs)))
