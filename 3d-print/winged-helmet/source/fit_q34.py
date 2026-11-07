"""Find the camera that best matches the 3/4 picture: render the design at several
angles, fit scale+shift of its face-opening edge onto the traced photo edge (near side
and nose guard), keep the best.  usage: fit_q34.py model.scad"""
import json, subprocess, sys, itertools
import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.spatial import cKDTree
from skimage.morphology import convex_hull_image
M = sys.argv[1]
t = json.load(open('ref2/q34_trace.json'))
ph = np.array(t['nose_left'] + t['nose_right'] + [p for p in t['brow'] if p[0] > t['nose_right'][0][0]] + t['right'])
tree_ph = cKDTree(ph)
def design_edge(png):
    a = np.asarray(Image.open(png).convert('RGB')).astype(int)
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    bg = a.min(2) >= 200; mag = (R > 0.7 * B) & (R > G + 20)
    dots = ((R > 150) & (G < 70) & (B < 70)) | ((G > 150) & (R < 90)) | ((B > 150) & (R < 70) & (G < 70))
    navy = ~bg & ~mag
    hull = convex_hull_image(navy | mag)
    mag &= ~dots; navy = ~bg & ~mag                  # marker dots count as shell
    hull = convex_hull_image(navy | mag)
    opening = hull & ~navy
    edge = navy & ndimage.binary_dilation(opening, iterations=2) & ~ndimage.binary_dilation(~hull, iterations=6)
    lab, n = ndimage.label(edge, structure=np.ones((3, 3)))
    if n == 0: return None
    sizes = ndimage.sum(edge, lab, range(1, n + 1)); edge = lab == (np.argmax(sizes) + 1)
    ey, ex = np.nonzero(edge); return np.stack([ex, ey], 1).astype(float)
PH_TIP = ph[np.argmax(ph[:, 1])] if False else np.array(t['nose_left'][-1])
near_brow = np.array([p for p in t['brow'] if p[0] > t['nose_right'][0][0]])
PH_TOP = near_brow[np.argmin(near_brow[:, 1])]
def fit(d, blue_x):
    # anchors: nose-guard tip (lowest edge point near the centre line) and top of the near eye
    near = d[np.abs(d[:, 0] - blue_x) < 60]
    tip = near[np.argmax(near[:, 1])]
    right = d[(d[:, 0] > tip[0] + 20) & (d[:, 1] < tip[1])]
    top = right[np.argmin(right[:, 1])]
    s = (PH_TIP[1] - PH_TOP[1]) / (tip[1] - top[1]); t_ = PH_TIP - s * tip
    tree_d = cKDTree(d)
    for _ in range(20):
        q = (ph - t_) / s; dist, idx = tree_d.query(q); m = d[idx]
        X = np.c_[np.r_[m[:, 0], m[:, 1]], np.r_[np.ones(len(m)), np.zeros(len(m))], np.r_[np.zeros(len(m)), np.ones(len(m))]]
        sol, *_ = np.linalg.lstsq(X, np.r_[ph[:, 0], ph[:, 1]], rcond=None)
        s, t_ = sol[0], sol[1:]
    q = (ph - t_) / s; dist, _ = tree_d.query(q)
    return s, t_, float(np.sqrt(np.mean((dist * s) ** 2)))
best = None
for yaw, el in itertools.product([20, 25, 30, 35, 40], [4, 8, 12, 16, 20]):
    png = f'helmet/match/_fit_{yaw}_{el}.png'
    subprocess.run(['./ana.sh', M, '../' + png[len('helmet/'):] if False else png[len('helmet/'):], str(yaw), str(el)], cwd='helmet', capture_output=True)
    d = design_edge(png)
    if d is None: continue
    # only the visible near side + nose of the design: drop the far side (left of the nose guard)
    a_ = np.asarray(Image.open(png).convert('RGB')).astype(int)
    bm = (a_[..., 2] > 150) & (a_[..., 0] < 70) & (a_[..., 1] < 70)
    s, t_, rms = fit(d, np.nonzero(bm)[1].mean())
    print(yaw, el, 'rms px', round(rms, 2))
    if best is None or rms < best[0]: best = (rms, yaw, el, s, t_.tolist())
print('best', best)
json.dump(best, open('ref2/q34_fit.json', 'w'))
