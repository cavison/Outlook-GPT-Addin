src = open('wing2_build.py').read().split('# pegs and lightening holes in the hub')[0]
exec(src)
for c in ('CU', 'CL'):
    u_ = unary_union([REG[c], PLATE[c]])
    print(c, 'REG dist to disc', round(REG[c].distance(disc.exterior), 2))
    # radial profile: where between r 60 and 80 is there a gap?
    ring = disc.buffer(8).difference(disc.buffer(-8))
    gap = ring.intersection(PLATE[c].buffer(10)).difference(u_)
    gaps = [g for g in getattr(gap, 'geoms', [gap]) if g.area > 1]
    print('  gap pieces', [(round(g.area, 1), round(g.length, 1)) for g in gaps][:10])
    others = unary_union([REG[k] for k in REG if k != c])
    print('  other regions touching ring', round(others.intersection(ring).area, 1))
print(list(REG.keys()))
from PIL import Image, ImageDraw
def zoom(cx, cy, R, fn, layers, S=5.0):
    W = int(2 * R * S); im = Image.new('RGBA', (W, W), 'white')
    def P(c): return [((x - cx + R) * S, (cy + R - y) * S) for x, y in c]
    for g, col in layers:
        lay = Image.new('RGBA', (W, W), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        for q in getattr(g, 'geoms', [g]):
            if q.geom_type != 'Polygon': continue
            d.polygon(P(q.exterior.coords), fill=col, outline=(0, 0, 0, 255))
            for i in q.interiors: d.polygon(P(i.coords), fill=(255, 255, 255, 255), outline=(0, 0, 0, 255))
        im.alpha_composite(lay)
    d = ImageDraw.Draw(im)
    for x in range(int(cx - R) // 10 * 10, int(cx + R), 10):
        d.line(P([(x, cy - R), (x, cy + R)]), fill=(180, 180, 180)); d.text(P([(x, cy - R + 1)])[0], str(x), fill='gray')
    for y in range(int(cy - R) // 10 * 10, int(cy + R), 10):
        d.line(P([(cx - R, y), (cx + R, y)]), fill=(180, 180, 180)); d.text(P([(cx - R + 1, y)])[0], str(y), fill='gray')
    im.convert('RGB').save(fn)
lay = [(REG[k], (215, 215, 215, 255)) for k in REG if k not in ('CU', 'CL')]
lay += [(REG['CU'], (120, 150, 230, 200)), (REG['CL'], (230, 150, 120, 200)), (PLATE['CU'], (60, 60, 200, 90)), (PLATE['CL'], (200, 60, 60, 90))]
print('Cc', Cc)
zoom(Cc[0], Cc[1], 95, 'helmet/sheet/jz_hub.png', lay)
