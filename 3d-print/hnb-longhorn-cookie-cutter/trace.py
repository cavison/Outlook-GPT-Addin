"""Turn the supplied raster artwork into printable vector outlines.

The source images are light artwork on a dark ground, saved as JPEG. Three
things have to be dealt with before the shapes are usable as geometry:

  * JPEG ringing puts stray light pixels along the frame edges, which would
    otherwise trace as phantom shapes;
  * pixel edges are stair-stepped, and those steps would print as visible
    serrations along every horn and letter;
  * letters like O, G and B have counters, so contour nesting has to be
    respected rather than filling every outline solid.

Illustrated artwork needs the opposite of that last point: a drawing split into
panels by light seams should come back as one solid silhouette, so `invert`,
`close_px` and `fill_holes` handle dark-on-light sources whose interior
detailing must be swallowed rather than preserved.
"""

from __future__ import annotations

import cv2
import numpy as np
from shapely.affinity import scale as shp_scale, translate
from shapely.geometry import Polygon
from shapely.ops import unary_union


def _mask(path, blur_px, min_area_frac, invert=False, close_px=0.0,
          fill_holes=False):
    """Binary mask of the artwork, de-speckled and edge-smoothed."""
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(path)

    mode = cv2.THRESH_BINARY_INV if invert else cv2.THRESH_BINARY
    _, mask = cv2.threshold(img, 0, 255, mode + cv2.THRESH_OTSU)

    # Illustrated artwork is often carved up by thin light-coloured seams
    # between panels. For a silhouette those are not real edges, so close them
    # before anything else -- the kernel is sized to swallow a seam and stay far
    # narrower than a genuine gap such as the space between two legs.
    if close_px > 0:
        k = int(close_px * 2) | 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    # Drop everything that is not a real piece of artwork -- JPEG noise along
    # the frame, stray specks in the background.
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    keep = np.zeros_like(mask)
    floor = min_area_frac * mask.size
    for i in range(1, count):
        if stats[i, cv2.CC_STAT_AREA] >= floor:
            keep[labels == i] = 255

    # Blurring then re-thresholding rounds the pixel staircase off the edges.
    # The kernel stays far smaller than any real stroke, so nothing thins.
    if blur_px > 0:
        k = int(blur_px * 4) | 1
        keep = cv2.GaussianBlur(keep, (k, k), blur_px)
        _, keep = cv2.threshold(keep, 127, 255, cv2.THRESH_BINARY)

    # Any light region fully enclosed by artwork is interior detail, not a real
    # opening, so flooding in from outside and keeping what it cannot reach
    # leaves a solid silhouette.
    if fill_holes:
        flood = keep.copy()
        pad = np.zeros((flood.shape[0] + 2, flood.shape[1] + 2), np.uint8)
        cv2.floodFill(flood, pad, (0, 0), 255)
        keep = keep | cv2.bitwise_not(flood)
    return keep


def _contours_to_polygon(mask, simplify_px):
    """Contours -> shapely, honouring nesting so counters stay open."""
    contours, hierarchy = cv2.findContours(mask, cv2.RETR_CCOMP,
                                           cv2.CHAIN_APPROX_SIMPLE)
    if hierarchy is None:
        raise ValueError("no contours found")
    hierarchy = hierarchy[0]

    shells, holes = [], []
    for contour, (_, _, _, parent) in zip(contours, hierarchy):
        if len(contour) < 4:
            continue
        poly = Polygon(contour[:, 0, :])
        if not poly.is_valid:
            poly = poly.buffer(0)
        if poly.is_empty or poly.area <= 0:
            continue
        (holes if parent >= 0 else shells).append(poly)

    built = []
    for shell in shells:
        own = [h for h in holes if shell.contains(h.representative_point())]
        built.append(shell.difference(unary_union(own)) if own else shell)

    art = unary_union(built)
    return art.simplify(simplify_px) if simplify_px else art


def trace(path, width_mm, blur_px=2.0, simplify_px=1.2, min_area_frac=2e-4,
          round_mm=0.0, invert=False, close_px=0.0, fill_holes=False):
    """Trace an image into a shapely shape `width_mm` wide, centred on the origin.

    Image rows run downward, so the result is flipped to put y upward.
    `round_mm` softens remaining corners by an open-close pair, which is worth a
    little on hand-drawn artwork and nothing on clean geometry.
    """
    mask = _mask(path, blur_px, min_area_frac, invert, close_px, fill_holes)
    art = _contours_to_polygon(mask, simplify_px)

    minx, miny, maxx, maxy = art.bounds
    factor = width_mm / (maxx - minx)
    art = shp_scale(art, xfact=factor, yfact=-factor, origin=(0, 0))

    if round_mm > 0:
        art = art.buffer(round_mm).buffer(-2 * round_mm).buffer(round_mm)

    minx, miny, maxx, maxy = art.bounds
    return translate(art, xoff=-(minx + maxx) / 2.0, yoff=-(miny + maxy) / 2.0)
