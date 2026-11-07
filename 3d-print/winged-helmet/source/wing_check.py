import glob, numpy as np, trimesh, manifold3d as m3
exec(open('wing_build.py').read().split("if __name__ == '__main__':")[0])
D = 'helmet/out_v23/print_wing/'
def L(n): return to_m(trimesh.load(D + n + '.stl'))
# 1. every half (all colours together) is one solid
for nm in NAMES:
    for side in ('A', 'B') + (('Akey', 'Bkey') if nm == 'shoulder' else ()):
      for pn in [nm] + sorted({os.path.basename(f).split('_A_')[0][5:] for f in glob.glob(D + f'wing_{nm}[0-9]_A_navy.stl')}):
        cols = [L(f'wing_{pn}_{side}_navy')] + [L(f'wing_{pn}_{side[0]}_{c}') for c in ('gold', 'white') if os.path.exists(D + f'wing_{pn}_{side[0]}_{c}.stl')]
        u = union(cols); n = len([q for q in u.decompose() if q.volume() > 1])
        print(f'{pn:18s} {side:5s} one solid: {n == 1}' + ('' if n == 1 else f'  ({n} parts)'))
# 2. assembled right wing (flat frame) vs the approved OpenSCAD wing, per colour
asm = {c: [] for c in ('navy', 'gold', 'white')}
for f in sorted(glob.glob(D + 'wing_*_A_*.stl')):
    c = f.rsplit('_', 1)[1][:-4]
    m = to_m(trimesh.load(f)); asm[c] += [front_frame(m), back_frame(m)]
for f in sorted(glob.glob(D + 'wing_*_core_white.stl')): asm['white'].append(to_m(trimesh.load(f)).translate([0, 0, -MID_T / 2]))
for c in asm:
    mine = placed(union(asm[c]))
    ref = to_m(trimesh.load(f'helmet/out_v23/wingB_{c}.stl'))
    print(f'{c:5s} pieces {mine.volume()/1000:7.1f} cm3   approved wing {ref.volume()/1000:7.1f} cm3   shared {(mine ^ ref).volume()/1000:7.1f} cm3')
