import sys, numpy as np, trimesh
from PIL import Image
x0, x1, z0, z1, res = [float(a) for a in sys.argv[1:6]]
xs = np.arange(x0, x1, res); zs = np.arange(z1, z0, -res)
X, Z = np.meshgrid(xs, zs)
orig = np.stack([X.ravel(), np.full(X.size, -500.0), Z.ravel()], 1); dirs = np.tile([0, 1.0, 0], (X.size, 1))
ims = []
for f, c in [('bandL_white', (200,200,200)), ('bandL_gold', (210,160,30)), ('bandL_navy', (60,80,160))]:
    m = trimesh.load(f'helmet/out_v21/{f}.stl')
    loc, ri, _ = m.ray.intersects_location(orig, dirs, multiple_hits=False)
    col = np.full((X.size, 3), 255, np.uint8); col[ri[loc[:, 1] < 0]] = c
    ims.append(Image.fromarray(col.reshape(X.shape + (3,))))
w, h = ims[0].size; out = Image.new('RGB', (w * 3 + 20, h), 'black')
for i, im in enumerate(ims): out.paste(im, (i * (w + 10), 0))
out.save(sys.argv[6])
