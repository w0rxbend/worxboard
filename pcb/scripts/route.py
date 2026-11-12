# SPDX-License-Identifier: GPL-3.0-or-later
"""Route what the locked critical routes leave open, stitch and fill the pours (spec §9 stage 10).

    python3 pcb/scripts/route.py <side> [--continue]     (edits pcb/<side>/worxboard-<side>.kicad_pcb)

--continue runs more completion rounds on the board as saved (stage_c.sh uses it while DRC still
reports unconnected items).

complete_routes.py routes every open connection of the placed board with its maze router, the U1
fan-out nets first (and, for the last gaps, rips up and reroutes other nets, keeping a change only
when fewer gaps remain). No external autorouter runs: on four layers GND and VLED are planes, the
matrix and the LED cells are locked copper (route_critical.py), and about a hundred short signal and
supply connections remain (docs/deviations.md REVB-8). Then GND stitching vias go on a STITCH_NEAR
grid in Z_BACK around U1, Y1 and J1 and a STITCH_FAR grid elsewhere, wherever a via clears every
other net, hole and the edge (spec §8.4). They are placed after routing rather than before
(docs/deviations.md WS2b), so they never block a route. The pours are then filled; vias that do not
land in filled GND on both outer layers are dropped and the pours refilled.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pcbnew  # noqa: E402
from shapely.geometry import LineString, Point, Polygon, box  # noqa: E402
from shapely.ops import unary_union  # noqa: E402
from shapely.strtree import STRtree  # noqa: E402

import complete_routes  # noqa: E402
from place import VIA, layout_side, mm, outline_points, pt, seed_kiids  # noqa: E402
from route_critical import Router  # noqa: E402

STITCH_NEAR = 5.0            # grid pitch near U1 / Y1 / J1 (mm)
STITCH_FAR = 10.0            # grid pitch elsewhere
NEAR_R = 14.0                # "near" = within this of the U1 / Y1 / J1 centres
CLEAR = 0.25                 # via copper to other copper (Default clearance 0.2 + margin)
HOLE_CLEAR = 0.3             # via to any drilled hole
EDGE_CLEAR = 0.6             # via copper to the board edge
COURTYARD_CLEAR = 0.2        # vias stay out of footprint courtyards (bodies, sockets)
LAYERS = (pcbnew.F_Cu, pcbnew.B_Cu)
COMPLETE_ROUNDS = 3          # completion passes against the filled pours
LATE_MAX_POPS = 6_000_000    # --continue rounds: A* budget per attempt
LATE_ATTEMPTS = ((0.1, 35.0),)   # ... and one wide-window attempt
LATE_HEURISTIC = 2.5         # ... and a greedier A*: a board-crossing rip-up route otherwise spends the budget


def to_mm(v) -> tuple[float, float]:
    return pcbnew.ToMM(v.x), pcbnew.ToMM(v.y)


def poly_of(sps) -> list[Polygon]:
    out = []
    for i in range(sps.OutlineCount()):
        o = sps.Outline(i)
        pts = [to_mm(o.CPoint(j)) for j in range(o.PointCount())]
        if len(pts) >= 3:
            out.append(Polygon(pts).buffer(0))
    return out


def obstacles(board: pcbnew.BOARD) -> STRtree:
    """Everything a GND stitching via must stay clear of."""
    gnd = board.FindNet("GND").GetNetCode()
    geoms = []
    for t in board.GetTracks():
        if t.GetNetCode() == gnd:
            continue
        if t.Type() == pcbnew.PCB_VIA_T:
            geoms.append(Point(to_mm(t.GetPosition())).buffer(pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu)) / 2))
        else:
            geoms.append(LineString([to_mm(t.GetStart()), to_mm(t.GetEnd())]).buffer(pcbnew.ToMM(t.GetWidth()) / 2))
    for fp in board.GetFootprints():
        for layer in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
            geoms += [g.buffer(COURTYARD_CLEAR) for g in poly_of(fp.GetCourtyard(layer))]
        for pad in fp.Pads():
            bb = pad.GetBoundingBox()
            x0, y0 = to_mm(bb.GetOrigin())
            x1, y1 = to_mm(bb.GetEnd())
            if pad.GetNetCode() != gnd:
                geoms.append(box(x0, y0, x1, y1))
            if pad.HasHole():
                d = max(pcbnew.ToMM(pad.GetDrillSize().x), pcbnew.ToMM(pad.GetDrillSize().y))
                geoms.append(Point(to_mm(pad.GetPosition())).buffer(d / 2 + HOLE_CLEAR - CLEAR))
    for z in board.Zones():
        if z.GetIsRuleArea() and z.GetDoNotAllowVias():
            geoms += poly_of(z.Outline())
    geoms += complete_routes.led_cutouts(board)        # rev B LED cutouts, grown by their 0.3 mm rule
    return STRtree(geoms)


def candidates(board: pcbnew.BOARD, side: str) -> list[tuple[float, float]]:
    lay = layout_side(side)
    pcb = Polygon(outline_points(side)).buffer(-(EDGE_CLEAR + VIA[0] / 2))
    back = unary_union([Polygon(p["exterior"], p.get("holes", [])) for p in lay["zones"]["Z_BACK"]])
    centres = [to_mm(board.FindFootprintByReference(r).GetPosition()) for r in ("U1", "Y1", "J1")]
    x0, y0, x1, y1 = pcb.bounds
    pts = set()
    for pitch, keep in ((STITCH_FAR, lambda p: True),
                        (STITCH_NEAR, lambda p: back.contains(Point(p)) and
                         min(math.dist(p, c) for c in centres) < NEAR_R)):
        nx, ny = int((x1 - x0) / pitch) + 1, int((y1 - y0) / pitch) + 1
        for i in range(nx):
            for j in range(ny):
                p = (round(x0 + i * pitch, 3), round(y0 + j * pitch, 3))
                if pcb.contains(Point(p)) and keep(p):
                    pts.add(p)
    return sorted(pts)


def add_stitching(board: pcbnew.BOARD, side: str) -> list[pcbnew.PCB_VIA]:
    tree = obstacles(board)
    gnd = board.FindNet("GND")
    vias = []
    placed = []
    for p in candidates(board, side):
        disc = Point(p).buffer(VIA[0] / 2 + CLEAR)
        if tree.query(disc, predicate="intersects").size:
            continue
        if any(math.dist(p, q) < VIA[0] + CLEAR for q in placed):
            continue
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(pt(*p))
        v.SetWidth(mm(VIA[0]))
        v.SetDrill(mm(VIA[1]))
        v.SetNet(gnd)
        board.Add(v)
        vias.append(v)
        placed.append(p)
    return vias


def fill(board: pcbnew.BOARD) -> None:
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())


def in_both_pours(board: pcbnew.BOARD, v: pcbnew.PCB_VIA) -> bool:
    pos = v.GetPosition()
    hit = set()
    for z in board.Zones():
        if z.GetIsRuleArea() or z.GetNetname() != "GND":
            continue
        for layer in LAYERS:
            if z.IsOnLayer(layer) and z.HitTestFilledArea(layer, pos):
                hit.add(layer)
    return len(hit) == len(LAYERS)


def pours(board: pcbnew.BOARD) -> list:
    fill(board)
    return complete_routes.pour_copper(board)


def finish_open(board: pcbnew.BOARD, side: str, fanout: set[str]) -> list[str]:
    """Transactional rip-up for the gaps the plain completion left, then GND against the
    refilled pours."""
    complete_routes.negotiate(board, side, fanout, pours)
    failed = complete_routes.complete(board, side, fanout, skip=(), extra=pours(board))
    fill(board)
    return failed


def main(argv: list[str]) -> int:
    if len(argv) not in (2, 3) or argv[1] not in ("left", "right") or argv[2:] not in ([], ["--continue"]):
        print(__doc__)
        return 2
    side = argv[1]
    path = ROOT / "pcb" / side / f"worxboard-{side}.kicad_pcb"
    seed_kiids(side, b"route", " ".join(argv[1:]).encode(), path.read_bytes())
    board = pcbnew.LoadBoard(str(path))
    if argv[2:] == ["--continue"]:
        # later rounds: bigger windows and search budgets for the long leftovers
        complete_routes.MAX_POPS = LATE_MAX_POPS
        complete_routes.ATTEMPTS = complete_routes.ATTEMPTS + LATE_ATTEMPTS
        complete_routes.HEURISTIC = LATE_HEURISTIC
        fill(board)
        fanout = set(Router.fanout_nets(board))
        failed = complete_routes.complete(board, side, fanout, skip=(), extra=complete_routes.pour_copper(board))
        fill(board)
        if failed:
            failed = finish_open(board, side, fanout)
        board.Save(str(path))
        print(f"{side}: completion round, still open: {', '.join(failed) or 'none'}")
        return 0
    for t in list(board.GetTracks()):          # a re-run replaces the previous routes
        if not t.IsLocked():
            board.Delete(t)
    fanout = set(Router.fanout_nets(board))
    failed = complete_routes.complete(board, side, fanout)
    vias = add_stitching(board, side)
    fill(board)
    dead = [v for v in vias if not in_both_pours(board, v)]
    for v in dead:
        board.Delete(v)
    fill(board)
    # GND pads the pours left isolated, and anything a rip-up left open: route against the
    # filled pours, refill, up to COMPLETE_ROUNDS times
    for _ in range(COMPLETE_ROUNDS):
        failed = complete_routes.complete(board, side, fanout, skip=(), extra=complete_routes.pour_copper(board))
        fill(board)
        if not failed:
            break
    if failed:
        failed = finish_open(board, side, fanout)
    if failed:
        print(f"{side}: still open after completion: {', '.join(failed)}")
    board.Save(str(path))
    stats = {"tracks": sum(t.Type() == pcbnew.PCB_TRACE_T for t in board.GetTracks()),
             "vias": sum(t.Type() == pcbnew.PCB_VIA_T for t in board.GetTracks()),
             "stitching": len(vias) - len(dead)}
    print(f"{side}: routed, {json.dumps(stats)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
