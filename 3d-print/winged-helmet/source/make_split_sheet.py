"""Split sheet: exploded views with labels, the cheek guard piece outside/inside, back options A/B."""
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont
U = '/root/.claude/uploads/319431bf-dd7d-5dd8-8f43-98ef81b3e188/'
F = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 28)
FB = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 22)
FS = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 21)
INK, MUT, DOT = "#1B1F2A", "#4A5160", (220, 30, 110)
def trim(path, pad=8):
    im = Image.open(path).convert("RGB"); bb = ImageChops.difference(im, Image.new("RGB", im.size, im.getpixel((0, 0)))).getbbox(); im = im.crop(bb)
    a = np.asarray(im).astype(int); m = ((a.max(2) - a.min(2)) <= 3) & (a.min(2) >= 240); b = np.array(im); b[m] = 255; im = Image.fromarray(b)
    o = Image.new("RGB", (im.width + 2 * pad, im.height + 2 * pad), (255, 255, 255)); o.paste(im, (pad, pad)); return o
def fit(im, h): return im.resize((int(im.width * h / im.height), h), Image.LANCZOS)
ef = fit(trim('helmet/sheet/sp_expl_front.png'), 470)
eb = fit(trim('helmet/sheet/sp_expl_back.png'), 470)
go = fit(trim('helmet/sheet/sp_guard_out.png'), 300)
gi = fit(trim('helmet/sheet/sp_guard_in.png'), 300)
pa = fit(trim('helmet/sheet/sp_A.png'), 330)
pb = fit(trim('helmet/sheet/sp_B.png'), 330)
ph = fit(Image.open(U + 'e0a9281d-image.jpg').convert('RGB').crop((470, 190, 900, 690)), 330)
W = max(ef.width + eb.width + 60, go.width + gi.width + 60 + 560, ph.width + pa.width + pb.width + 80)
H = 50 + 470 + 30 + 50 + 300 + 30 + 50 + 330 + 60
c = Image.new('RGB', (W, H), 'white'); d = ImageDraw.Draw(c)
def tag(n, x, y):
    d.ellipse((x - 19, y - 19, x + 19, y + 19), fill=(27, 31, 42), outline='white', width=2); d.text((x, y), str(n), font=FB, fill='white', anchor='mm')
y = 10
d.text((20, y), 'Pulled apart (full size): front | back', font=F, fill=INK)
c.paste(ef, (20, y + 40)); c.paste(eb, (ef.width + 50, y + 40))
# labels on the exploded front view (positions relative to the image)
ox, oy = 20, y + 40
for n, (fx, fy) in ((1, (0.30, 0.28)), (2, (0.70, 0.12)), (3, (0.12, 0.62)), (3, (0.83, 0.70))):
    tag(n, ox + fx * ef.width, oy + fy * ef.height)
ox2 = ef.width + 50
for n, (fx, fy) in ((2, (0.38, 0.35)), (1, (0.70, 0.12)), (4, (0.25, 0.83)), (3, (0.88, 0.67))):
    tag(n, ox2 + fx * eb.width, oy + fy * eb.height)
y += 40 + 470 + 30
d.text((20, y), 'Cheek guard piece: outside | inside', font=F, fill=INK)
c.paste(go, (20, y + 40)); c.paste(gi, (go.width + 50, y + 40))
lx = go.width + gi.width + 90; ly = y + 50
legend = [(1, 'Upper front: dome, band, nose guard'), (2, 'Upper back: dome, band, back V'),
          (3, 'Cheek guard x2: navy plate + its gold border'), (4, 'Lower back (option A only)')]
for n, t in legend:
    tag(n, lx + 19, ly + 15); d.text((lx + 50, ly + 3), t, font=FS, fill=INK); ly += 46
d.text((lx, ly + 10), 'Navy tab along the cheek guard top =', font=FS, fill=MUT)
d.text((lx, ly + 38), 'the hidden tongue that slides up inside', font=FS, fill=MUT)
d.text((lx, ly + 66), 'the helmet, behind the band, and snaps in.', font=FS, fill=MUT)
y += 40 + 300 + 30
d.text((20, y), 'Back: your photo | A: lower back as its own piece | B: helmet ends at the band', font=F, fill=INK)
c.paste(ph, (20, y + 40)); c.paste(pa, (ph.width + 50, y + 40)); c.paste(pb, (ph.width + pa.width + 80, y + 40))
c.save('pkg/split_plan.jpg', quality=92); print(c.size)
