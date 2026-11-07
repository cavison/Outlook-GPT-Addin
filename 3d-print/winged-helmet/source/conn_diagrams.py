"""Cross-section diagrams of the four connector types."""
from PIL import Image, ImageDraw, ImageFont
NAVY, GOLD, WHITE, PIN, INK, MUT, LINE = (30, 42, 82), (242, 193, 46), (236, 236, 228), (224, 36, 94), "#1B1F2A", "#4A5160", (60, 60, 60)
F = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 26)
FB = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 19)
FS = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 18)
W_, H_ = 520, 470
def panel(title, sub):
    im = Image.new('RGB', (W_, H_), 'white'); d = ImageDraw.Draw(im)
    d.rounded_rectangle((2, 2, W_ - 3, H_ - 3), 14, outline=(200, 203, 210), width=2)
    d.text((18, 14), title, font=F, fill=INK)
    for i, t in enumerate(sub): d.text((18, H_ - 30 - 24 * (len(sub) - 1 - i)), t, font=FS, fill=MUT)
    return im, d
def R(d, x0, y0, x1, y1, col): d.rectangle((x0, y0, x1, y1), fill=col, outline=LINE, width=2)
def label(d, x, y, t, tx, ty):
    d.line((x, y, tx, ty), fill=(150, 150, 150), width=2); d.text((tx + 4, ty - 10), t, font=FB, fill=INK)
# A. dowel-pin seam
im, d = panel('A  Dowel-pin seam', ['Shell front and back meet on thick inner ribs.', 'Pins sit half in each rib: they line the', 'halves up and carry the load.'])
R(d, 60, 90, 250, 120, NAVY); R(d, 60, 120, 250, 170, NAVY)          # front half: wall + rib (top-down section)
R(d, 270, 90, 460, 120, NAVY); R(d, 270, 120, 460, 170, NAVY)        # back half
for y in (130,):
    d.rectangle((215, 135, 305, 155), fill=PIN, outline=LINE, width=2)
d.line((260, 80, 260, 185), fill=(150, 150, 150), width=1)
label(d, 150, 105, 'shell wall', 120, 215); label(d, 380, 150, 'inner rib', 330, 250); label(d, 260, 145, 'pin', 245, 290)
d.text((140, 60), 'outside', font=FS, fill=MUT); d.text((140, 180), 'inside', font=FS, fill=MUT)
A = im
# B. snap tongue
im, d = panel('B  Snap tongue', ['Cheek guards and neck plate: a tongue slides', 'up inside the shell; bumps click into windows', 'in the shell, hidden under the band.'])
R(d, 250, 70, 270, 330, NAVY)                        # shell wall (vertical section)
R(d, 230, 90, 250, 290, NAVY)                        # band (outside)
R(d, 222, 90, 230, 110, WHITE); R(d, 222, 270, 230, 290, WHITE)
d.rectangle((250, 165, 270, 190), fill='white', outline=LINE, width=2)   # window
R(d, 272, 140, 290, 330, NAVY)                       # tongue (inside)
R(d, 250, 330, 290, 392, NAVY)                       # guard plate below
d.pieslice((258, 165, 282, 190), 90, 270, fill=PIN, outline=LINE)      # bump
label(d, 240, 190, 'band (outside)', 60, 225); label(d, 262, 175, 'window', 320, 120); label(d, 270, 178, 'snap bump', 330, 180)
label(d, 281, 260, 'tongue', 330, 260); label(d, 270, 365, "cheek guard", 330, 365)
B = im
# C. press-fit peg
im, d = panel('C  Press-fit peg', ['H badges, crest, cheek H and the wing layers:', 'pegs with small crush ribs press into', 'matching holes and hold tight.'])
R(d, 100, 110, 420, 140, GOLD); R(d, 100, 140, 420, 160, WHITE); R(d, 100, 160, 420, 180, NAVY)
for x in (180, 340):
    d.rectangle((x - 12, 180, x + 12, 240), fill=PIN, outline=LINE, width=2)
R(d, 80, 280, 440, 320, NAVY)
for x in (180, 340): d.rectangle((x - 13, 280, x + 13, 304), fill='white', outline=LINE, width=2)
d.text((110, 70), 'badge (pulled up)', font=FB, fill=INK); d.text((110, 330), 'shell', font=FB, fill=INK)
d.line((180, 245, 180, 275), fill=(150, 150, 150), width=2); d.polygon([(174, 268), (186, 268), (180, 278)], fill=(150, 150, 150))
d.line((340, 245, 340, 275), fill=(150, 150, 150), width=2); d.polygon([(334, 268), (346, 268), (340, 278)], fill=(150, 150, 150))
C = im
# D. wing mount
im, d = panel('D  Wing mount', ['Dovetail key behind the eagle slides down into a', 'socket on the helmet side and a catch clicks;', 'a round peg stops it twisting.'])
R(d, 150, 80, 370, 360, NAVY)                         # socket block (front view)
d.polygon([(205, 80), (315, 80), (295, 330), (225, 330)], fill='white', outline=LINE)   # dovetail slot (tapered)
d.polygon([(212, 60), (308, 60), (290, 300), (230, 300)], fill=(150, 160, 190), outline=LINE)  # key (lighter = wing side)
d.rectangle((240, 330, 280, 350), fill=PIN, outline=LINE, width=2)   # catch
d.ellipse((330, 120, 356, 146), fill=PIN, outline=LINE, width=2)     # anti-twist peg
label(d, 260, 150, 'key on wing', 390, 70); label(d, 300, 300, 'socket', 390, 300); label(d, 260, 340, 'snap catch', 390, 345); label(d, 343, 133, 'anti-twist peg', 390, 140)
D = im
sheet = Image.new('RGB', (2 * W_ + 30, 2 * H_ + 30), 'white')
for i, p in enumerate((A, B, C, D)): sheet.paste(p, (10 + (i % 2) * (W_ + 10), 10 + (i // 2) * (H_ + 10)))
sheet.save('ref2/conn_diagrams.png'); print(sheet.size)
