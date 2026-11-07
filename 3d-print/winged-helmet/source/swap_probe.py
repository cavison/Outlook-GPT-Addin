# colour bands by height for each multi-colour piece (to estimate filament swaps per plate)
import numpy as np, trimesh
exec(open('plates_build.py').read().split('# ---------- packing ----------')[0].split('# ---------- orient every piece ----------')[0])
exec('def _o():\n pass')
src = open('plates_build.py').read()
exec(src[src.index('# ---------- orient every piece ----------'):src.index('# ---------- packing ----------')])
LH0, LH = 0.25, 0.2
def layers(h):
    z = [LH0]; 
    while z[-1] < h - 1e-6: z.append(z[-1] + LH)
    return np.array(z)
for p in P:
    if not p['group'].startswith('multi'): continue
    parts = oriented(p)
    print(p['name'], 'h %.1f' % max(m.vertices[:, 2].max() for m, _ in parts))
    for m, c in parts:
        bodies = m.split(only_watertight=False)
        rngs = sorted((b.bounds[0, 2], b.bounds[1, 2]) for b in bodies)
        zs = [r for r in rngs]
        print('   %-6s %3d bodies  z %s' % (c, len(bodies), ' '.join('%.1f-%.1f' % r for r in zs[:6]) + (' ...' if len(zs) > 6 else '')))
