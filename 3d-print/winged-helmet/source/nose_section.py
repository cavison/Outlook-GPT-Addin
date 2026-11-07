# Side cross-section of the nose clip at x = X0 (through a snap bump), drawn from the real meshes.
import sys, numpy as np, trimesh
from shapely.geometry import Polygon
from shapely.ops import unary_union
from PIL import Image, ImageDraw, ImageFont
X0 = float(sys.argv[1]) if len(sys.argv) > 1 else 7.0
OUT = sys.argv[2] if len(sys.argv) > 2 else 'ref2/nose_section.png'
parts = [  # file, fill, outline
    ('helmet/out_v22/shell_nose.stl', (52, 70, 128), (20, 28, 60)),
    ('helmet/out_v22/bandL_white.stl', (245, 245, 238), (120, 120, 120)),
    ('helmet/out_v22/bandL_gold.stl', (232, 182, 40), (140, 100, 10)),
    ('helmet/out_v22/bandL_navy.stl', (30, 42, 82), (10, 14, 30)),
    ('helmet/out_v22/nose_body.stl', (242, 193, 46), (140, 100, 10)),
    ('helmet/out_v22/nose_panel.stl', (30, 42, 82), (10, 14, 30)),
    ('helmet/out_v22/nose_pin.stl', (245, 245, 238), (120, 120, 120)),
]
Y0, Y1, Z0, Z1, SC = -150.0, -118.0, -62.0, 32.0, 14.0   # window (mm) and pixels per mm
W, H = int((Y1 - Y0) * SC), int((Z1 - Z0) * SC)
img = Image.new('RGB', (W, H), 'white'); d = ImageDraw.Draw(img)
def px(y, z): return ((y - Y0) * SC, (Z1 - z) * SC)
for f, fill, line in parts:
    m = trimesh.load(f)
    sec = m.section(plane_origin=[X0, 0, 0], plane_normal=[1, 0, 0])
    if sec is None: continue
    loops = [Polygon(l[:, 1:3]) for l in sec.discrete if len(l) > 3]
    geo = None
    for p in loops:
        p = p.buffer(0)
        geo = p if geo is None else geo.symmetric_difference(p)
    if geo is None: continue
    for g in getattr(geo, 'geoms', [geo]):
        if g.is_empty: continue
        d.polygon([px(*c) for c in g.exterior.coords], fill=fill, outline=line)
        for h in g.interiors: d.polygon([px(*c) for c in h.coords], fill='white', outline=line)
img.save(OUT); print(img.size)
