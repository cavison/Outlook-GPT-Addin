#!/usr/bin/env python3
"""Print-readiness checks for the generated parts.

Renders look fine long before a model actually prints, so this checks the
numbers that decide whether it comes off the bed: how thin the thinnest
artwork is, how far the engraving has to bridge, how steep the steepest
overhang is, and whether every solid is watertight.
"""

from __future__ import annotations

import argparse

import numpy as np

import design
import geom
import hnb_cutter as H


def max_inscribed_radius(polygon, hi=12.0, steps=26):
    """Largest circle that fits inside a shape, by bisection on negative buffer.

    On a letter of constant weight this lands on half the stroke width -- the
    number that decides whether a nozzle can lay the stroke down cleanly. On a
    solid shape it gives the widest span, which is what an engraved recess has
    to bridge across.
    """
    lo = 0.0
    for _ in range(steps):
        mid = (lo + hi) / 2.0
        if polygon.buffer(-mid).is_empty:
            hi = mid
        else:
            lo = mid
    return lo


def thin_area(polygon, min_width):
    """Area of material sitting in regions narrower than min_width."""
    core = polygon.buffer(-min_width / 2.0).buffer(min_width / 2.0)
    return polygon.difference(core).area


def report_art(label, art, floor=1.0):
    parts = sorted(getattr(art, "geoms", [art]), key=lambda p: p.area, reverse=True)
    widths = [2.0 * max_inscribed_radius(p) for p in parts]
    b = art.bounds
    thin = thin_area(art, floor)
    print(f"  {label}")
    print(f"      size {b[2]-b[0]:.1f} x {b[3]-b[1]:.1f} mm   "
          f"{len(parts)} island(s)   max radius {design.max_radius(art):.1f} mm")
    print(f"      narrowest island {min(widths):.2f} mm   "
          f"widest solid {max(widths):.2f} mm")
    print(f"      material under {floor:.1f} mm wide: {thin:.1f} mm2 "
          f"({100*thin/art.area:.1f}%)")
    return max(widths)


def overhang_report(mesh, engrave_z=None, bed_tol=0.05):
    """Area of downward-facing surface too shallow to print unsupported.

    Angles are measured from vertical: 0 deg is a plain wall, 90 deg a flat
    ceiling. Past 45 deg needs support -- unless it is a short bridge, which
    prints fine across a gap.

    The engraved wordmark is cut into the face that sits on the bed, so its
    ceiling is by definition a flat 90 deg overhang. That is the intended
    bridge, not a defect, so it is separated out here -- otherwise it swamps
    the number and hides anything that genuinely does need support.
    """
    normals = mesh.face_normals
    tris = mesh.vertices[mesh.faces]
    z_min = mesh.bounds[0][2]

    downward = normals[:, 2] < -1e-6
    on_bed = tris[:, :, 2].max(axis=1) <= z_min + bed_tol
    angle = np.degrees(np.arcsin(np.clip(-normals[:, 2], 0, 1)))
    flagged = downward & ~on_bed & (angle > 45.0)

    engraved = np.zeros(len(flagged), bool)
    if engrave_z is not None:
        ceiling = np.abs(tris[:, :, 2] - (z_min + engrave_z)).max(axis=1) < 1e-3
        engraved = flagged & ceiling

    rest = flagged & ~engraved
    return {
        "worst": float(angle[rest].max()) if rest.any() else 0.0,
        "area": float(mesh.area_faces[rest].sum()),
        "faces": int(rest.sum()),
        "engraved_area": float(mesh.area_faces[engraved].sum()),
    }


def main():
    ap = argparse.ArgumentParser(description="print-readiness checks")
    ap.add_argument("--diameter", type=float, default=H.Config.diameter)
    ap.add_argument("--emboss", default=None,
                    choices=list(design.SILHOUETTES),
                    help="which cookie-face artwork to check (default: each "
                         "variant present in the repo)")
    a = ap.parse_args()

    cfg = H.Config(diameter=a.diameter)
    variants = [a.emboss] if a.emboss else design.available_emboss()
    longhorn = design.emboss(variants[0], cfg.stamp_art_limit_r, cfg.mirror)
    logo_stamp = design.logo(cfg.stamp_art_limit_r, cfg.mirror)
    logo_comb = design.logo(cfg.combined_art_limit_r, cfg.mirror)

    print("=" * 74)
    print(f"ARTWORK  ({cfg.diameter:.0f} mm, all values in mm)")
    print("=" * 74)
    for name in variants:
        report_art(f"{name}, raised on the cookie face",
                   design.emboss(name, cfg.stamp_art_limit_r, cfg.mirror))
    bridge = report_art("wordmark, engraved into the hand face", logo_stamp)

    # An engraved channel is harder to render than a raised stroke of the same
    # width: below roughly a nozzle diameter the slicer simply fills it in, and
    # the letters close up. The wordmark's narrowest letter is what sets the
    # smallest cookie this design can carry.
    letters = [2.0 * max_inscribed_radius(p)
               for p in getattr(logo_stamp, "geoms", [logo_stamp])]
    narrowest = min(letters)
    if narrowest < 1.0:
        print(f"  *** wordmark letters down to {narrowest:.2f} mm -- engraving will "
              f"close up; keep the diameter at 70 mm or above ***")
    else:
        print(f"  wordmark letters {narrowest:.2f} mm at their narrowest -- engraves clean")

    print()
    print("=" * 74)
    print("PARTS")
    print("=" * 74)
    builders = {
        "cutter ring": lambda: H.build_cutter(cfg),
        "stamp": lambda: H.build_stamp(cfg, longhorn, logo_stamp),
        "combined": lambda: H.build_combined(cfg, longhorn, logo_comb),
    }
    ok = True
    for name, build in builders.items():
        mesh = build()
        oh = overhang_report(mesh, None if name == "cutter ring" else cfg.logo_depth)
        good = mesh.is_watertight and mesh.is_winding_consistent and mesh.volume > 0
        ok &= good
        print(f"  {name}")
        print(f"      watertight {mesh.is_watertight}   "
              f"winding {mesh.is_winding_consistent}   "
              f"volume {mesh.volume/1000:.1f} cm3   {len(mesh.faces)} tris")
        print(f"      engraving ceiling (bridges): {oh['engraved_area']:6.1f} mm2")
        print(f"      other unsupported:           {oh['area']:6.1f} mm2 over "
              f"{oh['faces']} faces, worst {oh['worst']:.0f} deg from vertical")

    print()
    print("=" * 74)
    print("FITS AND DEPTHS")
    print("=" * 74)
    print(f"  stamp OD {2*cfg.stamp_r:.2f} into cutter ID "
          f"{2*(cfg.cutter_r-cfg.wall_base):.2f}   -> "
          f"{cfg.stamp_clearance*2:.2f} diametral clearance")
    print(f"  blade edge / base             {cfg.wall_edge:.2f} / {cfg.wall_base:.2f}")

    # The engraved recess is cut into the face that sits on the bed, so its
    # ceiling bridges. Bridge length is the widest solid run in the wordmark.
    print(f"  engraving depth               {cfg.logo_depth:.2f} into a "
          f"{cfg.plate_thickness:.1f} plate "
          f"({cfg.plate_thickness - cfg.logo_depth:.1f} left under the longhorn)")
    verdict = "OK" if bridge <= 20.0 else "*** LONG BRIDGE ***"
    print(f"  longest engraving bridge      {bridge:.1f}   {verdict}")
    comb_left = cfg.combined_plate_thickness - cfg.logo_depth
    print(f"  one-piece plate under engrave {comb_left:.2f} thick"
          f"   {'OK' if comb_left >= 1.0 else '*** TOO THIN ***'}")

    proud = cfg.combined_blade_height - cfg.relief_height
    print(f"  one-piece blade / relief      {cfg.combined_blade_height:.2f} / "
          f"{cfg.relief_height:.2f}  -> blade stands {proud:.2f} proud"
          f"   {'OK' if proud >= 1.5 else '*** NOT PROUD ENOUGH ***'}")
    print(f"  one-piece dough window        {proud:.1f} to "
          f"{cfg.combined_blade_height:.1f} mm thick")

    taper = cfg.wall_base - cfg.wall_edge
    print(f"  blade lean, ring / one-piece  "
          f"{np.degrees(np.arctan(taper/cfg.blade_height)):.1f} / "
          f"{np.degrees(np.arctan(taper/cfg.combined_blade_height)):.1f} deg from vertical")

    print()
    print("ALL SOLID CHECKS PASSED" if ok else "*** PROBLEM FOUND ***")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
