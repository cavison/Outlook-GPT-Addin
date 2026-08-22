#!/usr/bin/env python3
"""Print-readiness checks for the generated parts.

Renders look fine long before a model actually prints, so this checks the
numbers that decide whether it comes off the bed: how thin the thinnest
feature is, how steep the steepest overhang is, and whether every solid is
watertight.
"""

from __future__ import annotations

import numpy as np

import design
import geom
import hnb_cutter as H


def max_inscribed_radius(polygon, hi=12.0, steps=26):
    """Largest circle that fits inside a shape, by bisection on negative buffer.

    For a constant-weight letter this lands on half the stem width, which is the
    number that decides whether a nozzle can lay the stroke down cleanly.
    """
    lo = 0.0
    for _ in range(steps):
        mid = (lo + hi) / 2.0
        if polygon.buffer(-mid).is_empty:
            hi = mid
        else:
            lo = mid
    return lo


def overhang_report(mesh, bed_tol=0.05):
    """Area of downward-facing surface too shallow to print unsupported.

    Angles are measured from vertical: 0 deg is a plain wall, 90 deg is a flat
    ceiling. Anything past 45 deg needs support -- unless it is a short bridge,
    which prints fine across a gap.
    """
    normals = mesh.face_normals
    tris = mesh.vertices[mesh.faces]
    z_min = mesh.bounds[0][2]

    downward = normals[:, 2] < -1e-6
    on_bed = tris[:, :, 2].max(axis=1) <= z_min + bed_tol
    angle = np.degrees(np.arcsin(np.clip(-normals[:, 2], 0, 1)))

    flagged = downward & ~on_bed & (angle > 45.0)
    areas = mesh.area_faces
    return {
        "worst_angle_deg": float(angle[flagged].max()) if flagged.any() else 0.0,
        "unsupported_area_mm2": float(areas[flagged].sum()),
        "faces": int(flagged.sum()),
    }


def main():
    import argparse
    ap = argparse.ArgumentParser(description="print-readiness checks")
    ap.add_argument("--diameter", type=float, default=H.Config.diameter)
    ap.add_argument("--top-text", default=H.Config.top_text)
    ap.add_argument("--bottom-text", default=H.Config.bottom_text)
    ap.add_argument("--font", default=H.Config.font)
    a = ap.parse_args()

    cfg = H.Config(diameter=a.diameter, top_text=a.top_text,
                   bottom_text=a.bottom_text, font=a.font)
    scale = cfg.diameter / 90.0
    cfg.top_cap_height *= scale
    cfg.bottom_cap_height *= scale
    cfg.longhorn_span *= scale

    print(f"config: {cfg.diameter:.0f} mm  "
          f"{cfg.top_text!r} / {cfg.bottom_text!r}  font {cfg.font!r}")
    art, report = H.build_artwork(cfg)

    print("=" * 74)
    print("ARTWORK  (all values in mm)")
    print("=" * 74)
    for k, v in report.items():
        print(f"  {k:<28} {v}")

    parts = sorted(getattr(art, "geoms", [art]), key=lambda p: p.area, reverse=True)
    widths = [(2.0 * max_inscribed_radius(p), p.area) for p in parts]
    letters = [w for w, a in widths if a < 200.0]
    print(f"  components                   {len(parts)}")
    print(f"  thinnest stroke              {min(letters):.2f}  "
          f"(letters; needs >= 1.00 for a 0.4 mm nozzle)")
    print(f"  border ring width            {cfg.border_width:.2f}")

    # Features that sit too close together fuse on the printer and trap dough
    # between them in use, so the imprint reads as a smudge rather than letters.
    closest, pair = float("inf"), None
    for i, a in enumerate(parts):
        for b in parts[i + 1:]:
            d = a.distance(b)
            if d < closest:
                closest, pair = d, (a, b)
    print(f"  closest feature gap          {closest:.2f}  "
          f"(needs >= 0.80 so dough releases)")
    print(f"  horn tip width               {cfg.min_feature:.2f}")
    print(f"  relief height                {cfg.relief_height:.2f}")

    print()
    print("=" * 74)
    print("PARTS")
    print("=" * 74)
    builders = {
        "cutter ring": lambda: H.build_cutter(cfg),
        "stamp": lambda: H.build_stamp(cfg, art),
        "stamp handle": lambda: H.build_handle(cfg),
        "combined": lambda: H.build_combined(cfg, art),
    }
    ok = True
    for name, build in builders.items():
        mesh = build()
        oh = overhang_report(mesh)
        watertight = mesh.is_watertight
        winding = mesh.is_winding_consistent
        volume_ok = mesh.volume > 0
        ok &= watertight and winding and volume_ok
        print(f"  {name}")
        print(f"      watertight {watertight}   winding {winding}   "
              f"volume {mesh.volume/1000:.1f} cm3   {len(mesh.faces)} tris")
        print(f"      unsupported: {oh['unsupported_area_mm2']:7.1f} mm2 "
              f"over {oh['faces']} faces, worst {oh['worst_angle_deg']:.0f} deg "
              f"from vertical")

    print()
    print("=" * 74)
    print("FITS")
    print("=" * 74)
    peg_r = (cfg.socket_diameter - cfg.handle_peg_clearance) / 2.0
    print(f"  stamp OD {2*cfg.stamp_r:.2f} into cutter ID {2*(cfg.cutter_r-cfg.wall_base):.2f}"
          f"   -> {cfg.stamp_clearance*2:.2f} diametral clearance")
    print(f"  peg OD {2*peg_r:.2f} into socket ID {cfg.socket_diameter:.2f}"
          f"   -> {cfg.handle_peg_clearance:.2f} press fit")
    print(f"  socket ceiling                {cfg.plate_thickness - cfg.socket_depth:.2f} thick, "
          f"{cfg.socket_diameter:.1f} bridge span")
    print(f"  blade edge / base             {cfg.wall_edge:.2f} / {cfg.wall_base:.2f}")
    blade_lean = np.degrees(np.arctan((cfg.wall_base - cfg.wall_edge) / cfg.blade_height))
    print(f"  blade inner face leans        {blade_lean:.1f} deg from vertical")

    print()
    print("ALL SOLID CHECKS PASSED" if ok else "*** PROBLEM FOUND ***")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
