"""Trace the front H from the straight-on front picture: gold letter, white outline width,
navy outline width.  The letter is made exactly symmetric with straight edges.
Coordinates: u sideways, v up from the brow line, in band half-widths (as face_trace.scad)."""
import json
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from skimage import measure
U = '/root/.claude/uploads/319431bf-dd7d-5dd8-8f43-98ef81b3e188/'
im = np.asarray(Image.open(U + 'fdb87b20-image.jpg').convert('RGB')).astype(float)
XC, RB = 689.0, 187.0
BROW_Y = min(p[1] for p in json.load(open('ref2/front_trace.json'))['brow'])
X0, Y0, X1, Y1 = 610, 285, 770, 440
UP = 8
ys = np.linspace(Y0, Y1, (Y1 - Y0) * UP); xs = np.linspace(X0, X1, (X1 - X0) * UP)
YY, XX = np.meshgrid(ys, xs, indexing='ij')
ch = [ndimage.map_coordinates(im[..., k], [YY, XX], order=3) for k in range(3)]
r, g, b = ch; mx = np.maximum(np.maximum(r, g), b); mn = np.minimum(np.minimum(r, g), b)
sig = lambda x: 1 / (1 + np.exp(-x))
gold_s = sig((r - b - 45) / 7) * sig((r - 110) / 8)
white_s = sig((mn - 165) / 7) * sig((40 - (mx - mn)) / 6)
dark_s = sig((70 - mx) / 6)
gold = ndimage.gaussian_filter(gold_s, UP * 0.5) > 0.5
lab, n = ndimage.label(gold); s = ndimage.sum(gold, lab, range(1, n + 1)); gold = lab == (np.argmax(s) + 1)
gold = ndimage.binary_fill_holes(gold)
# outline widths: from the gold edge outwards, how far white continues, then dark (navy edge)
dt = ndimage.distance_transform_edt(~gold) / UP            # photo px from the gold
white = ndimage.gaussian_filter(white_s, UP * 0.4) > 0.5
dark = ndimage.gaussian_filter(dark_s, UP * 0.4) > 0.5
wd = [dt[white & (dt < 8)].max()]
# white outline width: 90th percentile of white distances among white pixels touching the gold region band
wvals = dt[white & (dt > 0) & (dt < 8)]
print('white outline px: median %.2f  p90 %.2f' % (np.median(wvals), np.percentile(wvals, 90)))
dvals = dt[dark & (dt > np.percentile(wvals, 90)) & (dt < 12)]
print('navy edge px: p10 %.2f  p90 %.2f' % (np.percentile(dvals, 10), np.percentile(dvals, 90)))
# gold outline -> polygon, straight edges
c = max(measure.find_contours(np.pad(gold.astype(float), 2), 0.5), key=len) - 2
poly = measure.approximate_polygon(c, UP * 0.9)
P = np.stack([(X0 + poly[:, 1] / UP - XC) / RB, (BROW_Y - (Y0 + poly[:, 0] / UP)) / RB], 1)
# symmetrize: right half (u >= 0) mirrored onto the left; snap near-horizontal / vertical edges
def snap(Q, tol=0.06):
    Q = Q.copy()
    for _ in range(3):
        for i in range(len(Q)):
            j = (i + 1) % len(Q); d = Q[j] - Q[i]
            if abs(d[1]) < tol * abs(d[0]): m = (Q[i, 1] + Q[j, 1]) / 2; Q[i, 1] = Q[j, 1] = m
            elif abs(d[0]) < tol * abs(d[1]): m = (Q[i, 0] + Q[j, 0]) / 2; Q[i, 0] = Q[j, 0] = m
    return Q
L = P.copy(); L[:, 0] = -L[:, 0]
both = np.vstack([P, L])
right = P[P[:, 0] >= 0]
print('H gold extent u %.3f..%.3f v %.3f..%.3f' % (P[:, 0].min(), P[:, 0].max(), P[:, 1].min(), P[:, 1].max()))
json.dump({'poly': P.tolist(), 'white_px': float(np.percentile(wvals, 90)),
           'navy_px': float(np.percentile(dvals, 90)), 'brow_y': BROW_Y}, open('ref2/H_trace.json', 'w'))
# preview
pv = Image.fromarray(np.uint8(np.dstack([r, g, b]).clip(0, 255))).convert('RGB')
d = ImageDraw.Draw(pv)
d.line([(q[1], q[0]) for q in np.vstack([poly, poly[:1]])], fill=(255, 0, 120), width=5)
pv.resize((pv.width // 2, pv.height // 2)).save('ref2/H_trace.png')
print('poly points', len(P))

# ---- measure a clean parametric H from the gold mask (both halves averaged) ----
def to_u(col): return (X0 + col / UP - XC) / RB
def to_v(row): return (BROW_Y - (Y0 + row / UP)) / RB
rows = np.nonzero(gold.any(1))[0]; top, bot = rows.min(), rows.max()
def spans(row):
    x = np.nonzero(gold[row])[0]
    if not len(x): return []
    runs = np.split(x, np.nonzero(np.diff(x) > 1)[0] + 1)
    return [(to_u(q[0] - 0.5), to_u(q[-1] + 0.5)) for q in runs]
prof = []
for row in range(top, bot + 1, 2):
    sp = spans(row)
    if len(sp) == 1: kind = 'bar'; w_out = (sp[0][1] - sp[0][0]) / 2; w_in = 0
    elif len(sp) == 2: kind = 'legs'; w_out = (sp[1][1] - sp[0][0]) / 2; w_in = (sp[1][0] - sp[0][1]) / 2
    else: continue
    prof.append((to_v(row), kind, w_out, w_in))
prof = np.array([(v, 1 if k == 'bar' else 0, wo, wi) for v, k, wo, wi in prof])
bar = prof[prof[:, 1] == 1]
print('crossbar v %.3f..%.3f' % (bar[:, 0].min(), bar[:, 0].max()))
for v, k, wo, wi in prof[::6]: print('v %.3f %s out %.3f in %.3f' % (v, 'bar ' if k else 'legs', wo, wi))
