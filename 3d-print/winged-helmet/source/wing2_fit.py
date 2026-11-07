# the new wing on the helmet: clearance to the shell + band, key in the mount block
import pickle, numpy as np, trimesh, manifold3d as m3
exec(open('wing_build.py').read().split("if __name__ == '__main__':")[0])
A = pickle.load(open('ref2/wing2_assembled.pkl', 'rb'))
SOLID = to_m(trimesh.load('helmet/out_v23/solid_out.stl'))
import glob
band = union([to_m(trimesh.load(f)) for f in glob.glob('helmet/out_v23/print/band_*.stl')])
mount = to_m(trimesh.load('helmet/out_v23/print/wing_mount_R_navy.stl'))
helmet = SOLID + band
wing = {n: placed(union([to_m(t) for t in parts.values()])) for n, parts in A.items()}
allw = union(list(wing.values()))
print('wing vs helmet shell+band overlap mm3:', round((allw ^ helmet).volume(), 1))
for n, w in wing.items():
    v = (w ^ mount).volume()
    if v > 0.05: print('  touches mount block:', n, round(v, 2), 'mm3')
# smallest gap helmet -> wing (excluding the key / boss of the back medallion)
pts = to_t(allw).sample(40000)
ht = to_t(helmet)
from trimesh.proximity import ProximityQuery
d = ProximityQuery(ht).signed_distance(pts[:20000])
print('closest wing point to helmet surface: %.1f mm (positive = inside helmet)' % (d.max()))
print('wing points within 3 mm of the helmet:', int((d > -3).sum()), 'of', len(d))
