# side + top views of a G-code file: model in grey, support in red
import sys, numpy as np
from PIL import Image, ImageDraw
def load(gc):
    x = y = z = 0.0; typ = None; segs = []
    for line in open(gc):
        if line.startswith(';TYPE:'): typ = line[6:].strip(); continue
        if not line.startswith('G1'): continue
        nx, ny, nz, e = x, y, z, 0.0
        for w in line.split(';')[0].split()[1:]:
            k, v = w[0], w[1:]
            if k == 'X': nx = float(v)
            elif k == 'Y': ny = float(v)
            elif k == 'Z': nz = float(v)
            elif k == 'E': e = float(v)
        if e > 0 and typ: segs.append((x, y, nx, ny, nz, 'Support' in typ))
        x, y, z = nx, ny, nz
    return np.array([s[:5] for s in segs]), np.array([s[5] for s in segs])
def draw(gc, out, title):
    S, sup = load(gc)
    W = 330; img = Image.new('RGB', (3 * W, W + 20), 'white'); d = ImageDraw.Draw(img); sc = 1.4
    for j, (u, v) in enumerate(((0, 4), (1, 4), (0, 1))):
        ox = j * W + 8
        for flag, col in ((False, (150, 150, 150)), (True, (220, 30, 30))):
            P = S[sup == flag][::3]
            for s in P:
                if v == 4: d.point((ox + s[u] * sc, W + 5 - s[4] * sc), fill=col)
                else: d.line([(ox + s[0] * sc, W + 5 - s[1] * sc), (ox + s[2] * sc, W + 5 - s[3] * sc)], fill=col)
    d.text((5, 3), title, fill='black'); img.save(out)
if __name__ == '__main__':
    draw(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else sys.argv[1])
