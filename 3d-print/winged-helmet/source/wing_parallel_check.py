# Straighten the wings (no yaw, lean kept), pivoting on the dovetail key, optionally pushed out by dx;
# report how close each wing piece comes to the helmet (with the new thicker band) for a few dx values.
import glob, os, sys, pickle, numpy as np, trimesh
exec(open('wing_build.py').read().split("if __name__ == '__main__':")[0])
from scipy.spatial import cKDTree
A = pickle.load(open('ref2/wing2_assembled.pkl', 'rb'))
OLD, NEW = 'helmet/out_v23/print/', 'helmet/out_v23/print_band2/'
helmet = []
for f in sorted(glob.glob(OLD + '*.stl')):
    n = os.path.basename(f)[:-4]
    if n.startswith(('wing_mount', 'seam_dowel', 'nose_pin', 'cheek_rivet')): continue
    helmet.append(trimesh.load(NEW + n + '.stl' if os.path.exists(NEW + n + '.stl') else f))
H = trimesh.util.concatenate(helmet)
tree = cKDTree(np.vstack([H.vertices, trimesh.sample.sample_surface(H, 600000, seed=1)[0]]))
# key centre in the wing frame (u, v, w): dovetail mid-depth behind the back medallion
w_key = -(MID_T / 2 + ROOT_TOP + KEY_D / 2)
key_w = np.array([K_U, K_V, w_key, 1.0])
c = (PLACE @ key_w)[:3]
def pose(dx):
    M = Tr(*c) @ Rz(YAW) @ Tr(*(-c)) @ PLACE           # undo the yaw about a vertical line through the key
    return Tr(dx, 0, 0) @ M
print('key centre (helmet frame):', c.round(1).tolist())
pieces = {n: union([to_m(t) for t in p.values()]) for n, p in A.items()}
samples = {n: np.vstack([to_t(m).vertices, trimesh.sample.sample_surface(to_t(m), 8000, seed=2)[0]]) for n, m in pieces.items()}
def clear(M):
    out = {}
    for n, pts in samples.items():
        P = (np.c_[pts, np.ones(len(pts))] @ M.T)[:, :3]
        out[n] = tree.query(P)[0].min()
    return out
base = clear(PLACE)
print('now (15 deg):  ' + '  '.join(f'{n} {v:.1f}' for n, v in sorted(base.items(), key=lambda kv: kv[1])[:6]))
for dx in [float(a) for a in sys.argv[1:]] or (0.0, 3.0, 6.0, 10.0):
    r = clear(pose(dx))
    worst = sorted(r.items(), key=lambda kv: kv[1])
    tips = (pose(dx) @ np.array([K_U, K_V, 0, 1.0]))[:3]
    print(f'straight dx {dx:4.1f}: medallion centre x {tips[0]:.1f} | ' + '  '.join(f'{n} {v:.1f}' for n, v in worst[:6]))
