"""Clean, smooth brow-band scrollwork from the new pictures.
Same unwrapping as trace_band2.py, but: sampled at ~15x the photo's resolution
with smooth colour interpolation, soft colour scores blurred before contouring,
small bumps / specks / pin-holes removed, outlines smoothed along their length,
and the white dots replaced by true circles.
Writes helmet/band_motif3.scad:
  BAND_FRONT_GOLD, BAND_BACK_GOLD : outline sets [angle deg, t] (even-odd)
  BAND_FRONT_DOTS, BAND_BACK_DOTS : [angle deg, t, diameter in band half-widths]"""
import json
import numpy as np
from PIL import Image
from scipy import ndimage
from skimage import measure, morphology
U = '/root/.claude/uploads/319431bf-dd7d-5dd8-8f43-98ef81b3e188/'
RB_PX = 187.0                                      # band half-width in the pictures (px) = 1 unit

def load(f): return np.asarray(Image.open(U + f).convert('RGB')).astype(float)
def sig(x): return 1 / (1 + np.exp(-x))

def rims(img, x0, x1, ylo, yhi):
    mx, mn = img.max(2), img.min(2)
    white = ndimage.binary_opening((mn > 165) & (mx - mn < 40), iterations=1)
    xs, a = [], []
    for x in range(x0, x1):
        ys = np.nonzero(white[ylo:yhi, x])[0] + ylo
        if not len(ys): continue
        runs = [q for q in np.split(ys, np.nonzero(np.diff(ys) > 1)[0] + 1) if len(q) >= 3]
        if len(runs) < 2: continue
        xs.append(x); a.append([runs[0][-1] + 1, runs[-1][0] - 1])
    a = np.array(a, float)
    for k in range(2): a[:, k] = ndimage.median_filter(a[:, k], 9, mode='nearest')
    return np.polyfit(xs, a[:, 0], 3), np.polyfit(xs, a[:, 1], 3)

def unwrap(img, xc, R, ptop, pbot, phis, NT):
    xcol = xc + R * np.sin(np.radians(phis))
    yt, yb = np.polyval(ptop, xcol), np.polyval(pbot, xcol)
    ts = np.linspace(0, 1, NT)
    X = np.broadcast_to(xcol, (NT, len(phis))); Y = yt[None, :] + ts[:, None] * (yb - yt)[None, :]
    ch = [ndimage.map_coordinates(img[..., k], [Y, X], order=3, mode='nearest') for k in range(3)]
    r, g, b = ch
    gold = sig((r - b - 45) / 7) * sig((r - 110) / 8)
    mx = np.maximum(np.maximum(r, g), b); mn = np.minimum(np.minimum(r, g), b)
    white = sig((mn - 165) / 7) * sig((40 - (mx - mn)) / 6)
    # pixel size of one photo pixel on the grid, for blur and cleanup sizes
    px_th = len(phis) / (R * (np.sin(np.radians(phis[-1])) - np.sin(np.radians(phis[0]))))
    px_t = NT / np.mean(yb - yt)
    return gold, white, ts, px_th, px_t

BLUR, MORPH, ALONG, SIMP = 0.35, 0.0, 1.2, 0.10     # photo-pixel units (see sweep in the notes)
def smooth_contours(score, ths, ts, px, min_area_px, hole_px):
    """contour a soft colour score: edges come from the smooth colour interpolation, so only a
    light blur and a light smoothing along the outline are needed; corners and gaps survive"""
    s = ndimage.gaussian_filter(score, (BLUR * px[1], BLUR * px[0])) if BLUR > 0 else score
    m = s > 0.5
    if MORPH > 0:
        rad = max(1, int(round(MORPH * min(px))))
        m = morphology.binary_opening(m, morphology.disk(rad))
    m = morphology.remove_small_objects(m, int(min_area_px * px[0] * px[1]))
    m = morphology.remove_small_holes(m, int(hole_px * px[0] * px[1]))
    s2 = np.where(m, np.maximum(s, 0.5001), np.minimum(s, 0.4999))   # keep the soft edge, drop removed bits
    out = []
    for c in measure.find_contours(np.pad(s2, 2, constant_values=0), 0.5):
        c = c - 2
        d = np.r_[0, np.cumsum(np.hypot(np.diff(c[:, 0]) / px[1], np.diff(c[:, 1]) / px[0]))]
        if d[-1] < 6: continue
        n = max(24, int(d[-1] / 0.35))
        u = np.linspace(0, d[-1], n, endpoint=False)
        cy = np.interp(u, d, c[:, 0]); cx = np.interp(u, d, c[:, 1])
        cy = ndimage.gaussian_filter1d(cy, ALONG, mode='wrap'); cx = ndimage.gaussian_filter1d(cx, ALONG, mode='wrap')
        poly = np.stack([cy, cx], 1)
        poly = measure.approximate_polygon(np.vstack([poly, poly[:1]]), SIMP * min(px))[:-1]
        if len(poly) < 6: continue
        th = np.interp(poly[:, 1], np.arange(len(ths)), ths)
        tt = np.interp(poly[:, 0], np.arange(len(ts)), ts)
        out.append(np.stack([th, tt], 1))
    return out, m

def dots(score, ths, ts, px, field_px):
    s = ndimage.gaussian_filter(score, (0.6 * px[1], 0.6 * px[0])) > 0.5
    l, k = ndimage.label(s); res = []
    for i in range(1, k + 1):
        rr, cc = np.nonzero(l == i)
        if rr.min() <= 3 or rr.max() >= s.shape[0] - 4: continue      # rims
        area_photo_px = len(rr) / (px[0] * px[1])
        if area_photo_px < 12: continue
        d = 2 * np.sqrt(area_photo_px / np.pi) / RB_PX                 # diameter in band half-widths
        res.append([float(np.interp(cc.mean(), np.arange(len(ths)), ths)), float(np.interp(rr.mean(), np.arange(len(ts)), ts)), float(d)])
    return res

out = {}
# front (image right half), angle 0 at the nose-guard centre
F = load('fdb87b20-image.jpg'); XC_F, R_F = 689.0, 188.0
pt, pb = rims(F, 742, 868, 385, 530)
phis = np.linspace(9.6, 70.0, 2400); NT = 520
G, Wt, ts, pth, ptt = unwrap(F, XC_F, R_F, pt, pb, phis, NT)
TH, TT = np.meshgrid(phis, ts)
G = G * ~(TH < 11.0) * ~((TH < 21.0) & (TT < 0.32))
out['BAND_FRONT_GOLD'], mF = smooth_contours(G, phis, ts, (pth, ptt), 30, 8)
out['BAND_FRONT_DOTS'] = dots(Wt * ~((TH < 21.0) & (TT < 0.32)), phis, ts, (pth, ptt), None)
# back (image right half), angle 180 at the back centre; the V there is drawn on its own
B = load('e0a9281d-image.jpg'); XC_B, R_B = 687.5, 183.0
pt2, pb2 = rims(B, 700, 862, 440, 620)
phis2 = np.linspace(14.0, 72.0, 2300)
G2, W2, ts2, pth2, ptt2 = unwrap(B, XC_B, R_B, pt2, pb2, phis2, NT)
TH2, _ = np.meshgrid(180.0 - phis2, ts2)
G2 = G2 * ~(TH2 > 165.0)
g2, mB = smooth_contours(G2, 180.0 - phis2, ts2, (pth2, ptt2), 30, 8)
out['BAND_BACK_GOLD'] = g2
out['BAND_BACK_DOTS'] = dots(W2, 180.0 - phis2, ts2, (pth2, ptt2), None)
with open('helmet/band_motif3.scad', 'w') as f:
    f.write('// Brow-band scrollwork, cleaned and smoothed, from the new front and back pictures (one side).\n')
    f.write('// Outlines: [angle (deg, 0 = front centre, 180 = back centre), t] with t = 0 at the bottom of\n')
    f.write('// the top rim and 1 at the top of the bottom rim.  Dots: [angle, t, diameter in band half-widths].\n')
    for k in ('BAND_FRONT_GOLD', 'BAND_BACK_GOLD'):
        f.write(f"{k} = [\n" + ",\n".join("  [" + ",".join(f"[{p:.3f},{q:.4f}]" for p, q in poly) + "]" for poly in out[k]) + "\n];\n")
    for k in ('BAND_FRONT_DOTS', 'BAND_BACK_DOTS'):
        f.write(f"{k} = [" + ", ".join(f"[{a:.3f},{b:.4f},{c:.4f}]" for a, b, c in out[k]) + "];\n")
print({k: (len(v), sum(len(p) for p in v) if k.endswith('GOLD') else v) for k, v in out.items()})
# vector previews (old trace vs new), drawn at high zoom
from PIL import ImageDraw
def draw(sets, ths_range, fname, dots_=()):
    W_, H_ = 1800, 520
    im = Image.new('RGB', (W_, H_), (40, 55, 110)); d = ImageDraw.Draw(im)
    lo, hi = ths_range
    def P(p): return ((p[0] - lo) / (hi - lo) * W_, p[1] * (H_ - 1))
    for poly in sets:
        d.polygon([P(p) for p in poly], fill=None, outline=(242, 193, 46))
    im2 = Image.new('L', (W_, H_), 0); d2 = ImageDraw.Draw(im2)
    for poly in sets: d2.polygon([P(p) for p in poly], fill=255)
    # even-odd fill: XOR each polygon in turn
    acc = np.zeros((H_, W_), bool)
    for poly in sets:
        t_ = Image.new('L', (W_, H_), 0); ImageDraw.Draw(t_).polygon([P(p) for p in poly], fill=255)
        acc ^= np.asarray(t_) > 0
    a = np.array(im); a[acc] = (242, 193, 46)
    im = Image.fromarray(a); d = ImageDraw.Draw(im)
    for th, t, dia in dots_:
        x, y = P((th, t)); rx = dia * RB_PX * 0.5 * W_ / ((hi - lo) / 60 * 150); ry = rx
        d.ellipse((x - rx, y - ry, x + rx, y + ry), fill=(250, 250, 250))
    im.save(fname)
draw(out['BAND_FRONT_GOLD'], (9.6, 70.0), 'ref2/band3_front.png', out['BAND_FRONT_DOTS'])
