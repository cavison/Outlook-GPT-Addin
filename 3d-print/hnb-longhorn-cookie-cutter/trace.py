"""Turn the supplied raster artwork into printable vector outlines.

The source images are light artwork on a dark ground, saved as JPEG. Three
things have to be dealt with before the shapes are usable as geometry:

  * JPEG ringing puts stray light pixels along the frame edges, which would
    otherwise trace as phantom shapes;
  * pixel edges are stair-stepped, and those steps would print as visible
    serrations along every horn and letter;
  * letters like O, G and B have counters, so contour nesting has to be
    respected rather than filling every outline solid.
"""

from __future__ import annotations

import cv2
import numpy as np
from shapely.affinity import scale as shp_scale, translate
from shapely.geometry import Polygon
from shapely.ops import unary_union


def _mask(path, blur_px, min_area_frac):
    """Binary mask of the artwork, de-speckled and edge-smoothed."""
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(path)

    _, mask = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

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
          round_mm=0.0):
    """Trace an image into a shapely shape `width_mm` wide, centred on the origin.

    Image rows run downward, so the result is flipped to put y upward.
    `round_mm` softens remaining corners by an open-close pair, which is worth a
    little on hand-drawn artwork and nothing on clean geometry.
    """
    mask = _mask(path, blur_px, min_area_frac)
    art = _contours_to_polygon(mask, simplify_px)

    minx, miny, maxx, maxy = art.bounds
    factor = width_mm / (maxx - minx)
    art = shp_scale(art, xfact=factor, yfact=-factor, origin=(0, 0))

    if round_mm > 0:
        art = art.buffer(round_mm).buffer(-2 * round_mm).buffer(round_mm)

    minx, miny, maxx, maxy = art.bounds
    return translate(art, xoff=-(minx + maxx) / 2.0, yoff=-(miny + maxy) / 2.0)
