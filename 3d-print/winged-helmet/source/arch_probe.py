src = open('fit_ring_build.py').read()
exec(src[:src.index('zs = np.linspace(0, H, 41)')])
import glob
Z0 = 15.0
def r_out(z, T_=2.4): return (RI + T_) * (1 - min(z / (HI + T_), 1) ** P) ** (1 / P)
zz = np.linspace(Z0, HI, 120)
dome_cav = stretch(revolve([(0, Z0), *[(r_in(z) + 0.4, z) for z in zz], (0, HI + 0.4)]))
slab = m3.Manifold.cube([15.0, 600, 400]).translate([-7.5, -300, 0])
strip = dome_cav ^ slab
SKIP = ('wing', 'seam_dowel_pin', 'nose_pin')
for f in sorted(glob.glob(PR + '*.stl')):
    if any(k in f for k in SKIP) and 'wing_mount' not in f: continue
    m = to_m(trimesh.load(f)) ^ strip
    if m.volume() < 0.5: continue
    t = to_t(m); pts = t.sample(5000)
    rho = np.sqrt(pts[:, 0] ** 2 + (pts[:, 1] / K) ** 2)
    # depth below the dome surface along the radial direction in the circular frame (approx.)
    dep = np.array([r_in(z) for z in pts[:, 2]]) - rho
    sel = dep > 0.5
    if sel.any():
        p = pts[sel]
        print(f'{f.split("/")[-1]:26s} reaches {dep[sel].max():4.1f} mm in; y {p[:, 1].min():6.0f}..{p[:, 1].max():6.0f}  z {p[:, 2].min():5.0f}..{p[:, 2].max():5.0f}')
# vertical headroom along the centreline: shell inner surface z at x=0 for several y
S = union([to_m(trimesh.load(PR + f'shell_{p}_navy.stl')) for p in ('front', 'back')])
T_ = to_t(S)
for y in (-120, -90, -60, -30, -10, 0, 10, 30, 60, 90, 120):
    locs, _, _ = T_.ray.intersects_location([[0, y, 0]], [[0, 0, 1]], multiple_hits=True)
    zs_ = sorted(locs[:, 2]) if len(locs) else []
    zf = K * 0 + HI * (1 - min(abs(y) / (RI * K), 1) ** P) ** (1 / P)
    print(f'y {y:5d}: shell hits z {[round(v, 1) for v in zs_[:4]]}  formula inner z {zf:6.1f}')
