import sys, numpy as np, trimesh
from PIL import Image
files = [('helmet/out_v21/shell.stl', (30,40,90)), ('helmet/out_v21/bandL_white.stl', (240,240,240)),
         ('helmet/out_v21/bandL_gold.stl', (210,160,30)), ('helmet/out_v21/bandL_navy.stl', (60,80,160))]
x0, x1, z0, z1, res = [float(a) for a in sys.argv[1:6]]
xs = np.arange(x0, x1, res); zs = np.arange(z1, z0, -res)
X, Z = np.meshgrid(xs, zs)
orig = np.stack([X.ravel(), np.full(X.size, -500.0), Z.ravel()], 1); dirs = np.tile([0, 1.0, 0], (X.size, 1))
best = np.full(X.size, np.inf); col = np.zeros((X.size, 3), np.uint8) + 255
for f, c in files:
    m = trimesh.load(f)
    loc, ri, _ = m.ray.intersects_location(orig, dirs, multiple_hits=False)
    d = loc[:, 1] + 500
    upd = d < best[ri] - 1e-6
    best[ri[upd]] = d[upd]; col[ri[upd]] = c
Image.fromarray(col.reshape(X.shape + (3,))).resize((X.shape[1] * 2, X.shape[0] * 2), Image.NEAREST).save(sys.argv[6])
