src = open('wing2_build.py').read().split('JOINTS = {n: joint(n) for n in FE}')[0]
src = src.replace("    assert best is not None, n\n", "    if best is None:\n        DBG[n] = dict(L=L, u=u, nr=nr, mid=mid, ok=ok, near=near, w_max=w_max, socket=socket); return None\n")
DBG = {}
exec(src)
J = {}
for n in FE:
    J[n] = joint(n)
    if J[n]: print(n, J[n][2])
for n, d in DBG.items():
    print('FAIL', n, 'L', round(d['L'], 1), 'w_max', round(d['w_max'], 1), 'u', d['u'].round(2), 'nr', d['nr'].round(2))
    for dep in (16.0, 20.0):
        for w in (d['w_max'], 16.0, 12.0, 10.0):
            sk = d['socket'](w, dep)
            print('  dep', dep, 'w', round(w, 1), 'outside ok', round(sk.difference(d['near']).difference(d['ok']).area, 1))
import pickle; pickle.dump({n: {k: v for k, v in d.items() if k != 'socket'} for n, d in DBG.items()}, open('ref2/jdbg.pkl', 'wb'))
