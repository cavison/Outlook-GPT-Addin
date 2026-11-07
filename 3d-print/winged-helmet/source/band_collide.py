# new (thicker) band pieces vs every other part of the helmet: overlaps in mm3, and how close the wings come
import glob, os, pickle, numpy as np, trimesh
exec(open('wing_build.py').read().split("if __name__ == '__main__':")[0])
OLD, NEW = 'helmet/out_v23/print/', 'helmet/out_v23/print_band2/'
band_names = sorted(os.path.basename(f)[:-4] for f in glob.glob(NEW + 'band_*.stl'))
new = {n: to_m(trimesh.load(NEW + n + '.stl')) for n in band_names}
others = {}
for f in sorted(glob.glob(OLD + '*.stl')):
    n = os.path.basename(f)[:-4]
    if n.startswith('band_') or n.startswith('seam_dowel') or n.startswith('nose_pin') or n.startswith('cheek_rivet'): continue
    if os.path.exists(NEW + n + '.stl'): f = NEW + n + '.stl'          # use the new version where there is one
    others[n] = to_m(trimesh.load(f))
bad = []
for bn, bm in new.items():
    for on, om in others.items():
        v = (bm ^ om).volume()
        if v > 0.5: bad.append((bn, on, v)); print(f'OVERLAP {bn} x {on}: {v:.1f} mm3')
# band pieces among themselves: they nest (pegs through holes) but must not overlap
names = list(new)
for i in range(len(names)):
    for j in range(i + 1, len(names)):
        v = (new[names[i]] ^ new[names[j]]).volume()
        if v > 0.5: bad.append((names[i], names[j], v)); print(f'OVERLAP {names[i]} x {names[j]}: {v:.1f} mm3')
# wings: nearest approach of the assembled wing to the new band (both sides are mirror images)
A = pickle.load(open('ref2/wing2_assembled.pkl', 'rb'))
wing = to_t(union([placed(union([to_m(t) for t in p.values()])) for p in A.values()]))
from scipy.spatial import cKDTree
bt = to_t(union(list(new.values())))
pts = np.vstack([bt.vertices, trimesh.sample.sample_surface(bt, 200000)[0]])
d, _ = cKDTree(np.vstack([wing.vertices, trimesh.sample.sample_surface(wing, 300000)[0]])).query(pts)
print(f'closest the right wing comes to the band: {d.min():.1f} mm')
print('overlaps found:', len(bad))
pickle.dump(bad, open('ref2/band_collide.pkl', 'wb'))
