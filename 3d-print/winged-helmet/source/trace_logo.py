"""Trace a flat 3-color logo (navy outline, white, gold) into OpenSCAD polygons.

Writes an include file with three outline sets, in a unit box (width = 1,
centered on the origin, y up):
  LOGO_SIL   - whole logo silhouette (holes filled)
  LOGO_WHITE - white areas inside the logo
  LOGO_GOLD  - gold areas
Navy is whatever is left: silhouette minus white minus gold.

usage: python trace_logo.py <logo.png> <out.scad> <preview.png>
"""
import sys
import numpy as np
from PIL import Image
from scipy import ndimage
from skimage import measure

src, out_scad, out_png = sys.argv[1:4]
UP = 4            # upsample before contouring, for smooth edges
TOL = 0.6         # polygon simplification tolerance, in original pixels

a = np.asarray(Image.open(src).convert("RGB")).astype(float)
ref = {"navy": (12, 30, 62), "gold": (242, 178, 24), "white": (250, 250, 250)}
d = np.stack([np.linalg.norm(a - np.array(c), axis=2) for c in ref.values()], axis=-1)
lab = d.argmin(-1)                                    # 0 navy, 1 gold, 2 white

# background = white connected to the image border
white = lab == 2
cc, _ = ndimage.label(white)
border = set(np.unique(np.concatenate([cc[0], cc[-1], cc[:, 0], cc[:, -1]]))) - {0}
bg = np.isin(cc, list(border))
sil = ndimage.binary_fill_holes(~bg)
inner_white = white & ~bg
gold = lab == 1

# drop specks
def clean(m, min_px=12):
    l, n = ndimage.label(m)
    sizes = ndimage.sum(m, l, range(1, n + 1))
    return np.isin(l, [i + 1 for i, s in enumerate(sizes) if s >= min_px])

sil, inner_white, gold = clean(sil, 200), clean(inner_white), clean(gold)

ys, xs = np.nonzero(sil)
x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
cx, cy, W = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0)


def contours(mask):
    m = np.pad(mask.astype(float), 2)
    m = ndimage.zoom(m, UP, order=1)
    m = ndimage.gaussian_filter(m, UP * 0.6)
    polys = []
    for c in measure.find_contours(m, 0.5):
        c = measure.approximate_polygon(c, TOL * UP)
        if len(c) < 4:
            continue
        # back to original pixel coords, then unit box (y up)
        py = c[:, 0] / UP - 2
        px = c[:, 1] / UP - 2
        pts = np.stack([(px - cx) / W, -(py - cy) / W], axis=1)
        area = 0.5 * np.sum(pts[:-1, 0] * pts[1:, 1] - pts[1:, 0] * pts[:-1, 1])
        if abs(area) < 2e-5:
            continue
        polys.append(pts[:-1])
    return polys


sets = {"LOGO_SIL": contours(sil), "LOGO_WHITE": contours(inner_white), "LOGO_GOLD": contours(gold)}


def fmt(polys):
    rows = []
    for p in polys:
        rows.append("  [" + ",".join(f"[{x:.4f},{y:.4f}]" for x, y in p) + "]")
    return "[\n" + ",\n".join(rows) + "\n]"


with open(out_scad, "w") as f:
    f.write("// Eagle-head logo, traced from the supplied artwork.\n")
    f.write("// Unit box: 1.0 wide, centred on the origin, y up.  Height / width = "
            f"{(y1 - y0) / W:.3f}\n")
    f.write(f"LOGO_ASPECT = {(y1 - y0) / W:.4f};\n")
    for k, v in sets.items():
        f.write(f"{k} = {fmt(v)};\n")
    f.write("""
// each set is a list of closed outlines; nested outlines are holes (even-odd)
module logo_set(set) {
    pts   = [for (p = set) each p];
    start = [for (i = [0:len(set)-1]) i == 0 ? 0 : len([for (j = [0:i-1]) each set[j]])];
    polygon(pts, [for (i = [0:len(set)-1]) [for (k = [0:len(set[i])-1]) start[i] + k]]);
}
""")

# preview of the traced regions
prev = np.full(a.shape, 255, np.uint8)
prev[sil] = (30, 42, 82)
prev[inner_white] = (245, 245, 245)
prev[gold] = (242, 193, 46)
Image.fromarray(prev).save(out_png)
print({k: (len(v), sum(len(p) for p in v)) for k, v in sets.items()}, "aspect", round((y1 - y0) / W, 3))
