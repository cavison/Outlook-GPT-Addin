#!/usr/bin/env python
# Orca project for the fit-test rings: plate 1 = helmet ring (4 pieces, navy), plate 2 = head ring (white)
import io, os, json, math, uuid, zipfile, subprocess
import numpy as np, trimesh
from PIL import Image, ImageDraw
D = 'helmet/out_v23/fit_test/'; OUT3MF = 'pkg/fit_test_AD5X.3mf'
BED = 220.0
SLOT = {'navy': 1, 'white': 2, 'gold': 3}; RGB = {'navy': (30, 42, 82), 'white': (236, 236, 228), 'gold': (242, 193, 46)}
SET = dict(wall_loops='4', sparse_infill_density='15%', brim_type='no_brim', enable_support='0')
# (name, file, colour, plate, centre x, centre y, turn deg)
ITEMS = [('Fit band side L', 'fit_side_L', 'navy', 0, 28, 110, 0), ('Fit band front', 'fit_front', 'navy', 0, 80, 110, 90),
         ('Fit band back', 'fit_back', 'navy', 0, 137, 110, 90), ('Fit band side R', 'fit_side_R', 'navy', 0, 189, 110, 0),
         ('Top strap front half', 'fit_arch_front', 'navy', 1, 9 + 145.6 / 2, 16 + 138.4 / 2, 0),
         ('Top strap back half', 'fit_arch_back', 'navy', 1, 9 + 62 + 139.0 / 2, 16 + 44 + 138.4 / 2, 0)]
PLATES = ['01 Fit band (helmet inside at the brow, 4 pieces)', '02 Top strap (helmet inside, front to back, 2 halves)']
def fmt(x): return ('%.4f' % x).rstrip('0').rstrip('.') if abs(x) > 1e-9 else '0'
def mesh_xml(m):
    out = io.StringIO(); out.write('    <mesh>\n     <vertices>\n')
    for v in m.vertices: out.write(f'      <vertex x="{fmt(v[0])}" y="{fmt(v[1])}" z="{fmt(v[2])}"/>\n')
    out.write('     </vertices>\n     <triangles>\n')
    for f in m.faces: out.write(f'      <triangle v1="{f[0]}" v2="{f[1]}" v3="{f[2]}"/>\n')
    out.write('     </triangles>\n    </mesh>\n'); return out.getvalue()
NS = ('unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
      'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p"')
STRIDE = BED * 1.2
z = zipfile.ZipFile(OUT3MF, 'w', zipfile.ZIP_DEFLATED, compresslevel=6)
main_objs, build_items, rels, cfg_objs, assemble = [], [], [], [], []
inst = {0: [], 1: []}; placed = {0: [], 1: []}
nid, identify = 1, 100
for k, (name, f, c, pl, cx, cy, turn) in enumerate(ITEMS):
    m = trimesh.load(D + f + '.stl')
    a = math.radians(turn); R = np.array([[math.cos(a), -math.sin(a), 0, 0], [math.sin(a), math.cos(a), 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])
    m.apply_transform(R); b = m.bounds; m.apply_translation([-(b[0][0] + b[1][0]) / 2, -(b[0][1] + b[1][1]) / 2, -b[0][2]])
    e = m.extents
    assert cx - e[0] / 2 >= 3 and cx + e[0] / 2 <= 217 and cy - e[1] / 2 >= 3 and cy + e[1] / 2 <= BED - 3.5, (name, e)
    placed[pl].append((m, c, cx, cy))
    pid, oid = nid, nid + 1; nid += 2
    path = f'3D/Objects/object_{k + 1}.model'
    z.writestr(path, f'<?xml version="1.0" encoding="UTF-8"?>\n<model {NS}>\n <metadata name="BambuStudio:3mfVersion">1</metadata>\n <resources>\n'
               f'  <object id="{pid}" p:UUID="{uuid.uuid4()}" type="model">\n' + mesh_xml(m) + '  </object>\n </resources>\n <build/>\n</model>\n')
    rels.append(path)
    main_objs.append(f'  <object id="{oid}" p:UUID="{uuid.uuid4()}" type="model">\n   <components>\n'
                     f'    <component p:path="/{path}" objectid="{pid}" p:UUID="{uuid.uuid4()}" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>\n   </components>\n  </object>\n')
    ox, oy = pl * STRIDE, 0.0                         # plates in a row
    tr = f'1 0 0 0 1 0 0 0 1 {fmt(ox + cx)} {fmt(oy + cy)} 0'
    build_items.append(f'  <item objectid="{oid}" p:UUID="{uuid.uuid4()}" transform="{tr}" printable="1"/>\n')
    o = [f'  <object id="{oid}">\n', f'    <metadata key="name" value="{name}"/>\n', f'    <metadata key="extruder" value="{SLOT[c]}"/>\n']
    o += [f'    <metadata key="{kk}" value="{vv}"/>\n' for kk, vv in SET.items()]
    o += [f'    <part id="{pid}" subtype="normal_part">\n', f'      <metadata key="name" value="{f}"/>\n',
          '      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>\n', f'      <metadata key="extruder" value="{SLOT[c]}"/>\n',
          '      <mesh_stat edges_fixed="0" degenerate_facets="0" facets_removed="0" facets_reversed="0" backwards_edges="0"/>\n', '    </part>\n  </object>\n']
    cfg_objs.append(''.join(o))
    inst[pl].append(f'    <model_instance>\n      <metadata key="object_id" value="{oid}"/>\n      <metadata key="instance_id" value="0"/>\n      <metadata key="identify_id" value="{identify}"/>\n    </model_instance>\n')
    assemble.append(f'   <assemble_item object_id="{oid}" instance_id="0" transform="{tr}" offset="0 0 0"/>\n'); identify += 1
cfg_plates = []
for pl, title in enumerate(PLATES):
    cfg_plates.append(f'  <plate>\n    <metadata key="plater_id" value="{pl + 1}"/>\n    <metadata key="plater_name" value="{title}"/>\n    <metadata key="locked" value="false"/>\n'
                      f'    <metadata key="thumbnail_file" value="Metadata/plate_{pl + 1}.png"/>\n' + ''.join(inst[pl]) + '  </plate>\n')
    S = 2; img = Image.new('RGB', (int(BED * S), int(BED * S)), (58, 62, 70)); d = ImageDraw.Draw(img)
    tris = []
    for m, c, cx, cy in placed[pl]:
        sel = m.face_normals[:, 2] > 0.2
        for t, zz in zip(m.vertices[m.faces[sel]][:, :, :2] + [cx, cy], m.triangles_center[sel, 2]): tris.append((zz, t, RGB[c]))
    for zz, t, col in sorted(tris, key=lambda x: x[0]): d.polygon([(q[0] * S, (BED - q[1]) * S) for q in t], fill=col)
    buf = io.BytesIO(); img.resize((512, 512)).save(buf, 'PNG'); z.writestr(f'Metadata/plate_{pl + 1}.png', buf.getvalue())
    small = io.BytesIO(); img.resize((128, 128)).save(small, 'PNG'); z.writestr(f'Metadata/plate_{pl + 1}_small.png', small.getvalue())
    img.save(f'ref2/fit_plate_{pl + 1}.png')
model = (f'<?xml version="1.0" encoding="UTF-8"?>\n<model {NS}>\n <metadata name="Application">OrcaSlicer-2.3.0</metadata>\n <metadata name="BambuStudio:3mfVersion">1</metadata>\n'
         ' <metadata name="Title">Winged helmet - fit test rings</metadata>\n <metadata name="Designer"></metadata>\n <resources>\n' + ''.join(main_objs) + ' </resources>\n'
         f' <build p:UUID="{uuid.uuid4()}">\n' + ''.join(build_items) + ' </build>\n</model>\n')
z.writestr('3D/3dmodel.model', model)
z.writestr('3D/_rels/3dmodel.model.rels', '<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
           + ''.join(f' <Relationship Target="/{p}" Id="rel-{i + 1}" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n' for i, p in enumerate(rels)) + '</Relationships>')
exec(open('make_project_config.py').read().split("if __name__ == '__main__':")[0])
PCFG = build(len(PLATES), ['#1E2A52', '#ECECE4', '#F2C12E'], (15, BED - 28 + 1))
PCFG['enable_prime_tower'] = '0'                       # single colour plates: no tower
z.writestr('Metadata/project_settings.config', json.dumps(PCFG, indent=4))
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
print('wrote', OUT3MF, '%.1f MB' % (os.path.getsize(OUT3MF) / 1e6))
# print time per plate (PrusaSlicer, same base settings)
os.makedirs('ps/fit', exist_ok=True)
for pl, title in enumerate(PLATES):
    ms = []
    for m, c, cx, cy in placed[pl]:
        mm = m.copy(); mm.apply_translation([cx, cy, 0]); ms.append(mm)
    stl = f'ps/fit/plate_{pl + 1}.stl'; trimesh.util.concatenate(ms).export(stl)
    gc = stl[:-4] + '.gcode'
    if os.path.exists(gc): os.remove(gc)
    subprocess.run(['prusa-slicer', '--export-gcode', '--load', 'ps/base.ini', '--use-relative-e-distances', '--fill-density', '15%', '--perimeters', '4',
                    '--no-support-material', '--dont-arrange', stl, '--output', gc], capture_output=True, timeout=1800)
    t = g = None
    for line in open(gc):
        if line.startswith('; estimated printing time (normal mode)'): t = line.split('=')[1].strip()
        if line.startswith('; total filament used [g]'): g = line.split('=')[1].strip()
    print(f'  {title}: {t}, {g} g')
