#!/usr/bin/env python
# Lay every print piece out on 220 x 220 plates for the Flashforge AD5X and write an Orca Slicer project (.3mf).
#   * filament slots: 1 navy, 2 white, 3 gold (slot 4 spare)
#   * single-colour pieces only share plates with their own colour -> those plates need no filament changes
#   * multi-colour pieces (wing halves, front H) share plates with pieces of similar height / infill;
#     a corner is kept clear on those plates for the prime tower
#   * each piece carries its own settings (infill, walls, supports) as Orca per-object settings
import glob, io, json, math, os, uuid, zipfile
import numpy as np, trimesh
from PIL import Image, ImageDraw
from scipy.signal import fftconvolve
from scipy import ndimage

PR, PW = 'helmet/out_v23/print/', 'helmet/out_v23/print_wing/'
OUT3MF = 'pkg/winged_helmet_AD5X.3mf'
SLOT = {'navy': 1, 'white': 2, 'gold': 3}
RGB = {'navy': (30, 42, 82), 'white': (236, 236, 228), 'gold': (242, 193, 46)}
BED, MARGIN, GAP, RES = 220.0, 2.0, 5.0, 1.0          # mm: edge margin, gap between pieces, packing grid
TOWER_X0, TOWER_X1, TOWER_D = 10.0, 66.0, 28.0        # kept clear on multi-colour plates: Orca's default prime tower spot
                                                      # (x 15-60, at the back; it only primes ~45 mm3 per swap here, so it stays shallow)
BACK_MARGIN = 3.5                                     # clear of the purge line at the back edge
BRIM_W = 4.0                                          # outer brim on tall, narrow-footed pieces
ANGLES, TRIES = list(range(0, 360, 10)), 6
K = 1.23505

# ---------- per-piece settings (Orca per-object settings) ----------
SUP = {'enable_support': '1', 'support_type': 'tree(auto)', 'support_on_build_plate_only': '1'}
# per-part settings: the gold and white of the v2 wings are solid all the way down (2.4 / 1.6 mm), so no navy shows through
PART_SET = {'wing2': {'gold': dict(sparse_infill_density='100%', sparse_infill_pattern='rectilinear'),
                      'white': dict(sparse_infill_density='100%', sparse_infill_pattern='rectilinear')}}
PART_SET['wing2s'] = PART_SET['wing2']
SET = {
    'shell':  dict(wall_loops='3', sparse_infill_density='12%', brim_type='no_brim', **SUP),   # 215 mm wide: no room for a brim
    'thin':   dict(wall_loops='2', sparse_infill_density='15%', **SUP),          # band layers, frames, guards, neck
    'strong': dict(wall_loops='4', sparse_infill_density='40%', **SUP),          # mount blocks, nose clip
    'pin':    dict(wall_loops='6', sparse_infill_density='100%', sparse_infill_pattern='rectilinear'),   # pins and dowels: solid
    'crest':  dict(wall_loops='3', sparse_infill_density='12%', sparse_infill_pattern='gyroid', **SUP),
    'core':   dict(wall_loops='2', sparse_infill_density='8%', sparse_infill_pattern='gyroid', top_shell_layers='3', bottom_shell_layers='3'),
    'half':   dict(wall_loops='2', sparse_infill_density='10%', sparse_infill_pattern='gyroid'),
    'half_s': dict(wall_loops='2', sparse_infill_density='10%', sparse_infill_pattern='gyroid', **SUP),   # with the scallop lip
    'small':  dict(wall_loops='3', sparse_infill_density='20%', **SUP),
    'badge':  dict(wall_loops='3', sparse_infill_density='10%', sparse_infill_pattern='gyroid', **SUP),
    'wing2':  dict(wall_loops='2', sparse_infill_density='12%', sparse_infill_pattern='gyroid', top_shell_layers='4', bottom_shell_layers='4'),
    # tip B: its hidden tongue (into F9) sits mid-thickness, 2 mm off the bed, so it gets supports under it
    'wing2s': dict(wall_loops='2', sparse_infill_density='12%', sparse_infill_pattern='gyroid', top_shell_layers='4', bottom_shell_layers='4', **SUP),
}

# ---------- orientation helpers ----------
def rot(axis, deg):
    a = math.radians(deg); c, s = math.cos(a), math.sin(a)
    if axis == 'x': R = [[1, 0, 0], [0, c, -s], [0, s, c]]
    elif axis == 'y': R = [[c, 0, s], [0, 1, 0], [-s, 0, c]]
    else: R = [[c, -s, 0], [s, c, 0], [0, 0, 1]]
    M = np.eye(4); M[:3, :3] = R; return M
def align(d, to=(0, 0, 1)):
    """rotation taking direction d onto 'to'"""
    d = np.asarray(d, float) / np.linalg.norm(d); t = np.asarray(to, float)
    v = np.cross(d, t); c = float(np.dot(d, t))
    if np.linalg.norm(v) < 1e-9: R = np.eye(3) if c > 0 else np.diag([1., -1., -1.])
    else:
        vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]]); R = np.eye(3) + vx + vx @ vx / (1 + c)
    M = np.eye(4); M[:3, :3] = R; return M
def outward(p):                       # outward normal of the (stretched) helmet side at p, horizontal
    n = np.array([p[0], p[1] / K ** 2, 0.0]); return n / np.linalg.norm(n)

# mount push-on direction (from the wing build's placement)
WPX, PY_, YAW, LEAN, ZB, MID_T = 103.942, -60.0, 15.0, 4.0, -135.0, 4.0
def _Rz(a): return rot('z', a)
def _Ry(a): return rot('y', a)
def _Tr(x, y, z): M = np.eye(4); M[:3, 3] = [x, y, z]; return M
SIDE = np.array([[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1]], float)
PLACE = _Tr(WPX, PY_, 0) @ _Rz(-YAW) @ _Tr(0, -PY_, 0) @ _Tr(0, 0, ZB) @ _Ry(LEAN) @ _Tr(0, 0, -ZB) @ SIDE
BACK = PLACE @ _Tr(0, 0, -MID_T / 2) @ np.diag([1, 1, -1, 1])
NRM = BACK[:3, 2] / np.linalg.norm(BACK[:3, 2])

# ---------- the piece list ----------
# (name, [(file, colour)], quantity, orientation, settings, group)
P = []
def add(name, parts, qty, orient, settings, group): P.append(dict(name=name, parts=parts, qty=qty, orient=orient, settings=settings, group=group))
def one(f, colour): return [(f, colour)]
add('Shell front', one(PR + 'shell_front_navy.stl', 'navy'), 1, 'upright', 'shell', 'navy')
add('Shell back', one(PR + 'shell_back_navy.stl', 'navy'), 1, 'tilt8', 'shell', 'navy')
for s in 'RL':
    add(f'Cheek guard {s}', one(PR + f'cheek_guard_{s}_navy.stl', 'navy'), 1, 'upright', 'thin', 'navy')
    add(f'Wing mount {s}', one(PR + f'wing_mount_{s}_navy.stl', 'navy'), 1, 'mount' + s, 'strong', 'navy')
    add(f'Cheek frame {s}', one(PR + f'cheek_frame_{s}_gold.stl', 'gold'), 1, 'upright', 'thin', 'gold')
    add(f'Cheek H {s}', one(PR + f'cheek_H_{s}_white.stl', 'white'), 1, 'axis', 'small', 'white')
    add(f'Cheek rivet {s}', one(PR + f'cheek_rivet_{s}_white.stl', 'white'), 1, 'axis', 'small', 'white')
add('Neck plate', one(PR + 'neck_plate_navy.stl', 'navy'), 1, 'upright', 'thin', 'navy')
for c in ('navy', 'gold', 'white'):
    for f in sorted(glob.glob(PR + f'band_{c}_*.stl')):
        add('Band ' + c + ' ' + os.path.basename(f)[len(f'band_{c}_'):-4], one(f, c), 1, 'upright', 'thin', c)
for c in ('navy', 'gold'):
    add(f'Back V {c}', one(PR + f'band_V_{c}.stl', c), 1, 'upright', 'thin', c)
for c in ('white', 'gold'):
    for piece in ('front', 'back'):
        add(f'Crest {c} {piece}', one(PR + f'crest_{c}_{piece}.stl', c), 1, 'side', 'crest', c)
add('Nose clip', one(PR + 'nose_body_gold.stl', 'gold'), 1, 'upright', 'strong', 'gold')
add('Nose panel', one(PR + 'nose_panel_navy.stl', 'navy'), 1, 'upright', 'small', 'navy')
add('Nose rivet pin', one(PR + 'nose_pin_white.stl', 'white'), 1, 'nose_pin', 'small', 'white')
add('Seam dowel pin', one(PR + 'seam_dowel_pin_navy.stl', 'navy'), 7, 'as_is', 'pin', 'navy')
add('Front H badge', [(PR + 'H_badge_navy.stl', 'navy'), (PR + 'H_badge_white.stl', 'white'), (PR + 'H_badge_gold.stl', 'gold')], 1, 'face_up', 'badge', 'multi')
# wings v2 (hub and feathers): the collars are coloured on both faces with centred sockets, so one print serves both
# wings (turned over for the left); feathers and tips have their tongue flush with the show face (printed face down,
# tongue on the bed), so they are made right and left, like the medallions
PW2 = 'helmet/out_v23/print_wing2/'
def w2(name):
    return [(PW2 + f'wing2_{name}_{c}.stl', c) for c in ('navy', 'gold', 'white') if os.path.exists(PW2 + f'wing2_{name}_{c}.stl')]
for sd, sfx in (('R', ''), ('L', '_L')):
    for k in range(1, 10):
        add(f'Wing feather F{k} {sd}', w2(f'F{k}{sfx}'), 1, 'as_is', 'wing2', 'multi')
    add(f'Wing tip A {sd}', w2(f'TA{sfx}'), 1, 'as_is', 'wing2', 'multi')
    add(f'Wing tip B {sd}', w2(f'TB{sfx}'), 1, 'as_is', 'wing2s', 'multi')
add('Wing upper collar', w2('CU'), 2, 'as_is', 'wing2', 'multi')
add('Wing lower collar', w2('CL'), 2, 'as_is', 'wing2', 'multi')
add('Wing front medallion R', w2('MF'), 1, 'as_is', 'wing2', 'multi')
add('Wing front medallion L', w2('MF_L'), 1, 'as_is', 'wing2', 'multi')
add('Wing back medallion R (key)', w2('MB'), 1, 'as_is', 'wing2', 'multi')
add('Wing back medallion L (key)', w2('MB_L'), 1, 'as_is', 'wing2', 'multi')

# ---------- orient every piece ----------
ORIENT = json.load(open('ref2/orient.json')) if os.path.exists('ref2/orient.json') else {}
def oriented(p):
    meshes = [(trimesh.load(f), c) for f, c in p['parts']]
    allv = np.vstack([m.vertices for m, _ in meshes]); cen = allv.mean(0)
    o = p['orient']
    if p['name'] in ORIENT: M = np.array(ORIENT[p['name']]['R'])          # chosen from slicing trials (orient_pick.py)
    elif o in ('upright', 'as_is', 'flat'): M = np.eye(4)
    elif o == 'tilt8': M = rot('x', 8)
    elif o == 'side': M = rot('y', 90)
    elif o == 'axis': M = align(outward(cen))                  # head / face up, pegs down
    elif o == 'nose_pin': M = align([0, -1, 0])
    elif o == 'mountR': M = align(NRM)                          # face toward the wing on the bed
    elif o == 'mountL': M = align(NRM * np.array([-1, 1, 1]))
    elif o == 'face_up':                                        # the H's flat face up
        g = trimesh.load(PR + 'H_badge_gold.stl'); v = g.vertices - g.vertices.mean(0)
        n = np.linalg.svd(v, full_matrices=False)[2][2]
        if n[1] > 0: n = -n                                   # the face points forward (-y)
        M = align(n)
    out = []
    for m, c in meshes:
        m = m.copy(); m.apply_transform(M); out.append((m, c))
    allv = np.vstack([m.vertices for m, _ in out]); lo, hi = allv.min(0), allv.max(0)
    shift = np.array([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]])
    for m, _ in out: m.apply_translation(shift)
    return out
def outline(parts):
    """exact top-view outline of the piece (shapely), centred on its bounding-box centre"""
    import shapely
    from shapely.geometry import Polygon
    tris = np.vstack([m.vertices[m.faces][:, :, :2] for m, _ in parts])
    u, v = tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]
    a = 0.5 * np.abs(u[:, 0] * v[:, 1] - u[:, 1] * v[:, 0])
    poly = shapely.union_all(shapely.polygons(tris[a > 1e-6])).buffer(0.01)
    return poly
def raster(poly, a, grow=0.0):
    """1 mm mask of the outline turned by a degrees (counter-clockwise, about the piece centre at 0,0), drawn
    conservatively (every cell the outline touches); also returns where the piece centre falls in the mask (mm)"""
    from shapely import affinity
    q = affinity.rotate(poly, a, origin=(0, 0))
    if grow: q = q.buffer(grow, 8)
    x0, y0, x1, y1 = q.bounds
    w, h = int(math.ceil((x1 - x0) / RES)) + 1, int(math.ceil((y1 - y0) / RES)) + 1
    img = Image.new('L', (w, h), 0); d = ImageDraw.Draw(img)
    for g in (q.geoms if hasattr(q, 'geoms') else [q]):
        d.polygon([((x - x0) / RES, (y - y0) / RES) for x, y in g.exterior.coords], fill=1, outline=1)
    for g in (q.geoms if hasattr(q, 'geoms') else [q]):
        for hole in g.interiors:
            hp = affinity.scale(type(g)(hole.coords), 1, 1).buffer(-1.0)       # keep a 1 mm rim of the piece around holes
            if not hp.is_empty:
                for hg in (hp.geoms if hasattr(hp, 'geoms') else [hp]):
                    d.polygon([((x - x0) / RES, (y - y0) / RES) for x, y in hg.exterior.coords], fill=0)
    return np.array(img, bool), (-x0, -y0)
# ---------- packing ----------
NB = int(BED / RES)
def disk(r): return ndimage.iterate_structure(ndimage.generate_binary_structure(2, 1), int(round(r / RES)))
DISK = disk(GAP)
def border_grid(margin, multi):
    border = np.zeros((NB, NB), bool); mg = int(math.ceil(margin / RES))
    border[:mg, :] = border[-mg:, :] = border[:, :mg] = border[:, -mg:] = True
    border[NB - int(math.ceil(max(margin, BACK_MARGIN) / RES)):, :] = True     # the AD5X start purge line runs along y 219.6-220
    if multi:                                                     # prime tower: AD5X default spot, x 15-60 at the back
        border[NB - int(TOWER_D / RES):, int(TOWER_X0 / RES):int(TOWER_X1 / RES)] = True
    return border
def empty_plate(g):
    multi = g == 'multi'
    return dict(group=g, items=[], raw=np.zeros((NB, NB), bool), used=0,
                border={False: border_grid(MARGIN, multi), True: border_grid(MARGIN + BRIM_W + 0.5, multi)},
                spread=np.zeros((NB, NB), bool))
def fits(pl, mask, brim):
    """every spot where the piece keeps GAP from the other pieces and its margin from the edge"""
    mh, mw = mask.shape
    if mh > NB or mw > NB: return None
    check = pl['spread'] | pl['border'][brim]
    hit = fftconvolve(check.astype(np.float32), mask[::-1, ::-1].astype(np.float32), mode='valid')
    return np.argwhere(hit < 0.5)
def fine_masks(p):
    """2-degree turns, made on first use: tried only before a piece would open a new plate"""
    if 'fine' not in p:
        p['fine'] = {}
        for a in range(0, 360, 2):
            if a in p['masks'] or p['settings'] == 'pin': continue
            m, c = raster(p['outline'], a, BRIM_W if p['brim'] else 0.0); p['fine'][a] = m; p['centre'][a] = c
    return p['fine']
def best_spot(pl, p, rule, fine=False):
    best = None
    for a, m in (fine_masks(p) if fine else p['masks']).items():
        free = fits(pl, m, False)
        if free is None or len(free) == 0: continue
        if rule == 'contact':          # hug what is already there (fewer gaps); ties go front-left
            zone = ndimage.binary_dilation(pl['raw'] | pl['border'][False], structure=disk(GAP + 2))
            edge = m & ~ndimage.binary_erosion(m)
            touch = fftconvolve(zone.astype(np.float32), edge[::-1, ::-1].astype(np.float32), mode='valid')
            sc = touch[free[:, 0], free[:, 1]]
            k = np.lexsort((free[:, 1], free[:, 0], -np.round(sc)))[0]
            key = (-round(float(sc[k])), int(free[k, 0]), int(free[k, 1]))
        else:                          # front-most, then left-most
            k = np.lexsort((free[:, 1], free[:, 0]))[0]
            key = (int(free[k, 0]), int(free[k, 1]))
        if best is None or key < best[0]: best = (key, tuple(free[k]), a, m)
    return best
def pack(todo, g, rule):
    plates = []
    for i, k in todo:
        p = P[i]
        for pl in plates + [None]:
            if pl is None: pl = empty_plate(g); plates.append(pl)
            elif NB * NB * 0.9 - pl['used'] < p['area']: continue
            best = best_spot(pl, p, rule)
            if best is None:
                if not pl['items']: raise SystemExit(f"{p['name']} does not fit an empty plate")
                continue
            _, (r0, c0), a, m = best
            pl['raw'][r0:r0 + m.shape[0], c0:c0 + m.shape[1]] |= m
            pl['spread'] = ndimage.binary_dilation(pl['raw'], structure=DISK)
            pl['used'] += p['area']
            pl['items'].append((i, k, a, c0 * RES + p['centre'][a][0], r0 * RES + p['centre'][a][1]))
            break
    return plates
def place(pl, p, i, k, best):
    _, (r0, c0), a, m = best
    pl['raw'][r0:r0 + m.shape[0], c0:c0 + m.shape[1]] |= m
    pl['spread'] = ndimage.binary_dilation(pl['raw'], structure=DISK)
    pl['used'] += p['area']
    pl['items'].append((i, k, a, c0 * RES + p['centre'][a][0], r0 * RES + p['centre'][a][1]))
def consolidate(plates, rule):
    """try to empty the least-full plate: move its pieces onto the other plates, trying 2-degree turns"""
    while len(plates) > 1:
        last = min(plates, key=lambda q: q['used'])
        others = [q for q in plates if q is not last]
        trial = [dict(q, raw=q['raw'].copy(), spread=q['spread'].copy(), items=list(q['items'])) for q in others]
        ok = True
        for (i, k, a, cx, cy) in sorted(last['items'], key=lambda it: -P[it[0]]['area']):
            p = P[i]
            for q in trial:
                b = best_spot(q, p, rule) or best_spot(q, p, rule, fine=True)
                if b is not None: place(q, p, i, k, b); break
            else: ok = False; break
        if not ok: break
        plates = trial
    return plates
def score(plates):          # fewest plates, then the fullest plates first (empties the last one)
    return (len(plates), -sum((pl['used'] / NB ** 2) ** 2 for pl in plates))
pieces_ready = {}
for i, p in enumerate(P):
    parts = oriented(p); pieces_ready[i] = parts
    os.makedirs('ps/final', exist_ok=True)
    trimesh.util.concatenate([m for m, _ in parts]).export(f"ps/final/{p['name'].replace(' ', '_')}.stl")
    p['bands'] = [(c, b.bounds[0, 2], b.bounds[1, 2]) for m, c in parts for b in (m.split(only_watertight=False) if len(parts) > 1 else [m])]
    p['outline'] = outline(parts)
    base_mask, _ = raster(p['outline'], 0)
    p['area'] = int(base_mask.sum()); p['bbox'] = base_mask.shape[0] * base_mask.shape[1]
    p['hgt'] = max(m.vertices[:, 2].max() for m, _ in parts)
    # contact with the bed and whether the piece needs a brim (tall for its foot, not a shell or pin)
    lowv = np.vstack([m.vertices[m.vertices[:, 2] < 0.8][:, :2] for m, _ in parts])
    contact = len(np.unique(np.floor(lowv / 2.0).astype(int), axis=0)) if len(lowv) else 0      # 2 mm cells touching the bed
    p['contact'] = contact
    tippy = p['name'] in ORIENT and not ORIENT[p['name']]['stable']
    p['brim'] = (p['settings'] not in ('shell', 'pin') and (tippy or (p['hgt'] > 15 and contact < 2 * p['hgt']))
                 and max(base_mask.shape) * RES <= BED - 2 * (MARGIN + BRIM_W + 0.5))
    angs = (0, 90) if p['settings'] == 'pin' else ANGLES
    p['masks'], p['centre'] = {}, {}
    for a in angs:                       # the brim is part of the footprint, so neighbours keep the full gap from it
        p['masks'][a], p['centre'][a] = raster(p['outline'], a, BRIM_W if p['brim'] else 0.0)
    print(f"  {p['name']:32s} x{p['qty']:<3d} {base_mask.shape[1]:4d} x {base_mask.shape[0]:4d} mm  h {p['hgt']:6.1f}  base {contact:5d} cells  {'brim' if p['brim'] else '    '} [{p['group']}]")
rng = np.random.default_rng(7)
plates = []
import hashlib, pickle
KEY = hashlib.md5(json.dumps(['v3-consolidate'] + [(p['name'], int(p['qty']), int(p['area']), bool(p['brim']), [float(a) for a in sorted(p['masks'])]) for p in P] + [MARGIN, BACK_MARGIN, GAP, TOWER_X0, TOWER_X1, TOWER_D, BRIM_W, TRIES]).encode()).hexdigest()
CACHE = 'ref2/pack_cache.pkl'
cached = pickle.load(open(CACHE, 'rb')) if os.path.exists(CACHE) else None
if cached and cached['key'] == KEY:
    plates = cached['plates']; print('  (packing reused from cache)')
for g in (() if plates else ('navy', 'white', 'gold', 'multi')):
    todo = [(i, k) for i, p in enumerate(P) if p['group'] == g for k in range(p['qty'])]
    orders = [sorted(todo, key=lambda ik: -P[ik[0]]['bbox']), sorted(todo, key=lambda ik: -P[ik[0]]['area']),
              sorted(todo, key=lambda ik: -max(P[ik[0]]['masks'][0].shape))]
    for _ in range(TRIES):
        w = {i: rng.uniform(0.75, 1.25) for i in {i for i, _ in todo}}
        orders.append(sorted(todo, key=lambda ik: -P[ik[0]]['bbox'] * w[ik[0]]))
    best = None
    for oi, order in enumerate(orders):
        for rule in ('front', 'contact'):
            res = pack(order, g, rule)
            if best is None or score(res) < score(best[0]): best = (res, oi, rule)
    res = consolidate(best[0], best[2])
    print(f'  {g}: {len(res)} plates (order {best[1]}, {best[2]}{", consolidated from %d" % len(best[0]) if len(res) < len(best[0]) else ""})')
    plates += res
pickle.dump(dict(key=KEY, plates=plates), open(CACHE, 'wb'))
print(f'{len(plates)} plates')
# ---------- filament swaps and print time per plate ----------
SWAP_S = 78.0                     # AD5X profile: 39 s unload + 39 s load
TIMES = json.load(open('ref2/piece_times.json')) if os.path.exists('ref2/piece_times.json') else {}
def plate_swaps(pl):
    bands = [b for (i, k, a, cx, cy) in pl['items'] for b in P[i]['bands']]
    top = max(hi for _, _, hi in bands); zs = [0.0, 0.25]
    while zs[-1] < top - 1e-6: zs.append(zs[-1] + 0.2)
    sets = [{c for c, lo, hi in bands if lo < b - 1e-3 and hi > a + 1e-3} for a, b in zip(zs[:-1], zs[1:])]
    sets = [s for s in sets if s]
    last, n = None, 0
    for j, S in enumerate(sets):
        nxt = sets[j + 1] if j + 1 < len(sets) else set()
        if last is None: n += len(S) - 1
        elif last in S: n += len(S) - 1
        else: n += len(S)
        rest = [c for c in S if c != last] or list(S)
        keep = [c for c in rest if c in nxt]
        last = (keep or rest)[0] if len(S) > 1 or last not in S else last
    return n
for pl in plates:
    pl['swaps'] = plate_swaps(pl) if pl['group'] == 'multi' else 0
    hrs = [TIMES.get(P[i]['name'], {}).get('hours') for (i, k, a, cx, cy) in pl['items']]
    pl['print_h'] = sum(hrs) if all(h is not None for h in hrs) else None
    pl['grams'] = sum(TIMES.get(P[i]['name'], {}).get('total_g', 0) for (i, k, a, cx, cy) in pl['items'])

# ---------- write the Orca project ----------
def fmt(x): return ('%.4f' % x).rstrip('0').rstrip('.') if abs(x) > 1e-9 else '0'
def mesh_xml(m):
    out = io.StringIO()
    out.write('    <mesh>\n     <vertices>\n')
    for v in m.vertices: out.write(f'      <vertex x="{fmt(v[0])}" y="{fmt(v[1])}" z="{fmt(v[2])}"/>\n')
    out.write('     </vertices>\n     <triangles>\n')
    for f in m.faces: out.write(f'      <triangle v1="{f[0]}" v2="{f[1]}" v3="{f[2]}"/>\n')
    out.write('     </triangles>\n    </mesh>\n')
    return out.getvalue()
NS = ('unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
      'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p"')
v = math.sqrt(len(plates)); cols = int(round(v)) + (1 if v > round(v) else 0)
STRIDE = BED * 1.2
z = zipfile.ZipFile(OUT3MF, 'w', zipfile.ZIP_DEFLATED, compresslevel=6)
main_objs, build_items, rels, cfg_objs, cfg_plates, assemble = [], [], [], [], [], []
next_id, obj_index, identify = 1, 0, 100
plate_names = {'navy': 'navy only', 'white': 'white only', 'gold': 'gold only', 'multi': 'multi-colour'}
plate_rows = []
def plate_label(pl):
    names = [P[i]['name'] for (i, k, a, cx, cy) in pl['items']]
    big = max(pl['items'], key=lambda it: P[it[0]]['area'])
    lead = P[big[0]]['name']
    lead = lead.replace('Wing middle', 'wing middle').replace('Wing ', 'wing ')
    rest = len(names) - 1
    return lead + (f' + {rest} more' if rest else '')
for pi, pl in enumerate(plates):
    row, col = pi // cols, pi % cols
    ox, oy = col * STRIDE, -row * STRIDE
    inst = []
    for (i, k, a, cx, cy) in pl['items']:
        p = P[i]; parts = pieces_ready[i]; obj_index += 1
        part_ids = list(range(next_id, next_id + len(parts))); obj_id = next_id + len(parts); next_id = obj_id + 1
        path = f'3D/Objects/object_{obj_index}.model'
        sub = io.StringIO()
        sub.write(f'<?xml version="1.0" encoding="UTF-8"?>\n<model {NS}>\n <metadata name="BambuStudio:3mfVersion">1</metadata>\n <resources>\n')
        R = rot('z', a)           # same turn as the packing mask (shapely, counter-clockwise)
        for pid, (m, c) in zip(part_ids, parts):
            mm = m.copy(); mm.apply_transform(R)
            sub.write(f'  <object id="{pid}" p:UUID="{uuid.uuid4()}" type="model">\n')
            sub.write(mesh_xml(mm)); sub.write('  </object>\n')
        sub.write(' </resources>\n <build/>\n</model>\n')
        z.writestr(path, sub.getvalue())
        rels.append(path)
        comps = ''.join(f'    <component p:path="/{path}" objectid="{pid}" p:UUID="{uuid.uuid4()}" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>\n' for pid in part_ids)
        main_objs.append(f'  <object id="{obj_id}" p:UUID="{uuid.uuid4()}" type="model">\n   <components>\n{comps}   </components>\n  </object>\n')
        tx, ty = ox + cx, oy + cy
        tr = f'1 0 0 0 1 0 0 0 1 {fmt(tx)} {fmt(ty)} 0'
        build_items.append(f'  <item objectid="{obj_id}" p:UUID="{uuid.uuid4()}" transform="{tr}" printable="1"/>\n')
        name = p['name'] + (f' {k + 1}' if p['qty'] > 1 else '')
        main_colour = p['parts'][0][1]
        o = [f'  <object id="{obj_id}">\n', f'    <metadata key="name" value="{name}"/>\n', f'    <metadata key="extruder" value="{SLOT[main_colour]}"/>\n']
        st = dict(SET[p['settings']]); st.update(dict(brim_type='outer_only', brim_width=str(BRIM_W)) if p['brim'] else dict(brim_type='no_brim'))
        for key, val in st.items(): o.append(f'    <metadata key="{key}" value="{val}"/>\n')
        for pid, (m, c), (f, _) in zip(part_ids, parts, p['parts']):
            o.append(f'    <part id="{pid}" subtype="normal_part">\n')
            o.append(f'      <metadata key="name" value="{os.path.basename(f)[:-4]}"/>\n')
            o.append('      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>\n')
            o.append(f'      <metadata key="extruder" value="{SLOT[c]}"/>\n')
            for key, val in PART_SET.get(p['settings'], {}).get(c, {}).items(): o.append(f'      <metadata key="{key}" value="{val}"/>\n')
            o.append('      <mesh_stat edges_fixed="0" degenerate_facets="0" facets_removed="0" facets_reversed="0" backwards_edges="0"/>\n')
            o.append('    </part>\n')
        o.append('  </object>\n'); cfg_objs.append(''.join(o))
        inst.append(f'    <model_instance>\n      <metadata key="object_id" value="{obj_id}"/>\n      <metadata key="instance_id" value="0"/>\n      <metadata key="identify_id" value="{identify}"/>\n    </model_instance>\n')
        assemble.append(f'   <assemble_item object_id="{obj_id}" instance_id="0" transform="{tr}" offset="0 0 0"/>\n')
        identify += 1
    colours = sorted({c for (i, k, a, cx, cy) in pl['items'] for _, c in P[i]['parts']}, key=lambda c: SLOT[c])
    title = f'{pi + 1:02d} {plate_names[pl["group"]]} - {plate_label(pl)}'
    cfg_plates.append(f'  <plate>\n    <metadata key="plater_id" value="{pi + 1}"/>\n    <metadata key="plater_name" value="{title}"/>\n    <metadata key="locked" value="false"/>\n'
                      + f'    <metadata key="thumbnail_file" value="Metadata/plate_{pi + 1}.png"/>\n' + ''.join(inst) + '  </plate>\n')
    # thumbnail: top view of the plate
    S = 2; img = Image.new('RGB', (int(BED * S), int(BED * S)), (58, 62, 70)); d = ImageDraw.Draw(img)
    if pl['group'] == 'multi': d.rectangle([TOWER_X0 * S, 0, TOWER_X1 * S, TOWER_D * S], outline=(160, 160, 160))
    for (i, k, a, cx, cy) in pl['items']:
        R = rot('z', a)           # same turn as the packing mask (shapely, counter-clockwise)
        tris = []                                   # every upward face of every colour, drawn lowest first
        for m, c in pieces_ready[i]:
            vv = (np.c_[m.vertices, np.ones(len(m.vertices))] @ R.T)[:, :2] + [cx, cy]
            sel = m.face_normals[:, 2] > 0.2
            zc = m.triangles_center[sel, 2]
            for t, zz in zip(vv[m.faces[sel]], zc): tris.append((zz, t, RGB[c]))
        for zz, t, col in sorted(tris, key=lambda x: x[0]):
            d.polygon([(q[0] * S, (BED - q[1]) * S) for q in t], fill=col)
    buf = io.BytesIO(); img.resize((512, 512)).save(buf, 'PNG'); z.writestr(f'Metadata/plate_{pi + 1}.png', buf.getvalue())
    small = io.BytesIO(); img.resize((128, 128)).save(small, 'PNG'); z.writestr(f'Metadata/plate_{pi + 1}_small.png', small.getvalue())
    img.save(f'ref2/plate_{pi + 1:02d}.png')
    plate_rows.append(dict(plate=pi + 1, title=title, group=pl['group'], colours=colours, swaps=pl['swaps'], print_h=pl['print_h'], grams=pl['grams'],
                           pieces=[P[i]['name'] + (f' {k + 1}' if P[i]['qty'] > 1 else '') for (i, k, a, cx, cy) in pl['items']]))
model = (f'<?xml version="1.0" encoding="UTF-8"?>\n<model {NS}>\n'
         ' <metadata name="Application">OrcaSlicer-2.3.0</metadata>\n <metadata name="BambuStudio:3mfVersion">1</metadata>\n'
         ' <metadata name="Title">Winged varsity helmet</metadata>\n <metadata name="Designer"></metadata>\n'
         ' <resources>\n' + ''.join(main_objs) + ' </resources>\n'
         f' <build p:UUID="{uuid.uuid4()}">\n' + ''.join(build_items) + ' </build>\n</model>\n')
z.writestr('3D/3dmodel.model', model)
z.writestr('3D/_rels/3dmodel.model.rels', '<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
           + ''.join(f' <Relationship Target="/{p}" Id="rel-{i + 1}" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n' for i, p in enumerate(rels))
           + '</Relationships>')
exec(open('make_project_config.py').read().split("if __name__ == '__main__':")[0])
PCFG = build(len(plates), ['#1E2A52', '#ECECE4', '#F2C12E'], (TOWER_X0 + 5, BED - TOWER_D + 1))
z.writestr('Metadata/project_settings.config', json.dumps(PCFG, indent=4))
z.writestr('Metadata/model_settings.config', '<?xml version="1.0" encoding="UTF-8"?>\n<config>\n' + ''.join(cfg_objs) + ''.join(cfg_plates)
           + '  <assemble>\n' + ''.join(assemble) + '  </assemble>\n</config>\n')
z.writestr('[Content_Types].xml', '<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
           ' <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
           ' <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>\n'
           ' <Default Extension="png" ContentType="image/png"/>\n <Default Extension="gcode" ContentType="text/x.gcode"/>\n</Types>')
z.writestr('_rels/.rels', '<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
           ' <Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n'
           ' <Relationship Target="/Metadata/plate_1.png" Id="rel-2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/thumbnail"/>\n'
           ' <Relationship Target="/Metadata/plate_1.png" Id="rel-4" Type="http://schemas.bambulab.com/package/2021/cover-thumbnail-middle"/>\n'
           ' <Relationship Target="/Metadata/plate_1_small.png" Id="rel-5" Type="http://schemas.bambulab.com/package/2021/cover-thumbnail-small"/>\n</Relationships>')
z.close()
json.dump(plate_rows, open('ref2/plates.json', 'w'), indent=1)
print('wrote', OUT3MF, '%.1f MB' % (os.path.getsize(OUT3MF) / 1e6))
for r in plate_rows:
    t = '' if r['print_h'] is None else f"{r['print_h'] + r['swaps'] * SWAP_S / 3600:5.1f} h"
    print(f"  plate {r['plate']:2d}  {r['title']:46s} {len(r['pieces']):3d} pieces  swaps {r['swaps']:3d}  {t}  {r['grams']:5.0f} g")
