# every helmet piece as it will sit on the bed (two side views, bed = red line)
import numpy as np, trimesh, sys
from PIL import Image, ImageDraw, ImageFont
_s = open('plates_build.py').read(); exec(_s[:_s.index('# ---------- packing ----------')])
_v = open('view_pieces.py').read(); exec(_v[_v.index('def view('):_v.index('tiles = []')])
F = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 13)
names = [p['name'] for p in P if p['group'] != 'multi' and p['settings'] not in ('pin', 'core')]
T = 170; cols = 4
tiles = []
for nm in names:
    p = [q for q in P if q['name'] == nm][0]
    parts = oriented(p)
    ext = np.ptp(np.vstack([m.vertices for m, _ in parts]), 0).max()
    t = Image.new('RGB', (2 * T + 10, T + 22), 'white'); d = ImageDraw.Draw(t)
    for j, ax in enumerate(('front', 'side')):
        t.paste(view(parts, ax, (T - 20) / ext, T), (j * (T + 5), 20))
    h = max(m.vertices[:, 2].max() for m, _ in parts)
    d.text((4, 3), f'{nm}  ({h:.0f} mm tall)', fill='black', font=F)
    tiles.append(t)
rows = (len(tiles) + cols - 1) // cols
sheet = Image.new('RGB', (cols * (2 * T + 20), rows * (T + 30)), (235, 235, 235))
for k, t in enumerate(tiles): sheet.paste(t, ((k % cols) * (2 * T + 20) + 5, (k // cols) * (T + 30) + 5))
sheet.save(sys.argv[1] if len(sys.argv) > 1 else 'ref2/orient_sheet.png')
