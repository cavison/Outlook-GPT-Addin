import json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
F = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 30)
FB = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 21)
FS = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 20)
INK, MUT, PINK = "#1B1F2A", "#4A5160", (224, 36, 94)
pos = json.load(open('ref2/jm_pos.json'))
def annotate(img, items):
    im = img.convert('RGB').copy(); d = ImageDraw.Draw(im)
    for n, key, (ox, oy) in items:
        x, y = pos[key]; tx, ty = x + ox, y + oy
        d.line((x, y, tx, ty), fill=(40, 40, 40), width=4)
        d.ellipse((x - 9, y - 9, x + 9, y + 9), fill=PINK, outline='white', width=3)
        d.ellipse((tx - 30, ty - 30, tx + 30, ty + 30), fill=(27, 31, 42), outline='white', width=4)
        d.text((tx, ty), str(n), font=ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 34), fill='white', anchor='mm')
    return im
fr = annotate(Image.open('helmet/sheet/jm_front.png'), [(1, 'f0', (40, -150)), (2, 'f2', (230, 40)), (3, 'f3', (190, 120)), (6, 'f6', (-170, -60)),
                                                        (7, 'f7', (-60, 150)), (8, 'f8', (-150, -170))])
bk = annotate(Image.open('helmet/sheet/jm_back.png'), [(1, 'b1', (170, -120)), (4, 'b4', (-60, 170)), (5, 'b5', (170, 120)), (8, 'b9', (-170, -160))])
def crop(im): return im.crop((150, 120, 1100, 1080))
fr, bk = crop(fr), crop(bk)
H1 = 560; fr = fr.resize((int(fr.width * H1 / fr.height), H1), Image.LANCZOS); bk = bk.resize((int(bk.width * H1 / bk.height), H1), Image.LANCZOS)
wing = Image.open('ref2/wing_pieces.png').convert('RGB'); H2 = 620; wing = wing.resize((int(wing.width * H2 / wing.height), H2), Image.LANCZOS)
diag = Image.open('ref2/conn_diagrams.png').convert('RGB'); diag = diag.resize((int(diag.width * 0.78), int(diag.height * 0.78)), Image.LANCZOS)
rows = [
    ('1', 'Top shell: front to back seam', 'A  dowel pins', '7', '5 mm pins'),
    ('2', 'Wing mount block (bridges the seam)', 'A dowels + D', '4 + slide', 'new small piece, each side'),
    ('3', 'Cheek guard to shell', 'B  snap tongue', '2 bumps + 1 pin', 'each side'),
    ('4', 'Neck plate to shell', 'B  snap tongue', '3 bumps', ''),
    ('5', 'Cheek guard to neck plate', 'C  peg', '1', 'each side'),
    ('6', 'Front H to shell', 'C  pegs', '3', ''),
    ('7', 'Cheek H to cheek guard', 'C  pegs', '2', 'each side'),
    ('8', 'Crest: white to shell, gold to white', 'C  pegs', '3 per piece', '4 pieces'),
    ('9', 'Wing layers (front / white / back)', 'C  pegs', '3 per section', 'pink dots'),
    ('10', 'Wing sections to the shoulder', 'C  pegs', '2 per joint', 'orange diamonds'),
]
W = max(fr.width + bk.width + 60, wing.width + diag.width + 60)
TH = 46 + 34 * len(rows) + 120
Htot = 60 + H1 + 30 + max(H2, diag.height) + 60 + TH
c = Image.new('RGB', (W, Htot), 'white'); d = ImageDraw.Draw(c)
d.text((20, 12), 'Every joint is pegged or snapped: where each connector goes', font=F, fill=INK)
c.paste(fr, (20, 60)); c.paste(bk, (fr.width + 40, 60))
y = 60 + H1 + 20
d.text((20, y), 'Wing pegs (one wing; the other is its mirror)', font=FB, fill=INK)
d.text((wing.width + 40, y), 'Connector types', font=FB, fill=INK)
c.paste(wing, (20, y + 34)); c.paste(diag, (wing.width + 40, y + 34))
y = y + 34 + max(H2, diag.height) + 30
cols = [20, 80, 560, 760, 960]
for x, t in zip(cols, ['#', 'Joint', 'Connector', 'Count', 'Note']): d.text((x, y), t, font=FB, fill=INK)
y += 36
for r in rows:
    for x, t in zip(cols, r): d.text((x, y), t, font=FS, fill=INK if x == cols[1] else MUT)
    y += 34
y += 12
for t in ['Full size: printed pegs and pins (5 mm) with small crush ribs; snap bumps click into windows hidden under the band.',
          '5" version: printed pegs would be under 1.5 mm and snap off, so every peg spot becomes a hole for a short piece of',
          '1.75 mm filament used as a pin (stronger than a printed peg at that size). Same holes, same places, nothing glued alone.']:
    d.text((20, y), t, font=FS, fill=MUT); y += 30
c.save('pkg/step5_connectors.jpg', quality=92); print(c.size)
