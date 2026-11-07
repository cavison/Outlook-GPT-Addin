"""Step-1 sheet: photo, photo with the design's face-opening edge drawn on it, plain shell, 4 views."""
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont
from scipy import ndimage
from skimage.morphology import convex_hull_image
PHOTO = "/root/.claude/uploads/319431bf-dd7d-5dd8-8f43-98ef81b3e188/068c6438-image.jpg"
CROP = (345, 150, 665, 560)
F = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 28)
FS = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 21)
INK = "#1B1F2A"

def trim(path, pad=10):
    im = Image.open(path).convert("RGB")
    a = np.asarray(im).astype(int); m = ((a.max(2) - a.min(2)) <= 3) & (a.min(2) >= 240)
    b = np.array(im); b[m] = 255; im = Image.fromarray(b)
    bb = ImageChops.difference(im, Image.new("RGB", im.size, (255, 255, 255))).getbbox(); im = im.crop(bb)
    o = Image.new("RGB", (im.width + 2 * pad, im.height + 2 * pad), (255, 255, 255)); o.paste(im, (pad, pad)); return o

# design opening edge, from the photo-matched analysis render (same alignment as overlay.py)
a = np.asarray(Image.open("helmet/match/ana_v9.png").convert("RGB")).astype(int)
r_, g_, b_ = a[..., 0], a[..., 1], a[..., 2]
bg = a.min(2) >= 200
mag = (r_ > g_ + 60) & (b_ > g_ + 60)
red = (r_ > 150) & (g_ < 70) & (b_ < 70); grn = (g_ > 150) & (r_ < 90) & (b_ < 90); blu = (b_ > 150) & (r_ < 70) & (g_ < 70)
navy = ~bg & ~mag            # marker dots count as shell
m45 = np.array(np.nonzero(red)[::-1]).mean(1); mfc = np.array(np.nonzero(blu)[::-1]).mean(1)
top_r = np.nonzero(navy.any(1))[0].min()
s = (367.5 - 164.0) / (m45[1] - top_r)
t = np.array([443.0 - s * mfc[0], 367.5 - s * m45[1]])
hull = convex_hull_image(navy | mag)
opening = hull & ~navy
edge = navy & ndimage.binary_dilation(opening, iterations=2) & ~ndimage.binary_erosion(hull, iterations=0) 
edge &= ~ndimage.binary_dilation(~hull, iterations=6)          # drop the outer silhouette
ey, ex = np.nonzero(edge)
px, py = t[0] + ex * s, t[1] + ey * s
# keep the edges you can compare in the photo: the near eye and guard, the nose guard and brow.
# The far guard's outer side and the near guard's back edge (behind the wing) are left out.
keep = (px < 628) & ~((px < 405) & (py > 380))
px, py = px[keep], py[keep]

H = 600
photo = Image.open(PHOTO).convert("RGB").crop(CROP)
k = H / photo.height
photo = photo.resize((int(photo.width * k), H), Image.LANCZOS)
ov = photo.copy(); d = ImageDraw.Draw(ov)
for x, y in zip((px - CROP[0]) * k, (py - CROP[1]) * k):
    d.ellipse((x - 1.6, y - 1.6, x + 1.6, y + 1.6), fill=(0, 230, 255))
r = trim("helmet/sheet/s9_photo.png"); r = r.resize((int(r.width * H / r.height), H), Image.LANCZOS)
views = [trim(f"helmet/sheet/s9_{n}.png") for n in ["front", "34", "side", "back34"]]
vh = 360; views = [v.resize((int(v.width * vh / v.height), vh), Image.LANCZOS) for v in views]
W = max(photo.width * 2 + r.width + 80, sum(v.width for v in views) + 70)
c = Image.new("RGB", (W, 50 + H + 40 + 60 + vh + 20), "white"); d = ImageDraw.Draw(c)
x0 = 20
for img, title in ((photo, "Your photo"), (ov, "New opening drawn on your photo"), (r, "New shell, same viewpoint")):
    d.text((x0, 10), title, font=F, fill=INK); c.paste(img, (x0, 50)); x0 += img.width + 20
d.text((photo.width + 40, 50 + H + 6), "Blue line = the new design's opening edge", font=FS, fill="#4A5160")
x = 20; y = 50 + H + 50
for v, l in zip(views, ["Front", "3/4", "Side", "Back 3/4"]):
    d.text((x + v.width // 2, y), l, font=F, fill=INK, anchor="ma"); c.paste(v, (x, y + 40)); x += v.width + 15
c.save("pkg/step1b_cat_eye.jpg", quality=92); print(c.size)
