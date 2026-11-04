# SPDX-License-Identifier: GPL-3.0-or-later
"""Tie U1's GND copper to the GND planes where routing left it on a thin neck (spec §6.4, §9 stage 11).

    python3 pcb/scripts/gnd_ties.py <side>     (edits pcb/<side>/worxboard-<side>.kicad_pcb)

Runs in stage C on the routed, filled board, after the DRC gate and before prune.py. It reads the U1
GND gates of checks.py (docs/deviations.md ORDER-4):

- links: the exposed pad (EP, the RP2040's only GND pin) reaches the GND planes GND_LINK_WIN out by
  GND_LINKS_MIN separate paths over copper about GND_NECK_W wide;
- U4 pin 2 (the USB ESD clamp's GND) reaches a J1 GND pad, and the flash cap C5's GND pad reaches U2
  pin 4, within GND_PIN_MAX_MM of GND copper.

While one fails, it tries GND ties, TIE_WIDTHS wide, in this order:

1. link ties from the EP's own B.Cu copper (the GND pour piece round the EP's via array, taken before
   the first tie; U4 pin 2 and U2 pin 4 reach it through their own vias) to the main F.Cu and B.Cu GND
   pour pieces outside it, starting near each failing pin's PIN_ANCHORS (U4 pin 2; C5, U2, U2 pin 4);
2. pair ties, pad to pad (PAIR_TIES: U2 pin 4 to C5's GND pad), at most PAIR_MAX_MM long;
3. pad ties (PAD_TIES): the pad, by its own via, to the main B.Cu GND piece;
4. link ties in each of WEDGES directions round the EP, while the links fail.

A link or pad tie is at most TIE_MAX_MM long; every tie has at most TIE_MAX_VIAS vias. A tie is routed
by the completion router's A* (complete_routes.route_pair) and may cross other nets' unlocked copper at
a cost per cell (TIE_COSTS; PAIR_COSTS for pair ties, which may rip more): that copper is ripped up and
its nets are routed again, GUARD_R clear of the tie's ends (complete_routes.complete, then soft_route,
as negotiate() does). A tie is kept only if every net is closed afterwards and the gates improve (more
links, or a failing pin path at least GAIN_MM shorter) without any getting worse; else the board is
restored. Kept ties are locked, so prune.py and later rip-ups leave them alone, and each new tie keeps
clear of the ties before it. Exits 1 if a gate still fails. A board that passes is left untouched (not
even saved): the right half stays as it was.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pcbnew  # noqa: E402
from shapely.geometry import LineString, Point, Polygon  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

import checks  # noqa: E402
import complete_routes as cr  # noqa: E402
from complete_routes import Index, Item, collect, emit, pour_copper, route_pair  # noqa: E402
from place import seed_kiids  # noqa: E402
from route_critical import Router  # noqa: E402

TIE_WIDTHS = (0.5, 0.4)      # mm: >= checks.GND_NECK_W, so a tie counts as a link
TIE_NEAR = 4.0               # mm: a tie for a pin path starts this close to its anchor pad
PIN_ANCHORS = {"U4.2": ("U4.2",), "U2.4": ("C5.2", "U2", "U2.4")}   # C5 sits across U2 from pin 4
PAIR_TIES = {"U2.4": (("U2.4", "C5.2"),)}   # then: pad to pad (the flash's GND pin to its cap)
PAIR_MAX_MM = 16.0           # a pad-to-pad tie may run this long: U2.4 and C5.2 are 10.1 mm apart
PAIR_COSTS = (0.5, 2.0, 8.0)  # mm per crossed cell: a pair tie may rip more on its way
PAD_TIES = {"U4.2": ("U4.2",), "U2.4": ("C5.2", "U2.4")}   # then: the pad by its own via to main B.Cu
TIE_MAX_MM = 12.0            # a longer tie, or one with more vias, is a detour, not a tie
TIE_MAX_VIAS = 2
WEDGES = 8                   # directions round the EP for link ties
TIE_COSTS = (2.0, 8.0, 20.0)  # mm per grid cell for crossing another net's unlocked copper
GAIN_MM = 1.0
GUARD_R = 0.8                # mm: other nets' reroutes keep this far from each tie end, so the pours
                             # it ends in still reach it
MAX_TIES = 10


def fill(board: pcbnew.BOARD) -> None:
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())


def gnd_pours(board: pcbnew.BOARD) -> list[Item]:
    gnd = board.FindNet("GND").GetNetCode()
    return [it for it in pour_copper(board) if it.net == gnd]


def metrics(board: pcbnew.BOARD) -> dict[str, float]:
    """links (count) and the two pin paths (mm) of checks.py."""
    links = [d for d in checks.u1_gnd_links(board) if d <= checks.GND_LINK_MAX_MM]
    (_, d4), (_, d2) = checks.gnd_pin_paths(board).items()
    return {"EP": len(links), "U4.2": d4, "U2.4": d2}


def failing(m: dict[str, float]) -> dict[str, bool]:
    return {"EP": m["EP"] < checks.GND_LINKS_MIN, "U4.2": m["U4.2"] > checks.GND_PIN_MAX_MM,
            "U2.4": m["U2.4"] > checks.GND_PIN_MAX_MM}


def show(m: dict[str, float]) -> str:
    return (f"links {m['EP']} (need {checks.GND_LINKS_MIN}), U4 pin 2 -> J1 GND {m['U4.2']:.1f} mm, "
            f"C5 -> U2 pin 4 {m['U2.4']:.1f} mm (max {checks.GND_PIN_MAX_MM})")


def better(new: dict[str, float], old: dict[str, float]) -> bool:
    """More links or a failing pin path GAIN_MM shorter, and nothing worse."""
    if new["EP"] < old["EP"] or any(new[k] > old[k] + 0.05 for k in ("U4.2", "U2.4")):
        return False
    bad = failing(old)
    return new["EP"] > old["EP"] or any(bad[k] and new[k] <= old[k] - GAIN_MM for k in ("U4.2", "U2.4"))


def regions(board: pcbnew.BOARD):
    """Before any tie: the B.Cu GND pour piece(s) round the EP's vias (the EP's own copper), the main
    F.Cu and B.Cu GND pour pieces outside it, as shapes, and the EP centre. A tie runs from the first
    to the second, so it stays a separate path even once earlier ties have joined the pieces into one."""
    F, B = pcbnew.F_Cu, pcbnew.B_Cu
    pours = gnd_pours(board)
    main_b = max((it for it in pours if B in it.geoms), key=lambda it: it.geoms[B].area)
    main_f = max((it for it in pours if F in it.geoms), key=lambda it: it.geoms[F].area)
    gnd = board.FindNet("GND").GetNetCode()
    ep = checks.pad_poly(next(p for p in board.FindFootprintByReference("U1").Pads() if p.GetNumber() == "57"))
    vias = [Point(cr.xy(t.GetPosition())) for t in board.GetTracks()
            if t.Type() == pcbnew.PCB_VIA_T and t.GetNetCode() == gnd and ep.contains(Point(cr.xy(t.GetPosition())))]
    own = unary_union([it.geoms[B] for it in pours
                       if B in it.geoms and it is not main_b and any(it.geoms[B].contains(v) for v in vias)])
    return own, {F: main_f.geoms[F].difference(own), B: main_b.geoms[B].difference(own)}, ep.centroid


def anchor_area(board: pcbnew.BOARD, anchor, centre: Point):
    """Where a tie may start: within TIE_NEAR of a pad (REF.n) or a part's origin (REF), or a wedge round
    the EP (an int)."""
    if isinstance(anchor, str):
        ref, _, num = anchor.partition(".")
        fp = board.FindFootprintByReference(ref)
        at = next(p for p in fp.Pads() if p.GetNumber() == num).GetPosition() if num else fp.GetPosition()
        return Point(cr.xy(at)).buffer(TIE_NEAR)
    a0, a1 = (2 * math.pi * (anchor + s) / WEDGES for s in (-0.5, 0.5))
    pts = [(centre.x, centre.y)] + [(centre.x + 50 * math.cos(a), centre.y + 50 * math.sin(a))
                                    for a in (a0 + (a1 - a0) * t / 8 for t in range(9))]
    return Polygon(pts)


def pad_item(board: pcbnew.BOARD, name: str) -> Item:
    """Pad REF.n as a GND copper item."""
    ref, _, num = name.partition(".")
    pad = next(q for q in board.FindFootprintByReference(ref).Pads() if q.GetNumber() == num)
    geoms = {l: cr.poly(pad.GetEffectivePolygon(l, pcbnew.ERROR_INSIDE)) for l in cr.LAYERS if pad.IsOnLayer(l)}
    return Item(board.FindNet("GND").GetNetCode(), geoms, pad=True, anchors={l: [cr.xy(pad.GetPosition())] for l in geoms})


def ends(board: pcbnew.BOARD, area, own, main) -> tuple[list[Item], list[Item]]:
    """(tie start, targets) as copper now. A link tie (`area` a shape): the EP's own B.Cu copper within
    `area`, and the main pour pieces outside the EP's own copper. A pair tie (`area` two pad names): the
    first pad, and the second. A pad tie (`area` a pad name REF.n): the pad itself, and the main B.Cu
    pour piece outside the EP's own copper, so the pad gets its own via into the board-wide plane."""
    B = pcbnew.B_Cu
    gnd = board.FindNet("GND").GetNetCode()
    if isinstance(area, tuple):
        return [pad_item(board, area[0])], [pad_item(board, area[1])]
    a, b = [], []
    if isinstance(area, str):
        a.append(pad_item(board, area))
        layers = (B,)
    else:
        start = own.intersection(area)
        layers = (pcbnew.F_Cu, B)
    for it in gnd_pours(board):
        (layer, g), = it.geoms.items()
        if layer == B and not isinstance(area, str):
            part = g.intersection(start)
            if part.area > 0:
                a.append(Item(gnd, {B: part}, pour=True))
        rest = g.intersection(main[layer])
        if layer in layers and rest.area > 0:
            b.append(Item(gnd, {layer: rest}, pour=True))
    return a, b


def try_tie(board: pcbnew.BOARD, side: str, fanout: set[str], label: str, area, cost: float,
            blockers: list[Item], guards: list[Item], own, main):
    """Route one tie across other nets' unlocked copper at `cost`, rip that copper up and route its
    nets again. Returns (tie items, width, snapshot, description) with every net closed, else None
    (board restored)."""
    gnd_net = board.FindNet("GND")
    gnd = gnd_net.GetNetCode()
    nets = {c: ni for c, ni in board.GetNetsByNetcode().items()
            if c > 0 and not ni.GetNetname().startswith("unconnected-")}
    a, b = ends(board, area, own, main)
    if not a or not b:
        return None
    items, keepouts = collect(board)
    index = Index(items + gnd_pours(board) + blockers)
    snap = cr.snapshot(board)
    saved = cr.SOFT_COST, cr.QUANT, cr.MAX_POPS
    cr.SOFT_COST, cr.QUANT, cr.MAX_POPS = cost, cr.NEGOTIATE_QUANT, cr.NEGOTIATE_MAX_POPS
    found = None
    try:
        for w in TIE_WIDTHS:
            for step, margin in cr.NEGOTIATE_ATTEMPTS:
                path = route_pair(index, keepouts, gnd, a, b, w, step, margin, side, True)
                if path and cr.path_clear(index, keepouts, gnd, path, w, side):
                    found = path, w
                    break
                path = None
            if found:
                break
    finally:
        cr.SOFT_COST, cr.QUANT, cr.MAX_POPS = saved
    if not found:
        return None
    path, w = found
    hops = sum(1 for p, q in zip(path, path[1:]) if p[0] != q[0])
    length = sum(math.dist(p[1], q[1]) for p, q in zip(path, path[1:]))
    if length > (PAIR_MAX_MM if isinstance(area, tuple) else TIE_MAX_MM) or hops > TIE_MAX_VIAS:
        print(f"  too long: tie {label}, {length:.1f} mm, {hops} via(s), cost {cost}", flush=True)
        return None
    new = emit(board, gnd_net, path, w)
    hit = cr.ripped(index, new, gnd)
    for it in hit:
        board.Delete(it.ref)
    tie = [it.ref for it in new]
    for t in tie:
        t.SetLocked(True)
    touched = {it.net for it in hit} & nets.keys()
    ends_now = guards + [Item(-2, {l: Point(p).buffer(GUARD_R) for l in cr.LAYERS}) for _, p in (path[0], path[-1])]
    cr.PROTECT.clear()
    cr.PROTECT.add(gnd)
    for _ in range(cr.NEGOTIATE_DEPTH):              # victims that cannot reroute rip in turn
        if not touched:
            break
        cr.complete(board, side, fanout, only=tuple(nets[c].GetNetname() for c in touched), skip=(), extra=ends_now)
        still = [c for c, n in cr.open_counts(board, touched).items() if n]
        if not still:
            break
        for c in still:
            cr.PROTECT.add(c)
            more = cr.soft_route(board, side, fanout, c, cost, ends_now)
            touched |= (more or set()) & nets.keys()
    cr.PROTECT.clear()
    fill(board)
    if cr.open_counts(board, [gnd], gnd_pours(board))[gnd]:     # a reroute cut a GND pad off its pour
        cr.complete(board, side, fanout, only=("GND",), skip=(), extra=gnd_pours(board))
        fill(board)
    what = (f"tie {label}: {w} mm, {length:.1f} mm, {hops} via(s), ({path[0][1][0]:.2f}, {path[0][1][1]:.2f}) -> "
            f"({path[-1][1][0]:.2f}, {path[-1][1][1]:.2f}), cost {cost}, ripped {len(hit)} items of "
            f"{', '.join(sorted({nets[it.net].GetNetname() for it in hit})) or 'no net'}")
    open_now = {c: n for c, n in cr.open_counts(board, nets, gnd_pours(board)).items() if n}
    if open_now:
        print(f"  rejected {what}: open {', '.join(nets[c].GetNetname() for c in open_now)}", flush=True)
        undo(board, tie, snap)
        return None
    return tie, w, snap, what, ends_now[len(guards):]


def undo(board: pcbnew.BOARD, tie: list, snap: dict) -> None:
    for t in tie:
        board.Delete(t)
    cr.restore(board, snap)
    fill(board)


def candidates(bad: dict[str, bool]) -> list[tuple[str, str, object]]:
    """(gate, kind, anchor) in the order tried: link ties from the EP's own copper near each failing
    pin's anchors, then pad ties from the failing pins' pads, then link ties in each EP wedge."""
    pins = [g for g in ("U4.2", "U2.4") if bad[g]]
    out = [(g, "link", a) for g in pins for a in PIN_ANCHORS[g]]
    out += [(g, "pair", a) for g in pins for a in PAIR_TIES.get(g, ())]
    out += [(g, "pad", a) for g in pins for a in PAD_TIES[g]]
    return out + ([("EP", "link", k) for k in range(WEDGES)] if bad["EP"] else [])


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in ("left", "right"):
        print(__doc__)
        return 2
    side = argv[1]
    path = ROOT / "pcb" / side / f"worxboard-{side}.kicad_pcb"
    seed_kiids(side, b"gnd_ties", path.read_bytes())
    board = pcbnew.LoadBoard(str(path))
    state = metrics(board)
    print(f"{side}: U1 GND: {show(state)}", flush=True)
    if not any(failing(state).values()):
        print(f"{side}: U1 GND passes, no ties")
        return 0
    fanout = set(Router.fanout_nets(board))
    own, main, centre = regions(board)
    blockers: list[Item] = []                  # kept ties: later ones keep clear of them
    guards: list[Item] = []                    # their ends: reroutes keep clear of them
    ties = 0
    while any(failing(state).values()) and ties < MAX_TIES:
        progress = False
        for gate, kind, anchor in candidates(failing(state)):
            label = (f"{gate} from pad {anchor}" if kind == "pad" else
                     f"{gate} pads {anchor[0]} -> {anchor[1]}" if kind == "pair" else
                     f"{gate} at {anchor}" if isinstance(anchor, str) else f"EP wedge {anchor}")
            area = anchor if kind in ("pad", "pair") else anchor_area(board, anchor, centre)
            for cost in (PAIR_COSTS if kind == "pair" else TIE_COSTS):
                res = try_tie(board, side, fanout, label, area, cost, blockers, guards, own, main)
                if res is None:
                    continue
                tie, w, snap, what, tie_guards = res
                new = metrics(board)
                if not better(new, state):
                    print(f"  no gain {what}: {show(new)}", flush=True)
                    undo(board, tie, snap)
                    continue
                state, progress, ties = new, True, ties + 1
                guards += tie_guards
                print(f"  kept {what}: {show(state)}", flush=True)
                for t in tie:
                    if t.Type() == pcbnew.PCB_VIA_T:
                        c = Point(cr.xy(t.GetPosition()))
                        blockers.append(Item(-2, {l: c.buffer(cr.VIA[0] / 2) for l in cr.LAYERS}, c.buffer(cr.VIA[1] / 2)))
                    else:
                        line = LineString([cr.xy(t.GetStart()), cr.xy(t.GetEnd())])
                        blockers.append(Item(-2, {t.GetLayer(): line.buffer(w / 2)}))
                break
            if progress:
                break
        if not progress:
            break
    board.Save(str(path))
    if any(failing(state).values()):
        print(f"{side}: U1 GND still fails after {ties} tie(s): {show(state)}")
        return 1
    print(f"{side}: U1 GND passes with {ties} tie(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
