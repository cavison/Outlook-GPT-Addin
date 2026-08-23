"""Emboss-style dimensions, kept separate so the round set stays reproducible."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EmbossConfig:
    diameter: float = 90.0
    wall_base: float = 1.6
    stamp_clearance: float = 0.35
    plate_thickness: float = 6.0
    relief_height: float = 1.8
    logo_depth: float = 1.0
    art_margin: float = 2.5

    @property
    def stamp_r(self):
        return self.diameter / 2.0 - self.wall_base - self.stamp_clearance

    @property
    def stamp_art_limit_r(self):
        return self.stamp_r - self.art_margin
