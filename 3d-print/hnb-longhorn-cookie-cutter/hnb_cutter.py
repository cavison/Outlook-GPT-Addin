#!/usr/bin/env python3
"""HNB Longhorns cookie cutter -- parametric STL generator.

Produces a cutter ring plus a two-sided stamp, and a one-piece
cutter/embosser alternative. The stamp carries the longhorn on the face that
meets the dough and the HNB Longhorns wordmark engraved on the face you hold.

    python3 hnb_cutter.py                  # defaults, 90 mm
    python3 hnb_cutter.py --diameter 75    # smaller cookies

All meshes export in PRINT orientation: drop them on the bed as-is, no
rotation and no supports needed.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass

import trimesh

import design
import geom


@dataclass
class Config:
    # --- overall size -----------------------------------------------------
    diameter: float = 90.0          # outside of the cutting edge = cookie size
    segments: int = 256             # facets around the circle

    # --- cutter ring ------------------------------------------------------
    blade_height: float = 15.0
    wall_base: float = 1.6          # blade thickness at the flange end
    wall_edge: float = 0.5          # blade thickness at the cutting edge
    flange_width: float = 5.0       # grip rim sticking out from the blade
    flange_thickness: float = 2.5

    # --- stamp ------------------------------------------------------------
    stamp_clearance: float = 0.35   # radial gap so the stamp drops into the cutter
    plate_thickness: float = 6.0
    relief_height: float = 1.8      # how deep the longhorn presses into the dough
    plate_chamfer: float = 0.8

    # --- engraved branding ------------------------------------------------
    logo_depth: float = 1.0         # how deep the wordmark is cut into the hand face

    # --- one-piece variant ------------------------------------------------
    combined_blade_height: float = 5.0
    combined_plate_thickness: float = 2.6

    # --- artwork ----------------------------------------------------------
    art_margin: float = 2.5         # clear ring left around the artwork
    mirror: bool = True

    # --- derived ----------------------------------------------------------
    @property
    def cutter_r(self) -> float:
        return self.diameter / 2.0

    @property
    def stamp_r(self) -> float:
        return self.cutter_r - self.wall_base - self.stamp_clearance

    @property
    def stamp_art_limit_r(self) -> float:
        return self.stamp_r - self.art_margin

    @property
    def combined_art_limit_r(self) -> float:
        return self.cutter_r - self.art_margin


# --------------------------------------------------------------------------
# parts
# --------------------------------------------------------------------------


def build_cutter(cfg: Config) -> trimesh.Trimesh:
    """Round cutter ring, modelled flange-down / cutting-edge-up for printing.

    The blade is thick at the flange and tapers to a fine edge, so the inner
    face leans outwards by only a few degrees going up -- self-supporting, and
    it gives a properly sharp edge without a knife-thin first layer.
    """
    r_out = cfg.cutter_r
    profile = [
        (r_out - cfg.wall_base, 0.0),
        (r_out + cfg.flange_width, 0.0),
        (r_out + cfg.flange_width, cfg.flange_thickness),
        (r_out, cfg.flange_thickness + cfg.flange_width * 0.6),
        (r_out, cfg.blade_height),
        (r_out - cfg.wall_edge, cfg.blade_height),
    ]
    return geom.revolve(profile, cfg.segments)


def _engrave(cfg: Config, logo):
    """The solid to subtract for the engraved wordmark, cut into the z=0 face."""
    return geom.prism(logo, -0.5, cfg.logo_depth)


def build_stamp(cfg: Config, longhorn, logo) -> trimesh.Trimesh:
    """Two-sided stamp: longhorn raised on the cookie face, wordmark engraved
    into the hand face.

    Printed longhorn-up. That puts the engraved face on the bed, where the
    wordmark becomes a shallow recess rather than a raised feature -- which is
    the only way round: raised artwork on the bed face would leave the part
    standing on its own logo, and flipping the part instead would leave the
    whole plate overhanging the longhorn.
    """
    plate = geom.prism(geom.disc(cfg.stamp_r, cfg.segments), 0.0, cfg.plate_thickness)

    cuts = [_engrave(cfg, logo)]
    if cfg.plate_chamfer > 0:
        ch = cfg.plate_chamfer
        cuts.append(geom.revolve([
            (cfg.stamp_r - ch, 0.0),
            (cfg.stamp_r, ch),
            (cfg.stamp_r + 1.0, ch),
            (cfg.stamp_r + 1.0, -1.0),
            (cfg.stamp_r - ch, -1.0),
        ], cfg.segments))
    plate = geom.difference([plate] + cuts)

    relief = geom.prism(longhorn, cfg.plate_thickness - 0.4,
                        cfg.plate_thickness + cfg.relief_height)
    return geom.union([plate, relief])


def build_combined(cfg: Config, longhorn, logo) -> trimesh.Trimesh:
    """One-piece cutter + embosser, with the wordmark engraved into its back.

    Two depths are in tension. The blade has to stand proud of the longhorn so
    the edge cuts clean through while the artwork only presses in. But the blade
    also caps dough thickness: you press until it bottoms out on the board, so
    the plate ends up one blade-height above it, and thicker dough never gets
    cut through. Dough thinner than `blade - relief` never touches the artwork.
    Roll to roughly the blade height and both work.
    """
    plate_t = cfg.combined_plate_thickness
    r_out = cfg.cutter_r

    plate = geom.difference([
        geom.prism(geom.disc(r_out, cfg.segments), 0.0, plate_t),
        _engrave(cfg, logo),
    ])
    relief = geom.prism(longhorn, plate_t - 0.4, plate_t + cfg.relief_height)
    blade = geom.revolve([
        (r_out - cfg.wall_base, plate_t - 1.0),
        (r_out, plate_t - 1.0),
        (r_out, plate_t + cfg.combined_blade_height),
        (r_out - cfg.wall_edge, plate_t + cfg.combined_blade_height),
    ], cfg.segments)
    return geom.union([plate, relief, blade])


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------


def describe(name, mesh):
    lo, hi = mesh.bounds
    return (f"  {name:<28} {hi[0]-lo[0]:6.1f} x {hi[1]-lo[1]:6.1f} x {hi[2]-lo[2]:6.1f} mm"
            f"   {mesh.volume/1000.0:6.1f} cm3   "
            f"{'watertight' if mesh.is_watertight else 'NOT WATERTIGHT'}"
            f"   {len(mesh.faces):>7d} tris")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--diameter", type=float, default=Config.diameter,
                    help="cookie diameter in mm (default 90)")
    ap.add_argument("--blade-height", type=float, default=Config.blade_height,
                    help="cutter ring cutting depth in mm (default 15)")
    ap.add_argument("--combined-blade-height", type=float,
                    default=Config.combined_blade_height,
                    help="one-piece blade depth in mm (default 5); this is also "
                         "the maximum dough thickness that part can handle")
    ap.add_argument("--relief-height", type=float, default=Config.relief_height,
                    help="how far the longhorn stands proud, in mm (default 1.8)")
    ap.add_argument("--logo-depth", type=float, default=Config.logo_depth,
                    help="engraving depth for the wordmark, in mm (default 1.0)")
    ap.add_argument("--no-mirror", action="store_true",
                    help="skip both mirrors -- only useful for a plaque, never "
                         "for a stamp")
    ap.add_argument("--outdir", default="stl")
    ap.add_argument("--no-preview", action="store_true")
    args = ap.parse_args()

    cfg = Config(diameter=args.diameter, blade_height=args.blade_height,
                 combined_blade_height=args.combined_blade_height,
                 relief_height=args.relief_height, logo_depth=args.logo_depth,
                 mirror=not args.no_mirror)

    print(f"HNB Longhorns cookie cutter -- {cfg.diameter:.0f} mm")
    longhorn = design.longhorn(cfg.stamp_art_limit_r, cfg.mirror)
    logo_stamp = design.logo(cfg.stamp_art_limit_r, cfg.mirror)
    logo_combined = design.logo(cfg.combined_art_limit_r, cfg.mirror)

    for label, art in (("longhorn (cookie face)", longhorn),
                       ("wordmark (hand face)", logo_stamp)):
        b = art.bounds
        print(f"  {label:<24} {b[2]-b[0]:5.1f} x {b[3]-b[1]:5.1f} mm")
    print()

    parts = {
        "1_cutter_ring": build_cutter(cfg),
        "2_stamp": build_stamp(cfg, longhorn, logo_stamp),
        "3_combined_cutter_stamp": build_combined(cfg, longhorn, logo_combined),
    }

    os.makedirs(args.outdir, exist_ok=True)
    for name, mesh in parts.items():
        print(describe(name, mesh))
        mesh.export(os.path.join(args.outdir, f"hnb_longhorn_{name}.stl"))

    if not args.no_preview:
        import preview
        os.makedirs("preview", exist_ok=True)
        preview.plot_flat(
            [("cookie face (mirrored - what you print)", longhorn, "#3f6b8a"),
             ("the cookie (what you get)", design.mirror_x(longhorn), "#a9752f")],
            "preview/01_cookie_face.png", disc_radius=cfg.stamp_r)
        preview.plot_flat(
            [("hand face, engraved (as it reads in your hand)",
              design.mirror_x(logo_stamp), "#2f2a26")],
            "preview/02_hand_face.png", disc_radius=cfg.stamp_r)
        preview.render_mesh(parts["2_stamp"], "preview/03_stamp_cookie_side.png",
                            colours=["#4a7fa5"], title="stamp, cookie side (as printed)",
                            highlight_above=cfg.plate_thickness + 0.05)
        # Viewed from below, world +y only reads as screen-up for azimuths on
        # the far side; at the default azimuth the wordmark comes out rotated.
        preview.render_mesh(parts["2_stamp"], "preview/04_stamp_hand_side.png",
                            colours=["#4a7fa5"], elev=-34.0, azim=128.0,
                            title="stamp, hand side (engraved wordmark)",
                            engrave_above=0.05)
        preview.render_mesh(parts["1_cutter_ring"], "preview/05_cutter.png",
                            colours=["#7d8a96"], title="cutter ring (edge up, as printed)")
        preview.render_mesh(parts["3_combined_cutter_stamp"], "preview/06_combined.png",
                            colours=["#8a6a4a"], title="one-piece cutter + embosser",
                            highlight_above=cfg.combined_plate_thickness + 0.05)
        print("\n  previews written to preview/")


if __name__ == "__main__":
    main()
