#!/usr/bin/env python3
"""Build cookie cutters. One entry point, three styles.

    python3 make.py                        # every design whose artwork is present
    python3 make.py --style cutout         # one style
    python3 make.py --design skull         # one design
    python3 make.py --list                 # what is registered

STLs land in designs/<style>/<design>_<part>.stl, so the styles never mix.
Every part exports in print orientation on z=0: no supports, no rotation.
"""

from __future__ import annotations

import argparse
import dataclasses
import os

import artwork
import body
import styles


def narrow_area(shape, width):
    """Area of cookie sitting in runs narrower than `width` -- the dough that snaps."""
    return shape.difference(shape.buffer(-width / 2.0).buffer(width / 2.0)).area


def report(name, design, parts, shapes, spec):
    shape = shapes["outline"]
    b = shape.bounds
    thin = 100 * narrow_area(shape, spec.min_dough) / shape.area
    islands = len(getattr(shape, "geoms", [shape]))

    print(f"  {name}  [{design.style}]")
    print(f"      cookie {b[2]-b[0]:5.1f} x {b[3]-b[1]:5.1f} mm "
          f"({(b[2]-b[0])/25.4:.2f} x {(b[3]-b[1])/25.4:.2f} in)"
          f"   dough under {spec.min_dough:.0f} mm: {thin:.0f}%"
          f"{'' if thin < 25 else '  *** fragile ***'}")
    if islands != 1:
        print(f"      *** outline is {islands} islands -- would print as separate pieces ***")

    ok = islands == 1
    for part, mesh in parts.items():
        lo, hi = mesh.bounds
        good = mesh.is_watertight
        ok &= good
        print(f"      {part:<8} {hi[0]-lo[0]:6.1f} x {hi[1]-lo[1]:6.1f} x {hi[2]-lo[2]:5.1f} mm"
              f"   {mesh.volume/1000:5.1f} cm3   "
              f"{'watertight' if good else 'NOT WATERTIGHT'}")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--style", choices=artwork.STYLES)
    ap.add_argument("--design", choices=list(artwork.DESIGNS))
    ap.add_argument("--size", type=float, help="override cookie size in mm")
    ap.add_argument("--outdir", default="designs")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--no-preview", action="store_true")
    args = ap.parse_args()

    if args.list:
        print(f"  {'design':<18} {'style':<8} {'outline':<8} {'size':>6}  artwork")
        for n, d in artwork.DESIGNS.items():
            miss = artwork.missing_art(n)
            print(f"  {n:<18} {d.style:<8} {d.outline:<8} {d.size:6.1f}  "
                  f"{'ready' if not miss else 'MISSING ' + ', '.join(miss)}")
        return 0

    wanted = [n for n, d in artwork.DESIGNS.items()
              if (args.design in (None, n)) and (args.style in (None, d.style))]
    if not wanted:
        raise SystemExit("nothing matches that selection")

    base = body.Spec()
    ok = True
    print(f"Building {len(wanted)} design(s)\n")
    for name in wanted:
        design = artwork.DESIGNS[name]
        if args.size:
            design = type(design)(**{**design.__dict__, "size": args.size})
        if not artwork.available(name):
            print(f"  {name}  [{design.style}]  skipped -- missing "
                  f"{', '.join(artwork.missing_art(name))}")
            continue

        spec = dataclasses.replace(base, **design.spec)
        parts, shapes = styles.BUILDERS[design.style](design, spec)
        ok &= report(name, design, parts, shapes, spec)

        out = os.path.join(args.outdir, design.style)
        os.makedirs(out, exist_ok=True)
        for part, mesh in parts.items():
            mesh.export(os.path.join(out, f"{name}_{part}.stl"))

        if not args.no_preview:
            import preview
            os.makedirs("preview", exist_ok=True)
            panels = [(f"{name}: cookie outline", artwork.mirror_x(shapes["outline"]),
                       "#a9752f")]
            if shapes.get("detail") is not None:
                panels.append((f"{name}: embossed lines",
                               artwork.mirror_x(shapes["detail"]), "#3f6b8a"))
            preview.plot_flat(panels, f"preview/{design.style}_{name}.png",
                              disc_radius=design.size * 0.60)

    print("\nALL PARTS OK" if ok else "\n*** PROBLEM FOUND ***")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
