# SPDX-License-Identifier: GPL-3.0-or-later
"""Scripted board checks after routing (spec §9 stage 12).

    python3 pcb/scripts/checks.py <side>     (reads pcb/<side>/*.kicad_pcb and build/<side>/drc.json)

- USB: each line's copper path from the U1 pin to the nearest J1 pin of its net (through
  R3/R4 and the U4 pass-through) is <= USB_MAX_MM, and D+ / D- differ by <= USB_SKEW_MM;
- Y1: its courtyard lies within Y1_MAX_MM of the U1 XIN / XOUT pads;
- Edge.Cuts: every outline vertex equals layout/build/layout.json within EDGE_TOL_MM;
- DRC: build/<side>/drc.json lists 0 unconnected items and no error-level violations.
"""
from __future__ import annotations

import heapq
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pcbnew  # noqa: E402
from shapely.geometry import Point, Polygon  # noqa: E402

from place import layout_side  # noqa: E402

USB_MAX_MM = 25.0
USB_SKEW_MM = 1.0
Y1_MAX_MM = 3.0
EDGE_TOL_MM = 0.01
SNAP = 1e-3                  # mm, track end-point identity
USB_LINES = {"D+": (("USB_DP", "USB_C_DP"), "47"), "D-": (("USB_DM", "USB_C_DM"), "46")}
XTAL_PINS = ("20", "21")   # RP2040 XIN, XOUT
SERIES = ("R3", "R4")        # series resistors: their two pads count as joined


def mm_xy(v) -> tuple[float, float]:
    return pcbnew.ToMM(v.x), pcbnew.ToMM(v.y)


def pad_poly(pad: pcbnew.PAD) -> Polygon:
    sps = pad.GetEffectivePolygon(pcbnew.F_Cu if pad.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu, pcbnew.ERROR_INSIDE)
    o = sps.Outline(0)
    return Polygon([mm_xy(o.CPoint(i)) for i in range(o.PointCount())])


def usb_paths(board: pcbnew.BOARD) -> dict[str, float]:
    """Shortest copper path U1 pin -> any J1 pin per USB line (tracks + series resistors)."""
    out = {}
    for name, (nets, u1_pin) in USB_LINES.items():
        codes = {board.FindNet(n).GetNetCode() for n in nets}
        graph: dict[object, list[tuple[object, float]]] = defaultdict(list)

        def node(p):
            return (round(p[0] / SNAP), round(p[1] / SNAP))

        def edge(a, b, w):
            graph[a].append((b, w))
            graph[b].append((a, w))
        ends = []
        for t in board.GetTracks():
            if t.GetNetCode() in codes and t.Type() == pcbnew.PCB_TRACE_T:
                a, b = mm_xy(t.GetStart()), mm_xy(t.GetEnd())
                edge(node(a), node(b), math.dist(a, b))
                ends += [a, b]
            elif t.GetNetCode() in codes and t.Type() == pcbnew.PCB_VIA_T:
                ends.append(mm_xy(t.GetPosition()))
        pads = {}
        for fp in board.GetFootprints():
            for pad in fp.Pads():
                if pad.GetNetCode() in codes:
                    key = (fp.GetReference(), pad.GetNumber(), pad.GetPosition().x, pad.GetPosition().y)
                    pads[key] = pad
                    poly = pad_poly(pad).buffer(SNAP)
                    for e in ends:                      # track ends inside the pad join it
                        if poly.contains(Point(e)):
                            edge(key, node(e), math.dist(e, mm_xy(pad.GetPosition())))
        for (ref, _, _, _), pad in list(pads.items()):
            if ref in SERIES:
                a, b = [k for k in pads if k[0] == ref]
                edge(a, b, math.dist(mm_xy(pads[a].GetPosition()), mm_xy(pads[b].GetPosition())))
                break
        starts = [k for k in pads if k[0] == "U1" and k[1] == u1_pin]
        goals = {k for k in pads if k[0] == "J1"}
        out[name] = dijkstra(graph, starts, goals)
    return out


def dijkstra(graph, starts, goals) -> float:
    dist = {s: 0.0 for s in starts}
    heap = [(0.0, i, s) for i, s in enumerate(starts)]
    n = len(heap)
    while heap:
        d, _, u = heapq.heappop(heap)
        if u in goals:
            return d
        if d > dist.get(u, math.inf):
            continue
        for v, w in graph[u]:
            if d + w < dist.get(v, math.inf):
                dist[v] = d + w
                n += 1
                heapq.heappush(heap, (d + w, n, v))
    return math.inf


def courtyard(fp: pcbnew.FOOTPRINT) -> Polygon:
    sps = fp.GetCourtyard(pcbnew.F_CrtYd)
    o = sps.Outline(0)
    return Polygon([mm_xy(o.CPoint(i)) for i in range(o.PointCount())])


def y1_distance(board: pcbnew.BOARD) -> float:
    u1, y1 = board.FindFootprintByReference("U1"), board.FindFootprintByReference("Y1")
    cy = courtyard(y1)
    pins = [p for p in u1.Pads() if p.GetNumber() in XTAL_PINS]
    if len(pins) != 2:
        raise SystemExit("U1 XIN/XOUT pads not found")
    return max(pad_poly(p).distance(cy) for p in pins)


def edge_vertices(board: pcbnew.BOARD) -> list[tuple[float, float]]:
    pts = []
    for d in board.GetDrawings():
        if d.GetLayer() != pcbnew.Edge_Cuts:
            continue
        pts += [mm_xy(d.GetStart()), mm_xy(d.GetEnd())]
        if d.GetShape() == pcbnew.SHAPE_T_ARC:
            pts.append(mm_xy(d.GetArcMid()))
    return pts


def check_edges(board: pcbnew.BOARD, side: str) -> list[str]:
    want = []
    for s in layout_side(side)["outline"]["segments"]:
        want += [tuple(s["start"]), tuple(s["end"])] + ([tuple(s["mid"])] if s["type"] == "arc" else [])
    have = edge_vertices(board)
    errs = []
    for label, a, b in (("layout vertex missing from Edge.Cuts", want, have),
                        ("Edge.Cuts vertex not in layout", have, want)):
        for p in a:
            d = min(math.dist(p, q) for q in b)
            if d > EDGE_TOL_MM:
                errs.append(f"{label}: ({p[0]:.4f}, {p[1]:.4f}) off by {d:.4f} mm")
    return errs


def check_drc(path: Path) -> list[str]:
    if not path.exists():
        return [f"{path} missing: run the DRC gate first"]
    d = json.loads(path.read_text())
    errs = [f"{len(d.get('unconnected_items', []))} unconnected items"] if d.get("unconnected_items") else []
    bad = [v for v in d.get("violations", []) if v["severity"] == "error"]
    bad += [v for v in d.get("schematic_parity", []) if v["severity"] == "error"]
    errs += [f"{len(bad)} DRC / parity errors ({', '.join(sorted({v['type'] for v in bad}))})"] if bad else []
    return errs


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in ("left", "right"):
        print(__doc__)
        return 2
    side = argv[1]
    board = pcbnew.LoadBoard(str(ROOT / "pcb" / side / f"worxboard-{side}.kicad_pcb"))
    results: list[tuple[str, list[str]]] = []
    usb = usb_paths(board)
    errs = [f"{n} path {v:.2f} mm > {USB_MAX_MM}" for n, v in usb.items() if v > USB_MAX_MM]
    skew = abs(usb["D+"] - usb["D-"])
    errs += [f"D+/D- differ by {skew:.2f} mm > {USB_SKEW_MM}"] if skew > USB_SKEW_MM else []
    results.append((f"USB pair: D+ {usb['D+']:.2f} mm, D- {usb['D-']:.2f} mm, skew {skew:.2f} mm", errs))
    y1 = y1_distance(board)
    results.append((f"Y1 courtyard {y1:.2f} mm from XIN/XOUT",
                    [f"{y1:.2f} mm > {Y1_MAX_MM}"] if y1 > Y1_MAX_MM else []))
    results.append(("Edge.Cuts equals layout", check_edges(board, side)))
    results.append(("DRC: 0 unconnected, 0 errors", check_drc(ROOT / "build" / side / "drc.json")))
    failed = 0
    for title, errs in results:
        print(f"{'FAIL' if errs else 'ok  '} {title}")
        for e in errs:
            print(f"       {e}")
        failed += bool(errs)
    print(f"checks {side}: {len(results) - failed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
