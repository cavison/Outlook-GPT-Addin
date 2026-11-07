"""Step-1 sheet, v10: design vs the four new pictures."""
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont
U = '/root/.claude/uploads/319431bf-dd7d-5dd8-8f43-98ef81b3e188/'
F = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 30)
FS = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 22)
INK, MUT = "#1B1F2A", "#4A5160"
def trim(path, pad=10):
    im = Image.open(path).convert("RGB")
    a = np.asarray(im).astype(int); m = ((a.max(2) - a.min(2)) <= 3) & (a.min(2) >= 240)
    b = np.array(im); b[m] = 255; im = Image.fromarray(b)
    bb = ImageChops.difference(im, Image.new("RGB", im.size, (255, 255, 255))).getbbox(); im = im.crop(bb)
    o = Image.new("RGB", (im.width + 2 * pad, im.height + 2 * pad), (255, 255, 255)); o.paste(im, (pad, pad)); return o
def fit_h(im, h): return im.resize((int(im.width * h / im.height), h), Image.LANCZOS)
ovf = fit_h(Image.open('ref2/v10_front_overlay_o.png'), 560)
ovq = fit_h(Image.open('ref2/v10_q34_overlay.png'), 560)
pairs = []
for n, f, crop in (('front', 'fdb87b20', (470, 190, 910, 720)), ('q34', '9821a39f', (440, 190, 900, 730)),
                   ('side', 'd47111e3', (420, 200, 920, 710)), ('back', 'e0a9281d', (470, 190, 900, 690))):
    ph = fit_h(Image.open(U + f + '-image.jpg').convert('RGB').crop(crop), 300)
    rd = fit_h(trim(f'helmet/sheet/v10_{n}.png'), 300)
    c = Image.new('RGB', (ph.width + rd.width + 8, 300), 'white'); c.paste(ph, (0, 0)); c.paste(rd, (ph.width + 8, 0)); pairs.append(c)
W = max(ovf.width + ovq.width + 60, pairs[0].width + pairs[1].width + 60)
row2 = max(pairs[0].width + pairs[1].width, pairs[2].width + pairs[3].width) + 60
W = max(W, row2)
H = 50 + 560 + 50 + 2 * (44 + 300 + 20) + 20
c = Image.new('RGB', (W, H), 'white'); d = ImageDraw.Draw(c)
d.text((20, 10), 'Front: your photo (pink) vs new design (blue)', font=F, fill=INK)
d.text((ovf.width + 50, 10), '3/4: your photo (pink) vs new design (blue)', font=F, fill=INK)
c.paste(ovf, (20, 50)); c.paste(ovq, (ovf.width + 50, 50))
d.text((20, 50 + 560 + 10), 'The blue line is the new helmet\'s opening edge, drawn on your pictures.', font=FS, fill=MUT)
y = 50 + 560 + 50
for i, (p, t) in enumerate(zip(pairs, ('Front', '3/4', 'Side', 'Back'))):
    x = 20 + (i % 2) * (pairs[0].width + 40 if i % 2 else 0)
    if i % 2: x = 20 + max(pairs[0].width, pairs[2].width) + 40
    yy = y + (i // 2) * (44 + 300 + 20)
    d.text((x, yy), f'{t}: your photo | new design', font=F, fill=INK); c.paste(p, (x, yy + 44))
c.save('pkg/step1d_v10.jpg', quality=92); print(c.size)
