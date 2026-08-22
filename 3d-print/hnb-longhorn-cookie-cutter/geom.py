"""Reusable 2D/3D geometry helpers for the HNB Longhorns cookie cutter generator.

Everything here works in millimetres. 2D shapes are shapely geometries; 3D
shapes are trimesh meshes. Nothing in this module knows about the longhorn
design itself -- see design.py for that.
"""

from __future__ import annotations

import numpy as np
import shapely
import trimesh
from matplotlib.font_manager import FontProperties, findfont
from matplotlib.textpath import TextPath
from shapely.geometry import MultiPolygon, Point, Polygon
from shapely.ops import unary_union

# --------------------------------------------------------------------------
# curve primitives
# --------------------------------------------------------------------------


def bezier(p0, p1, p2, p3, n=96):
    """Sample a cubic bezier as an (n, 2) array of points."""
    t = np.linspace(0.0, 1.0, n)[:, None]
    p0, p1, p2, p3 = (np.asarray(p, float) for p in (p0, p1, p2, p3))
    return ((1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1
            + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3)


def catmull_rom(points, samples_per_segment=24, closed=True):
    """Smooth a control polygon into a Catmull-Rom spline.

    Used for the longhorn's head outline so a handful of control points give a
    flowing silhouette instead of a faceted one.
    """
    p = np.asarray(points, float)
    n = len(p)
    idx = (lambda i: p[i % n]) if closed else (lambda i: p[min(max(i, 0), n - 1)])
    last = n if closed else n - 1
    out = []
    for i in range(last):
        p0, p1, p2, p3 = idx(i - 1), idx(i), idx(i + 1), idx(i + 2)
        t = np.linspace(0.0, 1.0, samples_per_segment, endpoint=False)[:, None]
        out.append(0.5 * ((2 * p1)
                          + (-p0 + p2) * t
                          + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t ** 2
                          + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    return np.vstack(out)


def variable_width_stroke(centerline, widths, round_tip=True, tip_segments=24):
    """Turn a centreline into a filled polygon whose width varies along it.

    This is how the horns are built: a swept curve that starts fat where it
    meets the skull and tapers to a rounded point. `widths` is the full width
    at each centreline sample.
    """
    c = np.asarray(centerline, float)
    w = np.asarray(widths, float)
    d = np.gradient(c, axis=0)
    length = np.linalg.norm(d, axis=1, keepdims=True)
    length[length == 0] = 1.0
    tangent = d / length
    normal = np.column_stack([-tangent[:, 1], tangent[:, 0]])

    left = c + normal * (w[:, None] / 2.0)
    right = c - normal * (w[:, None] / 2.0)

    if round_tip:
        centre, radius = c[-1], w[-1] / 2.0
        start = np.arctan2(left[-1, 1] - centre[1], left[-1, 0] - centre[0])
        cap_ang = start + np.linspace(0, -np.pi, tip_segments)
        cap = centre + radius * np.column_stack([np.cos(cap_ang), np.sin(cap_ang)])
        ring = np.vstack([left, cap, right[::-1]])
    else:
        ring = np.vstack([left, right[::-1]])

    return Polygon(ring).buffer(0)


def resample(ring, max_segment=0.25):
    """Subdivide a ring so no edge is longer than `max_segment`.

    Called before the arc warp -- straight glyph edges have to become many
    short edges or they cut across the curve as visible chords.
    """
    pts = np.asarray(ring, float)
    if not np.allclose(pts[0], pts[-1]):
        pts = np.vstack([pts, pts[:1]])
    out = []
    for a, b in zip(pts[:-1], pts[1:]):
        steps = max(1, int(np.ceil(np.linalg.norm(b - a) / max_segment)))
        t = np.linspace(0.0, 1.0, steps, endpoint=False)[:, None]
        out.append(a + (b - a) * t)
    return np.vstack(out)


# --------------------------------------------------------------------------
# text
# --------------------------------------------------------------------------


def _rings_to_polygon(rings):
    """Assemble raw glyph contours into polygons using the even-odd rule.

    Font outlines arrive as a flat list of contours: the outside of an 'O' and
    the hole inside it are two separate rings. Ring depth (how many other rings
    contain it) decides which is which.
    """
    candidates = []
    for ring in rings:
        if len(ring) < 3:
            continue
        poly = Polygon(ring)
        if not poly.is_valid:
            poly = poly.buffer(0)
        if poly.is_empty or poly.area <= 1e-9:
            continue
        candidates.append(Polygon(ring))
    candidates.sort(key=lambda p: p.area, reverse=True)

    shells, holes = [], []
    for i, poly in enumerate(candidates):
        probe = poly.representative_point()
        depth = sum(1 for j, other in enumerate(candidates)
                    if j != i and other.area > poly.area and other.contains(probe))
        (holes if depth % 2 else shells).append(poly)

    built = []
    for shell in shells:
        own = [h.exterior.coords for h in holes if shell.contains(h.representative_point())]
        built.append(Polygon(shell.exterior.coords, own).buffer(0))
    return unary_union(built) if built else Polygon()


def _glyph_clusters(geom):
    """Split a rendered string into per-glyph groups by x-overlap.

    Lets us apply letter tracking after the fact: matplotlib gives correct
    kerning for the whole string, and we just spread the clusters apart.
    """
    parts = list(geom.geoms) if isinstance(geom, MultiPolygon) else [geom]
    spans = sorted(((p.bounds[0], p.bounds[2], p) for p in parts), key=lambda s: s[0])

    clusters = []
    for lo, hi, poly in spans:
        if clusters and lo <= clusters[-1][1] + 1e-9:
            clusters[-1][1] = max(clusters[-1][1], hi)
            clusters[-1][2].append(poly)
        else:
            clusters.append([lo, hi, [poly]])
    return clusters


def text_outline(text, font_path, cap_height, tracking=0.0):
    """Flat text as a polygon: baseline on y=0, centred on x=0, caps `cap_height` tall."""
    from shapely.affinity import scale as shp_scale, translate

    path = TextPath((0, 0), text, size=100.0,
                    prop=FontProperties(fname=font_path))
    geom = _rings_to_polygon(path.to_polygons(closed_only=False))
    if geom.is_empty:
        raise ValueError(f"font produced no outline for {text!r}")

    if tracking:
        shifted = []
        for i, (_, _, polys) in enumerate(_glyph_clusters(geom)):
            for poly in polys:
                shifted.append(translate(poly, xoff=i * tracking * 100.0 / cap_height))
        geom = unary_union(shifted)

    minx, miny, maxx, maxy = geom.bounds
    factor = cap_height / (maxy - miny)
    geom = shp_scale(geom, xfact=factor, yfact=factor, origin=(0, 0))

    minx, miny, maxx, maxy = geom.bounds
    return translate(geom, xoff=-(minx + maxx) / 2.0, yoff=-miny)


def arc_text(text, font_path, cap_height, radius, on_top=True,
             tracking=0.0, max_segment=0.25):
    """Bend text around a circle centred on the origin.

    `radius` is the baseline radius. Top text grows outward from the baseline
    and reads left-to-right over the top; bottom text grows inward and reads
    left-to-right along the bottom, matching how a badge or coaster is set.
    """
    flat = text_outline(text, font_path, cap_height, tracking)
    parts = list(flat.geoms) if isinstance(flat, MultiPolygon) else [flat]

    warped = []
    for poly in parts:
        rings = [poly.exterior.coords] + [r.coords for r in poly.interiors]
        bent = []
        for ring in rings:
            pts = resample(ring, max_segment)
            x, y = pts[:, 0], pts[:, 1]
            if on_top:
                theta = np.pi / 2.0 - x / radius
                r = radius + y
            else:
                theta = -np.pi / 2.0 + x / radius
                r = radius - y
            bent.append(np.column_stack([r * np.cos(theta), r * np.sin(theta)]))
        warped.append(Polygon(bent[0], bent[1:]).buffer(0))
    return unary_union(warped)


def resolve_font(name_or_path):
    """Accept either a literal .ttf path or a family name to look up."""
    if str(name_or_path).lower().endswith((".ttf", ".otf")):
        return str(name_or_path)
    return findfont(FontProperties(family=name_or_path, weight="bold"))


# --------------------------------------------------------------------------
# 2D -> 3D
# --------------------------------------------------------------------------


def disc(radius, segments=256):
    return Point(0, 0).buffer(radius, quad_segs=max(4, segments // 4))


def ring(outer, width, segments=256):
    return disc(outer, segments).difference(disc(outer - width, segments))


# Unioning curves that meet at a shallow angle -- the horns into the skull --
# leaves vertices a few nanometres apart. Shapely calls the result valid, but
# the triangulator quietly produces a hole there, which then fails every
# downstream boolean. Snapping to a grid far below print resolution merges those
# points; the coarser simplifications are fallbacks for stubborn cases.
_EXTRUDE_REPAIRS = (
    ("as drawn", lambda p: p),
    ("snapped to 1e-4 mm", lambda p: shapely.set_precision(p, 1e-4)),
    ("simplified 1e-4 mm", lambda p: p.simplify(1e-4)),
    ("simplified 1e-3 mm", lambda p: p.simplify(1e-3)),
)


def _extrude_solid(part, height):
    """Extrude one polygon, repairing it until the result is a closed solid."""
    for _, repair in _EXTRUDE_REPAIRS:
        try:
            cleaned = repair(part)
            if cleaned.is_empty or cleaned.geom_type != "Polygon" or cleaned.area <= 0:
                continue
            mesh = trimesh.creation.extrude_polygon(cleaned, height=height)
        except Exception:
            continue
        if mesh.is_watertight and mesh.volume > 0:
            return mesh
    raise ValueError(
        f"could not extrude a closed solid from a polygon of area {part.area:.3f} "
        f"mm2 -- it is probably self-intersecting or has a zero-width sliver")


def prism(polygon, z0, z1):
    """Extrude a shapely polygon (or MultiPolygon) between two z heights.

    The artwork is a MultiPolygon -- border ring, each letter and the longhorn
    are separate islands -- so each piece is extruded on its own and the
    results are concatenated into one multi-body mesh.
    """
    meshes = []
    for part in getattr(polygon, "geoms", [polygon]):
        if part.is_empty or part.area <= 0:
            continue
        mesh = _extrude_solid(part, float(z1 - z0))
        mesh.apply_translation([0, 0, float(z0)])
        meshes.append(mesh)
    if not meshes:
        raise ValueError("nothing to extrude")
    return meshes[0] if len(meshes) == 1 else trimesh.util.concatenate(meshes)


def revolve(profile, segments=256):
    """Revolve a closed (r, z) profile around the z axis into a solid.

    Used for the parts that are lathe-like -- the tapered cutter blade with its
    grip flange, the stamp handle, and the chamfer cut on the stamp plate.
    Profile points may sit on the axis (r=0).
    """
    prof = np.asarray(profile, float)
    n_prof = len(prof)
    ang = np.linspace(0.0, 2.0 * np.pi, segments, endpoint=False)

    r = np.repeat(prof[None, :, 0], segments, axis=0)
    z = np.repeat(prof[None, :, 1], segments, axis=0)
    verts = np.stack([r * np.cos(ang)[:, None],
                      r * np.sin(ang)[:, None],
                      z], axis=-1).reshape(-1, 3)

    i = np.arange(segments)[:, None]
    j = (i + 1) % segments
    k = np.arange(n_prof)[None, :]
    k2 = (k + 1) % n_prof
    a = (i * n_prof + k).ravel()
    b = (i * n_prof + k2).ravel()
    c = (j * n_prof + k2).ravel()
    d = (j * n_prof + k).ravel()
    faces = np.vstack([np.column_stack([a, b, c]), np.column_stack([a, c, d])])

    mesh = trimesh.Trimesh(vertices=verts, faces=faces, process=True)
    # Profile points sitting on the axis collapse to a single vertex, leaving a
    # fan of zero-area triangles behind. Drop them or the solid reads as broken.
    mesh.update_faces(mesh.nondegenerate_faces())
    mesh.remove_unreferenced_vertices()
    mesh.merge_vertices()
    mesh.fix_normals()
    return mesh


def union(meshes):
    """Boolean-union a list of meshes into one watertight solid."""
    meshes = [m for m in meshes if m is not None and len(m.faces)]
    if len(meshes) == 1:
        return meshes[0]
    return trimesh.boolean.union(meshes, engine="manifold")


def difference(meshes):
    return trimesh.boolean.difference(meshes, engine="manifold")
