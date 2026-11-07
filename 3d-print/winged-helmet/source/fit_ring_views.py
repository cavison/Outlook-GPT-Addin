# views of the fit rings: assembled helmet ring (pieces coloured), exploded, head ring
import pickle, numpy as np, trimesh
A = pickle.load(open('ref2/fit_ring.pkl', 'rb'))
V = 'helmet/out_v23/view/'
for n, t in A.items(): t.export(V + f'fit_{n}.stl')
# exploded: each ring piece pulled outward 25 mm, front/back lifted 15 mm (as if about to slide up into the sides)
off = {'front': (0, -25, -12), 'back': (0, 25, -12), 'side_R': (25, 0, 0), 'side_L': (-25, 0, 0)}
for n, d in off.items():
    t = A[n].copy(); t.apply_translation(d); t.export(V + f'fit_x_{n}.stl')
print('ok')
