#!/usr/bin/env python
# Pick the print orientation of each helmet piece from the slicing trials (ref2/orient_eval.json) -> ref2/orient.json
#   cost = print hours + support g / 25 + overhang g / 25 (+3 if it starts on a few points)   [from ps_eval.py]
#        + 0.1 per cm2 of SHOW face (outer side of the helmet) that would sit on support
#        + 0.5 per unit of slenderness above 3 (height in mm per 2 mm cell of bed contact)
# Mirrored pairs (R / L) share one choice, mirrored, so both sides look the same.
import json, os, numpy as np, trimesh
_s = open('orient_search.py').read(); exec(_s[:_s.index("if __name__ == '__main__':")])
ev = json.load(open('ref2/orient_eval.json'))
MANUAL = json.load(open('ref2/orient_manual.json')) if os.path.exists('ref2/orient_manual.json') else {}
COS30 = math.cos(math.radians(30))
def show_area(p, g):
    m = trimesh.util.concatenate([trimesh.load(f) for f, _ in p['parts']])
    C = m.triangles_center; radial = np.c_[C[:, 0], C[:, 1] / K ** 2, np.maximum(C[:, 2], 0)]
    outer = np.einsum('ij,ij->i', m.face_normals, radial) > 0
    g = np.asarray(g, float) / np.linalg.norm(g)
    h = -(C @ g); h -= (-(m.vertices @ g)).min()
    sup = (m.face_normals @ g > COS30) & (h > 0.3) & outer
    return float(m.area_faces[sup].sum() / 100.0)
PBY = {p['name']: p for p in P}
def best(name):
    rows = ev[name]
    for r in rows:
        r['show_cm2'] = show_area(PBY[name], r['down'])
        slender = max(0.0, r['height'] / max(r['cells'], 1) - 3.0)       # tall pieces on a small foot wobble: favour a longer edge on the bed
        r['cost2'] = r['cost'] + 0.1 * r['show_cm2'] + 0.5 * slender
    rows.sort(key=lambda r: r['cost2'])
    return rows
def mirror_name(n):
    for a, b in ((' R', ' L'), ('BR', 'BL')):
        if n.endswith(a): return n[:-len(a)] + b
    return None
out = {}
for name in ev:
    if name in out or name in MANUAL or not ev[name]: continue
    rows = best(name)
    other = mirror_name(name)
    if other in ev:
        mo = trimesh.load(PBY[other]['parts'][0][0]); mr = trimesh.load(PBY[name]['parts'][0][0])
        mirrored = abs(mo.volume - mr.volume) / mr.volume < 0.02 and np.allclose(mo.bounds[:, 1:], mr.bounds[:, 1:], atol=1.5)
        if mirrored:
            r = rows[0]
            gm = [-r['down'][0], r['down'][1], r['down'][2]]
            mo_cells, _ = contact_cells(trimesh.util.concatenate([trimesh.load(f) for f, _ in PBY[other]['parts']]), np.array([gm]) / np.linalg.norm(gm))
            if mo_cells[0] < max(5, 0.5 * r['cells']):          # not a true mirror at the bed: let each side choose for itself
                out[name] = dict(r); out[other] = dict(best(other)[0]); continue
            out[name] = dict(r)
            out[other] = dict(r, down=gm, show_cm2=show_area(PBY[other], gm), mirrored_from=name)
            continue
    out[name] = dict(rows[0])
for name, r in MANUAL.items(): out[name] = r
for name, r in out.items():
    R = np.eye(4); R[:3, :3] = align_down(np.array(r['down'], float) / np.linalg.norm(r['down'])); r['R'] = R.tolist()
json.dump(out, open('ref2/orient.json', 'w'), indent=1)
for n, r in out.items():
    print(f"{n:22s} down {str(np.round(r['down'], 2).tolist()):24s} {r['hours']:5.2f} h  support {r['support_g']:5.1f} g  show-face on support {r.get('show_cm2', 0):5.1f} cm2  {'stable' if r['stable'] else 'tippy'}{'  (mirror of ' + r['mirrored_from'] + ')' if 'mirrored_from' in r else ''}")
