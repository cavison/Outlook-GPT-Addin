"""One builder per style. Each returns {part name: mesh}.

    emboss  a plain outline cutter, plus a two-sided stamp that presses an
            unrelated design into the cookie it cuts
    cutout  the silhouette, cut, and nothing else
    hybrid  the silhouette cut by a ring, with that subject's own detail lines
            pressed in by an insert nested inside it
"""

from __future__ import annotations

import artwork
import body
import geom


def build_cutout(design, spec: body.Spec):
    shape = artwork.outline_shape(design)
    return {"cutter": body.cutter_body(shape, spec)}, {"outline": shape}


def build_hybrid(design, spec: body.Spec):
    """Ring plus nested insert, as the reference hybrids are built.

    The blade runs `cut_depth` alone before the ribs begin, so the dough has to
    be about that thick: the blade reaches the board while the ribs press into
    the top of it. Thinner dough is cut but never marked.
    """
    shape = artwork.outline_shape(design)
    detail = artwork.mirror_x(
        artwork.resize(artwork.silhouette(design.inner, design.size), design.size))

    # The insert drops in from the lip end and seats flush, so its rib tips end
    # up (ring height - insert height) above the cutting edge. That gap is the
    # dough depth the blade cuts before the ribs start marking.
    ring_h = spec.insert_plate + spec.rib_height + spec.cut_depth
    parts = {
        "ring": body.cutter_body(shape, spec, height=ring_h),
        "insert": body.rib_stamp(shape, detail, spec),
    }
    return parts, {"outline": shape, "detail": detail}


def build_emboss(design, spec: body.Spec):
    """The round set: cutter ring, and a stamp with artwork raised on the
    cookie face and the wordmark engraved on the hand face."""
    import hnb_config as cfgmod
    cfg = cfgmod.EmbossConfig(diameter=design.size)

    shape = artwork.outline_shape(design)
    inner = artwork.mirror_x(
        artwork.fit_to_radius(artwork.silhouette(design.inner, 70.0),
                              cfg.stamp_art_limit_r))
    back = None
    if design.back:
        back = artwork.mirror_x(
            artwork.fit_to_radius(artwork.silhouette(design.back, 70.0),
                                  cfg.stamp_art_limit_r))

    parts = {
        "cutter": body.cutter_body(shape, spec),
        "stamp": body.stamp_plate(geom.disc(cfg.stamp_r, 256), inner, back, spec,
                                  cfg.plate_thickness, cfg.relief_height,
                                  cfg.logo_depth),
    }
    return parts, {"outline": shape, "inner": inner, "back": back}


BUILDERS = {"emboss": build_emboss, "cutout": build_cutout, "hybrid": build_hybrid}
