"""Places the supplied HNB artwork on the two faces of the tool.

Two pieces of artwork, two faces, and both need mirroring -- for different
reasons that are easy to conflate:

  Cookie face (longhorn, raised). Pressed into dough, and dough receives a
  mirror of whatever presses it. Mirror so the cookie reads forwards.

  Hand face (logo, engraved). Nothing is pressed here, so the stamping mirror
  does not apply. But this face is looked at from its own side, and any plane
  seen from behind reads mirrored -- write a letter on glass, walk around it,
  and you read it backwards. Mirror so the logo reads forwards in the hand.

So both faces get mirrored polygons. Same operation, unrelated causes.
"""

from __future__ import annotations

import os

import numpy as np
from shapely.affinity import scale as shp_scale

import trace

LOGO_IMAGE = "art/logo_source.jpg"

# Silhouette artwork, shared by the embossing stamps and the outline cutters.
# Each entry is a source image plus
# whatever the tracer needs to read it: the skull is light on dark and traces
# straight, while the steer is a dark illustration on white whose panel seams
# have to be closed and whose interior detail has to be flooded solid before it
# reads as one silhouette.
SILHOUETTES = {
    "skull": {"path": "art/longhorn_source.jpg"},
    "steer": {"path": "art/steer_source.png", "invert": True,
              "close_px": 6.0, "fill_holes": True},
}


def mirror_x(polygon):
    return shp_scale(polygon, xfact=-1.0, yfact=1.0, origin=(0, 0))


def max_radius(polygon):
    """Largest distance from the origin to any point on the shape."""
    best = 0.0
    for part in getattr(polygon, "geoms", [polygon]):
        for ring in [part.exterior, *part.interiors]:
            pts = np.asarray(ring.coords)
            best = max(best, float(np.hypot(pts[:, 0], pts[:, 1]).max()))
    return best


def fit_to_radius(art, limit_r):
    """Scale artwork about the origin until it just fits inside `limit_r`.

    The artwork is centred on the origin, so max radius scales linearly and
    this lands exactly in one step -- no search needed.
    """
    factor = limit_r / max_radius(art)
    return shp_scale(art, xfact=factor, yfact=factor, origin=(0, 0))


def available_emboss():
    """Emboss variants whose source image is actually present."""
    return [n for n, spec in SILHOUETTES.items()
            if os.path.exists(spec["path"])]


def emboss(name, limit_r, mirror=True):
    """Cookie-face silhouette for one variant, sized to fill `limit_r`."""
    art = silhouette(name, width_mm=70.0)
    art = fit_to_radius(art, limit_r)
    return mirror_x(art) if mirror else art


def silhouette(name, width_mm):
    """Raw traced silhouette, scaled so its widest dimension is `width_mm`."""
    spec = dict(SILHOUETTES[name])
    path = spec.pop("path")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"silhouette {name!r} needs {path}, which is not in the repo")
    art = trace.trace(path, width_mm=width_mm, **spec)
    minx, miny, maxx, maxy = art.bounds
    span = max(maxx - minx, maxy - miny)
    if abs(span - width_mm) > 1e-9:
        art = shp_scale(art, xfact=width_mm / span, yfact=width_mm / span,
                        origin=(0, 0))
    return art


def logo(limit_r, mirror=True):
    """The HNB Longhorns wordmark and skull for the hand face."""
    art = fit_to_radius(trace.trace(LOGO_IMAGE, width_mm=70.0), limit_r)
    return mirror_x(art) if mirror else art
