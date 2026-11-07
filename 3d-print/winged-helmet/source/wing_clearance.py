"""Overlap volume and smallest surface gap between the right wing and the helmet pieces."""
import sys, trimesh, numpy as np
from scipy.spatial import cKDTree
D = sys.argv[1] if len(sys.argv) > 1 else 'helmet/out_v18'
wing = [trimesh.load(f'{D}/wing_{c}.stl') for c in ('navy', 'gold', 'white')]
wpts = np.vstack([w.sample(80000) for w in wing]); tree = cKDTree(wpts)
names = ['out_v13/upper_front', 'out_v13/upper_back', 'out_v13/neck', 'out_v13/guard_navy', 'out_v13/guard_gold',
         'out_v14/band_navy', 'out_v14/band_gold', 'out_v14/band_white', 'out_v14/crest_gold', 'out_v14/crest_white']
worst = (1e9, '')
for n in names:
    m = trimesh.load(f'helmet/{n}.stl')
    ov = sum(trimesh.boolean.intersection([w, m], engine='manifold').volume for w in wing)
    hp = m.sample(60000); d, _ = tree.query(hp)
    print('%-22s overlap %7.1f mm3   smallest gap %5.1f mm' % (n, ov, d.min()))
    if d.min() < worst[0]: worst = (d.min(), n, hp[np.argmin(d)])
print('closest:', worst[1], round(worst[0], 1), 'mm at', worst[2].round(0))
