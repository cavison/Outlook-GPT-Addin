# how deep / wide can each tongue's socket go and still keep >= WALL of collar around it?
src = open('wing2_build.py').read().split('JOINTS = {n: joint(n) for n in FE}')[0]
exec(src)
WALL = 1.5
def room(n):
    a = OUTL[n]; hb = HOST[n]
    b = (REG[hb] if hb in ('CU', 'CL') else OUTL[hb])
    shared = a.buffer(0.8).intersection(b.buffer(0.8))
    cs = np.array(shared.minimum_rotated_rectangle.exterior.coords)[:4]
    e1, e2 = cs[1] - cs[0], cs[2] - cs[1]
    edge = e1 if np.linalg.norm(e1) > np.linalg.norm(e2) else e2
    L = np.linalg.norm(edge); u = edge / L; nr = np.array([-u[1], u[0]])
    mid = np.array([shared.centroid.x, shared.centroid.y])
    if b.distance(Point(*(mid + 6 * nr))) > b.distance(Point(*(mid - 6 * nr))): nr = -nr
    def rect(x0, x1, y0, y1):
        return Polygon([mid + u * x0 + nr * y0, mid + u * x1 + nr * y0, mid + u * x1 + nr * y1, mid + u * x0 + nr * y1])
    if hb in ('CU', 'CL'):
        ok = OUTL[hb].buffer(-WALL)
        bad = unary_union([Point(*q).buffer(PEG_D / 2 + 0.15 + WALL) for q in PEGS] + [LIGHT.buffer(WALL), LAPZ.buffer(WALL)])
        ok = ok.difference(bad)
    else:
        ok = OUTL[hb].buffer(-1.2)
    res = []
    for dep in (30, 26, 22, 19, 16, 13):
        best = None
        for wf in (0.9, 0.8, 0.7, 0.6, 0.5, 0.4):
            w = float(np.clip(wf * L, 12.0, 40.0))
            deep = rect(-w / 2 - 0.2 - BUMP - 0.4, w / 2 + 0.2 + BUMP + 0.4, 2.0, dep + 0.6)
            if deep.difference(ok).area < 0.5:
                best = round(w, 1); break
        res.append((dep, best))
    return L, res
for n in FE:
    L, res = room(n)
    print(f'{n:3s} host {HOST[n]:3s} edge {L:5.1f}  ' + '  '.join(f'd{d}:{w}' for d, w in res))

from PIL import Image, ImageDraw
allg = unary_union([OUTL[k] for k in OUTL])
x0, y0, x1, y1 = allg.bounds; S = 4.0
W, H = int((x1 - x0) * S) + 40, int((y1 - y0) * S) + 40
im = Image.new('RGBA', (W, H), 'white')
def P(c): return [((x - x0) * S + 20, (y1 - y) * S + 20) for x, y in c]
def draw(g, col):
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for q in getattr(g, 'geoms', [g]):
        if q.geom_type != 'Polygon': continue
        d.polygon(P(q.exterior.coords), fill=col, outline=(0, 0, 0, 255))
        for i in q.interiors: d.polygon(P(i.coords), fill=(255, 255, 255, 255), outline=(0, 0, 0, 255))
    im.alpha_composite(lay)
for k in ('CU', 'CL'):
    draw(OUTL[k], (159, 179, 224, 255) if k == 'CU' else (224, 179, 159, 255))
    ok = OUTL[k].buffer(-WALL).difference(unary_union([Point(*q).buffer(PEG_D / 2 + 0.15 + WALL) for q in PEGS] + [LIGHT.buffer(WALL), LAPZ.buffer(WALL)]))
    draw(ok, (42, 157, 58, 110))
for n in FE: draw(OUTL[n], (220, 220, 220, 255))
for n in FE:
    t, s_, info = joint(n); draw(s_, (230, 0, 0, 150))
d = ImageDraw.Draw(im)
for n in FE:
    c = OUTL[n].centroid; d.text(P([(c.x, c.y)])[0], n, fill='black')
im.convert('RGB').save('helmet/sheet/joint_room.png')
