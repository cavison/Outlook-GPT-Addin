"""Wing outline from the side picture.  Outer edges come from the picture (wing vs background);
where the wing lies over the helmet the edge was placed by hand (ZONE); in the lower-back
corner the wing is told apart from the navy dome by colour (gold / white feathers only)."""
import json
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from skimage import measure, morphology
U = '/root/.claude/uploads/319431bf-dd7d-5dd8-8f43-98ef81b3e188/'
im = np.asarray(Image.open(U + 'd47111e3-image.jpg').convert('RGB')).astype(int)
H_, W_ = im.shape[:2]
mx, mn = im.max(2), im.min(2); r, g, b = im[..., 0], im[..., 1], im[..., 2]
bg = (mn > 195) & ((mx - mn) < 22)
lab, n = ndimage.label(bg); border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
obj = ~np.isin(lab, list(border))
gray = ((mx - mn) < 18) & (mx > 110)                     # table shadow
obj &= ~gray
ZONE = [(603, 457), (598, 443), (595, 413), (595, 380), (600, 347), (610, 320), (627, 290), (660, 270), (703, 250),
        (737, 233), (760, 222), (800, 160), (1000, 40), (1130, 20), (1130, 470), (905, 470), (852, 470), (852, 597), (776, 597),
        (772, 620), (752, 650), (738, 672), (731, 684), (700, 705), (545, 705), (545, 690), (573, 663), (593, 630), (610, 597), (620, 573), (625, 547), (632, 513), (638, 468)]
zm = Image.new('L', (W_, H_), 0); ImageDraw.Draw(zm).polygon(ZONE, fill=255); zone = np.asarray(zm) > 0
wing = obj & zone
# lower-back corner: only the gold / white feathers belong to the wing there (the rest is the dome)
sub = np.zeros_like(wing); sub[440:597, 790:853] = True
gold = (r > 110) & (r - b > 45); white = (mn > 165) & ((mx - mn) < 40)
gw = ndimage.binary_closing(gold | white, iterations=2)
wing = np.where(sub, wing & gw, wing)
# the upper wing over the corner (lowest upper feathers) stays: rows above its underside
wing = ndimage.binary_opening(wing, iterations=2)
wing = ndimage.binary_closing(wing, iterations=2)
wing = ndimage.binary_fill_holes(wing)
wing = morphology.remove_small_objects(wing, 400)
lab, n = ndimage.label(wing); s = ndimage.sum(wing, lab, range(1, n + 1)); wing = lab == (np.argmax(s) + 1)
np.save('ref2/wing_mask.npy', wing)
c = max(measure.find_contours(np.pad(ndimage.gaussian_filter(wing.astype(float), 1.0), 1), 0.5), key=len) - 1
c = measure.approximate_polygon(c, 0.7)
json.dump([[float(x), float(y)] for y, x in c], open('ref2/wing_outline_px.json', 'w'))
ov = Image.open(U + 'd47111e3-image.jpg').convert('RGB'); d = ImageDraw.Draw(ov)
d.line([(x, y) for y, x in c], fill=(255, 0, 150), width=3)
ov.crop((440, 0, 1140, 720)).save('ref2/wing_outline_check.png')
ys, xs = np.nonzero(wing)
print('wing bbox x', xs.min(), xs.max(), 'y', ys.min(), ys.max(), 'points', len(c))
