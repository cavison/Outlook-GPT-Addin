import sys
exec(open('jdbg5.py').read().split('from PIL import')[0])
n = sys.argv[1]; hb = HOST[n]; a = OUTL[n]
ok = host_room(n); near, cover = a.buffer(3.5), unary_union([a.buffer(0.6), OUTL[hb]])
line = a.exterior.intersection(OUTL[hb].buffer(1.0))
print('line', line.geom_type, [(g.geom_type, round(g.length, 1)) for g in getattr(line, 'geoms', [line])])
print('dist', round(a.distance(OUTL[hb]), 2))
mx, my, ang = float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
nr = np.array([math.cos(math.radians(ang)), math.sin(math.radians(ang))]); u = np.array([nr[1], -nr[0]])
for w in (10.0, 14.0, 18.0):
    for dep in (18.0, 22.0):
        t, sk, root, fl = joint_shape(np.array([mx, my]), u, nr, w, dep, 3.0)
        print(w, dep, 'leak', round(sk.difference(cover).area, 1), 'wall', round(sk.difference(near).difference(ok).area, 1), 'root out', round(root.difference(a.buffer(0.6)).area / root.area, 2))
for pt in ((-20, -50), (-20, -40), (-20, -64), (-20, -70), (-30, -50)):
    print(pt, 'CL', OUTL['CL'].contains(Point(*pt)), 'F9', OUTL['F9'].contains(Point(*pt)), 'ok', ok.contains(Point(*pt)))
print('F9 bounds', np.round(OUTL['F9'].bounds, 1), 'CL bounds', np.round(OUTL['CL'].bounds, 1))
print('line coords', np.round(np.array(line.coords)[::4], 1).tolist())
