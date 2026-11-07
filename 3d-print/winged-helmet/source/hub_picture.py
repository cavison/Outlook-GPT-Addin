# Concept picture: hub-and-feather wing (two medallions clamp the collars, collars clamp the feathers)
import pickle, math, numpy as np
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union
from shapely import affinity
from PIL import Image, ImageDraw, ImageFont
hp = pickle.load(open('ref2/hub_pieces.pkl', 'rb'))
pieces, REG, MED, C, plate, RIM_IN = hp['pieces'], hp['REG'], hp['MED'], hp['C'], hp['plate'], hp['RIM_IN']
lc = pickle.load(open('ref2/layered_concept.pkl', 'rb')); V = lc['V']
# merge the two feathers that do not reach a collar into their neighbours
F = {'P1': pieces['P1'], 'P2': pieces['P2'], 'P3': pieces['P3'], 'P4': unary_union([pieces['P4'], pieces['P5']]).buffer(0.3).buffer(-0.3),
     'H1': pieces['H1'], 'H2': pieces['H2'], 'H3': pieces['H3'], 'H4': pieces['H4'], 'H5': unary_union([pieces['H5'], pieces['H6']]).buffer(0.3).buffer(-0.3)}
VIS = {'P4': unary_union([REG['P4'], REG['P5']]), 'H5': unary_union([REG['H5'], REG['H6']])}
COLL = {'CU': pieces['CU'], 'CL': pieces['CL']}
pickle.dump(dict(F=F, COLL=COLL, MED=MED, C=C, plate=plate), open('ref2/hub_final.pkl', 'wb'))
COL = {'navy': (32, 44, 86), 'gold': (240, 190, 50), 'white': (238, 238, 230)}
def shade(c, f): return tuple(int(v * f) for v in c)
def Fnt(sz, b=False): return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf' % ('-Bold' if b else ''), sz)
W_, H_ = 2900, 1620
img = Image.new('RGB', (W_, H_), (247, 246, 242)); dr = ImageDraw.Draw(img)
def fill(p, T, col, outline=None, width=2):
    for q in getattr(p, 'geoms', [p]):
        if q.geom_type != 'Polygon' or q.is_empty: continue
        ext = [T(x, y) for x, y in q.exterior.coords]; holes = [[T(x, y) for x, y in h.coords] for h in q.interiors]
        xs = [a for a, _ in ext]; ys = [b for _, b in ext]
        bx0, by0, bx1, by1 = max(int(min(xs)) - 2, 0), max(int(min(ys)) - 2, 0), min(int(max(xs)) + 3, W_), min(int(max(ys)) + 3, H_)
        if bx1 <= bx0 or by1 <= by0: continue
        m = Image.new('L', (bx1 - bx0, by1 - by0), 0); md = ImageDraw.Draw(m)
        md.polygon([(a - bx0, b - by0) for a, b in ext], fill=255)
        for h in holes: md.polygon([(a - bx0, b - by0) for a, b in h], fill=0)
        img.paste(Image.new('RGB', m.size, col), (bx0, by0), m)
        if outline: dr.line(ext + [ext[0]], fill=outline, width=width)
def art(region, T, dim=1.0):
    """the wing artwork clipped to a region"""
    fill(region, T, shade(COL['navy'], dim))
    for c in ('gold', 'white', 'navy'):
        g = V[c].intersection(region)
        if not g.is_empty: fill(g, T, shade(COL[c], dim))
x0, y0, x1, y1 = plate.bounds
# ---------------- panel A: front view with the pieces outlined ----------------
SA = 2.15; oxA, oyA = 50, 150
TA = lambda x, y: (oxA + (x - x0) * SA, oyA + (y1 - y) * SA)
dr.text((oxA, 30), 'One wing - front view', fill=(30, 30, 30), font=Fnt(32, True))
dr.text((oxA, 74), 'red lines = where the pieces meet; the back looks the same', fill=(90, 90, 90), font=Fnt(22))
art(plate, TA)
for n, g in list(F.items()):
    vis = VIS.get(n, REG[n])
    for q in getattr(vis, 'geoms', [vis]): dr.line([TA(*c) for c in q.exterior.coords], fill=(225, 40, 40), width=3)
for n in ('CU', 'CL'):
    for q in getattr(REG[n], 'geoms', [REG[n]]): dr.line([TA(*c) for c in q.exterior.coords], fill=(225, 40, 40), width=3)
dr.line([TA(*c) for c in MED.exterior.coords], fill=(225, 40, 40), width=3)
LBL = {'P1': 'F1', 'P2': 'F2', 'P3': 'F3', 'P4': 'F4', 'H1': 'F5', 'H2': 'F6', 'H3': 'F7', 'H4': 'F8', 'H5': 'F9'}
for n, g in F.items():
    p = VIS.get(n, REG[n]).representative_point(); tx, ty = TA(p.x, p.y)
    dr.rounded_rectangle([tx - 22, ty - 14, tx + 22, ty + 14], 6, fill=(225, 40, 40)); dr.text((tx - 15, ty - 12), LBL[n], fill='white', font=Fnt(20, True))
comps = pickle.load(open('ref2/feather_comps.pkl', 'rb'))
for n, txt, ids in (('CU', 'upper collar', [13, 11]), ('CL', 'lower collar', [17, 21])):
    p = unary_union([comps[i] for i in ids]).centroid; tx, ty = TA(p.x, p.y)
    dr.rounded_rectangle([tx - 70, ty - 14, tx + 70, ty + 14], 6, fill=(40, 120, 200)); dr.text((tx - 62, ty - 12), txt, fill='white', font=Fnt(19, True))
tx, ty = TA(*C); dr.rounded_rectangle([tx - 58, ty + 70, tx + 58, ty + 98], 6, fill=(40, 150, 60)); dr.text((tx - 50, ty + 72), 'medallion', fill='white', font=Fnt(19, True))
# ---------------- panel B: exploded stack ----------------
SB = 1.3; oxB, oyB = 860, 1500
def TB(z): return lambda x, y: (oxB + ((x - x0) + 0.30 * (y - y0)) * SB, oyB - (y - y0) * 0.50 * SB - z)
dr.text((1000, 30), 'How it goes together (exploded)', fill=(30, 30, 30), font=Fnt(32, True))
dr.text((1000, 74), 'helmet side at the bottom, show side on top', fill=(90, 90, 90), font=Fnt(22))
def slab(g, z, th, top_col=None, artwork=True, edge=(40, 40, 40)):
    fill(g, TB(z - th), (110, 110, 110))
    if artwork: art(g, TB(z))
    else: fill(g, TB(z), top_col)
    for q in getattr(g, 'geoms', [g]): dr.line([TB(z)(*c) for c in q.exterior.coords], fill=edge, width=2)
Z = {'bm': 0, 'bc': 190, 'f': 390, 'fc': 590, 'fm': 780}
medal_ring = MED
slab(MED, Z['bm'], 7)                                                  # back medallion (art faces the helmet... and has the key)
kx, ky = C[0] + 10, C[1] - 5
key = Polygon([(kx - 12, ky - 40), (kx + 12, ky - 40), (kx + 16, ky + 30), (kx - 16, ky + 30)])
fill(key, TB(Z['bm'] - 7), (70, 70, 70)); fill(key, TB(Z['bm'] - 30), (60, 60, 60))
for c in ('CU', 'CL'): slab(COLL[c], Z['bc'], 5)
for n, g in F.items():
    slab(g, Z['f'], 8)
    root = g.difference(VIS.get(n, REG[n]).buffer(0.2))
    if not root.is_empty: fill(root, TB(Z['f']), (150, 150, 165))            # hidden root (goes under the collars)
for c in ('CU', 'CL'): slab(COLL[c], Z['fc'], 5)
slab(MED, Z['fm'], 7)
# pins: 2 per feather root, 3 per collar under the medallion rim
pins = []
for n, g in F.items():
    root = g.difference(VIS.get(n, REG[n]).buffer(0.2))
    for q in sorted(getattr(root, 'geoms', [root]), key=lambda q: -q.area)[:1]:
        if q.area > 60: pins.append(q.representative_point())
for c in ('CU', 'CL'):
    rim = COLL[c].intersection(MED)
    if not rim.is_empty: pins.append(rim.representative_point())
for p in pins:
    a = TB(Z['bc'])(p.x, p.y); b = TB(Z['fm'] if MED.contains(p) else Z['fc'])(p.x, p.y)
    dr.line([a, b], fill=(160, 160, 160), width=2)
    for z in (Z['bc'], Z['f'], Z['fc']):
        q = TB(z)(p.x, p.y); dr.ellipse([q[0] - 5, q[1] - 4, q[0] + 5, q[1] + 4], fill=(90, 90, 90))
labels = [('fm', 'Front medallion  (eagle, show side)'), ('fc', 'Front collars  (upper + lower)'), ('f', '9 feathers  (coloured both sides)'),
          ('bc', 'Back collars  (upper + lower)'), ('bm', 'Back medallion  + KEY into the helmet mount')]
for k, t in labels:
    yy = oyB - Z[k] - 165
    dr.text((oxB + 650, yy), t, fill=(30, 30, 30), font=Fnt(22, True))
dr.text((oxB + 650, oyB - Z['f'] - 138), 'grey = hidden root that slides under the collars', fill=(90, 90, 90), font=Fnt(18))
dr.text((oxB + 650, oyB - Z['bc'] - 138), 'dots = pins that click through every layer', fill=(90, 90, 90), font=Fnt(18))
# ---------------- panel C: cross sections ----------------
cx, cy = 2120, 260
dr.text((cx, 30), 'Cut through the middle', fill=(30, 30, 30), font=Fnt(32, True))
dr.text((cx, 74), 'medallion to feather tip', fill=(90, 90, 90), font=Fnt(22))
sc = 3.2
def bar(a, b, z0, th, col, lbl=None):
    dr.rectangle([cx + a * sc, cy + 120 - (z0 + th) * 6, cx + b * sc, cy + 120 - z0 * 6], fill=col, outline=(60, 60, 60))
th_m, th_c, th_f = 3.0, 2.4, 4.4
z = 0
bar(0, 70, 0, th_m, COL['navy']); z1 = th_m
bar(0, 120, z1, th_c, COL['gold']); z2 = z1 + th_c
bar(20, 200, z2, th_f, COL['navy']); z3 = z2 + th_f
bar(0, 120, z3, th_c, COL['gold']); z4 = z3 + th_c
bar(0, 70, z4, th_m, COL['navy'])
for px in (60, 100):
    dr.rectangle([cx + px * sc - 3, cy + 120 - z4 * 6 - (th_m * 6 if px < 70 else 0), cx + px * sc + 3, cy + 120 - z1 * 6 + th_c * 0], fill=(110, 110, 110))
dr.text((cx + 150 * sc, cy + 120 - z3 * 6 - 34), 'feather', fill=(60, 60, 60), font=Fnt(18))
dr.text((cx, cy + 140), 'medallions  |  collars  |  feather root     pins lock it all', fill=(90, 90, 90), font=Fnt(18))
# feather skin section
fy = 560
dr.text((cx, fy - 70), 'Inside one feather', fill=(30, 30, 30), font=Fnt(28, True))
sw = 2.6
segs = [(0, 40, 'gold'), (40, 46, 'white'), (46, 110, 'gold'), (110, 170, 'navy')]
for z0, th, face in ((0, 1.0, 'bottom'), (3.4, 1.0, 'top')):
    for a, b, c in segs: dr.rectangle([cx + a * sw, fy + 120 - (z0 + th) * 22, cx + b * sw, fy + 120 - z0 * 22], fill=COL[c], outline=(80, 80, 80))
dr.rectangle([cx, fy + 120 - 3.4 * 22, cx + 170 * sw, fy + 120 - 1.0 * 22], fill=COL['navy'], outline=(80, 80, 80))
dr.text((cx + 175 * sw, fy + 120 - 4.4 * 22), 'colour skin (top face)', fill=(60, 60, 60), font=Fnt(18))
dr.text((cx + 175 * sw, fy + 120 - 2.6 * 22), 'solid navy core', fill=(60, 60, 60), font=Fnt(18))
dr.text((cx + 175 * sw, fy + 120 - 1.0 * 22), 'colour skin (bottom face)', fill=(60, 60, 60), font=Fnt(18))
dr.text((cx, fy + 140), 'every colour sits on solid plastic - nothing in mid-air', fill=(90, 90, 90), font=Fnt(18))
dr.text((cx, fy + 164), 'colour changes only in the thin skins (~1 mm each side)', fill=(90, 90, 90), font=Fnt(18))
# ---------------- panel D: piece list ----------------
ty = 930
dr.text((cx, ty), 'Pieces for one wing', fill=(30, 30, 30), font=Fnt(28, True))
rows = []
for n in ('P1', 'P2', 'P3', 'P4', 'H1', 'H2', 'H3', 'H4', 'H5'):
    g = F[n]; L = max(affinity.rotate(g, a, origin='centroid').bounds[2] - affinity.rotate(g, a, origin='centroid').bounds[0] for a in range(0, 180, 3))
    rows.append((LBL[n], L))
lines = ['feathers F1-F9: ' + ', '.join(f'{l} {L:.0f}' for l, L in rows[:5]) + ',',
         '   ' + ', '.join(f'{l} {L:.0f}' for l, L in rows[5:]) + ' mm long',
         'collars: upper x2, lower x2 (front + back), up to ~180 mm',
         'medallions: front + back (key), 140 mm across',
         '= 15 pieces per wing, every one fits 210 x 210',
         'longest feather ~176 mm - no feather needs splitting']
for k, t in enumerate(lines): dr.text((cx, ty + 44 + k * 30), t, fill=(50, 50, 50), font=Fnt(19))
dr.rectangle([40, 1550, W_ - 40, 1608], fill=(235, 233, 226))
dr.text((60, 1563), 'Both wings: 30 pieces  |  ~130 filament swaps (~3 h) instead of 345  |  about 0.35-0.4 kg per wing  |  all pieces snap to the medallions, key stays on the helmet-side medallion', fill=(40, 40, 40), font=Fnt(21))
img.save('pkg/step12_hub_feather_wing.jpg', quality=92)
print('saved')
