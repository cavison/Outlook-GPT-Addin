import sys, trimesh, numpy as np
from collections import Counter
m = trimesh.load_mesh(sys.argv[1], process=True)
e = np.sort(m.edges, axis=1); c = Counter(map(tuple, e))
bad = [k for k, v in c.items() if v != 2]
for k in bad:
    faces = [i for i,(a,b,cc) in enumerate(m.faces) if len({a,b,cc} & set(k))==2]
    print(k, c[k], np.round(m.vertices[list(k)],3).tolist(), "faces", len(faces))
