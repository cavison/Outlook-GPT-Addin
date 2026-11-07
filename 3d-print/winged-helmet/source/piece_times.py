#!/usr/bin/env python
# Print time and filament per piece (PrusaSlicer, same settings as the Orca project) -> ref2/piece_times.json
import json, os, subprocess, math
from concurrent.futures import ThreadPoolExecutor
_s = open('plates_build.py').read(); exec(_s[:_s.index('# ---------- orient every piece ----------')])
_e = open('ps_eval.py').read(); exec(_e[_e.index('FIL = '):_e.index('def candidates(')])
ORIENT = json.load(open('ref2/orient.json')) if os.path.exists('ref2/orient.json') else {}
out = json.load(open('ref2/piece_times.json')) if os.path.exists('ref2/piece_times.json') else {}
def job(p):
    s = SET[p['settings']]
    stl = f"ps/final/{p['name'].replace(' ', '_')}.stl"; gc = stl[:-4] + '.gcode'
    if os.path.exists(gc): os.remove(gc)
    args = ['prusa-slicer', '--export-gcode', '--load', 'ps/base.ini', '--use-relative-e-distances', '--fill-density', s['sparse_infill_density'],
            '--perimeters', s['wall_loops'], '--center', '110,110', '--fill-pattern', {'gyroid': 'gyroid', 'rectilinear': 'rectilinear'}.get(s.get('sparse_infill_pattern'), 'grid')]
    if 'top_shell_layers' in s: args += ['--top-solid-layers', s['top_shell_layers'], '--bottom-solid-layers', s['bottom_shell_layers']]
    if p['settings'].startswith('wing2'): args += ['--top-solid-layers', '12', '--bottom-solid-layers', '12']     # solid colour depth (approx.)
    if s.get('enable_support') != '1': args += ['--no-support-material']
    subprocess.run(args + [stl, '--output', gc], capture_output=True, timeout=1800)
    return p['name'], slice_stats(stl, s['sparse_infill_density'], s['wall_loops'])
todo = [p for p in P if p['name'] not in out or out[p['name']].get('failed')]
with ThreadPoolExecutor(4) as ex:
    for name, st in ex.map(job, todo):
        out[name] = st; print(f"{name:32s} {st['hours']:5.2f} h  {st['total_g']:6.1f} g  support {st['support_g']:5.1f} g", flush=True)
        json.dump(out, open('ref2/piece_times.json', 'w'), indent=1)
