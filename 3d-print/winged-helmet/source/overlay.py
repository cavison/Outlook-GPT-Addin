"""Overlay a photo-matched analysis render's outline on the reference photo.
usage: overlay.py <ana.png> <out.png>
Photo opening = dark region; render: navy shell, magenta lining, light background."""
import sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
PHOTO = '/root/.claude/uploads/319431bf-dd7d-5dd8-8f43-98ef81b3e188/068c6438-image.jpg'
ph = np.asarray(Image.open(PHOTO).convert('RGB')).astype(int)
CX, R = 502.0, 137.0
BROW_Y = 371.0          # photo: band bottom edge just outside the nose guard (x ~ 475)

def photo_open():
    x0, y0, x1, y1 = 360, 330, 660, 545
    v = ph[y0:y1, x0:x1].max(2)
    m = v < 50
    l, n = ndimage.label(m); s = ndimage.sum(m, l, range(1, n + 1))
    big = l == (np.argmax(s) + 1)
    big = ndimage.binary_closing(big, iterations=2)
    full = np.zeros(ph.shape[:2], bool); full[y0:y1, x0:x1] = big
    return full

def render_masks(path):
    a = np.asarray(Image.open(path).convert('RGB')).astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    bg = a.min(2) >= 200
    mag = (r > g + 60) & (b > g + 60)
    navy = ~bg & ~mag
    return navy, mag, bg

navy, mag, bg = render_masks(sys.argv[1])
a = np.asarray(Image.open(sys.argv[1]).convert('RGB')).astype(int)
red = (a[..., 0] > 150) & (a[..., 1] < 70) & (a[..., 2] < 70)
grn = (a[..., 1] > 150) & (a[..., 0] < 90) & (a[..., 2] < 90)
navy &= ~red & ~grn
blu = (a[..., 2] > 150) & (a[..., 0] < 70) & (a[..., 1] < 70)
navy &= ~blu
m45 = np.array(np.nonzero(red)[::-1]).mean(1); m90 = np.array(np.nonzero(grn)[::-1]).mean(1)
mfc = np.array(np.nonzero(blu)[::-1]).mean(1)
top_r = np.nonzero(navy.any(1))[0].min()
# photo anchors: shell top (crest relief removed) 164, brow line at 45 deg 367.5, front centre x 443
s = (367.5 - 164.0) / (m45[1] - top_r)
t = np.array([443.0 - s * mfc[0], 367.5 - s * m45[1]])
print('scale', round(s, 4), 'markers', m45.round(1), m90.round(1))
edge = navy ^ ndimage.binary_erosion(navy)
ey, ex = np.nonzero(edge)
px = t[0] + ex * s; py = t[1] + ey * s
po = photo_open(); pe = po ^ ndimage.binary_erosion(po)
out = Image.fromarray(ph.astype(np.uint8)).convert('RGB')
d = ImageDraw.Draw(out)
for x, y in zip(px, py):
    d.point((x, y), fill=(0, 255, 255))
yy, xx = np.nonzero(pe)
for x, y in zip(xx, yy):
    d.point((x, y), fill=(255, 40, 40))
CROP = tuple(int(v) for v in sys.argv[4].split(",")) if len(sys.argv) > 4 else (330, 150, 700, 560)
out = out.crop(CROP); out = out.resize((out.width * 3, out.height * 3), Image.NEAREST) if len(sys.argv) > 4 else out.resize((740, 820), Image.LANCZOS)
out.save(sys.argv[2])
