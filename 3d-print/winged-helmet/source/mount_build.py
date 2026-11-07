#!/usr/bin/env python
# Wing mount blocks: one each side, shaped to the shell on the inside and flat toward the wing, with a
# dovetail socket (open at the top) that takes the key behind the eagle, a slot for the anti-twist peg,
# and 4 pegs into the shell - two in each shell half, so the block also bridges the front / back seam.
# Run after conn_build.py and wing_build.py: it adds the pegs' holes and bosses to the shell halves.
import numpy as np, trimesh, manifold3d as m3
exec(open('wing_build.py').read().split("if __name__ == '__main__':")[0])
PR = 'helmet/out_v23/print/'
SOLID = to_m(trimesh.load('helmet/out_v23/solid_out.stl'))
SHELL_T = trimesh.load('helmet/out_v22/shell_nose.stl')
W_SHELL, BOSS_H = 2.4, 2.0

BACK = PLACE @ Tr(0, 0, -MID_T / 2) @ np.diag([1, 1, -1, 1])          # back-half frame (h up = toward the helmet)
def to_world(m): return m.transform(BACK[:3, :].astype(np.float32))
def pt_world(u, v, h): return (BACK @ np.array([u, v, h, 1.0]))[:3]

U0, U1 = K_U - 33, K_U + 14
V0, V1 = K_V - KEY_LEN / 2 - 4, K_V + 24
raw = to_world(m3.Manifold.cube([U1 - U0, V1 - V0, 80]).translate([U0, V0, BLOCK_FACE]))
# keep clear of the band layers below it (a slightly enlarged, raised copy of them is cut away)
import glob as _g
_band = union([to_m(trimesh.load(f)) for f in _g.glob(PR + 'band_*.stl')])
band_env = _band + _band.scale([1.015, 1.015, 1.0]).translate([0, 0, 1.0])
block = raw - SOLID - to_world(socket_local()) - band_env
nrm = BACK[:3, 2] / np.linalg.norm(BACK[:3, 2])               # push-on direction (toward the helmet)
log('mount block: %d body, %.0f cm3' % (len(block.decompose()), block.volume() / 1000))

# pegs: at the block's corners, along the push-on direction, into the shell
def shell_hit(o, d):
    loc, _, tri = SHELL_T.ray.intersects_location([o], [d], multiple_hits=True)
    if len(loc) == 0: return None
    k = np.argmin(np.dot(loc - o, d)); return loc[k]
spots = []
for u, v in ((U0 + 9, V0 + 8), (U0 + 9, V1 - 8), (U1 - 8, V0 + 8), (U1 - 8, V1 - 8)):
    o = pt_world(u, v, BLOCK_FACE + 1)
    p = shell_hit(o, nrm)
    spots.append(p)
    log('  peg at u %.0f v %.0f -> world %s' % (u, v, np.round(p, 1).tolist()))
def ccyl(p, d, r, a0, a1):
    return m3.Manifold.cylinder(a1 - a0, r, r, 32).translate([0, 0, a0]).transform(frame_m(p, d))
def frame_m(p, n):
    n = np.asarray(n, float) / np.linalg.norm(n); z = np.array([0, 0, 1.]); v = np.cross(z, n); c = float(np.dot(z, n))
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]]); R = np.eye(3) + vx + vx @ vx / (1 + c)
    return np.hstack([R, np.asarray(p, float).reshape(3, 1)]).astype(np.float32)
pegs, holes, bosses = [], [], []
for p in spots:
    r = 2.5
    body = ccyl(p, nrm, r, -3.0, W_SHELL + BOSS_H - 0.9) + m3.Manifold.cylinder(0.52, r, r - 0.3, 32).translate([0, 0, W_SHELL + BOSS_H - 0.92]).transform(frame_m(p, nrm))
    ribs = [m3.Manifold.cylinder(W_SHELL + BOSS_H - 0.8 + 3.0, 0.3, 0.3, 8).translate([r * np.cos(a), r * np.sin(a), -3.0]).transform(frame_m(p, nrm)) for a in (0, 2.0944, 4.1888)]
    pegs.append(union([body] + ribs))
    holes.append(ccyl(p, nrm, (5 + CLR) / 2, -0.5, W_SHELL / 0.95 + BOSS_H + 1.0))
    bosses.append(ccyl(p, nrm, 4.5, W_SHELL * 0.6, W_SHELL / 0.95 + BOSS_H))
block_R = block + union(pegs)
log('mount block with pegs: %d body' % len(block_R.decompose()))
block_L = (block.mirror([1, 0, 0]) - band_env) + union(pegs).mirror([1, 0, 0])    # trimmed against its own side's band
to_t(block_R).export(PR + 'wing_mount_R_navy.stl'); to_t(block_L).export(PR + 'wing_mount_L_navy.stl')

# holes and bosses in the shell halves, both sides (the bosses stay inside the shell: clip to the solid)
for name, sgn in (('shell_front_navy', -1), ('shell_back_navy', 1)):
    sh = to_m(trimesh.load(PR + name + '.stl'))
    adds, cuts = [], []
    for p, b, h in zip(spots, bosses, holes):
        if np.sign(p[1]) != sgn: continue
        for mir in (False, True):
            bb_, hh = (b.mirror([1, 0, 0]), h.mirror([1, 0, 0])) if mir else (b, h)
            adds.append(bb_ ^ SOLID); cuts.append(hh)
    if adds:
        sh = (sh + union(adds)) - union(cuts)
        to_t(sh).export(PR + name + '.stl')
        log(f'  {name}: +{len(adds)} mount peg seats, {len(sh.decompose())} body')
open(PR + 'mount_report.txt', 'w').write('\n'.join(report) + '\n')
