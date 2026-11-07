import sys
src = open('wing2_build.py').read().split('def place_all(order):')[0]
src = src.replace("    assert best is not None, n\n", "    if best is None: return None\n")
exec(src)
JOINTS = {}; TAKEN.clear()
ORDER = sorted(FE, key=lambda n: (HOST[n] in FE, n))
for n in ORDER:
    j = joint(n)
    if j: JOINTS[n] = j; print(n, j[2])
    else: print(n, 'FAILED')
from PIL import Image, ImageDraw
def zoom(cx, cy, R, fn, focus):
    S = 8.0; W = int(2 * R * S)
    im = Image.new('RGBA', (W, W), 'white')
    def P(c): return [((x - cx + R) * S, (cy + R - y) * S) for x, y in c]
    def draw(g, col):
        lay = Image.new('RGBA', (W, W), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        for q in getattr(g, 'geoms', [g]):
            if q.geom_type != 'Polygon': continue
            d.polygon(P(q.exterior.coords), fill=col, outline=(0, 0, 0, 255))
            for i in q.interiors: d.polygon(P(i.coords), fill=(255, 255, 255, 255), outline=(0, 0, 0, 255))
        im.alpha_composite(lay)
    for k in ('CU', 'CL'): draw(OUTL[k], (159, 179, 224, 255) if k == 'CU' else (224, 179, 159, 255))
    draw(host_room(focus), (42, 157, 58, 110))
    for k in FE: draw(OUTL[k], (215, 215, 215, 255))
    for k, j in JOINTS.items(): draw(j[1], (230, 0, 0, 120))
    d = ImageDraw.Draw(im)
    for k in FE:
        c = OUTL[k].centroid; d.text(P([(c.x, c.y)])[0], k, fill='black')
    for x in range(int(cx - R) // 10 * 10, int(cx + R), 10):
        d.line(P([(x, cy - R), (x, cy + R)]), fill=(180, 180, 180)); d.text(P([(x, cy - R + 1)])[0], str(x), fill='gray')
    for y in range(int(cy - R) // 10 * 10, int(cy + R), 10):
        d.line(P([(cx - R, y), (cx + R, y)]), fill=(180, 180, 180)); d.text(P([(cx - R + 1, y)])[0], str(y), fill='gray')
    im.convert('RGB').save(fn)
f = sys.argv[1]
if f in FE:
    c = OUTL[HOST[f]].intersection(OUTL[f].buffer(2)).centroid; zoom(c.x, c.y, 25, f'helmet/sheet/jz_{f}.png', f)
else:
    zoom(float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), f'helmet/sheet/jz_{f}.png', sys.argv[5])
