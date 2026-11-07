#!/usr/bin/env python
# Lay every print piece out on 220 x 220 plates for the Flashforge AD5X and write an Orca Slicer project (.3mf).
#   * filament slots: 1 navy, 2 white, 3 gold (slot 4 spare)
#   * single-colour pieces only share plates with their own colour -> those plates need no filament changes
#   * multi-colour pieces (wing halves, front H) share plates with pieces of similar height / infill;
#     a corner is kept clear on those plates for the prime tower
#   * each piece carries its own settings (infill, walls, supports) as Orca per-object settings
import glob, io, json, math, os, uuid, zipfile
import numpy as np, trimesh
from PIL import Image, ImageDraw
from scipy.signal import fftconvolve
from scipy import ndimage

PR, PW = 'helmet/out_v23/print/', 'helmet/out_v23/print_wing/'
OUT3MF = 'pkg/winged_helmet_AD5X.3mf'
SLOT = {'navy': 1, 'white': 2, 'gold': 3}
RGB = {'navy': (30, 42, 82), 'white': (236, 236, 228), 'gold': (242, 193, 46)}
BED, MARGIN, GAP, RES = 220.0, 2.0, 5.0, 1.0          # mm: edge margin, gap between pieces, packing grid
TOWER = 52.0                                          # kept clear (top-left) on multi-colour plates
K = 1.23505

# ---------- per-piece settings (Orca per-object settings) ----------
SUP = {'enable_support': '1', 'support_type': 'tree(auto)', 'support_on_build_plate_only': '1'}
SET = {
    'shell':  dict(wall_loops='3', sparse_infill_density='12%', brim_type='no_brim', **SUP),   # 215 mm wide: no room for a brim
    'thin':   dict(wall_loops='2', sparse_infill_density='15%', **SUP),          # band layers, frames, guards, neck
    'strong': dict(wall_loops='4', sparse_infill_density='40%', **SUP),          # mount blocks, nose clip
    'pin':    dict(wall_loops='6', sparse_infill_density='100%'),                 # pins and dowels: solid
    'crest':  dict(wall_loops='3', sparse_infill_density='12%', sparse_infill_pattern='gyroid', **SUP),
    'core':   dict(wall_loops='2', sparse_infill_density='8%', sparse_infill_pattern='gyroid', top_shell_layers='3', bottom_shell_layers='3'),
    'half':   dict(wall_loops='2', sparse_infill_density='10%', sparse_infill_pattern='gyroid'),
    'half_s': dict(wall_loops='2', sparse_infill_density='10%', sparse_infill_pattern='gyroid', **SUP),   # with the scallop lip
    'small':  dict(wall_loops='3', sparse_infill_density='20%', **SUP),
    'badge':  dict(wall_loops='3', sparse_infill_density='10%', sparse_infill_pattern='gyroid', **SUP),
}

# ---------- orientation helpers ----------
def rot(axis, deg):
    a = math.radians(deg); c, s = math.cos(a), math.sin(a)
    if axis == 'x': R = [[1, 0, 0], [0, c, -s], [0, s, c]]
    elif axis == 'y': R = [[c, 0, s], [0, 1, 0], [-s, 0, c]]
    else: R = [[c, -s, 0], [s, c, 0], [0, 0, 1]]
    M = np.eye(4); M[:3, :3] = R; return M
def align(d, to=(0, 0, 1)):
    """rotation taking direction d onto 'to'"""
    d = np.asarray(d, float) / np.linalg.norm(d); t = np.asarray(to, float)
    v = np.cross(d, t); c = float(np.dot(d, t))
    if np.linalg.norm(v) < 1e-9: R = np.eye(3) if c > 0 else np.diag([1., -1., -1.])
    else:
        vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]]); R = np.eye(3) + vx + vx @ vx / (1 + c)
    M = np.eye(4); M[:3, :3] = R; return M
def outward(p):                       # outward normal of the (stretched) helmet side at p, horizontal
    n = np.array([p[0], p[1] / K ** 2, 0.0]); return n / np.linalg.norm(n)

# mount push-on direction (from the wing build's placement)
WPX, PY_, YAW, LEAN, ZB, MID_T = 103.942, -60.0, 15.0, 4.0, -135.0, 4.0
def _Rz(a): return rot('z', a)
def _Ry(a): return rot('y', a)
def _Tr(x, y, z): M = np.eye(4); M[:3, 3] = [x, y, z]; return M
SIDE = np.array([[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1]], float)
PLACE = _Tr(WPX, PY_, 0) @ _Rz(-YAW) @ _Tr(0, -PY_, 0) @ _Tr(0, 0, ZB) @ _Ry(LEAN) @ _Tr(0, 0, -ZB) @ SIDE
BACK = PLACE @ _Tr(0, 0, -MID_T / 2) @ np.diag([1, 1, -1, 1])
NRM = BACK[:3, 2] / np.linalg.norm(BACK[:3, 2])

# ---------- the piece list ----------
# (name, [(file, colour)], quantity, orientation, settings, group)
P = []
def add(name, parts, qty, orient, settings, group): P.append(dict(name=name, parts=parts, qty=qty, orient=orient, settings=settings, group=group))
def one(f, colour): return [(f, colour)]
add('Shell front', one(PR + 'shell_front_navy.stl', 'navy'), 1, 'upright', 'shell', 'navy')
add('Shell back', one(PR + 'shell_back_navy.stl', 'navy'), 1, 'tilt8', 'shell', 'navy')
for s in 'RL':
    add(f'Cheek guard {s}', one(PR + f'cheek_guard_{s}_navy.stl', 'navy'), 1, 'upright', 'thin', 'navy')
    add(f'Wing mount {s}', one(PR + f'wing_mount_{s}_navy.stl', 'navy'), 1, 'mount' + s, 'strong', 'navy')
    add(f'Cheek frame {s}', one(PR + f'cheek_frame_{s}_gold.stl', 'gold'), 1, 'upright', 'thin', 'gold')
    add(f'Cheek H {s}', one(PR + f'cheek_H_{s}_white.stl', 'white'), 1, 'axis', 'small', 'white')
    add(f'Cheek rivet {s}', one(PR + f'cheek_rivet_{s}_white.stl', 'white'), 1, 'axis', 'small', 'white')
add('Neck plate', one(PR + 'neck_plate_navy.stl', 'navy'), 1, 'upright', 'thin', 'navy')
for c in ('navy', 'gold', 'white'):
    for f in sorted(glob.glob(PR + f'band_{c}_*.stl')):
        add('Band ' + c + ' ' + os.path.basename(f)[len(f'band_{c}_'):-4], one(f, c), 1, 'upright', 'thin', c)
for c in ('navy', 'gold'):
    add(f'Back V {c}', one(PR + f'band_V_{c}.stl', c), 1, 'upright', 'thin', c)
for c in ('white', 'gold'):
    for piece in ('front', 'back'):
        add(f'Crest {c} {piece}', one(PR + f'crest_{c}_{piece}.stl', c), 1, 'side', 'crest', c)
add('Nose clip', one(PR + 'nose_body_gold.stl', 'gold'), 1, 'upright', 'strong', 'gold')
add('Nose panel', one(PR + 'nose_panel_navy.stl', 'navy'), 1, 'upright', 'small', 'navy')
add('Nose rivet pin', one(PR + 'nose_pin_white.stl', 'white'), 1, 'nose_pin', 'small', 'white')
add('Seam dowel pin', one(PR + 'seam_dowel_pin_navy.stl', 'navy'), 7, 'as_is', 'pin', 'navy')
add('Front H badge', [(PR + 'H_badge_navy.stl', 'navy'), (PR + 'H_badge_white.stl', 'white'), (PR + 'H_badge_gold.stl', 'gold')], 1, 'face_up', 'badge', 'multi_tall')
# wings: right wing = A front + B back (shoulder back keyed); left wing = B front + A back (shoulder back keyed)
def half(base, side, key=False):
    parts = [(PW + f'wing_{base}_{side}{"key" if key else ""}_{c}.stl', c) for c in ('navy', 'gold', 'white')]
    return [(f, c) for f, c in parts if os.path.exists(f)]
for base in ('shoulder', 'front_edge', 'top_feathers', 'lower_feathers', 'lower_feathers2', 'hanging_feathers'):
    nice = base.replace('_', ' ').replace('feathers2', 'feathers (small)')
    lip = base in ('shoulder', 'front_edge')
    grp = 'multi_tall' if base == 'shoulder' else 'multi_flat'
    if base == 'shoulder':
        add('Wing R shoulder front', half(base, 'A'), 1, 'flat', 'half_s', grp)
        add('Wing R shoulder back (key)', half(base, 'B', key=True), 1, 'flat', 'half_s', grp)
        add('Wing L shoulder front', half(base, 'B'), 1, 'flat', 'half_s', grp)
        add('Wing L shoulder back (key)', half(base, 'A', key=True), 1, 'flat', 'half_s', grp)
    else:
        add(f'Wing {nice} A', half(base, 'A'), 2, 'flat', 'half_s' if lip else 'half', grp)
        add(f'Wing {nice} B', half(base, 'B'), 2, 'flat', 'half_s' if lip else 'half', grp)
for base in ('shoulder', 'front_edge', 'top_feathers', 'lower_feathers', 'hanging_feathers'):
    add('Wing middle ' + base.replace('_', ' '), one(PW + f'wing_{base}_core_white.stl', 'white'), 2, 'flat', 'core', 'white')
import pickle
WB = pickle.load(open('ref2/wing_build.pkl', 'rb'))
add('Wing pin 10 mm', one(PW + 'wing_pin_layer_white.stl', 'white'), 2 * WB['N_PIN_LAYER'] + 2, 'as_is', 'pin', 'white')
add('Wing pin 12 mm', one(PW + 'wing_pin_joint_white.stl', 'white'), 2 * WB['N_PIN_JOINT'] + 2, 'as_is', 'pin', 'white')

# ---------- orient every piece ----------
def oriented(p):
    meshes = [(trimesh.load(f), c) for f, c in p['parts']]
    allv = np.vstack([m.vertices for m, _ in meshes]); cen = allv.mean(0)
    o = p['orient']
    if o in ('upright', 'as_is', 'flat'): M = np.eye(4)
    elif o == 'tilt8': M = rot('x', 8)
    elif o == 'side': M = rot('y', 90)
    elif o == 'axis': M = align(outward(cen))                  # head / face up, pegs down
    elif o == 'nose_pin': M = align([0, -1, 0])
    elif o == 'mountR': M = align(NRM)                          # face toward the wing on the bed
    elif o == 'mountL': M = align(NRM * np.array([-1, 1, 1]))
    elif o == 'face_up':                                        # the H's flat face up
        g = trimesh.load(PR + 'H_badge_gold.stl'); v = g.vertices - g.vertices.mean(0)
        n = np.linalg.svd(v, full_matrices=False)[2][2]
        if n[1] > 0: n = -n                                   # the face points forward (-y)
        M = align(n)
    out = []
    for m, c in meshes:
        m = m.copy(); m.apply_transform(M); out.append((m, c))
    allv = np.vstack([m.vertices for m, _ in out]); lo, hi = allv.min(0), allv.max(0)
    shift = np.array([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]])
    for m, _ in out: m.apply_translation(shift)
    return out
def footprint(parts):
    """1 mm raster of the piece seen from above, grown by half the gap"""
    allv = np.vstack([m.vertices for m, _ in parts]); lo, hi = allv.min(0), allv.max(0)
    w, h = int(math.ceil((hi[0] - lo[0]) / RES)) + 1, int(math.ceil((hi[1] - lo[1]) / RES)) + 1
    img = Image.new('L', (w, h), 0); d = ImageDraw.Draw(img)
    for m, _ in parts:
        tri = (m.vertices[m.faces][:, :, :2] - lo[:2]) / RES
        for t in tri: d.polygon([tuple(q) for q in t], fill=1)
    return np.array(img, bool), lo[:2]

# ---------- packing ----------
NB = int(BED / RES)
DISK = ndimage.iterate_structure(ndimage.generate_binary_structure(2, 1), int(round(GAP / RES)))
def empty_plate(multi):
    border = np.zeros((NB, NB), bool); mg = int(math.ceil(MARGIN / RES))
    border[:mg, :] = border[-mg:, :] = border[:, :mg] = border[:, -mg:] = True
    if multi:
        t = int(TOWER / RES); border[NB - t:, :t] = True          # rows = y; top-left corner (high y, low x)
    return dict(raw=np.zeros((NB, NB), bool), check=border.copy(), border=border)
def try_place(pl, mask):
    """lowest, then left-most spot where the piece keeps GAP from other pieces and MARGIN from the edge"""
    mh, mw = mask.shape
    if mh > NB or mw > NB: return None
    hit = fftconvolve(pl['check'].astype(np.float32), mask[::-1, ::-1].astype(np.float32), mode='valid')
    free = np.argwhere(hit < 0.5)
    if len(free) == 0: return None
    k = np.lexsort((free[:, 1], free[:, 0]))[0]
    return tuple(free[k])
def commit(pl, r0, c0, mask):
    pl['raw'][r0:r0 + mask.shape[0], c0:c0 + mask.shape[1]] |= mask
    pl['check'] = ndimage.binary_dilation(pl['raw'], structure=DISK) | pl['border']
ANGLES = list(range(0, 360, 15))
plates = []
pieces_ready = {}
for i, p in enumerate(P):
    parts = oriented(p); pieces_ready[i] = parts
    base_mask, lo = footprint(parts)
    p['area'] = base_mask.sum()
    p['masks'] = {a: ndimage.rotate(base_mask.astype(np.uint8), a, reshape=True, order=0) > 0 for a in ANGLES}
    p['hgt'] = max(m.vertices[:, 2].max() for m, _ in parts)
    print(f"  {p['name']:32s} x{p['qty']:<3d} {base_mask.shape[1]:4d} x {base_mask.shape[0]:4d} mm  h {p['hgt']:6.1f}  [{p['group']}]")
for g in ('navy', 'white', 'gold', 'multi_tall', 'multi_flat'):
    todo = [(i, k) for i, p in enumerate(P) if p['group'] == g for k in range(p['qty'])]
    todo.sort(key=lambda ik: -P[ik[0]]['area'])
    for i, k in todo:
        p = P[i]
        for pl in [q for q in plates if q['group'] == g] + [None]:
            if pl is None:
                pl = dict(group=g, items=[], **empty_plate(g.startswith('multi'))); plates.append(pl)
            best = None
            for a, m in p['masks'].items():
                pos = try_place(pl, m)
                if pos is not None and (best is None or pos < best[0]): best = (pos, a, m)
            if best is None:
                if not pl['items']: raise SystemExit(f"{p['name']} does not fit an empty plate")
                continue
            (r0, c0), a, m = best
            commit(pl, r0, c0, m)
            cx, cy = (c0 + m.shape[1] / 2) * RES, (r0 + m.shape[0] / 2) * RES
            pl['items'].append((i, k, a, cx, cy))
            break
print(f'{len(plates)} plates')

# ---------- write the Orca project ----------
def fmt(x): return ('%.4f' % x).rstrip('0').rstrip('.') if abs(x) > 1e-9 else '0'
def mesh_xml(m):
    out = io.StringIO()
    out.write('    <mesh>\n     <vertices>\n')
    for v in m.vertices: out.write(f'      <vertex x="{fmt(v[0])}" y="{fmt(v[1])}" z="{fmt(v[2])}"/>\n')
    out.write('     </vertices>\n     <triangles>\n')
    for f in m.faces: out.write(f'      <triangle v1="{f[0]}" v2="{f[1]}" v3="{f[2]}"/>\n')
    out.write('     </triangles>\n    </mesh>\n')
    return out.getvalue()
NS = ('unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
      'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p"')
v = math.sqrt(len(plates)); cols = int(round(v)) + (1 if v > round(v) else 0)
STRIDE = BED * 1.2
z = zipfile.ZipFile(OUT3MF, 'w', zipfile.ZIP_DEFLATED, compresslevel=6)
main_objs, build_items, rels, cfg_objs, cfg_plates, assemble = [], [], [], [], [], []
next_id, obj_index, identify = 1, 0, 100
plate_names = {'navy': 'navy only', 'white': 'white only', 'gold': 'gold only', 'multi_tall': 'multi-colour', 'multi_flat': 'multi-colour'}
plate_rows = []
for pi, pl in enumerate(plates):
    row, col = pi // cols, pi % cols
    ox, oy = col * STRIDE, -row * STRIDE
    inst = []
    for (i, k, a, cx, cy) in pl['items']:
        p = P[i]; parts = pieces_ready[i]; obj_index += 1
        part_ids = list(range(next_id, next_id + len(parts))); obj_id = next_id + len(parts); next_id = obj_id + 1
        path = f'3D/Objects/object_{obj_index}.model'
        sub = io.StringIO()
        sub.write(f'<?xml version="1.0" encoding="UTF-8"?>\n<model {NS}>\n <metadata name="BambuStudio:3mfVersion">1</metadata>\n <resources>\n')
        R = rot('z', -a)          # the packing masks turn the opposite way (checked)
        for pid, (m, c) in zip(part_ids, parts):
            mm = m.copy(); mm.apply_transform(R)
            sub.write(f'  <object id="{pid}" p:UUID="{uuid.uuid4()}" type="model">\n')
            sub.write(mesh_xml(mm)); sub.write('  </object>\n')
        sub.write(' </resources>\n <build/>\n</model>\n')
        z.writestr(path, sub.getvalue())
        rels.append(path)
        comps = ''.join(f'    <component p:path="/{path}" objectid="{pid}" p:UUID="{uuid.uuid4()}" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>\n' for pid in part_ids)
        main_objs.append(f'  <object id="{obj_id}" p:UUID="{uuid.uuid4()}" type="model">\n   <components>\n{comps}   </components>\n  </object>\n')
        tx, ty = ox + cx, oy + cy
        tr = f'1 0 0 0 1 0 0 0 1 {fmt(tx)} {fmt(ty)} 0'
        build_items.append(f'  <item objectid="{obj_id}" p:UUID="{uuid.uuid4()}" transform="{tr}" printable="1"/>\n')
        name = p['name'] + (f' {k + 1}' if p['qty'] > 1 else '')
        main_colour = p['parts'][0][1]
        o = [f'  <object id="{obj_id}">\n', f'    <metadata key="name" value="{name}"/>\n', f'    <metadata key="extruder" value="{SLOT[main_colour]}"/>\n']
        for key, val in SET[p['settings']].items(): o.append(f'    <metadata key="{key}" value="{val}"/>\n')
        for pid, (m, c), (f, _) in zip(part_ids, parts, p['parts']):
            o.append(f'    <part id="{pid}" subtype="normal_part">\n')
            o.append(f'      <metadata key="name" value="{os.path.basename(f)[:-4]}"/>\n')
            o.append('      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>\n')
            o.append(f'      <metadata key="extruder" value="{SLOT[c]}"/>\n')
            o.append('      <mesh_stat edges_fixed="0" degenerate_facets="0" facets_removed="0" facets_reversed="0" backwards_edges="0"/>\n')
            o.append('    </part>\n')
        o.append('  </object>\n'); cfg_objs.append(''.join(o))
        inst.append(f'    <model_instance>\n      <metadata key="object_id" value="{obj_id}"/>\n      <metadata key="instance_id" value="0"/>\n      <metadata key="identify_id" value="{identify}"/>\n    </model_instance>\n')
        assemble.append(f'   <assemble_item object_id="{obj_id}" instance_id="0" transform="{tr}" offset="0 0 0"/>\n')
        identify += 1
    colours = sorted({c for (i, k, a, cx, cy) in pl['items'] for _, c in P[i]['parts']}, key=lambda c: SLOT[c])
    title = f'{pi + 1:02d} {plate_names[pl["group"]]}'
    cfg_plates.append(f'  <plate>\n    <metadata key="plater_id" value="{pi + 1}"/>\n    <metadata key="plater_name" value="{title}"/>\n    <metadata key="locked" value="false"/>\n'
                      + f'    <metadata key="thumbnail_file" value="Metadata/plate_{pi + 1}.png"/>\n' + ''.join(inst) + '  </plate>\n')
    # thumbnail: top view of the plate
    S = 2; img = Image.new('RGB', (int(BED * S), int(BED * S)), (58, 62, 70)); d = ImageDraw.Draw(img)
    if pl['group'].startswith('multi'): d.rectangle([0, 0, TOWER * S, TOWER * S], outline=(160, 160, 160))
    for (i, k, a, cx, cy) in pl['items']:
        R = rot('z', -a)          # the packing masks turn the opposite way (checked)
        for m, c in sorted(pieces_ready[i], key=lambda mc: mc[0].vertices[:, 2].max()):
            vv = (np.c_[m.vertices, np.ones(len(m.vertices))] @ R.T)[:, :2] + [cx, cy]
            top = m.faces[m.face_normals[:, 2] > 0.2]
            for t in vv[top]: d.polygon([(q[0] * S, (BED - q[1]) * S) for q in t], fill=RGB[c])
    buf = io.BytesIO(); img.resize((512, 512)).save(buf, 'PNG'); z.writestr(f'Metadata/plate_{pi + 1}.png', buf.getvalue())
    small = io.BytesIO(); img.resize((128, 128)).save(small, 'PNG'); z.writestr(f'Metadata/plate_{pi + 1}_small.png', small.getvalue())
    img.save(f'ref2/plate_{pi + 1:02d}.png')
    plate_rows.append(dict(plate=pi + 1, title=title, group=pl['group'], colours=colours,
                           pieces=[P[i]['name'] + (f' {k + 1}' if P[i]['qty'] > 1 else '') for (i, k, a, cx, cy) in pl['items']]))
model = (f'<?xml version="1.0" encoding="UTF-8"?>\n<model {NS}>\n'
         ' <metadata name="Application">OrcaSlicer-2.0.0</metadata>\n <metadata name="BambuStudio:3mfVersion">1</metadata>\n'
         ' <metadata name="Title">Winged varsity helmet</metadata>\n <metadata name="Designer"></metadata>\n'
         ' <resources>\n' + ''.join(main_objs) + ' </resources>\n'
         f' <build p:UUID="{uuid.uuid4()}">\n' + ''.join(build_items) + ' </build>\n</model>\n')
z.writestr('3D/3dmodel.model', model)
z.writestr('3D/_rels/3dmodel.model.rels', '<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
           + ''.join(f' <Relationship Target="/{p}" Id="rel-{i + 1}" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n' for i, p in enumerate(rels))
           + '</Relationships>')
z.writestr('Metadata/model_settings.config', '<?xml version="1.0" encoding="UTF-8"?>\n<config>\n' + ''.join(cfg_objs) + ''.join(cfg_plates)
           + '  <assemble>\n' + ''.join(assemble) + '  </assemble>\n</config>\n')
z.writestr('[Content_Types].xml', '<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
           ' <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
           ' <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>\n'
           ' <Default Extension="png" ContentType="image/png"/>\n <Default Extension="gcode" ContentType="text/x.gcode"/>\n</Types>')
z.writestr('_rels/.rels', '<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
           ' <Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n'
           ' <Relationship Target="/Metadata/plate_1.png" Id="rel-2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/thumbnail"/>\n'
           ' <Relationship Target="/Metadata/plate_1.png" Id="rel-4" Type="http://schemas.bambulab.com/package/2021/cover-thumbnail-middle"/>\n'
           ' <Relationship Target="/Metadata/plate_1_small.png" Id="rel-5" Type="http://schemas.bambulab.com/package/2021/cover-thumbnail-small"/>\n</Relationships>')
z.close()
json.dump(plate_rows, open('ref2/plates.json', 'w'), indent=1)
print('wrote', OUT3MF, '%.1f MB' % (os.path.getsize(OUT3MF) / 1e6))
for r in plate_rows: print(f"  plate {r['plate']:2d}  {r['title']:22s} {', '.join(r['colours']):18s} {len(r['pieces'])} pieces")
