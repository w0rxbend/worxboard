# SPDX-License-Identifier: GPL-3.0-or-later
"""Finish the connections Freerouting left open (spec §9 stage 10, after the session import).

A small two-layer maze router: for every net still split into islands it rasterises, on a fine
grid around the gap (ATTEMPTS), all other-net copper, holes, keepouts and the board edge (dilated by the
track half-width + the clearance + a grid margin), then runs A* with 45 deg moves and vias between the
islands. Routes are written as ordinary (unlocked) tracks and vias; DRC is the judge afterwards.

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
SOFT_COST = 3.0              # mm of track that crossing a rippable track costs, per grid cell
MAX_RIP_CHAIN = 80           # items ripped with one route at most
MAX_RIPS = 6                 # times one net may be ripped up
MAX_ROUTES = 400
HEURISTIC = 1.3              # A* weight (> 1: faster, slightly longer routes)
WIDTHS = {"power": (0.5, 0.25), "fanout": (0.15,), "default": (0.25, 0.15)}
LAYERS = (pcbnew.F_Cu, pcbnew.B_Cu)
STATS: dict = {}             # last route_pair call: grid cells, start / goal cells, expansions
MOVES = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
         (1, 1, math.sqrt(2)), (1, -1, math.sqrt(2)), (-1, 1, math.sqrt(2)), (-1, -1, math.sqrt(2))]


@dataclass(eq=False)
class Item:
    net: int
    geoms: dict                  # layer -> shapely geometry (copper)
    hole: object = None          # drilled hole (shapely), any net
    ref: object = None           # the unlocked board track / via (may be ripped up)


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
                              None if t.IsLocked() else t))
        else:
            seg = LineString([xy(t.GetStart()), xy(t.GetEnd())]).buffer(pcbnew.ToMM(t.GetWidth()) / 2)
            items.append(Item(t.GetNetCode(), {t.GetLayer(): seg}, None, None if t.IsLocked() else t))
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            geoms = {l: poly(pad.GetEffectivePolygon(l, pcbnew.ERROR_OUTSIDE)) for l in LAYERS if pad.IsOnLayer(l)}
            hole = None
            if pad.HasHole():
                d = max(pcbnew.ToMM(pad.GetDrillSize().x), pcbnew.ToMM(pad.GetDrillSize().y))
                hole = Point(xy(pad.GetPosition())).buffer(d / 2)
            if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                geoms = {}
            items.append(Item(pad.GetNetCode() if geoms else -1, geoms, hole))
    for z in board.Zones():
        if z.GetIsRuleArea() and z.GetDoNotAllowTracks():
            keepouts.append(([l for l in LAYERS if z.IsOnLayer(l)], poly(z.Outline()), z.GetDoNotAllowVias()))
    return items, keepouts


def islands(items: list[Item], net: int) -> list[list[Item]]:
    """Copper of one net grouped into electrically joined islands (overlap on a layer)."""
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
        for a, b in zip(*tree.query(geoms, predicate="intersects")):
            parent[find(idx[a])] = find(idx[b])
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
    win = box(grid.x0, grid.y0, grid.x0 + grid.nx * step, grid.y0 + grid.ny * step).buffer(1.0)
    half = width / 2
    quant = 0.6 * step                        # covers the grid quantisation of the centre line
    blocked = {l: np.zeros((grid.ny, grid.nx), bool) for l in LAYERS}
    soft = {l: np.zeros((grid.ny, grid.nx), bool) for l in LAYERS}
    via_bad = np.zeros((grid.ny, grid.nx), bool)
    via_soft = np.zeros((grid.ny, grid.nx), bool)
    vr = VIA[0] / 2
    inside = edge.buffer(-(EDGE_CLEARANCE + half))
    for l in LAYERS:
        blocked[l] |= ~shapely.contains_xy(inside, grid.X, grid.Y)
    via_bad |= ~shapely.contains_xy(edge.buffer(-(EDGE_CLEARANCE + vr)), grid.X, grid.Y)
    for it, key in index.near(win):
        if key == "hole":
            if it.net != net:
                for l in LAYERS:
                    grid.mark(index.dilated(it, key, HOLE_CLEARANCE + half + quant), blocked[l])
            grid.mark(index.dilated(it, key, HOLE_CLEARANCE + vr + quant), via_bad)
        elif it.net != net:
            ripable = soft_ok and it.ref is not None
            grid.mark(index.dilated(it, key, CLEARANCE + half + quant), (soft if ripable else blocked)[key])
            grid.mark(index.dilated(it, key, CLEARANCE + vr + quant), via_soft if ripable else via_bad)
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
                ng = g0 + c + (soft_cells if sft[k][jj, ii] else 0.0)
                if ng < cost[nn]:
                    cost[nn] = ng
                    prev[nn] = n
                    heapq.heappush(heap, (ng + HEURISTIC * h(jj, ii), ng, nn))
        if not via_bad[j, i] and not blk[1 - k][j, i]:
            nn = (1 - k) * nyx + j * grid.nx + i
            ng = g0 + via_cells + (soft_cells if via_sft[j, i] else 0.0)
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
    return [(LAYERS[k], grid.point(j, i)) for k, j, i in path]


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
            new.append(Item(net_item.GetNetCode(), {run[0][0]: LineString([p, q]).buffer(width / 2)}, None, t))
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
            new.append(Item(net_item.GetNetCode(), {l: c.buffer(VIA[0] / 2) for l in LAYERS}, c.buffer(VIA[1] / 2), v))
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
                    out.append(Item(z.GetNetCode(), {l: part}))
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
    queue = [code for code, _, _ in sorted(todo, key=lambda t: t[2])]
    rips: dict[int, int] = {}
    failed, routes = set(), 0
    while queue and routes < MAX_ROUTES:
        code = queue.pop(0)
        ni = nets[code]
        name = ni.GetNetname()
        groups = islands(items, code)
        if len(groups) < 2:
            continue
        geoms = [unary_union([g for it in grp for g in it.geoms.values()]) for grp in groups]
        pairs = sorted((geoms[i].distance(geoms[j]), i, j) for i in range(len(groups)) for j in range(i + 1, len(groups)))
        path = None
        for soft_ok in (False, True):
            for _, i, j in pairs[:3]:
                if geoms[i].area > geoms[j].area:     # search from the smaller island
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
            if path or name == "GND":
                break
        if not path:
            failed.add(name)
            log(f"  FAILED {name}: {len(groups)} islands")
            continue
        new = emit(board, ni, path, w)
        hit = ripped(index, new, code)
        for it in hit:
            board.Remove(it.ref)
        index.remove(hit)
        index.add(new)
        routes += 1
        log(f"  routed {name} ({w} mm, {len(path)} cells{f', ripped {len(hit)}' if hit else ''})")
        queue.append(code)                       # more islands may remain
        for other in {it.net for it in hit}:
            rips[other] = rips.get(other, 0) + 1
            if rips[other] <= MAX_RIPS and other not in queue:
                queue.append(other)
    failed |= {nets[c].GetNetname() for c in queue}
    return sorted(failed)


def ripped(index: "Index", new: list[Item], net: int) -> list[Item]:
    """Unlocked other-net copper the new route violates, extended to the whole unlocked chain
    each hit belongs to (so no orphan pieces of a ripped route stay behind)."""
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
    i = 0
    while i < len(hit) and len(hit) < MAX_RIP_CHAIN:   # grow along the hit net's unlocked copper
        it = hit[i]
        i += 1
        for l, g in it.geoms.items():
            for other, key in index.near(g):
                if key != l or other.ref is None or other.net != it.net or id(other) in seen:
                    continue
                if other.geoms[l].intersects(g):
                    hit.append(other)
                    seen.add(id(other))
    return hit
