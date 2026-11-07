src = open('wing2_build.py').read().split('JOINTS = {}\nORDER')[0]
exec(src)
JOINTS = {}
n = 'F4'; hb = HOST[n]; a = OUTL[n]
ok = host_room(n); near, cover = a.buffer(3.5), unary_union([a.buffer(0.6), OUTL[hb]])
line = a.exterior.intersection(OUTL[hb].buffer(1.0))
print('line', line.geom_type, round(line.length, 1), [ (g.geom_type, round(g.length,1)) for g in getattr(line, 'geoms', [line])])
print('dist F4-CU', a.distance(OUTL[hb]), 'F4-REG', a.distance(REG[hb]))
segs = [g for g in getattr(line, 'geoms', [line]) if g.geom_type == 'LineString' and g.length > 2]
res = []
for g in segs:
    for d in np.arange(1.5, g.length - 1.4, 3.0):
        p0, p1 = g.interpolate(d - 1.0), g.interpolate(d + 1.0)
        t = np.array([p1.x - p0.x, p1.y - p0.y]); t /= np.linalg.norm(t) + 1e-9
        m = np.array([g.interpolate(d).x, g.interpolate(d).y]); nn = np.array([-t[1], t[0]])
        if a.contains(Point(*(m + 2 * nn))): nn = -nn
        for da in np.radians(np.arange(-40, 41, 10)):
            c_, s_ = math.cos(da), math.sin(da)
            nr = np.array([c_ * nn[0] - s_ * nn[1], s_ * nn[0] + c_ * nn[1]]); u = np.array([nr[1], -nr[0]])
            t_, sk, root, _ = joint_shape(m, u, nr, 10.0, 16.0)
            c1 = sk.difference(cover).area; c2 = sk.difference(near).difference(ok).area; c3 = root.difference(a.buffer(0.6)).area / root.area
            res.append((c1 + c2 + 50 * c3, round(c1, 1), round(c2, 1), round(c3, 2), m.round(1), round(math.degrees(da))))
res.sort(key=lambda r: r[0])
for r in res[:8]: print(r)
from PIL import Image, ImageDraw
def zoom(cx, cy, R, fn, extra=()):
    S = 12.0; W = int(2 * R * S)
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
    draw(ok, (42, 157, 58, 110))
    for k in FE: draw(OUTL[k], (215, 215, 215, 255))
    for g, col in extra: draw(g, col)
    d = ImageDraw.Draw(im)
    for k in FE:
        c = OUTL[k].centroid; d.text(P([(c.x, c.y)])[0], k, fill='black')
    for x in range(int(cx - R), int(cx + R), 10):
        d.line(P([(x, cy - R), (x, cy + R)]), fill=(200, 200, 200)); d.text(P([(x, cy - R + 1)])[0], str(x), fill='gray')
    for y in range(int(cy - R), int(cy + R), 10):
        d.line(P([(cx - R, y), (cx + R, y)]), fill=(200, 200, 200)); d.text(P([(cx - R + 1, y)])[0], str(y), fill='gray')
    im.convert('RGB').save(fn)
zoom(84, 42, 30, 'helmet/sheet/jz_F4.png')
