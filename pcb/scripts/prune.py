# SPDX-License-Identifier: GPL-3.0-or-later
"""Clean up the dangling copper routing leaves behind (spec §9 stage 11).

    python3 pcb/scripts/prune.py <side>      (edits pcb/<side>/worxboard-<side>.kicad_pcb)

The rip-up of complete_routes.negotiate() cuts other nets' routes and reroutes them, and Freerouting
runs some segments past the point where the rest of their net joins them. KiCad's DRC reports what
is left as `track_dangling` and `via_dangling` warnings (docs/deviations.md BOARD-4). Each round runs
the DRC and, for every unlocked item it names:

- deletes it if its net keeps its island count without it (a stub), then whatever that deletion
  leaves loose;
- else, for a track with one loose end, cuts the segment back to the last point where copper of its
  net joins it (an overhang);
- else, for a via that joins copper on one layer only, replaces it by short tracks on that layer from
  its centre to each track end it held;
- else, for a track whose end lies part-way along another unlocked track of its net (a T junction),
  splits that track at the junction. KiCad's dangling test credits a track that one end of a short
  segment hits to whichever end lies nearer that track's own ends, so a short jog whose end meets
  a long track part-way is called dangling although both ends are joined; with the long track split
  there, its new end lies on the junction and the test credits the right end.

Every change is kept only if the item's net keeps its island count, and the pours are refilled after
each round. Locked copper (fan-out, USB pair, matrix) is never touched; it lists what it left. If
unlocked copper is still dangling after the last round, it exits 1 (deviations BOARD-14); the DRC gate
that follows in stage_c.sh judges the rest.
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pcbnew  # noqa: E402
from shapely.geometry import LineString, Point  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

import complete_routes  # noqa: E402
from complete_routes import LAYERS, VIA, Item, islands, xy  # noqa: E402
from place import mm, pt, seed_kiids  # noqa: E402

DANGLING = ("track_dangling", "via_dangling")
MAX_ROUNDS = 30             # the right needs 11 (a chain of stubs goes a few items per round)
EPS = 1e-4                   # mm: an anchor this close to copper touches it
MIN_TRIM = 0.01              # mm: shorter overhangs are left alone
JOIN_TOL = 1e-3              # mm: a via-replacing join may pass the copper it replaces by this much
                             # (the polygons of two equal round caps differ by slivers ~1e-5 mm2)
JOIN_WIDTHS = (0.4, 0.3, 0.25, 0.2, 0.15)   # mm: narrower joins tried when the track's own width pokes out


def dangling(pcb: Path, report: Path) -> list[str]:
    """UUIDs of the items the DRC calls dangling, in report order."""
    subprocess.run(["kicad-cli", "pcb", "drc", "--severity-warning", "--format", "json", "-o", str(report),
                    str(pcb)], check=True, stdout=subprocess.DEVNULL)
    data = json.loads(report.read_text())
    out = []
    for v in data["violations"]:
        if v["type"] in DANGLING:
            out += [it["uuid"] for it in v["items"] if it["uuid"] not in out]
    return out


def touches(x: Item, layer, p) -> bool:
    g = x.geoms.get(layer)
    return g is not None and g.distance(Point(p)) < EPS


def loose_ends(items: list[Item], it: Item) -> list[tuple[float, float]]:
    """The ends of track `it` that lie in no other copper of its net on its layer."""
    (layer, ends), = it.anchors.items()
    mine = [x for x in items if x.net == it.net and x is not it]
    return [p for p in ends if not any(touches(x, layer, p) for x in mine)]


def via_layers(items: list[Item], it: Item) -> list:
    """The layers on which copper of its net joins via `it` (KiCad: a track end in the via, the via
    centre in a pad, or a pour over the via)."""
    c = it.anchors[LAYERS[0]][0]
    disc = Point(c).buffer(VIA[0] / 2)
    out = []
    for layer in LAYERS:
        for x in items:
            if x.net != it.net or x is it or layer not in x.geoms:
                continue
            if x.pour:
                hit = x.geoms[layer].intersects(disc)
            elif x.pad:
                hit = touches(x, layer, c)
            else:
                hit = any(disc.distance(Point(q)) < EPS for q in x.anchors.get(layer, []))
            if hit:
                out.append(layer)
                break
    return out


def loose(items: list[Item], it: Item) -> bool:
    """KiCad's dangling test on our copper model."""
    return bool(loose_ends(items, it)) if len(it.geoms) == 1 else len(via_layers(items, it)) < 2


def track_item(t: pcbnew.PCB_TRACK) -> Item:
    a, b = xy(t.GetStart()), xy(t.GetEnd())
    return Item(t.GetNetCode(), {t.GetLayer(): LineString([a, b]).buffer(pcbnew.ToMM(t.GetWidth()) / 2)}, None, t,
                anchors={t.GetLayer(): [a, b]})


def _coords(geom) -> list[tuple[float, float]]:
    if hasattr(geom, "geoms"):
        return [q for g in geom.geoms for q in _coords(g)]
    return list(geom.coords)


class Cleaner:
    def __init__(self, board: pcbnew.BOARD):
        self.board = board
        self.items, _ = complete_routes.collect(board)
        self.items += complete_routes.pour_copper(board)
        self.deleted = self.trimmed = self.merged = self.split_n = 0

    @staticmethod
    def same_islands(before: list[Item], after: list[Item], net: int) -> bool:
        return len(islands(after, net)) <= len(islands(before, net))

    def drop(self, it: Item) -> bool:
        rest = [x for x in self.items if x is not it]
        if not self.same_islands(self.items, rest, it.net):
            return False                                # it still joins two pieces of its net
        self.board.Delete(it.ref)
        self.items = rest
        self.deleted += 1
        return True

    def trim(self, it: Item) -> bool:
        """Cut a track with one loose end back to the furthest point where its net joins it."""
        free_end = loose_ends(self.items, it)
        (layer, (a, b)), = it.anchors.items()
        if len(free_end) != 1:
            return False
        fixed, free = (a, b) if free_end[0] == b else (b, a)
        seg = LineString([fixed, free])
        half = pcbnew.ToMM(it.ref.GetWidth()) / 2
        reach = 0.0
        for x in self.items:
            if x.net != it.net or x is it or layer not in x.geoms:
                continue
            if x.pour or x.pad:
                hit = x.geoms[layer].intersection(seg)
                if not hit.is_empty:
                    reach = max(reach, max(seg.project(Point(q)) for q in _coords(hit)))
            else:
                for q in x.anchors.get(layer, []):
                    if seg.distance(Point(q)) <= half + EPS:
                        reach = max(reach, seg.project(Point(q)))
        if seg.length - reach < MIN_TRIM or reach < EPS:
            return False
        end = seg.interpolate(reach).coords[0]
        t = it.ref
        s0, e0 = t.GetStart(), t.GetEnd()
        old = (pcbnew.VECTOR2I(s0.x, s0.y), pcbnew.VECTOR2I(e0.x, e0.y))
        if free == b:
            t.SetEnd(pt(*end))
        else:
            t.SetStart(pt(*end))
        new = track_item(t)
        rest = [x for x in self.items if x is not it] + [new]
        if not self.same_islands(self.items, rest, it.net) or not self.joined_at(rest, new, end, half):
            t.SetStart(old[0])
            t.SetEnd(old[1])
            return False
        self.items = rest
        self.trimmed += 1
        return True

    @staticmethod
    def joined_at(items: list[Item], it: Item, p, half: float) -> bool:
        """KiCad's dangling test for one end of a track: other copper of its net on its layer lies
        within the track's half width of the end (CONNECTIVITY_DATA::TestTrackEndpointDangling)."""
        (layer, _), = it.anchors.items()
        q = Point(p)
        return any(x.geoms[layer].distance(q) <= half for x in items
                   if x.net == it.net and x is not it and layer in x.geoms)

    def split(self, it: Item) -> bool:
        """Split each unlocked track of its net that an end of track `it` meets part-way."""
        (layer, ends), = it.anchors.items()
        done = False
        for p in ends:
            q = Point(p)
            for x in list(self.items):
                if (x.net != it.net or x is it or x.ref is None or x.pour or x.pad or len(x.geoms) != 1
                        or layer not in x.geoms or x.geoms[layer].distance(q) > EPS):
                    continue
                a, b = x.anchors[layer]
                seg = LineString([a, b])
                s = seg.project(q)
                if s < MIN_TRIM or seg.length - s < MIN_TRIM:
                    continue                              # meets it at an end already
                m = seg.interpolate(s).coords[0]
                t = x.ref
                u = pcbnew.PCB_TRACK(self.board)
                u.SetStart(pt(*m))
                u.SetEnd(t.GetEnd())
                u.SetWidth(t.GetWidth())
                u.SetLayer(t.GetLayer())
                u.SetNet(t.GetNet())
                t.SetEnd(pt(*m))
                self.board.Add(u)
                self.items = [y for y in self.items if y is not x] + [track_item(t), track_item(u)]
                done = True
        if done:
            self.split_n += 1
        return done

    def merge(self, it: Item) -> bool:
        """Replace a via that joins copper on one layer only by tracks on that layer from its centre
        to each track end it held."""
        layers = via_layers(self.items, it)
        if len(layers) != 1:
            return False
        layer = layers[0]
        c = it.anchors[LAYERS[0]][0]
        disc = Point(c).buffer(VIA[0] / 2)
        ends, held = [], [disc]
        for x in self.items:
            if x.net == it.net and x is not it and x.ref is not None and len(x.geoms) == 1 and layer in x.geoms:
                for q in x.anchors[layer]:
                    if disc.distance(Point(q)) < EPS and math.dist(q, c) > EPS:
                        ends.append((q, pcbnew.ToMM(x.ref.GetWidth())))
                        held.append(x.geoms[layer])
        # the joins must stay inside the via and the tracks it held, so no clearance can shrink: a join
        # to an end off the held track's axis is narrowed through JOIN_WIDTHS until it fits
        inside = unary_union(held).buffer(JOIN_TOL)
        fitted = []
        for q, w in ends:
            widths = [w] + [x for x in JOIN_WIDTHS if x < w]
            fit = next((x for x in widths if LineString([c, q]).buffer(x / 2).difference(inside).area <= 1e-6), None)
            if fit is None:
                return False
            fitted.append((q, fit))
        ends = fitted
        net = it.ref.GetNet()
        self.board.Delete(it.ref)
        rest = [x for x in self.items if x is not it]
        added = []
        for q, w in ends:
            t = pcbnew.PCB_TRACK(self.board)
            t.SetStart(pt(*c))
            t.SetEnd(pt(*q))
            t.SetWidth(mm(w))
            t.SetLayer(layer)
            t.SetNet(net)
            self.board.Add(t)
            added.append(t)
            rest.append(track_item(t))
        if self.same_islands(self.items, rest, it.net):
            self.items = rest
            self.merged += 1
            return True
        for t in added:                                 # put the via back
            self.board.Delete(t)
        v = pcbnew.PCB_VIA(self.board)
        v.SetPosition(pt(*c))
        v.SetWidth(mm(VIA[0]))
        v.SetDrill(mm(VIA[1]))
        v.SetNet(net)
        self.board.Add(v)
        it.ref = v
        return False

    def run(self, uuids: list[str]) -> list[str]:
        """Clean the items of `uuids`; returns what was left."""
        by_uuid = {it.ref.m_Uuid.AsString(): it for it in self.items if it.ref is not None}
        tracks = {t.m_Uuid.AsString(): t for t in self.board.GetTracks()}
        kept, gone = [], []
        for u in uuids:
            it = by_uuid.get(u)
            if it is None:                              # locked (or not copper): leave it
                t = tracks.get(u)
                kept.append(f"locked {t.GetNetname()} at {xy(t.GetPosition())}" if t else u)
            elif self.drop(it):
                gone.append(it)
            elif not (self.trim(it) or self.split(it) if len(it.geoms) == 1 else self.merge(it)):
                kept.append(f"needed {it.ref.GetNetname()} at {xy(it.ref.GetPosition())}")
        while gone:                                     # what the deleted items touched may dangle now
            near = {id(x): x for g in gone for x in self.items
                    if x.net == g.net and x.ref is not None and not x.pour
                    and any(x.geoms[l].distance(g.geoms[l]) < EPS for l in x.geoms if l in g.geoms)}
            gone = [x for x in near.values() if loose(self.items, x) and self.drop(x)]
        return kept


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in ("left", "right"):
        print(__doc__)
        return 2
    side = argv[1]
    pcb = ROOT / "pcb" / side / f"worxboard-{side}.kicad_pcb"
    report = ROOT / "build" / side / "drc-dangling.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    totals = [0, 0, 0, 0]
    kept: list[str] = []
    for rnd in range(MAX_ROUNDS):
        uuids = dangling(pcb, report)
        if not uuids:
            kept = []
            break
        seed_kiids(side, b"prune", str(rnd).encode(), pcb.read_bytes())    # merge() adds tracks
        board = pcbnew.LoadBoard(str(pcb))
        c = Cleaner(board)
        kept = c.run(uuids)
        if not (c.deleted or c.trimmed or c.merged or c.split_n):
            break
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
        board.Save(str(pcb))
        totals = [a + b for a, b in zip(totals, (c.deleted, c.trimmed, c.merged, c.split_n))]
        print(f"{side}: prune round {rnd + 1}: deleted {c.deleted}, trimmed {c.trimmed}, vias merged {c.merged}, "
              f"T junctions split {c.split_n}")
    print(f"{side}: dangling copper: {totals[0]} items deleted, {totals[1]} tracks trimmed, "
          f"{totals[2]} one-layer vias replaced, {totals[3]} T junctions split; left {len(kept)}: "
          f"{'; '.join(kept) or 'none'}")
    needed = [k for k in kept if k.startswith("needed")]
    if needed:
        print(f"{side}: {len(needed)} unlocked items still dangling")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
