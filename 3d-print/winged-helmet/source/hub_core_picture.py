# Hub core: each collar carries a wide hidden plate; the two plates half-lap into one disc between the medallions
import pickle, math, numpy as np
from shapely.geometry import Point, Polygon, LineString, box
from shapely.ops import unary_union
from shapely import affinity
from PIL import Image, ImageDraw, ImageFont
h = pickle.load(open('ref2/hub_regions.pkl', 'rb')); REG, MED, C, plate = h['REG'], h['MED'], h['C'], h['plate']
lc = pickle.load(open('ref2/layered_concept.pkl', 'rb')); V = lc['V']
C = np.array(C); R_CORE = 66.0; LAP = 16.0
cu, cl = REG['CU'].centroid, REG['CL'].centroid
axis = np.array([cu.x - cl.x, cu.y - cl.y]); axis /= np.linalg.norm(axis)        # from lower collar toward upper collar
perp = np.array([-axis[1], axis[0]])
core = Point(*C).buffer(R_CORE, 256)
def half(sign, extra):
    # half-plane on the given side of the line through the centre, pushed 'extra' mm across it
    p0 = C - axis * sign * extra
    big = Polygon([p0 + perp * 400, p0 - perp * 400, p0 - perp * 400 + axis * sign * 400, p0 + perp * 400 + axis * sign * 400])
    return core.intersection(big)
up_ext = half(+1, LAP / 2); lo_ext = half(-1, LAP / 2)
lap = up_ext.intersection(lo_ext)
# lightening holes (hidden inside the sandwich) and pins
holes = []
for k, a in enumerate(np.linspace(0, 2 * math.pi, 13)[:-1]):
    c = C + 36 * np.array([math.cos(a), math.sin(a)])
    hc = Point(*c).buffer(8, 32)
    if not hc.intersects(lap.buffer(4)): holes.append(hc)
holes = unary_union(holes)
pins = [C + 56 * np.array([math.cos(a), math.sin(a)]) for a in np.linspace(0, 2 * math.pi, 9)[:-1]]
pins += [C + perp * 25, C - perp * 25]                         # through the half-lap: lock the two collars together
COL = {'navy': (32, 44, 86), 'gold': (240, 190, 50), 'white': (238, 238, 230)}
def Fnt(sz, b=False): return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf' % ('-Bold' if b else ''), sz)
W_, H_ = 2700, 1500
img = Image.new('RGB', (W_, H_), (247, 246, 242)); dr = ImageDraw.Draw(img)
def fill(p, T, col, outline=None, width=2):
    for q in getattr(p, 'geoms', [p]):
        if q.geom_type != 'Polygon' or q.is_empty: continue
        ext = [T(x, y) for x, y in q.exterior.coords]; hs = [[T(x, y) for x, y in hh.coords] for hh in q.interiors]
        xs = [a for a, _ in ext]; ys = [b for _, b in ext]
        bx0, by0, bx1, by1 = max(int(min(xs)) - 2, 0), max(int(min(ys)) - 2, 0), min(int(max(xs)) + 3, W_), min(int(max(ys)) + 3, H_)
        if bx1 <= bx0 or by1 <= by0: continue
        m = Image.new('L', (bx1 - bx0, by1 - by0), 0); md = ImageDraw.Draw(m)
        md.polygon([(a - bx0, b - by0) for a, b in ext], fill=255)
        for hh in hs: md.polygon([(a - bx0, b - by0) for a, b in hh], fill=0)
        img.paste(Image.new('RGB', m.size, col), (bx0, by0), m)
        if outline:
            dr.line(ext + [ext[0]], fill=outline, width=width)
            for hh in hs: dr.line(hh + [hh[0]], fill=outline, width=width)
def art(region, T):
    fill(region, T, COL['navy'])
    for c in ('gold', 'white', 'navy'):
        g = V[c].intersection(region)
        if not g.is_empty: fill(g, T, COL[c])
# ---- left: the two collars with their hidden plates (medallions removed) ----
S = 4.1
bb = unary_union([REG['CU'], REG['CL'], core]).bounds
ox, oy = 90, 140
T = lambda x, y: (ox + (x - bb[0]) * S, oy + (bb[3] - y) * S)
dr.text((50, 30), 'Collars with their hidden plates (medallions taken off)', fill=(30, 30, 30), font=Fnt(32, True))
dr.text((50, 76), 'the two plates overlap in the middle and become one solid disc between the medallions', fill=(90, 90, 90), font=Fnt(22))
UPC, LOC = (95, 160, 215), (225, 120, 70)
art(REG['CU'], T); art(REG['CL'], T)
fill(up_ext.difference(holes), T, UPC, outline=(40, 40, 40))
fill(lo_ext.difference(holes).difference(lap), T, LOC, outline=(40, 40, 40))
fill(lap.difference(holes), T, (150, 120, 170), outline=(40, 40, 40))
for c in (REG['CU'], REG['CL']): dr.line([T(*q) for q in c.exterior.coords], fill=(40, 40, 40), width=2)
for p in pins:
    x, y = T(*p); dr.ellipse([x - 8, y - 8, x + 8, y + 8], fill=(60, 60, 60), outline='white')
dr.line([T(*c) for c in MED.exterior.coords], fill=(40, 150, 60), width=3)
tx, ty = T(*(C + axis * 44 + perp * 6)); dr.text((tx - 90, ty - 12), 'upper collar plate', fill='white', font=Fnt(21, True))
tx, ty = T(*(C - axis * 50 + perp * 6)); dr.text((tx - 90, ty - 12), 'lower collar plate', fill='white', font=Fnt(21, True))
ly = 1250
for col, t in ((UPC, 'hidden plate on the upper collar (same piece as the collar)'), (LOC, 'hidden plate on the lower collar (same piece as the collar)'),
               ((150, 120, 170), 'half-lap: the plates overlap here and pin together'), ((247, 246, 242), 'lightening holes - weight out, strength stays'),
               ((60, 60, 60), 'snap pins through medallion + plate + medallion')):
    dr.rectangle([60, ly, 90, ly + 24], fill=col, outline=(60, 60, 60)); dr.text((100, ly), t, fill=(50, 50, 50), font=Fnt(20)); ly += 34
dr.text((60, ly + 4), 'green circle = where the medallions cover it - none of the plate shows from either side', fill=(40, 120, 50), font=Fnt(20))
# ---- right: cut through the hub ----
rx = 1500
dr.text((rx, 150), 'Cut through the hub (edge view)', fill=(30, 30, 30), font=Fnt(28, True))
k = 10; sx = 3.6; bx, by = rx + 30, 470
def E(a, z0, b, z1, col): dr.rectangle([bx + a * sx, by - z1 * k, bx + b * sx, by - z0 * k], fill=col, outline=(60, 60, 60))
# back medallion 4 mm, collar plates 6.4 (upper on one side, lower on the other, half-lap in the middle), front medallion 3 mm
E(-70, 0, 70, 4.0, COL['navy'])
E(-70, 4.0, -8, 10.4, LOC); E(8, 4.0, 70, 10.4, UPC)
E(-8, 4.0, 8, 7.2, LOC); E(-8, 7.2, 8, 10.4, UPC)
E(-70, 10.4, 70, 13.4, COL['navy'])
E(70, 4.0, 160, 10.4, COL['gold']); E(-160, 4.0, -70, 10.4, COL['gold'])
for px in (-56, -25, 25, 56):
    dr.rectangle([bx + px * sx - 4, by - 13.4 * k, bx + px * sx + 4, by], fill=(110, 110, 110))
dr.polygon([(bx - 14 * sx, by), (bx + 14 * sx, by), (bx + 18 * sx, by + 34), (bx - 18 * sx, by + 34)], fill=(70, 70, 70))
dr.text((bx + 20 * sx, by + 8), 'key - on the helmet-side medallion', fill=(60, 60, 60), font=Fnt(18))
dr.text((bx - 66 * sx, by - 13.4 * k - 30), 'front medallion (eagle)', fill=(60, 60, 60), font=Fnt(18))
dr.text((bx + 72 * sx, by - 10.4 * k - 28), 'upper collar', fill=(60, 60, 60), font=Fnt(18))
dr.text((bx - 158 * sx, by - 10.4 * k - 28), 'lower collar', fill=(60, 60, 60), font=Fnt(18))
dr.text((bx - 10 * sx, by - 10.4 * k - 28), 'half-lap', fill=(60, 60, 60), font=Fnt(18))
notes = ['How the weight travels:',
         '  feather  ->  tongue in its collar socket  ->  collar',
         '  collar  ->  its wide plate, clamped over a 13 cm disc by both medallions',
         '  medallions  ->  key  ->  helmet mount',
         '',
         'Why it holds:',
         '  - the plate is clamped across its whole face, not just at a thin rim',
         '  - 8 pins around the edge + 2 through the half-lap lock the collars to each other',
         '  - the two collars brace each other through the half-lap',
         '  - the back medallion is 4 mm thick, carries the key, and is pinned to the plates',
         '',
         'Hub thickness about 13 mm; lightening holes keep the hidden plates light.']
for i, t in enumerate(notes): dr.text((rx, 700 + i * 34), t, fill=(50, 50, 50), font=Fnt(21, i in (0, 5)))
img.save('pkg/step14_hub_core.jpg', quality=92)
print('core plate area cm2', round(core.area / 100, 1), 'holes', round(holes.area / 100, 1))
