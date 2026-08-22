#!/usr/bin/env python3
"""HNB Longhorns cookie cutter + stamp -- parametric STL generator.

Produces a two-piece set (a round cutter ring and a drop-in stamp with a
push handle) plus an optional one-piece cutter/embosser. Every dimension
below is a knob you can turn; re-run the script and the STLs regenerate.

    python3 hnb_cutter.py                       # defaults, 90 mm
    python3 hnb_cutter.py --diameter 75         # smaller cookies
    python3 hnb_cutter.py --top-text HNB --bottom-text LONGHORNS

All meshes are exported in PRINT orientation: drop them on the bed as-is,
no rotation and no supports needed.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field

import numpy as np
import trimesh
from shapely.affinity import translate
from shapely.ops import unary_union

import design
import geom


# --------------------------------------------------------------------------
# configuration
# --------------------------------------------------------------------------


@dataclass
class Config:
    # --- overall size -----------------------------------------------------
    diameter: float = 90.0          # outside of the cutting edge = cookie size
    segments: int = 256             # facets around the circle

    # --- cutter ring ------------------------------------------------------
    blade_height: float = 15.0      # cutting depth
    wall_base: float = 1.6          # blade thickness at the flange end
    wall_edge: float = 0.5          # blade thickness at the cutting edge
    flange_width: float = 5.0       # grip rim sticking out from the blade
    flange_thickness: float = 2.5

    # --- stamp ------------------------------------------------------------
    stamp_clearance: float = 0.35   # radial gap so the stamp drops into the cutter
    plate_thickness: float = 5.0
    relief_height: float = 1.8      # how deep the design presses into the dough
    plate_chamfer: float = 0.8
    socket_diameter: float = 10.0   # blind hole in the back for the handle peg
    socket_depth: float = 3.5

    # --- handle -----------------------------------------------------------
    handle_palm_diameter: float = 18.0
    handle_flange_diameter: float = 26.0
    handle_height: float = 25.0
    handle_peg_clearance: float = 0.3

    # --- one-piece variant ------------------------------------------------
    combined_blade_height: float = 5.0    # sets the max dough thickness -- see below
    combined_plate_thickness: float = 2.2

    # --- artwork ----------------------------------------------------------
    font: str = "DejaVu Sans"
    top_text: str = "HNB"
    bottom_text: str = "LONGHORNS"
    top_cap_height: float = 9.0
    bottom_cap_height: float = 7.0
    top_tracking: float = 1.6
    bottom_tracking: float = 0.7
    border_width: float = 1.8
    border_inset: float = 1.2       # gap between border ring and stamp edge
    text_gap: float = 1.4           # gap between border ring and letters
    art_gap: float = 2.0            # gap between longhorn and everything else
    longhorn_span: float = 76.0     # requested horn tip-to-tip; auto-shrinks to fit
    longhorn_offset_y: float = 1.0
    min_feature: float = 1.6        # thinnest printable/stampable detail

    mirror: bool = True             # backwards artwork so the cookie reads forwards

    # --- derived ----------------------------------------------------------
    @property
    def cutter_r(self) -> float:
        return self.diameter / 2.0

    @property
    def stamp_r(self) -> float:
        return self.cutter_r - self.wall_base - self.stamp_clearance

    @property
    def border_outer_r(self) -> float:
        return self.stamp_r - self.border_inset

    @property
    def text_outer_r(self) -> float:
        return self.border_outer_r - self.border_width - self.text_gap

    @property
    def top_baseline_r(self) -> float:
        return self.text_outer_r - self.top_cap_height

    @property
    def bottom_baseline_r(self) -> float:
        return self.text_outer_r

    @property
    def art_limit_r(self) -> float:
        return self.text_outer_r


# --------------------------------------------------------------------------
# artwork placement
# --------------------------------------------------------------------------


def build_artwork(cfg: Config):
    """Compose border + text + longhorn, sizing the longhorn to fit the gaps.

    Returns (artwork_polygon, report_dict). The artwork is in tool orientation
    -- i.e. already mirrored, unless cfg.mirror is off.
    """
    font = geom.resolve_font(cfg.font)

    fixed = []
    if cfg.border_width > 0:
        fixed.append(geom.ring(cfg.border_outer_r, cfg.border_width, cfg.segments))
    fixed.append(geom.arc_text(cfg.top_text, font, cfg.top_cap_height,
                               cfg.top_baseline_r, on_top=True,
                               tracking=cfg.top_tracking))
    fixed.append(geom.arc_text(cfg.bottom_text, font, cfg.bottom_cap_height,
                               cfg.bottom_baseline_r, on_top=False,
                               tracking=cfg.bottom_tracking))
    obstacles = unary_union([p.buffer(0) for p in fixed]).buffer(0)

    horn, span = _fit_longhorn(cfg, obstacles)
    art = unary_union([obstacles, horn]).buffer(0)
    if cfg.mirror:
        art = design._mirror_x(art)

    report = {
        "longhorn_span_mm": round(span, 2),
        "longhorn_gap_mm": round(horn.distance(obstacles), 2),
        "artwork_max_radius_mm": round(design.max_radius(art), 2),
        "stamp_radius_mm": round(cfg.stamp_r, 2),
    }
    return art, report


def _fit_longhorn(cfg: Config, obstacles):
    """Shrink the longhorn until it clears the text and stays inside the plate.

    Uses real polygon-to-polygon distance rather than a crude radius test, so
    the horns can reach out past the ends of the bottom text where there is
    nothing to collide with.
    """
    def attempt(fraction):
        shape = translate(design.longhorn(cfg.longhorn_span * fraction, cfg.min_feature),
                          yoff=cfg.longhorn_offset_y)
        if design.max_radius(shape) > cfg.art_limit_r:
            return None
        if not obstacles.is_empty and shape.distance(obstacles) < cfg.art_gap:
            return None
        return shape

    full = attempt(1.0)
    if full is not None:
        return full, cfg.longhorn_span

    lo, hi, best = 0.25, 1.0, None
    for _ in range(30):
        mid = (lo + hi) / 2.0
        shape = attempt(mid)
        if shape is None:
            hi = mid
        else:
            lo, best = mid, shape
    if best is None:
        raise RuntimeError("longhorn will not fit -- shrink the text or widen the disc")
    return best, cfg.longhorn_span * lo


# --------------------------------------------------------------------------
# parts
# --------------------------------------------------------------------------


def build_cutter(cfg: Config) -> trimesh.Trimesh:
    """Round cutter ring, modelled flange-down / cutting-edge-up for printing.

    The blade is thick at the flange and tapers to a fine edge, which means the
    inner face leans outwards by only a few degrees going up -- self-supporting,
    and it gives a properly sharp edge without a knife-thin first layer.
    """
    r_out = cfg.cutter_r
    r_in_base = r_out - cfg.wall_base
    r_in_edge = r_out - cfg.wall_edge
    gusset = cfg.flange_thickness + cfg.flange_width * 0.6

    profile = [
        (r_in_base, 0.0),
        (r_out + cfg.flange_width, 0.0),
        (r_out + cfg.flange_width, cfg.flange_thickness),
        (r_out, gusset),
        (r_out, cfg.blade_height),
        (r_in_edge, cfg.blade_height),
    ]
    return geom.revolve(profile, cfg.segments)


def build_stamp(cfg: Config, art) -> trimesh.Trimesh:
    """Drop-in stamp: a plate with the raised artwork on top and a handle socket
    underneath. Printed artwork-up, so every letter grows off the bed."""
    plate = geom.prism(geom.disc(cfg.stamp_r, cfg.segments), 0.0, cfg.plate_thickness)

    cuts = [geom.prism(geom.disc(cfg.socket_diameter / 2.0, 96), -0.5, cfg.socket_depth)]
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

    relief = geom.prism(art, cfg.plate_thickness - 0.4,
                        cfg.plate_thickness + cfg.relief_height)
    return geom.union([plate, relief])


def build_handle(cfg: Config) -> trimesh.Trimesh:
    """Press-fit knob for the back of the stamp. Prints peg-up, no supports."""
    peg_r = (cfg.socket_diameter - cfg.handle_peg_clearance) / 2.0
    peg_len = cfg.socket_depth - 0.3
    palm_r = cfg.handle_palm_diameter / 2.0
    flange_r = cfg.handle_flange_diameter / 2.0
    top = cfg.handle_height

    profile = [
        (0.0, 0.0),
        (palm_r, 0.0),
        (palm_r + 1.0, 1.2),
        (flange_r, top - 3.0),
        (flange_r, top),
        (peg_r, top),
        (peg_r, top + peg_len),
        (0.0, top + peg_len),
    ]
    return geom.revolve(profile, cfg.segments)


def build_combined(cfg: Config, art) -> trimesh.Trimesh:
    """One-piece cutter + embosser: backing plate, raised artwork, blade around it.

    Two depths are in tension here. The blade has to stand proud of the artwork
    so the edge cuts clean through while the artwork only presses in -- that is
    what `blade - relief` buys. But the blade also caps how thick the dough can
    be: you press until the blade bottoms out on the board, so the plate ends up
    one blade-height above it, and any dough thicker than that never gets cut
    through. Dough thinner than `blade - relief` never touches the artwork at
    all. Roll to roughly the blade height and both work.
    """
    plate_t = cfg.combined_plate_thickness
    r_out = cfg.cutter_r
    plate = geom.prism(geom.disc(r_out, cfg.segments), 0.0, plate_t)
    relief = geom.prism(art, plate_t - 0.4, plate_t + cfg.relief_height)
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
    return (f"  {name:<26} {hi[0]-lo[0]:6.1f} x {hi[1]-lo[1]:6.1f} x {hi[2]-lo[2]:6.1f} mm"
            f"   {mesh.volume/1000.0:6.1f} cm3   "
            f"{'watertight' if mesh.is_watertight else 'NOT WATERTIGHT'}"
            f"   {len(mesh.faces):>7d} tris")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--diameter", type=float, default=Config.diameter,
                    help="cookie diameter in mm (default 90)")
    ap.add_argument("--top-text", default=Config.top_text)
    ap.add_argument("--bottom-text", default=Config.bottom_text)
    ap.add_argument("--font", default=Config.font)
    ap.add_argument("--blade-height", type=float, default=Config.blade_height,
                    help="cutter ring cutting depth in mm (default 15)")
    ap.add_argument("--combined-blade-height", type=float,
                    default=Config.combined_blade_height,
                    help="one-piece blade depth in mm (default 5); this is also "
                         "the maximum dough thickness that part can handle")
    ap.add_argument("--relief-height", type=float, default=Config.relief_height)
    ap.add_argument("--no-mirror", action="store_true",
                    help="skip the mirror (artwork reads forwards on the tool -- "
                         "only useful for a coaster or a plaque)")
    ap.add_argument("--outdir", default="stl")
    ap.add_argument("--no-preview", action="store_true")
    args = ap.parse_args()

    cfg = Config(diameter=args.diameter, top_text=args.top_text,
                 bottom_text=args.bottom_text, font=args.font,
                 blade_height=args.blade_height, relief_height=args.relief_height,
                 combined_blade_height=args.combined_blade_height,
                 mirror=not args.no_mirror)

    scale = cfg.diameter / 90.0
    cfg.top_cap_height *= scale
    cfg.bottom_cap_height *= scale
    cfg.longhorn_span *= scale

    print(f"HNB Longhorns cookie cutter -- {cfg.diameter:.0f} mm")
    art, report = build_artwork(cfg)
    for k, v in report.items():
        print(f"  {k:<24} {v}")
    print()

    parts = {
        "1_cutter_ring": build_cutter(cfg),
        "2_stamp": build_stamp(cfg, art),
        "3_stamp_handle": build_handle(cfg),
        "4_combined_cutter_stamp": build_combined(cfg, art),
    }

    import os
    os.makedirs(args.outdir, exist_ok=True)
    for name, mesh in parts.items():
        print(describe(name, mesh))
        mesh.export(os.path.join(args.outdir, f"hnb_longhorn_{name}.stl"))

    if not args.no_preview:
        import preview
        os.makedirs("preview", exist_ok=True)
        cookie = design._mirror_x(art) if cfg.mirror else art
        preview.plot_flat(
            [("stamp face (mirrored - what you print)", art, "#3f6b8a"),
             ("the cookie (what you get)", cookie, "#a9752f")],
            "preview/01_artwork.png", disc_radius=cfg.stamp_r)
        preview.render_mesh(parts["2_stamp"], "preview/02_stamp.png",
                            colours=["#4a7fa5"], title="stamp (artwork up, as printed)",
                            highlight_above=cfg.plate_thickness + 0.05)
        preview.render_mesh(parts["1_cutter_ring"], "preview/03_cutter.png",
                            colours=["#7d8a96"], title="cutter ring (edge up, as printed)")
        preview.render_mesh(parts["4_combined_cutter_stamp"], "preview/04_combined.png",
                            colours=["#8a6a4a"], title="one-piece cutter + embosser",
                            highlight_above=cfg.combined_plate_thickness + 0.05)
        handle_beside = parts["3_stamp_handle"].copy()
        handle_beside.apply_translation([cfg.stamp_r + 22.0, 0, 0])
        preview.render_mesh([parts["2_stamp"], handle_beside],
                            "preview/05_set.png", colours=["#4a7fa5", "#c2603f"],
                            highlight_above=cfg.plate_thickness + 0.05,
                            title="stamp + handle, laid out as they print")
        print("\n  previews written to preview/")


if __name__ == "__main__":
    main()
