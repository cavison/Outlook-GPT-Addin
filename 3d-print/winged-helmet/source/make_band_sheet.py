"""Brow band step sheet: your photo | design, front close-up and four views."""
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont
U = '/root/.claude/uploads/319431bf-dd7d-5dd8-8f43-98ef81b3e188/'
F = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 28)
FS = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 21)
INK, MUT = "#1B1F2A", "#4A5160"
def trim(path, pad=8):
    im = Image.open(path).convert("RGB")
    a = np.asarray(im).astype(int); m = ((a.max(2) - a.min(2)) <= 3) & (a.min(2) >= 240)
    b = np.array(im); b[m] = 255; im = Image.fromarray(b)
    bb = ImageChops.difference(im, Image.new("RGB", im.size, (255, 255, 255))).getbbox(); im = im.crop(bb)
    o = Image.new("RGB", (im.width + 2 * pad, im.height + 2 * pad), (255, 255, 255)); o.paste(im, (pad, pad)); return o
def fit(im, h): return im.resize((int(im.width * h / im.height), h), Image.LANCZOS)
# close-up: photo band vs render band (front)
ph = fit(Image.open(U + 'fdb87b20-image.jpg').convert('RGB').crop((495, 380, 885, 575)), 300)
r = Image.open('helmet/sheet/b11_front_o.png').convert('RGB'); a = np.asarray(r).astype(int)
gold = (a[..., 0] > 150) & (a[..., 0] - a[..., 2] > 60); ys, xs = np.nonzero(gold); cx = (xs.min() + xs.max()) / 2
rz = fit(r.crop((int(cx) - 395, ys.min() - 75, int(cx) + 395, ys.max() + 20)), 300)
pairs = []
for n, f, crop in (('front', 'fdb87b20', (470, 190, 910, 720)), ('q34', '9821a39f', (440, 190, 900, 730)),
                   ('side', 'd47111e3', (420, 200, 920, 710)), ('back', 'e0a9281d', (470, 190, 900, 690))):
    p_ = fit(Image.open(U + f + '-image.jpg').convert('RGB').crop(crop), 290)
    d_ = fit(trim(f'helmet/sheet/b11_{n}.png'), 290)
    c = Image.new('RGB', (p_.width + d_.width + 8, 290), 'white'); c.paste(p_, (0, 0)); c.paste(d_, (p_.width + 8, 0)); pairs.append(c)
W = max(ph.width + rz.width + 60, pairs[0].width + pairs[1].width + 60, pairs[2].width + pairs[3].width + 60)
H = 50 + 300 + 50 + 2 * (44 + 290 + 16) + 20
c = Image.new('RGB', (W, H), 'white'); d = ImageDraw.Draw(c)
d.text((20, 10), 'Front band close-up: your photo', font=F, fill=INK); d.text((ph.width + 50, 10), 'new design', font=F, fill=INK)
c.paste(ph, (20, 50)); c.paste(rz, (ph.width + 50, 50))
d.text((20, 360), 'Plain helmet + band only. The H, crest, cheek guards, trim and wings come in the next steps.', font=FS, fill=MUT)
y = 400
x2 = 20 + max(pairs[0].width, pairs[2].width) + 40
for i, (p_, t) in enumerate(zip(pairs, ('Front', '3/4', 'Side', 'Back'))):
    x = 20 if i % 2 == 0 else x2
    yy = y + (i // 2) * (44 + 290 + 16)
    d.text((x, yy), f'{t}: your photo | new design', font=F, fill=INK); c.paste(p_, (x, yy + 42))
c.save('pkg/step2_band.jpg', quality=92); print(c.size)
