import time, openscad as o
t=time.time()
s = o.scad(open('helmet/t.scad').read())
print(type(s))
o.export(s, 'helmet/t2.stl')
print('t', time.time()-t)
help(o.scad)
