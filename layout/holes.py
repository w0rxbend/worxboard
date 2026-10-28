# SPDX-License-Identifier: GPL-3.0-or-later
"""M2.5 mounting holes (spec §8.2), right frame.

The original ErgoDox hole pattern (also the EZ bottom-screw pattern), with #7
moved off the display to the old TRRS spot on the back row.
"""
from __future__ import annotations

HOLE_D = 2.7             # NPTH
KEEPOUT_D = 6.5          # copper / component keepout == case boss
_O = (50.8, 177.8)       # original PCB datum (T3 centre)

ORIGINAL = [(_O[0] + dx, _O[1] + dy) for dx, dy in (
    (3.0988, -11.9634), (8.8646, -56.134), (54.6354, -20.0406),
    (150.9776, -37.7444), (88.2396, -86.2076), (150.3426, -140.6652),
    (67.4116, -140.6652), (16.6116, -140.6652))]

MOVED = {7: (88.0, ORIGINAL[7][1])}      # was (67.41, 37.13), under the display
HOLES = [MOVED.get(i, p) for i, p in enumerate(ORIGINAL)]
