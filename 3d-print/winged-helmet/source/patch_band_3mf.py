#!/usr/bin/env python
# Swap the changed pieces into the main Orca project IN PLACE (same plate, same spot, same turn, same settings),
# so the plates the user has already printed keep their numbers.  Each new piece gets exactly the rigid move the
# old piece got (found from the old STL and the old object's mesh), then is set down on the bed.
# Also writes a one-plate reprint project with the three navy band pieces the user needs again.
import io, re, os, sys, json, math, uuid, zipfile, shutil
import numpy as np, trimesh
from shapely.geometry import MultiPoint
from shapely import affinity
SRC3MF = 'pkg/winged_helmet_AD5X.3mf'
BACKUP = 'ref2/winged_helmet_AD5X_before_band2.3mf'
OLD, NEW = 'helmet/out_v23/print/', 'helmet/out_v23/print_band2/'
if not os.path.exists(BACKUP): shutil.copy(SRC3MF, BACKUP)
ns = {}
src = open('plates_build.py').read(); exec(src[:src.index('# ---------- orient every piece ----------')], ns)
P = ns['P']
swap = {}                                             # object name -> (old stl, new stl)
for p in P:
    for f, c in p['parts']:
        if f.startswith(OLD) and os.path.exists(NEW + os.path.basename(f)):
            assert len(p['parts']) == 1 and p['qty'] == 1, p['name']
            swap[p['name']] = (f, NEW + os.path.basename(f))
print('pieces to swap:', len(swap)); [print('  ', k) for k in swap]
def fmt(x): return ('%.4f' % x).rstrip('0').rstrip('.') if abs(x) > 1e-9 else '0'
def mesh_xml(m):
    out = io.StringIO(); out.write('    <mesh>\n     <vertices>\n')
    for v in m.vertices: out.write(f'      <vertex x="{fmt(v[0])}" y="{fmt(v[1])}" z="{fmt(v[2])}"/>\n')
    out.write('     </vertices>\n     <triangles>\n')
    for f in m.faces: out.write(f'      <triangle v1="{f[0]}" v2="{f[1]}" v3="{f[2]}"/>\n')
    out.write('     </triangles>\n    </mesh>\n'); return out.getvalue()
def read_mesh(xml):
    V = np.array([[float(a), float(b), float(c)] for a, b, c in re.findall(r'<vertex x="([^"]+)" y="([^"]+)" z="([^"]+)"', xml)])
    Fc = np.array([[int(a), int(b), int(c)] for a, b, c in re.findall(r'<triangle v1="(\d+)" v2="(\d+)" v3="(\d+)"', xml)])
    return V, Fc
def kabsch(A, B):                                     # rigid R, t with B ~ A R^T + t
    ca, cb = A.mean(0), B.mean(0); H = (A - ca).T @ (B - cb)
    U, S, Vt = np.linalg.svd(H); d = np.sign(np.linalg.det(Vt.T @ U.T))
    R = Vt.T @ np.diag([1, 1, d]) @ U.T; return R, cb - ca @ R.T
zin = zipfile.ZipFile(BACKUP)
cfg = zin.read('Metadata/model_settings.config').decode()
main = zin.read('3D/3dmodel.model').decode()
new_files, report, placed = {}, [], {}
for name, (fo, fn) in swap.items():
    i = cfg.find(f'<metadata key="name" value="{name}"/>'); blk = cfg[cfg.rfind('<object', 0, i):cfg.find('</object>', i)]
    oid = re.search(r'<object id="(\d+)"', blk).group(1)
    ob = main[main.find(f'<object id="{oid}"'):]; ob = ob[:ob.find('</object>')]
    path = re.search(r'p:path="/([^"]+)"', ob).group(1)
    xml = zin.read(path).decode()
    V, Fc = read_mesh(xml)
    old = trimesh.load(fo); new = trimesh.load(fn)
    assert len(old.vertices) == len(V), (name, len(old.vertices), len(V))
    R, t = kabsch(np.asarray(old.vertices), V)
    res = np.abs(np.asarray(old.vertices) @ R.T + t - V).max()
    assert res < 0.01, (name, res)
    NV = np.asarray(new.vertices) @ R.T + t
    NV[:, 2] -= NV[:, 2].min()                           # set it down on the bed
    c_old = (V[:, :2].max(0) + V[:, :2].min(0)) / 2; c_new = (NV[:, :2].max(0) + NV[:, :2].min(0)) / 2
    NV[:, :2] += c_old - c_new                           # same spot on the plate as the old piece
    nm = trimesh.Trimesh(NV, new.faces, process=False)
    head = xml[:xml.find('    <mesh>')]; tail = xml[xml.find('    </mesh>') + len('    </mesh>\n'):]
    new_files[path] = head + mesh_xml(nm) + tail
    placed[name] = (nm, blk)
    e_o = V.max(0) - V.min(0); e_n = NV.max(0) - NV.min(0)
    report.append(f'{name:22s} fit residual {res:.4f} mm   size {e_o[0]:.0f}x{e_o[1]:.0f}x{e_o[2]:.1f} -> {e_n[0]:.0f}x{e_n[1]:.0f}x{e_n[2]:.1f} mm')
print('\n'.join(report))
zout = zipfile.ZipFile(SRC3MF, 'w', zipfile.ZIP_DEFLATED, compresslevel=6)
for item in zin.infolist():
    data = new_files[item.filename].encode() if item.filename in new_files else zin.read(item.filename)
    zout.writestr(item, data)
zout.close()
print('updated', SRC3MF)
json.dump({k: [os.path.basename(a), os.path.basename(b)] for k, (a, b) in swap.items()}, open('ref2/band2_swapped.json', 'w'), indent=1)
pickle_ok = True
import pickle; pickle.dump({k: (v[0], v[1]) for k, v in placed.items()}, open('ref2/band2_placed.pkl', 'wb'))
