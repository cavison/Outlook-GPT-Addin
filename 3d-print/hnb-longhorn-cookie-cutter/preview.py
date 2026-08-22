"""Preview renderers: flat artwork plots and shaded 3D views of the meshes."""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import PolyCollection
from matplotlib.patches import PathPatch
from matplotlib.path import Path


def _shapely_patch(polygon, **kw):
    verts, codes = [], []
    for part in getattr(polygon, "geoms", [polygon]):
        for ring in [part.exterior, *part.interiors]:
            pts = np.asarray(ring.coords)
            verts.extend(pts)
            codes.extend([Path.MOVETO] + [Path.LINETO] * (len(pts) - 1))
    return PathPatch(Path(verts, codes), **kw)


def plot_flat(panels, path, disc_radius=None, dpi=150):
    """Draw one or more flat artwork panels side by side."""
    fig, axes = plt.subplots(1, len(panels), figsize=(6.0 * len(panels), 6.4))
    axes = np.atleast_1d(axes)
    for ax, (title, art, colour) in zip(axes, panels):
        if disc_radius:
            ax.add_patch(plt.Circle((0, 0), disc_radius, facecolor="#e9e4da",
                                    edgecolor="#b9b0a1", lw=1.4, zorder=0))
        ax.add_patch(_shapely_patch(art, facecolor=colour, edgecolor="none", zorder=2))
        lim = (disc_radius or 50) * 1.06
        ax.set_xlim(-lim, lim)
        ax.set_ylim(-lim, lim)
        ax.set_aspect("equal")
        ax.set_title(title, fontsize=13, pad=12)
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(path, dpi=dpi, facecolor="white")
    plt.close(fig)


def render_mesh(meshes, path, elev=32.0, azim=-52.0, colours=None,
                size=(9, 7), dpi=150, title=None, highlight_above=None,
                engrave_above=None, highlight_colour="#d8b061",
                engrave_colour="#2b2723"):
    """Shaded isometric render using a painter's algorithm.

    Cheap stand-in for a real renderer: backface-cull, sort triangles by depth,
    shade by facet normal against a fixed light.
    """
    if not isinstance(meshes, (list, tuple)):
        meshes = [meshes]
    colours = colours or ["#5f7f9a"] * len(meshes)

    e, a = np.radians(elev), np.radians(azim)
    view = np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])
    right = np.cross(np.array([0.0, 0.0, 1.0]), view)
    right /= np.linalg.norm(right)
    up = np.cross(view, right)
    light = np.array([0.35, -0.55, 0.76])
    light /= np.linalg.norm(light)

    polys, facecolours, depths = [], [], []
    for mesh, base in zip(meshes, colours):
        tris = mesh.vertices[mesh.faces]
        normals = mesh.face_normals
        keep = normals @ view > 0.0
        tris, normals = tris[keep], normals[keep]

        shade = np.clip(normals @ light, 0.0, 1.0) * 0.72 + 0.28
        rgb = np.tile(matplotlib.colors.to_rgb(base), (len(tris), 1))
        if highlight_above is not None:
            # Raised artwork sits parallel to the plate it grows out of, so flat
            # shading alone renders them the same colour. Tint anything standing
            # proud of the plate to make the relief legible.
            raised = tris[:, :, 2].min(axis=1) > highlight_above
            rgb[raised] = matplotlib.colors.to_rgb(highlight_colour)
        if engrave_above is not None:
            # An engraved recess reads the same way: its floor is a
            # downward-facing surface parked above the face it is cut into.
            floor = (normals[:, 2] < 0) & (tris[:, :, 2].min(axis=1) > engrave_above)
            rgb[floor] = matplotlib.colors.to_rgb(engrave_colour)
        facecolours.append(np.clip(rgb * shade[:, None], 0, 1))

        polys.append(np.stack([tris @ right, tris @ up], axis=-1))
        depths.append(tris @ view)

    poly = np.concatenate(polys)
    facecolour = np.concatenate(facecolours)
    depth = np.concatenate(depths).mean(axis=1)
    order = np.argsort(depth)

    fig, ax = plt.subplots(figsize=size)
    ax.add_collection(PolyCollection(poly[order], facecolors=facecolour[order],
                                     edgecolors="none", antialiased=False))
    flat = poly.reshape(-1, 2)
    pad = 0.04 * float(np.ptp(flat[:, 0]) + np.ptp(flat[:, 1]))
    ax.set_xlim(flat[:, 0].min() - pad, flat[:, 0].max() + pad)
    ax.set_ylim(flat[:, 1].min() - pad, flat[:, 1].max() + pad)
    ax.set_aspect("equal")
    ax.axis("off")
    if title:
        ax.set_title(title, fontsize=13, pad=10)
    fig.tight_layout()
    fig.savefig(path, dpi=dpi, facecolor="white")
    plt.close(fig)
