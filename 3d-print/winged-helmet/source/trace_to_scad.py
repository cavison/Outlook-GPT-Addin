"""Turn the face-opening trace from the front picture into a model outline.
Coordinates are normalised by the band's half-width in the photo (187 px), so the
model can scale them to any head size: u = sideways (0 = centre, + = wearer's right
as seen from the front), v = up from the brow line (the top of the eye openings)."""
import json
import numpy as np
from scipy import ndimage
from skimage.measure import approximate_polygon
t = json.load(open('ref2/front_trace.json'))
XC = 689.0; RB = 187.0
nl, nr = np.array(t['nose_left']), np.array(t['nose_right'])
brow = np.array(t['brow']); L, R = np.array(t['left']), np.array(t['right'])
brow_top = brow[:, 1].min()
# each half runs: nose tip -> up the nose guard side -> along the brow -> down the guard -> guard tip
right = np.concatenate([nr[::-1], brow[brow[:, 0] > nr[0, 0]], R])
left = np.concatenate([nl[::-1], brow[brow[:, 0] < nl[0, 0]][::-1], L])
def norm(p, sgn):
    return np.stack([sgn * (p[:, 0] - XC) / RB, (brow_top - p[:, 1]) / RB], 1)
def resample(p, n=400):
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))]
    s = np.linspace(0, d[-1], n)
    return np.stack([np.interp(s, d, p[:, 0]), np.interp(s, d, p[:, 1])], 1)
a, b = resample(norm(right, 1)), resample(norm(left, -1))
print('left/right mismatch (max, as % of band half-width):', round(100 * np.abs(a - b).max(), 1))
half = (a + b) / 2
half[:, 0] = ndimage.gaussian_filter1d(half[:, 0], 2, mode='nearest')
half[:, 1] = ndimage.gaussian_filter1d(half[:, 1], 2, mode='nearest')
half[0, 0] = 0.0                                          # nose tip on the centre line
half = approximate_polygon(half, 0.0025)
print('points', len(half), 'nose tip v', round(half[0, 1], 3), 'guard tip', half[-1].round(3))
with open('helmet/face_trace.scad', 'w') as f:
    f.write('// Face-opening edge traced from the straight-on front picture (right half).\n')
    f.write('// [u, v]: u = sideways from the centre, v = up from the brow line, both as a\n')
    f.write('// fraction of the band\'s half-width.  Runs nose-guard tip -> up the nose guard ->\n')
    f.write('// along the brow -> down the cheek guard -> guard tip.\n')
    f.write('FACE_HALF = [' + ', '.join(f'[{u:.4f}, {v:.4f}]' for u, v in half) + '];\n')
json.dump(half.tolist(), open('ref2/face_half.json', 'w'))

# brow part (for the band and trim later): from where it leaves the nose guard to the outer eye corner
i0 = next(i for i in range(1, len(half)) if half[i, 0] > half[:i, 0].max() + 0.02 and half[i, 1] > -0.2)
i1 = max(i for i in range(len(half)) if half[i, 1] > -0.06)
brow_uv = half[i0 - 1:i1 + 1]
nose_hw = half[1:i0, 0].max()
with open('helmet/face_trace.scad', 'a') as f:
    f.write('// the brow part of it, sorted by u, and the nose guard half-width at its top\n')
    f.write('FACE_BROW = [' + ', '.join(f'[{u:.4f}, {v:.4f}]' for u, v in brow_uv) + '];\n')
    f.write(f'FACE_NOSE_HW = {nose_hw:.4f};\n')
print('brow', brow_uv.round(3).tolist(), 'nose hw', round(nose_hw, 3))
