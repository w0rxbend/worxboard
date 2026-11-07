# SPDX-License-Identifier: GPL-3.0-or-later
"""0.91" 128 x 32 SSD1306 I2C OLED module in the old C6R0 slot (spec §4), right frame.

The common AliExpress module: a 38 x 12 mm board, a 1 x 4 2.54 mm header at one short end and the
OLED glass over the rest. Sellers' drawings differ, so every number below is gate G1: check it on
the first module (docs/verification.md). The header order varies between sellers (GND-VCC-SCL-SDA or
VCC-GND-SCL-SDA); JP2/JP3 on the PCB pick which of J3 pins 1 and 2 is GND (docs/deviations.md DISP-1).
"""
from __future__ import annotations

from .keys import C6R0_CENTRE, PITCH

MODULE = (12.0, 38.0)                     # module footprint w x h (gate G1)
MODULE_CX = C6R0_CENTRE[0]                # 72.39
MODULE_Y1 = C6R0_CENTRE[1] + PITCH / 2    # front edge on the old C6R0 cell boundary, as before:
                                          # the 2 mm the OLED is longer than the nice!view go back
MODULE_RECT = (MODULE_CX - MODULE[0] / 2, MODULE_Y1 - MODULE[1],
               MODULE_CX + MODULE[0] / 2, MODULE_Y1)   # x0, y0, x1, y1

# The header row is 1.3 mm in from the module's header-end edge, its four pins centred across the
# 12 mm width. The module's header end is its back (low-y) edge, as the nice!view's was
VIEW_EDGE = 1.3                           # header row -> module header-end edge (gate G1)
HEADER = (MODULE_CX, round(MODULE_RECT[1] + VIEW_EDGE, 3))   # J3 1x4 socket centre (72.39, 37.925)
HEADER_PINS = 4
HEADER_PITCH = 2.54
HEADER_PIN_ORDER = ("GND", "VCC", "SCL", "SDA")   # module pin 1..4 as JP2/JP3 ship (bridged 1-2)
HEADER_COURTYARD = 3.3                    # socket courtyard across / beyond the end pins

# The active area (22.38 x 5.58) lies on a 30 mm glass. Drawings put the glass centre about 20 mm from
# the header-end edge but do not agree within +-2 mm, so the window is 28 x 8: it shows the active
# area anywhere within 2.8 mm (along) and 1.2 mm (across) of that centre (gate G1)
VIEW_CENTRE = 20.0                        # module header-end edge -> active-area centre (nominal)
VIEW_LEN = 22.38                          # active area along the module
VIEW_W = 5.58                             # active area across the module
WINDOW = (8.0, 28.0)                      # viewing window w x h (long axis y)
WINDOW_CENTRE = (72.39, round(MODULE_RECT[1] + VIEW_CENTRE, 3))   # y 56.625
WINDOW_R = 1.0
WINDOW_CHAMFER = 0.5

POCKET_GROW = 0.5                         # case pocket = module + 0.5 mm
Z_PCB_TOP = 8.6
# 5.0 mm J3 socket + the module's 2.5 mm header plastic + 2.7 mm module (board and glass), nominal
STACK_NOMINAL = 10.2
Z_POCKET_TOP = round(Z_PCB_TOP + STACK_NOMINAL, 3)


def _rect(cx: float, cy: float, w: float, h: float) -> tuple[float, float, float, float]:
    return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


WINDOW_RECT = _rect(*WINDOW_CENTRE, *WINDOW)
POCKET_RECT = tuple(v + s * POCKET_GROW for v, s in zip(MODULE_RECT, (-1, -1, 1, 1)))


def header_pins() -> list[tuple[float, float]]:
    """J3 pin centres in pin order, pin 1 (GND by default) first at HIGH x (gate G1).

    Seen glass up with its header on the left, the module's pins read GND, VCC, SCL, SDA from the
    top. On the board the module lies glass up with its header at the back (low y): that view turned
    a quarter clockwise, so pin 1 is at high x. Not mirrored: the module is the same part on both
    halves."""
    x0 = HEADER[0] + (HEADER_PINS - 1) / 2 * HEADER_PITCH
    return [(x0 - i * HEADER_PITCH, HEADER[1]) for i in range(HEADER_PINS)]
