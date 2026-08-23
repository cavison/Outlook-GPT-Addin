"""Shared solids. All three styles are assembled from these.

Dimensions come from measuring the reference cutters, not from guessing:

  ref/sample_tree.obj        plain cutter -- 15.0 tall, 0.80 blade,
                             lip +2.0 outward over 3.4, 1.6 chamfer
  ref/hybrid/obj_2_tygr.stl  hybrid -- ring 13.0 tall with a 1.2 blade
                             thinning to 0.80 at the edge, plus a separate
                             nested insert: 4.5 plate carrying 3.0 tall,
                             1.27 wide detail ribs, inset ~0.9 from the cavity
"""

from __future__ import annotations

from dataclasses import dataclass

import geom


@dataclass
class Spec:
    # --- cutter body ------------------------------------------------------
    height: float = 15.0
    wall: float = 0.80          # blade thickness at the cutting edge
    lip_offset: float = 2.0     # how far the lip flares outward
    lip_height: float = 3.4
    chamfer: float = 1.6
    chamfer_steps: int = 8      # 0.2 mm per step: one layer, so invisible

    # --- hybrid insert ----------------------------------------------------
    insert_clearance: float = 0.9   # inset from the blade cavity
    insert_plate: float = 3.0       # solid backing behind the ribs
    rib_height: float = 3.0
    rib_width: float = 1.3
    cut_depth: float = 6.0          # blade alone below the ribs = dough depth

    # --- practical --------------------------------------------------------
    min_dough: float = 5.0      # dough narrower than this snaps when handled


def cutter_body(shape, spec: Spec, height=None):
    """Blade following `shape`, with the grip lip flaring out at the base.

    Swept outer profile minus one cavity prism. The lip's inner edge and the
    blade's inner edge are the same curve -- that is how the reference is
    built -- so the cavity is a plain vertical prism and no lofting between
    changing cross-sections is needed.

    The chamfer is stepped rather than lofted because offsetting a silhouette
    by a varying amount changes its topology unpredictably.
    """
    height = height or spec.height
    blade_top = spec.lip_height + spec.chamfer
    if blade_top >= height:
        raise ValueError("lip and chamfer are taller than the cutter")

    layers = [geom.prism(shape.buffer(spec.lip_offset), 0.0, spec.lip_height)]
    for i in range(spec.chamfer_steps):
        z0 = spec.lip_height + i * spec.chamfer / spec.chamfer_steps
        z1 = z0 + spec.chamfer / spec.chamfer_steps
        out = spec.lip_offset * (1.0 - (i + 0.5) / spec.chamfer_steps)
        layers.append(geom.prism(shape.buffer(out), z0, z1))
    layers.append(geom.prism(shape, blade_top, height))

    cavity = shape.buffer(-spec.wall)
    if cavity.is_empty:
        raise ValueError("wall is thicker than the shape -- nothing left to cut")
    return geom.difference([geom.union(layers),
                            geom.prism(cavity, -1.0, height + 1.0)])


def rib_stamp(shape, detail, spec: Spec):
    """Hybrid insert: a backing plate with detail ribs standing off it.

    Nests inside the cutter's cavity. Printed ribs-up, which is the only way
    round -- ribs on the bed would be a scatter of tiny first-layer islands.
    """
    plate = shape.buffer(-spec.wall - spec.insert_clearance)
    if plate.is_empty:
        raise ValueError("shape too small to hold an insert at this clearance")

    ribs = detail.intersection(plate.buffer(-0.4))
    if ribs.is_empty:
        raise ValueError("detail lines fall outside the insert plate")

    return geom.union([
        geom.prism(plate, 0.0, spec.insert_plate),
        geom.prism(ribs, spec.insert_plate - 0.3,
                   spec.insert_plate + spec.rib_height),
    ])


def stamp_plate(shape, raised, engraved, spec: Spec, thickness, relief,
                engrave_depth):
    """Emboss-style two-sided stamp: raised artwork one face, engraving the other."""
    plate = geom.prism(shape, 0.0, thickness)
    if engraved is not None:
        plate = geom.difference([plate, geom.prism(engraved, -0.5, engrave_depth)])
    return geom.union([plate,
                       geom.prism(raised, thickness - 0.4, thickness + relief)])
