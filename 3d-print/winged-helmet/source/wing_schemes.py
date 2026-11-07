"""Three colour schemes on the same feather layout (navy / gold / white only)."""
import pickle, numpy as np
from PIL import Image, ImageDraw, ImageFont
from wing_draw import P, S, fill, D
NAVY, GOLD, WHITE = (30, 42, 82), (242, 193, 46), (246, 246, 240)
EAGLE_PH = (205, 205, 205)
def wing_image(paint):
    im = Image.new('RGB', (int(345 * S), int(400 * S)), 'white'); d = ImageDraw.Draw(im)
    fill(d, D['WING'], NAVY)                          # navy base plate shows in the grooves
    paint(d)
    fill(d, D['EAGLE'], EAGLE_PH)
    x, y = D['EAGLE'].centroid.coords[0]
    d.text(P(x - 14, y + 4), 'eagle', fill=(110, 110, 110))
    return im
def cov(d, row, body, rim=None, rim_w=4.5):
    for g in D[row]:
        fill(d, g, rim if rim else body)
        if rim: fill(d, g.buffer(-rim_w, join_style=1), body)
# A: bright gold wing - gold feathers, white trailing edges, navy shafts; navy coverts rimmed gold
def scheme_A(d):
    for f in D['PRIM'] + D['HANG']:
        if f is None: continue
        fill(d, f['full'], GOLD); fill(d, f['edge_lo'], WHITE); fill(d, f['shaft'], NAVY)
    cov(d, 'COV2', NAVY, GOLD); cov(d, 'COV1', GOLD, NAVY, 3.5)
# B: dipped tips - navy feathers with gold tips (like a real bird's darker base), white shafts
def scheme_B(d):
    for f in D['PRIM'] + D['HANG']:
        if f is None: continue
        fill(d, f['full'], NAVY); fill(d, f['tipzone'], GOLD); fill(d, f['shaft'], WHITE)
    cov(d, 'COV2', GOLD, WHITE, 3.5); cov(d, 'COV1', NAVY, GOLD)
# C: two-tone vanes - each feather gold on top, navy below, split along a white shaft; gold coverts rimmed navy
def scheme_C(d):
    for f in D['PRIM']:
        if f is None: continue
        fill(d, f['full'], NAVY); fill(d, f['upper'], GOLD); fill(d, f['shaft'], WHITE)
    for f in D['HANG']:
        if f is None: continue
        fill(d, f['full'], GOLD); fill(d, f['edge_lo'], WHITE); fill(d, f['shaft'], NAVY)
    cov(d, 'COV2', GOLD, NAVY, 3.5); cov(d, 'COV1', NAVY, GOLD)
if __name__ == '__main__':
    for n, fn in (('A', scheme_A), ('B', scheme_B), ('C', scheme_C)):
        wing_image(fn).save(f'ref2/wing_scheme_{n}.png')
    print('ok')
