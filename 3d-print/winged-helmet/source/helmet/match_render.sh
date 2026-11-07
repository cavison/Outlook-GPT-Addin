#!/bin/bash
# usage: match_render.sh <outdir> <tag>   -> match/<tag>_photo.png (photo-matched camera) + side-by-side
D=$1; T=$2
cam=$(python3 -c "
import math; yaw,el,d=25,12,560; cz=8
print(f'{d*math.sin(math.radians(yaw))*math.cos(math.radians(el)):.1f},{-d*math.cos(math.radians(yaw))*math.cos(math.radians(el)):.1f},{cz+d*math.sin(math.radians(el)):.1f},0,0,{cz}')")
timeout 900 xvfb-run -a openscad -D 'view="assembled"' -D "D=\"$D\"" -o match/${T}_cam.png --imgsize=1400,1000 --camera=$cam --viewall --projection=p --colorscheme=Tomorrow views.scad 2>&1 | grep ERROR
cd .. && ./venv/bin/python - "$T" <<'PY'
import sys
from PIL import Image, ImageChops, ImageDraw, ImageFont
import numpy as np
T=sys.argv[1]
F=ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",26)
photo=Image.open("/root/.claude/uploads/319431bf-dd7d-5dd8-8f43-98ef81b3e188/068c6438-image.jpg").convert("RGB").crop((300,0,920,572))
r=Image.open(f"helmet/match/{T}_cam.png").convert("RGB")
a=np.asarray(r).astype(int); m=((a.max(2)-a.min(2))<=3)&(a.min(2)>=240); b=np.array(r); b[m]=255; r=Image.fromarray(b)
bb=ImageChops.difference(r, Image.new("RGB", r.size,(255,255,255))).getbbox(); r=r.crop(bb)
s=photo.height/r.height; r=r.resize((int(r.width*s), photo.height), Image.LANCZOS)
c=Image.new("RGB",(photo.width+r.width+20, photo.height+40),"white"); c.paste(photo,(0,40)); c.paste(r,(photo.width+20,40))
d=ImageDraw.Draw(c); d.text((10,6),"Your photo",font=F,fill="#1B1F2A"); d.text((photo.width+30,6),"Design (same viewpoint)",font=F,fill="#1B1F2A")
c.save(f"helmet/match/{T}_vs_photo.png")
PY
