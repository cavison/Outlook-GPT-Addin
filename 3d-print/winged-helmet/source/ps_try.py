# slice given orientations of one piece: python ps_try.py "<piece name>" "x,y,z" ["x,y,z" ...]
import sys, numpy as np, trimesh
_s = open('ps_eval.py').read(); exec(_s[:_s.rindex("if __name__ == '__main__':")])
from concurrent.futures import ThreadPoolExecutor
name = sys.argv[1]; p = [q for q in P if q['name'] == name][0]
m = trimesh.util.concatenate([trimesh.load(f) for f, _ in p['parts']])
jobs = []
for j, d in enumerate(sys.argv[2:]):
    g = np.array([float(x) for x in d.split(',')]); g /= np.linalg.norm(g)
    q = m.copy(); R = np.eye(4); R[:3, :3] = align_down(g); q.apply_transform(R); q.apply_translation(-q.bounds[0])
    stl = f"{OUT}/try_{name.replace(' ', '_')}_{d.replace(',', '_')}.stl"; q.export(stl)
    cells, stable = contact_cells(m, g[None])
    jobs.append((d, stl, q.bounds[1].round(1), cells[0], stable[0]))
s = SET[p['settings']]
with ThreadPoolExecutor(4) as ex:
    st = list(ex.map(lambda jb: slice_stats(jb[1], s['sparse_infill_density'], s['wall_loops']), jobs))
for (d, stl, ext, c, sb), r in zip(jobs, st):
    print(f"{name:22s} down {d:22s} size {ext}  cells {c:4d} stable {sb}  {r['hours']:5.2f} h  support {r['support_g']:6.1f} g  total {r['total_g']:6.1f} g")
