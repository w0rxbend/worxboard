# SPDX-License-Identifier: GPL-3.0-or-later
"""Switch positions, matrix wiring and legends (spec §5), right frame.

Main-block centres come from the original ErgoDox PCB (Fredrik Atmer, GPLv3,
github.com/bishboria/ErgoDox). The inner-top key C6R0 is replaced by the display.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from shapely.affinity import rotate, translate
from shapely.geometry import Polygon, box

PITCH = 19.05            # 1u key cell
HOUSING = 15.6           # MX lower housing incl. clips (no overlap allowed)
MATRIX_COLS = 7          # per half; global map is 6 x 14
OUTER_1U5_X = 186.69 + 4.7625   # outer 1.5u column centre


@dataclass(frozen=True)
class Key:
    id: str              # physical C<col>R<row> (thumbs T0..T5)
    x: float
    y: float
    rot: float           # deg, CCW on screen
    w: float             # cap size in key units, along the key's own axes
    h: float
    row: int             # ROWn net
    col: int             # COLn net == physical column (C0 outer, C6 inner)
    legend_left: str
    legend_right: str

    def rc(self, side: str) -> tuple[int, int]:
        """Global ZMK (row, col) in the 6 x 14 transform."""
        return (self.row, self.col if side == "left" else 2 * MATRIX_COLS - 1 - self.col)


# id, x, y, w, h, row, col, left legend, right legend (rot 0)
_MAIN = [
    ("C0R0", OUTER_1U5_X, 67.0052, 1.5, 1, 0, 0, "=", "-"),
    ("C1R0", 167.64, 67.0052, 1, 1, 0, 1, "1", "0"),
    ("C2R0", 148.59, 63.82766, 1, 1, 0, 2, "2", "9"),
    ("C3R0", 129.54, 62.23, 1, 1, 0, 3, "3", "8"),
    ("C4R0", 110.49, 63.82766, 1, 1, 0, 4, "4", "7"),
    ("C5R0", 91.44, 65.1002, 1, 1, 0, 5, "5", "6"),
    ("C0R1", OUTER_1U5_X, 86.05266, 1.5, 1, 1, 0, "DEL", "\\"),
    ("C1R1", 167.64, 86.05266, 1, 1, 1, 1, "Q", "P"),
    ("C2R1", 148.59, 82.87766, 1, 1, 1, 2, "W", "O"),
    ("C3R1", 129.54, 81.28, 1, 1, 1, 3, "E", "I"),
    ("C4R1", 110.49, 82.87766, 1, 1, 1, 4, "R", "U"),
    ("C5R1", 91.44, 84.14766, 1, 1, 1, 5, "T", "Y"),
    ("C6R1", 72.39, 88.91016, 1, 1.5, 1, 6, "TG(1)", "TG(1)"),
    ("C0R2", OUTER_1U5_X, 105.10266, 1.5, 1, 2, 0, "BSPC", "GUI_T(')"),
    ("C1R2", 167.64, 105.10266, 1, 1, 2, 1, "A", "LT(2,;)"),
    ("C2R2", 148.59, 101.92766, 1, 1, 2, 2, "S", "L"),
    ("C3R2", 129.54, 100.33, 1, 1, 2, 3, "D", "K"),
    ("C4R2", 110.49, 101.92766, 1, 1, 2, 4, "F", "J"),
    ("C5R2", 91.44, 103.19766, 1, 1, 2, 5, "G", "H"),
    ("C0R3", OUTER_1U5_X, 124.15266, 1.5, 1, 3, 0, "LSFT", "RSFT"),
    ("C1R3", 167.64, 124.15266, 1, 1, 3, 1, "CTL_T(Z)", "CTL_T(/)"),
    ("C2R3", 148.59, 120.97766, 1, 1, 3, 2, "X", "."),
    ("C3R3", 129.54, 119.38, 1, 1, 3, 3, "C", ","),
    ("C4R3", 110.49, 120.97766, 1, 1, 3, 4, "V", "M"),
    ("C5R3", 91.44, 122.24766, 1, 1, 3, 5, "B", "N"),
    ("C6R2", 72.39, 117.48516, 1, 1.5, 3, 6, "HYPER", "MEH"),
    ("C0R4", 186.69, 143.20266, 1, 1, 4, 0, "LT(1,`)", "TT(1)"),
    ("C1R4", 167.64, 143.20266, 1, 1, 4, 1, "'", "]"),
    ("C2R4", 148.59, 140.02766, 1, 1, 4, 2, "LA(LSFT)", "["),
    ("C3R4", 129.54, 138.43, 1, 1, 4, 3, "LEFT", "DOWN"),
    ("C4R4", 110.49, 140.02766, 1, 1, 4, 4, "RGHT", "UP"),
]

# The deleted key: its cell bounds the display (spec §4)
C6R0_CENTRE = (72.39, 65.1002)

MAIN_KEYS = [Key(i, x, y, 0.0, w, h, r, c, ll, lr) for i, x, y, w, h, r, c, ll, lr in _MAIN]


def _rect(x: float, y: float, sx: float, sy: float, rot: float, grow: float = 0.0) -> Polygon:
    """Rectangle centred at (x, y), rotated CCW on screen (y points down)."""
    b = box(-sx / 2 - grow, -sy / 2 - grow, sx / 2 + grow, sy / 2 + grow)
    return translate(rotate(b, -rot, origin=(0, 0)), x, y)


def cell(k: Key, grow: float = 0.0) -> Polygon:
    """Key-cap cell (w x h units), optionally grown."""
    return _rect(k.x, k.y, k.w * PITCH, k.h * PITCH, k.rot, grow)


def housing(k: Key, grow: float = 0.0) -> Polygon:
    """Switch housing square (spacer/plate keepout)."""
    return _rect(k.x, k.y, HOUSING, HOUSING, k.rot, grow)


def local_axes(rot: float) -> tuple[tuple[float, float], tuple[float, float]]:
    """Unit vectors of a key's own x (width) and y (height) axes in the KiCad frame."""
    a = math.radians(rot)
    return (math.cos(a), -math.sin(a)), (math.sin(a), math.cos(a))
