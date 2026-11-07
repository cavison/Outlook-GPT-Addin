from PIL import Image, ImageDraw, ImageFont
B = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"; R = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
F, FB, FS, FC = ImageFont.truetype(B, 32), ImageFont.truetype(B, 22), ImageFont.truetype(R, 21), ImageFont.truetype(R, 18)
INK, MUT = "#1B1F2A", "#4A5160"
S = 'helmet/sheet/'
def img(n, w, box=None):
    im = Image.open(S + n + '.png').convert('RGB')
    if box: im = im.crop(box)
    return im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)
M, G = 24, 16
W = 1600
top = [('Assembled, front', img('cv_assembled', 770, (60, 40, 1060, 1060))), ('Assembled, back', img('cv_assembled_back', 770, (60, 40, 1060, 1060)))]
cw = (W - 2 * M - 3 * G) // 4
grid = [
    ('v_shell_back_in', 'Shell back, inside', ['Seam rib with dowel holes;', 'a boss behind every peg hole']),
    ('v_guard_out', 'Cheek guard, outside', ['Tongue with 3 snap bumps, pocket', 'for the white H, frame peg holes']),
    ('v_frame_back', 'Gold cheek frame, back', ['7 pegs into the guard']),
    ('v_neck_out', 'Neck plate', ['Tongue with 3 snap bumps;', 'lugs inside meet the guards']),
    ('v_band_white_back', 'Band, white base (front piece)', ['Pegs into the shell; the white', 'dots are pegs through all 3 layers']),
    ('v_band_gold_back', 'Band, gold middle', ['Pegs through the white', 'layer into the shell']),
    ('v_band_navy_back', 'Band, navy top', ['Pegs through gold and', 'white into the shell']),
    ('v_V', 'Back V: gold outline + navy', ['2 pegs each, on the', 'white base']),
    ('v_crest_under', 'Crest, back pieces', ['White pegs into the shell; gold', 'pegs pass through the white']),
    ('v_H_back', 'Front H, back', ['3 pegs (5 mm) into', 'bosses in the shell']),
    ('v_small', 'Cheek H and rivet', ['White H: 2 pegs;', 'rivet: a pin with a domed head']),
    ('v_shell_front_in', 'Shell front, inside', ['Bosses, nose snap holes,', 'seam rib along the edge']),
]
cells = [(img(n, cw), t, cap) for n, t, cap in grid]
ch = max(c[0].height for c in cells)
notes = [
    ('Checked', ['All 38 pieces are single solid parts. Every piece was placed in its assembled position and checked against',
                 'every other: nothing collides. Pegs have 0.1 mm of room plus small crush ribs, so they press in snug.']),
    ('Two small changes from the connector map', [
        'Cheek guard to shell: 3 snap bumps instead of 2 bumps + 1 pin (the third bump does the pin\'s job).',
        'Cheek guard to neck plate: the peg sits on a lug inside, so it is hidden and slides in as the neck plate goes on.']),
    ('Band seams', ['The band layers split into front, back and two side pieces. Every seam sits behind a wing (73 to 107 degrees),',
                    'and the white, gold and navy seams are staggered so no two line up, and none lines up with the shell seam.']),
    ('Parts and filament (helmet only, wings next)', [
        '38 pieces + 7 seam dowel pins.  About 685 g navy, 159 g gold, 120 g white.',
        'The back shell half prints dome-up, tilted 8 degrees, to fit the 220 mm bed (215 x 156 x 204 mm).']),
]
TH = sum(34 + 28 * len(l) + 12 for _, l in notes)
H = 70 + 34 + top[0][1].height + 24 + 3 * (34 + ch + 58 + 16) + TH + 20
c = Image.new('RGB', (W, H), 'white'); d = ImageDraw.Draw(c)
d.text((M, 18), 'Helmet pieces with their connectors built in', font=F, fill=INK)
y = 70
for k, (t, im) in enumerate(top):
    x = M + k * (770 + G); d.text((x, y), t, font=FB, fill=INK); c.paste(im, (x, y + 34))
y += 34 + top[0][1].height + 24
for r in range(3):
    for k in range(4):
        im, t, cap = cells[r * 4 + k]; x = M + k * (cw + G)
        d.text((x, y), t, font=FB, fill=INK); c.paste(im, (x, y + 32))
        for j, line in enumerate(cap): d.text((x, y + 32 + ch + 6 + j * 24), line, font=FC, fill=MUT)
    y += 32 + ch + 58 + 16
for head, lines in notes:
    d.text((M, y), head, font=FB, fill=INK); y += 32
    for l in lines: d.text((M, y), l, font=FS, fill=MUT); y += 28
    y += 12
c = c.crop((0, 0, W, y + 10)); c.save('pkg/step8_connectors_built.jpg', quality=90); print(c.size)
