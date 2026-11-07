"""Front-view review: the photo's traced opening (pink) vs the current design's opening (blue)."""
import json, sys, numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from skimage.morphology import convex_hull_image
a = np.asarray(Image.open(sys.argv[1] if len(sys.argv) > 1 else 'helmet/match/ana_v9_front.png').convert('RGB')).astype(int)
R, G, B = a[..., 0], a[..., 1], a[..., 2]
bg = a.min(2) >= 200; mag = (R > 0.7 * B) & (R > G + 20)      # lining, incl. its shaded parts
navy = ~bg & ~mag
grn = (G > 150) & (R < 90) & (B < 90)
gy = int(np.nonzero(grn)[0].mean())
row = np.nonzero(navy[gy])[0]; cx, hw = (row.min() + row.max()) / 2, (row.max() - row.min()) / 2
# photo: lower white rim of the band runs from x 503 to 877; its ends sit at y 476
s = 187.0 / hw; tx = 690 - cx * s; ty = 476 - gy * s
hull = convex_hull_image(navy | mag)
opening = hull & ~navy
edge = navy & ndimage.binary_dilation(opening, iterations=2) & ~ndimage.binary_dilation(~hull, iterations=6)
edge &= (np.arange(edge.shape[0]) > 0)[:, None]
lab, n = ndimage.label(edge, structure=np.ones((3, 3)))
sizes = ndimage.sum(edge, lab, range(1, n + 1))
edge = lab == (np.argmax(sizes) + 1)                    # the opening outline is one connected loop
red = (R > 150) & (G < 70) & (B < 70)
for m_ in (red, grn):                                    # drop the line where it bends round a marker dot
    if m_.any():
        my, mx = np.array(np.nonzero(m_)).mean(1)
        yy, xx = np.mgrid[:edge.shape[0], :edge.shape[1]]
        edge &= (yy - my) ** 2 + (xx - mx) ** 2 > 14 ** 2
ey, ex = np.nonzero(edge)
px, py = tx + ex * s, ty + ey * s
keep = py > 440                      # the opening only
px, py = px[keep], py[keep]
# line the two up at the brow: top of the design's opening -> top of the photo's opening
t0 = json.load(open('ref2/front_trace.json'))
py += min(p[1] for p in t0['brow']) - py.min()
photo = Image.open('/root/.claude/uploads/319431bf-dd7d-5dd8-8f43-98ef81b3e188/fdb87b20-image.jpg').convert('RGB')
CROP = (470, 360, 910, 720); k = 3
z = photo.crop(CROP).resize(((CROP[2] - CROP[0]) * k, (CROP[3] - CROP[1]) * k), Image.LANCZOS)
z = Image.blend(z, Image.new('RGB', z.size, 'white'), 0.45)
d = ImageDraw.Draw(z)
for x, y in zip((px - CROP[0]) * k, (py - CROP[1]) * k):
    d.ellipse((x - 2.2, y - 2.2, x + 2.2, y + 2.2), fill=(20, 110, 255))
t = json.load(open('ref2/front_trace.json'))
d.line([((x - CROP[0]) * k, (y - CROP[1]) * k) for x, y in t['outline']], fill=(255, 40, 150), width=5)
z.save(sys.argv[2] if len(sys.argv) > 2 else 'ref2/review_front_overlay.png')
print('scale', round(s, 3))
