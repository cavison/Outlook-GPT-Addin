import json, re, os, numpy as np, pickle
report = []
def log(*a): print(*a)
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from PIL import Image, ImageDraw
src = open('wing_build.py').read()
exec(src[src.index('T, MID_T = '):src.index('# ---------- sections ----------')])
for n, g in WG.items(): print(f'{n:12s} area {g.area/100:7.1f} cm2  parts {len(getattr(g, "geoms", [g]))}  bounds {np.round(g.bounds, 0)}')
for n, g in LOGO.items(): print(f'{n:12s} area {g.area/100:7.1f} cm2  parts {len(getattr(g, "geoms", [g]))}')
# render target look (top view) and each level
COL = {'navy': (30, 42, 82), 'gold': (242, 193, 46), 'white': (236, 236, 228)}
x0, y0, x1, y1 = WG['WG_PLATE'].bounds; S = 2.2; pad = 10
W, H_ = int((x1 - x0 + 2 * pad) * S), int((y1 - y0 + 2 * pad) * S)
def draw(d, g, col, ox=0):
    for p in getattr(g, 'geoms', [g]):
        if p.is_empty or p.geom_type != 'Polygon': continue
        d.polygon([(ox + (x - x0 + pad) * S, (y1 - y + pad) * S) for x, y in p.exterior.coords], fill=col)
        for h in p.interiors: d.polygon([(ox + (x - x0 + pad) * S, (y1 - y + pad) * S) for x, y in h.coords], fill=(250, 250, 250))
img = Image.new('RGB', (W * 4, H_), (250, 250, 250)); d = ImageDraw.Draw(img)
# panel 0: current visible look (painter's order: plate, L1, L2, L3, medallion)
draw(d, WG['WG_PLATE'], COL['navy'])
for lvl in (('WG_L1_NAVY', 'navy'), ('WG_L1_GOLD', 'gold'), ('WG_L1_WHITE', 'white'), ('WG_L2_GOLD', 'gold'), ('WG_L2_WHITE', 'white'), ('WG_L3_NAVY', 'navy'), ('WG_L3_GOLD', 'gold')):
    draw(d, WG[lvl[0]], COL[lvl[1]])
draw(d, disc, COL['navy']); draw(d, ring, COL['gold']); draw(d, LOGO['LOGO_WHITE'], COL['white']); draw(d, LOGO['LOGO_GOLD'], COL['gold'])
# panels 1-3: each level alone, coloured, over a grey plate
for k, names in enumerate((('WG_L1_NAVY', 'WG_L1_GOLD', 'WG_L1_WHITE'), ('WG_L2_GOLD', 'WG_L2_WHITE'), ('WG_L3_NAVY', 'WG_L3_GOLD'))):
    ox = W * (k + 1); draw(d, WG['WG_PLATE'], (200, 200, 200), ox)
    for n in names: draw(d, WG[n], COL[n.split('_')[-1].lower()], ox)
img.save('ref2/wing_levels.png'); print(img.size)
