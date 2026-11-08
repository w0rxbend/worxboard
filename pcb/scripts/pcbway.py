# SPDX-License-Identifier: GPL-3.0-or-later
"""The PCBWay turnkey order files of one half, next to the JLC package (stage_p.sh step P6).

    python3 pcb/scripts/pcbway.py <side> <board.kicad_pcb> <panel pos.csv> <bare pos.csv> <facts.json> <package dir>

<panel pos.csv> and <bare pos.csv> are KiCad's own position files of the KiKit panel and of the board
(`kicad-cli pcb export pos --format csv --units mm --side both --use-drill-file-origin`). <package dir>
is the JLC package package.py wrote (build/<side>/production): this script reads its BOM, CPLs and
Gerbers and writes <package dir>/pcbway/ (committed as pcb/production/<side>/pcbway/):
  bom.csv                  one line per part number: manufacturer and MPN from mpn.json, LCSC number
                           as the alternate source, SMD/THT from the footprint, side
  centroid-panel.csv       KiCad's positions and rotations as they are (no JLC correction), in the
  centroid-bare-board.csv  frame of ../gerbers.zip (panel) and ../bare-board/gerbers.zip
  README.md                which files to upload, PCBWay's order form, the remark, substitution rules
It fails, and writes nothing, unless:
  - the designators are the JLC BOM's, which are the parts design.py fits, each with design.py's LCSC
    number, and every LCSC number design.py names has an mpn.json entry (mpn.py check)
  - the panel centroids are the bare-board ones moved by one offset (the KiKit panel's), side and
    rotation unchanged, and every centroid lies inside the Edge.Cuts of its Gerber set
  - re-applying pcb/scripts/jlc_rotations.csv and JLC's bottom-side rotation to these centroids gives
    the JLC CPL (../cpl.csv, ../bare-board/cpl.csv) within 0.01 mm and 0.01 degree for every part:
    so a part whose footprint has no row there sits exactly where JLC's CPL puts it
Output is reproducible byte for byte (no dates; the inputs are), like the JLC package.
"""
from __future__ import annotations

import csv
import json
import math
import re
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))

import mpn  # noqa: E402
from jlc_check import edge_bbox, natural  # noqa: E402
from package import csv_bytes, hole_remark  # noqa: E402

BOM_HEADER = ["Item", "Designator", "Qty", "Manufacturer", "Manufacturer Part Number", "Description",
              "Package", "Mount", "Side", "LCSC # (alternate source)"]
CENTROID_HEADER = ["Designator", "Value", "Package", "Mid X (mm)", "Mid Y (mm)", "Rotation", "Layer"]
POS_HEADER = ["Ref", "Val", "Package", "PosX", "PosY", "Rot", "Side"]       # kicad-cli pos, csv
ROTATIONS = HERE / "jlc_rotations.csv"
TOL_MM, TOL_DEG = 0.01, 0.01
REMARK_MAX = 200                     # PCBWay's "Other special request" field
GENERIC_PACKAGE = {"", "-", "SMD", "Plugin", "Through Hole"}
ASCII = {"Ω": "ohm", "±": "+/-", "℃": "C", "°": "deg", "µ": "u", "μ": "u", "×": "x", "–": "-"}
# PCBWay's form: min track/spacing and min hole size options (mm)
TRACK_OPTIONS = [(0.2032, "8/8mil"), (0.1524, "6/6mil"), (0.127, "5/5mil"), (0.1016, "4/4mil"), (0.0762, "3/3mil")]
HOLE_OPTIONS = [(0.3, "0.3mm ↑"), (0.25, "0.25mm"), (0.2, "0.2mm"), (0.15, "0.15mm")]

# Substitution rules, first match on (designator, footprint) wins; {cl} and {value} are filled per line
SUBSTITUTES = [
    ("pinsocket", r"^J\d+$", r":PinSocket_1x05_P2\.54mm_Vertical_H5\.0mm$",
     "only a 1x5, 2.54 mm pitch, single-row through-hole female header with a **5.0 mm** body: the display "
     "height in the case depends on it; otherwise ask"),
    ("crystal", r"^Y\d+$", r"^Crystal:Crystal_SMD_3225",
     "{value}, 3225 four-pad, CL {cl}, ±20 ppm or better; otherwise ask"),
    ("socket", r"^SK\d+$", r":SW_MX_Hotswap",
     "only the second source {second}, same land pattern; otherwise ask"),
    ("led", r"^LED\d+$", r":LED_SK6812MINI-E", "only an SK6812MINI-E (3.2 x 2.8 mm reverse-mount, the same pinout): "
     "the PCB cutout and pads are made for it; otherwise ask"),
    ("passive", r"^R\d+$", r"^Resistor_SMD:", "any resistor of the same value, size, tolerance and power rating "
     "or better"),
    ("passive", r"^C\d+$", r"^Capacitor_SMD:", "any MLCC of the same value, size, dielectric and tolerance, same "
     "or higher voltage"),
    ("passive", r"^F\d+$", r"^Fuse:", "any PTC fuse of the same size and hold current, same or higher voltage"),
    ("diode", r"^D\d+$", r"^Diode_SMD:", "the same diode type from another maker, same package, same or better "
     "ratings"),
    ("switch", r"^SW\d+$", r"^Button_Switch_SMD:SW_SPST_TS-1088", "a tact switch on the same TS-1088 land "
     "pattern; otherwise ask"),
    ("none", r".", r".", "no substitute: ask first"),
]
SOCKET_SECOND_SOURCE = "C49352235"   # design.py LCSC_SOCKET comment: same land pattern


def ascii_text(s: str) -> str:
    """PCBWay opens the CSVs in Excel, which reads UTF-8 without a BOM as Latin-1: keep them ASCII."""
    out = "".join(ASCII.get(c, c) for c in s)
    bad = sorted({c for c in out if ord(c) > 126})
    if bad:
        raise SystemExit(f"pcbway: no ASCII for {bad} in {s!r}: add it to ASCII in {Path(__file__).name}")
    return out


def read_csv(path: Path) -> list[list[str]]:
    return list(csv.reader(path.open(newline="", encoding="utf-8")))


def read_pos(path: Path) -> dict[str, dict]:
    """kicad-cli position file -> ref: fields, KiKit's own panel footprints (fiducials, tooling) left out."""
    rows = read_csv(path)
    if rows[0] != POS_HEADER:
        raise SystemExit(f"{path}: header {rows[0]}, want {POS_HEADER}")
    out = {}
    for ref, val, pkg, x, y, rot, side in rows[1:]:
        if ref.startswith("KiKit_"):
            continue
        if ref in out or side not in ("top", "bottom"):
            raise SystemExit(f"{path}: {ref} twice or side {side!r}")
        out[ref] = {"value": val, "package": pkg, "x": x, "y": y, "rot": float(rot), "layer": side.capitalize()}
    return out


def rot_text(r: float) -> str:
    """KiCad's angle (counter-clockwise, top view; KiCad writes -180..180), as 0 <= r < 360."""
    r = round(r % 360.0, 6) % 360.0
    return f"{r:.6f}"


def rotation_rows() -> list[tuple[re.Pattern, float, float, float]]:
    rows = read_csv(ROTATIONS)
    return [(re.compile(fp), float(x), float(y), float(r)) for fp, _part, x, y, r in rows[1:]]


def correction(rows, lib_id: str) -> tuple[float, float, float] | None:
    """The jlc_rotations.csv row KiKit applies to a footprint (first re.match on the lib id), or None."""
    return next(((x, y, r) for pat, x, y, r in rows if pat.match(lib_id)), None)


def part_correction(rows, part, lib_id: str) -> tuple[float, float, float] | None:
    """KiKit's order: a part's own JLCPCB_CORRECTION field ("x;y;rot", design.py extra) wins over the
    footprint row of jlc_rotations.csv (kikit/fab/common.py collectPosData)."""
    field = part.extra.get("JLCPCB_CORRECTION", "") if part is not None else ""
    if field:
        x, y, r = (float(v) for v in field.split(";"))
        return x, y, r
    return correction(rows, lib_id)


def jlc_expected(x: float, y: float, rot: float, layer: str, corr) -> tuple[float, float, float]:
    """KiKit's JLC transform (kikit/fab/common.py footprintPosition / footprintOrientation with
    MirrorBottom) applied to a KiCad centroid: the offset turns with the footprint and is not mirrored on
    the bottom; the rotation is 180 - angle on the bottom, plus the correction."""
    cx, cy, cr = corr or (0.0, 0.0, 0.0)
    t = math.radians(rot)
    ex = x + cx * math.cos(t) + cy * math.sin(t)
    ey = y + cx * math.sin(t) - cy * math.cos(t)
    er = ((180.0 - rot) if layer == "Bottom" else rot) + cr
    return ex, ey, er % 360.0


def angle_diff(a: float, b: float) -> float:
    d = (a - b) % 360.0
    return min(d, 360.0 - d)


def gerber_bbox(zip_path: Path):
    z = zipfile.ZipFile(zip_path)
    name = next(n for n in z.namelist() if n.endswith("-EdgeCuts.gm1"))
    return edge_bbox(z.read(name).decode())


def board_facts(board_path: str) -> dict:
    """What the PCB form and the remark need from the board itself (pcbnew)."""
    import pcbnew
    board = pcbnew.LoadBoard(board_path)
    ds = board.GetDesignSettings()
    fps = {}
    for fp in board.GetFootprints():
        attr = fp.GetAttributes()
        mount = "SMD" if attr & pcbnew.FP_SMD else "THT" if attr & pcbnew.FP_THROUGH_HOLE else ""
        pads = [p for p in fp.Pads() if p.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH]
        pth = [p for p in pads if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH]
        centre = None
        if pads:
            box = pads[0].GetBoundingBox()
            for p in pads[1:]:
                box.Merge(p.GetBoundingBox())
            c, o = box.GetCenter(), fp.GetPosition()
            centre = math.hypot(pcbnew.ToMM(c.x - o.x), pcbnew.ToMM(c.y - o.y))
        fps[fp.GetReference()] = {"mount": mount, "lib": str(fp.GetFPID().GetUniStringLibId()),
                                  "pth": len(pth), "origin_off": centre}
    tracks = [pcbnew.ToMM(t.GetWidth()) for t in board.GetTracks() if t.GetClass() == "PCB_TRACK"]
    drills = [pcbnew.ToMM(t.GetDrillValue()) for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
    drills += [pcbnew.ToMM(min(p.GetDrillSize().x, p.GetDrillSize().y)) for fp in board.GetFootprints()
               for p in fp.Pads() if p.HasHole()]
    # the board's minimum clearance rule (the netclasses are wider; DRC holds every gap to it)
    return {"fps": fps, "min_track": min(tracks), "min_clear": pcbnew.ToMM(ds.m_MinClearance),
            "min_drill": min(drills)}


def pick(options, value: float) -> str:
    """The coarsest PCBWay option the board still meets (option <= value)."""
    return next(label for limit, label in options if limit <= value + 1e-6)


def substitution(ref: str, lib: str, value: str, part: dict, parts: dict) -> tuple[str, str]:
    for key, ref_re, lib_re, text in SUBSTITUTES:
        if re.search(ref_re, ref) and re.search(lib_re, lib):
            cl = re.search(r"(\d+(?:\.\d+)?)\s*pF", part["description"])
            second = parts.get(SOCKET_SECOND_SOURCE)
            return key, text.format(value=value, cl=f"{cl.group(1)} pF" if cl else "as the BOM part",
                                    second=f"{second['manufacturer']} {second['mpn']} (LCSC {SOCKET_SECOND_SOURCE})"
                                    if second else "the BOM part")
    raise AssertionError("the last rule matches everything")


def build(side: str, board_path: str, panel_pos: Path, bare_pos: Path, facts: dict, pkg: Path):
    from design import design
    errs: list[str] = []
    parts = mpn.load()
    errs += [f"mpn: {e}" for e in mpn.problems(parts, mpn.required())]
    fitted = {p.ref: p for p in design(side) if p.in_bom and not p.dnp}
    # the JLC BOM (panel and bare board): designator -> (comment, footprint, LCSC)
    jlc_bom = {}
    for sub in ("", "bare-board/"):
        rows = read_csv(pkg / sub / "bom.csv")
        refs = {d.strip(): (c, fp, code) for c, ds, fp, code in rows[1:] for d in ds.split(",")}
        if jlc_bom and refs != jlc_bom:
            errs.append("the panel and bare-board JLC BOMs differ")
        jlc_bom = refs
    if set(jlc_bom) != set(fitted):
        errs.append(f"JLC BOM {sorted(set(jlc_bom) ^ set(fitted), key=natural)} vs design.py")
    errs += [f"{r}: JLC BOM {jlc_bom[r][2]}, design.py {fitted[r].lcsc}" for r in sorted(fitted, key=natural)
             if r in jlc_bom and jlc_bom[r][2] != fitted[r].lcsc]
    bf = board_facts(board_path)
    pos = {"panel": read_pos(panel_pos), "bare": read_pos(bare_pos)}
    for what, p in pos.items():
        if set(p) != set(jlc_bom):
            errs.append(f"{what} position file {sorted(set(p) ^ set(jlc_bom), key=natural)} vs the JLC BOM")
    if errs:
        raise SystemExit("pcbway:\n  " + "\n  ".join(errs))
    refs = sorted(jlc_bom, key=natural)
    # panel = bare board moved by the KiKit panel's offset
    offs = {r: (float(pos["panel"][r]["x"]) - float(pos["bare"][r]["x"]),
                float(pos["panel"][r]["y"]) - float(pos["bare"][r]["y"])) for r in refs}
    dx, dy = offs[refs[0]]
    for r in refs:
        a, b = pos["panel"][r], pos["bare"][r]
        if math.hypot(offs[r][0] - dx, offs[r][1] - dy) > 1e-4 or a["layer"] != b["layer"] \
                or angle_diff(a["rot"], b["rot"]) > 1e-6 or (a["value"], a["package"]) != (b["value"], b["package"]):
            errs.append(f"{r}: panel {a} is not the bare board {b} moved by ({dx:.4f}, {dy:.4f})")
    # inside the Edge.Cuts of the matching Gerbers, and the JLC CPL re-derived
    rot_rows = rotation_rows()
    cross = {}
    for what, sub in (("panel", ""), ("bare", "bare-board/")):
        x0, y0, x1, y1 = gerber_bbox(pkg / sub / "gerbers.zip")
        cpl = {d: (float(x), float(y), layer, float(r)) for d, x, y, layer, r in read_csv(pkg / sub / "cpl.csv")[1:]}
        plain = corrected = 0
        worst = 0.0
        for r in refs:
            p = pos[what][r]
            x, y = float(p["x"]), float(p["y"])
            if not (x0 <= x <= x1 and y0 <= y <= y1):
                errs.append(f"{what} {r} at ({x}, {y}) outside the Gerber outline ({x0}, {y0})-({x1}, {y1})")
            corr = part_correction(rot_rows, fitted.get(r), jlc_bom[r][1])
            ex, ey, er = jlc_expected(x, y, p["rot"], p["layer"], corr)
            jx, jy, jl, jr = cpl[r]
            d = math.hypot(ex - jx, ey - jy)
            worst = max(worst, d) if corr is None else worst
            if d > TOL_MM or angle_diff(er, jr) > TOL_DEG or jl != p["layer"]:
                errs.append(f"{what} {r}: KiCad ({x}, {y}, {p['rot']}, {p['layer']}) with JLC correction {corr} "
                            f"gives ({ex:.3f}, {ey:.3f}, {er:.2f}), JLC CPL has {cpl[r]}")
            plain, corrected = plain + (corr is None), corrected + (corr is not None)
        cross[what] = {"plain": plain, "corrected": corrected, "worst_plain": worst}
    for r in refs:
        if bf["fps"][r]["mount"] not in ("SMD", "THT"):
            errs.append(f"{r}: footprint type neither SMD nor through-hole")
    if errs:
        raise SystemExit("pcbway:\n  " + "\n  ".join(errs))

    # BOM: one line per LCSC number (= one MPN)
    lines = defaultdict(list)
    for r in refs:
        lines[fitted[r].lcsc].append(r)
    order = sorted(lines, key=lambda c: natural(lines[c][0]))
    bom_rows, subs = [BOM_HEADER], []
    for i, code in enumerate(order, 1):
        rs = lines[code]
        e = parts[code]
        values = list(dict.fromkeys(fitted[r].value for r in rs))
        mounts = sorted({bf["fps"][r]["mount"] for r in rs})
        layers = [s for s in ("Top", "Bottom") if any(pos["bare"][r]["layer"] == s for r in rs)]
        package = e["package"] if e["package"] not in GENERIC_PACKAGE else pos["bare"][rs[0]]["package"]
        bom_rows.append([str(i), ",".join(rs), str(len(rs)), ascii_text(e["manufacturer"]), ascii_text(e["mpn"]),
                         ascii_text(f"{'/'.join(values)} - {e['description']}"), ascii_text(package),
                         "/".join(mounts), "+".join(layers), code])
        key, text = substitution(rs[0], bf["fps"][rs[0]]["lib"], "/".join(values), e, parts)
        subs.append((rs, e, key, text))

    def centroid(what: str) -> bytes:
        return csv_bytes([CENTROID_HEADER] + [[r, pos[what][r]["value"], pos[what][r]["package"], pos[what][r]["x"],
                                               pos[what][r]["y"], rot_text(pos[what][r]["rot"]), pos[what][r]["layer"]]
                                              for r in refs])

    # parts whose KiCad zero orientation is not JLC's (the rotation column of jlc_rotations.csv)
    turned = [r for r in refs if (part_correction(rot_rows, fitted.get(r), jlc_bom[r][1]) or (0, 0, 0))[2] % 360]
    info = {"side": side, "refs": refs, "pos": pos["bare"], "fps": bf["fps"], "lines": lines, "order": order,
            "turned": turned,
            "parts": parts, "fitted": fitted, "subs": subs, "offset": (dx, dy), "cross": cross, "facts": facts,
            "track": pick(TRACK_OPTIONS, min(bf["min_track"], bf["min_clear"])), "min_track": bf["min_track"],
            "min_clear": bf["min_clear"], "hole": pick(HOLE_OPTIONS, bf["min_drill"]), "min_drill": bf["min_drill"]}
    return {"bom.csv": csv_bytes(bom_rows), "centroid-panel.csv": centroid("panel"),
            "centroid-bare-board.csv": centroid("bare"), "README.md": readme(info)}, info


def ranges(refs) -> str:
    """D1, D101-D137, C5, C8-C17: runs of three or more consecutive designators as a range."""
    out, run = [], []
    for r in sorted(set(refs), key=natural) + [None]:
        if run and (r is None or natural(r)[0] != natural(run[-1])[0] or natural(r)[1] != natural(run[-1])[1] + 1):
            out += [f"{run[0]}-{run[-1]}"] if len(run) >= 3 else run
            run = []
        if r is not None:
            run.append(r)
    return ", ".join(out)


def by_line(info: dict, refs: list[str]) -> str:
    """'37 x 1N4148W D101-D137' style, one entry per BOM line, for the designators refs."""
    out = []
    for code in info["order"]:
        rs = [r for r in info["lines"][code] if r in refs]
        if rs:
            out.append(f"{len(rs)} x {info['parts'][code]['mpn']} {ranges(rs)}")
    return ", ".join(out)


def readme(info: dict) -> bytes:
    f, side, refs, pos, fps = info["facts"], info["side"], info["refs"], info["pos"], info["fps"]
    p, b = f["panel"], f["bare"]
    n = len(refs)
    bottom = [r for r in refs if pos[r]["layer"] == "Bottom"]
    tht = [r for r in refs if fps[r]["mount"] == "THT"]
    smd = [r for r in refs if fps[r]["mount"] == "SMD"]
    pip = [r for r in smd if fps[r]["pth"]]                   # SMD parts with plated legs (pin-in-paste)
    fine = [r for r in refs if re.search(r"(QFN|QFP|BGA)", fps[r]["lib"])]
    dx, dy = info["offset"]
    cr = info["cross"]
    tht_text = (f"{tht[0]} is the only through-hole part ({pos[tht[0]]['layer'].lower()} side): please hand-solder "
                "it." if len(tht) == 1 else f"{', '.join(tht)} are the through-hole parts: please hand-solder them."
                if tht else "There is no through-hole part.")
    pip_text = [f"{r} ({info['parts'][info['fitted'][r].lcsc]['mpn']}): its {fps[r]['pth']} plated through-hole "
                "legs are opened in the paste layer (pin-in-paste); please solder them too." for r in pip]
    sub_line = []                                      # one sentence per rule, in SUBSTITUTES order
    for key in dict.fromkeys(k for k, *_ in SUBSTITUTES):
        rs = sorted((r for r_s, _, k, _ in info["subs"] if k == key for r in r_s), key=natural)
        texts = list(dict.fromkeys(t.replace("**", "") for _, _, k, t in info["subs"] if k == key))
        if rs and key == "none":
            sub_line.append(f"No substitute for {ranges(rs)}: ask first.")
        elif rs:
            text = "any equivalent of the same value, size and rating" if key == "passive" else "; ".join(texts)
            sub_line.append(f"{ranges(rs)}: {text}.")
    top = [r for r in refs if pos[r]["layer"] == "Top"]
    pin1 = [r for r in top if re.match(r"^(U|Y|Q|LED)\d+$", r)]
    diodes_top = [r for r in top if re.match(r"^D\d+$", r) and fps[r]["lib"].startswith("Diode_SMD:")]
    off_lines = []                                     # footprint origin away from the pads' centre
    for code in info["order"]:
        rs = [r for r in info["lines"][code] if (fps[r]["origin_off"] or 0) > 0.25]
        if rs:
            off_lines.append(f"{ranges(rs)} ({max(fps[r]['origin_off'] for r in rs):.1f} mm)")
    remark = [
        f"Turnkey PCBA, both sides, {n} placements: {len(top)} top, {len(bottom)} bottom ({by_line(info, bottom)}).",
        f"Gerbers: 1 board in a customer panel (frame, {f['rail_min']:g} mm rails, {len(p['fiducials_top'])} "
        f"fiducials per side, {len(p['tooling'])} NPTH tooling holes {f['tool_d']:.1f} mm, mouse-bite tabs, no "
        "V-cut). Ship with the frame attached.",
        "J1 (USB-C) and J2 (TRRS) overhang the board edge into the milled slot on purpose.",
        tht_text,
        *pip_text,
        "Centroid: KiCad's own position file (footprint origins, KiCad rotations, no offsets added), X/Y in the "
        "Gerber frame seen from the top. Bottom-side rotations are KiCad's: seen from the bottom, a part is turned "
        "by 180 deg minus the value.",
        "Please send the placement of both sides (orientation and polarity) for confirmation before production.",
        "Substitutes: " + " ".join(sub_line),
        *hole_remark(f),
    ]
    short = (f"Panel by customer: 1 board in a frame, tab-route mouse-bites, no V-cut. J1/J2 overhang the board "
             f"edge into the slot on purpose." + (" Close NPTH stab hole pairs intended." if f["close_holes"] else "")
             + " Ship in the frame.")
    if len(short) > REMARK_MAX:
        raise SystemExit(f"pcbway: the short remark is {len(short)} characters, PCBWay takes {REMARK_MAX}")
    L = [f"# worxboard {side} half: PCBWay turnkey order",
         "",
         f"Generated by `just pcb-pcbway {side}` (part of `just pcb-production {side}`) from the committed board, "
         "`pcb/scripts/design.py` and `pcb/scripts/mpn.json`; do not edit. CI rebuilds these files and fails on "
         "any difference.",
         "",
         "Do **not** upload the JLC files one directory up (`../bom.csv`, `../cpl.csv`) to PCBWay: the CPL "
         "carries JLC-only corrections (`pcb/scripts/jlc_rotations.csv`) and JLC's bottom-side rotation, and the "
         "BOM only LCSC numbers. Only the Gerbers are shared.",
         "",
         "## Files",
         "",
         "| PCBWay upload | File | Contents |",
         "|---|---|---|",
         f"| Gerber file | [`../gerbers.zip`](../gerbers.zip) | the **panel**, {p['w']:.2f} x {p['h']:.2f} mm: "
         f"the board in a frame with {f['rail_min']:g} mm rails, {f['tabs']} mouse-bite tabs, "
         f"{len(p['fiducials_top'])} fiducials per side, {len(p['tooling'])} tooling holes |",
         f"| BOM | [`bom.csv`](bom.csv) | {len(info['order'])} lines, {n} parts: manufacturer and part number, "
         "description, package, SMD/THT, side, LCSC number as an alternate source |",
         f"| Centroid (pick and place) | [`centroid-panel.csv`](centroid-panel.csv) | {n} placements, "
         f"{len(bottom)} on the bottom, in the panel Gerbers' frame |",
         "",
         f"Upload the panel. J1 (USB-C) and J2 (TRRS) overhang the board edge by design, into the frame's "
         f"{f['slot']:.1f} mm milled slot; the frame carries the rails, fiducials and tooling holes and has no tab in "
         "front of either connector. Only if PCBWay refuses the panel, upload "
         f"[`../bare-board/gerbers.zip`](../bare-board/gerbers.zip) ({b['w']:.2f} x {b['h']:.2f} mm) with "
         "[`centroid-bare-board.csv`](centroid-bare-board.csv), choose Board type **Single pieces**, and ask in the "
         "remark for break-away rails with a routed gap and mouse-bites, no V-cut, and no rail or tab in front of "
         "J1 and J2.",
         "",
         "## Coordinates and rotations",
         "",
         "Both centroid files are KiCad's own position file (`kicad-cli pcb export pos --use-drill-file-origin`, "
         "millimetres) of the panel and of the board, unchanged but for the column names and the rotation "
         "written as 0-360°:",
         "",
         "- **Origin:** the drill/place origin, which is the origin of the matching Gerbers: the panel's top-left "
         "corner for `centroid-panel.csv`, the board's coordinate origin for `centroid-bare-board.csv`. Y points "
         "up, as in the Gerbers, so the Y values are negative.",
         f"- **Panel offset:** each panel centroid is the bare-board one moved by ({dx:+.4f}, {dy:+.4f}) mm, the "
         "KiKit panel's offset, read from the panel this stage builds.",
         "- **Mid X / Mid Y** is each footprint's KiCad origin, with no correction. For most parts it is the body "
         "centre. " + ("Not for these, whose pads are centred this far from the origin: " + ", ".join(off_lines)
                       + ". Place them by their pads." if off_lines else ""),
         "- **Rotation** is KiCad's footprint angle, counter-clockwise, with KiCad's library footprint as 0°. That "
         "is not always the zero orientation of IPC-7351 or of the part on its tape"
         + (f" (for {ranges(info['turned'])} it is not: JLC's CPL turns them by 90°, 180° or 270°)"
            if info["turned"] else "") + ", so align each part with its pads and polarity marks.",
         "- **Bottom side** (Layer `Bottom`): X and Y are seen from the top, through the board (X not negated), in "
         "the same frame as the Gerbers. The rotation is KiCad's: seen from the top, the part is its library "
         "footprint mirrored top to bottom, then turned counter-clockwise by the Rotation value. Seen from the "
         "bottom (the board turned over about its vertical axis), it is the footprint turned counter-clockwise by "
         "**180° minus the Rotation value**, the number bottom-view tools such as JLC's use.",
         "",
         "## PCB order form",
         "",
         "Option names as on PCBWay's form in 2026-11; pick the closest match if they change.",
         "",
         "| Option | Value |",
         "|---|---|",
         "| Board type | **Panel by Customer** |",
         "| Panel requirements | Route process **Panel as Tab Route**; X-out allowance **Not Accept**; break-away "
         "rail **Yes** (the frame in the Gerbers is the rail); different design in panel **1** |",
         f"| Size | {p['w']:.2f} x {p['h']:.2f} mm (the panel, from the Gerbers) |",
         "| Quantity | 5 (the minimum) |",
         "| Layers | **2** |",
         "| Material | FR-4, TG 130-140 (the default) |",
         "| Thickness | **1.6 mm** |",
         f"| Min track/spacing | **{info['track']}** (narrowest track {info['min_track']:.3f} mm, clearance rule "
         f"{info['min_clear']:.3f} mm) |",
         f"| Min hole size | **{info['hole']}** (smallest drill {info['min_drill']:.2f} mm) |",
         "| Solder mask | any colour (green is the default) |",
         "| Silkscreen | **White** |",
         "| UV printing (multi-colour) | **None** |",
         "| Edge connector | No |",
         "| Surface finish | **Immersion gold (ENIG)**, 1U\" |",
         "| Via process | **Tenting vias** |",
         "| Finished copper | **1 oz Cu** |",
         "| Remove product No. | Yes (extra charge) for no PCBWay number on the board; No lets PCBWay print it |",
         f"| Other special request ({REMARK_MAX} characters at most) | `{short}` |",
         "",
         "## Assembly form",
         "",
         "| Option | Value |",
         "|---|---|",
         "| Service type | **Turnkey** |",
         "| Board type | **Panelized PCBs** (Single pieces for the bare board) |",
         "| Assembly side(s) | **Both sides** |",
         "| Quantity | 2 to 5 boards (one board per panel) |",
         "| Accept alternatives/substitutes made in China | Yes, within the substitution rules below |",
         "| Function test / Firmware loading | No / No (the firmware goes on over USB, see the build guide) |",
         f"| Number of unique parts | {len(info['order'])} |",
         f"| Number of SMD parts | {len(smd)} |",
         f"| Number of BGA/QFP parts | {len(fine)}" + (f" ({', '.join(fine)}: {', '.join(fps[r]['lib'].split(':')[1] for r in fine)}, no BGA)"
                                                 if fine else "") + " |",
         f"| Number of through-hole parts | {len(tht)}" + (f" ({', '.join(tht)})" if tht else "") + " |",
         "| Depanel the boards to delivery | **No** (ship in the frame; break the tabs yourself) |",
         "",
         "## Remark",
         "",
         "Paste this into the assembly order's notes (or send it to the PCBWay engineer who reviews the files). "
         "It answers what they would otherwise ask, and each question holds the order:",
         "",
         *[f"> {line}" for line in remark],
         "",
         "## Substitution rules",
         "",
         "| Designators | BOM part | Substitute |",
         "|---|---|---|",
         *[f"| {ranges(rs)} | {e['manufacturer']} {e['mpn']} | {text} |" for rs, e, key, text in info["subs"]],
         "",
         "## Placement confirmation: what to check",
         "",
         f"- **Bottom** ({ranges(bottom)}): each hot-swap socket's curved notch wraps the round switch-centre "
         "hole and its two terminals sit on the two pads; each diode's cathode band is at pad 1 (the ROW side).",
         f"- **{ranges(pin1)}**: the pin-1 mark (dot, bevel or corner) at pad 1 and the pin-1 mark of the "
         "silkscreen" + (f"; **{ranges(diodes_top)}**: the cathode band at pad 1." if diodes_top else "."),
         "- **J1** (USB-C) and **J2** (TRRS): the pegs in their holes, the mouths over the board edge.",
         "- **J3**: on its five holes, on the top side.",
         "",
         "## Checks run on these files",
         "",
         f"- Designators: the {n} parts of the JLC BOM, which are exactly the parts `design.py` fits, each with "
         "its LCSC number; every LCSC number in `design.py` has a manufacturer part number in "
         "`pcb/scripts/mpn.json` (`pcb/scripts/mpn.py check`).",
         f"- Every centroid lies inside the Edge.Cuts of its Gerber set; the panel centroids are the bare-board "
         f"ones moved by ({dx:+.4f}, {dy:+.4f}) mm.",
         f"- Against the JLC CPL: the {cr['bare']['plain']} parts whose footprint has no row in "
         f"`pcb/scripts/jlc_rotations.csv` sit where the JLC CPL puts them (within {TOL_MM} mm, worst "
         f"{max(cr['bare']['worst_plain'], cr['panel']['worst_plain']):.4f} mm, panel and bare board), and "
         f"re-applying the row to the other {cr['bare']['corrected']} gives the JLC CPL too: the files differ only "
         "by JLC's documented corrections and bottom-side rotation.",
         ""]
    return "\n".join(L).encode()


def main(argv: list[str]) -> int:
    if len(argv) != 6:
        print(__doc__)
        return 2
    side, board, panel_pos, bare_pos, facts_path, pkg = argv
    files, info = build(side, board, Path(panel_pos), Path(bare_pos), json.loads(Path(facts_path).read_text()),
                        Path(pkg))
    out = Path(pkg) / "pcbway"
    out.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        (out / name).write_bytes(data)
    cr, (dx, dy) = info["cross"], info["offset"]
    print(f"pcbway {side}: {out}; panel offset ({dx:+.4f}, {dy:+.4f}) mm; JLC CPL re-derived for "
          f"{cr['bare']['plain']} plain + {cr['bare']['corrected']} corrected parts (worst plain "
          f"{max(cr['bare']['worst_plain'], cr['panel']['worst_plain']):.4f} mm)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
