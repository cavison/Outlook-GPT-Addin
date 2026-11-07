import pickle, math, numpy as np, trimesh
src = open('fit_ring_build.py').read(); exec(src[src.index('C, Q = 579.0'):src.index('def revolve')])
A = pickle.load(open('ref2/fit_ring.pkl', 'rb'))
def head_z(y): return BROW_TO_CROWN * max(0, 1 - (abs(y) / (HEAD_A * Q)) ** P) ** (1 / P)
# top strap (helmet frame), lowest material above the centre line
strap = trimesh.util.concatenate([A['arch_front'], A['arch_back']])
rows = []
for y in np.arange(-125, 126, 5.0):
    best = None
    for x in (-6, -3, 0, 3, 6):
        locs, _, _ = strap.ray.intersects_location([[x, y, 0]], [[0, 0, 1]])
        if len(locs): z = locs[:, 2].min(); best = z if best is None else min(best, z)
    if best is not None: rows.append((y, best, best - head_z(y)))
gap = min(rows, key=lambda r: r[2])
print('top strap: smallest gap above the modelled head %.1f mm at y=%.0f (z %.1f)' % (gap[2], gap[0], gap[1]))
for y, z, g in rows:
    if abs(y) in (0, 30, 60, 90, 120) or g < 15: print(f'   y {y:5.0f}  strap z {z:6.1f}  head z {head_z(y):6.1f}  gap {g:5.1f}')
# band at the brow: radial gaps around the head oval (helmet frame, slice at z = 5)
band = trimesh.util.concatenate([A[n] for n in ('front', 'back', 'side_R', 'side_L')])
print('band (5 mm above the brow line): gap from head oval to band inner surface')
for ang in range(0, 360, 15):
    a = math.radians(ang); d = np.array([math.cos(a), math.sin(a), 0.0])
    locs, _, _ = band.ray.intersects_location([[0, 0, 5]], [d])
    if not len(locs): continue
    r_band = np.linalg.norm(locs[:, :2], axis=1).min()
    # head oval along this ray
    r_head = 1 / math.sqrt((math.cos(a) / HEAD_A) ** 2 + (math.sin(a) / (HEAD_A * Q)) ** 2)
    print(f'   angle {ang:3d} ({"R" if ang == 0 else "back" if ang == 90 else "L" if ang == 180 else "front" if ang == 270 else "":5s})  gap {r_band - r_head:5.1f} mm')
