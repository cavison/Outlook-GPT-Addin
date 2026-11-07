"""Redraw the band scrollwork as clean strokes.
From the photo's gold areas (unrolled band): find each gold line's centre line
(skeleton), fit smooth curves, then draw every line again at its own smoothed width,
with pointed tips where a line ends.  Output is clean vector outlines in the same
[angle, t] form as before.  usage: scroll_strokes.py   (writes helmet/band_motif4.scad)"""
import re, json
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from skimage import morphology, measure
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union
exec(open('trace_band3.py').read().split("out = {}")[0])        # load(), rims(), unwrap(), dots()

R_MM, FIELD_MM = 107.0, 27.0          # band radius and nominal field height (full size)
MMPX = 0.05                           # working grid: 0.05 mm per cell
DOT_MIN = 99 
DOT_S_MIN = 0.0                       # set per side: no round dots nearer the centre line than this (mm)                        # a width peak above this radius (mm) is a round dot, not a line

def iso_grid(score, phis, ts):
    """resample the [t, angle] grid to square 0.05 mm cells: returns grid, s0 (mm), helpers"""
    s_mm = np.radians(phis) * R_MM; z_mm = ts * FIELD_MM
    ns = int((s_mm[-1] - s_mm[0]) / MMPX); nz = int(FIELD_MM / MMPX)
    S = np.linspace(s_mm[0], s_mm[-1], ns); Z = np.linspace(0, FIELD_MM, nz)
    ci = np.interp(S, s_mm, np.arange(len(phis))); ri = np.interp(Z, z_mm, np.arange(len(ts)))
    RR, CC = np.meshgrid(ri, ci, indexing='ij')
    return ndimage.map_coordinates(score, [RR, CC], order=1), S, Z

def skeleton_paths(skel):
    """split a skeleton into paths between end points / junctions; returns lists of (r, c)"""
    k = np.ones((3, 3)); k[1, 1] = 0
    nb = ndimage.convolve(skel.astype(int), k, mode='constant') * skel
    node = skel & ((nb == 1) | (nb >= 3))
    H, W = skel.shape
    def nbrs(r, c):
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if (dr or dc) and 0 <= r + dr < H and 0 <= c + dc < W and skel[r + dr, c + dc]:
                    yield r + dr, c + dc
    used = set(); paths = []
    for r, c in zip(*np.nonzero(node)):
        for n in nbrs(r, c):
            if node[n]:
                continue
            if ((r, c), n) in used: continue
            path = [(r, c), n]; prev, cur = (r, c), n
            while not node[cur]:
                nxt = [q for q in nbrs(*cur) if q != prev and q not in path[-3:]]
                if not nxt: break
                prev, cur = cur, nxt[0]; path.append(cur)
            used.add(((r, c), path[1])); used.add((path[-1], path[-2]))
            paths.append(path)
    # closed loops with no nodes
    left = skel.copy()
    for p in paths:
        for q in p: left[q] = False
    lab, nl = ndimage.label(left, np.ones((3, 3)))
    for i in range(1, nl + 1):
        pts = list(zip(*np.nonzero(lab == i)))
        if len(pts) < 20: continue
        start = pts[0]; path = [start]; prev = None; cur = start
        while True:
            nxt = [q for q in nbrs(*cur) if lab[q] == i and q != prev and q not in path[-3:]]
            if not nxt or (len(path) > 3 and start in nxt): break
            prev, cur = cur, nxt[0]; path.append(cur)
        paths.append(path + [start])
    return paths, node, nb

def round_blobs(mask, S):
    """small, separate, roundish gold blobs (the spiral's centre, the end dot): return circles and the mask without them"""
    lab = measure.label(mask); circles = []; rest = mask.copy()
    for rp in measure.regionprops(lab):
        area_mm2 = rp.area * MMPX ** 2
        if area_mm2 < 80 and rp.eccentricity < 0.9 and rp.solidity > 0.85 and S[0] + rp.centroid[1] * MMPX > DOT_S_MIN:
            r, c = rp.centroid
            circles.append((S[0] + c * MMPX, r * MMPX, np.sqrt(area_mm2 / np.pi)))
            rest[lab == rp.label] = False
    return circles, rest

PRUNE_MM = 3.2
def strokes(mask, dt, S, Z, prune_mm=None):
    prune_mm = prune_mm or PRUNE_MM
    circles, mask = round_blobs(mask, S)
    skel = morphology.skeletonize(mask)
    for _ in range(6):                                   # prune short spurs (they would draw as thorns)
        paths, node, nb = skeleton_paths(skel)
        changed = False
        for p in paths:
            ends = [nb[q] == 1 for q in (p[0], p[-1])]
            if any(ends) and len(p) * MMPX < prune_mm:
                for q in p:
                    if nb[q] < 3: skel[q] = False
                changed = True
        if not changed: break
        skel = morphology.skeletonize(skel)
    paths, node, nb = skeleton_paths(skel)
    from scipy.interpolate import splprep, splev
    shapes = []
    for p in paths:
        if len(p) * MMPX < 1.5: continue
        p = np.array(p, float)
        closed = len(p) > 3 and np.all(p[0] == p[-1])
        wloc = 2 * dt[p[:, 0].astype(int), p[:, 1].astype(int)] * MMPX
        wc = float(np.clip(np.median(wloc), 1.4, 4.2))          # one even width per line
        xy = np.stack([S[0] + p[:, 1] * MMPX, p[:, 0] * MMPX], 1)
        if closed: xy = xy[:-1]
        # one smooth curve through the centre line
        try:
            tck, _ = splprep([xy[:, 0], xy[:, 1]], s=len(xy) * 0.12 ** 2, per=1 if closed else 0, k=3)
        except Exception:
            continue
        L = np.sum(np.linalg.norm(np.diff(xy, axis=0), axis=1))
        uu = np.linspace(0, 1, max(20, int(L / 0.15)), endpoint=not closed)
        xy = np.stack(splev(uu, tck), 1)
        e0 = (not closed) and nb[tuple(p[0].astype(int))] == 1
        e1 = (not closed) and nb[tuple(p[-1].astype(int))] == 1
        d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(xy, axis=0), axis=1))]
        w = np.full(len(xy), wc)
        Lt = 2.4 * wc                                          # long, even taper to a sharp tip
        if e0: w = w * np.clip(d / Lt, 0.0, 1)
        if e1: w = w * np.clip((d[-1] - d) / Lt, 0.0, 1)
        t = np.gradient(xy, axis=0); t /= np.linalg.norm(t, axis=1, keepdims=True) + 1e-9
        n = np.stack([-t[:, 1], t[:, 0]], 1)
        left = xy + n * w[:, None] / 2; right = xy - n * w[:, None] / 2
        if closed:
            shapes.append(Polygon(left).buffer(0).difference(Polygon(right).buffer(0)) if Polygon(left).area > Polygon(right).area
                          else Polygon(right).buffer(0).difference(Polygon(left).buffer(0)))
        else:
            shapes.append(Polygon(np.vstack([left, right[::-1]])).buffer(0))
            for k, e in ((0, e0), (-1, e1)):
                if not e: shapes.append(Point(xy[k]).buffer(wc / 2, 32))
    for x, y, r in circles:
        shapes.append(Point(x, y).buffer(r, 48))
        print('  gold dot at %.1f deg, z=%.1f mm, r=%.1f mm' % (np.degrees(x / R_MM), y, r))
    return unary_union(shapes).simplify(0.015)

def to_sets(geom, s0_deg_fn):
    rings = []
    geoms = [geom] if geom.geom_type == 'Polygon' else list(geom.geoms)
    for g in geoms:
        if g.area < 4.0: continue                         # no slivers or crumbs (under 4 mm2 at full size)
        for ring in [g.exterior] + list(g.interiors):
            a = np.array(ring.coords)[:-1]
            if len(a) < 4: continue
            if ring is not g.exterior and Polygon(a).area < 0.25: continue
            rings.append(np.stack([np.degrees(a[:, 0] / R_MM), a[:, 1] / FIELD_MM], 1))
    return rings

def run(img_name, xc, R, rim_args, phis, cut, th_of_phi):
    I = load(img_name); pt, pb = rims(I, *rim_args)
    G, Wt, ts, pth, ptt = unwrap(I, xc, R, pt, pb, phis, 520)
    TH, TT = np.meshgrid(th_of_phi(phis), ts)
    G = G * ~cut(TH, TT)
    g, S, Z = iso_grid(G, phis, ts)
    g = ndimage.gaussian_filter(g, 3) > 0.5
    g = morphology.remove_small_objects(g, int(1.5 / MMPX ** 2)); g = morphology.remove_small_holes(g, int(0.8 / MMPX ** 2))
    dt = ndimage.distance_transform_edt(g)
    geom = strokes(g, dt, S, Z)
    sets = to_sets(geom, None)
    if th_of_phi(np.array([0.0]))[0] != 0.0:            # back: angle = 180 - phi
        sets = [np.stack([180.0 - p[:, 0], p[:, 1]], 1) for p in sets]
    return sets, (G, Wt, ts, pth, ptt)

front, fr = run('fdb87b20-image.jpg', 689.0, 188.0, (742, 868, 385, 530), np.linspace(9.6, 70.0, 2400),
                lambda TH, TT: (TH < 11.0) | ((TH < 21.0) & (TT < 0.32)), lambda p: p)
DOT_S_MIN = np.radians(19.0) * R_MM      # back: keep clear of the V
PRUNE_MM = 5.5                           # back: wedge corners would otherwise draw as thorns
back, br = run('e0a9281d-image.jpg', 687.5, 183.0, (700, 862, 440, 620), np.linspace(14.0, 72.0, 2300),
               lambda TH, TT: (TH > 161.0), lambda p: 180.0 - p)
dots_f = dots(fr[1] * ~((np.meshgrid(np.linspace(9.6, 70.0, 2400), fr[2])[0] < 21.0) & (np.meshgrid(np.linspace(9.6, 70.0, 2400), fr[2])[1] < 0.32)),
              np.linspace(9.6, 70.0, 2400), fr[2], (fr[3], fr[4]), None)
dots_b = dots(br[1], 180.0 - np.linspace(14.0, 72.0, 2300), br[2], (br[3], br[4]), None)
with open('helmet/band_motif4.scad', 'w') as f:
    f.write('// Brow-band scrollwork redrawn as clean strokes from the new front and back pictures (one side).\n')
    f.write('// Outlines: [angle (deg, 0 = front centre, 180 = back centre), t] with t = 0 at the bottom of\n')
    f.write('// the top rim and 1 at the top of the bottom rim (even-odd).  Dots: [angle, t, diameter in band half-widths].\n')
    for k, v in (('BAND_FRONT_GOLD', front), ('BAND_BACK_GOLD', back)):
        f.write(f"{k} = [\n" + ",\n".join("  [" + ",".join(f"[{p:.3f},{q:.4f}]" for p, q in poly) + "]" for poly in v) + "\n];\n")
    for k, v in (('BAND_FRONT_DOTS', dots_f), ('BAND_BACK_DOTS', dots_b)):
        f.write(f"{k} = [" + ", ".join(f"[{a:.3f},{b:.4f},{c:.4f}]" for a, b, c in v) + "];\n")
print('front rings', len(front), 'back rings', len(back), 'dots', len(dots_f), len(dots_b))
