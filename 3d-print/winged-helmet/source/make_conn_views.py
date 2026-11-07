# writes OpenSCAD view files that import the print pieces (exploded assembly + single-piece close-ups)
import glob, os, numpy as np, trimesh
D = 'out_v23/print/'
COL = {'navy': '"#1E2A52"', 'gold': '"#F2C12E"', 'white': '"#F4F4EE"'}
def colour(n): return COL['navy'] if 'navy' in n else COL['gold'] if 'gold' in n else COL['white']
names = sorted(os.path.basename(f)[:-4] for f in glob.glob('helmet/' + D + '*.stl'))
cent = {n: trimesh.load('helmet/' + D + n + '.stl').bounding_box.centroid for n in names}
def explode(n):
    c = cent[n].copy()
    if n.startswith('shell_front'): return [0, -30, 0]
    if n.startswith('shell_back'): return [0, 30, 0]
    lay = {'white': 1, 'gold': 2, 'navy': 3}
    if n.startswith('band_'):
        col = n.split('_')[1] if n.split('_')[1] in lay else 'gold'
        k = 22 + 16 * lay.get(col, 2) if not n.startswith('band_V') else 70
        d = np.array([c[0], c[1] / 1.235, 0]); d /= np.linalg.norm(d) + 1e-9
        return (d * k + np.array([0, 0, -10])).round(1).tolist()
    if n.startswith('cheek'):
        s = 1 if c[0] > 0 else -1
        k = {'guard': 45, 'frame': 85, 'H': 115, 'rivet': 115}[n.split('_')[1]]
        return [s * k, -10, -40]
    if n.startswith('neck'): return [0, 60, -45]
    if n.startswith('crest'): return [0, 0, 55 if 'white' in n else 85]
    if n.startswith('H_badge'): return [0, {'navy': -60, 'white': -78, 'gold': -94}[n.split('_')[2]], 10]
    if n.startswith('nose'): return [0, {'body': -60, 'panel': -78, 'white': -92}.get(n.split('_')[1], -92), -50]
    return [0, 0, 0]
skip = {'seam_dowel_pin_navy'}
with open('helmet/conn_explode_view.scad', 'w') as f:
    f.write('// exploded assembly of the print pieces (connectors visible)\nex = 1;\n')
    for n in names:
        if n in skip: continue
        e = explode(n)
        f.write(f'color({colour(n)}) translate(ex * {e}) import("{D}{n}.stl");\n')
print(len(names), 'pieces')
