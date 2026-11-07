"""Draw wing feather layouts flat (PIL) for quick review.  draw(scheme) -> Image"""
import pickle, numpy as np
from PIL import Image, ImageDraw
D = pickle.load(open('ref2/wing_feathers.pkl', 'rb'))
NAVY, GOLD, WHITE = (30, 42, 82), (242, 193, 46), (246, 246, 240)
S = 2.4; U0, V0 = -75, 250            # mm -> px
def P(x, y): return ((x - U0) * S, (V0 - y) * S)
def fill(d, geom, col):
    if geom is None or geom.is_empty: return
    for g in (geom.geoms if hasattr(geom, 'geoms') else [geom]):
        if g.geom_type != 'Polygon': continue
        d.polygon([P(*q) for q in g.exterior.coords], fill=col)
        for h in g.interiors: d.polygon([P(*q) for q in h.coords], fill=(255, 255, 255, 0))
def draw(scheme, debug=False):
    im = Image.new('RGB', (int(345 * S), int(400 * S)), 'white'); d = ImageDraw.Draw(im)
    fill(d, D['WING'], scheme.get('groove', NAVY))
    for kind in ('PRIM', 'HANG'):
        for i, f in enumerate(D[kind]):
            if f is None: continue
            cols = scheme[kind](i, len(D[kind]))
            for part in ('full', 'inner', 'margin', 'shaft'):
                if part in cols: fill(d, f[part], cols[part])
    for kind in ('COV2', 'COV1'):
        for i, g in enumerate(D[kind]):
            cols = scheme[kind](i)
            fill(d, g, cols['full'])
            if 'inner' in cols: fill(d, g.buffer(-4.5, join_style=1), cols['inner'])
    fill(d, D['EAGLE'], scheme.get('eagle', (150, 150, 150)))
    if debug:
        for kind in ('PRIM', 'HANG'):
            for i, f in enumerate(D[kind]):
                if f: x, y = f['full'].centroid.coords[0]; d.text(P(x, y), f'{kind[0]}{i}', fill=(255, 0, 0))
    return im
