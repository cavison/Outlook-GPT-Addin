import sys, numpy as np, trimesh, manifold3d as m3
out = sys.argv[1]
def M(n):
    t = trimesh.load_mesh(f"{out}/{n}.stl")
    return m3.Manifold(m3.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))
for piece in ["helmet", "wing_right", "wing_left"]:
    u = None
    for c in ["navy", "gold", "white"]:
        m = M(f"{piece}_{c}")
        # grow slightly so touching parts count as connected
        u = m if u is None else u + m
    parts = u.decompose()
    vols = sorted([p.volume() for p in parts], reverse=True)
    print(piece, "connected pieces:", len(parts), "volumes:", [round(v,2) for v in vols[:6]])
