"""The HNB Longhorns artwork: an original longhorn silhouette plus arc text.

The silhouette is drawn from scratch as a generic longhorn steer head -- it is
deliberately not a trace of any university or club mark, so the model stays
yours to print, share or sell.

Everything is laid out at true millimetre scale on the stamp face. The final
step mirrors the whole composition, because a stamp pressed into dough leaves a
mirror image: the artwork on the tool has to be backwards so the cookie comes
out reading forwards.
"""

from __future__ import annotations

import numpy as np
from shapely.affinity import scale as shp_scale, translate
from shapely.geometry import Polygon
from shapely.ops import unary_union

import geom

# Head outline control points, right-hand half, running from the top of the
# skull down to the chin. Units are arbitrary here; the whole silhouette gets
# scaled to fit the stamp later.
HEAD_HALF = [
    (0.0, 14.5), (7.2, 13.8), (12.4, 10.6), (15.0, 4.6), (14.6, -2.4),
    (12.2, -9.4), (9.4, -16.2), (8.4, -21.6), (6.4, -25.8), (3.0, -27.8),
    (0.0, -28.3),
]

# Horn centreline as a cubic bezier, shaped after a mounted longhorn skull:
# the horn leaves the top of the skull, dips just below its own base, sweeps
# far out nearly level, then hooks hard upward in the last stretch. The two
# middle control points sit low and far out, which is what keeps the sweep flat
# and concentrates all the rise into the tip -- a hook rather than a gentle arc.
HORN_BEZIER = [(8.0, 7.0), (30.0, 2.0), (55.0, 3.0), (60.0, 23.0)]
HORN_BASE_WIDTH = 12.0
HORN_TAPER = 1.75              # higher = holds thickness longer, then tapers fast
HORN_SPAN_UNITS = 2 * HORN_BEZIER[-1][0]   # rough first guess only

EAR_CENTRE = (17.5, 1.0)
EAR_AXES = (6.4, 3.0)
EAR_ANGLE_DEG = -25.0


def _mirror_x(polygon):
    return shp_scale(polygon, xfact=-1.0, yfact=1.0, origin=(0, 0))


def _head():
    right = HEAD_HALF
    left = [(-x, y) for x, y in reversed(right[1:-1])]
    loop = right + left
    return Polygon(geom.catmull_rom(loop, samples_per_segment=18, closed=True)).buffer(0)


def _horn(tip_width_units):
    p0, p1, p2, p3 = HORN_BEZIER
    centre = geom.bezier(p0, p1, p2, p3, n=180)
    t = np.linspace(0.0, 1.0, len(centre))
    widths = tip_width_units + (HORN_BASE_WIDTH - tip_width_units) * (1.0 - t) ** HORN_TAPER
    return geom.variable_width_stroke(centre, widths, round_tip=True)


def _ear():
    ang = np.linspace(0, 2 * np.pi, 64, endpoint=False)
    pts = np.column_stack([EAR_AXES[0] * np.cos(ang), EAR_AXES[1] * np.sin(ang)])
    th = np.radians(EAR_ANGLE_DEG)
    rot = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    return Polygon(pts @ rot.T + np.asarray(EAR_CENTRE)).buffer(0)


def _assemble(tip_width_units):
    horn_r = _horn(tip_width_units)
    parts = [_head(), _ear(), horn_r, _mirror_x(_ear()), _mirror_x(horn_r)]
    return unary_union([p.buffer(0) for p in parts]).buffer(0)


def longhorn(span_mm, min_tip_width_mm=1.6):
    """Longhorn head silhouette, tip-to-tip `span_mm` wide, centred on the origin.

    `min_tip_width_mm` is enforced in real millimetres so the horn tips stay
    thick enough to both print cleanly and leave a mark in dough. That creates a
    circularity -- the tip width depends on the scale, and the scale depends on
    the assembled width -- so the scale is refined over a few passes. Since the
    tips hook upward the widest point is not simply the last control point, so
    the width is measured off the finished outline rather than assumed.
    """
    scale = span_mm / HORN_SPAN_UNITS
    for _ in range(4):
        shape = _assemble(min_tip_width_mm / scale)
        minx, _, maxx, _ = shape.bounds
        scale = span_mm / (maxx - minx)

    shape = shp_scale(shape, xfact=scale, yfact=scale, origin=(0, 0))
    minx, miny, maxx, maxy = shape.bounds
    return translate(shape, xoff=-(minx + maxx) / 2.0, yoff=-(miny + maxy) / 2.0)


def horn_profile(span_mm, min_tip_width_mm=1.6):
    """Width of one horn along its length, in real millimetres.

    The hooked tip is the thinnest structural feature in the whole design, so
    this is what decides whether the horns print and whether they leave a mark
    in dough. Returns (distance_from_tip_mm, width_mm).
    """
    scale = span_mm / HORN_SPAN_UNITS
    for _ in range(4):
        shape = _assemble(min_tip_width_mm / scale)
        minx, _, maxx, _ = shape.bounds
        scale = span_mm / (maxx - minx)

    tip_units = min_tip_width_mm / scale
    centre = geom.bezier(*HORN_BEZIER, n=180) * scale
    t = np.linspace(0.0, 1.0, len(centre))
    widths = (tip_units + (HORN_BASE_WIDTH - tip_units) * (1.0 - t) ** HORN_TAPER) * scale

    steps = np.linalg.norm(np.diff(centre, axis=0), axis=1)
    arc = np.concatenate([[0.0], np.cumsum(steps)])
    return arc[-1] - arc, widths


def max_radius(polygon):
    """Largest distance from the origin to any point on the shape."""
    best = 0.0
    parts = getattr(polygon, "geoms", [polygon])
    for part in parts:
        for ring in [part.exterior, *part.interiors]:
            pts = np.asarray(ring.coords)
            best = max(best, float(np.hypot(pts[:, 0], pts[:, 1]).max()))
    return best


def fit_longhorn(span_mm, limit_r, min_tip_width_mm=1.6, centre_y=0.0):
    """Build the longhorn, shrinking it until it clears `limit_r`."""
    for _ in range(24):
        shape = translate(longhorn(span_mm, min_tip_width_mm), yoff=centre_y)
        if max_radius(shape) <= limit_r:
            return shape, span_mm
        span_mm *= 0.97
    return shape, span_mm


def compose(cfg):
    """Build the artwork as it should appear ON THE COOKIE (not mirrored yet)."""
    font = geom.resolve_font(cfg.font)
    pieces = []

    if cfg.border_width > 0:
        pieces.append(geom.ring(cfg.border_outer_r, cfg.border_width, cfg.segments))

    pieces.append(geom.arc_text(cfg.top_text, font, cfg.top_cap_height,
                                cfg.top_baseline_r, on_top=True,
                                tracking=cfg.top_tracking))
    pieces.append(geom.arc_text(cfg.bottom_text, font, cfg.bottom_cap_height,
                                cfg.bottom_baseline_r, on_top=False,
                                tracking=cfg.bottom_tracking))

    horn, used_span = fit_longhorn(cfg.longhorn_span, cfg.longhorn_limit_r,
                                   cfg.min_feature, cfg.longhorn_offset_y)
    pieces.append(horn)

    art = unary_union([p.buffer(0) for p in pieces]).buffer(0)
    return art, used_span


def stamp_face(cfg):
    """The artwork as it must sit on the tool: mirrored left-to-right.

    Mirroring about the vertical axis keeps HNB at the top and LONGHORNS at the
    bottom while reversing the letters, which is exactly what a press-in stamp
    needs.
    """
    art, used_span = compose(cfg)
    return _mirror_x(art), used_span
