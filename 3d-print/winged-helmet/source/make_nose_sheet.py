from PIL import Image, ImageDraw, ImageFont
B = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"; R = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
F, FB, FS, FL = ImageFont.truetype(B, 32), ImageFont.truetype(B, 22), ImageFont.truetype(R, 21), ImageFont.truetype(B, 19)
INK, MUT, PINK = "#1B1F2A", "#4A5160", (224, 36, 94)
def load(n, box=None, w=None, h=None):
    im = Image.open(n).convert('RGB')
    if box: im = im.crop(box)
    if w: return im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)
    return im.resize((int(im.width * h / im.height), h), Image.LANCZOS)
S = 'helmet/sheet/'
# --- annotated cross-section (labels drawn at the final size) ---
H2 = 760
sec = Image.open('ref2/nose_section.png').convert('RGB')        # window y -150..-118, z -62..32, 14 px/mm
k = H2 / sec.height; sec = sec.resize((int(sec.width * k), H2), Image.LANCZOS)
Y0, Z1, SC = -150.0, 32.0, 14.0 * k
def px(y, z): return ((y - Y0) * SC, (Z1 - z) * SC)
LM, RM = 330, 330
FL = ImageFont.truetype(B, 21)
cs = Image.new('RGB', (sec.width + LM + RM, sec.height), 'white'); cs.paste(sec, (LM, 0)); d = ImageDraw.Draw(cs)
left = [('Strap plate (gold)', -137.1, 14, 90), ('Navy panel', -138.5, 4, 200), ('Nose bar, leans 10° forward', -136, -45, 640)]
right = [('Shell', -129.9, 24, 90), ('Band layers', -133.4, -2, 230), ('Snap bump in a hole', -129.3, 8, 360),
         ('Tongue (inside)', -127.3, -4, 490)]
for t, y, z, ty in left:
    x, yy = px(y, z); x += LM; tx = LM - 20
    d.line((x, yy, tx, ty), fill=(40, 40, 40), width=2); d.ellipse((x - 6, yy - 6, x + 6, yy + 6), fill=PINK, outline='white', width=2)
    d.text((tx - 8, ty), t, font=FL, fill=INK, anchor='rm')
for t, y, z, ty in right:
    x, yy = px(y, z); x += LM; tx = LM + sec.width + 20
    d.line((x, yy, tx, ty), fill=(40, 40, 40), width=2); d.ellipse((x - 6, yy - 6, x + 6, yy + 6), fill=PINK, outline='white', width=2)
    d.text((tx + 8, ty), t, font=FL, fill=INK, anchor='lm')
d.text((LM - 60, 16), 'OUTSIDE', font=FB, fill=MUT, anchor='rt'); d.text((LM + sec.width + 60, 16), 'INSIDE', font=FB, fill=MUT, anchor='lt')
# --- layout ---
M, G = 24, 20
row1 = [('Nose on', load(S + 'nz_on.png', (150, 40, 1050, 1000), w=480)),
        ('Nose off: band stays complete', load(S + 'nz_off.png', (150, 40, 1050, 1000), w=480)),
        ('Other option: a strap stub stays on', load(S + 'nz_off_stub.png', (150, 40, 1050, 1000), w=480))]
side = load(S + 'nz_side.png', (330, 150, 1000, 1080), h=H2)
secimg = cs
pieces = load(S + 'nz_pieces.png', (80, 110, 1520, 740), w=1480)
W = M * 2 + 480 * 3 + G * 2
text = [
    ('How it goes on and off', [
        'Slide it up from below. The strap plate rides over the band, the tongue goes up inside the shell, and two bumps',
        'click into holes in the shell (hidden under the band). Pull down firmly to take it off. No tools, no glue.',
        'Below the brow the bar leans 10° forward, so the tip sits about 7 mm further from your nose.']),
    ('Pieces (each one colour, no swaps)', [
        'Gold body: the border, the point under the H and both gold rivets (about 23 g).',
        'Navy panel: sits flush in the body; the gold rivets poke up through it.',
        'White rivet pin: presses through the panel into the body and locks the panel in.']),
]
TH = sum(40 + 30 * len(l) + 10 for _, l in text)
H = 70 + 34 + row1[0][1].height + 30 + 34 + H2 + 30 + 34 + pieces.height + 20 + TH + 20
c = Image.new('RGB', (W, H), 'white'); d = ImageDraw.Draw(c)
d.text((M, 18), 'Detachable nose piece: slides up and clicks on, pulls off by hand', font=F, fill=INK)
y = 70
for k, (t, im) in enumerate(row1):
    x = M + k * (480 + G); d.text((x, y), t, font=FB, fill=INK); c.paste(im, (x, y + 34))
d.rectangle((M + 480 + G - 4, y + 30, M + 2 * 480 + G + 4, y + 34 + row1[1][1].height + 4), outline=(46, 160, 90), width=4)
bx, by = M + 480 + G, y + 34 + row1[1][1].height - 40
d.rectangle((bx, by, bx + 170, by + 40), fill=(46, 160, 90)); d.text((bx + 85, by + 20), 'recommended', font=FB, fill='white', anchor='mm')
y += 34 + row1[0][1].height + 30
d.text((M, y), 'Side view', font=FB, fill=INK); d.text((M + side.width + G, y), 'Cut through the clip (side on)', font=FB, fill=INK)
c.paste(side, (M, y + 34)); c.paste(secimg, (M + side.width + G, y + 34))
y += 34 + H2 + 30
d.text((M, y), 'The parts: gold body (front, back), navy panel, white rivet pin', font=FB, fill=INK)
c.paste(pieces, (M, y + 34)); y += 34 + pieces.height + 20
for head, lines in text:
    d.text((M, y), head, font=FB, fill=INK); y += 34
    for t in lines: d.text((M, y), t, font=FS, fill=MUT); y += 30
    y += 16
c = c.crop((0, 0, W, y + 10))
c.save('pkg/step7_nose_piece.jpg', quality=92); print(c.size, side.width, secimg.width)
