#!/bin/bash
# usage: render_set.sh <build> <outdir> part1 part2 ...
B=$1; O=$2; shift 2
for P in "$@"; do
  ( s=$(date +%s); openscad -D "build=\"$B\"" -D "part=\"$P\"" -o "$O/${P}.stl" winged_helmet.scad > "logs/${B}_${P}.log" 2>&1; echo "$P done in $(( $(date +%s)-s ))s rc=$?" >> logs/${B}_status.txt ) &
done
wait
