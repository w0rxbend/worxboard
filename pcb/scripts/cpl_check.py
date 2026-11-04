# SPDX-License-Identifier: GPL-3.0-or-later
"""Place JLC's own footprint of every CPL row the way JLC does and check it against the KiCad pads.

    python3 pcb/scripts/cpl_check.py [--svg DIR] [--quiet] <board.kicad_pcb> <bom.csv> <cpl.csv> [...]

Runs in the kicad/kicad:10.0.7 container (pcbnew + shapely from pcb/.tools/site313). For every CPL
row it takes the LCSC part of that designator from the BOM, takes JLC's footprint of that part from
pcb/scripts/jlc_footprints.json (the EasyEDA / JLCEDA official-library footprint JLC places by:
origin = CPL centroid, zero orientation = CPL rotation 0), puts it where JLC puts it, and compares it
with the real pads of that footprint on the board (pcbnew, board coordinates, either side).

JLC's placement, as KiKit (MirrorBottom), kicad-jlcpcb-tools and KiBot write it (JLC documents only the
top side: "Mid X/Mid Y = centroid, positive rotation counter-clockwise"):
  top     board point = (Mid X, Mid Y) + Rot(rotation) * p           (p: footprint point, y up)
  bottom  the same in the bottom view, which mirrors x: board = (Mid X, Mid Y) + Mx * Rot(rotation) * p
and CPL y is up from the board's auxiliary origin (KiKit writes -y). Gates, per placed part:
  placement  every point of the footprint lies within 0.1 mm of where the best fit of JLC's footprint
             onto the KiCad footprint puts it. The fit is on the part's locating features when it has
             them (pegs / barrels: USB-C, TRRS jack, hot-swap socket), otherwise on its pads.
  pins       every JLC pad lands nearest the KiCad pad of the same pin (pin 1 on pin 1, cathode on K),
             with the pad names mapped where the two libraries name them differently (PIN_MAP).
  terminals  every terminal of the part (EasyEDA's lead-shape layer: the metal that gets soldered) lies
             on its KiCad pad: SMD terminals with their centre on the pad copper and >= 75 % of their
             area on it; THT pins and shell legs wholly inside their drilled hole.
  body       the part's body outline (EasyEDA's component-shape layer) reaches no more than 0.05 mm into
             any hole of the KiCad footprint that the part does not plug into (the hot-swap socket must
             clear the switch's Ø4 centre post: its notch wraps the post; its outline grazes a Ø1.75 peg
             hole by 0.02 mm, within the drawing's own tolerance).
Land patterns differ between the two libraries (JLC's pads are often longer), so pad-centre offsets
are reported, not gated; the terminal gate is the physical one. --svg writes one overlay per part type.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import pcbnew
from shapely.affinity import affine_transform
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
FOOTPRINTS = HERE / "jlc_footprints.json"
PLACE_TOL = 0.1          # mm, placement gate
LEAD_AREA_MIN = 0.75     # SMD terminal area on its pad
HOLE_TOL = 0.02          # mm, a THT pin may touch its drill wall by rounding
BODY_TOL = 0.05          # mm, a body edge may graze a clearance hole (the socket's at the switch peg: 0.02)
# JLC pad name -> the KiCad pad names it may land on, where the libraries differ (by LCSC number)
PIN_MAP: dict[str, dict[str, set[str]]] = {
    "C165948": {"A1B12": {"A1", "B12"}, "B1A12": {"B1", "A12"}, "A4B9": {"A4", "B9"},
                "B4A9": {"B4", "A9"}, "1": {"SH"}, "2": {"SH"}, "3": {"SH"}, "4": {"SH"}},
    # PJ-320D: EasyEDA numbers the contacts, KiCad names them. With both peg holes aligned the pads
    # coincide as 1 = S (alone on its side), 4 = T, 3 = R1, 2 = R2 (0.1 mm along the axis)
    "C95562": {"1": {"S"}, "2": {"R2"}, "3": {"R1"}, "4": {"T"}},
}


def mm(v) -> tuple[float, float]:
    return (pcbnew.ToMM(v.x), pcbnew.ToMM(v.y))


@dataclass
class KPad:
    num: str
    at: tuple[float, float]
    copper: Polygon | None          # outline on the footprint's copper side
    hole: Polygon | None            # drilled hole (round or slot)
    npth: bool


@dataclass
class KFoot:
    ref: str
    fpid: str
    bottom: bool
    at: tuple[float, float]
    rot: float
    pads: list[KPad] = field(default_factory=list)


def chain_poly(ps) -> Polygon:
    o = ps.Outline(0)
    return Polygon([mm(o.CPoint(i)) for i in range(o.PointCount())])


def board_edge(board):
    """Board outline (Edge.Cuts) as shapely polygons, for the overlay drawings."""
    ps = pcbnew.SHAPE_POLY_SET()
    board.GetBoardPolygonOutlines(ps, True)
    polys = []
    for i in range(ps.OutlineCount()):
        o = ps.Outline(i)
        holes = [ps.Hole(i, j) for j in range(ps.HoleCount(i))]
        polys.append(Polygon([mm(o.CPoint(n)) for n in range(o.PointCount())],
                             [[mm(h.CPoint(n)) for n in range(h.PointCount())] for h in holes]))
    return unary_union(polys)


def load_board(path: str) -> tuple[dict[str, KFoot], tuple[float, float], object]:
    board = pcbnew.LoadBoard(path)
    aux = mm(board.GetDesignSettings().GetAuxOrigin())
    out = {}
    for fp in board.GetFootprints():
        bottom = fp.GetLayer() == pcbnew.B_Cu
        side = pcbnew.B_Cu if bottom else pcbnew.F_Cu
        k = KFoot(fp.GetReference(), str(fp.GetFPID().GetUniStringLibId()), bottom, mm(fp.GetPosition()),
                  fp.GetOrientation().AsDegrees())
        for p in fp.Pads():
            npth = p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH
            copper = None
            if not npth and p.IsOnLayer(side):
                copper = chain_poly(p.GetEffectivePolygon(side, pcbnew.ERROR_INSIDE))
            hole = None
            if p.HasHole():
                h = p.GetEffectiveHoleShape()
                a, b, r = mm(h.GetSeg().A), mm(h.GetSeg().B), pcbnew.ToMM(h.GetWidth()) / 2
                hole = (LineString([a, b]) if a != b else Point(a)).buffer(r, 32)     # slot or round
            if copper is None and hole is None:
                continue                                    # paste-only apertures (U1's exposed pad)
            k.pads.append(KPad(p.GetNumber(), mm(p.GetPosition()), copper, hole, npth))
        out[k.ref] = k
    return out, aux, board_edge(board)


def read_csv(path: str) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return [{(k or "").strip(): (v or "").strip() for k, v in r.items()} for r in csv.DictReader(f)]


def bom_lcsc(path: str) -> dict[str, str]:
    out = {}
    for row in read_csv(path):
        code = row.get("LCSC Part #") or row.get("LCSC") or row.get("JLCPCB Part #") or ""
        for ref in row.get("Designator", "").split(","):
            if ref.strip():
                out[ref.strip()] = code
    return out


@dataclass
class Placement:
    x: float
    y: float
    rot: float
    bottom: bool
    aux: tuple[float, float]

    def matrix(self) -> list[float]:
        """shapely affine [a, b, d, e, xoff, yoff]: footprint (mm, y down) -> board (mm, y down)."""
        c, s = math.cos(math.radians(self.rot)), math.sin(math.radians(self.rot))
        m = -1.0 if self.bottom else 1.0
        # u = (px, -py); v = R u; v.x *= m; board = (aux.x + X + v.x, aux.y - Y - v.y)
        return [m * c, m * s, -s, c, self.aux[0] + self.x, self.aux[1] - self.y]

    def point(self, p) -> tuple[float, float]:
        a, b, d, e, xo, yo = self.matrix()
        return (a * p[0] + b * p[1] + xo, d * p[0] + e * p[1] + yo)


def fit(src: list[tuple[float, float]], dst: list[tuple[float, float]], mirror: bool):
    """Least-squares rigid transform (with a fixed mirror) taking src onto dst -> point function."""
    s = [(x, -y if mirror else y) for x, y in src]
    n = len(s)
    sx, sy = sum(p[0] for p in s) / n, sum(p[1] for p in s) / n
    dx, dy = sum(p[0] for p in dst) / n, sum(p[1] for p in dst) / n
    num = sum((a[0] - sx) * (b[1] - dy) - (a[1] - sy) * (b[0] - dx) for a, b in zip(s, dst))
    den = sum((a[0] - sx) * (b[0] - dx) + (a[1] - sy) * (b[1] - dy) for a, b in zip(s, dst))
    t = math.atan2(num, den) if n > 1 else 0.0
    c, si = math.cos(t), math.sin(t)

    def f(p):
        x, y = p[0] - sx, (-p[1] if mirror else p[1]) - sy
        return (c * x - si * y + dx, si * x + c * y + dy)
    return f


@dataclass
class Result:
    ref: str
    lcsc: str
    package: str
    bottom: bool
    rot: float
    errors: list[str] = field(default_factory=list)
    place_err: float = 0.0
    anchor: str = ""
    pad_offset: float = 0.0          # worst JLC-pad-centre to KiCad-pad-centre (info)
    lead_min_area: float = 1.0
    lead_worst: float = 0.0          # worst terminal-centre to KiCad-pad-centre (info)
    body_clear: float | None = None  # least clearance from the body to a foreign hole wall
    post_clear: float | None = None  # clearance to the largest foreign hole (the switch's centre post)
    placement: Placement | None = None


def names_ok(lcsc: str, jlc: str, kicad: str) -> bool:
    return kicad in PIN_MAP.get(lcsc, {}).get(jlc, {jlc})


def check_part(ref: str, lcsc: str, fp: dict, k: KFoot, pl: Placement) -> Result:
    r = Result(ref, lcsc, fp["package"], pl.bottom, pl.rot)
    if pl.bottom != k.bottom:
        r.errors.append(f"CPL layer {'B' if pl.bottom else 'T'}, board {'B.Cu' if k.bottom else 'F.Cu'}")
        return r
    A = pl.matrix()
    kcu = [p for p in k.pads if p.copper is not None]
    kholes = [p for p in k.pads if p.hole is not None]
    # placement: fit on locating holes (NPTH pegs, barrels), else THT pins, else SMD pads
    jholes = [h["at"] for h in fp["holes"]]
    jtht = [p for p in fp["pads"] if p["hole"] > 0]
    src, dst = [], []
    if jholes or jtht:
        feats = jholes if jholes else [p["at"] for p in jtht]
        r.anchor = "pegs/barrels" if jholes else "THT pins"
        for q in feats:
            b = pl.point(q)
            near = min(kholes, key=lambda p: math.dist(b, p.at), default=None)
            if near is None:
                r.errors.append("the KiCad footprint has no hole for JLC's locating feature")
                return r
            src.append(q)
            dst.append(near.at)
    else:
        r.anchor = "pads"
        for q in fp["pads"]:
            b = pl.point(q["at"])
            cands = [p for p in kcu if names_ok(lcsc, q["num"], p.num)]
            if not cands:
                r.errors.append(f"JLC pad {q['num']} has no KiCad pad of that pin")
                return r
            src.append(q["at"])
            dst.append(min(cands, key=lambda p: math.dist(b, p.at)).at)
    best = fit(src, dst, pl.bottom)
    pts = [p["at"] for p in fp["pads"]] + jholes
    r.place_err = max(math.dist(pl.point(q), best(q)) for q in pts)
    if r.place_err > PLACE_TOL:
        r.errors.append(f"placement {r.place_err:.3f} mm off the best fit on its {r.anchor} (> {PLACE_TOL})")
    # pins: the nearest KiCad copper pad of every JLC pad carries the same pin
    for q in fp["pads"]:
        b = pl.point(q["at"])
        near = min(kcu, key=lambda p: math.dist(b, p.at))
        same = [p for p in kcu if names_ok(lcsc, q["num"], p.num)]
        if not names_ok(lcsc, q["num"], near.num):
            r.errors.append(f"JLC pin {q['num']} lands on KiCad pad {near.num} ({math.dist(b, near.at):.2f} mm)")
        elif same:
            r.pad_offset = max(r.pad_offset, min(math.dist(b, p.at) for p in same))
    # terminals
    jpads = [(q, Polygon(q["poly"])) for q in fp["pads"]]
    cut = unary_union([Polygon(c) for c in fp["lead_cutouts"]]) if fp["lead_cutouts"] else None
    for lead in fp["leads"]:
        lp = Polygon(lead)
        if cut is not None:
            lp = lp.difference(cut)
        if lp.is_empty or lp.area < 1e-6:
            continue
        c = lp.centroid
        owner = min(jpads, key=lambda qp: qp[1].distance(c))[0]
        placed = affine_transform(lp, A)
        pc = placed.centroid
        cands = [p for p in k.pads if names_ok(lcsc, owner["num"], p.num) and (p.copper or p.hole)]
        if not cands:
            r.errors.append(f"terminal of JLC pin {owner['num']}: no KiCad pad of that pin")
            continue
        kp = min(cands, key=lambda p: math.dist((pc.x, pc.y), p.at))
        r.lead_worst = max(r.lead_worst, math.dist((pc.x, pc.y), kp.at))
        if owner["hole"] > 0:
            if kp.hole is None:
                r.errors.append(f"THT pin {owner['num']}: KiCad pad {kp.num} has no hole")
                continue
            out = placed.difference(kp.hole.buffer(HOLE_TOL)).area
            if out > 1e-4:
                r.errors.append(f"THT pin {owner['num']} is {out:.3f} mm2 outside the hole of KiCad pad {kp.num}")
        else:
            if kp.copper is None:
                r.errors.append(f"terminal {owner['num']}: KiCad pad {kp.num} has no copper on this side")
                continue
            frac = placed.intersection(kp.copper).area / placed.area
            r.lead_min_area = min(r.lead_min_area, frac)
            if not kp.copper.contains(pc) or frac < LEAD_AREA_MIN:
                r.errors.append(f"terminal {owner['num']} {frac:.0%} on KiCad pad {kp.num}, centre "
                                f"{'on' if kp.copper.contains(pc) else 'off'} the pad")
    # body: clear of every hole of the footprint the part does not plug into
    if fp["body"]:
        body = unary_union([Polygon(b).buffer(0) for b in fp["body"]])
        placed = affine_transform(body, A)
        used = {id(min(kholes, key=lambda p: math.dist(pl.point(q), p.at))) for q in jholes + [p["at"] for p in jtht]}
        foreign = sorted((p for p in kholes if id(p) not in used and p.npth), key=lambda p: -p.hole.area)
        for p in foreign:
            # clearance from the body to the hole wall; negative = the body reaches into the hole
            radius = (p.hole.bounds[2] - p.hole.bounds[0]) / 2
            d = placed.distance(Point(p.at)) - radius if not placed.contains(Point(p.at)) else -radius
            r.body_clear = d if r.body_clear is None else min(r.body_clear, d)
            if r.post_clear is None:
                r.post_clear = d
            if d < -BODY_TOL:
                r.errors.append(f"body reaches {-d:.2f} mm into the KiCad hole (d {2 * radius:.2f} mm) at "
                                f"({p.at[0]:.2f}, {p.at[1]:.2f})")
    return r


def check_cpl(board_path: str, bom_path: str, cpl_path: str, fps: dict, quiet: bool):
    """Check one board's CPL -> (errors, results, board, aux)."""
    board, aux, edge = load_board(board_path)
    bom = bom_lcsc(bom_path)
    errors, results, seen = [], [], set()
    for row in read_csv(cpl_path):
        ref = row["Designator"]
        seen.add(ref)
        lcsc = bom.get(ref)
        if not lcsc:
            errors.append(f"{ref}: in the CPL, not in the BOM")
            continue
        if lcsc not in fps:
            errors.append(f"{ref}: no JLC footprint for {lcsc} in {FOOTPRINTS.name} (run jlc_footprints.py)")
            continue
        if ref not in board:
            errors.append(f"{ref}: not on {board_path}")
            continue
        layer = row["Layer"].strip().lower()
        if layer not in ("t", "b", "top", "bottom"):
            errors.append(f"{ref}: layer {row['Layer']!r}")
            continue
        pl = Placement(float(row["Mid X"]), float(row["Mid Y"]), float(row["Rotation"]), layer[0] == "b", aux)
        res = check_part(ref, lcsc, fps[lcsc], board[ref], pl)
        res.placement = pl
        results.append(res)
        errors += [f"{ref} ({lcsc} {res.package}, {'B' if res.bottom else 'T'} {res.rot:g}): {e}" for e in res.errors]
    errors += [f"{ref}: in the BOM, not in the CPL" for ref in sorted(set(bom) - seen)]
    if not quiet:
        summary = defaultdict(list)
        for res in results:
            summary[(res.lcsc, res.package)].append(res)
        print(f"{'LCSC':10} {'JLC footprint':36} {'n':>3} {'side/rot':18} {'place':>6} {'anchor':12} "
              f"{'pads':>5} {'term':>5} {'area':>5} {'body':>6} {'post':>5}")
        for (lcsc, pkg), rs in sorted(summary.items(), key=lambda kv: kv[1][0].ref):
            rots = sorted({f"{'B' if x.bottom else 'T'}{x.rot:g}" for x in rs})
            bc = [x.body_clear for x in rs if x.body_clear is not None]
            pc = [x.post_clear for x in rs if x.post_clear is not None]
            print(f"{lcsc:10} {pkg[:36]:36} {len(rs):3} {','.join(rots)[:18]:18} "
                  f"{max(x.place_err for x in rs):6.3f} {rs[0].anchor:12} {max(x.pad_offset for x in rs):5.2f} "
                  f"{max(x.lead_worst for x in rs):5.2f} {min(x.lead_min_area for x in rs):5.0%} "
                  f"{(f'{min(bc):6.3f}' if bc else '     -')} {(f'{min(pc):5.2f}' if pc else '    -')}")
    for e in errors:
        print(f"FAIL  {e}")
    bad = sum(1 for r in results if r.errors)
    print(f"cpl_check {cpl_path} on {board_path}: {len(results)} parts placed, {len(results) - bad} pass, "
          f"{len(errors)} errors")
    return errors, results, board, edge


def main(argv: list[str]) -> int:
    svg, quiet, pos = None, False, []
    it = iter(argv)
    for a in it:
        if a == "--svg":
            svg = next(it)
        elif a == "--quiet":
            quiet = True
        else:
            pos.append(a)
    if not pos or len(pos) % 3:
        print(__doc__)
        return 2
    fps = json.loads(FOOTPRINTS.read_text())
    failed, tiles = False, []
    for i in range(0, len(pos), 3):
        errors, results, board, edge = check_cpl(pos[i], pos[i + 1], pos[i + 2], fps, quiet)
        failed |= bool(errors)
        tiles.append((Path(pos[i]).stem, results, board, edge))
    if svg:
        sys.path.insert(0, str(HERE))
        import cpl_svg
        for name in cpl_svg.write_all(Path(svg), tiles, fps):
            print(f"wrote {name}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
