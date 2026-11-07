"""Estimate color changes for a multi-part piece printed in its exported orientation."""
import sys, numpy as np, trimesh
d, piece, lh = sys.argv[1], sys.argv[2], float(sys.argv[3])
ms = {c: trimesh.load_mesh(f"{d}/{piece}_{c}.stl") for c in ["navy", "gold", "white"]}
zmin = min(m.bounds[0][2] for m in ms.values()); zmax = max(m.bounds[1][2] for m in ms.values())
zs = np.arange(zmin + lh/2, zmax, lh)
changes, prev_last, layers3 = 0, None, 0
for z in zs:
    present = []
    for c, m in ms.items():
        s = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        if s is not None and len(s.entities):
            present.append(c)
    if not present: continue
    k = len(present); layers3 += (k == 3)
    # best case: start the layer on the color we ended with
    changes += (k - 1) + (0 if prev_last in present or prev_last is None else 1)
    order = ([prev_last] if prev_last in present else []) + [c for c in present if c != prev_last]
    prev_last = order[-1]
print(f"{piece}: {len(zs)} layers @ {lh} mm, {layers3} layers with all 3 colors, ~{changes} color changes")
