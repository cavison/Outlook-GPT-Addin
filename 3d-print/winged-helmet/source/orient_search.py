#!/usr/bin/env python
# Find a print orientation for every helmet piece (the wing pieces are already flat):
#   * as much flat contact with the bed as possible,
#   * as little support as possible, and support on the hidden (inner) faces rather than the show faces,
#   * fits the AD5X: footprint within 216 x 216, height within 218.
# Writes ref2/orient.json: piece name -> 4x4 rotation (applied to the piece in helmet coordinates).
import json, math, sys, numpy as np, trimesh
from shapely.geometry import MultiPoint
src = open('plates_build.py').read()
exec(src[:src.index('# ---------- orient every piece ----------')])
K = 1.23505
COS45 = math.cos(math.radians(30))          # Orca AD5X: support where the slope is under 30 deg from horizontal
def fib(n):
    i = np.arange(n) + 0.5; phi = np.arccos(1 - 2 * i / n); th = math.pi * (1 + 5 ** 0.5) * i
    return np.c_[np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)]
DIRS = fib(4000)
def align_down(g):
    """rotation taking direction g to -z"""
    g = g / np.linalg.norm(g); t = np.array([0, 0, -1.0]); v = np.cross(g, t); c = float(g @ t)
    if np.linalg.norm(v) < 1e-9: R = np.eye(3) if c > 0 else np.diag([1., -1., -1.])
    else:
        vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]]); R = np.eye(3) + vx + vx @ vx / (1 + c)
    return R
def evaluate(m, outer, dirs):
    n, A, C = m.face_normals, m.area_faces, m.triangles_center
    V = m.vertices
    res = []
    for chunk in np.array_split(np.arange(len(dirs)), max(1, len(dirs) // 200)):
        G = dirs[chunk]                                     # (k,3) down directions
        hv = -(V @ G.T); h0 = hv.min(0)                     # vertex heights
        hc = -(C @ G.T) - h0                                # face-centre heights (F,k)
        ng = n @ G.T                                        # cos(normal, down)
        contact = ((ng > 0.985) & (hc < 0.3)) * A[:, None]
        over = (ng > COS45) & (hc >= 0.3)
        sup = over * (A * 1.0)[:, None] * ng * hc
        w = np.where(outer, 4.0, 1.0)[:, None]               # supports on a show face count 4x
        height = hv.max(0) - h0
        res.append(np.c_[contact.sum(0), (sup * w).sum(0), sup.sum(0), height])
    return np.vstack(res)
def footprint_ok(m, g):
    """fits within 216 x 216 at SOME turn on the bed (not only the minimum-area rectangle)"""
    R = align_down(g); p = (m.vertices @ R.T)[:, :2]
    hull = np.array(MultiPoint(p[::max(1, len(p) // 3000)]).convex_hull.exterior.coords)
    best = None
    for a in np.radians(np.arange(0, 90, 2.0)):
        c, s_ = math.cos(a), math.sin(a)
        e = np.ptp(hull @ np.array([[c, -s_], [s_, c]]).T, 0)
        if best is None or max(e) < max(best): best = e
    e = sorted(best)
    return e[1] <= 216 and e[0] <= 216, e
def base_ok(m, g):
    """the piece stands on a real base: the points within 1 mm of the bed span a decent area and the
    centre of mass sits over it"""
    from shapely.geometry import Point
    R = align_down(g); p = m.vertices @ R.T; h = p[:, 2] - p[:, 2].min()
    low = p[h < 1.0][:, :2]
    if len(low) < 3: return False, 0.0
    hull = MultiPoint(low[::max(1, len(low) // 4000)]).convex_hull
    if hull.area < 1.0: return False, 0.0
    rect = np.array(hull.minimum_rotated_rectangle.exterior.coords)[:4]
    short = min(np.linalg.norm(rect[1] - rect[0]), np.linalg.norm(rect[2] - rect[1]))
    allr = np.array(MultiPoint(p[::max(1, len(p) // 3000), :2]).minimum_rotated_rectangle.exterior.coords)[:4]
    fshort = min(np.linalg.norm(allr[1] - allr[0]), np.linalg.norm(allr[2] - allr[1]))
    com = (m.center_mass if m.is_volume else m.centroid) @ R.T
    inside = hull.buffer(2.0).contains(Point(com[0], com[1]))
    need = min(20.0, 0.5 * fshort) if fshort >= 30 else 0.35 * fshort      # strips on edge: a narrow base is all they have
    return (short >= need and inside), float(hull.area)
def contact_cells(m, G):
    """how much of the piece touches the bed (vertices within 0.8 mm, counted in 2 mm cells) for each down
    direction, and whether the centre of mass sits over the touching points"""
    from shapely.geometry import Point
    V = m.vertices[::max(1, len(m.vertices) // 20000)]
    com = m.center_mass if m.is_volume else m.centroid
    cells, stable = [], []
    for g in G:
        R = align_down(g); p = V @ R.T; h = p[:, 2] - p[:, 2].min()
        low = p[h < 0.8][:, :2]
        u = np.unique(np.floor(low / 2.0).astype(int), axis=0)
        cells.append(len(u))
        if len(u) >= 3:
            hull = MultiPoint(low).convex_hull.buffer(5.0); c = com @ R.T
            stable.append(hull.contains(Point(c[0], c[1])))
        else: stable.append(False)
    return np.array(cells), np.array(stable)
def solve(name, parts, extra=(), only=None):
    m = trimesh.util.concatenate([q for q, _ in parts])
    C = m.triangles_center
    radial = np.c_[C[:, 0], C[:, 1] / K ** 2, np.maximum(C[:, 2], 0)]
    outer = np.einsum('ij,ij->i', m.face_normals, radial) > 0
    dirs = np.vstack([DIRS] + [np.asarray(e, float).reshape(1, 3) for e in extra])
    if only is not None: dirs = np.asarray(only, float).reshape(1, 3) / np.linalg.norm(only)
    contact, sup_w, sup, height = evaluate(m, outer, dirs).T
    cells, stable = contact_cells(m, dirs)
    # cm3 of support (4x on show faces) + 1 cm3 per 100 mm of height - 1 cm3 per 20 touching cells
    score = sup_w / 1000.0 + 0.01 * height - 0.05 * cells
    score[(height > 218) | ~stable | (cells < 8)] = np.inf
    if only is not None: score[:] = 0
    for k in np.argsort(score):
        if not np.isfinite(score[k]): break
        ok, e = footprint_ok(m, dirs[k])
        if ok: return dirs[k], dict(contact=float(contact[k]), support=float(sup[k]), support_weighted=float(sup_w[k]), height=float(height[k]),
                                    foot=[round(x) for x in e], base=int(cells[k]), score=float(score[k]))
    raise SystemExit('no orientation fits for ' + name)
FIXED = {}
SEARCH = ('Shell front', 'Shell back', 'Cheek guard R', 'Cheek guard L', 'Cheek frame R', 'Cheek frame L', 'Neck plate',
          'Back V navy', 'Back V gold', 'Nose clip', 'Nose panel')
if __name__ == '__main__':
    out = {}
    want = sys.argv[1:] or None
    for p in P:
        if not (p['name'] in SEARCH or p['name'] in FIXED or p['name'].startswith('Band ')): continue
        if want and p['name'] not in want: continue
        parts = [(trimesh.load(f), c) for f, c in p['parts']]
        if p['name'] in FIXED:
            g, info = solve(p['name'], parts, only=FIXED[p['name']])
        else:
            g, info = solve(p['name'], parts, extra=[(0, 0, -1), (0, 0, 1), (0, 1, 0), (0, -1, 0), (0, -0.4455, -0.8953)])
        R = np.eye(4); R[:3, :3] = align_down(g)
        out[p['name']] = dict(R=R.tolist(), **info)
        print(f"{p['name']:26s} contact {info['contact']:7.0f} mm2  support {info['support'] / 1000:6.1f} cm3 (weighted {info['support_weighted'] / 1000:6.1f})  h {info['height']:5.1f}  foot {info['foot']}  cells {info['base']}  down {np.round(g, 2).tolist()}")
    old = json.load(open('ref2/orient.json')) if want else {}
    old.update(out); json.dump(old, open('ref2/orient.json', 'w'), indent=1)
