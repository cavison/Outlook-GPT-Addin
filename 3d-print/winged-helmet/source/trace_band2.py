"""Trace the brow-band scrollwork from the new front and back pictures.
Each picture's band (right half of the image) is unwrapped onto a grid of
[angle round the helmet (deg, 0 = front centre, 180 = back centre), t] where
t = 0 at the bottom of the top rim and 1 at the top of the bottom rim.
Writes helmet/band_motif2.scad with gold and white outline sets (even-odd)."""
import json
import numpy as np
from PIL import Image
from scipy import ndimage
from skimage import measure
U = '/root/.claude/uploads/319431bf-dd7d-5dd8-8f43-98ef81b3e188/'

def load(f):
    return np.asarray(Image.open(U + f).convert('RGB')).astype(float)

def masks(img):
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    mx, mn = img.max(2), img.min(2)
    gold = (r > 110) & (r - b > 45)
    white = (mn > 165) & (mx - mn < 40)
    return gold, white

def rims(img, x0, x1, ylo, yhi, top_skip=None):
    """per column: (bottom edge of the top rim, top edge of the bottom rim)"""
    _, white = masks(img)
    white = ndimage.binary_opening(white, iterations=1)
    xs, a = [], []
    for x in range(x0, x1):
        ys = np.nonzero(white[ylo:yhi, x])[0] + ylo
        if not len(ys): continue
        runs = [q for q in np.split(ys, np.nonzero(np.diff(ys) > 1)[0] + 1) if len(q) >= 3]
        if len(runs) < 2: continue
        xs.append(x); a.append([runs[0][-1] + 1, runs[-1][0] - 1])
    a = np.array(a, float)
    for k in range(2): a[:, k] = ndimage.median_filter(a[:, k], 9, mode='nearest')
    return np.array(xs), a

def unwrap(img, xc, R, xs, a, th_of_phi, phis, NT=240, t0=0.0, t1=1.0):
    gold, white = masks(img)
    ptop = np.polyfit(xs, a[:, 0], 3); pbot = np.polyfit(xs, a[:, 1], 3)
    xcol = xc + R * np.sin(np.radians(phis))
    yt, yb = np.polyval(ptop, xcol), np.polyval(pbot, xcol)
    ts = np.linspace(t0, t1, NT)
    X = np.broadcast_to(xcol, (NT, len(phis))); Y = yt[None, :] + ts[:, None] * (yb - yt)[None, :]
    G = ndimage.map_coordinates(gold.astype(float), [Y, X], order=1) > 0.5
    Wm = ndimage.map_coordinates(white.astype(float), [Y, X], order=1) > 0.5
    return G, Wm, ts, th_of_phi(phis)

def clean(m, n):
    m = ndimage.binary_opening(m, iterations=1)
    l, k = ndimage.label(m); s = ndimage.sum(m, l, range(1, k + 1))
    return np.isin(l, [i + 1 for i, v in enumerate(s) if v >= n])

def drop(mask, test):
    """remove connected pieces for which test(rows, cols) is true"""
    l, k = ndimage.label(mask)
    for i in range(1, k + 1):
        rr, cc = np.nonzero(l == i)
        if test(rr, cc): mask[l == i] = False
    return mask

def contours(mask, ths, ts):
    m = ndimage.gaussian_filter(np.pad(mask.astype(float), 2), 1.6)
    out = []
    for c in measure.find_contours(m, 0.5):
        c = measure.approximate_polygon(c, 0.6)
        if len(c) < 5: continue
        ti = np.interp(c[:, 0] - 2, np.arange(len(ts)), ts)
        th = np.interp(c[:, 1] - 2, np.arange(len(ths)), ths)
        poly = np.stack([th, ti], 1)[:-1]
        x, y = poly[:, 0], poly[:, 1]
        if 0.5 * abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1))) < 0.05:   # specks (and pin-holes) too small to print
            continue
        out.append(poly)
    return out

sets = {}
# ---- front: image right half = one side of the helmet, angle 0 at the nose-guard centre
F = load('fdb87b20-image.jpg'); XC_F, R_F = 689.0, 188.0
xs, a = rims(F, 742, 868, 385, 530)
phis = np.linspace(9.6, 70.0, 900)                  # from the strap's gold border out to 70 deg
G, Wm, ts, ths = unwrap(F, XC_F, R_F, xs, a, lambda p: p, phis)
G = clean(G, 60); Wm = clean(Wm, 25)
NTg = G.shape[0]
# strap border and the H (left edge, top), rims (white touching top/bottom)
TH, TT = np.meshgrid(ths, ts)
G &= ~(TH < 11.0)                                   # the strap's gold border
G &= ~((TH < 21.0) & (TT < 0.32))                   # the H's leg over the band
G = clean(G, 60)
Wm = drop(Wm, lambda rr, cc: rr.min() <= 2 or rr.max() >= NTg - 3 or cc.min() <= 2 or cc.max() >= Wm.shape[1] - 3)
sets['front_gold'] = contours(G, ths, ts); sets['front_white'] = contours(Wm, ths, ts)
# ---- back: image right half, angle 180 at the back centre (the chevron is drawn separately)
B = load('e0a9281d-image.jpg'); XC_B, R_B = 687.5, 183.0
xs2, a2 = rims(B, 700, 862, 440, 620)
phis2 = np.linspace(14.0, 72.0, 900)
G2, W2, ts2, ths2 = unwrap(B, XC_B, R_B, xs2, a2, lambda p: 180.0 - p, phis2)
G2 = clean(G2, 60); W2 = clean(W2, 25)
TH2, _ = np.meshgrid(ths2, ts2)
G2 &= ~(TH2 > 165.0)                                # the back chevron (drawn on its own)
G2 = clean(G2, 60)
W2 = drop(W2, lambda rr, cc: rr.min() <= 2 or rr.max() >= W2.shape[0] - 3 or cc.min() <= 2)
sets['back_gold'] = contours(G2, ths2, ts2); sets['back_white'] = contours(W2, ths2, ts2)
# ---- the gold V at the back centre: same unwrap, t allowed past the rims
phis3 = np.linspace(0.0, 17.0, 400)
G3, _, ts3, ths3 = unwrap(B, XC_B, R_B, xs2, a2, lambda p: 180.0 - p, phis3, NT=400, t0=-0.3, t1=1.9)
G3 = clean(G3, 200)
l3, k3 = ndimage.label(G3)
keep = l3[np.argmin(np.abs(ts3 - 1.2)), 2]                        # the piece below the band at the centre line
G3 = (l3 == keep) if keep else G3
pv = np.zeros(G3.shape + (3,), np.uint8); pv[:] = (40, 55, 110); pv[G3] = (242, 193, 46)
Image.fromarray(pv).save('ref2/band_unwrap_chevron.png')
sets['back_chevron'] = contours(G3, ths3, ts3)
with open('helmet/band_motif2.scad', 'w') as f:
    f.write('// Brow-band scrollwork traced from the new front and back pictures (one side).\n')
    f.write('// Points are [angle round the helmet in degrees (0 = front centre, 180 = back centre), t],\n')
    f.write('// t = 0 at the bottom of the top rim, 1 at the top of the bottom rim.  Mirror for the other side.\n')
    for k, v in sets.items():
        f.write(f"BAND_{k.upper()} = [\n" + ",\n".join("  [" + ",".join(f"[{p:.3f},{q:.4f}]" for p, q in poly) + "]" for poly in v) + "\n];\n")
print({k: (len(v), sum(len(p) for p in v)) for k, v in sets.items()})
# previews of the unwrapped bands
for name, Gm, Wmm in (('front', G, Wm), ('back', G2, W2)):
    pv = np.zeros(Gm.shape + (3,), np.uint8); pv[:] = (40, 55, 110); pv[Gm] = (242, 193, 46); pv[Wmm] = (250, 250, 250)
    Image.fromarray(pv).resize((Gm.shape[1], Gm.shape[0] * 2)).save(f'ref2/band_unwrap_{name}.png')
json.dump({'front_rims': [xs.tolist(), a.tolist()], 'back_rims': [xs2.tolist(), a2.tolist()]}, open('ref2/band_rims2.json', 'w'))
