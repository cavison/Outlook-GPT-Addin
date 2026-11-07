import glob, numpy as np, trimesh, manifold3d as m3
exec(open('wing_build.py').read().split("if __name__ == '__main__':")[0])
from scipy.spatial import cKDTree
PR, PW = 'helmet/out_v23/print/', 'helmet/out_v23/print_wing/'
L = lambda f: to_m(trimesh.load(f))
block = L(PR + 'wing_mount_R_navy.stl')
helm = {os.path.basename(f)[:-4]: L(f) for f in glob.glob(PR + '*.stl') if 'mount' not in f and 'dowel' not in f}
print('block overlaps with helmet pieces (pegs give ~1-2 mm3 each):')
for n, m in helm.items():
    v = (block ^ m).volume()
    if v > 0.05: print(f'   {n}: {v:.2f} mm3')
# the assembled right wing: front halves (A), back halves (A, with the key on the shoulder), cores
wing = []
for f in sorted(glob.glob(PW + 'wing_*_A_*.stl')):
    m = L(f); base = os.path.basename(f)
    wing.append(placed(front_frame(m)))
    if base == 'wing_shoulder_A_navy.stl': m = L(PW + 'wing_shoulder_Akey_navy.stl')
    wing.append(placed(back_frame(m)))
for f in glob.glob(PW + 'wing_*_core_white.stl'): wing.append(placed(L(f).translate([0, 0, -MID_T / 2])))
wing = union(wing)
print('wing x block: %.2f mm3 (only the catch bump should touch)' % (wing ^ block).volume())
H = union(list(helm.values()))
print('wing x helmet: %.2f mm3' % (wing ^ H).volume())
wt, ht = to_t(wing), to_t(H)
d, _ = cKDTree(ht.sample(300000)).query(wt.sample(300000)); print('min gap wing to helmet: %.1f mm' % d.min())
# sliding on: lift the wing along its own up axis and check the path
up = PLACE[:3, 1] / np.linalg.norm(PLACE[:3, 1])
for s in (8, 16, 24, 32):
    w2 = wing.translate((up * s).tolist())
    print(f'   lifted {s} mm: wing x helmet {(w2 ^ H).volume():.2f} mm3, wing x block {(w2 ^ block).volume():.2f} mm3')
