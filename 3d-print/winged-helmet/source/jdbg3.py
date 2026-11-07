src = open('wing2_build.py').read().split('# pegs and lightening holes in the hub')[0]
exec(src)
for k in list(FE) + ['CU', 'CL']:
    g = OUTL[k]
    print(k, g.geom_type, 'interiors', [round(Polygon(i).area, 1) for i in getattr(g, 'interiors', [])][:20])
for k in ('CU', 'CL'):
    print(k, 'REG interiors', [round(Polygon(i).area, 1) for i in getattr(REG[k], 'interiors', [])][:20], 'REG∩disc area', round(REG[k].intersection(disc).area, 1))
