# overview of every plate: top view thumbnail, title, piece count, swaps, estimated time
import json, textwrap
from PIL import Image, ImageDraw, ImageFont
rows = json.load(open('ref2/plates.json'))
def font(sz, bold=False):
    for f in (('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),):
        try: return ImageFont.truetype(f, sz)
        except OSError: pass
    return ImageFont.load_default()
F, FB, FT = font(14), font(15, True), font(30, True)
W, TH = 5, 330
n = len(rows); H = (n + W - 1) // W
CW, CH = TH + 20, TH + 96
sheet = Image.new('RGB', (W * CW + 20, H * CH + 120), (24, 26, 32)); d = ImageDraw.Draw(sheet)
tot_h = sum((r['print_h'] or 0) + r['swaps'] * 78 / 3600 for r in rows); tot_sw = sum(r['swaps'] for r in rows)
d.text((20, 18), 'Winged helmet - AD5X plates (slots: 1 navy, 2 white, 3 gold)', fill='white', font=FT)
d.text((20, 62), f'{n} plates   about {tot_h:.0f} h of printing in total   {tot_sw} filament swaps (all on the multi-colour plates)   grey box = prime tower corner', fill=(200, 200, 200), font=F)
BADGE = {'navy': (30, 42, 82), 'white': (236, 236, 228), 'gold': (242, 193, 46)}
for k, r in enumerate(rows):
    x, y = 20 + (k % W) * CW, 110 + (k // W) * CH
    im = Image.open(f"ref2/plate_{r['plate']:02d}.png").resize((TH, TH))
    sheet.paste(im, (x, y + 58))
    t0 = r['title'].split(' - ')
    d.text((x, y), f"Plate {t0[0][:2]} · {t0[0][3:]}", fill='white', font=FB)
    d.text((x, y + 19), textwrap.shorten(t0[1] if len(t0) > 1 else '', 36, placeholder='...'), fill=(170, 170, 170), font=F)
    t = '' if r['print_h'] is None else f"~{r['print_h'] + r['swaps'] * 78 / 3600:.1f} h"
    sw = f"{r['swaps']} swaps" if r['swaps'] else 'no swaps'
    d.text((x, y + 36), f"{len(r['pieces'])} pieces   {sw}   {t}", fill=(210, 210, 210), font=F)
    for j, c in enumerate(r['colours']):
        d.rectangle([x + TH - 18 - 22 * j, y + 2, x + TH - 2 - 22 * j, y + 18], fill=BADGE[c], outline=(120, 120, 120))
sheet.save('pkg/step10_plates.jpg', quality=90)
print('saved', sheet.size)
