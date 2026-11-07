"""Band rims in the front picture, right half (wearer's left as seen... image right).
For each column: top rim (top/bottom edge), bottom rim (top/bottom edge), in photo pixels."""
import json, numpy as np
from PIL import Image
from scipy import ndimage
U = '/root/.claude/uploads/319431bf-dd7d-5dd8-8f43-98ef81b3e188/'
im = np.asarray(Image.open(U + 'fdb87b20-image.jpg').convert('RGB')).astype(int)
r, g, b = im[..., 0], im[..., 1], im[..., 2]; mx, mn = im.max(2), im.min(2)
white = ndimage.binary_opening((mn > 165) & (mx - mn < 40), iterations=1)
dark = mx < 45
gold = (r > 110) & (r - b > 45)
out = {}
for x in range(722, 878):
    col = white[385:530, x]; ys = np.nonzero(col)[0] + 385
    if not len(ys): continue
    runs = [q for q in np.split(ys, np.nonzero(np.diff(ys) > 1)[0] + 1) if len(q) >= 3]
    if len(runs) < 2: continue
    top = runs[0]
    # bottom rim: the white run sitting on the dark opening (or the lowest long run)
    bot = None
    for q in runs[1:]:
        below = dark[q[-1] + 1:q[-1] + 6, x]
        if below.any(): bot = q
    if bot is None: bot = runs[-1]
    if top[0] > 425: continue          # the H covers the top rim near the centre
    out[x] = [int(top[0]), int(top[-1]), int(bot[0]), int(bot[-1])]
xs = sorted(out)
a = np.array([out[x] for x in xs], float)
for k in range(4): a[:, k] = ndimage.median_filter(a[:, k], 7, mode='nearest')
json.dump({'x': xs, 'rims': a.tolist()}, open('ref2/band_rims_front.json', 'w'))
for x, row in list(zip(xs, a))[::10]: print(x, row)
