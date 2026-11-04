# SPDX-License-Identifier: GPL-3.0-or-later
"""KiKit tabs plugin for the JLC assembly panel (pcb/scripts/panel.json, run by stage_p.sh).

The panel is one board in a tight frame: a solid 6 mm-rail frame whose inside is milled out only
along a 2 mm slot round the board, so the board is held all the way round and nothing cantilevers
in reflow. A tab bridges the slot, square to a straight stretch of the board edge, and breaks off at
a line of mouse-bite holes on that edge (panel.json: Ø0.6 mm holes 1 mm apart, a third of each hole
in the board, as JLC's mouse-bite guide asks). Tabs go only where:
  - the board edge is straight for the tab width plus EDGE_MARGIN either side (a clean break line);
  - the tab, grown by KEEPOUT, meets no footprint courtyard and no pad on either side. That keeps
    them out of the USB-C (J1) and TRRS (J2) mouths, which overhang the edge, off the hot-swap
    sockets and parts near the edge, and keeps the mouse-bite holes clear of their copper;
  - the edge faces the frame (nothing of the board between it and the frame).
Along each valid stretch the tabs are TAB_PITCH apart, centred. The result depends only on the board.
"""
from __future__ import annotations

import math

import pcbnew
from kikit.annotations import TabAnnotation
from kikit.common import fromMm, toMm
from kikit.plugin import TabsPlugin
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

TAB_WIDTH = 5.0       # mm: 6 mouse-bite holes of 0.6 mm, 1 mm apart (JLC: 5-8 per tab)
TAB_PITCH = 45.0      # mm between tab centres along a stretch (JLC: a set every 50-60 mm)
EDGE_MARGIN = 1.0     # mm of straight edge beyond each side of a tab
KEEPOUT = 1.5         # mm from a tab to any courtyard or pad
STEP = 0.5            # mm sampling along an edge
STRAIGHT_DEG = 0.5    # segments within this angle are one straight edge


def keepouts(board: pcbnew.BOARD):
    shapes = []
    for fp in board.GetFootprints():
        if fp.GetReference().startswith("KiKit_"):
            continue
        for layer in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
            ps = fp.GetCourtyard(layer)
            for i in range(ps.OutlineCount()):
                o = ps.Outline(i)
                pts = [(o.CPoint(n).x, o.CPoint(n).y) for n in range(o.PointCount())]
                if len(pts) >= 3:
                    shapes.append(Polygon(pts).buffer(0))
        for pad in fp.Pads():
            bb = pad.GetBoundingBox()
            shapes.append(Point(pad.GetPosition().x, pad.GetPosition().y).buffer(
                max(bb.GetWidth(), bb.GetHeight()) / 2, 8))
    return unary_union(shapes)


def straight_edges(ring) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """Exterior ring -> maximal straight stretches (consecutive segments within STRAIGHT_DEG)."""
    pts = list(ring.coords)[:-1]
    segs = [(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]
    segs = [s for s in segs if math.dist(*s) > 1]

    def ang(s):
        return math.atan2(s[1][1] - s[0][1], s[1][0] - s[0][0])
    out = []
    for s in segs:
        if out and abs((ang(s) - ang(out[-1]) + math.pi) % (2 * math.pi) - math.pi) < math.radians(STRAIGHT_DEG) \
                and math.dist(out[-1][1], s[0]) < 1:
            out[-1] = (out[-1][0], s[1])
        else:
            out.append(s)
    if len(out) > 1 and abs((ang(out[0]) - ang(out[-1]) + math.pi) % (2 * math.pi) - math.pi) \
            < math.radians(STRAIGHT_DEG) and math.dist(out[-1][1], out[0][0]) < 1:
        out[0] = (out[-1][0], out[0][1])
        out.pop()
    return out


class FrameTabs(TabsPlugin):
    def buildTabAnnotations(self, panel) -> None:
        sub = panel.substrates[0]
        board = sub.substrates
        geom = board if board.geom_type == "Polygon" else max(board.geoms, key=lambda g: g.area)
        gap = max(self.preset["framing"]["hspace"], self.preset["framing"]["vspace"])
        width, margin, step = fromMm(TAB_WIDTH), fromMm(EDGE_MARGIN), fromMm(STEP)
        keep = keepouts(panel.board).buffer(fromMm(KEEPOUT))
        far = fromMm(1000)
        for a, b in sorted(straight_edges(geom.exterior), key=lambda s: (round(s[0][0]), round(s[0][1]))):
            length = math.dist(a, b)
            if length < width + 2 * margin:
                continue
            ux, uy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
            nx, ny = uy, -ux                                   # one normal; flip it to point outside
            mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            if geom.contains(Point(mid[0] + nx * fromMm(0.1), mid[1] + ny * fromMm(0.1))):
                nx, ny = -nx, -ny
            ok = []
            t = width / 2 + margin
            while t <= length - width / 2 - margin:
                p = (a[0] + ux * t, a[1] + uy * t)
                ok.append((t, self._valid(geom, keep, p, (ux, uy), (nx, ny), width, gap, far)))
                t += step
            for lo, hi in self._runs(ok):
                n = max(1, round(toMm(hi - lo) / TAB_PITCH))
                for i in range(n):
                    t = lo + (hi - lo) * (i + 0.5) / n
                    p = (a[0] + ux * t, a[1] + uy * t)
                    origin = (p[0] + nx * (gap / 2), p[1] + ny * (gap / 2))
                    sub.annotations.append(TabAnnotation(None, origin, (-nx, -ny), width))

    @staticmethod
    def _valid(geom, keep, p, u, n, width, gap, far) -> bool:
        half = (u[0] * width / 2, u[1] * width / 2)
        reach = gap + fromMm(0.5)
        strip = Polygon([(p[0] - half[0], p[1] - half[1]), (p[0] + half[0], p[1] + half[1]),
                         (p[0] + half[0] + n[0] * reach, p[1] + half[1] + n[1] * reach),
                         (p[0] - half[0] + n[0] * reach, p[1] - half[1] + n[1] * reach)])
        if strip.intersects(keep):
            return False
        start = (p[0] + n[0] * fromMm(0.05), p[1] + n[1] * fromMm(0.05))
        ray = LineString([start, (start[0] + n[0] * far, start[1] + n[1] * far)])
        return not ray.intersects(geom)

    @staticmethod
    def _runs(ok):
        runs, start, prev = [], None, None
        for t, v in ok:
            if v and start is None:
                start = t
            if not v and start is not None:
                runs.append((start, prev))
                start = None
            prev = t
        if start is not None:
            runs.append((start, prev))
        return runs
