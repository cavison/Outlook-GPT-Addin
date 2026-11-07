"""Split one wing into printable pieces along feather edges; draw them pulled apart (scheme B colours)."""
import pickle, numpy as np, math
from shapely.geometry import Point, Polygon, LineString
from shapely.ops import unary_union
from shapely import affinity
from PIL import Image, ImageDraw, ImageFont
D = pickle.load(open('ref2/wing_feathers.pkl', 'rb')); C = D['C']; W = D['WING']
cov = unary_union([D['cov1'], D['cov2'], D['EAGLE']]).intersection(W)
UNDER = 20                                   # how far feather pieces tuck under the shoulder piece
under = cov.difference(Point(*C).buffer(25))
P = [f['full'].buffer(1.6).intersection(W) for f in D['PRIM'] if f]
H = [f['full'].buffer(1.6).intersection(W) for f in D['HANG'] if f]
d = np.array([math.cos(math.radians(32)), math.sin(math.radians(32))]); n = np.array([-d[1], d[0]])
UCUT = 95
top = LineString([(UCUT, -300), (UCUT, 400)]).intersection(W)
p0 = np.array([UCUT, max(g.bounds[3] for g in getattr(top, 'geoms', [top]))])
front = Polygon([tuple(p0 - d * 600 + n * 400), tuple(p0 + n * 400), tuple(p0 - n * 400), tuple(p0 - d * 600 - n * 400)])
def tucked(g):
    # feathers of one section are joined by a hidden base strip under the shoulder feathers
    base = g.convex_hull.intersection(under).intersection(g.buffer(45))
    return unary_union([g, g.buffer(UNDER).intersection(under), base]).intersection(W)
# sections follow the feather-separator lines; each feather section tucks under the outer scallop row
from shapely.ops import split as _split
exec(open('wing_feathers.py').read().split('# ---------------- coverts and eagle')[0])        # WING, C, helpers
_cut = Polygon([(78.4, 13.7), (400, 13.7 - 40), (400, 600), (-300, 600), (-300, C[1] + 60), tuple(C)])
upper = W.intersection(_cut); lower = W.difference(_cut)
FLOW = ang(212)
sep1 = LineString([tuple(np.array((110.9, 110.4)) - FLOW * 30), tuple(np.array((110.9, 110.4)) + FLOW * 700)])
halves = sorted(pieces(_split(upper, sep1)), key=lambda q: -q.centroid.y)
top_r = halves[0]; low_r = unary_union(halves[1:])
cov1z = unary_union([D['cov1'], D['EAGLE']])
band = cov.difference(cov1z)                       # outer scallop row: the feather sections tuck under it
TUCK = 18                                          # hidden strip under the scallops, mm
def section(r):
    vis = r.difference(cov)
    return unary_union([vis, vis.buffer(TUCK).intersection(r).intersection(band)]).intersection(W)
arm = top_r.intersection(front)
# the two scallops over the front-edge / top-feather joint belong to the front-edge section
seam_lobes = unary_union(D['SEAM_LOBES']).intersection(W)
# the smallest long feather at the back corner goes with the hanging feathers (it sits beside them)
sep4 = LineString([tuple(np.array((84.6, 34.9)) - FLOW * 30), tuple(np.array((84.6, 34.9)) + FLOW * 700)])
lp = sorted(pieces(_split(low_r, sep4)), key=lambda q: -q.centroid.y)
low_main = lp[0]; corner = unary_union(lp[1:])
PIECES = [
    ('Shoulder: eagle + scallops', cov.difference(seam_lobes)),
    ('Front top edge', unary_union([section(arm), seam_lobes])),
    ('Top long feathers', section(top_r.difference(front))),
    ('Lower long feathers', section(low_main)),
    ('Hanging feathers', section(unary_union([lower, corner]))),
]
def fit(g):
    r = g.minimum_rotated_rectangle; xy = np.array(r.exterior.coords)
    return sorted([np.linalg.norm(xy[1] - xy[0]), np.linalg.norm(xy[2] - xy[1])])
extra = []
for i in range(1, len(PIECES)):
    k, g = PIECES[i]
    parts = sorted(getattr(g, 'geoms', [g]), key=lambda q: -q.area)
    print('  %s: %d part(s), %s' % (k, len(parts), [(round(q.area), tuple(np.round(q.centroid.coords[0]))) for q in parts[:4]]))
    PIECES[i] = (k, parts[0]); extra += [q for q in parts[1:]]
PIECES[0] = (PIECES[0][0], unary_union([PIECES[0][1]] + extra))
SIZES = [fit(g) for _, g in PIECES]
for (k, g), e in zip(PIECES, SIZES): print('%-28s %4.0f x %4.0f mm' % (k, e[0], e[1]))
pickle.dump(dict(PIECES=PIECES, SIZES=SIZES), open('ref2/wing_pieces.pkl', 'wb'))
if __name__ == '__main__':
    # pulled-apart drawing: each piece moved out from the shoulder, painted with scheme B
    from wing_schemes import wing_image
    import wing_schemes as ws
    full = ws.wing_image(ws.scheme_B)                     # full painted wing at wing_draw scale
    from wing_draw import S, U0, V0
    mask_base = Image.new('L', full.size, 0)
    out = Image.new('RGB', (int(full.width * 1.55), int(full.height * 1.45)), 'white')
    OX, OY = int(full.width * 0.22), int(full.height * 0.2)
    F = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 26)
    dr = ImageDraw.Draw(out)
    labels = []
    def mask_of(geom):
        m = Image.new('L', full.size, 0); md = ImageDraw.Draw(m)
        for q in getattr(geom, 'geoms', [geom]):
            if q.geom_type != 'Polygon' or q.is_empty: continue
            md.polygon([((x - U0) * S, (V0 - y) * S) for x, y in q.exterior.coords], fill=255)
            for h in q.interiors: md.polygon([((x - U0) * S, (V0 - y) * S) for x, y in h.coords], fill=0)
        return m
    hidden_col = Image.new('RGB', full.size, (78, 92, 140))
    for i, (k, g) in enumerate(PIECES):
        cov_hide = cov.difference(seam_lobes)          # the seam scallops are on top, not hidden
        vis = g if i == 0 else g.difference(cov_hide)
        hid = None if i == 0 else g.intersection(cov_hide)
        cx, cy = vis.centroid.coords[0]
        v = np.array([cx - C[0], cy - C[1]]); L = np.linalg.norm(v)
        off = (v / L * 55) if L > 1 else np.zeros(2)
        dx, dy = int(off[0] * S) + OX, int(-off[1] * S) + OY
        if hid is not None and not hid.is_empty: out.paste(hidden_col, (dx, dy), mask_of(hid))
        out.paste(full, (dx, dy), mask_of(vis))
        px, py = (cx - U0) * S + dx, (V0 - cy) * S + dy
        labels.append((i + 1, px, py))
    # snap pegs: pink = joins the three layers, orange = joins this section to the shoulder scallops
    import os
    if os.path.exists('ref2/wing_pegs.pkl'):
        PG = pickle.load(open('ref2/wing_pegs.pkl', 'rb'))
        for kind, col in (('LAYER', (224, 36, 94)), ('JOINT', (255, 140, 0))):
            for q in PG[kind]:
                pt = Point(*q)
                # which section is it in (joint pegs: the feather section that owns the tuck strip)
                own = [i for i, (k, g) in enumerate(PIECES) if g.buffer(0.5).contains(pt)]
                if kind == 'JOINT': own = [i for i in own if i > 0] or own
                if not own: continue
                i = own[0] if kind == 'LAYER' else own[-1]
                g = PIECES[i][1]
                cov_hide = cov.difference(seam_lobes)
                vis = g if i == 0 else g.difference(cov_hide)
                cx, cy = vis.centroid.coords[0]
                v = np.array([cx - C[0], cy - C[1]]); L = np.linalg.norm(v)
                off = (v / L * 55) if L > 1 else np.zeros(2)
                dx, dy = int(off[0] * S) + OX, int(-off[1] * S) + OY
                px, py = (q[0] - U0) * S + dx, (V0 - q[1]) * S + dy
                if kind == 'LAYER': dr.ellipse((px - 9, py - 9, px + 9, py + 9), fill=col, outline='white', width=2)
                else: dr.polygon([(px, py - 11), (px + 11, py), (px, py + 11), (px - 11, py)], fill=col, outline='white')
    for nlab, px, py in labels:
        dr.ellipse((px - 22, py - 22, px + 22, py + 22), fill=(27, 31, 42), outline='white', width=3)
        dr.text((px, py), str(nlab), font=F, fill='white', anchor='mm')
    bb = Image.eval(out.convert('L'), lambda v: 255 - v).getbbox(); out = out.crop((bb[0] - 20, bb[1] - 20, bb[2] + 20, bb[3] + 20))
    out.save('ref2/wing_pieces.png'); print(out.size)
