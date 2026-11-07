from PIL import Image, ImageDraw, ImageFont
B = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"; R = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
F, FB, FS, FC = ImageFont.truetype(B, 32), ImageFont.truetype(B, 22), ImageFont.truetype(R, 21), ImageFont.truetype(R, 19)
INK, MUT = "#1B1F2A", "#4A5160"
S = 'helmet/sheet/'
def img(n, w, box=None):
    im = Image.open(S + n + '.png').convert('RGB')
    if box: im = im.crop(box)
    return im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)
M, G, W = 24, 16, 1600
top = [('The whole helmet, built from the print pieces', img('full_front', 770, (80, 60, 1340, 1160))),
       ('From the back', img('full_back', 770, (80, 60, 1340, 1160)))]
cw = (W - 2 * M - 2 * G) // 3
mid = [('One wing pulled apart', img('wing_exploded', cw, (100, 0, 1400, 1100)), ['Front half, white middle, back half;', 'the feather sections pulled out']),
       ('Key behind the eagle', img('key_view', cw, (0, 0, 1000, 900)), ['Dovetail key with a catch bump,', 'and a round anti-twist peg']),
       ('Mount block on the helmet', img('block_view', cw, (150, 0, 1000, 850)), ['Socket open at the top, slot for the', 'peg; 4 pegs into both shell halves'])]
mh = max(i.height for _, i, _ in mid)
notes = [
    ('How each wing goes together', [
        'Each wing: 6 half pieces per face and 5 white middle pieces (17 pieces; 34 for both wings). The lowest long feather',
        'became its own piece, because it only joined its section under the scallops.',
        'Every piece is pegged: 3 pegs per section join the white middle to both halves, and at each joint under the scallops',
        'pegs go from the white middle, through the tucked feather plate, into the scallops above.',
        'The left wing uses the same shapes as the right (mirrored), and the white middles are identical for both.']),
    ('Mount', [
        'The key slides down into the block, a small bump clicks into a dimple at the bottom, and the round peg stops it twisting.',
        'The block is pegged into both shell halves, so it also bridges the front / back seam.',
        'Checked: the wing slides the full 32 mm down without touching the helmet, and sits 2.5 mm clear of it.']),
    ('One print note', [
        'The shoulder and front-edge halves need supports under the scallop lip that lies over the next feathers (2.5 mm high,',
        'on the hidden underside). Every other wing piece prints flat with no supports.']),
    ('Weight', [
        'If printed solid the wings would be about 1.9 kg; with normal infill expect about 600 g each, so the whole helmet',
        'comes to roughly 2.1 kg before padding: about a heavy football helmet, with the weight out at the sides.',
        'Filament to have on hand: 2 spools navy, 1 gold, 1 white (1 kg each).']),
]
TH = sum(34 + 28 * len(l) + 12 for _, l in notes)
H = 70 + 34 + top[0][1].height + 24 + 32 + mh + 58 + 16 + TH + 20
c = Image.new('RGB', (W, H), 'white'); d = ImageDraw.Draw(c)
d.text((M, 18), 'Wings: print pieces, pegs and the mount', font=F, fill=INK)
y = 70
for k, (t, im) in enumerate(top):
    x = M + k * (770 + G); d.text((x, y), t, font=FB, fill=INK); c.paste(im, (x, y + 34))
y += 34 + top[0][1].height + 24
for k, (t, im, cap) in enumerate(mid):
    x = M + k * (cw + G); d.text((x, y), t, font=FB, fill=INK); c.paste(im, (x, y + 32))
    for j, line in enumerate(cap): d.text((x, y + 32 + mh + 6 + j * 25), line, font=FC, fill=MUT)
y += 32 + mh + 58 + 16
for head, lines in notes:
    d.text((M, y), head, font=FB, fill=INK); y += 32
    for l in lines: d.text((M, y), l, font=FS, fill=MUT); y += 28
    y += 12
c = c.crop((0, 0, W, y + 10)); c.save('pkg/step9_wings.jpg', quality=90); print(c.size)
