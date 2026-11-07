"""Brow-band edges round the helmet, from the front and back pictures.
v = height above the brow line as a fraction of the band half-width (same unit as
face_trace.scad).  Angle 0 = front centre, 180 = back centre."""
import json
import numpy as np
from scipy.interpolate import PchipInterpolator
t = json.load(open('ref2/front_trace.json'))
BROW_Y = min(p[1] for p in t['brow'])            # top of the eye openings in the front picture
R0MM = 106.675                                   # trace unit at full size (mm), for the back numbers
r = json.load(open('ref2/band_rims_front.json'))
xs = np.array(r['x']); a = np.array(r['rims'])
sel = xs >= 742                                  # the H hides the top rim nearer the centre
th = np.degrees(np.arcsin((xs[sel] - 689.0) / 188.0))
vtop = (BROW_Y - a[sel, 0]) / 187.0
p = np.polyfit(th, vtop, 2)
front_th = np.arange(0, 66, 3.0)
front_v = np.polyval(p, np.clip(front_th, th.min(), None))
# behind the wings and round the back (from the back picture, perspective removed, in mm)
top_pts = list(zip(front_th, front_v)) + [(100, np.polyval(p, 66) - 22 / R0MM), (130, -15 / R0MM), (180, -41 / R0MM)]
bot_pts = [(62, -0.04), (75, -0.04), (100, -24 / R0MM), (130, -51 / R0MM), (180, -77 / R0MM)]
def table(pts, step=2.0):
    x, y = np.array(pts).T
    f = PchipInterpolator(x, y)
    xx = np.arange(x.min(), 180.0001, step)
    return np.stack([xx, f(xx)], 1)
TOP = table(top_pts); BOT = table(bot_pts)
with open('helmet/band_path.scad', 'w') as f:
    f.write('// Brow-band edges round the helmet, measured from the front and back pictures.\n')
    f.write('// [angle (deg, 0 = front centre, 180 = back centre), height above the brow line as a\n')
    f.write('// fraction of the band half-width (FACE_R0)].  BAND_BOT_V starts at the outer eye\n')
    f.write('// corner; in front of that the band sits on the brow line of the face opening.\n')
    f.write('BAND_TOP_V = [' + ', '.join(f'[{x:.1f}, {y:.4f}]' for x, y in TOP) + '];\n')
    f.write('BAND_BOT_V = [' + ', '.join(f'[{x:.1f}, {y:.4f}]' for x, y in BOT) + '];\n')
print('front top v at 20/45/65 deg:', np.polyval(p, [20.9, 45, 65]).round(3), '-> mm', (np.polyval(p, [20.9, 45, 65]) * R0MM).round(1))
print('top at 100/130/180 mm:', (TOP[[np.argmin(abs(TOP[:,0]-q)) for q in (100,130,180)],1]*R0MM).round(1))
