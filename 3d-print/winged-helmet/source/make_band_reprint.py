#!/usr/bin/env python
# One-plate Orca project with the three navy band pieces to reprint (thicker versions), taken straight from the
# updated main project: same print orientation and per-piece settings (tree supports, brim).
import io, re, os, json, uuid, zipfile
import numpy as np, trimesh
from PIL import Image, ImageDraw
from shapely.geometry import MultiPoint
MAIN, OUT3MF = 'pkg/winged_helmet_AD5X.3mf', 'pkg/band_reprint_AD5X.3mf'
BED = 220.0
# (name in the main project, centre x, centre y on the plate)
ITEMS = [('Band navy F', 110, 62), ('Band navy L', 62, 162), ('Back V navy', 160, 162)]
z = zipfile.ZipFile(MAIN)
cfg = z.read('Metadata/model_settings.config').decode(); main = z.read('3D/3dmodel.model').decode()
def fmt(x): return ('%.4f' % x).rstrip('0').rstrip('.') if abs(x) > 1e-9 else '0'
def mesh_xml(V, Fc):
    out = io.StringIO(); out.write('    <mesh>\n     <vertices>\n')
    for v in V: out.write(f'      <vertex x="{fmt(v[0])}" y="{fmt(v[1])}" z="{fmt(v[2])}"/>\n')
    out.write('     </vertices>\n     <triangles>\n')
    for f in Fc: out.write(f'      <triangle v1="{f[0]}" v2="{f[1]}" v3="{f[2]}"/>\n')
    out.write('     </triangles>\n    </mesh>\n'); return out.getvalue()
NS = ('unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
      'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p"')
zo = zipfile.ZipFile(OUT3MF, 'w', zipfile.ZIP_DEFLATED, compresslevel=6)
main_objs, build_items, rels, cfg_objs, inst, assemble, shapes = [], [], [], [], [], [], []
nid, ident = 1, 100
for k, (name, cx, cy) in enumerate(ITEMS):
    i = cfg.find(f'<metadata key="name" value="{name}"/>'); blk = cfg[cfg.rfind('<object', 0, i):cfg.find('</object>', i) + len('</object>')]
    oid = re.search(r'<object id="(\d+)"', blk).group(1)
    ob = main[main.find(f'<object id="{oid}"'):]; ob = ob[:ob.find('</object>')]
    path = re.search(r'p:path="/([^"]+)"', ob).group(1)
    xml = z.read(path).decode()
    V = np.array([[float(a), float(b), float(c)] for a, b, c in re.findall(r'<vertex x="([^"]+)" y="([^"]+)" z="([^"]+)"', xml)])
    Fc = np.array([[int(a), int(b), int(c)] for a, b, c in re.findall(r'<triangle v1="(\d+)" v2="(\d+)" v3="(\d+)"', xml)])
    hull = MultiPoint(V[:, :2] + [cx, cy]).convex_hull
    shapes.append((name, hull.buffer(4.0)))          # with the brim
    assert hull.bounds[0] >= 3 and hull.bounds[2] <= BED - 3 and hull.bounds[1] >= 3 and hull.bounds[3] <= BED - 3.5, (name, hull.bounds)
    pid, new_oid = nid, nid + 1; nid += 2
    p2 = f'3D/Objects/object_{k + 1}.model'
    zo.writestr(p2, f'<?xml version="1.0" encoding="UTF-8"?>\n<model {NS}>\n <metadata name="BambuStudio:3mfVersion">1</metadata>\n <resources>\n'
                f'  <object id="{pid}" p:UUID="{uuid.uuid4()}" type="model">\n' + mesh_xml(V, Fc) + '  </object>\n </resources>\n <build/>\n</model>\n')
    rels.append(p2)
    main_objs.append(f'  <object id="{new_oid}" p:UUID="{uuid.uuid4()}" type="model">\n   <components>\n'
                     f'    <component p:path="/{p2}" objectid="{pid}" p:UUID="{uuid.uuid4()}" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>\n   </components>\n  </object>\n')
    tr = f'1 0 0 0 1 0 0 0 1 {fmt(cx)} {fmt(cy)} 0'
    build_items.append(f'  <item objectid="{new_oid}" p:UUID="{uuid.uuid4()}" transform="{tr}" printable="1"/>\n')
    b2 = re.sub(r'<object id="\d+">', f'<object id="{new_oid}">', blk, count=1)
    b2 = re.sub(r'<part id="\d+"', f'<part id="{pid}"', b2, count=1)
    cfg_objs.append('  ' + b2 + '\n')
    inst.append(f'    <model_instance>\n      <metadata key="object_id" value="{new_oid}"/>\n      <metadata key="instance_id" value="0"/>\n      <metadata key="identify_id" value="{ident}"/>\n    </model_instance>\n')
    assemble.append(f'   <assemble_item object_id="{new_oid}" instance_id="0" transform="{tr}" offset="0 0 0"/>\n'); ident += 1
for a in range(len(shapes)):
    for b in range(a + 1, len(shapes)):
        assert shapes[a][1].distance(shapes[b][1]) > 2, (shapes[a][0], shapes[b][0])
title = '01 Band reprint (navy) - thicker band pieces'
plate = (f'  <plate>\n    <metadata key="plater_id" value="1"/>\n    <metadata key="plater_name" value="{title}"/>\n    <metadata key="locked" value="false"/>\n'
         '    <metadata key="thumbnail_file" value="Metadata/plate_1.png"/>\n' + ''.join(inst) + '  </plate>\n')
img = Image.new('RGB', (440, 440), (58, 62, 70)); d = ImageDraw.Draw(img)
for name, sh in shapes:
    d.polygon([(x * 2, (BED - y) * 2) for x, y in sh.buffer(-4.0).exterior.coords], fill=(30, 42, 82), outline=(120, 140, 200))
buf = io.BytesIO(); img.resize((512, 512)).save(buf, 'PNG'); zo.writestr('Metadata/plate_1.png', buf.getvalue())
small = io.BytesIO(); img.resize((128, 128)).save(small, 'PNG'); zo.writestr('Metadata/plate_1_small.png', small.getvalue())
img.save('ref2/band_reprint_plate.png')
zo.writestr('3D/3dmodel.model', f'<?xml version="1.0" encoding="UTF-8"?>\n<model {NS}>\n <metadata name="Application">OrcaSlicer-2.3.0</metadata>\n <metadata name="BambuStudio:3mfVersion">1</metadata>\n'
            ' <metadata name="Title">Winged helmet - band reprint</metadata>\n <metadata name="Designer"></metadata>\n <resources>\n' + ''.join(main_objs) + ' </resources>\n'
            f' <build p:UUID="{uuid.uuid4()}">\n' + ''.join(build_items) + ' </build>\n</model>\n')
zo.writestr('3D/_rels/3dmodel.model.rels', '<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
            + ''.join(f' <Relationship Target="/{p}" Id="rel-{i + 1}" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n' for i, p in enumerate(rels)) + '</Relationships>')
exec(open('make_project_config.py').read().split("if __name__ == '__main__':")[0])
PCFG = build(1, ['#1E2A52', '#ECECE4', '#F2C12E'], (15, BED - 28 + 1)); PCFG['enable_prime_tower'] = '0'
zo.writestr('Metadata/project_settings.config', json.dumps(PCFG, indent=4))
zo.writestr('Metadata/model_settings.config', '<?xml version="1.0" encoding="UTF-8"?>\n<config>\n' + ''.join(cfg_objs) + plate
            + '  <assemble>\n' + ''.join(assemble) + '  </assemble>\n</config>\n')
zo.writestr('[Content_Types].xml', '<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
            ' <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
            ' <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>\n'
            ' <Default Extension="png" ContentType="image/png"/>\n <Default Extension="gcode" ContentType="text/x.gcode"/>\n</Types>')
zo.writestr('_rels/.rels', '<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
            ' <Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n'
            ' <Relationship Target="/Metadata/plate_1.png" Id="rel-2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/thumbnail"/>\n'
            ' <Relationship Target="/Metadata/plate_1.png" Id="rel-4" Type="http://schemas.bambulab.com/package/2021/cover-thumbnail-middle"/>\n'
            ' <Relationship Target="/Metadata/plate_1_small.png" Id="rel-5" Type="http://schemas.bambulab.com/package/2021/cover-thumbnail-small"/>\n</Relationships>')
zo.close()
print('wrote', OUT3MF, '%.1f MB' % (os.path.getsize(OUT3MF) / 1e6))
