# SPDX-License-Identifier: GPL-3.0-or-later
"""Top-side component zones and part anchors (spec §8.3), right frame.

Every other top-side area is under the plate spacer and takes only switch holes.
"""
from __future__ import annotations

PART_ANCHORS = {         # ref: (x, y) centre
    "U1": (166.0, 44.0),     # RP2040
    "U2": (152.0, 42.0),     # W25Q128 flash
    "SW_BOOT": (176.0, 50.0),
    "SW_RST": (180.0, 50.0),
}
PART_BODIES = {          # ref: courtyard-ish w x h, for the zone checks
    "U1": (7.0, 7.0),
    "U2": (8.0, 5.3),        # SOIC-8 incl. pins
    "SW_BOOT": (3.0, 4.0),   # TS-1088 incl. pads
    "SW_RST": (3.0, 4.0),
}
Y1_MAX_FROM_U1 = 3.0

CELL_GROW = 0.6          # keepout around every key cell
BACK_Y = 57.0            # Z_BACK: y < BACK_Y
TRRS_X = 62.2            # Z_TRRS: x < TRRS_X, TRRS_Y0 <= y <= TRRS_Y1
TRRS_Y0, TRRS_Y1 = 88.0, 125.7
