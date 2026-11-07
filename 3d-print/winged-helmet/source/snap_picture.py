# Concept 2: feathers snap into one-piece collars, collars clamp into the medallion sandwich
import pickle, math, numpy as np
from shapely.geometry import Point, Polygon, LineString, box
from shapely.ops import unary_union
from shapely import affinity
from PIL import Image, ImageDraw, ImageFont
h = pickle.load(open('ref2/hub_regions.pkl', 'rb')); REG, MED, C, plate = h['REG'], h['MED'], h['C'], h['plate']
lc = pickle.load(open('ref2/layered_concept.pkl', 'rb')); V = lc['V']
FE = ['P1', 'P2', 'P3', 'P4', 'H1', 'H2', 'H3', 'H4', 'H5']
TIPS = ['P5', 'H6']
LBL = {'P1': 'F1', 'P2': 'F2', 'P3': 'F3', 'P4': 'F4', 'H1': 'F5', 'H2': 'F6', 'H3': 'F7', 'H4': 'F8', 'H5': 'F9', 'P5': 'tip A', 'H6': 'tip B'}
COLLAR_OF = {n: ('CU' if n[0] == 'P' else 'CL') for n in FE}
RIM_IN = 50.0
# collars: their own area plus an inner rim that tucks between the medallions
def collar_shape(n):
    reg = REG[n]
    angs = [math.atan2(y - C[1], x - C[0]) for x, y in reg.exterior.coords if Point(x, y).distance(Point(*C)) < 80]
    a = np.unwrap(sorted(angs)); a0, a1 = min(a), max(a)
    wedge = Polygon([tuple(C)] + [(C[0] + 200 * math.cos(t), C[1] + 200 * math.sin(t)) for t in np.linspace(a0, a1, 60)])
    rim = MED.difference(Point(*C).buffer(RIM_IN, 256)).intersection(wedge)
    return unary_union([reg, rim]).buffer(0.01).buffer(-0.01), rim
COL_SHAPE = {n: collar_shape(n) for n in ('CU', 'CL')}
# tongue on each feather root, socket of the same shape in its collar
TONGUE = {}
for n in FE:
    col = REG[COLLAR_OF[n]]
    shared = REG[n].buffer(0.8).intersection(col.buffer(0.8))
    rect = shared.minimum_rotated_rectangle
    cs = np.array(rect.exterior.coords)[:4]
    e1, e2 = cs[1] - cs[0], cs[2] - cs[1]
    edge = e1 if np.linalg.norm(e1) > np.linalg.norm(e2) else e2
    L = np.linalg.norm(edge); u = edge / L; nrm = np.array([-u[1], u[0]])
    mid = np.array([shared.centroid.x, shared.centroid.y])
    if col.contains(Point(*(mid + 5 * nrm))) is False and REG[n].contains(Point(*(mid + 5 * nrm))): nrm = -nrm
    w = min(0.6 * L, 30.0); dep = 16.0
    poly = Polygon([mid - u * w / 2 - nrm * 1.0, mid + u * w / 2 - nrm * 1.0, mid + u * w / 2 + nrm * dep, mid - u * w / 2 + nrm * dep])
    TONGUE[n] = poly.intersection(col.buffer(-1.5)).union(poly.intersection(REG[n].buffer(0.5)))
COLV = {'navy': (32, 44, 86), 'gold': (240, 190, 50), 'white': (238, 238, 230)}
def shade(c, f): return tuple(int(v * f) for v in c)
def Fnt(sz, b=False): return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf' % ('-Bold' if b else ''), sz)
W_, H_ = 2900, 1660
img = Image.new('RGB', (W_, H_), (247, 246, 242)); dr = ImageDraw.Draw(img)
def fill(p, T, col, outline=None, width=2):
    for q in getattr(p, 'geoms', [p]):
        if q.geom_type != 'Polygon' or q.is_empty: continue
        ext = [T(x, y) for x, y in q.exterior.coords]; holes = [[T(x, y) for x, y in hh.coords] for hh in q.interiors]
        xs = [a for a, _ in ext]; ys = [b for _, b in ext]
        bx0, by0, bx1, by1 = max(int(min(xs)) - 2, 0), max(int(min(ys)) - 2, 0), min(int(max(xs)) + 3, W_), min(int(max(ys)) + 3, H_)
        if bx1 <= bx0 or by1 <= by0: continue
        m = Image.new('L', (bx1 - bx0, by1 - by0), 0); md = ImageDraw.Draw(m)
        md.polygon([(a - bx0, b - by0) for a, b in ext], fill=255)
        for hh in holes: md.polygon([(a - bx0, b - by0) for a, b in hh], fill=0)
        img.paste(Image.new('RGB', m.size, col), (bx0, by0), m)
        if outline:
            dr.line(ext + [ext[0]], fill=outline, width=width)
def art(region, T):
    fill(region, T, COLV['navy'])
    for c in ('gold', 'white', 'navy'):
        g = V[c].intersection(region)
        if not g.is_empty: fill(g, T, COLV[c])
# ---------------- left: exploded in the plane of the wing ----------------
x0, y0, x1, y1 = plate.bounds
S = 2.15; ox, oy = 90, 170
def T_off(dx, dy): return lambda x, y: (ox + (x + dx - x0 + 40) * S, oy + (y1 + 30 - y - dy) * S)
dr.text((50, 30), 'Your version: feathers snap into the collars, collars clamp into the medallions', fill=(30, 30, 30), font=Fnt(32, True))
dr.text((50, 76), 'pulled apart in the plane of the wing - every piece is coloured on both faces', fill=(90, 90, 90), font=Fnt(22))
def push(g, dist):
    p = g.centroid; v = np.array([p.x - C[0], p.y - C[1]]); v = v / (np.linalg.norm(v) + 1e-9)
    return v * dist
# medallion (stays), collars pushed out a little, feathers further
Tm = T_off(0, 0)
art(MED, Tm); dr.line([Tm(*c) for c in MED.exterior.coords], fill=(40, 40, 40), width=2)
for n in ('CU', 'CL'):
    shape, rim = COL_SHAPE[n]
    dv = push(REG[n], 30); T = T_off(*dv)
    shape = REG[n]
    art(shape, T)
    for m in FE:
        if COLLAR_OF[m] == n and not TONGUE[m].is_empty: fill(TONGUE[m], T, (25, 25, 30))     # sockets
    dr.line([T(*c) for c in shape.exterior.coords], fill=(40, 40, 40), width=2)
for n in FE + TIPS:
    dv = push(REG[n], 80 if n in FE else 110); T = T_off(*dv)
    art(REG[n], T)
    if n in TONGUE and not TONGUE[n].is_empty: fill(TONGUE[n], T, (150, 150, 160), outline=(60, 60, 60))
    dr.line([T(*c) for c in REG[n].exterior.coords], fill=(40, 40, 40), width=2)
    p = REG[n].representative_point(); tx, ty = T(p.x, p.y)
    col = (225, 40, 40) if n in FE else (150, 80, 200)
    w = 24 if n in FE else 44
    dr.rounded_rectangle([tx - w, ty - 14, tx + w, ty + 14], 6, fill=col); dr.text((tx - w + 6, ty - 12), LBL[n], fill='white', font=Fnt(19, True))
for n, txt in (('CU', 'UPPER COLLAR'), ('CL', 'LOWER COLLAR')):
    comps = pickle.load(open('ref2/feather_comps.pkl', 'rb'))
    ids = [13, 11] if n == 'CU' else [17, 21]
    p = unary_union([comps[i] for i in ids]).centroid; dv = push(REG[n], 30); tx, ty = T_off(*dv)(p.x, p.y)
    dr.rounded_rectangle([tx - 82, ty - 15, tx + 82, ty + 15], 6, fill=(40, 120, 200)); dr.text((tx - 74, ty - 13), txt, fill='white', font=Fnt(19, True))
tx, ty = Tm(*C); dr.rounded_rectangle([tx - 80, ty + 95, tx + 80, ty + 125], 6, fill=(40, 150, 60)); dr.text((tx - 72, ty + 98), 'MEDALLIONS', fill='white', font=Fnt(19, True))
for tip, host in (('P5', 'P4'), ('H6', 'H5')):
    a = REG[tip].representative_point(); b = REG[host].representative_point()
    Ta = T_off(*push(REG[tip], 110)); Tb = T_off(*push(REG[host], 80))
    dr.line([Ta(a.x, a.y), Tb(b.x, b.y)], fill=(150, 80, 200), width=3)
dr.text((60, 1360), 'tips A and B sit against F4 and F9 with no collar edge to reach, so they click onto those', fill=(110, 60, 160), font=Fnt(20))
dr.text((60, 1388), 'feathers the same way (or I can extend the collar a little to reach them)', fill=(110, 60, 160), font=Fnt(20))
# legend
ly = 1450
for col, t in (((150, 150, 160), 'tongue on the feather root'), ((25, 25, 30), 'socket in the collar it clicks into')):
    dr.rectangle([60, ly, 90, ly + 24], fill=col, outline=(60, 60, 60)); dr.text((100, ly), t, fill=(50, 50, 50), font=Fnt(20)); ly += 36
# ---------------- right: joint close-ups ----------------
rx = 1700
dr.text((rx, 150), '1  Feather into collar (top view)', fill=(30, 30, 30), font=Fnt(26, True))
# simple schematic: collar block with a slot, feather with tongue + side barb
cxx, cyy = rx + 20, 210; s = 4.0
def R(a, b, c, d, col, out=(60, 60, 60)): dr.rectangle([cxx + a * s, cyy + b * s, cxx + c * s, cyy + d * s], fill=col, outline=out)
R(0, 0, 60, 50, COLV['gold'])                                        # collar
R(38, 15, 60, 35, (25, 25, 30))                                      # socket
dr.polygon([(cxx + 40 * s, cyy + 15 * s), (cxx + 44 * s, cyy + 15 * s), (cxx + 42 * s, cyy + 12 * s)], fill=(25, 25, 30))   # notch
R(75, 5, 150, 45, COLV['navy'])                                      # feather
R(53, 15.5, 75, 34.5, (150, 150, 160))                               # tongue
dr.polygon([(cxx + 55 * s, cyy + 15.5 * s), (cxx + 60 * s, cyy + 15.5 * s), (cxx + 57 * s, cyy + 12.5 * s)], fill=(150, 150, 160), outline=(60, 60, 60))   # barb
dr.line([(cxx + 66 * s, cyy + 25 * s), (cxx + 50 * s, cyy + 25 * s)], fill=(200, 30, 30), width=4)
dr.polygon([(cxx + 50 * s, cyy + 22 * s), (cxx + 50 * s, cyy + 28 * s), (cxx + 45 * s, cyy + 25 * s)], fill=(200, 30, 30))
dr.text((cxx, cyy + 54 * s), 'the tongue slides in and a small barb clicks into a notch', fill=(60, 60, 60), font=Fnt(19))
dr.text((cxx, cyy + 54 * s + 26), 'inside the socket - nothing shows on either face', fill=(60, 60, 60), font=Fnt(19))
# cross-section feather / collar
yy = 620
dr.text((rx, yy), '2  Same joint, cut through (edge view)', fill=(30, 30, 30), font=Fnt(26, True))
k = 9; bx, by = rx + 20, yy + 150
def E(a, z0, b, z1, col): dr.rectangle([bx + a * 3.2, by - z1 * k, bx + b * 3.2, by - z0 * k], fill=col, outline=(60, 60, 60))
E(0, 0, 70, 1.0, COLV['gold']); E(0, 1.0, 70, 5.4, COLV['navy']); E(0, 5.4, 70, 6.4, COLV['gold'])     # collar 6.4
E(48, 2.0, 70, 4.4, (25, 25, 30))                                                                        # slot
E(70, 1.0, 160, 2.0, COLV['gold']); E(70, 2.0, 160, 4.4, COLV['navy']); E(70, 4.4, 160, 5.4, COLV['gold'])  # feather 4.4
E(50, 2.05, 70, 4.35, (150, 150, 160))                                                                      # tongue
dr.text((bx, by + 14), 'collar 6.4 mm', fill=(60, 60, 60), font=Fnt(18)); dr.text((bx + 80 * 3.2, by + 14), 'feather 4.4 mm', fill=(60, 60, 60), font=Fnt(18))
dr.text((bx, by + 40), 'both faces coloured; the collar sits a touch proud of the feather,', fill=(60, 60, 60), font=Fnt(18))
dr.text((bx, by + 64), 'like real covert feathers lying over the long ones', fill=(60, 60, 60), font=Fnt(18))
# collar into medallion sandwich
yy = 980
dr.text((rx, yy), '3  Collars into the medallion sandwich', fill=(30, 30, 30), font=Fnt(26, True))
bx, by = rx + 20, yy + 190
E(0, 0, 60, 3.0, COLV['navy']); E(0, 9.4, 60, 12.4, COLV['navy'])                                      # back / front medallion
E(30, 3.0, 130, 9.4, COLV['gold'])                                                                       # collar rim between
for px in (40, 52):
    dr.rectangle([bx + px * 3.2 - 4, by - 12.4 * k, bx + px * 3.2 + 4, by], fill=(110, 110, 110))
dr.polygon([(bx + 10 * 3.2, by), (bx + 26 * 3.2, by), (bx + 30 * 3.2, by + 26), (bx + 6 * 3.2, by + 26)], fill=(70, 70, 70))
dr.text((bx + 34 * 3.2, by + 4), 'key (helmet side) slides into the mount', fill=(60, 60, 60), font=Fnt(18))
dr.text((bx, by - 12.4 * k - 30), 'front medallion (eagle)', fill=(60, 60, 60), font=Fnt(18))
dr.text((bx + 64 * 3.2, by - 9.4 * k - 4), 'collar', fill=(60, 60, 60), font=Fnt(18))
dr.text((bx, by + 40), 'the collar edge tucks between the two medallions; snap pins pull it tight', fill=(60, 60, 60), font=Fnt(18))
# summary bar
dr.rectangle([40, 1585, W_ - 40, 1645], fill=(235, 233, 226))
dr.text((60, 1600), 'Per wing: 2 medallions + 2 collars + 9 feathers (+ 2 small tips) = 13-15 pieces  |  every piece fits 210 x 210  |  both faces coloured  |  key on the helmet-side medallion', fill=(40, 40, 40), font=Fnt(21))
img.save('pkg/step13_snap_collar_wing.jpg', quality=92)
for n in FE: print(LBL[n], 'tongue width ~%.0f mm' % (TONGUE[n].area / 14 if not TONGUE[n].is_empty else 0))
