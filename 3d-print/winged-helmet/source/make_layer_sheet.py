from PIL import Image, ImageDraw, ImageFont
B = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"; R = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
F, FB, FS, FT = ImageFont.truetype(B, 32), ImageFont.truetype(B, 22), ImageFont.truetype(R, 21), ImageFont.truetype(B, 21)
INK, MUT, NAVY, GOLD = "#1B1F2A", "#4A5160", (27, 42, 92), (201, 151, 26)
def load(n, box=None, w=620):
    im = Image.open(f'helmet/sheet/{n}.png').convert('RGB')
    if box: im = im.crop(box)
    return im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)
rows = [
    (('Current: one multi-colour print', load('br_front', (230, 40, 1170, 960))), ('Layered: three single-colour layers', load('bl_front', (230, 40, 1170, 960)))),
    (('Close-up, current', load('br_close')), ('Close-up, layered', load('bl_close'))),
    (('Back, layered', load('bl_back', (230, 40, 1170, 960))), ('How it stacks: white base, gold middle, navy top', load('bl_explode', (40, 0, 1400, 1060)))),
]
GAP, M = 24, 24
W = M * 2 + 620 * 2 + GAP
table = [
    ('', 'Current', 'Layered'),
    ('Colour swaps on the band', 'about 1,600 (20+ hours of swapping)', '0'),
    ('Look', 'colours stand on top of the navy', 'colours set into the navy, like an inlay'),
    ('Height on the shell', '3 to 5 mm', '3.2 mm (1.2 white, 1.0 gold, 1.0 navy)'),
    ('Print pieces', 'multi-colour pieces', '4 white + 4 gold + 4 navy + small navy V insert'),
    ('Held by', 'pins into the shell', 'white dots are pegs locking the layers + shell pins'),
]
notes = [
    'Seams: navy and white split under the nose strap, the back V and the wings, so no seam shows. Gold splits where the navy covers it.',
    'The nose strap is shown attached here. It becomes the snap-on / snap-off nose piece in the next step.',
    'Whole helmet after this change: band 0 swaps, crest 0, cheek guards 0, front H 2, wings about 520 to 600 (roughly 7 to 9 hours).',
]
rh = [max(a[1].height, b[1].height) for a, b in rows]
H = 70 + sum(h + 44 for h in rh) + 20 + 40 * len(table) + 20 + 32 * len(notes) + 30
c = Image.new('RGB', (W, H), 'white'); d = ImageDraw.Draw(c)
d.text((M, 18), 'Layered band: same look, no colour swaps', font=F, fill=INK)
y = 70
for (ta, ia), (tb, ib) in rows:
    d.text((M, y), ta, font=FB, fill=INK); d.text((M + 620 + GAP, y), tb, font=FB, fill=INK)
    c.paste(ia, (M, y + 34)); c.paste(ib, (M + 620 + GAP, y + 34))
    y += max(ia.height, ib.height) + 44
y += 10
cols = [M, M + 290, M + 700]
for i, r in enumerate(table):
    if i == 0: d.rectangle((M - 6, y - 6, W - M + 6, y + 30), fill=(236, 239, 246))
    for k, (x, t) in enumerate(zip(cols, r)):
        d.text((x, y), t, font=FT if (i == 0 or k == 0) else FS, fill=INK if (i == 0 or k == 0) else (NAVY if k == 2 else MUT))
    y += 40
    d.line((M - 6, y - 8, W - M + 6, y - 8), fill=(225, 228, 235), width=1)
y += 14
for t in notes:
    d.text((M, y), t, font=FS, fill=MUT); y += 32
c.save('pkg/step6_layered_band.jpg', quality=92); print(c.size)
