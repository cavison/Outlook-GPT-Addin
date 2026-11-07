#!/usr/bin/env python
# Adds the connectors to the v23 base pieces and writes the print STLs:
#   pegs (with crush ribs) on one part + matching holes (and bosses inside the shell) on the other,
#   snap bumps on tongues + windows in the shell, seam dowel holes + dowel pins,
#   and splits the band layers into bed-sized pieces with their seams hidden behind the wings.
import json, os, re, sys
import numpy as np, trimesh, manifold3d as m3

SRC, OUT = 'helmet/out_v23/', 'helmet/out_v23/print/'
os.makedirs(OUT, exist_ok=True)
K, RI, W = 1.23505, 105.042, 2.4
CLR = 0.2                       # hole oversize for a peg
BOSS_H = 2.0                    # bosses inside the shell give the pegs more grip
LAYER = {'white': (0.0, 1.2), 'gold': (1.2, 2.2), 'navy': (2.2, 3.2)}    # band layers above the shell
SEAMS = {'navy': (73, 105), 'gold': (75, 103), 'white': (77, 107)}       # front / side / back splits (deg)
GUARD_BUMPS = (74, 103, 113); NECK_BUMPS = (150, 180, 210); BUMP_Z = 6
GUARD_TONGUE = 12; TONGUE_ZONES = ((68, 116), (124, 236))
rng = np.random.default_rng(1)

tab = open('helmet/t_tables.echo').read()
BAND = np.array(json.loads(re.search(r'BAND = (\[.*?\]\])', tab).group(1)))       # th, bb, top
DOTS = json.loads(re.search(r'DOTS = (\[.*?\]\])', tab).group(1))                  # th, z, r
def bb(th): th = abs(((th + 180) % 360) - 180); return np.interp(th, BAND[:, 0], BAND[:, 1])
def btop(th): th = abs(((th + 180) % 360) - 180); return np.interp(th, BAND[:, 0], BAND[:, 2])

# ---------- mesh helpers ----------
def to_m(t):
    return m3.Manifold(m3.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))
def to_t(m):
    g = m.to_mesh(); return trimesh.Trimesh(np.asarray(g.vert_properties)[:, :3], np.asarray(g.tri_verts), process=False)
def load(n, d=SRC): return to_m(trimesh.load(d + n + '.stl'))
def frame(p, n):
    n = np.array(n, float); n = n / np.linalg.norm(n); z = np.array([0, 0, 1.])
    v = np.cross(z, n); c = float(np.dot(z, n))
    if np.linalg.norm(v) < 1e-9: R = np.eye(3) if c > 0 else np.diag([1., -1., -1.])
    else:
        vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]]); R = np.eye(3) + vx + vx @ vx / (1 + c)
    return np.hstack([R, np.asarray(p, float).reshape(3, 1)]).astype(np.float32)
def cyl(r0, r1, z0, z1, seg=32): return m3.Manifold.cylinder(z1 - z0, r0, r1, seg).translate([0, 0, z0])
def place(m, p, n): return m.transform(frame(p, n))
def union(ms):
    ms = [m for m in ms if m is not None]
    return m3.Manifold.batch_boolean(ms, m3.OpType.Add) if ms else None
def peg(p, n, d, z0, z1):
    """press-fit peg along n from p+n*z0 to p+n*z1: chamfered tip, three small crush ribs"""
    r = d / 2
    b = cyl(r, r, z0, z1 - 0.5) + cyl(r, r - 0.3, z1 - 0.52, z1)      # parts overlap a little so they fuse
    for a in (0, 2.0944, 4.1888): b = b + cyl(0.3, 0.3, z0, z1 - 0.8, 8).translate([r * np.cos(a), r * np.sin(a), 0])
    return place(b, p, n)
def hole(p, n, d, z0, z1): return place(cyl((d + CLR) / 2, (d + CLR) / 2, z0, z1), p, n)
def boss(p, n, d, z0, z1): return place(cyl(d / 2, d / 2, z0, z1), p, n)

# ---------- surface lookups on the plain shell ----------
SHELL = trimesh.load('helmet/out_v22/shell_nose.stl')
def radial(th):
    t = np.radians(th); d = np.array([np.sin(t), -K * np.cos(t), 0.]); return d / np.linalg.norm(d)
def surf_dir(o, d):
    """first outer-surface hit of a ray (tries a few tiny shifts: a ray exactly on a mesh edge can slip through)"""
    o = np.asarray(o, float); d = np.asarray(d, float); d = d / np.linalg.norm(d)
    best = None
    for e in ((0.013, 0.017, 0.011), (-0.021, 0.009, 0.019), (0.007, -0.023, -0.016)):
        loc, _, tri = SHELL.ray.intersects_location([o + np.array(e)], [d], multiple_hits=True)
        order = np.argsort(np.dot(loc - o, d)) if len(loc) else []
        for k in order:
            nrm = SHELL.face_normals[tri[k]]
            if np.dot(nrm, d) >= 0: break                      # nearest hit is an inner face: this ray slipped through
            dist = np.dot(loc[k] - o, d)
            if best is None or dist < best[0]: best = (dist, loc[k].copy(), nrm.copy())
            break
    if best is None: return None, None
    return best[1], best[2]
def surf(th, z):
    """outer surface point and outward normal at angle th (deg from the front toward +x), height z"""
    d = radial(th); return surf_dir(np.array([0, 0, z]) + d * 400, -d)
def th_of(p): return np.degrees(np.arctan2(p[0], -p[1] / K))

def has_material(mesh_t, p, n, r, lo, hi, k=6):
    """True if the part covers a disc of radius r round p (on the surface), between offsets lo..hi along n"""
    n = n / np.linalg.norm(n); a = np.cross(n, [0, 0, 1.]); a /= np.linalg.norm(a); b = np.cross(n, a)
    pts = [p] + [p + r * (np.cos(t) * a + np.sin(t) * b) for t in np.linspace(0, 2 * np.pi, k, endpoint=False)]
    for q in pts:
        o = q + n * (hi + 5)
        loc, _, _ = mesh_t.ray.intersects_location([o], [-n], multiple_hits=True)
        if len(loc) == 0: return False
        dist = np.dot(loc - q, n)
        if not np.any((dist > lo - 0.3) & (dist < hi + 0.3)): return False
    return True

def pick(cands, k, min_d, taken):
    """farthest-point pick of k candidates, each at least min_d from the others and from taken points"""
    out = []
    pool = [c for c in cands if all(np.linalg.norm(c[0] - t) >= min_d for t in taken)]
    while pool and len(out) < k:
        if not out: c = pool[len(pool) // 2]
        else:
            dmin = [min(np.linalg.norm(c[0] - o[0]) for o in out) for c in pool]
            c = pool[int(np.argmax(dmin))]
        out.append(c)
        pool = [q for q in pool if np.linalg.norm(q[0] - c[0]) >= min_d]
    return out

report = []
def log(*a):
    s = ' '.join(str(x) for x in a); print(s); report.append(s)

# ---------- shell bosses / holes bookkeeping ----------
shell_add = {'upper_front': [], 'upper_back': [], 'neck': [], 'guard': []}
shell_cut = {'upper_front': [], 'upper_back': [], 'neck': [], 'guard': []}
taken = []          # every peg / bump / dowel position so far (no two too close)
def shell_part(th, z):
    """which shell piece is under the point"""
    a = ((th + 180) % 360) - 180
    if z < bb(a) - 0.5 and 12 <= abs(a) <= 120: return 'guard'
    if z < bb(a) - 0.5 and abs(a) > 120: return 'neck'
    return 'upper_front' if abs(a) < 90 else 'upper_back'
def into_shell(p, n, d, depth_above, boss_d, part=None):
    """peg seat through the shell (and anything above it) with a boss on the inside"""
    part = part or shell_part(th_of(p), p[2])
    shell_add[part].append(boss(p, n, boss_d, -W - BOSS_H, -W + 0.3))
    shell_cut[part].append(hole(p, n, d, -W - BOSS_H - 0.5, depth_above + 0.5))
    return part

def in_tongue_zone(th, z, margin):
    a = abs(((th + 180) % 360) - 180)
    for t0, t1 in TONGUE_ZONES:
        if t0 - 3 <= a <= t1 + 3 and z < bb(a) + GUARD_TONGUE + margin: return True
    return False

# ======================= snap bumps and windows =======================
def bump_and_window(th, part_shell):
    z = bb(th) + BUMP_Z
    p, n = surf(th, z); pin = p - n * W                 # inner surface of the upper shell
    c = pin - n * 0.8                                   # sphere centre: top reaches 0.8 into the window
    s = m3.Manifold.sphere(1.6, 32).translate(c.tolist())
    keep = place(cyl(3, 3, -1.2, 2), pin, n)            # the cap outside the tongue face, rooted 1 mm into the tongue
    shell_cut[part_shell].append(hole(pin, n, 3.4, -0.5, W + 0.5))
    taken.append(p)
    return s ^ keep, p
guard_bumps = []
for th in GUARD_BUMPS:
    b, p = bump_and_window(th, 'upper_front' if th < 90 else 'upper_back'); guard_bumps.append(b)
    b2, p2 = bump_and_window(-th, 'upper_front' if th < 90 else 'upper_back')   # left side windows (left guard is the mirror)
neck_bumps = []
for th in NECK_BUMPS:
    b, p = bump_and_window(th, 'upper_back'); neck_bumps.append(b)
log('snap bumps: guard', GUARD_BUMPS, 'neck', NECK_BUMPS)

# ======================= seam dowels =======================
DOWEL_D, DOWEL_DEPTH = 5.0, 8.5
dowels = []
for side in (1, -1):
    for zt in (12, 75, 118):
        best = None
        for psi in np.linspace(-10, 89, 400):
            d = np.array([side * np.cos(np.radians(psi)), 0, np.sin(np.radians(psi))])
            p, n = surf_dir(d * 400, -d)
            if p is not None and np.dot(p, d) > 0 and (best is None or abs(p[2] - zt) < abs(best[0][2] - zt)): best = (p, n)
        dowels.append(best)
p, n = surf_dir(np.array([0, 0, 400.]), np.array([0, 0, -1.])); dowels.append((p, n))
for p, n in dowels:
    p = p.copy(); p[1] = 0.0; n = n.copy(); n[1] = 0.0; n /= np.linalg.norm(n)
    c = p - n * (W + 6) / 2
    shell_cut['upper_front'].append(hole(c, [0, -1, 0], DOWEL_D, -0.5, DOWEL_DEPTH))
    shell_cut['upper_back'].append(hole(c, [0, 1, 0], DOWEL_D, -0.5, DOWEL_DEPTH))
    taken.append(p)
log('seam dowels at z =', [round(float(p[2]), 1) for p, n in dowels])
pin_len = 2 * DOWEL_DEPTH - 0.4
dowel_pin = cyl(2.5, 2.5, 0.58, pin_len - 0.58) + cyl(2.0, 2.5, 0, 0.6) + cyl(2.5, 2.0, pin_len - 0.6, pin_len)
for a in (0, 2.0944, 4.1888): dowel_pin = dowel_pin + cyl(0.3, 0.3, 0.8, pin_len - 0.8, 8).translate([2.5 * np.cos(a), 2.5 * np.sin(a), 0])

# ======================= front H =======================
h_navy = load('h_navy'); h_navy_t = trimesh.load(SRC + 'h_navy.stl')
h_pegs = []
for x, z in ((20, 38), (-20, 38), (0, 64)):
    p, n = surf_dir(np.array([x, -400, z]), np.array([0, 1., 0]))
    if not has_material(h_navy_t, p, np.array([0, -1., 0]), 3.5, -1, 20):
        log('WARNING H peg not on the backing at', x, z)
    h_pegs.append(peg(p, [0, 1, 0], 5, -1.0, W + BOSS_H - 0.4))
    part = shell_part(th_of(p), p[2])
    shell_add[part].append(place(cyl(4.5, 4.5, W - 0.3, W + BOSS_H), p, [0, 1, 0]) ^ place(cyl(9, 9, -20, 20), p, [0, 1, 0]))
    shell_cut[part].append(hole(p, [0, 1, 0], 5, -0.5, W + BOSS_H + 1.5))
    taken.append(p)
log('front H: 3 pegs (5 mm)')

# ======================= crest =======================
CR_CUT = {'white': -45, 'gold': 45}
CR_END_F, CR_END_B = 87.1, -44.6
def crest_points(x, n_pts, y0, y1):
    pts = []
    for phi in np.linspace(-85, 160, 500):
        d = np.array([0, np.sin(np.radians(phi)), np.cos(np.radians(phi))])
        p, nn = surf_dir(np.array([x, 0, 0]) + d * 400, -d)
        if p is None or np.dot(p - np.array([x, 0, 0]), d) <= 0: continue   # came in through the open bottom
        if p[1] < 0 and p[2] < CR_END_F + 6: continue
        if p[1] > 0 and p[2] < CR_END_B + 8: continue
        if abs(p[1]) < 16 or not (y0 + 9 < p[1] < y1 - 9): continue
        pts.append((p, nn))
    if len(pts) < n_pts: return pts
    idx = np.linspace(0, len(pts) - 1, n_pts + 2)[1:-1].round().astype(int)
    return [pts[i] for i in idx]
crest_pegs = {}
for color, n_f, n_b in (('white', 3, 4), ('gold', 4, 3)):
    cut = CR_CUT[color]
    for piece, y0, y1, k in (('front', -300, cut, n_f), ('back', cut, 300, n_b)):
        if color == 'white':
            pts = []
            cand = crest_points(14, k, y0, y1) + crest_points(-14, k, y0, y1)
            cand.sort(key=lambda c: c[0][1]); pts = [cand[i] for i in np.linspace(0, len(cand) - 1, k + 2)[1:-1].round().astype(int)]
        else:
            pts = crest_points(0, k, y0, y1)
        ndir = -np.mean([nn for _, nn in pts], axis=0); ndir /= np.linalg.norm(ndir)   # one push-on direction per piece
        above = 0.0 if color == 'white' else 2.5
        pg = []
        for p, nn in pts:
            pg.append(peg(p, ndir, 4, -above - 1.0 if color == 'gold' else -1.0, W + BOSS_H - 0.4))
            part = shell_part(th_of(p), p[2])
            shell_add[part].append(place(cyl(3.5, 3.5, W - 0.3, W + BOSS_H), p, ndir))
            shell_cut[part].append(hole(p, ndir, 4, -above - 0.5, W + BOSS_H + 1.0))
            taken.append(p)
        crest_pegs[(color, piece)] = (pg, [(p, ndir) for p, _ in pts])
        log(f'crest {color} {piece}: {len(pts)} pegs')

# ======================= band layers =======================
def sector(th0, th1):
    a = np.radians(np.arange(th0, th1 + 0.5, 1.0))
    poly = [[0, 0]] + [[400 * np.sin(t), -K * 400 * np.cos(t)] for t in a]
    return m3.CrossSection([poly]).extrude(600).translate([0, 0, -300])
def piece_ranges(color):
    s1, s2 = SEAMS[color]
    return {'F': (-s1, s1), 'R': (s1, s2), 'L': (-s2, -s1), 'B': (s2, 360 - s2)}
layers = {c: load('bandL_' + c) for c in ('white', 'gold', 'navy')}
layers_t = {c: trimesh.load(SRC + 'bandL_' + c + '.stl') for c in ('white', 'gold', 'navy')}
band_parts = {}
dot_pegs = []
for th, z, r in DOTS:
    for s in (1, -1):
        p, n = surf(s * th, z)
        dot_pegs.append(place(cyl(r - 0.12, r - 0.12, LAYER['white'][1] - 0.4, LAYER['navy'][1] - 0.02), p, n))
        taken.append(p)
log('white dot pegs:', len(dot_pegs))
WANT = {'white': {'F': 6, 'R': 2, 'L': 2, 'B': 4}, 'gold': {'F': 4, 'R': 2, 'L': 2, 'B': 4}, 'navy': {'F': 6, 'R': 2, 'L': 2, 'B': 4}}
band_pegs = {}
for color in ('white', 'gold', 'navy'):
    lo, hi = LAYER[color]
    for key, (t0, t1) in piece_ranges(color).items():
        want = WANT[color][key]
        # right-hand half of the piece (mirrored onto the left for F and B; R / L are mirror images)
        if key == 'F': ra = (0, t1)
        elif key == 'B': ra = (t0, 180)
        elif key == 'R': ra = (t0, t1)
        else: ra = None
        if ra is None: band_pegs[(color, key)] = [(p * np.array([-1, 1, 1]), n * np.array([-1, 1, 1])) for p, n in band_pegs[(color, 'R')]]; continue
        cands = []
        for th in np.arange(ra[0] + 4, ra[1] - 4 + 0.01, 2.0):
            if key in ('F', 'B') and (th < 6 or th > 174): continue
            if abs(th - 180) < 24: continue                       # the V inserts
            for f in (0.5, 0.65, 0.35, 0.78, 0.22):
                z = bb(th) + f * (btop(th) - bb(th))
                if z < bb(th) + 3 or z > btop(th) - 3: continue
                if in_tongue_zone(th, z, 4.0): continue
                p, n = surf(th, z)
                if p is None or abs(p[1]) < 6: continue           # not across the front / back seam
                if abs(p[0]) < 18 and p[2] < 21 and p[1] < 0: continue   # nose tongue
                if not has_material(layers_t[color], p, n, 2.2, lo, hi): continue
                cands.append((p, n))
        n_half = want // 2 if key in ('F', 'B') else want
        got = pick(cands, n_half, 8.5 if key in ('F', 'B') else 7.0, taken + [q * np.array([-1, 1, 1]) for q in taken])
        if len(got) < n_half: log(f'WARNING band {color} {key}: only {len(got)} of {n_half} peg spots')
        for p, n in got: taken.append(p); taken.append(p * np.array([-1, 1, 1]))
        if key in ('F', 'B'): got = got + [(p * np.array([-1, 1, 1]), n * np.array([-1, 1, 1])) for p, n in got]
        band_pegs[(color, key)] = got
for (color, key), got in band_pegs.items():
    lo, hi = LAYER[color]
    for p, n in got: into_shell(p, n, 3, lo, 7)
    log(f'band {color} {key}: {len(got)} pegs')

# V inserts on the back: pegs through the white layer into the shell
vparts = {'gold': load('bandV_gold'), 'navy': load('bandV_navy')}
vparts_t = {c: trimesh.load(SRC + 'bandV_' + c + '.stl') for c in vparts}
v_pegs = {}
for color, k in (('gold', 2), ('navy', 1)):        # per side, mirrored
    cands = []
    for x in np.arange(6, 40, 1.0):
        for z in np.arange(-90, -30, 1.0):
            p, n = surf_dir(np.array([x, 400, z]), np.array([0, -1., 0]))
            if p is None or in_tongue_zone(th_of(p), z, 4.5): continue
            if has_material(vparts_t[color], p, n, 2.0, 1.2, 3.2): cands.append((p, n))
    got = pick(cands, k, 14, taken + [q * np.array([-1, 1, 1]) for q in taken])
    got = got + [(p * np.array([-1, 1, 1]), n * np.array([-1, 1, 1])) for p, n in got]
    for p, n in got: taken.append(p); into_shell(p, n, 3, 1.2, 7)
    v_pegs[color] = got
    log(f'V {color}: {len(got)} pegs')

# ======================= cheek guard: gold frame, cheek H, rivet pin =======================
gframe_t = trimesh.load(SRC + 'guard_gold.stl')
cands = []
for th in np.arange(14, 120, 1.5):
    for z in np.arange(-136, -2, 1.5):
        if z > bb(th) - 2: continue
        p, n = surf(th, z)
        if p is None: continue
        if has_material(gframe_t, p, n, 1.9, 0, 4.3, k=8): cands.append((p, n))
frame_spots = pick(cands, 7, 25, [])
log('guard frame pegs:', len(frame_spots))
frame_pegs = [peg(p, -n, 3, -2.0, W + 1.5 - 0.3) for p, n in frame_spots]
guard_add = [boss(p, n, 6, -W - 1.5, -W + 0.3) for p, n in frame_spots]
guard_cut = [hole(p, -n, 3, -0.5, W + 2.0) for p, n in frame_spots]
cheek_h_t = trimesh.load(SRC + 'cheek_h.stl')
c0 = cheek_h_t.bounding_box.centroid
cands = []
for th in np.arange(55, 90, 0.5):
    for z in np.arange(-95, -50, 0.5):
        p, n = surf(th, z)
        if p is not None and has_material(cheek_h_t, p, n, 1.6, -1.0, 2.0, k=8): cands.append((p, n))
ch_spots = pick(cands, 2, 12, [])
log('cheek H pegs:', len(ch_spots))
ch_pegs = [peg(p, -n, 2.6, 0.5, 1.0 + 1.4 + 1.5 - 0.3) for p, n in ch_spots]
guard_add += [boss(p, n, 6, -W - 1.5, -W + 0.3) for p, n in ch_spots]
guard_cut += [hole(p, -n, 2.6, 0.5, 1.0 + 1.4 + 2.0) for p, n in ch_spots]
riv_t = trimesh.load(SRC + 'cheek_rivet.stl')
rc = riv_t.vertices.mean(axis=0)
p, n = surf(th_of(rc), rc[2])
rivet_shank = peg(p, -n, 3, -0.5, W + 1.5 - 0.3)
guard_add.append(boss(p, n, 6, -W - 1.5, -W + 0.3)); guard_cut.append(hole(p, -n, 3, -0.5, W + 2.0))

# ======================= assemble the print pieces =======================
def save(m, name, mirror=False, min_body=0, split_lr=False):
    """write a print piece; report its real bodies (from the solid itself), drop tiny islands if asked,
    and optionally write a piece that falls apart into left / right halves as two files"""
    if mirror: m = m.mirror([1, 0, 0])
    comps = sorted(m.decompose(), key=lambda q: -q.volume())
    if min_body:
        keep = [q for q in comps if q.volume() > min_body]
        if len(keep) < len(comps): log(f'  ({name}: dropped {len(comps) - len(keep)} tiny fragment(s))')
        comps = keep
    if split_lr and len(comps) == 2:
        for q in comps:
            bx = np.array(q.bounding_box()).reshape(2, 3); side = 'R' if bx[:, 0].mean() > 0 else 'L'
            save(q, name + side)
        return
    if len(comps) > 1:
        for q in comps[1:]:
            bx = np.array(q.bounding_box()).reshape(2, 3)
            log(f'  !! {name}: extra body {q.volume():.1f} mm3 at {bx.mean(axis=0).round(1).tolist()} size {(bx[1] - bx[0]).round(1).tolist()}')
    m = union(comps)
    t = to_t(m); t.export(OUT + name + '.stl')
    ext = (t.bounds[1] - t.bounds[0]).round(1)
    log(f'  {name}: {len(comps)} bod{"y" if len(comps) == 1 else "ies"}, {ext.tolist()} mm, {m.volume() / 1000 * 1.24:.0f} g')
    return t

log('--- print pieces ---')
uf = load('upper_front') + union(shell_add['upper_front'])
uf = uf - union(shell_cut['upper_front']); save(uf, 'shell_front_navy')
ub = load('upper_back') + union(shell_add['upper_back'])
ub = ub - union(shell_cut['upper_back']); save(ub, 'shell_back_navy')
g = load('guard_navy') + union(guard_bumps + guard_add + shell_add['guard'])
g = g - union(guard_cut + shell_cut['guard']); save(g, 'cheek_guard_R_navy'); save(g, 'cheek_guard_L_navy', mirror=True)
gf = load('guard_gold') + union(frame_pegs)      # saved at the end, trimmed against the band layers
ch = load('cheek_h') + union(ch_pegs); save(ch, 'cheek_H_R_white'); save(ch, 'cheek_H_L_white', mirror=True)
# the rivet dome as modelled passes right through the wall: keep only the head outside the guard
rv_head = [c for c in (load('cheek_rivet') - to_m(SHELL)).decompose() if np.dot(np.array(c.bounding_box()).reshape(2, 3).mean(0) - p, n) > 0]
rv = union(rv_head) + rivet_shank
save(rv, 'cheek_rivet_R_white'); save(rv, 'cheek_rivet_L_white', mirror=True)
nk = load('neck') + union(neck_bumps + shell_add['neck'])
if shell_cut['neck']: nk = nk - union(shell_cut['neck'])
save(nk, 'neck_plate_navy')
# band layers: pegs on each piece, holes for the pegs of the layers above
band_built = {}
for color in ('white', 'gold', 'navy'):
    lo, hi = LAYER[color]
    above = [c for c in ('gold', 'navy') if LAYER[c][0] > lo]
    for key, (t0, t1) in piece_ranges(color).items():
        m = layers[color] ^ sector(t0, t1)
        pg = [peg(p, -n, 3, -(lo + 0.6), W + BOSS_H - 0.4) for p, n in band_pegs[(color, key)]]
        if color == 'white':
            pg += [d for d, (th, z, r) in zip(dot_pegs, [(s * d[0], d[1], d[2]) for d in DOTS for s in (1, -1)])
                   if (t0 <= th <= t1) or (t0 <= th + 360 <= t1)]
        m = m + union(pg) if pg else m
        cuts = [hole(p, -n, 3, -(LAYER[c][0] + 0.3), W + 1) for c in above for kk in ('F', 'R', 'L', 'B') for p, n in band_pegs[(c, kk)]]
        if color == 'white': cuts += [hole(p, -n, 3, -1.5, W + 1) for c in ('gold', 'navy') for p, n in v_pegs[c]]
        if cuts: m = m - union(cuts)
        band_built[(color, key)] = m
        save(m, f'band_{color}_{key}', min_body=60, split_lr=(key == 'B'))
v_bits = []      # the crest rib cuts a small strip off the top of the gold V: it joins the crest's gold back piece
for color in ('gold', 'navy'):
    m = vparts[color] + union([peg(p, -n, 3, -1.8, W + BOSS_H - 0.4) for p, n in v_pegs[color]])
    if color == 'gold':
        bodies = sorted(m.decompose(), key=lambda q: -q.volume())
        m = bodies[0]; v_bits = bodies[1:]
    save(m, f'band_V_{color}')
for color in ('white', 'gold'):
    for piece in ('front', 'back'):
        pg, spots = crest_pegs[(color, piece)]
        m = load(f'crest_{color}_{piece}') + union(pg)
        if color == 'gold' and piece == 'back' and v_bits: m = m + union(v_bits)
        if color == 'white':   # holes for the gold pegs that pass through
            m = m - union([hole(p, nd, 4, -3.5, 1.0) for pc in ('front', 'back') for p, nd in crest_pegs[('gold', pc)][1]])
        save(m, f'crest_{color}_{piece}')
hg, hw = load('h_gold'), load('h_white')
hw = hw - hg                                              # colours must not overlap: gold letter, white outline, navy backing
hn = (h_navy + union(h_pegs)) - (hw + hg)
save(hn, 'H_badge_navy'); save(hw, 'H_badge_white'); save(hg, 'H_badge_gold')
for n_ in ('nose_body', 'nose_panel', 'nose_pin'): save(load(n_), {'nose_body': 'nose_body_gold', 'nose_panel': 'nose_panel_navy', 'nose_pin': 'nose_pin_white'}[n_])
save(dowel_pin, 'seam_dowel_pin_navy')
# gold cheek frames meet the band's bottom edge: trim them so the two never overlap (left and right each against their own side)
bands = union([m for (c, k), m in band_built.items()])
save(gf - bands, 'cheek_frame_R_gold', min_body=1)
save(gf.mirror([1, 0, 0]) - bands, 'cheek_frame_L_gold', min_body=1)
open(OUT + 'build_report.txt', 'w').write('\n'.join(report) + '\n')
