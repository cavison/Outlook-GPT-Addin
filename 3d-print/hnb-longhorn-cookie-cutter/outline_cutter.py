#!/usr/bin/env python3
"""Plain outline cookie cutters -- cut a shape out, no embossing.

Built to match the reference cutters in ref/: a thin blade the height of the
part, a lip flaring outwards at one end, and a chamfer joining the two. The
lip is printed face-down and ends up on top in use, giving the heel of your
hand something blunt to push against.

Measured off ref/sample_tree.obj:

    total height   15.0 mm
    blade wall      0.80 mm
    lip height      3.4 mm, offset +2.0 mm outward from the blade
    chamfer         1.6 mm back to the blade line

The useful structural fact is that the lip's inner edge and the blade's inner
edge are the same curve, so the cavity is one plain vertical prism the whole
way up. The part is therefore just an outer profile swept over z, minus that
single cavity -- no lofting between changing cross-sections.

    python3 outline_cutter.py                    # every silhouette present
    python3 outline_cutter.py --shape skull --size 76.2
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass

from shapely.affinity import scale as shp_scale

import design
import geom


@dataclass
class CutterSpec:
    size: float = 76.2          # widest dimension of the cookie, 3 inches
    height: float = 15.0
    wall: float = 0.80          # blade thickness
    lip_offset: float = 2.0     # how far the lip flares outward
    lip_height: float = 3.4
    chamfer: float = 1.6
    chamfer_steps: int = 8      # 1.6 mm over 8 steps = one layer per step
    fatten: float = 1.5         # thicken thin artwork so the cookie survives
    min_dough: float = 5.0      # dough narrower than this snaps when handled
    mirror: bool = True


def build_cutter(shape, spec: CutterSpec):
    """Sweep the outer profile over z, then hollow it with one cavity prism.

    The chamfer is stepped rather than lofted: offsetting a silhouette by a
    varying amount changes its topology unpredictably, so a true loft between
    the lip and blade outlines is fragile. At 0.2 mm per step the staircase is
    one layer tall -- the slicer cannot represent anything finer anyway.
    """
    blade_top = spec.lip_height + spec.chamfer
    if blade_top >= spec.height:
        raise ValueError("lip and chamfer are taller than the cutter")

    layers = [geom.prism(shape.buffer(spec.lip_offset), 0.0, spec.lip_height)]
    for i in range(spec.chamfer_steps):
        z0 = spec.lip_height + i * spec.chamfer / spec.chamfer_steps
        z1 = z0 + spec.chamfer / spec.chamfer_steps
        # midpoint of the step, so the staircase straddles the ideal slope
        out = spec.lip_offset * (1.0 - (i + 0.5) / spec.chamfer_steps)
        layers.append(geom.prism(shape.buffer(out), z0, z1))
    layers.append(geom.prism(shape, blade_top, spec.height))

    cavity = shape.buffer(-spec.wall)
    if cavity.is_empty:
        raise ValueError("wall is thicker than the shape -- nothing left to cut")
    return geom.difference([geom.union(layers),
                            geom.prism(cavity, -1.0, spec.height + 1.0)])


def narrow_area(shape, width):
    """Area of the cookie sitting in runs narrower than `width`."""
    return shape.difference(shape.buffer(-width / 2.0).buffer(width / 2.0)).area


def prepare(name, spec: CutterSpec):
    """Traced silhouette at final size, fattened and mirrored for use.

    Two adjustments happen here.

    Fattening: artwork that reads well as a flat silhouette can be a poor
    cookie. The skull's horns are long thin arcs -- over half the cookie sits
    in runs under 5 mm, which snap as soon as anyone lifts one off the counter.
    Dilating the outline thickens those runs far more, in relative terms, than
    it thickens the head, so the shape survives handling without losing its
    character. Scaling back afterwards keeps the requested cookie size exact.

    Mirroring: a cutter is printed lip-down and flipped lip-up to press, and
    flipping it mirrors the outline it cuts. So the artwork is mirrored in the
    model for the cookie to come out facing the same way as the source --
    invisible on a symmetric shape, but it decides which way the steer faces.
    """
    art = design.silhouette(name, spec.size)
    if spec.fatten > 0:
        art = art.buffer(spec.fatten)
        minx, miny, maxx, maxy = art.bounds
        span = max(maxx - minx, maxy - miny)
        art = shp_scale(art, xfact=spec.size / span, yfact=spec.size / span,
                        origin=(0, 0))
    return design.mirror_x(art) if spec.mirror else art


def report(name, shape, mesh, spec: CutterSpec, raw):
    islands = list(getattr(shape, "geoms", [shape]))
    solid = shape.difference(shape.buffer(-spec.wall).buffer(spec.wall))
    b = shape.bounds
    lo, hi = mesh.bounds
    thin = 100 * narrow_area(shape, spec.min_dough) / shape.area
    was = 100 * narrow_area(raw, spec.min_dough) / raw.area

    print(f"  {name}")
    print(f"      cookie {b[2]-b[0]:5.1f} x {b[3]-b[1]:5.1f} mm "
          f"({(b[2]-b[0])/25.4:.2f} x {(b[3]-b[1])/25.4:.2f} in)")
    print(f"      part   {hi[0]-lo[0]:5.1f} x {hi[1]-lo[1]:5.1f} x {hi[2]-lo[2]:4.1f} mm"
          f"   {mesh.volume/1000:5.1f} cm3   "
          f"{'watertight' if mesh.is_watertight else 'NOT WATERTIGHT'}")
    print(f"      dough under {spec.min_dough:.0f} mm: {thin:4.1f}% "
          f"(was {was:4.1f}% before fattening +{spec.fatten:.1f})"
          f"{'' if thin < 25 else '   *** fragile cookie ***'}")
    print(f"      {len(islands)} island(s)"
          f"{'' if len(islands) == 1 else '  *** would print as separate pieces ***'}"
          f"   solid, too narrow to hollow: {solid.area:.1f} mm2")
    return mesh.is_watertight and len(islands) == 1


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--shape", default="all",
                    choices=["all", *design.SILHOUETTES])
    ap.add_argument("--size", type=float, default=CutterSpec.size,
                    help="widest dimension of the cookie in mm (default 76.2 = 3 in)")
    ap.add_argument("--height", type=float, default=CutterSpec.height)
    ap.add_argument("--wall", type=float, default=CutterSpec.wall)
    ap.add_argument("--fatten", type=float, default=CutterSpec.fatten,
                    help="thicken the outline by this many mm so thin runs of "
                         "dough survive handling (default 1.5; 0 disables)")
    ap.add_argument("--outdir", default="stl/cutters")
    ap.add_argument("--no-preview", action="store_true")
    args = ap.parse_args()

    spec = CutterSpec(size=args.size, height=args.height, wall=args.wall,
                      fatten=args.fatten)

    if args.shape == "all":
        wanted = design.available_emboss()
        for name in design.SILHOUETTES:
            if name not in wanted:
                print(f"  skipping {name!r}: "
                      f"{design.SILHOUETTES[name]['path']} is not in the repo yet")
    else:
        wanted = [args.shape]
    if not wanted:
        raise SystemExit("no silhouette artwork available")

    print(f"Outline cutters -- {spec.size:.1f} mm ({spec.size/25.4:.2f} in) across, "
          f"{spec.height:.0f} mm tall, {spec.wall:.2f} mm blade\n")

    os.makedirs(args.outdir, exist_ok=True)
    ok = True
    shapes = {}
    for name in wanted:
        shape = prepare(name, spec)
        shapes[name] = shape
        mesh = build_cutter(shape, spec)
        ok &= report(name, shape, mesh, spec, design.silhouette(name, spec.size))
        mesh.export(os.path.join(args.outdir, f"hnb_cutter_{name}.stl"))

    if not args.no_preview:
        import preview
        os.makedirs("preview", exist_ok=True)
        for name, shape in shapes.items():
            preview.plot_flat([(f"{name}: cookie outline "
                                f"({spec.size/25.4:.1f} in across)",
                                design.mirror_x(shape), "#a9752f")],
                              f"preview/10_cutter_{name}_outline.png",
                              disc_radius=spec.size * 0.58)
            preview.render_mesh(build_cutter(shape, spec),
                                f"preview/11_cutter_{name}.png",
                                colours=["#7d8a96"],
                                title=f"{name} cutter (lip down, as printed)")
        print("\n  previews written to preview/")

    print("\nALL CUTTERS OK" if ok else "\n*** PROBLEM FOUND ***")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
