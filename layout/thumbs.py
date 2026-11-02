# SPDX-License-Identifier: GPL-3.0-or-later
"""25° thumb cluster (spec §5), right frame.

Centres are the original ErgoDox PCB switch positions. The grid formula
thumb_pt(u, v) reproduces them to 3 µm and is kept as the cross-check and for
anything placed in thumb-grid units (case legs, stabilisers).
"""
from __future__ import annotations

import math

from .keys import PITCH, Key, local_axes

THUMB_ANGLE = 25.0
THUMB_O = (34.69894, 143.2687)          # T0 centre
FORMULA_TOL = 0.003                     # formula vs original PCB (mm)
STAB_OFFSET = 11.938                    # MX 2u stabiliser NPTHs, along the long axis
STAB_HOLES = (3.05, 4.0)                # wire / housing NPTH diameters

U, V = local_axes(THUMB_ANGLE)          # along thumb rows / columns


def thumb_pt(u: float, v: float) -> tuple[float, float]:
    return (THUMB_O[0] + PITCH * (u * U[0] + v * V[0]),
            THUMB_O[1] + PITCH * (u * U[1] + v * V[1]))


# id, (u, v), (x, y) from the original PCB, w, h, row, col, left legend, right legend
_THUMBS = [
    ("T0", (0, 0), (34.69894, 143.2687), 1, 1, 5, 6, "LGUI", "LALT"),
    ("T1", (1, 0), (51.96332, 135.21944), 1, 1, 5, 5, "ALT_T(APP)", "CTL_T(ESC)"),
    ("T2", (0, 1), (42.7482, 160.53308), 1, 1, 5, 4, "HOME", "PGUP"),
    ("T3", (0, 2), (50.8, 177.8), 1, 1, 5, 3, "END", "PGDN"),
    ("T4", (1, 1.5), (64.03848, 161.11728), 1, 2, 5, 2, "BSPC", "TAB"),
    ("T5", (2, 1.5), (81.30286, 153.06548), 1, 2, 5, 1, "SPC", "ENT"),
]

THUMB_GRID = {i: uv for i, uv, *_ in _THUMBS}
THUMB_KEYS = [Key(i, x, y, THUMB_ANGLE, w, h, r, c, ll, lr)
              for i, _, (x, y), w, h, r, c, ll, lr in _THUMBS]
for _k in THUMB_KEYS:
    _fx, _fy = thumb_pt(*THUMB_GRID[_k.id])
    assert math.hypot(_fx - _k.x, _fy - _k.y) < FORMULA_TOL, _k.id


def stab_holes(k: Key) -> list[tuple[float, float]]:
    """2u stabiliser centres (±STAB_OFFSET along the key's long axis)."""
    _, vy = local_axes(k.rot)
    return [(k.x + s * STAB_OFFSET * vy[0], k.y + s * STAB_OFFSET * vy[1]) for s in (-1, 1)]


def stab_dir(k: Key, side: str) -> tuple[float, float]:
    """Unit vector across a 2u key towards its stabiliser housings: the Ø4.0 NPTHs on the PCB and
    the long half of the plate cut-out (Cherry: holes at +8.255, cut-out -5.53..+6.77). The PCB and
    the case both orient their stabiliser from it. -U on the right half and its mirror image (+U
    of the mirrored key frame) on the left, so the halves stay mirror-equal."""
    ux, uy = local_axes(k.rot)[0]
    s = -1.0 if side == "right" else 1.0
    return (s * ux + 0.0, s * uy + 0.0)
