# Concept picture: one wing built from single-colour layers that peg and glue together
import pickle, math, numpy as np
from shapely.ops import unary_union
from shapely.geometry import Point, Polygon
from shapely import affinity
from PIL import Image, ImageDraw, ImageFont
exec(open('layered_pieces.py').read().split("layers = {}")[0])
C = d['MED_C']; R = d['MED_R']
med = Point(*C).buffer(R + 0.5, 128)
LOGO = d['LOGO']
# ---- the pieces ----
def clean(pcs, a=150): return [p for p in pcs if p.area > a]
base = clean([p for r in regions((0, 0)) for p in parts(WHITE_BASE.intersection(r).buffer(0))])
gold = clean([p for r in regions((0, 0)) for p in parts(GOLD.difference(med).intersection(r).buffer(0))])
navy = clean([p for r in regions((0, 0)) for p in parts(NAVY.difference(med).intersection(r).buffer(0))])
# medallion badge: navy disc with the 12 cells standing up, gold ring frame over it, white eagle, gold eagle accents
badge_navy = Point(*C).buffer(R, 128)
cells = NAVY.intersection(Point(*C).buffer(R + 0.5, 128)).difference(Point(*C).buffer(R - 9, 128))
ring_gold = Point(*C).buffer(R, 128).difference(Point(*C).buffer(R - 3.5 - 9, 128)).difference(cells.buffer(0.3))
eagle_w = LOGO['LOGO_WHITE'].union(LOGO['LOGO_GOLD']).buffer(0.8)
eagle_g = LOGO['LOGO_GOLD']
badge = [('navy', badge_navy), ('gold', ring_gold), ('white', eagle_w), ('gold', eagle_g)]
small_gold = [p for p in gold if p.area < 2000]; big_gold = [p for p in gold if p.area >= 2000]
small_navy = [p for p in navy if p.area < 2000]; big_navy = [p for p in navy if p.area >= 2000]
print('base', len(base), 'gold', len(big_gold), '+', len(small_gold), 'navy', len(big_navy), '+', len(small_navy), 'badge', len(badge))
TH = {'white': 3.0, 'gold': 1.6, 'navy': 1.6}
vol = sum(p.area for p in base) * 3.0 + sum(p.area for p in gold) * 1.6 + sum(p.area for p in navy) * 1.6 + badge_navy.area * 1.6 + ring_gold.area * 1.6 + eagle_w.area * 1.6 + eagle_g.area * 1.0
print('volume cm3', vol / 1000)
pickle.dump(dict(base=base, gold=gold, navy=navy, badge=badge, vol=vol), open('ref2/layered_concept_pieces.pkl', 'wb'))
# ---- drawing ----
COL = {'navy': (32, 44, 86), 'gold': (240, 190, 50), 'white': (238, 238, 230)}
def shade(c, f): return tuple(int(v * f) for v in c)
def F(sz, b=False):
    return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf' % ('-Bold' if b else ''), sz)
W_, H_ = 2600, 1500
img = Image.new('RGB', (W_, H_), (247, 246, 242)); dr = ImageDraw.Draw(img)
x0, y0, x1, y1 = plate.bounds
def poly_pts(p, T):
    return [T(x, y) for x, y in p.exterior.coords], [[T(x, y) for x, y in h.coords] for h in p.interiors]
def fill(p, T, col, outline=None, hole_col=None, width=1):
    """filled polygon with real (see-through) holes"""
    for q in getattr(p, 'geoms', [p]):
        if q.geom_type != 'Polygon' or q.is_empty: continue
        ext, holes = poly_pts(q, T)
        xs = [a for a, _ in ext]; ys = [b for _, b in ext]
        bx0, by0 = int(min(xs)) - 2, int(min(ys)) - 2; bx1, by1 = int(max(xs)) + 3, int(max(ys)) + 3
        bx0, by0 = max(bx0, 0), max(by0, 0); bx1, by1 = min(bx1, W_), min(by1, H_)
        if bx1 <= bx0 or by1 <= by0: continue
        m = Image.new('L', (bx1 - bx0, by1 - by0), 0); md = ImageDraw.Draw(m)
        md.polygon([(a - bx0, b - by0) for a, b in ext], fill=255)
        for h in holes: md.polygon([(a - bx0, b - by0) for a, b in h], fill=0)
        img.paste(Image.new('RGB', m.size, col), (bx0, by0), m)
        if outline:
            dr.line(ext + [ext[0]], fill=outline, width=width)
            for h in holes: dr.line(h + [h[0]], fill=outline, width=1)
# --- panel 1: finished wing, top view with a little relief shadow ---
S1 = 1.55; ox1, oy1 = 60, 150
T1 = lambda x, y: (ox1 + (x - x0) * S1, oy1 + (y1 - y) * S1)
T1s = lambda dx, dy: (lambda x, y: (ox1 + (x - x0) * S1 + dx, oy1 + (y1 - y) * S1 + dy))
dr.text((ox1, 40), 'What it looks like (one wing, show side)', fill=(30, 30, 30), font=F(34, True))
dr.text((ox1, 88), 'navy frame on top, gold under it, white base at the bottom', fill=(90, 90, 90), font=F(24))
for p in base: fill(p, T1, COL['white'])
for layer, pcs in (('gold', gold), ('navy', navy)):
    for p in pcs: fill(p, T1s(3, 3), (150, 150, 140))
    for p in pcs: fill(p, T1, COL[layer])
for c, p in badge:
    fill(p, T1s(3, 3), (120, 120, 110)); fill(p, T1, COL[c])
dr.line([T1(x0, y0 - 8), T1(x1, y0 - 8)], fill=(120, 120, 120), width=2)
dr.text((T1((x0 + x1) / 2 - 25, y0 - 12)), f'{x1 - x0:.0f} mm', fill=(90, 90, 90), font=F(20))
# --- panel 2: exploded stack, tilted view ---
S2 = 1.38; ox2, oy2 = 880, 1340
def T2(z):
    return lambda x, y: (ox2 + ((x - x0) + 0.28 * (y - y0)) * S2, oy2 - ((y - y0) * 0.50) * S2 - z)
dr.text((900, 40), 'How it comes apart (exploded)', fill=(30, 30, 30), font=F(34, True))
def slab(pcs, z, col, th_px, edge=(60, 60, 60), mark_pieces=True):
    for p in pcs: fill(p, T2(z - th_px), shade(col, 0.62))
    order = sorted(range(len(pcs)), key=lambda i: -pcs[i].area)
    for k, i in enumerate(order): fill(pcs[i], T2(z), col if k % 2 == 0 else shade(col, 0.88), outline=edge if mark_pieces else None, width=2)
LIFT = {'white': 0, 'gold': 290, 'navy': 580}
slab(base, LIFT['white'], COL['white'], 9, edge=(40, 40, 40))
slab(gold, LIFT['gold'], COL['gold'], 6, edge=(150, 110, 20))
slab(navy, LIFT['navy'], COL['navy'], 6, edge=(150, 160, 200))
# pegs: a few hidden spots under the navy frame (shown on the base and as holes in the gold)
pegs = []
for p in base:
    cand = p.intersection(NAVY.buffer(-2.5)).difference(med)
    pts = [q.representative_point() for q in parts(cand, 30)]
    pts.sort(key=lambda q: -cand.area); pegs += pts[:3]
for q in pegs:
    bx, by = T2(LIFT['white'])(q.x, q.y); gx, gy = T2(LIFT['gold'])(q.x, q.y)
    dr.line([(bx, by), (gx, gy)], fill=(170, 170, 170), width=1)
    dr.ellipse([bx - 5, by - 4, bx + 5, by + 4], fill=(120, 120, 120))
    dr.ellipse([gx - 5, gy - 4, gx + 5, gy + 4], fill=(110, 80, 10))
# badge floating to the right of the navy layer
bc = C; S3 = 1.6
def T3(z, ox=2120, oy=420):
    return lambda x, y: (ox + (x - bc[0]) * S3 + 0.55 * (y - bc[1]) * S3 * 0.0, oy - (y - bc[1]) * 0.55 * S3 - z)
zz = 0
for c, p in badge:
    fill(p, T3(zz - 6), shade(COL[c], 0.6)); fill(p, T3(zz), COL[c], outline=(60, 60, 60))
    zz += 70
dr.text((1990, 120), 'Eagle medallion badge', fill=(30, 30, 30), font=F(26, True))
dr.text((1990, 154), 'built on its own, glued on last', fill=(90, 90, 90), font=F(20))
for k, (t) in enumerate(('navy disc', 'gold ring frame', 'white eagle', 'gold eagle accents')):
    dr.text((2290, 412 - k * 70 - 6), t, fill=(60, 60, 60), font=F(18))
# layer labels
lab = [('navy', 'NAVY FRAME  1.6 mm', f'{len(big_navy)} large + {len(small_navy)} small pieces'),
       ('gold', 'GOLD LAYER  1.6 mm', f'{len(big_gold)} sheets + {len(small_gold)} small feathers'),
       ('white', 'WHITE BASE  3 mm', f'{len(base)} sections (the structure), shaded apart')]
for c, t1, t2 in lab:
    yy = oy2 - LIFT[c] - 250
    dr.rectangle([1990, yy, 2020, yy + 30], fill=COL[c], outline=(60, 60, 60))
    dr.text((2035, yy - 2), t1, fill=(30, 30, 30), font=F(24, True))
    dr.text((2035, yy + 30), t2, fill=(80, 80, 80), font=F(20))
dr.text((1990, oy2 - 170), 'grey dots = alignment pegs in spots', fill=(80, 80, 80), font=F(18))
dr.text((1990, oy2 - 146), 'hidden under the navy frame', fill=(80, 80, 80), font=F(18))
# --- cross-section sketch ---
cx, cy = 60, 1330
dr.text((cx, cy - 130), 'Side cut through one feather', fill=(30, 30, 30), font=F(26, True))
sc = 9
def bar(xa, xb, z0, th, col): dr.rectangle([cx + xa * sc, cy - (z0 + th) * sc, cx + xb * sc, cy - z0 * sc], fill=col, outline=(70, 70, 70))
bar(0, 75, 0, 3.0, COL['white'])
bar(0, 30, 3.0, 1.6, COL['gold']); bar(36, 75, 3.0, 1.6, COL['gold'])      # gap = white quill line showing through
bar(0, 8, 4.6, 1.6, COL['navy']); bar(56, 75, 4.6, 1.6, COL['navy'])
dr.rectangle([cx + 62 * sc, cy - 4.6 * sc, cx + 63.5 * sc, cy - 3.0 * sc], fill=(120, 120, 120))   # peg
dr.text((cx + 22 * sc, cy - 9.5 * sc), 'white shows through the gap', fill=(80, 80, 80), font=F(16))
dr.text((cx + 77 * sc, cy - 4.5 * sc), 'about 6 mm', fill=(80, 80, 80), font=F(18))
dr.text((cx, cy + 14), 'glued; small pegs line the layers up', fill=(80, 80, 80), font=F(18))
dr.text((900, 88), 'each colour is its own flat piece - no colour changes while printing', fill=(90, 90, 90), font=F(24))
n_tot = len(base) + len(gold) + len(navy) + len(badge)
dr.rectangle([60, 1415, 2540, 1480], fill=(235, 233, 226))
dr.text((80, 1428), f'One wing: about {n_tot} single-colour pieces  |  about {vol / 1000 * 1.24 / 1000 * 0.95:.1f} kg  |  0 filament swaps  |  every piece prints flat, nothing in mid-air  |  back of the wing = plain white base', fill=(40, 40, 40), font=F(24))
img.save('pkg/step11_layered_wing_concept.jpg', quality=92)
print('saved')
