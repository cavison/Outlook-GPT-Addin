src = open('wing2_build.py').read().split('JOINTS = {}\nORDER')[0]
exec(src)
JOINTS = {}; TAKEN = {}
n = 'F4'; hb = HOST[n]; a = OUTL[n]
ok = host_room(n); near, cover = a.buffer(3.5), unary_union([a.buffer(0.6), OUTL[hb]])
print('F4 bounds', np.round(a.bounds, 1))
for mid, ang in (((88, 42), 180), ((88, 42), 160), ((90, 44), 150), ((86, 41), 180)):
    nr = np.array([math.cos(math.radians(ang)), math.sin(math.radians(ang))]); u = np.array([nr[1], -nr[0]])
    for w in (9.0, 10.0):
        t, sk, root, fl = joint_shape(np.array(mid, float), u, nr, w, 22.0, 1.5)
        print(mid, ang, w, 'leak', round(sk.difference(cover).area, 1), 'wall', round(sk.difference(near).difference(ok).area, 1), 'root out', round(root.difference(a.buffer(0.6)).area / root.area, 2))
