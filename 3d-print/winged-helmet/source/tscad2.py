import time, _openscad as o
t=time.time()
try:
    s = o.scad("sphere(5);")
    print('ok scad', s)
except Exception as e: print('scad fail', e)
try:
    s = o.osinclude('helmet/t.scad'); print('osinclude', s, dir(s)[:5])
except Exception as e: print('osinclude fail', repr(e))
