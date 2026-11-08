# SPDX-License-Identifier: GPL-3.0-or-later
"""Per-key RGB (rev B): one reverse-mount SK6812MINI-E under every switch, right frame.

The switches face south: the MX LED window is 5.08 mm below the switch centre (+y in the key's own
frame, opposite the two switch pins). The LED sits there on B.Cu with its body through a PCB cutout,
its decoupling cap beside it, and the key's matrix diode moves below it.

CHAIN is the data order (LED101 = CHAIN[0]), the same key ids on both halves: a serpentine through
the rows so every hop is to a neighbour, then the thumbs from the one next to C4R4.
"""
from __future__ import annotations

import math

from .keys import local_axes

LED_OFFSET = (0.0, 5.08)         # LED centre in the key frame: the MX LED window
DIODE_OFFSET = (0.0, 8.5)        # matrix diode centre in the key frame, below the LED
LED_REF0 = 101                   # LED<n> / its cap C<n>, n = LED_REF0 + chain index

CHAIN = (
    "C0R0", "C1R0", "C2R0", "C3R0", "C4R0", "C5R0",              # row 0, inward
    "C6R1", "C5R1", "C4R1", "C3R1", "C2R1", "C1R1", "C0R1",      # row 1, outward
    "C0R2", "C1R2", "C2R2", "C3R2", "C4R2", "C5R2",              # row 2, inward
    "C6R2",                                                      # inner 1.5u (rows 2-3)
    "C5R3", "C4R3", "C3R3", "C2R3", "C1R3", "C0R3",              # row 3, outward
    "C0R4", "C1R4", "C2R4", "C3R4", "C4R4",                      # row 4, inward
    "T5", "T4", "T3", "T2", "T0", "T1",                          # thumbs
)


def key_point(k, off: tuple[float, float]) -> tuple[float, float]:
    """A point given in a key's own frame (x along the cap width, y along its height), KiCad frame."""
    ax, ay = local_axes(k.rot)
    return (k.x + off[0] * ax[0] + off[1] * ay[0], k.y + off[0] * ax[1] + off[1] * ay[1])


def leds(keys) -> list[dict]:
    """The chain in order: ref, key id, centre, and the unit vector to the next LED (None at the end)."""
    by_id = {k.id: k for k in keys}
    assert sorted(CHAIN) == sorted(by_id), "CHAIN must name every key once"
    pts = [key_point(by_id[i], LED_OFFSET) for i in CHAIN]
    out = []
    for n, (kid, p) in enumerate(zip(CHAIN, pts)):
        nxt = None
        if n + 1 < len(pts):
            dx, dy = pts[n + 1][0] - p[0], pts[n + 1][1] - p[1]
            d = math.hypot(dx, dy)
            nxt = (dx / d, dy / d)
        out.append({"ref": f"LED{LED_REF0 + n}", "cap": f"C{LED_REF0 + n}", "key": kid, "x": p[0], "y": p[1],
                    "rot": by_id[kid].rot, "next": nxt})
    return out


def diode(k) -> tuple[float, float]:
    return key_point(k, DIODE_OFFSET)
