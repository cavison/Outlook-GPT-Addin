# sheet for the fit-test rings: to-scale top view (helmet inside vs head), joint detail, renders, how to test
import pickle, math, numpy as np
from PIL import Image, ImageDraw, ImageFont
exec(open('wing_build.py').read().split("if __name__ == '__main__':")[0])
src = open('fit_ring_build.py').read()
exec(src[src.index('C, Q = 579.0'):src.index('def revolve')])           # sizing constants
A = pickle.load(open('ref2/fit_ring.pkl', 'rb'))
F = lambda s, b=False: ImageFont.truetype('DejaVuSans-Bold.ttf' if b else 'DejaVuSans.ttf', s)
NAVY, GOLD, WHITE, INK, MUT, RED = (30, 42, 82), (242, 193, 46), (236, 236, 228), (25, 28, 38), (90, 95, 110), (200, 30, 30)
W, Hh = 2200, 1400
im = Image.new('RGB', (W, Hh), (248, 248, 244)); d = ImageDraw.Draw(im)
d.text((40, 24), 'Fit test before the shell: the helmet ring and the head ring', font=F(40, True), fill=INK)
d.text((40, 76), f'Built for a 579 mm head (hat size 7 1/4). Print plate 1 (helmet ring, ~2 h 50 min, 62 g) and plate 2 (head ring, ~40 min, 28 g) from fit_test_AD5X.3mf.', font=F(22), fill=MUT)
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
       f'back ({TOP_PAD:.0f} mm on top, not shown). The blocks at the sides\n'
       'are the seam connectors that join the front and back\n'
       'shell halves, ~6 mm in from the wall, copied from the\n'
       'real shell (as are the nose-clip and cheek-guard tabs).', font=F(19), fill=(40, 40, 40), spacing=6)
# ---------- B: joint detail (own canvas) ----------
pb = Image.new('RGB', (600, 420), (248, 248, 244)); db = ImageDraw.Draw(pb)
phi = math.radians(315)
jx, jy = (RI + 6) * math.cos(phi), (RI + 6) * math.sin(phi) * K
k2 = 9.0
def P2(x, y): return (300 + (x - jx) * k2, 210 - (y - jy) * k2)
for n in ('front', 'side_R'):
    for r in section(A[n], 5.0): db.polygon([P2(x, y) for x, y in r], fill=col[n], outline=(0, 0, 0))
db.text((330, 390), 'front piece (navy)', font=F(18, True), fill=NAVY); db.text((586, 10), 'side piece (gold)', font=F(18, True), fill=(150, 110, 10), anchor='ra')
im.paste(pb, (780, 150))
d.text((780, 120), 'B  How the pieces lock (one corner)', font=F(25, True), fill=INK)
d.text((780, 590), 'Front and back carry the dovetail tongues; the sides have the\n'
       'matching sockets. Each tongue slides UP into its socket from below\n'
       'and stops against a 1.2 mm roof. No glue; pull down to undo.', font=F(19), fill=(40, 40, 40), spacing=6)
# ---------- C, D: renders ----------
def paste(fn, x, y, w, crop=None, title=None):
    p = Image.open(fn).convert('RGB')
    if crop: p = p.crop(crop)
    p = p.resize((w, int(p.height * w / p.width)), Image.LANCZOS)
    im.paste(p, (x, y + 36))
    if title: d.text((x, y), title, font=F(25, True), fill=INK)
    return p.height
paste('helmet/sheet/fit_34.png', 1420, 120, 740, (60, 120, 1240, 900), 'C  Helmet ring, assembled')
paste('helmet/sheet/fit_head.png', 1500, 740, 600, (100, 150, 800, 680), 'D  Head ring (one piece)')
# ---------- E: how to test ----------
ex, ey = 780, 740
d.text((ex, ey), 'E  How to test', font=F(25, True), fill=INK)
steps = ['1  Head ring first, no padding. Wear it like a hat',
         '    band, bottom edge on your eyebrows. It should feel',
         '    snug, like a cap. Tight at the sides but loose front',
         '    and back = rounder head than assumed (and the reverse).',
         '2  Helmet ring: line the inside with your padding (or a',
         '    towel folded to the same thickness) and put it on the',
         '    same way, FRONT over your forehead. The seam blocks',
         '    sit just above your ears.',
         '3  Tell me snug / loose / tight, and where. I can change',
         '    the head size, the head shape and the padding gaps,',
         '    then rebuild the shell. If it fits, print the shell.',
         '',
         'If your padding will be thinner than ~20 mm, the helmet',
         'can shrink, which also gets the shell halves under 210 mm.']
for i, s in enumerate(steps): d.text((ex, ey + 46 + i * 30), s, font=F(19, i in (0, 4, 8)), fill=INK if i in (0, 4, 8) else (50, 50, 60))
im.save('pkg/step17_fit_rings.jpg', quality=90)
print('sheet written')
