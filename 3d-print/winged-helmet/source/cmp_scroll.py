"""Photo band (unrolled) vs traced scrollwork, front, left part. usage: cmp_scroll.py out.png [x0 x1]"""
import re, sys, numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
exec(open('trace_band3.py').read().split("out = {}")[0])
F_ = load('fdb87b20-image.jpg'); pt, pb = rims(F_, 742, 868, 385, 530)
phis = np.linspace(9.6, 70.0, 1800); NT = 520
xcol = 689 + 188 * np.sin(np.radians(phis)); yt, yb = np.polyval(pt, xcol), np.polyval(pb, xcol)
ts = np.linspace(0, 1, NT); X = np.broadcast_to(xcol, (NT, len(phis))); Y = yt[None, :] + ts[:, None] * (yb - yt)[None, :]
photo = np.stack([ndimage.map_coordinates(F_[..., k], [Y, X], order=3) for k in range(3)], -1).clip(0, 255).astype(np.uint8)
def parse(fname, name):
    s = open(fname).read(); block = s.split(name + ' = [')[1].split('];')[0]
    return [np.array([[float(a) for a in q.split(',')] for q in re.findall(r'\[([-\d.]+,[-\d.]+)\]', p)])
            for p in re.findall(r'\[(\[[-\d.]+,[-\d.]+\](?:,\[[-\d.]+,[-\d.]+\])*)\]', block)]
def render(sets, dots_=()):
    W_, H_ = 1800, NT
    def P(p): return ((p[0] - 9.6) / (70 - 9.6) * W_, p[1] * (H_ - 1))
    acc = np.zeros((H_, W_), bool)
    for poly in sets:
        t_ = Image.new('L', (W_, H_), 0); ImageDraw.Draw(t_).polygon([P(p) for p in poly], fill=255); acc ^= np.asarray(t_) > 0
    a = np.zeros((H_, W_, 3), np.uint8); a[:] = (40, 55, 110); a[acc] = (242, 193, 46)
    im = Image.fromarray(a); d = ImageDraw.Draw(im)
    for th, t, dia in dots_:
        x, y = P((th, t)); r_mm = dia * 106.7 / 2
        rx = r_mm / (np.pi / 180 * 107) / (70 - 9.6) * W_; ry = r_mm / 27.0 * (H_ - 1)
        d.ellipse((x - rx, y - ry, x + rx, y + ry), fill=(250, 250, 250))
    return im
MOTIF = sys.argv[4] if len(sys.argv) > 4 else 'helmet/band_motif3.scad'
s3 = open(MOTIF).read()
dots3 = [[float(v) for v in q.split(',')] for q in re.findall(r'\[([-\d.]+,[-\d.]+,[-\d.]+)\]', s3.split('BAND_FRONT_DOTS = [')[1].split('];')[0])]
new = render(parse(MOTIF, 'BAND_FRONT_GOLD'), dots3)
x0, x1 = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (0, 1100)
FT = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 34)
tiles = [(Image.fromarray(photo), 'Your photo (band unrolled flat)'), (new, 'Cleaned trace')]
c = Image.new('RGB', (x1 - x0, 2 * (NT + 60)), 'white'); d = ImageDraw.Draw(c)
for i, (im, t) in enumerate(tiles):
    d.text((10, i * (NT + 60) + 8), t, font=FT, fill='#1B1F2A'); c.paste(im.crop((x0, 0, x1, NT)), (0, i * (NT + 60) + 55))
c.save(sys.argv[1])
