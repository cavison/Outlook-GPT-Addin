#!/bin/bash
# usage: render_v23.sh part  -> out_v23/part.stl (+ .log)
p=$1
timeout 5400 openscad -D 'build="full"' -D "part=\"$p\"" -o out_v23/$p.stl winged_helmet_v23.scad > out_v23/$p.log 2>&1
echo "$p: $(grep -i 'error\|warn\|Volumes\|Total rendering' out_v23/$p.log | grep -v ECHO | tr '\n' ' ')"
