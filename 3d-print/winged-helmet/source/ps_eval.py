#!/usr/bin/env python
# Try several print orientations per helmet piece, slice each with PrusaSlicer (organic supports from the bed,
# 45 deg threshold, 0.2 mm layers) and keep the one with the best time + support, among those that stand
# stably on a real base.  Result -> ref2/orient.json
import json, math, os, subprocess, sys, numpy as np, trimesh
from concurrent.futures import ThreadPoolExecutor
src = open('orient_search.py').read()
exec(src[:src.index("if __name__ == '__main__':")])
OUT = 'ps/cand'; os.makedirs(OUT, exist_ok=True)
FIL = math.pi * 0.875 ** 2 * 1.24 / 1000          # g per mm of 1.75 PLA
def slice_stats(stl, infill, walls):
    gc = stl[:-4] + '.gcode'
    if not os.path.exists(gc):
        subprocess.run(['prusa-slicer', '--export-gcode', '--load', 'ps/base.ini', '--use-relative-e-distances',
                        '--fill-density', infill, '--perimeters', str(walls), '--center', '110,110', stl, '--output', gc],
                       capture_output=True, timeout=1200)
    if not os.path.exists(gc): return dict(hours=99.0, support_g=999.0, total_g=999.0, overhang_g=0.0, failed=True)
    per, typ, t = {}, None, None
    for line in open(gc):
        if line.startswith(';TYPE:'): typ = line[6:].strip()
        elif line.startswith('G1') and ' E' in line and typ:
            e = float(line.split(' E')[1].split()[0])
            if e > 0: per[typ] = per.get(typ, 0) + e
        elif line.startswith('; estimated printing time (normal mode)'): t = line.split('=')[1].strip()
    h = 0.0
    for part in t.replace('d', 'd ').split():
        v = float(part[:-1]); h += {'d': 24, 'h': 1, 'm': 1 / 60, 's': 1 / 3600}[part[-1]] * v
    sup = (per.get('Support material', 0) + per.get('Support material interface', 0)) * FIL
    return dict(hours=h, support_g=sup, total_g=sum(per.values()) * FIL, overhang_g=per.get('Overhang perimeter', 0) * FIL)
def candidates(m, outer, current=None):
    dirs = np.vstack([DIRS, np.eye(3), -np.eye(3)] + ([np.asarray(current, float)[None]] if current is not None else []))
    contact, sup_w, sup, height = evaluate(m, outer, dirs).T
    cells, stable = contact_cells(m, dirs)
    fit = np.array([height[k] <= 216 for k in range(len(dirs))])
    picks = []
    def take(sc, n_max):
        n = 0
        for k in np.argsort(sc):
            if not np.isfinite(sc[k]) or n >= n_max: break
            if any(np.dot(dirs[k], dirs[j]) > math.cos(math.radians(15)) for j in picks): continue
            if not footprint_ok(m, dirs[k])[0]: continue
            picks.append(k); n += 1
    for strict in (True, False):
        bad = ~fit | ((~stable | (cells < 8)) if strict else (cells < 3))
        for w_sup, w_cells in ((1.0, 0.05), (1.0, 0.2), (0.2, 0.05), (1.0, 0.01), (0.05, 0.2)):
            sc = w_sup * sup_w / 1000.0 + 0.01 * height - w_cells * cells; sc[bad] = np.inf
            take(sc, 2 if strict else 1)
        if len(picks) >= 4: break
    for k in range(len(DIRS), len(dirs)):                       # the axis directions and the current one, if they fit
        if fit[k] and footprint_ok(m, dirs[k])[0] and not any(np.dot(dirs[k], dirs[j]) > 0.99 for j in picks): picks.append(k)
    return [(dirs[k], dict(cells=int(cells[k]), height=float(height[k]), stable=bool(stable[k]))) for k in picks]
def run_piece(p):
    parts = [(trimesh.load(f), c) for f, c in p['parts']]
    m = trimesh.util.concatenate([q for q, _ in parts])
    C = m.triangles_center; radial = np.c_[C[:, 0], C[:, 1] / K ** 2, np.maximum(C[:, 2], 0)]
    outer = np.einsum('ij,ij->i', m.face_normals, radial) > 0
    cands = candidates(m, outer, current=p.get('current_down'))
    s = SET[p['settings']]
    done = [r for r in (json.load(open('ref2/orient_eval.json')).get(p['name'], []) if os.path.exists('ref2/orient_eval.json') else [])]
    reuse = []
    jobs = []
    for j, (g, info) in enumerate(cands):
        hit = [r for r in done if np.dot(np.array(r['down']) / np.linalg.norm(r['down']), g) > math.cos(math.radians(1.0))]
        if hit: reuse.append(hit[0]); continue
        q = m.copy(); R = np.eye(4); R[:3, :3] = align_down(g); q.apply_transform(R)
        q.apply_translation(-q.bounds[0])
        stl = f"{OUT}/{p['name'].replace(' ', '_')}_d{g[0]:+.3f}{g[1]:+.3f}{g[2]:+.3f}.stl"; q.export(stl)
        jobs.append((g, info, stl))
    with ThreadPoolExecutor(4) as ex:
        stats = list(ex.map(lambda jb: slice_stats(jb[2], s['sparse_infill_density'], s['wall_loops']), jobs))
    rows = []
    for (g, info, stl), st in zip(jobs, stats):
        cost = st['hours'] + st['support_g'] / 25.0 + st['overhang_g'] / 25.0
        if not info['stable']: cost += 3.0                     # starts on a few points: riskier
        rows.append(dict(down=np.round(g, 4).tolist(), cost=cost, **info, **st))
    seen = [np.array(r['down']) for r in rows]
    for r in done:                                               # keep every earlier trial too
        if not any(np.dot(np.array(r['down']) / np.linalg.norm(r['down']), d / np.linalg.norm(d)) > math.cos(math.radians(1.0)) for d in seen): rows.append(r)
    rows.sort(key=lambda r: r['cost'])
    return rows
if __name__ == '__main__':
    names = sys.argv[1:]
    if names == ['ALL']:
        names = [p['name'] for p in P if p['group'] != 'multi' and p['settings'] not in ('pin', 'core') and not p['name'].startswith(('Shell', 'Wing'))]
    res = json.load(open('ref2/orient_eval.json')) if os.path.exists('ref2/orient_eval.json') else {}
    for p in P:
        if p['name'] not in names: continue
        if p['orient'] == 'axis':
            c = np.vstack([trimesh.load(f).vertices for f, _ in p['parts']]).mean(0); p['current_down'] = -outward(c)
        if p['orient'] == 'nose_pin': p['current_down'] = np.array([0, 1.0, 0])
        rows = run_piece(p); res[p['name']] = rows
        print(p['name'])
        for r in rows: print(f"   down {str(r['down']):34s} h {r['height']:5.1f}  cells {r['cells']:4d} {'stable' if r['stable'] else 'TIPPY '}  {r['hours']:5.2f} h  support {r['support_g']:6.1f} g  overhang {r['overhang_g']:5.1f} g  total {r['total_g']:6.1f} g  cost {r['cost']:5.2f}")
        json.dump(res, open('ref2/orient_eval.json', 'w'), indent=1)
