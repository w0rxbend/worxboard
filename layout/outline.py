# SPDX-License-Identifier: GPL-3.0-or-later
"""PCB Edge.Cuts outline (spec §8.1), right frame.

Derived from the original ErgoDox Edge.Cuts: jack tabs removed, back edge straight,
inner edge on the case clearance line, plus the local TRRS bump.
"""
from __future__ import annotations

import math

from shapely.geometry import Polygon

ARC_SEGMENTS = 16        # per fillet, for the polygon approximation

# (x, y, fillet radius) in drawing order
VERTICES = [
    (62.275, 30.6, 0), (202.7428, 30.6, 0), (205.9178, 33.775, 0), (205.9178, 143.383, 0),
    (196.3928, 152.908, 0), (127.1524, 152.908, 0), (48.9839, 189.35192, 0),
    (44.76496, 187.81776, 0), (23.08098, 141.31544, 0), (24.61768, 137.0965, 0),
    (49.0, 125.7267, 0),                 # original 25° thumb top edge, extended to the bump
    (49.0, 88.0, 4.0), (59.1, 88.0, 4.0),  # TRRS bump
    (59.1, 33.775, 0),
]


def _fillet(p0, p1, p2, r: float):
    """Tangent points and arc mid-point of a radius-r fillet at corner p1."""
    def unit(a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        n = math.hypot(dx, dy)
        return dx / n, dy / n
    u1, u2 = unit(p1, p0), unit(p1, p2)
    half = math.acos(max(-1.0, min(1.0, u1[0] * u2[0] + u1[1] * u2[1]))) / 2
    t = r / math.tan(half)               # corner -> tangent point
    a = (p1[0] + u1[0] * t, p1[1] + u1[1] * t)
    b = (p1[0] + u2[0] * t, p1[1] + u2[1] * t)
    bis = unit((0, 0), (u1[0] + u2[0], u1[1] + u2[1]))
    d = r / math.sin(half)               # corner -> arc centre
    c = (p1[0] + bis[0] * d, p1[1] + bis[1] * d)
    m = (c[0] - bis[0] * r, c[1] - bis[1] * r)
    return a, m, b, c


def segments(verts: list[tuple[float, float, float]]) -> list[dict]:
    """KiCad-ready primitives: lines and three-point arcs, closed loop."""
    n = len(verts)
    ends = []                            # (entry point, arc or None, exit point) per vertex
    for i, (x, y, r) in enumerate(verts):
        if r:
            a, m, b, c = _fillet(verts[i - 1][:2], (x, y), verts[(i + 1) % n][:2], r)
            ends.append((a, (a, m, b, c), b))
        else:
            ends.append(((x, y), None, (x, y)))
    out = []
    for i in range(n):
        _, arc, exit_pt = ends[i]
        if arc:
            out.append({"type": "arc", "start": arc[0], "mid": arc[1], "end": arc[2], "centre": arc[3]})
        out.append({"type": "line", "start": exit_pt, "end": ends[(i + 1) % n][0]})
    return out


def polygon(segs: list[dict]) -> Polygon:
    """Polygon with arcs approximated by ARC_SEGMENTS chords."""
    pts = []
    for s in segs:
        if s["type"] == "line":
            pts.append(s["start"])
            continue
        (cx, cy), (sx, sy), (ex, ey) = s["centre"], s["start"], s["end"]
        r = math.hypot(sx - cx, sy - cy)
        a0, a1 = math.atan2(sy - cy, sx - cx), math.atan2(ey - cy, ex - cx)
        sweep = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi   # fillets are < 180°
        pts += [(cx + r * math.cos(a0 + sweep * k / ARC_SEGMENTS),
                 cy + r * math.sin(a0 + sweep * k / ARC_SEGMENTS)) for k in range(ARC_SEGMENTS)]
    return Polygon(pts)
