# Concept: one wing as single-colour layers (navy base / white / gold) - geometry in 2D for the picture
import json, re, os, pickle, numpy as np
from shapely.geometry import Polygon, Point, MultiPolygon
from shapely.ops import unary_union
report = []
def log(*a): print(*a)
src = open('wing_build.py').read()
exec(src[src.index('T, MID_T = '):src.index('# ---------- sections ----------')])
def parts(g, min_area=0.0):
    return [q for q in getattr(g, 'geoms', [g]) if q.geom_type == 'Polygon' and q.area > min_area]
# what the face shows now, painter's order (higher levels win)
order = [('WG_L1_NAVY', 'navy'), ('WG_L1_GOLD', 'gold'), ('WG_L1_WHITE', 'white'), ('WG_L2_GOLD', 'gold'), ('WG_L2_WHITE', 'white'),
         ('WG_L3_NAVY', 'navy'), ('WG_L3_GOLD', 'gold')]
V = {'navy': Polygon(), 'gold': Polygon(), 'white': Polygon()}
def paint(g, c):
    for k in V: V[k] = V[k].difference(g)
    V[c] = V[c].union(g)
for n, c in order: paint(WG[n], c)
paint(disc, 'navy'); paint(ring, 'gold'); paint(LOGO['LOGO_WHITE'], 'white'); paint(LOGO['LOGO_GOLD'], 'gold')
plate = WG['WG_PLATE']
for k in V: V[k] = V[k].intersection(plate).buffer(0)
WHITE = V['white'].union(V['gold']).buffer(0.01).buffer(-0.01)        # white sits under every gold piece
GOLD = V['gold'].buffer(0)
wp = parts(WHITE, 4.0); gp = parts(GOLD, 4.0)
print('white pieces', len(wp), 'tiny dropped', len(parts(WHITE)) - len(wp))
print('gold pieces', len(gp), 'tiny dropped', len(parts(GOLD)) - len(gp))
print('white areas cm2', sorted(round(p.area / 100, 1) for p in wp))
print('gold areas cm2', sorted(round(p.area / 100, 1) for p in gp))
pickle.dump(dict(V=V, WHITE=WHITE, GOLD=GOLD, plate=plate, disc=disc, ring=ring, LOGO=LOGO, MED_C=MED_C, MED_R=MED_R), open('ref2/layered_concept.pkl', 'wb'))
