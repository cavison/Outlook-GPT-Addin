# old vs new feather-tab strength: push at the far tip of each piece that bends its tab root to 40 MPa
import re, ast, json
SIG = 40.0
EDGE = {'F1': 52.8, 'F2': 22.1, 'F3': 26.7, 'F4': 38.2, 'F5': 33.6, 'F6': 22.2, 'F7': 24.0, 'F8': 24.1, 'F9': 27.1, 'TA': 22.9, 'TB': 51.3}
rows = []
for line in open('helmet/out_v23/print_wing2/build_report.txt'):
    m = re.match(r'(F\d|TA|TB)\s+bodies.*?(\{.*\})\s*$', line)
    if not m: continue
    n, info = m.group(1), ast.literal_eval(m.group(2))
    lever = info['lever']
    w_old = min(max(0.6 * EDGE[n], 10.0), 26.0)
    old = SIG * (w_old - 6.4) * 2.2 ** 2 / 6 / lever            # v1: 2.2 mm thick, slits 2.5 mm in -> spine only at the root
    t = 2.4 if n == 'TB' else 3.6
    new = SIG * (info['width'] + info['gusset']) * t ** 2 / 6 / lever
    rows.append(dict(piece=n, lever=lever, old_w=round(w_old, 1), old_depth=16, old_N=round(old, 1),
                     new_w=info['width'], gusset=info['gusset'], new_depth=info['depth'], new_t=t, new_N=round(new, 1), x=round(new / old, 1)))
json.dump(rows, open('ref2/wing2_strength.json', 'w'), indent=1)
print(f"{'piece':5s} {'lever':>5s} | {'old tab':>16s} {'old N':>6s} | {'new tab':>22s} {'new N':>6s} {'x':>5s}")
for r in rows:
    print(f"{r['piece']:5s} {r['lever']:5.0f} | {r['old_w']:5.1f} w x 2.2 x 16 {r['old_N']:6.1f} | {r['new_w']:5.1f}+{r['gusset']:.0f} w x {r['new_t']} x {r['new_depth']:4.1f} {r['new_N']:6.1f} {r['x']:5.1f}")
