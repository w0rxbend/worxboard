# SPDX-License-Identifier: GPL-3.0-or-later
"""JLC readiness of one half's order package (pcb/production/<side>/), and the panel facts it states.

    python3 pcb/scripts/jlc_check.py check <side> <package dir> [--panel P.kicad_pcb] [--stock N]
    python3 pcb/scripts/jlc_check.py facts <panel.kicad_pcb> <board.kicad_pcb> <panel kikit dir> <drc.json> <out.json>

`check` (stdlib + design.py; pcbnew only with --panel) fails on:
  - files: gerbers.zip, bom.csv, cpl.csv, README.md and worxboard-<side>-jlc-order.zip (holding exactly
    those four, byte-identical), and bare-board/ with its own gerbers.zip, bom.csv, cpl.csv, README.md
  - gerbers.zip: exactly the 9 Gerber layers and the PTH / NPTH drill files, no KiCad creation date
  - bom.csv: header exactly Comment,Designator,Footprint,LCSC Part #; an LCSC number (C + digits) on every
    line; no designator twice; at most 200 designators per line (JLC's limit)
  - cpl.csv: header exactly Designator,Mid X,Mid Y,Layer,Rotation; Layer Top or Bottom; numbers in mm;
    rotation 0-360; every placement inside the board outline
  - BOM and CPL list the same designators, and exactly the parts design.py has JLC fit, each with
    design.py's LCSC number: nothing not fitted on purpose (JP1, TP*, H*, STAB_*) and nothing missing
  - size: JLC Standard PCBA, a panel 70 x 70 to 250 x 250 mm, a single board 70 x 70 to 460 x 500 mm
  - --panel: 3 fiducials per side (1 mm copper, 2 mm opening, centre >= 3.85 mm from the panel edges),
    4 NPTH tooling holes on the rails, rails >= 5 mm
  - --stock N (network): every LCSC number in stock at JLC for N boards per half on both halves plus
    JLC's attrition, not discontinued (tests/integration/stock.py's rules). CI does not run it.
`facts` measures the panel for the README (package.py), and fails if two pad holes leave less than
HOLE_GAP of board between them anywhere but between two stabiliser footprints (STAB_*: non-plated
clearance holes, named in the README's remark; deviations ORDER-3).
"""
from __future__ import annotations

import csv
import io
import json
import math
import re
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))

BOM_HEADER = ["Comment", "Designator", "Footprint", "LCSC Part #"]
CPL_HEADER = ["Designator", "Mid X", "Mid Y", "Layer", "Rotation"]
GERBER_SUFFIXES = ["-CuTop.gtl", "-CuBottom.gbl", "-MaskTop.gts", "-MaskBottom.gbs", "-SilkTop.gto",
                   "-SilkBottom.gbo", "-PasteTop.gtp", "-PasteBottom.gbp", "-EdgeCuts.gm1", "-PTH.drl",
                   "-NPTH.drl"]
PANEL_LIMIT = (70.0, 250.0)          # JLC Standard PCBA panel, mm (capabilities page)
SINGLE_LIMIT = ((70.0, 70.0), (460.0, 500.0))
FID_EDGE_MIN = 3.85
RAIL_MIN = 5.0
BITE_CLEAR = 1.0                     # mm from a mouse-bite hole to any part's courtyard
HOLE_GAP = 0.45                      # mm, JLC's pad hole-to-hole spacing (capabilities page)
HOLE_GAP_OK = re.compile(r"^STAB_\w+$")   # closer pairs allowed only between these (ORDER-3)
NOT_FITTED = re.compile(r"^(JP\d+|TP\d+|H\d+|STAB_\w+)$")
DATE = re.compile(r"20\d\d-\d\d-\d\d")


def read_csv_bytes(data: bytes) -> list[list[str]]:
    return list(csv.reader(io.StringIO(data.decode("utf-8"), newline="")))


def edge_bbox(gm1: str) -> tuple[float, float, float, float]:
    """Edge.Cuts Gerber (KiKit: format 4.6 mm) -> min x, min y, max x, max y of its coordinates."""
    xs, ys = [], []
    x = y = 0
    for m in re.finditer(r"(?:X(-?\d+))?(?:Y(-?\d+))?(?:I-?\d+J-?\d+)?D0[12]\*", gm1):
        if m.group(1) is not None:
            x = int(m.group(1))
        if m.group(2) is not None:
            y = int(m.group(2))
        if m.group(1) is not None or m.group(2) is not None:
            xs.append(x / 1e6)
            ys.append(y / 1e6)
    return min(xs), min(ys), max(xs), max(ys)


class Check:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.passed: list[str] = []

    def section(self, name: str, errs: list[str]) -> None:
        (self.passed.append(name) if not errs else self.errors.extend(f"{name}: {e}" for e in errs))


def check_gerbers(data: bytes, panel: bool) -> tuple[list[str], tuple[float, float, float, float] | None]:
    errs = []
    z = zipfile.ZipFile(io.BytesIO(data))
    names = z.namelist()
    found = {}
    for n in names:
        suf = next((s for s in GERBER_SUFFIXES if n.endswith(s) and not (s == "-PTH.drl" and n.endswith("-NPTH.drl"))),
                   None)
        if suf is None:
            errs.append(f"unexpected file {n}")
        elif suf in found:
            errs.append(f"two files for *{suf}")
        else:
            found[suf] = n
    errs += [f"missing *{s}" for s in GERBER_SUFFIXES if s not in found]
    for n in names:
        text = z.read(n).decode()
        if not text.strip():
            errs.append(f"{n} is empty")
        if DATE.search(text):
            errs.append(f"{n} carries a date ({DATE.search(text).group(0)}): not reproducible")
    bbox = None
    if "-EdgeCuts.gm1" in found:
        bbox = edge_bbox(z.read(found["-EdgeCuts.gm1"]).decode())
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if panel:
            if not (PANEL_LIMIT[0] <= min(w, h) and max(w, h) <= PANEL_LIMIT[1]):
                errs.append(f"panel {w:.2f} x {h:.2f} mm outside JLC's Standard PCBA panel range "
                            f"{PANEL_LIMIT[0]:g}-{PANEL_LIMIT[1]:g} mm")
        else:
            lo, hi = SINGLE_LIMIT
            if not (min(w, h) >= lo[0] and max(w, h) <= hi[1] and min(w, h) <= hi[0]):
                errs.append(f"board {w:.2f} x {h:.2f} mm outside JLC's Standard PCBA single-board range")
    return errs, bbox


def check_bom(rows: list[list[str]]) -> tuple[list[str], dict[str, str]]:
    errs, refs = [], {}
    if not rows or rows[0] != BOM_HEADER:
        return [f"header {rows[0] if rows else None}, want {BOM_HEADER}"], refs
    for i, row in enumerate(rows[1:], 2):
        if len(row) != 4:
            errs.append(f"line {i}: {len(row)} columns")
            continue
        comment, designators, footprint, code = row
        ds = [d.strip() for d in designators.split(",") if d.strip()]
        if not comment or not footprint or not ds:
            errs.append(f"line {i}: empty Comment, Designator or Footprint")
        if not re.fullmatch(r"C\d+", code):
            errs.append(f"line {i} ({ds[0] if ds else '?'}): LCSC Part # {code!r}")
        if len(ds) > 200:
            errs.append(f"line {i}: {len(ds)} designators (JLC: at most 200)")
        for d in ds:
            if d in refs:
                errs.append(f"{d} on two lines")
            refs[d] = code
    upper = {}
    for d in refs:
        if d.upper() in upper:
            errs.append(f"{d} and {upper[d.upper()]} differ only in case (JLC upper-cases designators)")
        upper[d.upper()] = d
    return errs, refs


def check_cpl(rows: list[list[str]], bbox) -> tuple[list[str], dict[str, tuple]]:
    errs, out = [], {}
    if not rows or rows[0] != CPL_HEADER:
        return [f"header {rows[0] if rows else None}, want {CPL_HEADER}"], out
    for i, row in enumerate(rows[1:], 2):
        if len(row) != 5:
            errs.append(f"line {i}: {len(row)} columns")
            continue
        d, x, y, layer, rot = row
        try:
            fx, fy, fr = float(x), float(y), float(rot)
        except ValueError:
            errs.append(f"{d}: Mid X / Mid Y / Rotation not numbers ({x}, {y}, {rot})")
            continue
        if layer not in ("Top", "Bottom"):
            errs.append(f"{d}: Layer {layer!r} (Top or Bottom)")
        if not 0 <= fr < 360:
            errs.append(f"{d}: rotation {fr}")
        if d in out:
            errs.append(f"{d} placed twice")
        if bbox and not (bbox[0] <= fx <= bbox[2] and bbox[1] <= fy <= bbox[3]):
            errs.append(f"{d} at ({fx}, {fy}) outside the board outline")
        out[d] = (fx, fy, layer, fr)
    return errs, out


def check_design(side: str, bom: dict[str, str], cpl: dict[str, tuple]) -> tuple[list[str], list[str]]:
    from design import RETIRED, design
    parts = design(side)
    fitted = {p.ref: p.lcsc for p in parts if p.in_bom and not p.dnp}
    left_out = sorted((p.ref for p in parts if p.ref not in fitted), key=natural)
    errs = [f"{r} in the BOM, not in the CPL" for r in sorted(set(bom) - set(cpl), key=natural)]
    errs += [f"{r} in the CPL, not in the BOM" for r in sorted(set(cpl) - set(bom), key=natural)]
    errs += [f"{r} missing: design.py has JLC fit it" for r in sorted(set(fitted) - set(bom), key=natural)]
    errs += [f"{r} listed, but design.py does not have JLC fit it" for r in sorted(set(bom) - set(fitted), key=natural)]
    errs += [f"{r} listed, but it is copper or drill only" for r in bom if NOT_FITTED.match(r)]
    errs += [f"{r}: BOM {bom[r]}, design.py {fitted[r]}" for r in sorted(set(bom) & set(fitted), key=natural)
             if bom[r] != fitted[r]]
    errs += [f"{r}: {bom[r]} is retired ({RETIRED[bom[r]]})" for r in bom if bom[r] in RETIRED]
    return errs, left_out


def natural(ref: str) -> tuple[str, int]:
    m = re.fullmatch(r"(\D*)(\d*)", ref)
    return (m.group(1), int(m.group(2) or 0)) if m else (ref, 0)


def panel_features(path: str) -> dict:
    """Fiducials, tooling holes, rails and mouse-bites of a KiKit panel (pcbnew)."""
    import pcbnew
    board = pcbnew.LoadBoard(path)

    def mm(v):
        return (pcbnew.ToMM(v.x), pcbnew.ToMM(v.y))
    ps = pcbnew.SHAPE_POLY_SET()
    board.GetBoardPolygonOutlines(ps, True)
    outer = max(range(ps.OutlineCount()), key=lambda i: ps.Outline(i).Area())
    o = ps.Outline(outer)
    pts = [mm(o.CPoint(i)) for i in range(o.PointCount())]
    x0, y0 = min(p[0] for p in pts), min(p[1] for p in pts)
    x1, y1 = max(p[0] for p in pts), max(p[1] for p in pts)
    rail = math.inf
    for j in range(ps.HoleCount(outer)):
        h = ps.Hole(outer, j)
        for i in range(h.PointCount()):
            x, y = mm(h.CPoint(i))
            rail = min(rail, x - x0, x1 - x, y - y0, y1 - y)
    fids = {"top": [], "bottom": []}
    tooling, bites, holes = [], set(), []
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if ref.startswith("KiKit_FID_"):
            pad = next(iter(fp.Pads()))
            side = "bottom" if fp.GetLayer() == pcbnew.B_Cu else "top"
            copper = pcbnew.ToMM(pad.GetSize(pcbnew.B_Cu if side == "bottom" else pcbnew.F_Cu).x)
            margin = pad.GetLocalSolderMaskMargin()
            fids[side].append({"at": [round(v, 3) for v in mm(fp.GetPosition())], "copper": round(copper, 3),
                               "opening": round(copper + 2 * pcbnew.ToMM(margin or 0), 3)})
        elif ref.startswith("KiKit_TO_"):
            pad = next(iter(fp.Pads()))
            tooling.append({"at": [round(v, 3) for v in mm(fp.GetPosition())],
                            "d": round(pcbnew.ToMM(pad.GetDrillSize().x), 3),
                            "npth": pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH})
        elif ref.startswith("KiKit_MB_"):
            bites.add(ref.split("_")[2])                # KiKit_MB_<cut>_<hole>: one cut per tab
            holes.append((fp.GetPosition(), pcbnew.ToMM(next(iter(fp.Pads())).GetDrillSize().x) / 2))
    # least distance from a mouse-bite hole edge to each part's courtyard (either side)
    clear = {}
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if ref.startswith("KiKit_"):
            continue
        for layer in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
            ps = fp.GetCourtyard(layer)
            if ps.OutlineCount() == 0:
                continue
            for h, r in holes:
                d = pcbnew.ToMM(math.sqrt(ps.SquaredDistance(h))) - r
                clear[ref] = min(clear.get(ref, math.inf), d)
    return {"w": round(x1 - x0, 3), "h": round(y1 - y0, 3), "rail_min": round(rail, 3),
            "fiducials_top": sorted(fids["top"], key=lambda f: f["at"]),
            "fiducials_bottom": sorted(fids["bottom"], key=lambda f: f["at"]),
            "tooling": sorted(tooling, key=lambda t: t["at"]), "tabs": len(bites), "bounds": [x0, y0, x1, y1],
            "bite_clearance": {k: round(v, 3) for k, v in sorted(clear.items())}}


def check_panel(path: str) -> list[str]:
    f = panel_features(path)
    errs = []
    for side in ("top", "bottom"):
        fl = f[f"fiducials_{side}"]
        if len(fl) != 3:
            errs.append(f"{len(fl)} fiducials on the {side}, want 3")
        for fid in fl:
            x, y = fid["at"]
            x0, y0, x1, y1 = f["bounds"]
            edge = min(x - x0, x1 - x, y - y0, y1 - y)
            if edge < FID_EDGE_MIN - 1e-6:
                errs.append(f"{side} fiducial at ({x}, {y}) {edge:.2f} mm from the panel edge (>= {FID_EDGE_MIN})")
            if abs(fid["copper"] - 1.0) > 1e-3 or abs(fid["opening"] - 2.0) > 1e-3:
                errs.append(f"{side} fiducial copper {fid['copper']} / opening {fid['opening']} (1 / 2 mm)")
    if len(f["tooling"]) != 4 or not all(t["npth"] for t in f["tooling"]):
        errs.append(f"tooling holes {f['tooling']}, want 4 NPTH")
    if f["rail_min"] < RAIL_MIN:
        errs.append(f"rail {f['rail_min']:.2f} mm (>= {RAIL_MIN})")
    if f["tabs"] < 8:
        errs.append(f"only {f['tabs']} tabs")
    for ref, d in f["bite_clearance"].items():
        if d < BITE_CLEAR:
            errs.append(f"a mouse-bite hole is {d:.2f} mm from the courtyard of {ref} (>= {BITE_CLEAR})")
    return errs


def copper_digest(board, dx: int = 0, dy: int = 0) -> dict:
    """What the board's copper is made of, shifted by (dx, dy) nm: footprints, tracks, vias, zone fills."""
    import pcbnew
    fps = {fp.GetReference(): (fp.GetPosition().x - dx, fp.GetPosition().y - dy,
                               round(fp.GetOrientation().AsDegrees(), 4), fp.GetLayer(), str(fp.GetFPID().GetUniStringLibId()))
           for fp in board.GetFootprints() if not fp.GetReference().startswith("KiKit_")}
    tracks = sorted((t.GetClass(), t.GetLayer(), t.GetStart().x - dx, t.GetStart().y - dy, t.GetEnd().x - dx,
                     t.GetEnd().y - dy, t.GetWidth(pcbnew.F_Cu) if t.GetClass() == "PCB_VIA" else t.GetWidth(),
                     t.GetNetname()) for t in board.GetTracks())
    zones = sorted((z.GetNetname(), layer, round(pcbnew.ToMM(pcbnew.ToMM(z.GetFilledPolysList(layer).Area())), 4))
                   for z in board.Zones() for layer in z.GetLayerSet().Seq() if z.IsOnCopperLayer())
    return {"footprints": fps, "tracks": tracks, "zones": zones}


def check_panel_copper(panel_path: str, board_path: str) -> list[str]:
    """The panel carries the committed board unchanged: every footprint, track, via and zone fill."""
    import pcbnew
    panel, board = pcbnew.LoadBoard(panel_path), pcbnew.LoadBoard(board_path)
    ref = next(fp.GetReference() for fp in board.GetFootprints())
    pp = next(fp for fp in panel.GetFootprints() if fp.GetReference() == ref).GetPosition()
    bp = next(fp for fp in board.GetFootprints() if fp.GetReference() == ref).GetPosition()
    a, b = copper_digest(panel, pp.x - bp.x, pp.y - bp.y), copper_digest(board)
    errs = []
    if a["footprints"] != b["footprints"]:
        diff = sorted(k for k in set(a["footprints"]) | set(b["footprints"])
                      if a["footprints"].get(k) != b["footprints"].get(k))
        errs.append(f"footprints differ from the board: {diff[:8]}")
    if a["tracks"] != b["tracks"]:
        errs.append(f"tracks/vias differ from the board ({len(a['tracks'])} vs {len(b['tracks'])})")
    if a["zones"] != b["zones"]:
        errs.append(f"zone fills differ from the board: {sorted(set(a['zones']) ^ set(b['zones']))[:6]}")
    return errs


def stock(side: str, boards: int) -> list[str]:
    sys.path.insert(0, str(ROOT / "tests/integration"))
    import stock as st
    per_board, _ = st.bom()
    errs = []
    for code in sorted(per_board, key=lambda c: int(c[1:])):
        r = st.assess(code, per_board[code], boards, st.jlc(code), st.lcsc(code))
        print(f"  stock {code:10} need {r.need:>6} JLC {r.jlc_stock:>8} {r.library:9} {r.process:4} {r.part} "
              f"{' '.join(r.flags)}")
        errs += [f"{code} {flag}" for flag in r.flags]
    return errs


def cmd_check(argv: list[str]) -> int:
    side, pkg = argv[0], Path(argv[1])
    panel_board, boards = None, None
    it = iter(argv[2:])
    for a in it:
        if a == "--panel":
            panel_board = next(it)
        elif a == "--stock":
            boards = int(next(it))
    ck = Check()
    order = pkg / f"worxboard-{side}-jlc-order.zip"
    need = [pkg / n for n in ("gerbers.zip", "bom.csv", "cpl.csv", "README.md")] + [order] + \
        [pkg / "bare-board" / n for n in ("gerbers.zip", "bom.csv", "cpl.csv", "README.md")]
    missing = [str(p) for p in need if not p.is_file() or p.stat().st_size == 0]
    ck.section("package files present", missing and [f"missing or empty: {m}" for m in missing])
    if missing:
        return report(ck, side)
    z = zipfile.ZipFile(order)
    errs = []
    if sorted(z.namelist()) != sorted(["gerbers.zip", "bom.csv", "cpl.csv", "README.md"]):
        errs.append(f"{order.name} holds {z.namelist()}")
    errs += [f"{order.name}:{n} differs from {n}" for n in z.namelist() if (pkg / n).is_file()
             and z.read(n) != (pkg / n).read_bytes()]
    ck.section(f"{order.name} = gerbers.zip + bom.csv + cpl.csv + README.md", errs)
    for label, d, panel in (("panel", pkg, True), ("bare board", pkg / "bare-board", False)):
        gerr, bbox = check_gerbers((d / "gerbers.zip").read_bytes(), panel)
        size = f"{bbox[2] - bbox[0]:.2f} x {bbox[3] - bbox[1]:.2f} mm" if bbox else "?"
        ck.section(f"{label} gerbers.zip: 9 layers + PTH/NPTH drills, no dates, {size} within JLC limits", gerr)
        berr, bom = check_bom(read_csv_bytes((d / "bom.csv").read_bytes()))
        ck.section(f"{label} bom.csv: {','.join(BOM_HEADER)}; {len(set(bom.values()))} LCSC numbers", berr)
        cerr, cpl = check_cpl(read_csv_bytes((d / "cpl.csv").read_bytes()), bbox)
        nb = sum(1 for v in cpl.values() if v[2] == "Bottom")
        ck.section(f"{label} cpl.csv: {','.join(CPL_HEADER)}; {len(cpl)} placements, {nb} bottom", cerr)
        derr, left_out = check_design(side, bom, cpl)
        ck.section(f"{label}: BOM = CPL = the {len(bom)} parts design.py fits; not fitted on purpose: "
                   f"{compress(left_out)}", derr)
    if panel_board:
        ck.section("panel: 3 fiducials per side >= 3.85 mm from the edges, 4 tooling holes, rails >= 5 mm",
                   check_panel(panel_board))
        ck.section(f"panel carries pcb/{side}/worxboard-{side}.kicad_pcb unchanged (footprints, tracks, vias, "
                   f"zone fills)", check_panel_copper(panel_board, str(ROOT / f"pcb/{side}/worxboard-{side}.kicad_pcb")))
    if boards:
        ck.section(f"JLC stock for {boards} boards per half (both halves)", stock(side, boards))
    return report(ck, side)


def compress(refs: list[str]) -> str:
    groups: dict[str, list[int]] = {}
    for r in refs:
        a, n = natural(r)
        groups.setdefault(a, []).append(n)
    out = []
    for a, ns in groups.items():
        if len(ns) == 1:
            out.append(f"{a}{ns[0]}" if ns[0] else a)
        else:
            out.append(f"{a}{min(ns)}-{a}{max(ns)}" if ns == list(range(min(ns), max(ns) + 1)) else
                       ",".join(f"{a}{n}" for n in ns))
    return ", ".join(out)


def report(ck: Check, side: str) -> int:
    for p in ck.passed:
        print(f"PASS  {p}")
    for e in ck.errors:
        print(f"FAIL  {e}")
    print(f"jlc_check {side}: {len(ck.passed)} passed, {len(ck.errors)} errors")
    return 1 if ck.errors else 0


def close_holes(board) -> list[list]:
    """Pairs of pad holes (plated or not, vias aside) with less than HOLE_GAP of board between them:
    [ref, ref, gap mm, x, y] (deviations ORDER-3)."""
    import pcbnew
    from shapely.geometry import LineString, Point
    from shapely.strtree import STRtree
    holes = []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.HasHole():
                h = pad.GetEffectiveHoleShape()
                a, b = h.GetSeg().A, h.GetSeg().B
                a, b = (pcbnew.ToMM(a.x), pcbnew.ToMM(a.y)), (pcbnew.ToMM(b.x), pcbnew.ToMM(b.y))
                holes.append((fp.GetReference(), (LineString([a, b]) if a != b else Point(a)).buffer(pcbnew.ToMM(h.GetWidth()) / 2, 32)))
    tree = STRtree([g for _, g in holes])
    out = []
    for i, (ref, g) in enumerate(holes):
        for j in sorted(int(k) for k in tree.query(g.buffer(HOLE_GAP))):
            gap = g.distance(holes[j][1])
            if j > i and gap < HOLE_GAP:
                c = g.union(holes[j][1]).centroid
                out.append(sorted([ref, holes[j][0]], key=natural) + [round(gap, 3), round(c.x, 2), round(c.y, 2)])
    return sorted(out)


def cmd_facts(argv: list[str]) -> int:
    panel_path, board_path, kikit, drc_path, out = argv
    import pcbnew
    p = panel_features(panel_path)
    bps = pcbnew.SHAPE_POLY_SET()
    board = pcbnew.LoadBoard(board_path)
    board.GetBoardPolygonOutlines(bps, True)
    b = bps.BBox()
    rows = list(csv.reader(open(Path(kikit) / "pos.csv", newline="", encoding="utf-8")))[1:]
    bom_rows = list(csv.reader(open(Path(kikit) / "bom.csv", newline="", encoding="utf-8")))[1:]
    drc = json.loads(Path(drc_path).read_text())
    preset = json.loads((HERE / "panel.json").read_text())
    turned = sorted((r for r in rows if r[3] == "B" and float(r[4]) % 180),
                    key=lambda r: natural(r[0]))
    facts = {
        "panel": {k: p[k] for k in ("w", "h", "fiducials_top", "fiducials_bottom", "tooling")},
        "bare": {"w": round(pcbnew.ToMM(b.GetWidth()), 3), "h": round(pcbnew.ToMM(b.GetHeight()), 3)},
        "rail_min": p["rail_min"],
        "slot": float(preset["framing"]["slotwidth"].removesuffix("mm")),
        "tabs": p["tabs"],
        "bite_clear_min": min(p["bite_clearance"].values()),
        "bite_clear_j1_j2": min(p["bite_clearance"].get(r, math.inf) for r in ("J1", "J2")),
        "bite_d": float(preset["cuts"]["drill"].removesuffix("mm")),
        "fid_copper": p["fiducials_top"][0]["copper"] if p["fiducials_top"] else 0,
        "fid_opening": p["fiducials_top"][0]["opening"] if p["fiducials_top"] else 0,
        "fid_edge": round(min(min(f["at"][0] - p["bounds"][0], p["bounds"][2] - f["at"][0],
                                  f["at"][1] - p["bounds"][1], p["bounds"][3] - f["at"][1])
                              for f in p["fiducials_top"] + p["fiducials_bottom"]), 3),
        "tool_d": p["tooling"][0]["d"] if p["tooling"] else 0,
        "parts": len(rows),
        "bottom_parts": sum(1 for r in rows if r[3] == "B"),
        "bom_lines": len(bom_rows),
        "lcsc_numbers": len({r[3] for r in bom_rows}),
        "drc_errors": sum(1 for v in drc["violations"] if v["severity"] == "error"),
        "drc_unconnected": len(drc.get("unconnected_items", [])),
        "close_holes": close_holes(board),
        "hole_gap": HOLE_GAP,
        # bottom parts at an angle other than 0 / 180: the only ones whose look in JLC's viewer depends
        # on which way it turns bottom parts (deviations ORDER-2)
        "bottom_turned": {"refs": compress([r[0] for r in turned]), "n": len(turned),
                          "rot": sorted({float(r[4]) for r in turned})},
    }
    Path(out).write_text(json.dumps(facts, indent=1, sort_keys=True) + "\n")
    bad = [h for h in facts["close_holes"] if not all(HOLE_GAP_OK.match(r) for r in h[:2])]
    for a, b, gap, x, y in bad:
        print(f"jlc_check facts: holes of {a} and {b} {gap} mm apart at ({x}, {y}) < {HOLE_GAP} "
              "(JLC's pad hole-to-hole spacing)", file=sys.stderr)
    return 1 if bad else 0


def main(argv: list[str]) -> int:
    if argv[:1] == ["check"] and len(argv) >= 3:
        return cmd_check(argv[1:])
    if argv[:1] == ["facts"] and len(argv) == 6:
        return cmd_facts(argv[1:])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
