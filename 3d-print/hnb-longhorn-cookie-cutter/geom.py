"""2D/3D geometry helpers.

Everything works in millimetres. 2D shapes are shapely geometries, 3D shapes
are trimesh meshes. The artwork itself lives in trace.py and design.py.
"""

from __future__ import annotations

import numpy as np
import shapely
import trimesh
from shapely.geometry import Point


# --------------------------------------------------------------------------
# 2D primitives
# --------------------------------------------------------------------------


def disc(radius, segments=256):
    return Point(0, 0).buffer(radius, quad_segs=max(4, segments // 4))


def ring(outer, width, segments=256):
    return disc(outer, segments).difference(disc(outer - width, segments))


# --------------------------------------------------------------------------
# 2D -> 3D
# --------------------------------------------------------------------------

# Traced artwork carries thousands of contour points, and neighbouring ones can
# land close enough together that the triangulator quietly leaves a hole -- a
# mesh shapely still calls valid, but that fails every downstream boolean.
# Snapping to a grid far below print resolution merges them; the coarser
# simplifications are fallbacks for stubborn cases.
_EXTRUDE_REPAIRS = (
    ("as drawn", lambda p: p),
    ("snapped to 1e-4 mm", lambda p: shapely.set_precision(p, 1e-4)),
    ("simplified 1e-4 mm", lambda p: p.simplify(1e-4)),
    ("simplified 1e-3 mm", lambda p: p.simplify(1e-3)),
    ("simplified 1e-2 mm", lambda p: p.simplify(1e-2)),
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

    Artwork arrives as a MultiPolygon -- the skull and each letter are separate
    islands -- so each piece is extruded on its own and concatenated into one
    multi-body mesh.
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

    Used for the lathe-like parts: the tapered cutter blade with its grip
    flange, and the chamfer cut on the stamp plate. Profile points may sit on
    the axis (r=0).
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
    # Profile points on the axis collapse to one vertex, leaving a fan of
    # zero-area triangles behind. Drop them or the solid reads as broken.
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
