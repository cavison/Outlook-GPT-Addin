# the v2 wing on the helmet: overlap with shell + band, key vs mount block, closest gap per piece
import pickle, glob, numpy as np, trimesh, manifold3d as m3
from trimesh.proximity import ProximityQuery
exec(open('wing_build.py').read().split("if __name__ == '__main__':")[0])
A = pickle.load(open('ref2/wing2_assembled.pkl', 'rb'))
SOLID = to_m(trimesh.load('helmet/out_v23/solid_out.stl'))
band = union([to_m(trimesh.load(f)) for f in glob.glob('helmet/out_v23/print/band_*.stl')])
mount = to_m(trimesh.load('helmet/out_v23/print/wing_mount_R_navy.stl'))
helmet = SOLID + band
wing = {n: placed(union([to_m(t) for t in parts.values()])) for n, parts in A.items()}
allw = union(list(wing.values()))
print('wing vs helmet shell+band overlap mm3:', round((allw ^ helmet).volume(), 1))
for n, w in wing.items():
    v = (w ^ mount).volume()
    if v > 0.05: print('  touches mount block:', n, round(v, 2), 'mm3')
from scipy.spatial import cKDTree
ht = to_t(helmet)
hp, _ = trimesh.sample.sample_surface_even(ht, 600000)       # ~0.3 mm spacing on the helmet surface
tree = cKDTree(np.vstack([hp, ht.vertices]))
rows = []
for n, w in wing.items():
    t = to_t(w)
    pts = np.vstack([t.vertices, trimesh.sample.sample_surface(t, 20000)[0]])
    dd, _ = tree.query(pts)
    rows.append((n, float(dd.min())))
for n, d in sorted(rows, key=lambda r: r[1]):
    print(f'  {n:3s} closest to the helmet {d:5.1f} mm')
