# sheet for the fit-test rings: to-scale top view (helmet inside vs head), joint detail, renders, how to test
import pickle, math, numpy as np, trimesh
from PIL import Image, ImageDraw, ImageFont
exec(open('wing_build.py').read().split("if __name__ == '__main__':")[0])
src = open('fit_ring_build.py').read()
exec(src[src.index('C, Q = 579.0'):src.index('def revolve')])           # sizing constants
A = pickle.load(open('ref2/fit_ring.pkl', 'rb'))
F = lambda s, b=False: ImageFont.truetype('DejaVuSans-Bold.ttf' if b else 'DejaVuSans.ttf', s)
NAVY, GOLD, WHITE, INK, MUT, RED = (30, 42, 82), (242, 193, 46), (236, 236, 228), (25, 28, 38), (90, 95, 110), (200, 30, 30)
W, Hh = 2200, 1300
im = Image.new('RGB', (W, Hh), (248, 248, 244)); d = ImageDraw.Draw(im)
d.text((40, 24), 'Fit test: the helmet\'s inside, on your bare head', font=F(40, True), fill=INK)
d.text((40, 76), 'The band and the top strap are exactly the inside of the helmet as built for a 579 mm (7 1/4) head. Plate 1 band ~3 h 20 min, plate 2 strap ~1 h 15 min, 93 g in all.', font=F(22), fill=MUT)
def section(t, z):
    m = to_m(t); cs = m.slice(z)
    return [np.array(r) for r in cs.to_polygons() if len(r) > 2]
# ---------- A: to-scale top view (own canvas) ----------
pa = Image.new('RGB', (700, 860), (248, 248, 244)); da = ImageDraw.Draw(pa)
k = 2.45; cx, cy = 350, 400
def P(x, y): return (cx + x * k, cy - y * k)
col = {'front': NAVY, 'back': NAVY, 'side_R': GOLD, 'side_L': GOLD}
for n, c in col.items():
    for r in section(A[n], 5.0): da.polygon([P(x, y) for x, y in r], fill=c, outline=c)
ang = np.linspace(0, 2 * math.pi, 240)
oval = [(HEAD_A * math.cos(a_), HEAD_A * Q * math.sin(a_)) for a_ in ang]
for i in range(0, len(oval) - 1, 2): da.line([P(*oval[i]), P(*oval[i + 1])], fill=RED, width=3)
da.line([P(-RI, 0), P(RI, 0)], fill=(150, 150, 150), width=1); da.line([P(0, -RI * K), P(0, RI * K)], fill=(150, 150, 150), width=1)
da.text(P(-RI + 5, 3), f'inside {2 * RI:.0f} mm wide', font=F(17, True), fill=INK, anchor='lb')
da.text(P(3, RI * K - 30), f'inside {2 * RI * K:.0f}\nmm long', font=F(17, True), fill=INK, anchor='la')
da.text(P(0, 40), f'your head (red dashes)\n{2 * HEAD_A:.0f} x {2 * HEAD_A * Q:.0f} mm', font=F(17, True), fill=RED, anchor='mm', align='center')
da.text(P(-(HEAD_A + RI) / 2, -18), f'{SIDE_PAD:.0f}\nmm', font=F(16, True), fill=MUT, anchor='mm', align='center')
da.text(P(18, -(HEAD_A * Q + RI * K) / 2), f'{FB_PAD:.0f} mm', font=F(16, True), fill=MUT, anchor='lm')
da.text(P(0, -RI * K - 16), 'FRONT (face side)', font=F(19, True), fill=INK, anchor='mt')
da.text(P(0, RI * K + 16), 'BACK', font=F(19, True), fill=INK, anchor='mb')
da.text(P(RI + 18, 0), 'R', font=F(22, True), fill=INK, anchor='lm'); da.text(P(-RI - 18, 0), 'L', font=F(22, True), fill=INK, anchor='rm')
da.text(P(RI - 12, 22), 'seam\nblock', font=F(15, True), fill=MUT, anchor='rm', align='right')
im.paste(pa, (40, 150))
d.text((60, 120), 'A  From above, to scale', font=F(25, True), fill=INK)
d.text((60, 1020), 'Between the red oval (your head) and the ring is the\n'
       f'room for padding: {SIDE_PAD:.0f} mm at each side, {FB_PAD:.0f} mm front and\n'
       f'back ({TOP_PAD:.0f} mm on top, see B). The blocks at the sides\n'
       'are the seam connectors that join the front and back\n'
       'shell halves, ~6 mm in from the wall, copied from the\n'
       'real shell (as are the nose-clip and cheek-guard tabs).', font=F(19), fill=(40, 40, 40), spacing=6)
# ---------- B: side view, to scale (cut down the middle, front to back) ----------
pb = Image.new('RGB', (700, 470), (248, 248, 244)); db = ImageDraw.Draw(pb)
kb = 2.35
def P2(y, z): return (350 + y * kb, 400 - z * kb)
for n, c in (('front', NAVY), ('back', NAVY), ('arch_front', (120, 120, 112)), ('arch_back', (120, 120, 112))):
    segs = trimesh.intersections.mesh_plane(A[n], [1, 0, 0], [0, 0, 0])
    for sgm in segs: db.line([P2(sgm[0][1], sgm[0][2]), P2(sgm[1][1], sgm[1][2])], fill=c, width=3)
hy = np.linspace(-HEAD_A * Q, HEAD_A * Q, 200)
hz = [BROW_TO_CROWN * max(0, 1 - (abs(y) / (HEAD_A * Q)) ** 2.2) ** (1 / 2.2) for y in hy]      # same dome curve as the helmet
for i in range(0, len(hy) - 1, 2): db.line([P2(hy[i], hz[i]), P2(hy[i + 1], hz[i + 1])], fill=RED, width=3)
db.line([P2(-150, 0), P2(150, 0)], fill=(150, 150, 150), width=1)
db.text(P2(-148, 2), 'brow line', font=F(15, True), fill=MUT, anchor='lb')
db.text(P2(0, 60), f'your head (red dashes)\n{BROW_TO_CROWN:.0f} mm brow to crown', font=F(16, True), fill=RED, anchor='mm', align='center')
db.text(P2(4, 150), f'inside {HI:.0f} mm high', font=F(16, True), fill=INK, anchor='lb')
db.text(P2(-140, -8), 'FRONT', font=F(16, True), fill=INK, anchor='lt'); db.text(P2(140, -8), 'BACK', font=F(16, True), fill=INK, anchor='rt')
db.text(P2(14, 128), '12.5 mm under\nthe crown seam block', font=F(14, True), fill=MUT, anchor='lm')
import trimesh
im.paste(pb, (780, 150))
d.text((780, 120), 'B  From the side, to scale (cut down the middle)', font=F(25, True), fill=INK)
# ---------- C: render ----------
def paste(fn, x, y, w, crop=None, title=None):
    p_ = Image.open(fn).convert('RGB')
    if crop: p_ = p_.crop(crop)
    p_ = p_.resize((w, int(p_.height * w / p_.width)), Image.LANCZOS)
    im.paste(p_, (x, y + 36))
    if title: d.text((x, y), title, font=F(25, True), fill=INK)
    return p_.height
paste('helmet/sheet/fit_full34.png', 1500, 120, 660, (260, 230, 1060, 920), 'C  Band + top strap')
# ---------- D: how to test (bare head) + what to expect ----------
ex, ey = 780, 660
d.text((ex, ey), 'D  How to test (bare head, no padding)', font=F(25, True), fill=INK)
steps = ['1  Band: slide the front and back pieces UP into the two side pieces.',
         '    Strap: slide the two halves together sideways at the top joint,',
         '    then drop its ends onto the posts on the band (F end to the front).',
         '2  Put it on, FRONT at your forehead, and let it settle: it is bigger',
         '    than your head on purpose, so it rests on the top of your head.',
         '3  Measure, with a ruler or stacked fingers (one finger ~ 18 mm):',
         '    a. how far the band\'s bottom edge sits below your eyebrows,',
         '    b. the gap at each side above the ears, at the forehead and at the',
         '       back, with the band centred.',
         '4  Send me the numbers. If they are close to the table, the head size',
         '    is right and there is room for padding; if not, I adjust and rebuild.']
for i, t in enumerate(steps): d.text((ex, ey + 44 + i * 28), t, font=F(18, i in (0, 3, 5, 9)), fill=INK if i in (0, 3, 5, 9) else (50, 50, 60))
ty = ey + 44 + len(steps) * 28 + 20
d.text((ex, ty), 'What a 7 1/4 head should show (the room the helmet leaves for padding):', font=F(19, True), fill=INK)
tab = [('band below the eyebrows', '~12 mm (top gap: 12.5 under the seam block, ~20 beside it)'),
       ('each side, above the ears', '~19-23 mm (less right at the seam blocks)'),
       ('forehead', '~25 mm'), ('back of the head', '~28 mm')]
for i, (a_, b_) in enumerate(tab):
    d.text((ex + 10, ty + 34 + i * 28), a_, font=F(18, True), fill=(50, 50, 60)); d.text((ex + 300, ty + 34 + i * 28), b_, font=F(18), fill=(50, 50, 60))
d.text((60, 1020 + 170), 'Much bigger gaps = helmet too big for you; touching or tight = too small.', font=F(19, True), fill=RED)
im.save('pkg/step17_fit_test.jpg', quality=90)
print('sheet written')
