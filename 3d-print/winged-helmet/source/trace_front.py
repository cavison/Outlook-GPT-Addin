"""Trace the face-opening edge in the straight-on front picture.
The edge is the inner side of the gold trim (cheek guards, nose guard) and the
bottom of the white rim under the band.  Table shadows are never used: every
edge is found by stepping from the dark inside of the helmet onto trim."""
import json, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
SRC = '/root/.claude/uploads/319431bf-dd7d-5dd8-8f43-98ef81b3e188/fdb87b20-image.jpg'
im = np.asarray(Image.open(SRC).convert('RGB')).astype(int)
r, g, b = im[..., 0], im[..., 1], im[..., 2]
mx, mn = im.max(2), im.min(2)
gold = ndimage.binary_opening((r > 110) & (r - b > 45), iterations=1)
dark = mx < 45
light = (mn > 150) & (mx - mn < 30)

# nose guard centre and extent
row = gold[520, 600:780]; xs = np.nonzero(row)[0] + 600
xc = (xs.min() + xs.max()) / 2
print('nose centre x', xc)

def scan(y, x, step):
    """from (x, y) step sideways until gold; return the last non-gold x"""
    while 0 < x < im.shape[1] - 1 and not gold[y, x]:
        x += step
    return x - step

# rows covered by the opening: top of the dark inside to the guard tips
dark_rows = np.nonzero(dark[:, int(xc) - 120])[0]
y_top = dark_rows[(dark_rows > 420) & (dark_rows < 520)].min()
# nose guard: lowest gold row on the centre line
col = gold[:, int(xc)]; nose_rows = np.nonzero(col[440:640])[0] + 440
y_tip = nose_rows.max()
print('top of opening', y_top, 'nose tip', y_tip)

L, R = [], []
y = y_top
while True:
    sx = int(xc) if y > y_tip + 2 else int(xc) - 120      # start inside the eye while the nose guard is in the way
    xl = scan(y, sx, -1)
    sx = int(xc) if y > y_tip + 2 else int(xc) + 120
    xr = scan(y, sx, +1)
    if xl < 300 or xr > 1100:     # ran off the bottom of a guard
        break
    L.append((xl + 0.5, y)); R.append((xr - 0.5, y))
    y += 1
y_bot = y - 1
print('guard tips at', y_bot)

# brow: bottom of the white rim, column by column, across each eye
brow = []
for x in range(int(L[0][0]) - 0, int(R[0][0]) + 1):
    c = light[430:520, x]; d = dark[430:520, x]
    ys = [i for i in range(3, 75) if d[i:i + 12].all() and light[430 + i - 3:430 + i, x].any()]
    if ys:
        brow.append((x, 430 + ys[0] - 0.5))
# nose guard sides (outer edge of its gold trim) from the rim down to the tip
nl, nr = [], []
for y in range(y_top, y_tip + 1):
    xs = np.nonzero(gold[y, int(xc) - 90:int(xc) + 91])[0]
    if len(xs) == 0:
        continue
    xs = xs + int(xc) - 90
    nl.append((xs.min() - 0.5, y)); nr.append((xs.max() + 0.5, y))
# brow: drop rivet-dot spikes (anything well above the running median)
bx = np.array([p[0] for p in brow]); by = np.array([p[1] for p in brow])
med = ndimage.median_filter(by, 41, mode='nearest')
ok = np.abs(by - med) < 3
brow = [(float(x), float(y)) for x, y, k in zip(bx, by, ok) if k]
# nose sides: only below where the brow meets them
def brow_y_at(x):
    i = np.argmin([abs(p[0] - x) for p in brow]); return brow[i][1]
nl = [p for p in nl if p[1] >= brow_y_at(nl[0][0] - 3)]
nr = [p for p in nr if p[1] >= brow_y_at(nr[0][0] + 3)]
lb = [p for p in brow if p[0] < nl[0][0]]
rb = [p for p in brow if p[0] > nr[0][0]]
# one continuous outline, left guard tip -> up -> left brow -> nose -> right brow -> down -> right guard tip
outline = L[::-1] + lb + nl + nr[::-1] + rb + R
out = dict(outline=outline, xc=float(xc), y_top=int(y_top), y_tip=int(y_tip), y_bot=int(y_bot),
           left=L, right=R, brow=brow, nose_left=nl, nose_right=nr)
json.dump(out, open('ref2/front_trace.json', 'w'), default=float)

# picture: traced edge on the photo
base = Image.open(SRC).convert('RGB')
CROP = (470, 360, 910, 720); k = 3
z = base.crop(CROP).resize(((CROP[2] - CROP[0]) * k, (CROP[3] - CROP[1]) * k), Image.LANCZOS)
d = ImageDraw.Draw(z)
def line(pts, col=(255, 40, 150)):
    p = [((x - CROP[0]) * k, (y - CROP[1]) * k) for x, y in pts]
    if len(p) > 1:
        d.line(p, fill=col, width=4)
line(outline)
z.save('ref2/front_traced.png')
