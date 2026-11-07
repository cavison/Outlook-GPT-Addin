import sys
from PIL import Image, ImageDraw, ImageFont
U='/root/.claude/uploads/319431bf-dd7d-5dd8-8f43-98ef81b3e188/'
f, X0, Y0, X1, Y1, k, out = sys.argv[1], *map(int, sys.argv[2:7]), sys.argv[7]
im=Image.open(U+f).convert('RGB')
z=im.crop((X0,Y0,X1,Y1)).resize(((X1-X0)*k,(Y1-Y0)*k),Image.LANCZOS)
d=ImageDraw.Draw(z); F=ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",16)
for x in range(X0 - X0%10 + 10, X1, 10):
    X=(x-X0)*k; major = x%50==0
    d.line([(X,0),(X,z.height)],fill=(255,0,0) if major else (255,190,190),width=1)
    if major: d.text((X+2,2),str(x),fill=(255,0,0),font=F)
for y in range(Y0 - Y0%10 + 10, Y1, 10):
    Y=(y-Y0)*k; major = y%50==0
    d.line([(0,Y),(z.width,Y)],fill=(255,0,0) if major else (255,190,190),width=1)
    if major: d.text((2,Y+2),str(y),fill=(255,0,0),font=F)
z.save(out); print(z.size)
