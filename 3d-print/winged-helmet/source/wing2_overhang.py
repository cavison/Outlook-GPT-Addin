# unsupported area per wing piece, as printed: area of each 0.2 mm layer not over the layer below (grown by 0.3 mm)
import glob, os, numpy as np, trimesh, manifold3d as m3
exec(open('wing_build.py').read().split("if __name__ == '__main__':")[0])
from shapely.geometry import Polygon
from shapely.ops import unary_union
import sys
D = sys.argv[1] if len(sys.argv) > 1 else 'helmet/out_v23/print_wing2/'
PFX = sys.argv[2] if len(sys.argv) > 2 else 'wing2_'
names = sorted({os.path.basename(f)[len(PFX):].rsplit('_', 1)[0] if PFX == 'wing2_' else os.path.basename(f)[len(PFX):-4] for f in glob.glob(D + PFX + '*.stl')})
def section(m, z):
    cs = m.slice(z)
    polys = [Polygon(r) for r in cs.to_polygons() if len(r) >= 3]
    if not polys: return Polygon()
    # even-odd: rings alternate outer / hole
    out = Polygon()
    for q in sorted(polys, key=lambda q: -abs(q.area)):
        q = q.buffer(0)
        out = out.symmetric_difference(q)
    return out
for n in names:
    m = union([to_m(trimesh.load(f)) for f in (glob.glob(D + f'wing2_{n}_*.stl') if PFX == 'wing2_' else [D + PFX + n + '.stl'])])
    z1 = to_t(m).bounds[1][2]; prev = None; worst = []
    for z in np.arange(0.1, z1, 0.2):
        cur = section(m, z)
        if prev is not None:
            un = cur.difference(prev.buffer(0.3))
            big = [g for g in getattr(un, 'geoms', [un]) if g.area > 2.0]
            if big: worst.append((round(z, 1), round(sum(g.area for g in big)), len(big)))
        prev = cur
    first = round(section(m, 0.1).area)
    print(f'{n:6s} first layer {first:6d} mm2   unsupported (z, mm2, islands): {worst[:6]}{" ..." if len(worst) > 6 else ""}')
