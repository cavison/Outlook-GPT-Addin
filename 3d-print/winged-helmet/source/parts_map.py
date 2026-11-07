"""Parts map: numbered callouts on the front and back pictures + legend."""
from PIL import Image, ImageDraw, ImageFont
U = '/root/.claude/uploads/319431bf-dd7d-5dd8-8f43-98ef81b3e188/'
FB = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 22)
FT = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 30)
FL = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 23)
FS = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 21)
INK, MUT, DOT = "#1B1F2A", "#4A5160", (220, 30, 110)
PARTS = [  # number, name, qty, colours
    (1, "Dome, front (forehead + nose guard)", "1", "navy"),
    (2, "Dome, back", "1", "navy"),
    (3, "Neck guard", "1", "navy"),
    (4, "Cheek guard", "2", "navy"),
    (5, "Brow band (front + back)", "2", "navy, gold, white"),
    (6, "Nose-guard strap", "1", "gold, navy, white"),
    (7, "Crest stripe (front + back)", "2", "gold, white"),
    (8, "Front H", "1", "gold, white, navy"),
    (9, "Cheek H", "2", "white"),
    (10, "Cheek-guard trim", "2", "gold"),
    (11, "Wing (2 parts each side)", "4", "navy, gold, white"),
]
def panel(fname, crop, calls, scale=1.0):
    im = Image.open(U + fname).convert('RGB').crop(crop)
    W, H = im.width, im.height
    pad = 150
    c = Image.new('RGB', (W + 2 * pad, H), 'white'); c.paste(im, (pad, 0))
    d = ImageDraw.Draw(c)
    for n, (fx, fy), (lx, ly) in calls:
        fx, fy = fx - crop[0] + pad, fy - crop[1]
        lx, ly = lx - crop[0] + pad, ly - crop[1]
        d.line([(lx, ly), (fx, fy)], fill=DOT, width=3)
        d.ellipse((fx - 6, fy - 6, fx + 6, fy + 6), fill=DOT, outline='white', width=2)
        d.ellipse((lx - 21, ly - 21, lx + 21, ly + 21), fill=(27, 31, 42), outline='white', width=2)
        d.text((lx, ly), str(n), font=FB, fill='white', anchor='mm')
    return c
# front picture: feature point, label position (photo coordinates; labels sit in the margins)
front = panel('fdb87b20-image.jpg', (330, 60, 1050, 730), [
    (1, (585, 300), (230, 300)),
    (7, (690, 232), (690, 90)),
    (8, (735, 345), (1150, 300)),
    (5, (575, 440), (230, 420)),
    (6, (690, 528), (1150, 470)),
    (9, (515, 590), (230, 540)),
    (4, (527, 630), (230, 625)),
    (10, (566, 688), (230, 700)),
    (11, (430, 200), (230, 160)),
])
back = panel('e0a9281d-image.jpg', (240, 40, 1140, 700), [
    (2, (600, 360), (140, 330)),
    (7, (690, 290), (690, 110)),
    (5, (760, 555), (1240, 520)),
    (3, (690, 630), (1240, 640)),
    (4, (535, 600), (140, 600)),
    (11, (360, 250), (140, 170)),
])
H = 560
front = front.resize((int(front.width * H / front.height), H), Image.LANCZOS)
back = back.resize((int(back.width * H / back.height), H), Image.LANCZOS)
LW = 560
W = front.width + back.width + LW + 60
c = Image.new('RGB', (W, max(H + 110, 18 + 52 + 11 * 58 + 70)), 'white'); d = ImageDraw.Draw(c)
d.text((20, 14), 'Front', font=FT, fill=INK); d.text((front.width + 40, 14), 'Back', font=FT, fill=INK)
c.paste(front, (20, 60)); c.paste(back, (front.width + 40, 60))
x0 = front.width + back.width + 70; y = 18
d.text((x0, y), 'Parts (same set at 5" and full size)', font=FT, fill=INK); y += 52
for n, name, q, col in PARTS:
    d.ellipse((x0, y, x0 + 32, y + 32), fill=(27, 31, 42)); d.text((x0 + 16, y + 16), str(n), font=FS, fill='white', anchor='mm')
    d.text((x0 + 44, y - 1), f'{name}  x{q}', font=FL, fill=INK)
    d.text((x0 + 44, y + 25), col, font=FS, fill=MUT); y += 58
d.text((x0, y + 4), 'Total: 19 pieces', font=FT, fill=INK)
d.text((20, H + 80), 'Pink dot = where the part is. 1-4 are the navy structure; 5-11 are add-ons that glue into shallow locating pockets.', font=FS, fill=MUT)
c.save('pkg/parts_map.jpg', quality=92); print(c.size)
