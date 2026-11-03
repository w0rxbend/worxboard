# SPDX-License-Identifier: GPL-3.0-or-later
"""Edge connectors (spec §6), right frame. Both are F.Cu SMD parts assembled by JLC."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Jack:
    ref: str
    footprint: str
    x: float               # mouth centre on the PCB edge
    y: float
    facing: tuple[float, float]   # outward unit vector of the mouth
    body: tuple[float, float, float, float]   # x0, y0, x1, y1 on the PCB
    axis_z: float          # plug axis height above the PCB top
    height: float          # body height above the PCB top


BACK_EDGE_Y = 30.6
INNER_BUMP_X = 49.0

# USB-C HRO TYPE-C-31-M-12: 8.94 x 7.35 shell, mouth flush with the back edge
USB_X = 186.0
USB_BODY = (8.94, 7.35)
USB_HEIGHT = 3.2
J1 = Jack("J1", "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
          USB_X, BACK_EDGE_Y, (0.0, -1.0),
          (USB_X - USB_BODY[0] / 2, BACK_EDGE_Y, USB_X + USB_BODY[0] / 2, BACK_EDGE_Y + USB_BODY[1]),
          USB_HEIGHT / 2, USB_HEIGHT)

# TRRS PJ-320D-4A (HRO drawing, LCSC C95562; gate G2): body along x, mouth at the inner-bump edge.
# 2.00 barrel + 12.10 body = 14.10 long, 6.10 wide, 5.00 tall, plug axis centred 2.50 above the PCB.
# The body runs 0.9 mm past Z_TRRS (x 62.2) under the plate between C6R1 and C6R2; the case relieves
# it there (case/worxboard_case.py jack_relief_poly, deviations BOARD-13).
TRRS_Y = 103.0
TRRS_BODY = (14.1, 6.1)
TRRS_AXIS_Z = 2.5
TRRS_HEIGHT = 5.0
J2 = Jack("J2", "Connector_Audio:Jack_3.5mm_PJ320D_Horizontal",
          INNER_BUMP_X, TRRS_Y, (-1.0, 0.0),
          (INNER_BUMP_X, TRRS_Y - TRRS_BODY[1] / 2, INNER_BUMP_X + TRRS_BODY[0], TRRS_Y + TRRS_BODY[1] / 2),
          TRRS_AXIS_Z, TRRS_HEIGHT)

JACKS = (J1, J2)
