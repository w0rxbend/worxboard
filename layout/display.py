# SPDX-License-Identifier: GPL-3.0-or-later
"""nice!view-class memory LCD in the old C6R0 slot (spec §4), right frame."""
from __future__ import annotations

from .keys import C6R0_CENTRE, PITCH

MODULE = (14.0, 36.0)                     # assumed module footprint w x h (gate G1)
MODULE_CX = C6R0_CENTRE[0]                # 72.39
MODULE_Y1 = C6R0_CENTRE[1] + PITCH / 2    # bottom edge on the old C6R0 cell boundary
MODULE_RECT = (MODULE_CX - MODULE[0] / 2, MODULE_Y1 - MODULE[1],
               MODULE_CX + MODULE[0] / 2, MODULE_Y1)   # x0, y0, x1, y1

HEADER = (72.39, 40.6)                    # J3 1x5 socket centre, pins along x
HEADER_PINS = 5
HEADER_PITCH = 2.54
HEADER_PIN_ORDER = ("MOSI", "SCK", "VCC", "GND", "CS")   # pin 1..5 (gate G1)
HEADER_COURTYARD = 3.3                    # socket courtyard across / beyond the end pins

WINDOW = (12.0, 26.0)                     # viewing window w x h (the spec's 26 x 12, long axis y)
WINDOW_CENTRE = (72.39, 60.0)             # moved from y 62.5, see docs/deviations.md (WS0)
WINDOW_R = 1.0
WINDOW_CHAMFER = 0.5

POCKET_GROW = 0.5                         # case pocket = module + 0.5 mm
Z_PCB_TOP = 8.6
Z_POCKET_TOP = 16.8                       # stack (socket + module + glass) <= 8.2 mm


def _rect(cx: float, cy: float, w: float, h: float) -> tuple[float, float, float, float]:
    return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


WINDOW_RECT = _rect(*WINDOW_CENTRE, *WINDOW)
POCKET_RECT = tuple(v + s * POCKET_GROW for v, s in zip(MODULE_RECT, (-1, -1, 1, 1)))


def header_pins() -> list[tuple[float, float]]:
    """J3 pin centres, pin 1 first at low x. Not mirrored: the module is the same part on both halves."""
    x0 = HEADER[0] - (HEADER_PINS - 1) / 2 * HEADER_PITCH
    return [(x0 + i * HEADER_PITCH, HEADER[1]) for i in range(HEADER_PINS)]
