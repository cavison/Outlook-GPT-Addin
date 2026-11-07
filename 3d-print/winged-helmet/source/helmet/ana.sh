#!/bin/bash
# usage: ana.sh <model.scad> <out.png> [yaw el]   photo-matched preview with magenta lining
M=$1; O=$2; YAW=${3:-25}; EL=${4:-10}; PROJ=${5:-p}
sed "s|MODEL|$M|" ana_view.scad > _ana_$$.scad
[ "$6" = "nomark" ] && sed -i "/sphere(r = 2.2/d" _ana_$$.scad
cam=$(python3 -c "
import math; yaw,el,d=$YAW,$EL,1400
print(f'{d*math.sin(math.radians(yaw))*math.cos(math.radians(el)):.1f},{-d*math.cos(math.radians(yaw))*math.cos(math.radians(el)):.1f},{d*math.sin(math.radians(el)):.1f},0,0,0')")
timeout 600 xvfb-run -a openscad -o $O --imgsize=1400,1200 --camera=$cam --viewall --projection=$PROJ --colorscheme=Tomorrow _ana_$$.scad 2>&1 | grep -E "ERROR|WARN"
rm -f _ana_$$.scad
