"""Trace the brow-band scrollwork from the reference photo.

The band in the photo is seen at an angle on a round helmet, so each image
column is mapped back to its angle around the helmet (undoing the
foreshortening), and each column is stretched between the band's two white
rims (undoing the band's curve).  Output coordinates:
   phi = angle around the helmet in degrees (0 = front centre, + = toward the right side)
   t   = 0 at the top of the band field, 1 at the bottom
usage: python trace_band.py <photo> <out.scad> <preview.png>
"""
import sys
import numpy as np
from PIL import Image
from scipy import ndimage
from skimage import measure

src, out_scad, out_png = sys.argv[1:4]
img = np.asarray(Image.open(src).convert("RGB")).astype(float)

# camera model: helmet silhouette centre / radius in the photo, and where the front centre sits
CX, R = 502.0, 137.0
FRONT = np.degrees(np.arcsin((443.0 - CX) / R))       # angle offset of the front centre

# rim edges found by scanning the photo (orig pixel coords)
X0, Y0, U = 455, 300, 8
rims = np.load("trace/band_rims.npz")
xs = rims["xs"] / U + X0
top = ndimage.median_filter(rims["top"] / U + Y0, 9)
bot = ndimage.median_filter(rims["bot"] / U + Y0, 9)
ptop = np.polyfit(xs, top, 2)
pbot = np.polyfit(xs, bot, 3)

PHI0, PHI1, NP = 12.0, 78.0, 1320                      # output columns (0.05 deg each)
NT = 260                                                # output rows
phis = np.linspace(PHI0, PHI1, NP)
ts = np.linspace(0, 1, NT)
xcol = CX + R * np.sin(np.radians(phis + FRONT))
yt, yb = np.polyval(ptop, xcol) + 1.2, np.polyval(pbot, xcol) - 1.2   # stay inside the rims
X = np.broadcast_to(xcol, (NT, NP))
Y = yt[None, :] + ts[:, None] * (yb - yt)[None, :]

def sample(ch):
    return ndimage.map_coordinates(img[..., ch], [Y, X], order=1)

r, g, b = sample(0), sample(1), sample(2)
mx = np.maximum(np.maximum(r, g), b); mn = np.minimum(np.minimum(r, g), b)
sat = (mx - mn) / (mx + 1e-6); val = mx / 255
gold = (r > 140) & (g > 110) & (b < 125) & (sat > 0.33)
white = (val > 0.70) & (sat < 0.25)
# keep the motif only: drop the keystone border at the far left and specks
gold &= (phis[None, :] > 16.5)
def clean(m, n=60):
    m = ndimage.binary_opening(m, iterations=1)
    l, k = ndimage.label(m)
    s = ndimage.sum(m, l, range(1, k + 1))
    return np.isin(l, [i + 1 for i, v in enumerate(s) if v >= n])
gold = ndimage.binary_closing(gold, iterations=2)
white &= (phis[None, :] > 17.0) & (ts[:, None] > 0.25)       # drop a piece of the H outline
gold, white = clean(gold, 400), clean(white, 120)
holes = ndimage.binary_fill_holes(gold) & ~gold
hl, hn = ndimage.label(holes)
hs = ndimage.sum(holes, hl, range(1, hn + 1))
gold |= np.isin(hl, [i + 1 for i, v in enumerate(hs) if v < 250])     # fill pin-holes

def contours(mask):
    m = ndimage.gaussian_filter(np.pad(mask.astype(float), 2), 2.4)
    polys = []
    for c in measure.find_contours(m, 0.5):
        c = measure.approximate_polygon(c, 0.8)
        if len(c) < 5:
            continue
        t = (c[:, 0] - 2) / (NT - 1)
        ph = PHI0 + (c[:, 1] - 2) / (NP - 1) * (PHI1 - PHI0)
        polys.append(np.stack([ph, t], 1)[:-1])
    return polys

sets = {"MOTIF_GOLD": contours(gold), "MOTIF_WHITE": contours(white)}
with open(out_scad, "w") as f:
    f.write("// Brow-band scrollwork traced from the reference photo (right-hand side).\n")
    f.write("// Points are [angle around the helmet in degrees, t] with t = 0 at the top of the band, 1 at the bottom.\n")
    for k, v in sets.items():
        f.write(f"{k} = [\n" + ",\n".join("  [" + ",".join(f"[{p:.3f},{q:.4f}]" for p, q in poly) + "]" for poly in v) + "\n];\n")
prev = np.zeros((NT, NP, 3), np.uint8); prev[:] = (30, 42, 82)
for k, col in (("MOTIF_GOLD", (242, 193, 46)), ("MOTIF_WHITE", (250, 250, 250))):
    from skimage.draw import polygon as fillpoly
    for poly in sets[k]:
        rr, cc = fillpoly(poly[:, 1] * (NT - 1), (poly[:, 0] - PHI0) / (PHI1 - PHI0) * (NP - 1), prev.shape[:2])
        prev[rr, cc] = col if k == "MOTIF_WHITE" or prev[rr, cc].mean() < 100 else (30, 42, 82)
Image.fromarray(prev).resize((NP, NT * 2)).save(out_png)
print({k: (len(v), sum(len(p) for p in v)) for k, v in sets.items()})
