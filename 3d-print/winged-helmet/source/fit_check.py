# Assembled fit check: every pair of print pieces, overlap volume (pegs' crush ribs give small expected overlaps)
import glob, os, itertools, numpy as np, trimesh, manifold3d as m3
D = 'helmet/out_v23/print/'
def to_m(t): return m3.Manifold(m3.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))
parts = {}
for f in sorted(glob.glob(D + '*.stl')):
    n = os.path.basename(f)[:-4]
    if n == 'seam_dowel_pin_navy': continue
    t = trimesh.load(f); parts[n] = (to_m(t), t.bounds)
names = list(parts); rows = []
for a, b in itertools.combinations(names, 2):
    (ma, ba), (mb, bbx) = parts[a], parts[b]
    if np.any(ba[1] < bbx[0] - 0.5) or np.any(bbx[1] < ba[0] - 0.5): continue
    v = (ma ^ mb).volume()
    if v > 0.05: rows.append((v, a, b))
for v, a, b in sorted(rows, reverse=True): print(f'{v:9.2f} mm3  {a}  x  {b}')
print('pairs overlapping:', len(rows))
