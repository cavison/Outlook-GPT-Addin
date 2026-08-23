"""What artwork exists, and which tool each design turns into.

Two registries. ART is raw source images and how to trace each one. DESIGNS
names a finished product: a style, the artwork that style needs, and its size.
Adding a cutter means adding a DESIGNS entry, not writing code.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from shapely.affinity import scale as shp_scale

import geom
import trace

# Source images, with whatever the tracer needs to read each one. Light-on-dark
# artwork traces straight; a dark illustration on white needs inverting, its
# panel seams closed, and its interior detail flooded solid.
ART = {
    "skull": {"path": "art/longhorn_source.jpg"},
    "steer": {"path": "art/steer_source.png", "invert": True,
              "close_px": 6.0, "fill_holes": True},
    "logo":  {"path": "art/logo_source.jpg"},

    # Line art gives both halves of a hybrid from one drawing: flood it solid
    # for the shape to cut, and take the raw strokes for the lines to press in.
    # The outer stroke needs no special handling -- the insert plate is inset
    # from the cut edge, so clipping the detail to it drops the boundary line.
    "steerline":     {"path": "art/steer_line.png", "invert": True,
                      "close_px": 3.0, "fill_holes": True},
    "steerline_dtl": {"path": "art/steer_line.png", "invert": True,
                      "min_area_frac": 5e-5},

    # Head logo: its horn tips run off the edge of the source image, so they are
    # rebuilt and then lengthened. See restore.py.
    "headlogo":     {"path": "art/head_logo.png", "invert": True,
                     "fill_holes": True,
                     "restore": {"lengthen": 0.20, "sides": ("left", "right")}},
    "headlogo_dtl": {"path": "art/head_logo.png", "invert": True,
                     "detail_from_holes": True},

    "buckle":     {"path": "art/buckle.png", "invert": True, "fill_holes": True,
                   "close_px": 4.0},
    "buckle_dtl": {"path": "art/buckle.png", "invert": True, "min_area_frac": 3e-4},
}

STYLES = ("emboss", "cutout", "hybrid")


@dataclass
class Design:
    """One finished product.

    style    emboss  cut a plain outline, press a separate design into it
             cutout  cut a silhouette and nothing else
             hybrid  cut a silhouette, press that subject's own detail lines in
    outline  ART key for the cut shape, or "circle"
    inner    emboss: what is raised on the stamp. hybrid: the detail lines
    back     ART key engraved on the hand face (emboss only)
    size     widest dimension of the cookie, in mm
    fatten   dilate the outline so thin runs of dough survive handling
    """
    style: str
    outline: str
    inner: str | None = None
    back: str | None = None
    size: float = 76.2
    fatten: float = 1.5
    spec: dict = field(default_factory=dict)   # per-design body.Spec overrides
    notes: str = ""


DESIGNS = {
    # The original round set: a circular cookie with the skull pressed into it
    # and the wordmark engraved on the back. Not fattened -- nothing is cut to
    # a thin shape, so there is no fragile dough.
    "round_longhorn": Design("emboss", outline="circle", inner="skull",
                             back="logo", size=90.0, fatten=0.0,
                             spec={"lip_offset": 5.0, "lip_height": 2.5,
                                   "chamfer": 3.0}),

    "skull": Design("cutout", outline="skull",
                    notes="horns are thin; fattening does the heavy lifting"),
    "steer": Design("cutout", outline="steer"),

    # --- hybrids ----------------------------------------------------------
    "steer_line": Design("hybrid", outline="steerline", inner="steerline_dtl",
                         size=76.2,
                         notes="line drawing: filled for the cut, strokes for the ribs"),
    "head_logo":  Design("hybrid", outline="headlogo", inner="headlogo_dtl",
                         size=76.2, fatten=1.0,
                         notes="horn tips rebuilt from the crop and lengthened 20%"),
    "buckle":     Design("hybrid", outline="buckle", inner="buckle_dtl",
                         size=88.9, fatten=0.0,
                         notes="scrollwork is very fine; needs a big cookie"),
}


def available(name):
    """Is every image this design needs actually in the repo?"""
    d = DESIGNS[name]
    keys = [k for k in (d.outline, d.inner, d.back) if k and k != "circle"]
    return all(os.path.exists(ART[k]["path"]) for k in keys)


def missing_art(name):
    d = DESIGNS[name]
    keys = [k for k in (d.outline, d.inner, d.back) if k and k != "circle"]
    return sorted({ART[k]["path"] for k in keys
                   if not os.path.exists(ART[k]["path"])})


def silhouette(key, width_mm):
    """Traced artwork scaled so its widest dimension is `width_mm`."""
    spec = dict(ART[key])
    path = spec.pop("path")
    fix = spec.pop("restore", None)
    holes = spec.pop("detail_from_holes", False)
    if not os.path.exists(path):
        raise FileNotFoundError(f"artwork {key!r} needs {path}")

    art = trace.trace(path, width_mm=width_mm, **spec)

    if holes:
        # Interior detail of a solid logo lives in its holes -- the light lines
        # cut through the dark shape. Filling and differencing recovers them.
        import shapely
        solid = trace.trace(path, width_mm=width_mm, fill_holes=True, **spec)
        art = solid.difference(art)

    if fix:
        import restore
        art, notes = restore.extend_clipped(art, art.bounds, **fix)
        for n in notes:
            if n.get("rebuilt"):
                print(f"      rebuilt {n['side']} tip of {key!r}: "
                      f"+{n['added_mm']:.1f} mm off a {n['cut_width_mm']:.1f} mm cut")
    return resize(art, width_mm)


def resize(art, width_mm):
    minx, miny, maxx, maxy = art.bounds
    span = max(maxx - minx, maxy - miny)
    return shp_scale(art, xfact=width_mm / span, yfact=width_mm / span,
                     origin=(0, 0))


def mirror_x(polygon):
    return shp_scale(polygon, xfact=-1.0, yfact=1.0, origin=(0, 0))


def fit_to_radius(art, limit_r):
    """Scale artwork about the origin until it just fits inside `limit_r`."""
    import numpy as np
    best = 0.0
    for part in getattr(art, "geoms", [art]):
        for ring in [part.exterior, *part.interiors]:
            pts = np.asarray(ring.coords)
            best = max(best, float(np.hypot(pts[:, 0], pts[:, 1]).max()))
    f = limit_r / best
    return shp_scale(art, xfact=f, yfact=f, origin=(0, 0))


def outline_shape(design, spec_size=None):
    """The cut outline for a design, fattened and mirrored ready for use.

    Mirrored because a cutter is printed lip-down and flipped lip-up to press,
    and flipping mirrors the outline it cuts.
    """
    size = spec_size or design.size
    if design.outline == "circle":
        return geom.disc(size / 2.0)
    art = silhouette(design.outline, size)
    if design.fatten > 0:
        art = resize(art.buffer(design.fatten), size)
    return mirror_x(art)
