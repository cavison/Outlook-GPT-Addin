"""Rebuild artwork that runs off the edge of its own image.

Source art is often cropped: a longhorn's horn tips get cut by the frame. A
cutter built from it would have blunt, squared-off horns. This walks back from
each cut edge, reads how the horn was heading and how fast it was narrowing,
and continues it to a point -- optionally past the natural tip, to lengthen the
horns beyond what the original drawing showed.
"""

from __future__ import annotations

import numpy as np
from shapely.geometry import LineString, MultiPolygon, Polygon
from shapely.ops import unary_union

import geom

SIDES = {"left": 0, "right": 2, "bottom": 1, "top": 3}


def _clipped_runs(shape, frame, eps=1e-6):
    """Spans where the outline lies along the image border -- i.e. was cut."""
    minx, miny, maxx, maxy = frame
    runs = []
    for part in getattr(shape, "geoms", [shape]):
        pts = np.asarray(part.exterior.coords)
        for side, value, axis in (("left", minx, 0), ("right", maxx, 0),
                                  ("bottom", miny, 1), ("top", maxy, 1)):
            on = np.abs(pts[:, axis] - value) < eps + 1e-3
            if not on.any():
                continue
            other = 1 - axis
            idx = np.where(on)[0]
            # group consecutive indices into separate cut edges
            for grp in np.split(idx, np.where(np.diff(idx) != 1)[0] + 1):
                if len(grp) < 2:
                    continue
                lo, hi = pts[grp, other].min(), pts[grp, other].max()
                if hi - lo > 1e-3:
                    runs.append((side, axis, value, lo, hi))
    return runs


def _profile(shape, axis, value, lo, hi, inward, depth, samples):
    """Centre and half-width of the limb at increasing depth from the cut."""
    centres, halves, depths = [], [], []
    guess = (lo + hi) / 2.0
    for d in np.linspace(0.0, depth, samples):
        coord = value + inward * d
        if axis == 0:
            line = LineString([(coord, lo - depth * 3), (coord, hi + depth * 3)])
        else:
            line = LineString([(lo - depth * 3, coord), (hi + depth * 3, coord)])
        inter = shape.intersection(line)
        if inter.is_empty:
            break
        segs = list(getattr(inter, "geoms", [inter]))
        best = None
        for seg in segs:
            c = np.asarray(seg.coords)
            if len(c) < 2:
                continue
            a, b = c[:, 1 - axis].min(), c[:, 1 - axis].max()
            mid = (a + b) / 2.0
            if best is None or abs(mid - guess) < abs(best[0] - guess):
                best = (mid, (b - a) / 2.0)
        if best is None or best[1] <= 0:
            break
        guess = best[0]
        centres.append(best[0]); halves.append(best[1]); depths.append(d)
    return np.array(depths), np.array(centres), np.array(halves)


def _extend_one(shape, side, axis, value, lo, hi, lengthen, span, samples, depth):
    inward = 1.0 if side in ("left", "bottom") else -1.0
    d, c, h = _profile(shape, axis, value, lo, hi, inward, depth, samples)
    if len(d) < 4:
        return None

    # How the limb is heading and how fast it is narrowing, read just inside the
    # cut. Quadratic centre keeps the curve of the horn; linear half-width gives
    # the taper rate and therefore where the point would naturally have landed.
    cq = np.polyfit(d, c, 2)
    hl = np.polyfit(d, h, 1)
    slope = hl[0]
    if slope <= 1e-6:
        return None                      # not narrowing: not a cut-off tip
    natural = h[0] / slope               # distance beyond the cut to the point
    extra = lengthen * span / 2.0
    total = natural + extra
    if total <= 0:
        return None

    t = np.linspace(0.0, total, 60)
    dd = -t                              # walking back out past the border
    centre = np.polyval(cq, dd)
    # Taper from the cut width to a point over the whole extension. Following
    # the fitted line instead would reach zero at the natural tip and give the
    # requested extra length no width at all, so lengthening would do nothing.
    width = 2.0 * h[0] * np.clip(1.0 - t / total, 0.0, 1.0)

    coord = value + inward * dd
    pts = np.column_stack([coord, centre]) if axis == 0 else np.column_stack([centre, coord])
    return geom.variable_width_stroke(pts, width, round_tip=False)


def extend_clipped(shape, frame, lengthen=0.20, samples=16, depth=None,
                   sides=("left", "right")):
    """Restore every cut-off tip, and lengthen it by `lengthen` of the span.

    `lengthen` is a fraction of the artwork's overall width, applied per tip, so
    0.20 makes a two-horned silhouette roughly 20% wider overall.

    How far back from the cut to read the taper decides everything. Sampling too
    deep averages in the thick part of the horn near the skull, reads a gentler
    taper than the tip actually has, and overshoots the point badly -- at a fifth
    of the span it rebuilt 24 mm of horn where 10 mm was missing. Scaling the
    window to the width of the cut itself keeps the reading local to the tip.
    Checked against a deliberately cropped silhouette with a known answer, four
    times the cut width recovered 10.0 and 9.9 mm against a true 10.0 mm.

    `sides` limits which borders count as cuts: a chin resting on the bottom of
    the frame is not a severed horn.

    Returns (new_shape, [report dicts]).
    """
    minx, miny, maxx, maxy = frame
    span = maxx - minx

    additions, notes = [], []
    for side, axis, value, lo, hi in _clipped_runs(shape, frame):
        if side not in sides:
            continue
        window = depth or min(max(4.0 * (hi - lo), span * 0.02), span * 0.25)
        piece = _extend_one(shape, side, axis, value, lo, hi,
                            lengthen, span, samples, window)
        if piece is None or piece.is_empty:
            notes.append({"side": side, "at": (lo + hi) / 2.0, "rebuilt": False})
            continue
        additions.append(piece)
        b = piece.bounds
        notes.append({"side": side, "at": (lo + hi) / 2.0, "rebuilt": True,
                      "added_mm": max(b[2] - b[0], b[3] - b[1]),
                      "cut_width_mm": hi - lo})
    if not additions:
        return shape, notes
    return unary_union([shape, *additions]).buffer(0), notes
