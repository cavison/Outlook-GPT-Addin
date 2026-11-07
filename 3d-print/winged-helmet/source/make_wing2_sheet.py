from PIL import Image, ImageDraw, ImageFont
B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"; R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
F, FB, FS = ImageFont.truetype(B, 34), ImageFont.truetype(B, 24), ImageFont.truetype(R, 20)
INK, MUT = (27, 31, 42), (80, 86, 100)
def img(n, w, crop=None):
    im = Image.open('helmet/sheet/' + n + '.png').convert('RGB')
    if crop: im = im.crop(crop)
    return im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)
W = 2400; M = 30
rows = [
    [('On the helmet - front', img('w2_full_front', 1155, (0, 60, 1400, 1100))), ('On the helmet - back', img('w2_full_back', 1155, (0, 60, 1400, 1100)))],
    [('One wing - show side', img('w2_flat_front', 760, (150, 150, 1150, 1150))), ('Same wing - helmet side (key on the medallion)', img('w2_flat_back', 760, (150, 150, 1150, 1150))),
     ('Cut along a tab, collar on the right', img('w2_joint', 760))],
    [('Pulled apart: front medallion lifted, feathers out, plates and pegs visible', img('w2_explode', 1155)), (None, None)],
]
H = 3000
c = Image.new('RGB', (W, H), (248, 247, 243)); d = ImageDraw.Draw(c)
d.text((M, 20), 'Wings v2 - built: medallions + collars + snap-in feathers', fill=INK, font=F)
y = 80
for row in rows:
    x = M; hmax = 0
    for title, im in row:
        if im is None: continue
        d.text((x, y), title, fill=INK, font=FB)
        c.paste(im, (x, y + 36)); x += im.width + M; hmax = max(hmax, im.height + 46)
    if row is rows[2]:
        notes = ['Per wing (left wing = mirror of the right):',
                 '  front medallion, back medallion with the key,',
                 '  upper + lower collar with hidden plates,',
                 '  9 feathers + 2 tips   = 15 pieces',
                 'Collars have centred sockets and colour on both faces,',
                 'so one collar print serves both wings (turned over);',
                 'feathers, tips and medallions are made left and right.',
                 '',
                 'Tabs: 3.6 mm thick, 7-40 mm wide, 14-26 mm deep,',
                 '  printed on the bed (feathers print show face down).',
                 'Collar 8 mm: 2.2 mm proud of the feathers in front.',
                 'Colour: white 2.4 mm solid, gold 1.6 mm, then navy.',
                 'Tip A clicks into the lower collar, tip B into F9.',
                 'Nothing touches the helmet: feathers 11.5 mm away',
                 '  at the closest, back medallion 4.9 mm.',
                 'Largest piece 172 x 168 mm - all fit 210 x 210.']
        for k, t in enumerate(notes): d.text((x + 10, y + 50 + k * 31), t, fill=INK if k in (0, 8) else MUT, font=FS)
    y += hmax + 20
c = c.crop((0, 0, W, y)); c.save('pkg/step15_wings_v2_built.jpg', quality=90); print(c.size)
