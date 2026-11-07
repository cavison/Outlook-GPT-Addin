import re, sys, numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
exec(open('trace_band3.py').read().split("out = {}")[0])
B_ = load('e0a9281d-image.jpg'); pt, pb = rims(B_, 700, 862, 440, 620)
phis = np.linspace(14.0, 72.0, 1800); NT = 520
xcol = 687.5 + 183 * np.sin(np.radians(phis)); yt, yb = np.polyval(pt, xcol), np.polyval(pb, xcol)
ts = np.linspace(0, 1, NT); X = np.broadcast_to(xcol, (NT, len(phis))); Y = yt[None, :] + ts[:, None] * (yb - yt)[None, :]
photo = np.stack([ndimage.map_coordinates(B_[..., k], [Y, X], order=3) for k in range(3)], -1).clip(0, 255).astype(np.uint8)
def parse(fname, name):
    s = open(fname).read(); block = s.split(name + ' = [')[1].split('];')[0]
    return [np.array([[float(a) for a in q.split(',')] for q in re.findall(r'\[([-\d.]+,[-\d.]+)\]', p)])
            for p in re.findall(r'\[(\[[-\d.]+,[-\d.]+\](?:,\[[-\d.]+,[-\d.]+\])*)\]', block)]
s4 = open('helmet/band_motif4.scad').read()
dots = [[float(v) for v in q.split(',')] for q in re.findall(r'\[([-\d.]+,[-\d.]+,[-\d.]+)\]', s4.split('BAND_BACK_DOTS = [')[1].split('];')[0])]
W_, H_ = 1800, NT
def P(p): phi = 180.0 - p[0]; return ((phi - 14.0) / 58.0 * W_, p[1] * (H_ - 1))
acc = np.zeros((H_, W_), bool)
for poly in parse('helmet/band_motif4.scad', 'BAND_BACK_GOLD'):
    t_ = Image.new('L', (W_, H_), 0); ImageDraw.Draw(t_).polygon([P(p) for p in poly], fill=255); acc ^= np.asarray(t_) > 0
a = np.zeros((H_, W_, 3), np.uint8); a[:] = (40, 55, 110); a[acc] = (242, 193, 46)
im = Image.fromarray(a); d = ImageDraw.Draw(im)
for th, t, dia in dots:
    x, y = P((th, t)); r_mm = dia * 106.7 / 2; rx = r_mm / (np.pi / 180 * 107) / 58.0 * W_; ry = r_mm / 27.0 * (H_ - 1)
    d.ellipse((x - rx, y - ry, x + rx, y + ry), fill=(250, 250, 250))
FT = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 34)
c = Image.new('RGB', (W_, 2 * (NT + 60)), 'white'); dd = ImageDraw.Draw(c)
for i, (img, t) in enumerate(((Image.fromarray(photo), 'Back photo (band unrolled flat)'), (im, 'Clean redraw'))):
    dd.text((10, i * (NT + 60) + 8), t, font=FT, fill='#1B1F2A'); c.paste(img, (0, i * (NT + 60) + 55))
c.resize((1200, int(c.height * 1200 / W_))).save('ref2/scroll_back_cmp.png')
