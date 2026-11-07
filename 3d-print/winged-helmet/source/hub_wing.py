# Hub-and-feather wing: medallions clamp the covert collars, collars clamp the feather roots
import pickle, numpy as np, math
from shapely.geometry import Point, Polygon, MultiPolygon
from shapely.ops import unary_union
from shapely import affinity
from scipy import ndimage
from skimage.segmentation import watershed
from skimage import measure
from PIL import Image, ImageDraw
d = pickle.load(open('ref2/feather_split.pkl', 'rb')); plate, WG, C = d['plate'], d['WG'], np.array(d['MED_C'])
comps = pickle.load(open('ref2/feather_comps.pkl', 'rb'))
GROUPS = {'P1': [0, 5], 'P2': [1], 'P3': [2], 'P4': [3, 10], 'P5': [4, 7],
          'H1': [14, 15], 'H2': [18], 'H3': [19], 'H4': [22], 'H5': [24], 'H6': [26],
          'CU': [20, 13, 16, 9, 6, 11, 8, 23], 'CL': [12, 17, 21, 25]}
MED_R_OUT = 70.0                      # medallion incl. the ring of cells
MED = Point(*C).buffer(MED_R_OUT, 256)
RES = 0.5
x0, y0, x1, y1 = plate.bounds; x0 -= 5; y0 -= 5; x1 += 5; y1 += 5
W, H = int((x1 - x0) / RES), int((y1 - y0) / RES)
def rast(g, val=1, img=None):
    img = img or Image.new('I', (W, H), 0); dr = ImageDraw.Draw(img)
    for q in getattr(g, 'geoms', [g]):
        if q.geom_type != 'Polygon': continue
        dr.polygon([((x - x0) / RES, (y - y0) / RES) for x, y in q.exterior.coords], fill=val)
        for h in q.interiors: dr.polygon([((x - x0) / RES, (y - y0) / RES) for x, y in h.coords], fill=0)
    return img
mask = np.array(rast(plate.difference(MED))) > 0
markers = np.zeros((H, W), np.int32); names = list(GROUPS)
for k, n in enumerate(names):
    m = np.array(rast(unary_union([comps[i] for i in GROUPS[n]]).buffer(-0.5))) > 0
    markers[m & mask] = k + 1
lab = watershed(np.zeros((H, W)), markers, mask=mask)          # flood fill: borders fall halfway between features
def to_poly(binary):
    cs = measure.find_contours(np.pad(binary, 1).astype(float), 0.5)
    polys = [Polygon([(x0 + (c[1] - 1) * RES, y0 + (c[0] - 1) * RES) for c in cc]).buffer(0) for cc in cs if len(cc) > 10]
    if not polys: return Polygon()
    out = Polygon()
    for p in sorted(polys, key=lambda p: -p.area):
        out = out.symmetric_difference(p)
    return out.buffer(0).simplify(0.3)
REG = {n: to_poly(lab == k + 1).intersection(plate) for k, n in enumerate(names)}
pickle.dump(dict(REG=REG, MED=MED, C=C, plate=plate), open('ref2/hub_regions.pkl', 'wb'))
def fit(g):
    best = None
    for a in range(0, 180, 2):
        b = affinity.rotate(g, a, origin='centroid').bounds; e = (b[2] - b[0], b[3] - b[1])
        if best is None or max(e) < max(best[1]): best = (a, e)
    return best[1]
for n in names:
    e = fit(REG[n]); r0 = REG[n].distance(Point(*C))
    print(f'{n}: visible {REG[n].area/100:6.1f} cm2, fits {e[0]:4.0f} x {e[1]:4.0f} mm, nearest to medallion centre {r0:5.1f} mm, parts {len(getattr(REG[n], "geoms", [1]))}')
