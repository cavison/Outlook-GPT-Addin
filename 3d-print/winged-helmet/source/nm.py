import sys, trimesh, numpy as np
from collections import Counter
for f in sys.argv[1:]:
    m = trimesh.load_mesh(f, process=True)
    e = np.sort(m.edges, axis=1)
    c = Counter(map(tuple, e))
    bad = [k for k, v in c.items() if v != 2]
    pts = m.vertices[np.array(bad).ravel()] if bad else np.zeros((0,3))
    print(f, "bad edges:", len(bad), "bodies:", len(m.split(only_watertight=False)))
    if len(pts):
        # cluster
        r = np.round(pts, 0)
        u, cnt = np.unique(r, axis=0, return_counts=True)
        for p, n in sorted(zip(map(tuple,u), cnt), key=lambda x: -x[1])[:12]: print("  ", p, n)
