# quick shaded orthographic views of pieces as currently oriented (bed = bottom line)
import sys, numpy as np, trimesh
from PIL import Image, ImageDraw
src = open('plates_build.py').read()
exec(src[:src.index('# ---------- packing ----------')])
names = sys.argv[2].split(',')
out = sys.argv[1]
def view(meshes, axis, S=1.2, size=260):
    img = Image.new('RGB', (size, size), (250, 250, 250)); d = ImageDraw.Draw(img)
    # axis: 'front' looks along +y (x right, z up); 'side' looks along -x (y right, z up); 'top' (x right, y up)
    allv = np.vstack([m.vertices for m, _ in meshes])
    if axis == 'front': u, w, dep, vd = 0, 2, 1, np.array([0, 1, 0])
    elif axis == 'side': u, w, dep, vd = 1, 2, 0, np.array([-1, 0, 0])
    else: u, w, dep, vd = 0, 1, 2, np.array([0, 0, -1])
    cu = (allv[:, u].min() + allv[:, u].max()) / 2; cw = allv[:, w].min()
    if axis == 'top': cw = (allv[:, w].min() + allv[:, w].max()) / 2
    tris = []
    for m, c in meshes:
        n = m.face_normals; vis = (n @ -vd) > 0
        sh = np.clip(0.35 + 0.65 * np.abs(n @ np.array([0.3, -0.5, 0.8]) / np.linalg.norm([0.3, -0.5, 0.8])), 0, 1)
        T = m.vertices[m.faces]
        depth = (T @ vd).mean(1)
        for t, s, dd in zip(T[vis], sh[vis], depth[vis]):
            tris.append((dd, t, tuple(int(k * s) for k in RGB[c])))
    tris.sort(key=lambda x: -x[0])
    base = size - 15 if axis != 'top' else size / 2
    for _, t, col in tris:
        d.polygon([(size / 2 + (q[u] - cu) * S, base - (q[w] - cw) * S) for q in t], fill=col)
    if axis != 'top': d.line([(0, base), (size, base)], fill=(200, 0, 0))
    return img
tiles = []
for nm in names:
    p = [q for q in P if q['name'] == nm][0]
    parts = oriented(p)
    ext = np.ptp(np.vstack([m.vertices for m, _ in parts]), 0).max()
    S = 230 / ext
    row = Image.new('RGB', (3 * 265, 285), (255, 255, 255)); dr = ImageDraw.Draw(row)
    for j, ax in enumerate(('front', 'side', 'top')):
        row.paste(view(parts, ax, S), (j * 265, 22))
    dr.text((5, 4), f"{nm}  ({p['orient']})", fill=(0, 0, 0))
    tiles.append(row)
sheet = Image.new('RGB', (3 * 265, 285 * len(tiles)), (255, 255, 255))
for k, t in enumerate(tiles): sheet.paste(t, (0, 285 * k))
sheet.save(out)
