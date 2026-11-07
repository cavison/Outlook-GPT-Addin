"""Scrollwork sheet: your photo / before (gritty) / now (clean), flat; then the new band in 3D."""
import re, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageChops
from scipy import ndimage
exec(open('trace_band3.py').read().split("out = {}")[0])
F_ = load('fdb87b20-image.jpg'); pt, pb = rims(F_, 742, 868, 385, 530)
phis = np.linspace(9.6, 70.0, 1800); NT = 520
xcol = 689 + 188 * np.sin(np.radians(phis)); yt, yb = np.polyval(pt, xcol), np.polyval(pb, xcol)
ts = np.linspace(0, 1, NT); X = np.broadcast_to(xcol, (NT, len(phis))); Y = yt[None, :] + ts[:, None] * (yb - yt)[None, :]
photo = Image.fromarray(np.stack([ndimage.map_coordinates(F_[..., k], [Y, X], order=3) for k in range(3)], -1).clip(0, 255).astype(np.uint8))
def parse(fname, name):
    s = open(fname).read(); block = s.split(name + ' = [')[1].split('];')[0]
    return [np.array([[float(a) for a in q.split(',')] for q in re.findall(r'\[([-\d.]+,[-\d.]+)\]', p)])
            for p in re.findall(r'\[(\[[-\d.]+,[-\d.]+\](?:,\[[-\d.]+,[-\d.]+\])*)\]', block)]
def render(gold_sets, white_sets=(), dots_=()):
    W_, H_ = 1800, NT
    def P(p): return ((p[0] - 9.6) / (70 - 9.6) * W_, p[1] * (H_ - 1))
    def fill(sets):
        acc = np.zeros((H_, W_), bool)
        for poly in sets:
            t_ = Image.new('L', (W_, H_), 0); ImageDraw.Draw(t_).polygon([P(p) for p in poly], fill=255); acc ^= np.asarray(t_) > 0
        return acc
    a = np.zeros((H_, W_, 3), np.uint8); a[:] = (40, 55, 110); a[fill(gold_sets)] = (242, 193, 46)
    if white_sets: a[fill(white_sets)] = (250, 250, 250)
    im = Image.fromarray(a); d = ImageDraw.Draw(im)
    for th, t, dia in dots_:
        x, y = P((th, t)); r_mm = dia * 106.7 / 2
        rx = r_mm / (np.pi / 180 * 107) / (70 - 9.6) * W_; ry = r_mm / 27.0 * (H_ - 1)
        d.ellipse((x - rx, y - ry, x + rx, y + ry), fill=(250, 250, 250))
    return im
before = render(parse('helmet/band_motif2.scad', 'BAND_FRONT_GOLD'), parse('helmet/band_motif2.scad', 'BAND_FRONT_WHITE'))
s4 = open('helmet/band_motif4.scad').read()
d4 = [[float(v) for v in q.split(',')] for q in re.findall(r'\[([-\d.]+,[-\d.]+,[-\d.]+)\]', s4.split('BAND_FRONT_DOTS = [')[1].split('];')[0])]
now = render(parse('helmet/band_motif4.scad', 'BAND_FRONT_GOLD'), dots_=d4)
F = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 28)
FS = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 21)
TW = 1100; th_ = int(NT * TW / 1800)
tiles = [(photo, 'Your photo (one side of the front band, unrolled flat)'), (before, 'Before: traced from the photo pixels (gritty)'),
         (now, 'Now: redrawn as smooth, even gold lines with sharp tips')]
def trim(path, pad=6):
    im = Image.open(path).convert('RGB'); bb = ImageChops.difference(im, Image.new('RGB', im.size, im.getpixel((0, 0)))).getbbox()
    im = im.crop(bb); o = Image.new('RGB', (im.width + 2 * pad, im.height + 2 * pad), 'white'); o.paste(im, (pad, pad)); return o
r3a = Image.open('helmet/sheet/b12_front_o.png').convert('RGB'); a = np.asarray(r3a).astype(int)
gold = (a[..., 0] > 150) & (a[..., 0] - a[..., 2] > 60); ys, xs = np.nonzero(gold); cx = (xs.min() + xs.max()) / 2
r3a = r3a.crop((int(cx) - 395, ys.min() - 75, int(cx) + 395, ys.max() + 20))
r3b = trim('helmet/sheet/b12_back.png')
H3 = 400
r3a = r3a.resize((int(r3a.width * H3 / r3a.height), H3), Image.LANCZOS); r3b = r3b.resize((int(r3b.width * H3 / r3b.height), H3), Image.LANCZOS)
H = 3 * (th_ + 50) + 50 + H3 + 50
c = Image.new('RGB', (max(TW, r3a.width + r3b.width + 30) + 40, H), 'white'); d = ImageDraw.Draw(c)
y = 10
for im, t in tiles:
    d.text((20, y), t, font=F, fill='#1B1F2A'); c.paste(im.resize((TW, th_), Image.LANCZOS), (20, y + 40)); y += th_ + 50
d.text((20, y), 'Now, on the helmet (front and back)', font=F, fill='#1B1F2A')
c.paste(r3a, (20, y + 40)); c.paste(r3b, (20 + r3a.width + 30, y + 40))
c.save('pkg/step2b_scroll_clean.jpg', quality=92); print(c.size)
