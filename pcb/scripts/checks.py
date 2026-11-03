# SPDX-License-Identifier: GPL-3.0-or-later
"""Scripted board checks after routing (spec §9 stage 12).

    python3 pcb/scripts/checks.py <side>     (reads pcb/<side>/*.kicad_pcb and build/<side>/drc.json)

- USB: each line's copper path from the U1 pin to the nearest J1 pin of its net (through
  R3/R4 and the U4 pass-through) is <= USB_MAX_MM, and D+ / D- differ by <= USB_SKEW_MM;
- Y1: its courtyard lies within Y1_MAX_MM of the U1 XIN / XOUT pads, and no B.Cu track or via
  runs under it (its keepout);
- decoupling (spec §6.4): every RP2040 supply pin reaches a cap of its net within PIN_CAP_MAX_MM
  of copper, every supply cap (C8-C19) reaches a U1 supply pin within CAP_PIN_MAX_MM, and each
  cap's GND pad has a via within CAP_GND_VIA_MM;
- U4's VSYS clamp reference (pin 5) reaches a VSYS cap within U4_CAP_MAX_MM of copper;
- U1 GND: every thermal via of U1's exposed pad, and the GND via of each cap route_critical joins to
  it (GND_LINKED_CAPS), lies in the main B.Cu GND plane (the largest filled B.Cu GND area), joined to
  it over B.Cu alone; the other U1 caps' GND vias are listed (deviations BOARD-9);
- no via overlaps an SMD pad (the U1 exposed pad's thermal vias excepted);
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

import complete_routes  # noqa: E402
from complete_routes import vias_in_pads  # noqa: E402
from place import layout_side  # noqa: E402
from route_critical import GND_LINKED_CAPS  # noqa: E402

USB_MAX_MM = 25.0
USB_SKEW_MM = 1.0
Y1_MAX_MM = 3.0
EDGE_TOL_MM = 0.01
SNAP = 1e-3                  # mm, track end-point identity
USB_LINES = {"D+": (("USB_DP", "USB_C_DP"), "47"), "D-": (("USB_DM", "USB_C_DM"), "46")}
XTAL_PINS = ("20", "21")   # RP2040 XIN, XOUT
SERIES = ("R3", "R4")        # series resistors: their two pads count as joined
SUPPLY_NETS = ("3V3", "1V1")
U1_CAPS = tuple(f"C{n}" for n in range(8, 20))   # design._mcu: IOVDD, USB/ADC, DVDD, VREG caps
# Copper path limits (pad centre to pad centre). The IOVDD pins 10, 22 and 33 and VREG_VOUT 45 are
# joined to an exit inside the pad ring, so their caps sit at that exit (deviations WS2b-5,
# REVIEW-FIX-2); pin 22 is the furthest, around the east moat.
PIN_CAP_MAX_MM = 12.0
CAP_PIN_MAX_MM = 7.0
CAP_GND_VIA_MM = 1.0
# U4's clamp reference pin 5 is on VSYS (deviations ELEC-2); C2 sits at its via (BOARD-5)
U4_REF = ("U4.5", "VSYS", ("C1.1", "C2.1"))
U4_CAP_MAX_MM = 5.0


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


def copper_graph(board: pcbnew.BOARD, code: int):
    """Copper of one net as a graph: track ends (joined where an end lies in another track's,
    a via's or a pad's copper, T-junctions split by length), vias and pads (keyed REF.pad)."""
    from shapely.geometry import LineString
    graph: dict[object, list[tuple[object, float]]] = defaultdict(list)

    def edge(a, b, w):
        w = max(0.0, w)          # project() onto a segment end gives -3e-17: a negative cycle that
        graph[a].append((b, w))  # dijkstra() never leaves (killed for memory, ELEC-5)
        graph[b].append((a, w))
    segs, vias = [], []
    for t in board.GetTracks():
        if t.GetNetCode() != code:
            continue
        if t.Type() == pcbnew.PCB_VIA_T:
            vias.append((("via", len(vias)), Point(mm_xy(t.GetPosition())), pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu)) / 2))
        else:
            a, b = mm_xy(t.GetStart()), mm_xy(t.GetEnd())
            segs.append((a, b, t.GetLayer(), LineString([a, b]).buffer(pcbnew.ToMM(t.GetWidth()) / 2 + SNAP)))
    pads = []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetCode() == code:
                layers = [l for l in (pcbnew.F_Cu, pcbnew.B_Cu) if pad.IsOnLayer(l)]
                pads.append((f"{fp.GetReference()}.{pad.GetNumber()}", mm_xy(pad.GetPosition()), layers,
                             pad_poly(pad).buffer(SNAP)))
    for i, (a, b, layer, _) in enumerate(segs):
        edge(("s", i, 0), ("s", i, 1), math.dist(a, b))
        for end, p in ((0, a), (1, b)):
            q = Point(p)
            for j, (c, d, lj, gj) in enumerate(segs):
                if j != i and lj == layer and gj.contains(q):
                    s = LineString([c, d]).project(q)
                    edge(("s", i, end), ("s", j, 0), s)
                    edge(("s", i, end), ("s", j, 1), math.dist(c, d) - s)
            for key, c, r in vias:
                if c.distance(q) <= r + SNAP:
                    edge(("s", i, end), key, 0.0)
            for name, c, layers, poly in pads:
                if layer in layers and poly.contains(q):
                    edge(("s", i, end), name, math.dist(p, c))
    for i, (a, b, layer, _) in enumerate(segs):           # pads and vias a track runs through
        line = LineString([a, b])
        for name, c, layers, poly in pads:
            if layer in layers and line.intersects(poly):
                s = line.project(Point(c))
                edge(name, ("s", i, 0), s + line.distance(Point(c)))
                edge(name, ("s", i, 1), line.length - s + line.distance(Point(c)))
        for key, c, r in vias:
            if line.distance(c) <= r:
                s = line.project(c)
                edge(key, ("s", i, 0), s)
                edge(key, ("s", i, 1), line.length - s)
    for key, c, r in vias:
        for name, pc, _, poly in pads:
            if poly.contains(c):
                edge(key, name, math.dist(pc, (c.x, c.y)))
    return graph


def decoupling(board: pcbnew.BOARD) -> tuple[dict[str, float], dict[str, float], dict[str, float]]:
    """Copper path pin -> nearest cap and cap -> nearest U1 pin per supply net, and cap GND pad ->
    nearest GND via (straight distance)."""
    u1 = board.FindFootprintByReference("U1")
    pin_cap, cap_pin = {}, {}
    for name in SUPPLY_NETS:
        code = board.FindNet(name).GetNetCode()
        graph = copper_graph(board, code)
        pins = [f"U1.{p.GetNumber()}" for p in u1.Pads() if p.GetNetCode() == code]
        caps = [f"{c}.1" for c in U1_CAPS
                if any(p.GetNumber() == "1" and p.GetNetCode() == code for p in board.FindFootprintByReference(c).Pads())]
        for p in sorted(pins, key=lambda p: int(p[3:])):
            pin_cap[f"{name} {p}"] = dijkstra(graph, [p], set(caps))
        for c in caps:
            cap_pin[c[:-2]] = dijkstra(graph, [c], set(pins))
    gnd = board.FindNet("GND").GetNetCode()
    vias = [mm_xy(t.GetPosition()) for t in board.GetTracks() if t.Type() == pcbnew.PCB_VIA_T and t.GetNetCode() == gnd]
    gnd_via = {}
    for c in U1_CAPS:
        pad = next(p for p in board.FindFootprintByReference(c).Pads() if p.GetNumber() == "2")
        gnd_via[c] = min(math.dist(mm_xy(pad.GetPosition()), v) for v in vias)
    return pin_cap, cap_pin, gnd_via


def u1_gnd(board: pcbnew.BOARD, side: str) -> tuple[int, list[str], float, list[str]]:
    """U1's GND against the main B.Cu GND plane (the largest filled B.Cu GND area): the B.Cu copper
    of GND only (the saved pour fill, tracks, vias, pads), joined as complete_routes.islands joins
    it. Returns (EP vias in it, U1 caps whose GND via is in it, its area in mm2, errors)."""
    gnd, B = board.FindNet("GND").GetNetCode(), pcbnew.B_Cu
    items, _ = complete_routes.collect(board)
    mine = [complete_routes.Item(it.net, {B: it.geoms[B]}, ref=it, pad=it.pad,
                                 anchors={B: (it.anchors or {}).get(B, [])})
            for it in items if it.net == gnd and B in it.geoms]
    pours = [it for it in complete_routes.pour_copper(board) if it.net == gnd and B in it.geoms]
    if not pours:
        return 0, [], 0.0, ["no filled B.Cu GND pour"]
    main = max(pours, key=lambda it: it.geoms[B].area)
    group = next(g for g in complete_routes.islands(mine + pours, gnd) if any(it is main for it in g))
    joined = {id(it.ref) for it in group if it.ref is not None}
    vias = {it.ref.anchors[B][0]: it for it in mine if not it.pad and len(it.ref.geoms) == 2}
    ep = pad_poly(next(p for p in board.FindFootprintByReference("U1").Pads() if p.GetNumber() == "57"))
    ep_vias = [xy for xy in vias if ep.contains(Point(xy))]
    ep_in = sum(id(vias[xy].ref) in joined for xy in ep_vias)
    errs = [] if ep_vias and ep_in == len(ep_vias) else [
        f"U1 exposed pad: {ep_in} of {len(ep_vias)} thermal vias in the main B.Cu GND plane"]
    caps_in = []
    for c in U1_CAPS:
        pad = next(p for p in board.FindFootprintByReference(c).Pads() if p.GetNumber() == "2")
        xy = min(vias, key=lambda v: math.dist(v, mm_xy(pad.GetPosition())))
        if id(vias[xy].ref) in joined:
            caps_in.append(c)
        elif c in GND_LINKED_CAPS[side]:
            errs.append(f"{c} GND via at ({xy[0]:.2f}, {xy[1]:.2f}) is not in the main B.Cu GND plane")
    return ep_in, caps_in, main.geoms[B].area, errs


def under_crystal(board: pcbnew.BOARD) -> list[str]:
    """B.Cu tracks and any vias whose copper reaches under Y1's courtyard."""
    from shapely.geometry import LineString
    cy = courtyard(board.FindFootprintByReference("Y1"))
    out = []
    for t in board.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            g = Point(mm_xy(t.GetPosition())).buffer(pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu)) / 2)
        elif t.GetLayer() == pcbnew.B_Cu:
            g = LineString([mm_xy(t.GetStart()), mm_xy(t.GetEnd())]).buffer(pcbnew.ToMM(t.GetWidth()) / 2)
        else:
            continue
        if g.intersects(cy):
            out.append(f"{t.GetNetname()} {'via' if t.Type() == pcbnew.PCB_VIA_T else 'B.Cu track'} at "
                       f"({g.centroid.x:.2f}, {g.centroid.y:.2f})")
    return out


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
    results.append(("nothing on B.Cu or in vias under Y1", under_crystal(board)))
    pin_cap, cap_pin, gnd_via = decoupling(board)
    worst_pin, worst_cap, worst_via = (max(d, key=d.get) for d in (pin_cap, cap_pin, gnd_via))
    errs = [f"{p} is {v:.2f} mm of copper from a cap > {PIN_CAP_MAX_MM}" for p, v in pin_cap.items() if v > PIN_CAP_MAX_MM]
    errs += [f"{c} is {v:.2f} mm of copper from a U1 supply pin > {CAP_PIN_MAX_MM}" for c, v in cap_pin.items()
             if v > CAP_PIN_MAX_MM]
    errs += [f"{c} GND pad {v:.2f} mm from a GND via > {CAP_GND_VIA_MM}" for c, v in gnd_via.items() if v > CAP_GND_VIA_MM]
    results.append((f"decoupling: pins <= {pin_cap[worst_pin]:.2f} mm from a cap ({worst_pin}), caps <= "
                    f"{cap_pin[worst_cap]:.2f} mm from a pin ({worst_cap}), GND vias <= {gnd_via[worst_via]:.2f} mm",
                    errs))
    for net in SUPPLY_NETS:
        print(f"     {net} U1 pin -> nearest cap, mm: " + ", ".join(
            f"{k.split('.')[1]} {v:.1f}" for k, v in pin_cap.items() if k.startswith(net)))
    ep_in, caps_in, area, errs = u1_gnd(board, side)
    off = [c for c in U1_CAPS if c not in caps_in]
    results.append((f"U1 GND: {ep_in} EP vias and {len(caps_in)}/{len(U1_CAPS)} cap GND vias in the main B.Cu "
                    f"GND plane ({area:.0f} mm2); gated: EP + {', '.join(GND_LINKED_CAPS[side]) or 'no caps'}"
                    f"{'; not in it: ' + ', '.join(off) if off else ''}", errs))
    pin, net, caps = U4_REF
    ref = dijkstra(copper_graph(board, board.FindNet(net).GetNetCode()), [pin], set(caps))
    results.append((f"U4 {net} reference: {ref:.2f} mm of copper to a {net} cap",
                    [f"{ref:.2f} mm > {U4_CAP_MAX_MM}"] if ref > U4_CAP_MAX_MM else []))
    results.append(("no via in an SMD pad", [f"{v.GetNetname()} via at ({pcbnew.ToMM(v.GetPosition().x):.3f}, "
                                              f"{pcbnew.ToMM(v.GetPosition().y):.3f}) in {pad}"
                                              for v, pad in vias_in_pads(board)]))
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
