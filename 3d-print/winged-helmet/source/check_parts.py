"""Sanity checks for exported helmet STLs.

usage: python check_parts.py <outdir> XM YM ZM YAW SPLAY
 - each STL: watertight? volume, bounding box
 - color bodies of one piece must not overlap each other
 - mounted wings must not collide with the helmet
 - overall assembled height
"""
import sys, itertools, numpy as np, trimesh, manifold3d as m3

out = sys.argv[1]
XM, YM, ZM, YAW, SPL = map(float, sys.argv[2:7])
COLORS = ["navy", "gold", "white"]


def load(name):
    try:
        return trimesh.load_mesh(f"{out}/{name}.stl")
    except Exception:
        return None


def to_manifold(mesh):
    return m3.Manifold(m3.Mesh(vert_properties=np.asarray(mesh.vertices, np.float32),
                               tri_verts=np.asarray(mesh.faces, np.uint32)))


def rx(a):
    a = np.radians(a); c, s = np.cos(a), np.sin(a)
    return np.array([[1, 0, 0, 0], [0, c, -s, 0], [0, s, c, 0], [0, 0, 0, 1]])


def ry(a):
    a = np.radians(a); c, s = np.cos(a), np.sin(a)
    return np.array([[c, 0, s, 0], [0, 1, 0, 0], [-s, 0, c, 0], [0, 0, 0, 1]])


def rz(a):
    a = np.radians(a); c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0, 0], [s, c, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])


def tr(x, y, z):
    m = np.eye(4); m[:3, 3] = [x, y, z]; return m


FRAME = tr(XM, YM, ZM) @ rz(-YAW) @ ry(SPL) @ rz(90) @ rx(90)
MIRX = np.diag([-1, 1, 1, 1])

pieces = {}
for piece in ["helmet", "wing_right", "wing_left"]:
    for c in COLORS:
        m = load(f"{piece}_{c}")
        if m is None:
            continue
        pieces[(piece, c)] = m
        b = m.bounds
        print(f"{piece}_{c:5s} watertight={m.is_watertight} vol={m.volume:9.1f} mm3 "
              f"size={np.round(b[1]-b[0], 1)}")

# overlaps between colors of the same piece
for piece in ["helmet", "wing_right"]:
    ms = {c: to_manifold(pieces[(piece, c)]) for c in COLORS if (piece, c) in pieces}
    for a, b in itertools.combinations(ms, 2):
        v = (ms[a] ^ ms[b]).volume()
        print(f"overlap {piece}: {a}/{b} = {v:.3f} mm3")

# wings mounted on helmet
helmet = None
for c in COLORS:
    if ("helmet", c) in pieces:
        hm = to_manifold(pieces[("helmet", c)])
        helmet = hm if helmet is None else helmet + hm
allm = [pieces[k] for k in pieces if k[0] == "helmet"]
if helmet is not None and ("wing_right", "navy") in pieces:
    for c in COLORS:
        if ("wing_right", c) not in pieces:
            continue
        w = pieces[("wing_right", c)].copy(); w.apply_transform(FRAME)
        wl = pieces[("wing_right", c)].copy(); wl.apply_transform(MIRX @ FRAME)
        allm += [w, wl]
        v = (helmet ^ to_manifold(w)).volume()
        print(f"collision right wing {c} vs helmet: {v:.3f} mm3")
    z = np.concatenate([m.vertices[:, 2] for m in allm])
    x = np.concatenate([m.vertices[:, 0] for m in allm])
    y = np.concatenate([m.vertices[:, 1] for m in allm])
    print(f"ASSEMBLED  height {z.max()-z.min():.1f} mm ({(z.max()-z.min())/25.4:.2f} in)  "
          f"width {x.max()-x.min():.1f}  depth {y.max()-y.min():.1f}")
    scene = trimesh.util.concatenate(allm)
    scene.export(f"{out}/_assembled_check.stl")
