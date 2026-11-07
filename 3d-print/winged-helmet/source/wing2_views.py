# view meshes for the v2 wing: on the helmet, flat front / back, exploded, joint close-up
import pickle, json, numpy as np, trimesh, os, math
exec(open('wing_build.py').read().split("if __name__ == '__main__':")[0])
A = pickle.load(open('ref2/wing2_assembled.pkl', 'rb'))
Vd = 'helmet/out_v23/view/'
C = np.array(MED_C)
def per_colour(fn):
    out = {'navy': [], 'gold': [], 'white': []}
    for n, parts in A.items():
        for c, t in parts.items():
            m = fn(n, to_m(t))
            if m is not None: out[c].append(m)
    return {c: union(v) for c, v in out.items()}
# 1 on the helmet (right wing; the scene mirrors it for the left)
for c, m in per_colour(lambda n, m: placed(m)).items(): to_t(m).export(Vd + f'wing2R_{c}.stl')
# 2 flat, assembled
for c, m in per_colour(lambda n, m: m).items(): to_t(m).export(Vd + f'wing2_flat_{c}.stl')
# 3 exploded: feathers out along their direction, collars a little, medallions lifted off both faces
def explode(n, m):
    if n == 'MF': return m.translate([0, 0, 45])
    if n == 'MB': return m.translate([0, 0, -45])
    b = np.array(m.bounding_box()).reshape(2, 3).mean(0)[:2]
    d = b - C; d = d / (np.linalg.norm(d) + 1e-9)
    k = 12 if n in ('CU', 'CL') else 42
    return m.translate([d[0] * k, d[1] * k, 0])
for c, m in per_colour(explode).items(): to_t(m).export(Vd + f'wing2_explode_{c}.stl')
# 4 joint close-up: cut lengthwise through F1's tongue and its socket in the upper collar; F1 pulled back 10 mm
J = pickle.load(open('ref2/wing2_joints.pkl', 'rb'))
tg, sk, info = J['joints']['F1']
sc = np.array([sk.centroid.x, sk.centroid.y])
fo = np.array(J['outl']['F1'].centroid.coords[0]); dirv = fo - sc; dirv /= np.linalg.norm(dirv)       # out of the collar
ang = math.degrees(math.atan2(dirv[1], dirv[0]))
keep = m3.Manifold.cube([400, 300, 60]).translate([-200, -300, -30]).rotate([0, 0, ang]).translate([sc[0], sc[1], 0])   # the side right of the tongue axis
reg = m3.Manifold.cube([80, 70, 60]).translate([-50, -35, -30]).rotate([0, 0, ang]).translate([sc[0], sc[1], 0])
for c, t in A['CU'].items():
    to_t((to_m(t) ^ keep) ^ reg).export(Vd + f'wing2_joint_cu_{c}.stl')
reg2 = m3.Manifold.cube([55, 70, 60]).translate([-25, -35, -30]).rotate([0, 0, ang]).translate([sc[0], sc[1], 0])
for c, t in A['F1'].items():
    m = ((to_m(t) ^ keep) ^ reg2).translate([dirv[0] * 28, dirv[1] * 28, 0])
    to_t(m).export(Vd + f'wing2_joint_f1_{c}.stl')
perp = np.array([-dirv[1], dirv[0]])
ctr = sc + dirv * 14
eye = ctr - perp * 120 - dirv * 15
json.dump({'ctr': ctr.tolist(), 'eye': eye.tolist()}, open('ref2/wing2_joint_cam.json', 'w'))
print('views written')
