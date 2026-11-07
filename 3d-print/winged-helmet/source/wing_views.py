# assembled wing (placed on the helmet) and an exploded flat wing, for pictures
import glob, numpy as np, trimesh
exec(open('wing_build.py').read().split("if __name__ == '__main__':")[0])
PW, V = 'helmet/out_v23/print_wing/', 'helmet/out_v23/view/'
os.makedirs(V, exist_ok=True)
L = lambda f: to_m(trimesh.load(f))
cols = {'navy': [], 'gold': [], 'white': []}
ex = {'navy': [], 'gold': [], 'white': []}
centre = np.array(MED_C)
for f in sorted(glob.glob(PW + 'wing_*_A_*.stl')):
    base = os.path.basename(f); c = base.rsplit('_', 1)[1][:-4]
    m = L(f); mk = L(PW + 'wing_shoulder_Akey_navy.stl') if base == 'wing_shoulder_A_navy.stl' else m
    cols[c] += [front_frame(m), back_frame(mk)]
    sec = base[len('wing_'):].split('_A_')[0]
    cen = np.array(m.bounding_box()).reshape(2, 3).mean(0)[:2] if sec != 'shoulder' else centre
    d = cen - centre; d = d / (np.linalg.norm(d) + 1e-9) * (0 if sec == "shoulder" else 48)
    ex[c] += [front_frame(m).translate([d[0], d[1], 40]), back_frame(mk).translate([d[0], d[1], -40])]
for f in glob.glob(PW + 'wing_*_core_white.stl'):
    m = L(f).translate([0, 0, -MID_T / 2]); cols['white'].append(m)
    sec = os.path.basename(f)[len('wing_'):].split('_core')[0]
    cen = np.array(m.bounding_box()).reshape(2, 3).mean(0)[:2] if sec != 'shoulder' else centre
    d = cen - centre; d = d / (np.linalg.norm(d) + 1e-9) * (0 if sec == "shoulder" else 48)
    ex['white'].append(m.translate([d[0], d[1], 0]))
for c in cols:
    to_t(placed(union(cols[c]))).export(V + f'wingR_{c}.stl')
    to_t(union(ex[c])).export(V + f'wing_exploded_{c}.stl')
print('ok')
