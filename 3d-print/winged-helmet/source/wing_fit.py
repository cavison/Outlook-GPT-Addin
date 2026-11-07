import glob, itertools, numpy as np, trimesh
exec(open('wing_build.py').read().split("if __name__ == '__main__':")[0])
D = 'helmet/out_v23/print_wing/'
parts = {}
for f in sorted(glob.glob(D + 'wing_*_A_navy.stl')):
    base = os.path.basename(f)[:-len('_A_navy.stl')]
    cols = [to_m(trimesh.load(g)) for g in glob.glob(D + base + '_A_*.stl')]
    u = union(cols)
    parts[base + ' front'] = front_frame(u); parts[base + ' back'] = back_frame(u)
for f in sorted(glob.glob(D + 'wing_*_core_white.stl')):
    parts[os.path.basename(f)[:-4]] = to_m(trimesh.load(f)).translate([0, 0, -MID_T / 2])
rows = []
for a, b in itertools.combinations(parts, 2):
    v = (parts[a] ^ parts[b]).volume()
    if v > 0.05: rows.append((v, a, b))
for v, a, b in sorted(rows, reverse=True)[:14]: print(f'{v:8.2f} mm3  {a}  x  {b}')
print('pairs touching/overlapping:', len(rows), '  pegs:', sum(len(v) for v in LAYER_PEGS.values()) * 2 + sum(len(v) for v in JOINT_PEGS.values()) * 2)
