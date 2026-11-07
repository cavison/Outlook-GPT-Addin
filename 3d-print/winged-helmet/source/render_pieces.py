# one picture per key piece, from the side that shows its connectors
import subprocess, numpy as np, trimesh, concurrent.futures as cf
P = 'out_v23/print/'
COL = {'navy': '#1E2A52', 'gold': '#F2C12E', 'white': '#F4F4EE'}
def col(n): return COL['navy'] if 'navy' in n else COL['gold'] if 'gold' in n else COL['white']
VIEWS_ALL = [  # name, parts, eye offset direction (from piece centre), distance factor
    ('v_shell_front_in', ['shell_front_navy'], (0.0, 1.0, -0.75), 1.5),
    ('v_shell_back_in', ['shell_back_navy'], (0.75, -1.0, -0.35), 1.4),
    ('v_guard_in', ['cheek_guard_R_navy'], (-1.0, 0.25, 0.3), 1.6),
    ('v_frame_back', ['cheek_frame_R_gold'], (-1.0, 0.1, 0.15), 1.6),
    ('v_neck_in', ['neck_plate_navy'], (0.0, -0.55, -1.0), 1.5),
    ('v_band_white_back', ['band_white_F'], (0.0, 1.0, 0.35), 1.5),
    ('v_band_gold_back', ['band_gold_F'], (0.0, 1.0, 0.35), 1.5),
    ('v_band_navy_back', ['band_navy_F'], (0.0, 1.0, 0.35), 1.5),
    ('v_crest_under', ['crest_white_back', 'crest_gold_back'], (0.9, 0.2, -0.55), 1.5),
    ('v_H_back', ['H_badge_navy', 'H_badge_white', 'H_badge_gold'], (0.55, 1.0, 0.1), 1.8),
    ('v_small', ['cheek_H_R_white', 'cheek_rivet_R_white'], (-1.0, 0.3, 0.2), 2.6),
    ('v_V', ['band_V_gold', 'band_V_navy'], (0.2, -1.0, 0.1), 1.8),
    ('v_neck_out', ['neck_plate_navy'], (0.35, 1.0, 0.75), 1.3),
    ('v_guard_out', ['cheek_guard_R_navy'], (1.0, -0.2, 0.7), 1.3),
]
import sys
ONLY = sys.argv[1:]
VIEWS = [v for v in VIEWS_ALL if not ONLY or v[0] in ONLY]
def go(v):
    name, parts, d, k = v
    ms = [trimesh.load('helmet/' + P + p + '.stl') for p in parts]
    b = np.vstack([m.bounds for m in ms]); c = (b.min(0) + b.max(0)) / 2; size = np.linalg.norm(b.max(0) - b.min(0))
    d = np.array(d, float); d /= np.linalg.norm(d); eye = c + d * size * k
    scad = ''.join(f'color("{col(p)}") import("{P}{p}.stl");\n' for p in parts)
    open(f'helmet/_{name}.scad', 'w').write(scad)
    cam = ','.join(f'{x:.1f}' for x in list(eye) + list(c))
    subprocess.run(['timeout', '600', 'xvfb-run', '-a', 'openscad', '-o', f'sheet/{name}.png', '--imgsize=800,700', f'--camera={cam}',
                    '--projection=p', '--colorscheme=Tomorrow', f'_{name}.scad'], cwd='helmet', capture_output=True)
    return name
with cf.ThreadPoolExecutor(4) as ex:
    for n in ex.map(go, VIEWS): print('done', n)
