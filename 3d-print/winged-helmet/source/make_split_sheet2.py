"""Final split: top shell (front + back) ends at the band; cheek left, cheek right, neck plate below."""
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont
U = '/root/.claude/uploads/319431bf-dd7d-5dd8-8f43-98ef81b3e188/'
F = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 28)
FB = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 22)
FS = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 21)
INK, MUT = "#1B1F2A", "#4A5160"
def trim(path, pad=8):
    im = Image.open(path).convert("RGB"); bb = ImageChops.difference(im, Image.new("RGB", im.size, im.getpixel((0, 0)))).getbbox(); im = im.crop(bb)
    a = np.asarray(im).astype(int); m = ((a.max(2) - a.min(2)) <= 3) & (a.min(2) >= 240); b = np.array(im); b[m] = 255; im = Image.fromarray(b)
    o = Image.new("RGB", (im.width + 2 * pad, im.height + 2 * pad), (255, 255, 255)); o.paste(im, (pad, pad)); return o
def fit(im, h): return im.resize((int(im.width * h / im.height), h), Image.LANCZOS)
ef = fit(trim('helmet/sheet/sp_expl_front.png'), 470)
eb = fit(trim('helmet/sheet/sp_expl_back.png'), 470)
pa = fit(trim('helmet/sheet/sp_A.png'), 360)
ph = fit(Image.open(U + 'e0a9281d-image.jpg').convert('RGB').crop((470, 190, 900, 690)), 360)
LW = 600
W = max(ef.width + eb.width + 60, ph.width + pa.width + LW + 90)
H = 50 + 470 + 40 + 50 + 360 + 30
c = Image.new('RGB', (W, H), 'white'); d = ImageDraw.Draw(c)
def tag(n, x, y):
    d.ellipse((x - 19, y - 19, x + 19, y + 19), fill=(27, 31, 42), outline='white', width=2); d.text((x, y), str(n), font=FB, fill='white', anchor='mm')
d.text((20, 10), 'Pulled apart (full size): from the front | from the back', font=F, fill=INK)
c.paste(ef, (20, 50)); c.paste(eb, (ef.width + 50, 50))
for n, (fx, fy) in ((1, (0.30, 0.28)), (2, (0.70, 0.12)), (4, (0.12, 0.62)), (3, (0.83, 0.70))):
    tag(n, 20 + fx * ef.width, 50 + fy * ef.height)
ox2 = ef.width + 50
for n, (fx, fy) in ((2, (0.38, 0.35)), (1, (0.70, 0.12)), (5, (0.25, 0.83)), (3, (0.88, 0.67))):
    tag(n, ox2 + fx * eb.width, 50 + fy * eb.height)
y = 50 + 470 + 40
d.text((20, y), 'Back: your photo | put together', font=F, fill=INK)
c.paste(ph, (20, y + 40)); c.paste(pa, (ph.width + 50, y + 40))
lx = ph.width + pa.width + 90; ly = y + 50
legend = [(1, 'Top shell, front', '209 x 125 x 191 mm'), (2, 'Top shell, back', '209 x 125 x 213 mm'),
          (3, 'Cheek guard, right', '42 x 147 x 142 mm'), (4, 'Cheek guard, left', '42 x 147 x 142 mm'),
          (5, 'Neck plate', '176 x 62 x 74 mm')]
for n, t, sz in legend:
    tag(n, lx + 19, ly + 15); d.text((lx + 50, ly + 2), t, font=FB, fill=INK); d.text((lx + 290, ly + 3), sz, font=FS, fill=MUT); ly += 44
d.text((lx, ly + 12), 'Top shell ends at the band.  3, 4 and 5 hang', font=FS, fill=MUT)
d.text((lx, ly + 40), 'below it on hidden tongues behind the band.', font=FS, fill=MUT)
d.text((lx, ly + 68), 'All fit the 220 mm bed at full size.', font=FS, fill=MUT)
c.save('pkg/split_final.jpg', quality=92); print(c.size)
