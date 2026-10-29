# SPDX-License-Identifier: GPL-3.0-or-later
"""Finish the connections Freerouting left open (spec §9 stage 10, after the session import).

A small two-layer maze router: for every net still split into islands it rasterises, on a fine
grid around the gap (ATTEMPTS), all other-net copper, holes, keepouts and the board edge (dilated by the
track half-width + the clearance + a grid margin), then runs A* with 45 deg moves and vias between the
islands. Routes are written as ordinary (unlocked) tracks and vias; DRC is the judge afterwards.
negotiate() closes the last gaps by a transactional rip-up of other nets' unlocked copper.

    import complete_routes; complete_routes.complete(board, side)
"""
from __future__ import annotations

import heapq
import math
from dataclasses import dataclass

import numpy as np
import pcbnew
import shapely
import shapely.ops
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

from place import POWER_NETS, VIA, mm, outline_points, pt

ATTEMPTS = ((0.1, 6.0), (0.05, 4.0), (0.1, 18.0))   # (grid mm, window margin mm), in order
MAX_POPS = 1_500_000         # A* expansion budget per attempt
CLEARANCE = 0.2
HOLE_CLEARANCE = 0.25
EDGE_CLEARANCE = 0.5
VIA_COST = 1.6               # mm of track a via is worth
SOFT_RIP = False             # rip-up of other nets oscillates (routes churn); off by default
SOFT_COST = 3.0              # mm of track that crossing a rippable track costs, per grid cell
PAIR_TRIES = 3               # closest island pairs tried per round
MAX_RIPS = 2                 # rip-ups before a net waits for the soft queue
MAX_ROUTES = 600
HEURISTIC = 1.3              # A* weight (> 1: faster, slightly longer routes)
QUANT = 0.6                  # extra dilation, in grid steps, for the centre-line quantisation
WIDTHS = {"power": (0.5, 0.25, 0.2), "fanout": (0.15,), "default": (0.25, 0.15)}
LAYERS = (pcbnew.F_Cu, pcbnew.B_Cu)
ESCAPE_LEN = 2.0             # soft mode: a lane this long straight on from other nets' locked
ESCAPE_R = 0.35              # stub ends (+- this) costs ESCAPE_COST mm of track per grid cell,
ESCAPE_COST = 3.0            # so a rip-up route does not wall in the next stub
STUB_ENDS: list = []         # (net, layer, lane) for locked track ends that join nothing (collect)
PROTECT: set = set()         # nets a rip-up should spare (negotiate: those it just routed) ...
PROTECT_COST = 25.0          # ... crossing them costs this many mm of track per grid cell
STATS: dict = {}             # last route_pair call: grid cells, start / goal cells, expansions
MOVES = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
         (1, 1, math.sqrt(2)), (1, -1, math.sqrt(2)), (-1, 1, math.sqrt(2)), (-1, -1, math.sqrt(2))]


@dataclass(eq=False)
class Item:
    net: int
    geoms: dict                  # layer -> shapely geometry (copper)
    hole: object = None          # drilled hole (shapely), any net
    ref: object = None           # the unlocked board track / via (may be ripped up)
    pour: bool = False           # filled GND pour: a GND target, never an obstacle (refilled later)
    pad: bool = False            # a pour joins a pad it overlaps, but tracks / vias only by anchor
    anchors: dict = None         # layer -> [(x, y)]: track ends, via / pad centres (KiCad joins
                                 # items only where an anchor lies inside the other's copper)


def xy(v) -> tuple[float, float]:
    return pcbnew.ToMM(v.x), pcbnew.ToMM(v.y)


def poly(sps) -> object:
    out = []
    for i in range(sps.OutlineCount()):
        o = sps.Outline(i)
        pts = [xy(o.CPoint(j)) for j in range(o.PointCount())]
        if len(pts) >= 3:
            out.append(Polygon(pts).buffer(0))
    return unary_union(out)


def collect(board: pcbnew.BOARD) -> tuple[list[Item], list]:
    items, keepouts = [], []
    for t in board.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            c = Point(xy(t.GetPosition()))
            disc = c.buffer(pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu)) / 2)
            items.append(Item(t.GetNetCode(), {l: disc for l in LAYERS}, c.buffer(pcbnew.ToMM(t.GetDrillValue()) / 2),
                              None if t.IsLocked() else t, anchors={l: [(c.x, c.y)] for l in LAYERS}))
        else:
            a, b = xy(t.GetStart()), xy(t.GetEnd())
            seg = LineString([a, b]).buffer(pcbnew.ToMM(t.GetWidth()) / 2)
            items.append(Item(t.GetNetCode(), {t.GetLayer(): seg}, None, None if t.IsLocked() else t,
                              anchors={t.GetLayer(): [a, b]}))
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            geoms = {l: poly(pad.GetEffectivePolygon(l, pcbnew.ERROR_INSIDE)) for l in LAYERS if pad.IsOnLayer(l)}
            centre = xy(pad.GetPosition())
            hole = None
            if pad.HasHole():
                d = max(pcbnew.ToMM(pad.GetDrillSize().x), pcbnew.ToMM(pad.GetDrillSize().y))
                hole = Point(xy(pad.GetPosition())).buffer(d / 2)
            if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                geoms = {}
            items.append(Item(pad.GetNetCode() if geoms else -1, geoms, hole,
                              anchors={l: [centre] for l in geoms}, pad=True))
    for z in board.Zones():
        if z.GetIsRuleArea() and z.GetDoNotAllowTracks():
            keepouts.append(([l for l in LAYERS if z.IsOnLayer(l)], poly(z.Outline()), z.GetDoNotAllowVias()))
    STUB_ENDS[:] = stub_ends(items)
    return items, keepouts


def stub_ends(items: list[Item]) -> list:
    """Ends of locked tracks (the fan-out) that touch no other locked copper or pad of their net."""
    ends: dict = {}
    for it in items:
        if it.ref is None and not it.pad and not it.pour and len(it.geoms) == 1:
            (layer, pts), = it.anchors.items()
            for p, q in ((pts[0], pts[-1]), (pts[-1], pts[0])):
                k = (it.net, layer, round(p[0], 3), round(p[1], 3))
                n, _ = ends.get(k, (0, q))
                ends[k] = (n + 1, q)
    fixed = [(it.net, l, g) for it in items if it.ref is None and not it.pour and (it.pad or len(it.geoms) == 2)
             for l, g in it.geoms.items()]
    tree = shapely.STRtree(np.array([g for _, _, g in fixed], dtype=object))
    out = []
    for (net, layer, x, y), (n, q) in ends.items():
        if n != 1:
            continue
        hits = tree.query(Point(x, y).buffer(1e-3), predicate="intersects")
        if not any(fixed[h][0] == net and fixed[h][1] == layer for h in hits):
            d = math.dist((x, y), q) or 1.0
            ux, uy = (x - q[0]) / d, (y - q[1]) / d       # straight on, out of the stub
            out.append((net, layer, LineString([(x, y), (x + ux * ESCAPE_LEN, y + uy * ESCAPE_LEN)])))
    return out


def islands(items: list[Item], net: int) -> list[list[Item]]:
    """Copper of one net grouped into electrically joined islands: two items join when an anchor
    of one lies inside the other's copper on a shared layer (pours join whatever they cover)."""
    mine = [it for it in items if it.net == net and it.geoms]
    parent = list(range(len(mine)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for layer in LAYERS:
        idx = [i for i, it in enumerate(mine) if layer in it.geoms]
        if not idx:
            continue
        geoms = np.array([mine[i].geoms[layer] for i in idx], dtype=object)
        tree = shapely.STRtree(geoms)
        pts, owner = [], []
        for i in idx:
            for p in (mine[i].anchors or {}).get(layer, []):
                pts.append(Point(p))
                owner.append(i)
        if pts:
            for a, b in zip(*tree.query(np.array(pts, dtype=object), predicate="intersects")):
                parent[find(owner[a])] = find(idx[b])
        pours = [i for i in idx if mine[i].pour]
        if pours:                                 # a pour holds every pad it touches (KiCad)
            for a, b in zip(*tree.query(np.array([mine[i].geoms[layer] for i in pours], dtype=object),
                                        predicate="intersects")):
                if mine[idx[b]].pad:
                    parent[find(pours[a])] = find(idx[b])
    groups: dict[int, list[Item]] = {}
    for i, it in enumerate(mine):
        groups.setdefault(find(i), []).append(it)
    return list(groups.values())


def geom_of(group: list[Item], layer) -> object:
    return unary_union([it.geoms[layer] for it in group if layer in it.geoms])


class Grid:
    def __init__(self, bounds, side: str, step: float):
        x0, y0, x1, y1 = bounds
        self.step = step
        self.x0, self.y0 = x0, y0
        self.nx, self.ny = int((x1 - x0) / step) + 1, int((y1 - y0) / step) + 1
        xs = x0 + np.arange(self.nx) * step
        ys = y0 + np.arange(self.ny) * step
        self.X, self.Y = np.meshgrid(xs, ys)
        self.side = side

    def mark(self, geom, out: np.ndarray) -> None:
        if geom.is_empty:
            return
        gx0, gy0, gx1, gy1 = geom.bounds
        g = self.step
        i0, i1 = max(0, int((gx0 - self.x0) / g)), min(self.nx, int((gx1 - self.x0) / g) + 2)
        j0, j1 = max(0, int((gy0 - self.y0) / g)), min(self.ny, int((gy1 - self.y0) / g) + 2)
        if i0 >= i1 or j0 >= j1:
            return
        sub = shapely.contains_xy(geom, self.X[j0:j1, i0:i1], self.Y[j0:j1, i0:i1])
        out[j0:j1, i0:i1] |= sub

    def point(self, j: int, i: int) -> tuple[float, float]:
        return self.x0 + i * self.step, self.y0 + j * self.step


class Index:
    """STRtree over all copper and holes, plus a cache of dilated shapes."""
    def __init__(self, items: list[Item]):
        self.items = items
        self.cache: dict = {}
        self.rebuild()

    def rebuild(self):
        self.geoms, self.refs = [], []
        for it in self.items:
            for l, g in it.geoms.items():
                self.geoms.append(g)
                self.refs.append((it, l))
            if it.hole is not None:
                self.geoms.append(it.hole)
                self.refs.append((it, "hole"))
        self.tree = shapely.STRtree(np.array(self.geoms, dtype=object))

    def add(self, new: list[Item]):
        self.items += new
        self.rebuild()

    def remove(self, gone: list[Item]):
        drop = set(map(id, gone))
        self.items[:] = [it for it in self.items if id(it) not in drop]
        self.rebuild()

    def near(self, area):
        return [self.refs[i] for i in self.tree.query(area)]

    def dilated(self, it: Item, key, d: float):
        k = (id(it), key, round(d, 4))
        if k not in self.cache:
            self.cache[k] = (it.hole if key == "hole" else it.geoms[key]).buffer(d)
        return self.cache[k]


def route_pair(index: "Index", keepouts, net: int, a: list[Item], b: list[Item], width: float,
               step: float, margin: float, side: str, soft_ok: bool = False):
    """A* between islands a and b; with soft_ok, other nets' unlocked tracks and vias may be
    crossed at SOFT_COST per cell (the caller rips them up). Returns [(layer, (x, y))] or None."""
    ga = {l: geom_of(a, l) for l in LAYERS}
    gb = {l: geom_of(b, l) for l in LAYERS}
    # focus on the gap: keep only the copper near the closest points of the two islands
    ua = unary_union([g for g in ga.values() if not g.is_empty])
    ub = unary_union([g for g in gb.values() if not g.is_empty])
    pa, pb = shapely.ops.nearest_points(ua, ub)
    gap = pa.distance(pb)
    focus = LineString([pa, pb]).buffer(gap / 2 + margin) if gap > 0 else pa.buffer(margin)
    ga = {l: g.intersection(focus) for l, g in ga.items()}
    gb = {l: g.intersection(focus) for l, g in gb.items()}
    both = unary_union([g for g in (*ga.values(), *gb.values()) if not g.is_empty])
    x0, y0, x1, y1 = both.bounds
    edge = Polygon(outline_points(side))
    bx0, by0, bx1, by1 = edge.bounds
    grid = Grid((max(bx0, x0 - margin), max(by0, y0 - margin), min(bx1, x1 + margin), min(by1, y1 + margin)),
                side, step)
    if grid.nx < 2 or grid.ny < 2:              # the window lies off the board
        return None
    win = box(grid.x0, grid.y0, grid.x0 + grid.nx * step, grid.y0 + grid.ny * step).buffer(1.0)
    half = width / 2
    quant = QUANT * step                      # covers the grid quantisation of the centre line
    blocked = {l: np.zeros((grid.ny, grid.nx), bool) for l in LAYERS}
    soft = {l: np.zeros((grid.ny, grid.nx), bool) for l in LAYERS}
    via_bad = np.zeros((grid.ny, grid.nx), bool)
    via_soft = np.zeros((grid.ny, grid.nx), bool)
    dear = {l: np.zeros((grid.ny, grid.nx), bool) for l in LAYERS}
    via_dear = np.zeros((grid.ny, grid.nx), bool)
    vr = VIA[0] / 2
    inside = edge.buffer(-(EDGE_CLEARANCE + half))
    for l in LAYERS:
        blocked[l] |= ~shapely.contains_xy(inside, grid.X, grid.Y)
    via_bad |= ~shapely.contains_xy(edge.buffer(-(EDGE_CLEARANCE + vr)), grid.X, grid.Y)
    for it, key in index.near(win):
        if key == "hole":
            ripable = soft_ok and it.ref is not None and it.net != net
            dr = ripable and it.net in PROTECT
            if it.net != net:
                for l in LAYERS:
                    grid.mark(index.dilated(it, key, HOLE_CLEARANCE + half + quant),
                              (dear if dr else soft if ripable else blocked)[l])
            grid.mark(index.dilated(it, key, HOLE_CLEARANCE + vr + quant),
                      via_dear if dr else via_soft if ripable else via_bad)
        elif it.net != net and not it.pour:
            ripable = soft_ok and it.ref is not None
            dr = ripable and it.net in PROTECT
            grid.mark(index.dilated(it, key, CLEARANCE + half + quant), (dear if dr else soft if ripable else blocked)[key])
            grid.mark(index.dilated(it, key, CLEARANCE + vr + quant), via_dear if dr else via_soft if ripable else via_bad)
    penal = {l: np.zeros((grid.ny, grid.nx), bool) for l in LAYERS}
    if soft_ok:
        for n, l, lane in STUB_ENDS:
            if n != net and win.intersects(lane):
                grid.mark(lane.buffer(ESCAPE_R), penal[l])
    for layers, g, no_via in keepouts:
        if g.intersects(win):
            for l in layers:
                grid.mark(g.buffer(half), blocked[l])
            if no_via:
                grid.mark(g.buffer(vr), via_bad)
    start, goal = [], set()
    for k, l in enumerate(LAYERS):
        for src, dst in ((ga, start), (gb, None)):
            g = src[l]
            if g.is_empty:
                continue
            m = np.zeros((grid.ny, grid.nx), bool)
            grid.mark(g, m)
            m &= ~blocked[l]
            cells = np.argwhere(m)
            if dst is None:
                goal |= {(k, int(j), int(i)) for j, i in cells}
            else:
                dst += [(k, int(j), int(i)) for j, i in cells]
    STATS.update(cells=2 * grid.nx * grid.ny, start=len(start), goal=len(goal), pops=0)
    if not start or not goal:
        return None
    gj = np.array([c[1] for c in goal])
    gi = np.array([c[2] for c in goal])
    tj0, tj1, ti0, ti1 = gj.min(), gj.max(), gi.min(), gi.max()

    def h(j, i):
        dj = max(tj0 - j, 0, j - tj1)
        di = max(ti0 - i, 0, i - ti1)
        return max(dj, di) + (math.sqrt(2) - 1) * min(dj, di)
    nyx = grid.ny * grid.nx
    cost = np.full(2 * nyx, np.inf, dtype=np.float32)
    prev = np.full(2 * nyx, -1, dtype=np.int64)
    heap = []
    for k, j, i in start:
        n = k * nyx + j * grid.nx + i
        cost[n] = 0.0
        heapq.heappush(heap, (HEURISTIC * h(j, i), 0.0, n))
    via_cells = VIA_COST / step
    soft_cells = SOFT_COST / step
    sft = [soft[l] & ~blocked[l] for l in LAYERS]
    via_sft = via_soft & ~via_bad
    esc_cells = ESCAPE_COST / step
    dear_cells = PROTECT_COST / step
    dr = [dear[l] & ~blocked[l] for l in LAYERS]
    via_dr = via_dear & ~via_bad
    pen = [penal[l] for l in LAYERS]
    via_pen = penal[LAYERS[0]] | penal[LAYERS[1]]
    pops = 0
    blk = [blocked[l] for l in LAYERS]
    found = None
    while heap:
        f, g0, n = heapq.heappop(heap)
        if g0 > cost[n]:
            continue
        pops += 1
        if pops > MAX_POPS:
            STATS["pops"] = pops
            return None
        k, r = divmod(n, nyx)
        j, i = divmod(r, grid.nx)
        if (k, j, i) in goal:
            found = n
            break
        for dj, di, c in MOVES:
            jj, ii = j + dj, i + di
            if 0 <= jj < grid.ny and 0 <= ii < grid.nx and not blk[k][jj, ii]:
                if dj and di and (blk[k][j, ii] or blk[k][jj, i]):
                    continue                     # no corner cutting
                nn = k * nyx + jj * grid.nx + ii
                ng = (g0 + c + (soft_cells if sft[k][jj, ii] else 0.0) + (esc_cells if pen[k][jj, ii] else 0.0)
                      + (dear_cells if dr[k][jj, ii] else 0.0))
                if ng < cost[nn]:
                    cost[nn] = ng
                    prev[nn] = n
                    heapq.heappush(heap, (ng + HEURISTIC * h(jj, ii), ng, nn))
        if not via_bad[j, i] and not blk[1 - k][j, i]:
            nn = (1 - k) * nyx + j * grid.nx + i
            ng = (g0 + via_cells + (soft_cells if via_sft[j, i] else 0.0) + (esc_cells if via_pen[j, i] else 0.0)
                  + (dear_cells if via_dr[j, i] else 0.0))
            if ng < cost[nn]:
                cost[nn] = ng
                prev[nn] = n
                heapq.heappush(heap, (ng + HEURISTIC * h(j, i), ng, nn))
    STATS["pops"] = pops
    if found is None:
        return None
    path = []
    n = found
    while n != -1:
        k, r = divmod(n, nyx)
        j, i = divmod(r, grid.nx)
        path.append((k, j, i))
        n = int(prev[n])
    path.reverse()
    out = [(LAYERS[k], grid.point(j, i)) for k, j, i in path]
    if len(out) == 1:                            # the islands overlap without a shared anchor:
        layer, p = out[0]                        # join with a stub from an anchor of island a
        anchors = [q for it in a for q in (it.anchors or {}).get(layer, [])]
        if not anchors:
            return None
        q = min(anchors, key=lambda q: math.dist(q, p))
        if not 1e-3 < math.dist(q, p) < 1.0:
            return None
        out = [(layer, q), (layer, p)]
    return out


def emit(board, net_item, path, width: float) -> list[Item]:
    """Path cells -> tracks (collinear runs merged) and vias; returns the new copper."""
    new = []
    run = [path[0]]

    def flush(run):
        if len(run) < 2:
            return
        pts = [run[0][1]]
        for (l0, a), (l1, b), (l2, c) in zip(run, run[1:], run[2:]):
            if (round(b[0] - a[0], 6), round(b[1] - a[1], 6)) != (round(c[0] - b[0], 6), round(c[1] - b[1], 6)):
                pts.append(b)
        pts.append(run[-1][1])
        for p, q in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(pt(*p))
            t.SetEnd(pt(*q))
            t.SetWidth(mm(width))
            t.SetLayer(run[0][0])
            t.SetNet(net_item)
            board.Add(t)
            new.append(Item(net_item.GetNetCode(), {run[0][0]: LineString([p, q]).buffer(width / 2)}, None, t,
                            anchors={run[0][0]: [p, q]}))
    for step in path[1:]:
        if step[0] != run[-1][0]:
            flush(run)
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(pt(*step[1]))
            v.SetWidth(mm(VIA[0]))
            v.SetDrill(mm(VIA[1]))
            v.SetNet(net_item)
            board.Add(v)
            c = Point(step[1])
            new.append(Item(net_item.GetNetCode(), {l: c.buffer(VIA[0] / 2) for l in LAYERS}, c.buffer(VIA[1] / 2), v,
                            anchors={l: [step[1]] for l in LAYERS}))
            run = [step]
        else:
            run.append(step)
    flush(run)
    return new


def pour_copper(board: pcbnew.BOARD) -> list[Item]:
    """Filled GND pours as copper items (for the GND pass after the fill)."""
    out = []
    for z in board.Zones():
        if z.GetIsRuleArea() or not z.IsFilled():
            continue
        for l in LAYERS:
            if z.IsOnLayer(l):
                g = poly(z.GetFilledPolysList(l))
                for part in getattr(g, "geoms", [g]):
                    out.append(Item(z.GetNetCode(), {l: part}, pour=True))
    return out


def width_class(name: str, fanout: set[str]) -> tuple[float, ...]:
    if name in POWER_NETS:
        return WIDTHS["power"]
    return WIDTHS["fanout"] if name in fanout else WIDTHS["default"]


def log(msg: str) -> None:
    print(msg, flush=True)


def complete(board: pcbnew.BOARD, side: str, fanout: set[str], only: tuple[str, ...] | None = None,
             skip: tuple[str, ...] = ("GND",), extra: list[Item] = ()) -> list[str]:
    """Route every remaining island gap (nets in `only`, else all but `skip`); `extra` adds
    copper the board lists elsewhere (filled pours). Returns the nets still open."""
    items, keepouts = collect(board)
    items += list(extra)
    index = Index(items)
    nets = {code: ni for code, ni in board.GetNetsByNetcode().items() if code > 0}
    todo = []
    for code, ni in nets.items():
        name = ni.GetNetname()
        if (only is not None and name not in only) or (only is None and name in skip) or name.startswith("unconnected-"):
            continue
        groups = islands(items, code)
        if len(groups) > 1:
            todo.append((code, ni, len(groups)))
    hard = [code for code, _, _ in sorted(todo, key=lambda t: t[2])]
    soft: list[int] = []                         # nets that failed without ripping anything
    rips: dict[int, int] = {}
    dead: set = set()                            # (island, island, mode) pairs that found no route
    failed, routes = set(), 0
    while (hard or soft) and routes < MAX_ROUTES:
        soft_ok = not hard                       # rip-up only once every clean route is done
        code = (hard or soft).pop(0)
        ni = nets[code]
        name = ni.GetNetname()
        groups = islands(items, code)
        orphans = [it for grp in groups if all(it.ref is not None for it in grp) for it in grp]
        if orphans and len(groups) > 1:          # pieces of a ripped route: delete, not reconnect
            for it in orphans:
                board.Delete(it.ref)
            index.remove(orphans)
            groups = islands(items, code)
        if len(groups) < 2:
            continue
        geoms = [unary_union([g for it in grp for g in it.geoms.values()]) for grp in groups]
        sig = [(round(g.centroid.x, 1), round(g.centroid.y, 1)) for g in geoms]
        pairs = sorted((geoms[i].distance(geoms[j]), i, j) for i in range(len(groups)) for j in range(i + 1, len(groups))
                       if (code, sig[i], sig[j], soft_ok) not in dead)
        path = None
        for _, i, j in pairs[:PAIR_TRIES]:
            if geoms[i].area > geoms[j].area:    # search from the smaller island
                i, j = j, i
            for w in width_class(name, fanout):
                for step, margin in ATTEMPTS:
                    path = route_pair(index, keepouts, code, groups[i], groups[j], w, step, margin, side, soft_ok)
                    if path:
                        break
                if path:
                    break
            if path:
                break
            dead.add((code, sig[min(i, j)], sig[max(i, j)], soft_ok))
            dead.add((code, sig[i], sig[j], soft_ok))
            dead.add((code, sig[j], sig[i], soft_ok))
        if not path:
            if len(pairs) > PAIR_TRIES:          # other island pairs of this net may still route
                (soft if soft_ok else hard).append(code)
            elif SOFT_RIP and not soft_ok and name != "GND":
                soft.append(code)
            else:
                failed.add(name)
                log(f"  FAILED {name}: {len(groups)} islands")
            continue
        new = emit(board, ni, path, w)
        hit = ripped(index, new, code)
        for it in hit:
            board.Delete(it.ref)
        index.remove(hit)
        index.add(new)
        routes += 1
        log(f"  routed {name} ({w} mm, {len(path)} cells{f', ripped {len(hit)}' if hit else ''})")
        hard.insert(0, code)                     # more islands may remain
        for other in {it.net for it in hit}:
            rips[other] = rips.get(other, 0) + 1
            if other not in hard:
                (hard if rips[other] <= MAX_RIPS else soft).append(other)
    failed |= {nets[c].GetNetname() for c in hard + soft}
    return sorted(failed)


def ripped(index: "Index", new: list[Item], net: int) -> list[Item]:
    """Unlocked other-net copper the new route violates (to rip up; complete() deletes the
    orphan pieces this leaves)."""
    hit: list[Item] = []
    seen: set[int] = set()
    for it in new:
        for l, g in it.geoms.items():
            zone = g.buffer(CLEARANCE)
            for other, key in index.near(zone):
                if other.ref is None or other.net == net or id(other) in seen:
                    continue
                og = other.hole if key == "hole" else other.geoms[key] if key == l else None
                if og is not None and og.intersects(zone):
                    hit.append(other)
                    seen.add(id(other))
    return hit


# Copper is taken off the board with BOARD.Delete, not Remove: Remove hands ownership back to the
# Python wrapper, and collecting those wrappers corrupted the board (KiCad 10.0.7 SWIG).

# --- transactional rip-up ------------------------------------------------------------------
# The last few gaps (fan-out stubs boxed in by other nets' autorouted tracks) need a rip-up.
# Unlike SOFT_RIP above, negotiate() keeps a rip-up only when it lowers the open-island count
# of every net it touched together; otherwise the board is restored exactly.
NEGOTIATE_COSTS = (2.0, 8.0, 0.7, 20.0)   # SOFT_COST tries per open net (mm per crossed cell)
NEGOTIATE_ROUNDS = 4
NEGOTIATE_DEPTH = 5          # rip-up levels within one transaction
NEGOTIATE_ATTEMPTS = ((0.1, 8.0), (0.05, 4.0), (0.1, 30.0))
NEGOTIATE_QUANT = 0.1        # tighter grid margin: fan-out stub ends sit 0.3 mm from the next via;
                             # path_clear() then checks the route exactly against fixed copper
NEGOTIATE_MAX_POPS = 6_000_000   # long escapes (a row line back to the matrix) need it
EPS = 1e-4


def snapshot(board: pcbnew.BOARD) -> dict:
    """Unlocked tracks and vias by UUID -> what is needed to recreate them."""
    snap = {}
    for t in board.GetTracks():
        if t.IsLocked():
            continue
        # copy coordinates out: SWIG hands back references into the (soon removed) item
        if t.Type() == pcbnew.PCB_VIA_T:
            p = t.GetPosition()
            rec = ("via", (p.x, p.y), t.GetWidth(pcbnew.F_Cu), t.GetDrillValue(), t.GetNetCode())
        else:
            a, b = t.GetStart(), t.GetEnd()
            rec = ("track", (a.x, a.y), (b.x, b.y), t.GetWidth(), t.GetLayer(), t.GetNetCode())
        snap[t.m_Uuid.AsString()] = rec
    return snap


def restore(board: pcbnew.BOARD, snap: dict) -> None:
    """Undo everything since snapshot(): drop new copper, recreate the ripped copper."""
    nets = board.GetNetsByNetcode()
    have = set()
    for t in list(board.GetTracks()):
        if t.IsLocked():
            continue
        key = t.m_Uuid.AsString()
        if key in snap:
            have.add(key)
        else:
            board.Delete(t)
    for key, rec in snap.items():
        if key in have:
            continue
        if rec[0] == "via":
            _, pos, width, drill, net = rec
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(pcbnew.VECTOR2I(*pos))
            v.SetWidth(width)
            v.SetDrill(drill)
            v.SetNet(nets[net])
            board.Add(v)
        else:
            _, a, b, width, layer, net = rec
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(pcbnew.VECTOR2I(*a))
            t.SetEnd(pcbnew.VECTOR2I(*b))
            t.SetWidth(width)
            t.SetLayer(layer)
            t.SetNet(nets[net])
            board.Add(t)


def open_counts(board: pcbnew.BOARD, codes, extra=()) -> dict[int, int]:
    """Net code -> islands beyond the first."""
    items, _ = collect(board)
    items += list(extra)
    return {c: len(islands(items, c)) - 1 for c in codes}


def path_clear(index: "Index", keepouts, net: int, path, width: float, side: str) -> bool:
    """Exact check of a grid path against what a rip-up cannot move: pads, locked copper, holes,
    keepouts and the edge (unlocked copper it touches is ripped by the caller)."""
    shapes = []                                  # (layers, copper geometry, is_via)
    run = [path[0]]
    for step in path[1:] + [None]:
        if step is None or step[0] != run[-1][0]:
            pts = [p for _, p in run]
            g = LineString(pts) if len(pts) > 1 else Point(pts[0])
            shapes.append(((run[0][0],), g.buffer(width / 2), False))
            if step is not None:
                shapes.append((LAYERS, Point(step[1]).buffer(VIA[0] / 2), True))
                run = [step]
        else:
            run.append(step)
    inside = Polygon(outline_points(side)).buffer(-EDGE_CLEARANCE + EPS)
    for layers, g, is_via in shapes:
        if not inside.contains(g):
            STATS["unclear"] = ("edge", g.centroid.coords[0])
            return False
        for kl, kg, no_via in keepouts:
            if set(kl) & set(layers) and kg.intersects(g) and (no_via or not is_via):
                STATS["unclear"] = ("keepout", g.centroid.coords[0])
                return False
        for it, key in index.near(g.buffer(max(CLEARANCE, HOLE_CLEARANCE))):
            if it.pour or it.net == net and key != "hole":
                continue
            if key == "hole":
                if it.ref is None and it.net != net and g.distance(it.hole) < HOLE_CLEARANCE - EPS:
                    STATS["unclear"] = ("hole", it.hole.centroid.coords[0])
                    return False
            elif it.ref is None and key in layers and g.distance(it.geoms[key]) < CLEARANCE - EPS:
                STATS["unclear"] = ("copper", it.net, round(g.distance(it.geoms[key]), 3),
                                    it.geoms[key].centroid.coords[0])
                return False
    return True


def soft_route(board: pcbnew.BOARD, side: str, fanout: set[str], code: int, cost: float,
               extra=()) -> set[int] | None:
    """Route one island gap of `code` across other nets' unlocked copper and rip that copper
    up. Returns the ripped nets, or None when no route exists even so."""
    global SOFT_COST, QUANT, MAX_POPS
    items, keepouts = collect(board)
    items += list(extra)
    index = Index(items)
    groups = islands(items, code)
    if len(groups) < 2:
        return None
    ni = board.GetNetsByNetcode()[code]
    geoms = [unary_union([g for it in grp for g in it.geoms.values()]) for grp in groups]
    pairs = sorted((geoms[i].distance(geoms[j]), i, j) for i in range(len(groups)) for j in range(i + 1, len(groups)))
    saved, SOFT_COST = (SOFT_COST, QUANT, MAX_POPS), cost
    QUANT, MAX_POPS = NEGOTIATE_QUANT, max(MAX_POPS, NEGOTIATE_MAX_POPS)
    try:
        for _, i, j in pairs[:PAIR_TRIES]:
            if geoms[i].area > geoms[j].area:
                i, j = j, i
            for w in width_class(ni.GetNetname(), fanout):
                for step, margin in NEGOTIATE_ATTEMPTS:
                    path = route_pair(index, keepouts, code, groups[i], groups[j], w, step, margin, side, True)
                    if path and path_clear(index, keepouts, code, path, w, side):
                        new = emit(board, ni, path, w)
                        hit = ripped(index, new, code)
                        for it in hit:
                            board.Delete(it.ref)
                        return {it.net for it in hit}
    finally:
        SOFT_COST, QUANT, MAX_POPS = saved
    return None


def negotiate(board: pcbnew.BOARD, side: str, fanout: set[str], extra_fn=lambda b: [],
              skip: tuple[str, ...] = ()) -> list[str]:
    """Close the remaining gaps by transactional rip-up and reroute; returns the nets still open.
    extra_fn(board) supplies pour copper (filled GND) for the island count."""
    nets = {c: ni for c, ni in board.GetNetsByNetcode().items()
            if c > 0 and not ni.GetNetname().startswith("unconnected-") and ni.GetNetname() not in skip}
    for rnd in range(NEGOTIATE_ROUNDS):
        extra = extra_fn(board)
        base = open_counts(board, nets, extra)
        todo = [c for c, n in base.items() if n]
        if not todo:
            return []
        log(f"  negotiate round {rnd + 1}: {', '.join(nets[c].GetNetname() for c in todo)}")
        progress = False
        for code in todo:
            name = nets[code].GetNetname()
            avoid: set[int] = set()                  # nets whose rip-up failed before: leave them be
            for cost in NEGOTIATE_COSTS * 2:
                if not base[code]:
                    break
                snap = snapshot(board)
                PROTECT.clear()
                PROTECT.update(avoid)
                victims = soft_route(board, side, fanout, code, cost, extra)
                if victims is None:
                    restore(board, snap)
                    PROTECT.clear()
                    if avoid:                        # sparing the stuck nets leaves no route
                        avoid.clear()
                        continue
                    break                            # no route at any cost: next net
                touched = ({code} | victims) & nets.keys()
                PROTECT.add(code)
                fresh = extra
                for _ in range(NEGOTIATE_DEPTH):     # victims that cannot reroute rip in turn
                    complete(board, side, fanout, only=tuple(nets[c].GetNetname() for c in touched),
                             skip=(), extra=fresh)
                    # GND joins through the pours, which the reroutes may have cut: refill
                    gnd = any(nets[c].GetNetname() == "GND" for c in touched)
                    if gnd:
                        fresh = extra_fn(board)
                    counts = open_counts(board, touched, fresh)
                    still = [c for c, n in counts.items() if n]
                    if not still:
                        break
                    for c in still:
                        PROTECT.add(c)
                        more = soft_route(board, side, fanout, c, cost, fresh)
                        touched |= (more or set()) & nets.keys()
                PROTECT.clear()
                gnd = any(nets[c].GetNetname() == "GND" for c in touched)
                fresh = extra_fn(board) if gnd else extra
                after = open_counts(board, nets, fresh)          # every net: a reroute may rip others
                before, now = sum(base.values()), sum(after.values())
                if now < before:
                    base, extra = after, fresh
                    progress = True
                    log(f"  negotiated {name} (cost {cost}, ripped {len(victims)} nets, open {before} -> {now})")
                    break
                stuck = {c for c in touched if after[c] and c != code}
                avoid |= stuck
                restore(board, snap)
                if gnd:
                    extra = extra_fn(board)
                log(f"  rejected {name} at cost {cost} (ripped {len(victims)} nets, open {before} -> {now}; "
                    f"stuck: {', '.join(sorted(nets[c].GetNetname() for c in stuck))})")
        if not progress:
            break
    left = open_counts(board, nets, extra_fn(board))
    return sorted(nets[c].GetNetname() for c, n in left.items() if n)
