"""Build the visual guide (PDF + overview JPG) from rendered PNGs."""
import os
from PIL import Image, ImageChops, ImageDraw, ImageFont
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

SRC = "helmet/sheet"
OUT = "pkg/winged_helmet/previews"
NAVY, GOLD, INK, MUTED = "#1E2A52", "#F2C12E", "#1B1F2A", "#5B6272"
BG = (248, 248, 248)
FONT = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
FONT_B = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"


def trimmed(name, pad=30):
    im = Image.open(f"{SRC}/{name}.png").convert("RGB")
    diff = ImageChops.difference(im, Image.new("RGB", im.size, BG))
    box = ImageChops.add(diff, diff, 2.0, -12).getbbox()
    im = im.crop(box) if box else im
    import numpy as np
    a = np.asarray(im).copy()
    ai = a.astype(int)
    a[((ai.max(axis=2) - ai.min(axis=2)) <= 3) & (ai.min(axis=2) >= 240)] = 255   # gray backdrop -> white
    im = Image.fromarray(a)
    out = Image.new("RGB", (im.width + 2 * pad, im.height + 2 * pad), (255, 255, 255))
    out.paste(im, (pad, pad))
    return out


IMGS = {n: trimmed(n) for n in
        ["hero", "front", "side", "back", "plate_helmet", "plate_wings", "colors", "socket"]}

# ---------------------------------------------------------------- PDF
W, H = landscape(letter)
M = 36
pdf = canvas.Canvas(f"{OUT}/winged_helmet_visual_guide.pdf", pagesize=(W, H))
pdf.setTitle("Winged Helmet - 5 inch mini - visual guide")


def header(title, sub=None):
    pdf.setFillColor(HexColor(NAVY)); pdf.rect(0, H - 54, W, 54, stroke=0, fill=1)
    pdf.setFillColor(HexColor(GOLD)); pdf.rect(0, H - 58, W, 4, stroke=0, fill=1)
    pdf.setFillColor(HexColor("#FFFFFF")); pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(M, H - 36, title)
    if sub:
        pdf.setFont("Helvetica", 11); pdf.drawRightString(W - M, H - 34, sub)


def footer(n):
    pdf.setFillColor(HexColor(MUTED)); pdf.setFont("Helvetica", 8.5)
    pdf.drawString(M, 18, "Renders of the actual print files (stl_mini_5in). "
                          "Colors are approximate; the real print will show layer lines.")
    pdf.drawRightString(W - M, 18, f"{n} / 5")


def place(img, x, y, w, h):
    """Fit img inside box (x, y, w, h), centered. Returns drawn rect."""
    s = min(w / img.width, h / img.height)
    dw, dh = img.width * s, img.height * s
    dx, dy = x + (w - dw) / 2, y + (h - dh) / 2
    pdf.drawImage(ImageReader(img), dx, dy, dw, dh)
    return dx, dy, dw, dh


def caption(x, y, w, title, body=None):
    pdf.setFillColor(HexColor(INK)); pdf.setFont("Helvetica-Bold", 11.5)
    pdf.drawCentredString(x + w / 2, y, title)
    if body:
        pdf.setFillColor(HexColor(MUTED)); pdf.setFont("Helvetica", 9.5)
        for i, line in enumerate(body):
            pdf.drawCentredString(x + w / 2, y - 14 - 12 * i, line)


def bullets(x, y, items, size=11, lead=17, width=None):
    for head, text in items:
        pdf.setFillColor(HexColor(GOLD)); pdf.circle(x + 3, y + 3.5, 2.6, stroke=0, fill=1)
        pdf.setFillColor(HexColor(INK)); pdf.setFont("Helvetica-Bold", size)
        pdf.drawString(x + 12, y, head)
        if text:
            tw = pdf.stringWidth(head + "  ", "Helvetica-Bold", size)
            pdf.setFont("Helvetica", size); pdf.setFillColor(HexColor(MUTED))
            pdf.drawString(x + 12 + tw, y, text)
        y -= lead
    return y


# Page 1 - what it is
header("Winged Varsity Helmet  -  5\" mini", "Flashforge AD5X  |  navy / gold / white")
place(IMGS["hero"], M, 40, W * 0.56, H - 110)
x0 = W * 0.60
pdf.setFillColor(HexColor(INK)); pdf.setFont("Helvetica-Bold", 15)
pdf.drawString(x0, H - 100, "What you're printing")
y = bullets(x0, H - 128, [
    ("Overall height:", "127 mm (5.00 in) tall"),
    ("Helmet:", "84 x 99 x 96 mm, one piece"),
    ("Wings:", "2, each 53 x 70 x 4.2 mm"),
    ("Colors:", "3 STL files per piece"),
    ("Assembly:", "wings slide into gold sockets"),
])
pdf.setFillColor(HexColor(INK)); pdf.setFont("Helvetica-Bold", 13)
pdf.drawString(x0, y - 14, "Color key")
for i, (hexc, name, what) in enumerate([
        (NAVY, "Navy", "helmet shell, wing base, pegs"),
        (GOLD, "Gold", "crest, band, letter, trim, sockets"),
        ("#F4F4EE", "White", "stripes, outline, rivets, cheek H")]):
    yy = y - 40 - i * 24
    pdf.setFillColor(HexColor(hexc)); pdf.setStrokeColor(HexColor("#9AA0AA"))
    pdf.roundRect(x0, yy - 4, 26, 16, 3, stroke=1, fill=1)
    pdf.setFillColor(HexColor(INK)); pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(x0 + 36, yy, name)
    pdf.setFillColor(HexColor(MUTED)); pdf.setFont("Helvetica", 10)
    pdf.drawString(x0 + 80, yy, what)
footer(1); pdf.showPage()

# Page 2 - all angles
header("All angles", "assembled, wings mounted")
cw = (W - 2 * M) / 3
for i, (n, t) in enumerate([("front", "Front"), ("side", "Side"), ("back", "Back")]):
    place(IMGS[n], M + i * cw, 70, cw, H - 150)
    caption(M + i * cw, 52, cw, t)
footer(2); pdf.showPage()

# Page 3 - print plates
header("What comes off the printer", "AD5X 220 x 220 mm bed, grid = 20 mm")
hw = (W - 2 * M - 20) / 2
place(IMGS["plate_helmet"], M, 110, hw, H - 190)
caption(M, 92, hw, "Plate 1 - Helmet",
        ["Opening down, as exported. Tree supports + 5 mm brim.",
         "0.16 mm layers  |  about 980 color swaps"])
place(IMGS["plate_wings"], M + hw + 20, 110, hw, H - 190)
caption(M + hw + 20, 92, hw, "Plate 2 - Both wings",
        ["Flat, decorated side up, no supports.",
         "0.2 mm layers  |  about 42 color swaps"])
footer(3); pdf.showPage()

# Page 4 - color breakdown
header("How the 3 color files fit together", "helmet shown; wings work the same way")
place(IMGS["colors"], M, 110, W - 2 * M, H - 180)
for i, (t, f) in enumerate([("Navy", "helmet_navy.stl"), ("Gold", "helmet_gold.stl"),
                            ("White", "helmet_white.stl")]):
    caption(M + i * cw, 92, cw, t, [f])
pdf.setFillColor(HexColor(MUTED)); pdf.setFont("Helvetica", 10)
pdf.drawCentredString(W / 2, 50, "Load all three together as ONE object with multiple parts; "
                                 "they line up automatically. Assign one IFS slot to each.")
footer(4); pdf.showPage()

# Page 5 - assembly
header("Attaching the wings")
place(IMGS["socket"], M, 40, W * 0.55, H - 110)
x0 = W * 0.60
pdf.setFillColor(HexColor(INK)); pdf.setFont("Helvetica-Bold", 15)
pdf.drawString(x0, H - 100, "Steps")
steps = [
    "Each wing has a navy peg on its bottom edge.",
    "Each side of the helmet has a gold socket.",
    "Decorated face points OUTWARD; the wing",
    "sweeps toward the BACK of the helmet.",
    "Slide the peg straight down into the slot.",
    "Loose? One drop of super glue.",
    "Tight? Sand the peg lightly.",
]
pdf.setFont("Helvetica", 11.5)
yy = H - 130
for i, s in enumerate(steps):
    num = {0: "1", 1: "2", 2: "3", 4: "4", 5: "5", 6: "6"}.get(i)
    if num:
        pdf.setFillColor(HexColor(NAVY)); pdf.circle(x0 + 8, yy + 4, 9, stroke=0, fill=1)
        pdf.setFillColor(HexColor("#FFFFFF")); pdf.setFont("Helvetica-Bold", 10)
        pdf.drawCentredString(x0 + 8, yy + 0.5, num)
    pdf.setFillColor(HexColor(INK)); pdf.setFont("Helvetica", 11.5)
    pdf.drawString(x0 + 26, yy, s)
    yy -= 24 if i not in (2,) else 17
footer(5); pdf.showPage()
pdf.save()

# ---------------------------------------------------------------- overview JPG
CW, CH = 2400, 1600
sheet = Image.new("RGB", (CW, CH), (255, 255, 255))
d = ImageDraw.Draw(sheet)
f_t, f_s, f_c = ImageFont.truetype(FONT_B, 54), ImageFont.truetype(FONT, 30), ImageFont.truetype(FONT_B, 30)
d.rectangle([0, 0, CW, 110], fill=NAVY); d.rectangle([0, 110, CW, 118], fill=GOLD)
d.text((40, 24), "Winged Varsity Helmet  -  5\" mini", font=f_t, fill="white")
d.text((CW - 40, 40), "127 mm tall  |  navy / gold / white  |  Flashforge AD5X",
       font=f_s, fill="white", anchor="ra")


def paste_fit(img, x, y, w, h, label=None):
    im = img.copy(); im.thumbnail((w, h - (44 if label else 0)), Image.LANCZOS)
    sheet.paste(im, (x + (w - im.width) // 2, y + (h - (44 if label else 0) - im.height) // 2))
    if label:
        d.text((x + w // 2, y + h - 34), label, font=f_c, fill=INK, anchor="ma")


paste_fit(IMGS["hero"], 20, 140, 940, 1420, "Assembled")
gx, gy, gw, gh = 980, 140, 470, 700
paste_fit(IMGS["front"], gx, gy, gw, gh, "Front")
paste_fit(IMGS["side"], gx + gw, gy, gw, gh, "Side")
paste_fit(IMGS["back"], gx + 2 * gw, gy, gw - 20, gh, "Back")
paste_fit(IMGS["plate_helmet"], gx, gy + gh + 20, 700, 700, "Plate 1: helmet")
paste_fit(IMGS["plate_wings"], gx + 710, gy + gh + 20, 700, 700, "Plate 2: wings")
sheet.save(f"{OUT}/winged_helmet_overview.jpg", quality=92)
print("ok")
