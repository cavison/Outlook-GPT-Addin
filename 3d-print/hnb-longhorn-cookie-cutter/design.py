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

import numpy as np
from shapely.affinity import scale as shp_scale

import trace

LONGHORN_IMAGE = "art/longhorn_source.jpg"
LOGO_IMAGE = "art/logo_source.jpg"


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


def longhorn(limit_r, mirror=True):
    """The longhorn silhouette for the cookie face, sized to fill `limit_r`."""
    art = fit_to_radius(trace.trace(LONGHORN_IMAGE, width_mm=70.0), limit_r)
    return mirror_x(art) if mirror else art


def logo(limit_r, mirror=True):
    """The HNB Longhorns wordmark and skull for the hand face."""
    art = fit_to_radius(trace.trace(LOGO_IMAGE, width_mm=70.0), limit_r)
    return mirror_x(art) if mirror else art
