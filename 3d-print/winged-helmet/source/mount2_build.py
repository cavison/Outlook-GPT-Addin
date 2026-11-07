#!/usr/bin/env python
# Straight wings: new wing mount blocks that hold each wing parallel to the side of the head (yaw 15 -> 0, lean kept).
# Fixed by what is printed:
#   * the shell's 4 peg holes per side  -> the 4 pegs are rebuilt exactly as before (same spots, same axis);
#   * the back medallions' dovetail key -> the wing is turned about a vertical line through the key, so the key and
#     the medallion stay where they are and only turn; the socket turns with them.
# Nothing else changes; the shell files are only read.
import glob, os, json, numpy as np, trimesh, manifold3d as m3
exec(open('wing_build.py').read().split("if __name__ == '__main__':")[0])
PR, NEWB, OUT = 'helmet/out_v23/print/', 'helmet/out_v23/print_band2/', 'helmet/out_v23/print_mount2/'
os.makedirs(OUT, exist_ok=True)
SOLID = to_m(trimesh.load('helmet/out_v23/solid_out.stl'))
SHELL_T = trimesh.load('helmet/out_v22/shell_nose.stl')
W_SHELL, BOSS_H = 2.4, 2.0
rep = []
def say(*a):
    s = ' '.join(str(x) for x in a); print(s, flush=True); rep.append(s)
U0, U1 = K_U - 33, K_U + 14
V0, V1 = K_V - KEY_LEN / 2 - 4, K_V + 24
def frame_m(p, n):
    n = np.asarray(n, float) / np.linalg.norm(n); z = np.array([0, 0, 1.]); v = np.cross(z, n); c = float(np.dot(z, n))
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]]); R = np.eye(3) + vx + vx @ vx / (1 + c)
    return np.hstack([R, np.asarray(p, float).reshape(3, 1)]).astype(np.float32)
def ccyl(p, d, r, a0, a1):
    return m3.Manifold.cylinder(a1 - a0, r, r, 32).translate([0, 0, a0]).transform(frame_m(p, d))
def shell_hit(o, d):
    loc, _, tri = SHELL_T.ray.intersects_location([o], [d], multiple_hits=True)
    if len(loc) == 0: return None
    k = np.argmin(np.dot(loc - o, d)); return loc[k]
def band_env_of(folder):
    b = union([to_m(trimesh.load(f)) for f in glob.glob(folder + 'band_*.stl')])
    return b + b.scale([1.015, 1.015, 1.0]).translate([0, 0, 1.0])
def build(M, band_env, peg_from=None):
    """the block for wing placement M; pegs from peg_from = (spots, nrm) or computed from M as the old build did"""
    BACK = M @ Tr(0, 0, -MID_T / 2) @ np.diag([1, 1, -1, 1])
    to_world = lambda m: m.transform(BACK[:3, :].astype(np.float32))
    pt_world = lambda u, v, h: (BACK @ np.array([u, v, h, 1.0]))[:3]
    raw = to_world(m3.Manifold.cube([U1 - U0, V1 - V0, 80]).translate([U0, V0, BLOCK_FACE]))
    block = raw - SOLID - to_world(socket_local()) - band_env
    nrm = BACK[:3, 2] / np.linalg.norm(BACK[:3, 2])
    if peg_from is None:
        spots = [shell_hit(pt_world(u, v, BLOCK_FACE + 1), nrm) for u, v in ((U0 + 9, V0 + 8), (U0 + 9, V1 - 8), (U1 - 8, V0 + 8), (U1 - 8, V1 - 8))]
        pnrm = nrm
    else:
        spots, pnrm = peg_from
    pegs = []
    for p in spots:
        r = 2.5
        body = ccyl(p, pnrm, r, -3.0, W_SHELL + BOSS_H - 0.9) + m3.Manifold.cylinder(0.52, r, r - 0.3, 32).translate([0, 0, W_SHELL + BOSS_H - 0.92]).transform(frame_m(p, pnrm))
        ribs = [m3.Manifold.cylinder(W_SHELL + BOSS_H - 0.8 + 3.0, 0.3, 0.3, 8).translate([r * np.cos(a), r * np.sin(a), -3.0]).transform(frame_m(p, pnrm)) for a in (0, 2.0944, 4.1888)]
        pegs.append(union([body] + ribs))
    return block, union(pegs), (spots, pnrm), nrm, raw
# ---------- 1. reproduce the printed mount exactly (proves the pegs below are the printed ones) ----------
old_env = band_env_of(PR)
blk_o, pegs_o, peg_spec, nrm_old, raw_o = build(PLACE, old_env)
R_old = blk_o + pegs_o
printed = to_m(trimesh.load(PR + 'wing_mount_R_navy.stl'))
dv = abs(R_old.volume() - printed.volume()); dx = (R_old ^ printed).volume()
say(f'old right mount rebuilt: volume {R_old.volume() / 1000:.3f} vs printed {printed.volume() / 1000:.3f} cm3, shared {dx / printed.volume() * 100:.3f}%')
assert dv < 2.0 and dx / printed.volume() > 0.999
# ---------- 2. straight placement: undo the yaw about a vertical line through the key ----------
w_key = -(MID_T / 2 + ROOT_TOP + KEY_D / 2)
c = (PLACE @ np.array([K_U, K_V, w_key, 1.0]))[:3]
PLACE2 = Tr(*c) @ Rz(YAW) @ Tr(*(-c)) @ PLACE
np.save('ref2/place_straight.npy', PLACE2)
new_env = band_env_of(NEWB)
blk_n, pegs_n, _, nrm_new, raw_n = build(PLACE2, new_env, peg_from=peg_spec)
# the pegs' outer ends (3 mm above the shell) must sit in the block: add a pad round each peg if the new outline misses one
pads = []
for p in peg_spec[0]:
    pad = (ccyl(p, peg_spec[1], 5.0, -9.0, 0.0) - SOLID - new_env)
    if (blk_n ^ ccyl(p, peg_spec[1], 2.6, -3.0, -0.2)).volume() < 0.95 * (np.pi * 2.6 ** 2 * 2.8): pads.append(pad)
say(f'pegs needing an extra pad: {len(pads)}')
if pads: blk_n = blk_n + union(pads)
block_R = blk_n + pegs_n
block_L = (blk_n.mirror([1, 0, 0]) - new_env) + pegs_n.mirror([1, 0, 0])
for nm, b in (('R', block_R), ('L', block_L)):
    bodies = len([q for q in b.decompose() if q.volume() > 1])
    t = to_t(b); t.export(OUT + f'wing_mount_{nm}_navy.stl')
    say(f'new {nm} mount: {bodies} body, {b.volume() / 1000:.1f} cm3 (old {printed.volume() / 1000:.1f})')
# ---------- 3. checks ----------
shell = to_m(trimesh.load(PR + 'shell_front_navy.stl')) + to_m(trimesh.load(PR + 'shell_back_navy.stl'))
po, pn = (pegs_o ^ shell).volume(), (pegs_n ^ shell).volume()
say(f'pegs vs printed shell: old {po:.2f} mm3, new {pn:.2f} mm3 (press-fit ribs only; identical = same holes)')
assert abs(po - pn) < 0.01
others = []
for f in sorted(glob.glob(PR + '*.stl')):
    n = os.path.basename(f)[:-4]
    if n.startswith(('wing_mount', 'seam_dowel', 'nose_pin', 'cheek_rivet', 'shell_')): continue
    others.append((n, to_m(trimesh.load(NEWB + n + '.stl' if os.path.exists(NEWB + n + '.stl') else f))))
others.append(('shell', shell))
for side, b in (('R', blk_n), ('L', blk_n.mirror([1, 0, 0]) - new_env)):
    for n, m in others:
        v = (b ^ m).volume()
        if v > 0.3: say(f'  !! {side} block body overlaps {n}: {v:.1f} mm3')
# wing in its new pose against the new block: only the key in its socket and the root disc on the face
import pickle
A = pickle.load(open('ref2/wing2_assembled.pkl', 'rb'))
for n, p in A.items():
    w = union([to_m(t) for t in p.values()]).transform(PLACE2[:3, :].astype(np.float32))
    v = (w ^ blk_n).volume()
    if v > 0.05: say(f'  !! wing piece {n} overlaps the new block: {v:.2f} mm3')
say(f'push-on direction of the pegs vs the new face: {np.degrees(np.arccos(abs(np.dot(nrm_old, nrm_new)))):.1f} deg apart')
json.dump({'place2': PLACE2.tolist(), 'nrm_new': nrm_new.tolist(), 'nrm_old': nrm_old.tolist()}, open('ref2/mount2.json', 'w'))
open(OUT + 'report.txt', 'w').write('\n'.join(rep) + '\n')
