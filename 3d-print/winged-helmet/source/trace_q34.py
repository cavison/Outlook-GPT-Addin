"""Trace the face-opening edge in the 3/4 picture (same rules as trace_front.py)."""
import json
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
SRC = '/root/.claude/uploads/319431bf-dd7d-5dd8-8f43-98ef81b3e188/9821a39f-image.jpg'
im = np.asarray(Image.open(SRC).convert('RGB')).astype(int)
r, g, b = im[..., 0], im[..., 1], im[..., 2]
mx, mn = im.max(2), im.min(2)
gold = ndimage.binary_opening((r > 110) & (r - b > 45), iterations=1)
dark = mx < 45
light = (mn > 150) & (mx - mn < 30)
X0, Y0 = 470, 400                       # zoom-crop origin used while reading the picture

# nose guard: gold blob around zoom (250, 300) -> orig
lab, n = ndimage.label(gold)
cy, cx = Y0 + 125, X0 + 125              # middle of the nose guard (zoom 250, 250)
win = lab[cy - 40:cy + 40, cx - 40:cx + 40]
ids, cnt = np.unique(win[win > 0], return_counts=True)
nose_id = ids[np.argmax(cnt)] if len(ids) else 0
assert nose_id, 'nose guard not found'
nose = lab == nose_id
ys, xs = np.nonzero(nose[Y0 + 60:Y0 + 200, X0 + 60:X0 + 200]); ys += Y0 + 60; xs += X0 + 60
y_tip = ys.max(); x_tip = xs[ys == y_tip].mean()
print('nose tip', x_tip, y_tip)

def scan(y, x, step, lim):
    while lim[0] < x < lim[1] and not gold[y, x]:
        x += step
    return x - step

# brow: bottom of the white rim, column by column, from the far guard to the near guard
brow = []
for x in range(X0 + 40, X0 + 360):
    for i in range(Y0 + 30, Y0 + 160):
        if dark[i:i + 10, x].all() and light[i - 3:i, x].any():
            brow.append((float(x), i - 0.5)); break
bx = np.array([p[0] for p in brow]); by = np.array([p[1] for p in brow])
med = ndimage.median_filter(by, 31, mode='nearest')
brow = [(x, y) for x, y, m in zip(bx, by, med) if abs(y - m) < 3]

# nose guard outline (outer edge of its trim) below the brow
nl, nr = [], []
for y in range(int(min(p[1] for p in brow)), y_tip + 1):
    xs_ = np.nonzero(nose[y])[0]
    if len(xs_):
        nl.append((xs_.min() - 0.5, float(y))); nr.append((xs_.max() + 0.5, float(y)))
def brow_y(x):
    i = int(np.argmin([abs(p[0] - x) for p in brow])); return brow[i][1]
nl = [p for p in nl if p[1] >= brow_y(p[0] - 3)]
nr = [p for p in nr if p[1] >= brow_y(p[0] + 3)]

# near (right) guard: from the nose guard / centre step right until its trim
Rg = []
y = int(brow_y(X0 + 330))
while y < im.shape[0] - 1:
    sx = int(nr[-1][0]) + 5 if y <= y_tip else int(x_tip)
    sx = max(sx, int(nr[min(len(nr) - 1, max(0, y - int(nr[0][1])))][0]) + 5) if y <= y_tip else sx
    x = scan(y, sx, +1, (0, X0 + 420))
    if x >= X0 + 418:
        break
    Rg.append((x + 0.5, float(y))); y += 1
# far (left) guard: step left from the nose guard until its trim
Lg = []
y = int(brow_y(X0 + 60))
while y < im.shape[0] - 1:
    sx = int(nl[min(len(nl) - 1, max(0, y - int(nl[0][1])))][0]) - 5 if y <= y_tip else int(x_tip)
    x = scan(y, sx, -1, (X0 - 60, im.shape[1]))
    if x <= X0 - 58:
        break
    Lg.append((x - 0.5, float(y))); y += 1
lb = [p for p in brow if p[0] < nl[0][0]]
rb = [p for p in brow if p[0] > nr[0][0]]
outline = Lg[::-1] + lb + nl + nr[::-1] + rb + Rg
json.dump(dict(outline=outline, brow=brow, nose_left=nl, nose_right=nr, left=Lg, right=Rg), open('ref2/q34_trace.json', 'w'), default=float)
base = Image.open(SRC).convert('RGB')
CROP = (450, 380, 890, 740); k = 3
z = base.crop(CROP).resize(((CROP[2] - CROP[0]) * k, (CROP[3] - CROP[1]) * k), Image.LANCZOS)
d = ImageDraw.Draw(z)
# the far guard is seen nearly edge-on and can't be traced reliably here (the front picture covers it),
# so draw the nose guard and the near eye and guard only
for seg in (nl, nr[::-1] + rb + Rg):
    d.line([((x - CROP[0]) * k, (y - CROP[1]) * k) for x, y in seg], fill=(255, 40, 150), width=4)
z.save('ref2/q34_traced.png')
print('far guard rows', len(Lg), 'near guard rows', len(Rg))
