from PIL import Image, ImageDraw, ImageFont
U = '/root/.claude/uploads/319431bf-dd7d-5dd8-8f43-98ef81b3e188/'
F = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 30)
FS = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 21)
INK, MUT = "#1B1F2A", "#4A5160"
H = 560
def fit(im, h): return im.resize((int(im.width * h / im.height), h), Image.LANCZOS)
ph = fit(Image.open(U + 'd47111e3-image.jpg').convert('RGB').crop((540, 40, 1110, 705)), H)
ims = [fit(Image.open(f'ref2/wing_scheme_{n}.png').convert('RGB').crop((0, 0, 828, 960)), H) for n in 'ABC']
cap = {'Your photo': ['Wing shape we are keeping.'],
       'A: Gold wing': ['Gold feathers, white trailing edges,', 'navy shafts. Navy scallops rimmed in gold.', 'Brightest; closest to your photo overall.'],
       'B: Gold-tipped': ['Navy feathers with gold tips in one smooth', 'sweep, white shafts. Gold scallops.', 'Most like a real bird (dark base, light tips).'],
       'C: Two-tone': ['Long feathers gold on top, navy below,', 'split by a white shaft. Hanging feathers', 'as in A. Gold scallops rimmed in navy.']}
cols = [('Your photo', ph)] + list(zip(['A: Gold wing', 'B: Gold-tipped', 'C: Two-tone'], ims))
W = sum(im.width for _, im in cols) + 20 * (len(cols) + 1)
c = Image.new('RGB', (W, H + 190), 'white'); d = ImageDraw.Draw(c); x = 20
for t, im in cols:
    d.text((x, 12), t, font=F, fill=INK); c.paste(im, (x, 58))
    for k, line in enumerate(cap[t]): d.text((x, H + 72 + 28 * k), line, font=FS, fill=MUT)
    x += im.width + 20
c.save('pkg/step4b_wing_colours.jpg', quality=92); print(c.size)
