# sheet: the stronger feather tabs - cross-section, top view (old vs new), how it prints, strength per feather
import json, pickle, math, numpy as np
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Point, Polygon, box
from shapely import affinity
J = pickle.load(open('ref2/wing2_joints.pkl', 'rb'))
S = json.load(open('ref2/wing2_strength.json'))
FZ, HT, HC, TT, ST, MT = (J[k] for k in ('FZ', 'HT', 'HC', 'TT', 'ST', 'MT'))
NAVY, GOLD, WHITE, AIR = (30, 42, 82), (242, 193, 46), (236, 236, 228), (255, 255, 255)
F = lambda s, b=False: ImageFont.truetype('DejaVuSans-Bold.ttf' if b else 'DejaVuSans.ttf', s)
W, H = 2000, 1560
im = Image.new('RGB', (W, H), (248, 248, 244)); d = ImageDraw.Draw(im)
d.text((40, 24), 'Feather tabs: bigger, stiffer, and printed flat on the bed', font=F(40, True), fill=(20, 20, 20))
NAV2, COL2, GAPC = (46, 62, 120), (120, 140, 190), (255, 255, 255)
dep = next(r for r in S if r['piece'] == 'F1')['new_depth']
def rect(P, x_a, x_b, w_a, w_b, fill, outline=(0, 0, 0), wd=2):
    p1, p2 = P(x_a, w_b), P(x_b, w_a); d.rectangle([min(p1[0], p2[0]), min(p1[1], p2[1]), max(p1[0], p2[0]), max(p1[1], p2[1])], fill=fill, outline=outline, width=wd)
def dim(P, xa, wa, xb, wb, label, anchor='lm', off=(10, 0), col=(200, 30, 30)):
    a_, b_ = P(xa, wa), P(xb, wb); d.line([a_, b_], fill=col, width=3)
    for q in (a_, b_): d.ellipse([q[0] - 4, q[1] - 4, q[0] + 4, q[1] + 4], fill=col)
    m_ = ((a_[0] + b_[0]) / 2 + off[0], (a_[1] + b_[1]) / 2 + off[1])
    d.text(m_, label, font=F(20, True), fill=col, anchor=anchor)

# ---------- panel A: cut through a joint, as assembled ----------
ax, ay, k = 60, 110, 15.0
d.text((ax, ay), 'A  Cut through a joint (feather F1 clicked into the upper collar)', font=F(25, True), fill=(20, 20, 20))
XL, XR = -20.0, dep + 12.0
def PA(x, w): return (ax + 40 + (x - XL) * k, ay + 260 - w * k)
rect(PA, XL, -0.15, FZ - HT, FZ + HT, NAVY)                          # feather
rect(PA, 0.15, XR, -HC, HC, COL2)                                   # collar
rect(PA, 0.15, dep + 0.6, -ST / 2, ST / 2, GAPC)                    # socket
rect(PA, -1.0, dep, -TT / 2, TT / 2, NAVY)                          # tab
d.text(PA(XL + 1, FZ - 0.5), 'feather 6.4 mm', font=F(20, True), fill=(255, 255, 255), anchor='lm')
d.text(PA(dep + 1.5, -3.0), 'collar 8 mm', font=F(20, True), fill=(20, 20, 40), anchor='lm')
d.text(PA(dep * 0.35, 0), 'tab', font=F(20, True), fill=(255, 255, 255), anchor='mm')
dim(PA, dep + 6, -TT / 2, dep + 6, TT / 2, f'{TT:.1f} mm thick (was 2.2)', off=(12, 0))
dim(PA, 0.15, -6.3, dep, -6.3, f'{dep:.0f} mm into the collar (was 16)', anchor='mt', off=(0, 8))
dim(PA, dep + 10.5, ST / 2, dep + 10.5, HC, '', off=(0, 0))
d.text(PA(dep + 11.3, 3.0), f'{HC - ST / 2:.0f} mm wall', font=F(18, True), fill=(200, 30, 30), anchor='lm')
dim(PA, -2.5, FZ + HT, -2.5, HC, f'collar {HC - FZ - HT:.1f} mm proud', anchor='rm', off=(-12, -6))
d.text(PA(XL, 6.2), 'show side', font=F(19, True), fill=(110, 110, 110), anchor='lm')
d.text(PA(XL, -5.4), 'helmet side', font=F(19, True), fill=(110, 110, 110), anchor='lm')
d.text((ax, ay + 400), "The tab is flush with the feather's show face and sits in the middle of the 8 mm collar,\n"
       "with 2 mm of collar above and below it. The collar stands 2.2 mm proud of the feathers\n"
       "on the show side (like the covert feathers over a real wing) and 0.6 mm back on the\n"
       "helmet side. Feathers and collars keep their printed-in colour faces (not drawn here).", font=F(19), fill=(40, 40, 40), spacing=6)

# ---------- panel B: as printed ----------
bx, by, k2 = 60, 660, 15.0
d.text((bx, by), 'B  How a feather prints: show face down, tab on the bed', font=F(25, True), fill=(20, 20, 20))
def PB(x, z): return (bx + 40 + (x + 20) * k2, by + 190 - z * k2)
rect(PB, -20, 0, 0, 6.4, NAVY); rect(PB, -1, dep, 0, TT, NAVY)
d.line([PB(-21, -0.1), PB(dep + 4, -0.1)], fill=(120, 120, 120), width=6)
d.text(PB(-19, -0.8), 'print bed', font=F(19, True), fill=(100, 100, 100), anchor='lt')
d.text(PB(dep * 0.5, TT + 0.8), 'tab', font=F(19, True), fill=(20, 20, 40), anchor='mb')
d.text(PB(-10, 3.2), 'feather (show face down)', font=F(19, True), fill=(255, 255, 255), anchor='mm')
d.text((bx, by + 250), "Before this change the tab sat in the middle of the feather, 1.4 mm above the bed\n"
       "with nothing under it, so it would have printed in mid-air. Now every feather and tip A\n"
       "print with the tab's first layers on the bed: no supports, and the strongest, most\n"
       "accurate layers end up in the tab. Tip B plugs into F9 (not a collar), so its tab must\n"
       "stay hidden in the middle of its thickness; Orca puts a small support pad under it.", font=F(19), fill=(40, 40, 40), spacing=6)

# ---------- panel C: top view of the F1 joint, old vs new ----------
outl, (tg, sk, info) = J['outl'], J['joints']['F1']
inside = tg.intersection(outl['F1']); outside = tg.difference(outl['F1'])
m_in, m_out = np.array(inside.centroid.coords[0]), np.array(outside.centroid.coords[0])
nr0 = m_out - m_in; nr0 /= np.linalg.norm(nr0)
cs_ = np.array(sk.minimum_rotated_rectangle.exterior.coords)[:3]          # the socket's own axes
ax_ = [(cs_[1] - cs_[0]) / np.linalg.norm(cs_[1] - cs_[0]), (cs_[2] - cs_[1]) / np.linalg.norm(cs_[2] - cs_[1])]
nr = max(ax_ + [-a for a in ax_], key=lambda a: a @ nr0); u = np.array([nr[1], -nr[0]])
# mouth: where the tab axis crosses the F1 outline
from shapely.geometry import LineString
axl = LineString([m_out - nr * 40, m_out + nr * 40]).intersection(outl['F1'].boundary)
mouth = np.array(min(getattr(axl, 'geoms', [axl]), key=lambda q: np.linalg.norm(np.array(q.coords[0]) - m_out)).coords[0])
ang = math.degrees(math.atan2(nr[1], nr[0]))
def to_local(g):                                     # tab axis pointing up the page, mouth at the origin
    g = affinity.translate(g, -mouth[0], -mouth[1]); return affinity.rotate(g, 90 - ang, origin=(0, 0))
cx0, cy0, k3 = 1040, 110, 6.0
d.text((cx0, cy0), 'C  F1 joint from the front, collar see-through', font=F(25, True), fill=(20, 20, 20))
ox, oy = cx0 + 450, cy0 + 260
def PC(x, y): return (ox + x * k3, oy - y * k3)
frame = box(-70, -22, 70, 32)
def poly(g, fill, outline=(0, 0, 0), wd=2):
    g = to_local(g).intersection(frame)
    for q in getattr(g, 'geoms', [g]):
        if q.geom_type != 'Polygon' or q.is_empty: continue
        d.polygon([PC(x, y) for x, y in q.exterior.coords], fill=fill, outline=outline, width=wd)
poly(outl['CU'], (200, 208, 228)); poly(outl['F1'], (150, 160, 190)); poly(sk, GAPC); poly(tg, NAVY)
# old tab (v1): 26 wide, 16 deep, slits from 2.5 mm in
old = box(-13, -3, 13, 16)
for s_ in (-1, 1): old = old.difference(box(s_ * 9.4 - 0.4, 2.5, s_ * 9.4 + 0.4, 17))
for q in getattr(old, 'geoms', [old]):
    pts = [PC(x, y) for x, y in q.exterior.coords]
    for i in range(len(pts) - 1):
        a_, b_ = pts[i], pts[i + 1]; L = math.dist(a_, b_); n_ = max(1, int(L / 10))
        for j in range(0, n_, 2):
            d.line([(a_[0] + (b_[0] - a_[0]) * j / n_, a_[1] + (b_[1] - a_[1]) * j / n_), (a_[0] + (b_[0] - a_[0]) * min(j + 1, n_) / n_, a_[1] + (b_[1] - a_[1]) * min(j + 1, n_) / n_)], fill=(225, 40, 40), width=3)
d.text(PC(-68, 30), 'upper collar', font=F(20, True), fill=(60, 70, 110), anchor='lt')
d.text(PC(-12, -19), 'feather F1', font=F(20, True), fill=(255, 255, 255), anchor='lb')
d.text((cx0, cy0 + 420), f"New tab (navy): {info['width']:.0f} mm wide plus rounded root fillets, {info['depth']:.0f} mm deep,\n"
       f"solid across the root; the two snap fingers ({info['finger']:.0f} mm long) are in the far part.\n"
       "Old tab (red dashed): 26 x 16 mm, 2.2 mm thick, with the finger slits\n"
       "starting right at the root - the weak spot.", font=F(19), fill=(40, 40, 40), spacing=6)

# ---------- panel D: strength per feather ----------
gx, gy, gw, gh = 1100, 760, 850, 600
d.text((gx, gy - 40), 'D  Push at the feather tip that the tab root can take', font=F(26, True), fill=(20, 20, 20))
mx = max(r['new_N'] for r in S) * 1.1
bw = gw / len(S)
for yv in range(0, int(mx) + 1, 10):
    yy = gy + gh - yv / mx * gh; d.line([(gx, yy), (gx + gw, yy)], fill=(215, 215, 215)); d.text((gx - 8, yy), f'{yv}', font=F(17), fill=(110, 110, 110), anchor='rm')
for i, r in enumerate(S):
    x = gx + i * bw + 8
    for val, col, off in ((r['old_N'], (220, 90, 90), 0), (r['new_N'], NAVY, bw * 0.4)):
        yy = gy + gh - val / mx * gh
        d.rectangle([x + off, yy, x + off + bw * 0.36, gy + gh], fill=col)
    d.text((x + bw * 0.4, gy + gh + 8), r['piece'], font=F(19, True), fill=(30, 30, 30), anchor='ma')
    d.text((x + bw * 0.4, gy + gh - r['new_N'] / mx * gh - 6), f"x{r['x']:.0f}", font=F(16, True), fill=NAVY, anchor='mb')
d.text((gx, gy + gh + 40), 'newtons (10 N = about 1 kg pressing on the very tip; old = red, new = navy).\nPLA bending stress 40 MPa at the tab root; real breaking point is higher.', font=F(19), fill=(60, 60, 60), spacing=4)
im.save('pkg/step16_feather_tabs.jpg', quality=90)
print('sheet written')
