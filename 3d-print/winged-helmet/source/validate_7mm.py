#!/usr/bin/env python
# Re-open the written project and check it the way Orca will read it.
import sys, zipfile, math, re, numpy as np
import xml.etree.ElementTree as ET
from shapely.geometry import MultiPoint
from shapely.ops import unary_union
F = sys.argv[1] if len(sys.argv) > 1 else 'pkg/winged_helmet_AD5X.3mf'
NS = {'m': 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02', 'p': 'http://schemas.microsoft.com/3dmanufacturing/production/2015/06'}
PP = '{http://schemas.microsoft.com/3dmanufacturing/production/2015/06}'
z = zipfile.ZipFile(F); names = set(z.namelist()); errs = []
for n in names:
    if n.endswith(('.model', '.config', '.rels', '.xml')):
        try: ET.fromstring(z.read(n))
        except ET.ParseError as e: errs.append(f'XML error in {n}: {e}')
main = ET.fromstring(z.read('3D/3dmodel.model'))
objs = {o.get('id'): o for o in main.find('m:resources', NS)}
items = main.find('m:build', NS).findall('m:item', NS)
rels = z.read('3D/_rels/3dmodel.model.rels').decode()
sub_cache = {}
def sub_objects(path):
    if path not in sub_cache:
        r = ET.fromstring(z.read(path.lstrip('/')))
        sub_cache[path] = {o.get('id'): o for o in r.find('m:resources', NS)}
    return sub_cache[path]
cfg = ET.fromstring(z.read('Metadata/model_settings.config'))
cfg_objs = {o.get('id'): o for o in cfg.findall('object')}
plates = cfg.findall('plate')
n_pl = len(plates); v = math.sqrt(n_pl); cols = int(round(v)) + (1 if v > round(v) else 0); STRIDE = 220 * 1.2
inst_plate = {}
for k, pl in enumerate(plates):
    for mi in pl.findall('model_instance'):
        oid = [m.get('value') for m in mi.findall('metadata') if m.get('key') == 'object_id'][0]
        inst_plate[oid] = k
ids_seen = set()
foot = {}
for it in items:
    oid = it.get('objectid')
    if oid not in objs: errs.append(f'build item -> missing object {oid}'); continue
    if oid not in cfg_objs: errs.append(f'object {oid} missing from model_settings.config')
    if oid not in inst_plate: errs.append(f'object {oid} not on any plate')
    t = [float(x) for x in it.get('transform').split()]; tx, ty = t[9], t[10]
    pts = []
    for comp in objs[oid].find('m:components', NS):
        path = comp.get(PP + 'path')
        if path.lstrip('/') not in names: errs.append(f'missing file {path}'); continue
        if path not in rels: errs.append(f'{path} not in rels')
        so = sub_objects(path).get(comp.get('objectid'))
        if so is None: errs.append(f'{path}: no object {comp.get("objectid")}'); continue
        if comp.get('objectid') in ids_seen: errs.append(f'duplicate part id {comp.get("objectid")}')
        ids_seen.add(comp.get('objectid'))
        V = np.array([[float(v.get('x')), float(v.get('y')), float(v.get('z'))] for v in so.find('m:mesh', NS).find('m:vertices', NS)])
        if V[:, 2].min() < -1e-3: errs.append(f'object {oid}: below the bed ({V[:, 2].min():.3f})')
        if V[:, 2].max() > 220: errs.append(f'object {oid}: taller than 220 ({V[:, 2].max():.1f})')
        pts.append(V[:, :2] + [tx, ty])
    k = inst_plate.get(oid, 0); row, col = k // cols, k % cols; ox, oy = col * STRIDE, -row * STRIDE
    P2 = np.vstack(pts) - [ox, oy]
    lo, hi = P2.min(0), P2.max(0)
    if lo.min() < 1.0 or hi[0] > 219.0 or hi[1] > 217.0: errs.append(f'object {oid} on plate {k + 1} too close to / past the bed edge: {lo.round(1)}..{hi.round(1)}')
    foot.setdefault(k, []).append((oid, MultiPoint(P2[::max(1, len(P2) // 4000)]).convex_hull))
# overlaps between pieces on a plate (convex hulls are conservative, so only report real raster overlaps later)
print(f'{F}: {len(items)} objects on {n_pl} plates, {len(ids_seen)} parts, {len(names)} files')
names_ok = [pl.find("metadata[@key='plater_name']").get('value') for pl in plates]
print('plates:', '; '.join(names_ok[:3]), '...')
print('errors:', len(errs)); [print('  ', e) for e in errs[:30]]
# real overlap / spacing check: rasterise each object's triangles from above at 0.5 mm
from PIL import Image, ImageDraw
from scipy import ndimage
S = 2
bad = 0
for k in sorted(foot):
    masks = []
    for it in items:
        oid = it.get('objectid')
        if inst_plate.get(oid) != k: continue
        t = [float(x) for x in it.get('transform').split()]; row, col = k // cols, k % cols
        off = np.array([t[9] - col * STRIDE, t[10] + row * STRIDE])
        img = Image.new('L', (220 * S, 220 * S), 0); d = ImageDraw.Draw(img)
        for comp in objs[oid].find('m:components', NS):
            so = sub_objects(comp.get(PP + 'path'))[comp.get('objectid')]
            mesh = so.find('m:mesh', NS)
            V = np.array([[float(v.get('x')), float(v.get('y'))] for v in mesh.find('m:vertices', NS)]) + off
            T = np.array([[int(tr.get('v1')), int(tr.get('v2')), int(tr.get('v3'))] for tr in mesh.find('m:triangles', NS)])
            for tri in (V[T] * S):
                d.polygon([tuple(q) for q in tri], fill=1)
        masks.append((oid, np.array(img, bool)))
    grown = [ndimage.binary_dilation(m, iterations=7 * S) for _, m in masks]   # 3 mm apart at least
    for a in range(len(masks)):
        for b in range(a + 1, len(masks)):
            if (grown[a] & masks[b][1]).any():
                bad += 1; print(f'   plate {k + 1}: objects {masks[a][0]} and {masks[b][0]} closer than 3 mm')
print('spacing problems:', bad)
