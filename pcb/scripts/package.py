# SPDX-License-Identifier: GPL-3.0-or-later
"""Build the JLC turnkey order package of one half from KiKit's fab outputs (stage_p.sh).

    python3 pcb/scripts/package.py <side> <panel kikit dir> <bare kikit dir> <facts.json> <out dir>

<out dir> gets (committed under pcb/production/<side>/ by `just pcb-production <side>`):
  gerbers.zip, bom.csv, cpl.csv     the panel (board in a frame with rails, fiducials, tooling holes)
  README.md                         the order form, the preview checks, the panel facts
  worxboard-<side>-jlc-order.zip    the four files above, ready to hand over
  bare-board/                       gerbers.zip, bom.csv, cpl.csv, README.md for JLC-added rails
The output is byte-for-byte reproducible: the gerbers lose KiCad's creation dates, the zips carry fixed
times and order, so CI can rebuild the package from the committed boards and compare.
  gerbers.zip  copper, mask, silk, paste, Edge.Cuts, PTH and NPTH Excellon drills (KiKit names). Left
               out: KiKit's Cmts.User layer (it holds the mounting-hole circles under KiKit's "V-CUT"
               layer name), the drill maps, the drill report and the job file.
  bom.csv      Comment, Designator, Footprint, LCSC Part # (JLC's sample header; KiKit writes "LCSC")
  cpl.csv      Designator, Mid X, Mid Y, Layer, Rotation with Layer Top / Bottom (JLC's help page;
               KiKit writes T / B), positions and rotations as KiKit writes them with
               pcb/scripts/jlc_rotations.csv applied.
"""
from __future__ import annotations

import csv
import io
import json
import re
import sys
import zipfile
from pathlib import Path

GERBER_SUFFIXES = ["-CuTop.gtl", "-CuBottom.gbl", "-MaskTop.gts", "-MaskBottom.gbs", "-SilkTop.gto",
                   "-SilkBottom.gbo", "-PasteTop.gtp", "-PasteBottom.gbp", "-EdgeCuts.gm1", "-PTH.drl",
                   "-NPTH.drl"]
BOM_HEADER = ["Comment", "Designator", "Footprint", "LCSC Part #"]
CPL_HEADER = ["Designator", "Mid X", "Mid Y", "Layer", "Rotation"]
LAYER = {"T": "Top", "B": "Bottom"}
ZIP_TIME = (2026, 1, 1, 0, 0, 0)
DATE_LINES = [
    (re.compile(r"^G04 #@! TF\.CreationDate,.*\n", re.M), ""),
    (re.compile(r"^; #@! TF\.CreationDate,.*\n", re.M), ""),
    (re.compile(r"^(G04 Created by KiCad \([^)]*\)) date [^*]*\*$", re.M), r"\1*"),
    (re.compile(r"^(; DRILL file .*?) date \S+$", re.M), r"\1"),
]
DATE = re.compile(r"20\d\d-\d\d-\d\d")


def gerber_files(gerber_dir: Path) -> dict[str, bytes]:
    out = {}
    for suffix in GERBER_SUFFIXES:
        hits = sorted(p for p in gerber_dir.iterdir() if p.name.endswith(suffix)
                      and not (suffix == "-PTH.drl" and p.name.endswith("-NPTH.drl")))
        if len(hits) != 1:
            raise SystemExit(f"{gerber_dir}: expected one *{suffix}, found {[p.name for p in hits]}")
        text = hits[0].read_text()
        for pat, rep in DATE_LINES:
            text = pat.sub(rep, text)
        if DATE.search(text):
            raise SystemExit(f"{hits[0]}: a date survived normalisation: {DATE.search(text).group(0)}")
        out[hits[0].name] = text.encode()
    return out


def zip_bytes(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            info.create_system = 3
            z.writestr(info, files[name], compresslevel=9)
    return buf.getvalue()


def csv_bytes(rows: list[list[str]]) -> bytes:
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows(rows)      # LF: .gitattributes stores text as LF
    return buf.getvalue().encode()


def bom(kikit: Path) -> bytes:
    rows = list(csv.reader((kikit / "bom.csv").open(newline="", encoding="utf-8")))
    if rows[0] != ["Comment", "Designator", "Footprint", "LCSC"]:
        raise SystemExit(f"{kikit}/bom.csv: unexpected KiKit header {rows[0]}")
    return csv_bytes([BOM_HEADER] + rows[1:])


def cpl(kikit: Path) -> bytes:
    rows = list(csv.reader((kikit / "pos.csv").open(newline="", encoding="utf-8")))
    if rows[0] != CPL_HEADER:
        raise SystemExit(f"{kikit}/pos.csv: unexpected KiKit header {rows[0]}")
    return csv_bytes([CPL_HEADER] + [[d, x, y, LAYER[layer], r] for d, x, y, layer, r in rows[1:]])


def hole_remark(facts: dict) -> list[str]:
    """Remark lines for the hole pairs closer than JLC's pad hole-to-hole spacing (jlc_check.py facts
    allows them only between stabiliser footprints; deviations ORDER-3)."""
    pairs = facts["close_holes"]
    if not pairs:
        return []
    refs = sorted({r for h in pairs for r in h[:2]})
    gap = min(h[2] for h in pairs)
    return [f"NPTH: {len(pairs)} pairs of stabiliser clearance holes ({'/'.join(refs)}) leave {gap:.2f} mm between "
            f"them, under the {facts['hole_gap']} mm hole-to-hole spacing.",
            "Intended: no plating, no copper; they may break into each other."]


def turned_check(facts: dict) -> list[str]:
    """The preview check that tells JLC's bottom-side reading from KiKit's (deviations ORDER-2): a viewer
    that turns bottom parts the other way shows every part at 0 or 180 degrees as before and only the
    others off, by twice their angle."""
    t = facts["bottom_turned"]
    out = ["The bottom rows follow the convention KiKit, kicad-jlcpcb-tools and KiBot use for JLC (top-view X/Y,",
           "rotation 180° minus the KiCad angle plus the correction). JLC does not document its bottom side.",
           "A viewer that reads it another way shows one of two patterns:",
           ""]
    if t["n"]:
        rot = ", ".join(f"{r:g}°" for r in t["rot"])
        alt = ", ".join(f"{(360 - r) % 360:g}°" for r in t["rot"])
        off = ", ".join(f"{min(2 * r % 360, 360 - 2 * r % 360):g}°" for r in t["rot"])
        out += [f"- **Only the {t['n']} thumb parts {t['refs']} turned by about {off}** (the sockets several mm",
                "  off their pads), and every other bottom part right: the viewer turns bottom parts the other",
                f"  way round. Parts at 180° look the same either way, so these {t['n']} are the ones to look at.",
                f"  They need 360° minus the CPL value: **{alt}** instead of {rot}."]
    out += ["- **Every socket and diode on the bottom turned 180°:** the viewer mirrors bottom parts about the",
            "  other axis.",
            "",
            "In either case, do not edit the files: ask for the correction in the placement confirmation, with",
            "the designators and the rotation they need."]
    return out


def readme(side: str, facts: dict, bare: bool) -> bytes:
    p, b = facts["panel"], facts["bare"]
    n, nb = facts["parts"], facts["bottom_parts"]
    lines = [f"# worxboard {side} half: JLCPCB turnkey order" + (" (bare board, JLC-added rails)" if bare else ""),
             "",
             "Generated by `just pcb-production " + side + "` from the committed board; do not edit. CI rebuilds "
             "these files from the board and fails on any difference.",
             ""]
    if bare:
        lines += [
            f"The bare board ({b['w']:.2f} x {b['h']:.2f} mm) without rails. Prefer the panel one directory up;",
            "use these only if you want JLC to add the assembly rails and fiducials.",
            "",
            "| Upload | File |",
            "|---|---|",
            "| Gerber file | `gerbers.zip` |",
            "| BOM file | `bom.csv` |",
            "| CPL file | `cpl.csv` |",
            "",
            "Form differences from the panel order: Delivery format **Single PCB**; Edge rails/fiducials",
            "**Added by JLCPCB**; Tooling holes **Added by JLCPCB**. Paste this as the PCB remark:",
            "",
            "> Standard PCBA, both sides. Please add the assembly edge rails with a >= 2 mm routed gap and",
            "> mouse-bite tabs (no V-cut). J1 (USB-C) overhangs the back edge by 0.5 mm and J2 (TRRS) the",
            "> bump edge: no rail or tab in front of J1/J2. Keep tooling holes and fiducials on the rails",
            "> only, no holes inside the board outline. Deliver with rails attached.",
            "> J1 (USB-C, C165948): please solder its 4 through-hole shell legs (GND) too. The paste layer opens "
            "them for pin-in-paste.",
        ] + [f"> {line}" for line in hole_remark(facts)] + [
            "",
            "Everything else (settings, preview checks, after delivery) is as in `../README.md`.",
            ""]
        return "\n".join(lines).encode()
    lines += [
        "## Files",
        "",
        "| Upload as | File | Contents |",
        "|---|---|---|",
        f"| Gerber file | `gerbers.zip` | the panel, {p['w']:.2f} x {p['h']:.2f} mm: copper, mask, silk, paste, "
        "Edge.Cuts, PTH and NPTH drills |",
        f"| BOM file | `bom.csv` | {facts['bom_lines']} lines, {facts['lcsc_numbers']} LCSC part numbers, one on every line |",
        f"| CPL file | `cpl.csv` | {n} placements, {nb} on the bottom, JLC rotations and centroids applied |",
        "",
        f"`worxboard-{side}-jlc-order.zip` holds the same three files and this README. `bare-board/` holds the",
        "board without the panel frame, for an order where JLC adds the rails.",
        "",
        "## The panel",
        "",
        f"- One board ({b['w']:.2f} x {b['h']:.2f} mm) in a frame ({p['w']:.2f} x {p['h']:.2f} mm, inside "
        "JLC's 250 x 250 mm Standard PCBA panel limit). The frame is solid: only a "
        f"{facts['slot']:.1f} mm slot round the board is milled out, so the board is held all round.",
        f"- Rails {facts['rail_min']:.1f} mm wide or more on every side (JLC: at least 5 mm).",
        f"- {facts['tabs']} tabs, each with a row of Ø{facts['bite_d']:.1f} mm mouse-bite holes on the board "
        f"edge, {facts['bite_clear_min']:.1f} mm or more from any part's courtyard and "
        f"{facts['bite_clear_j1_j2']:.1f} mm or more from J1 (USB-C) and J2 (TRRS), whose mouths overhang the "
        "edge into the slot.",
        f"- {len(p['fiducials_top'])} fiducials on each side: Ø{facts['fid_copper']:.1f} mm copper in a "
        f"Ø{facts['fid_opening']:.1f} mm mask opening, centres {facts['fid_edge']:.2f} mm or more from the panel "
        "edges (JLC: 3.85 mm).",
        f"- {len(p['tooling'])} non-plated tooling holes Ø{facts['tool_d']:.1f} mm in the rail corners (JLC's "
        "SMT guideline of 2026-09: 2 mm; its older FAQ gives 1.152 mm, JLC adds its own if it needs others).",
        f"- Panel DRC: {facts['drc_errors']} errors, {facts['drc_unconnected']} unconnected items.",
        "",
        "## PCB order form",
        "",
        "Option names follow JLC's order form, whose wording changes now and then: pick the closest match.",
        "",
        "| Option | Value |",
        "|---|---|",
        "| Base material / layers | FR-4, **2** layers |",
        "| Dimensions | taken from the Gerbers |",
        "| PCB qty | 5 (the minimum) |",
        "| Product type | Industrial/Consumer electronics |",
        "| Delivery format | **Panel by Customer**: one board per panel (1 x 1 if the form asks) |",
        "| PCB thickness | **1.6 mm** |",
        "| Surface finish | **ENIG** |",
        "| Outer copper weight | 1 oz |",
        "| Via covering | Tented |",
        "| Min via hole size / diameter | 0.3 mm / (0.4/0.45 mm), the default |",
        "| Board outline tolerance | ±0.2 mm |",
        "| Mark on PCB | none |",
        "| Confirm production file | **Yes** |",
        "",
        "## PCBA order form",
        "",
        "| Option | Value |",
        "|---|---|",
        "| PCBA type | **Standard** (Economic places one side only) |",
        "| Assembly side | **Both sides** |",
        "| PCBA qty | 2 to 5 |",
        "| Tooling holes | **Added by Customer** |",
        "| Edge rails / fiducials | **Added by Customer** |",
        "| Confirm parts placement | **Yes** |",
        "| Depanel / remove edge rails | No (break the tabs yourself, see below) |",
        "",
        "J3 (display socket, C27985230) is a through-hole part: JLC solders it by hand, so the quote carries a",
        "small THT fee. Every other part is SMT. J1's four shell legs go through plated slots, but the paste",
        "layer opens them (pin-in-paste), so they reflow with J1's pins; the remark asks for them as well.",
        "Nothing is left for you to solder on the board.",
        "",
        "## Remark",
        "",
        "Paste this into the order's remark field. It answers what JLC's engineers would otherwise ask about,",
        "and each question puts the order on hold:",
        "",
        f"> Panel by customer: 1 board in a frame, {facts['rail_min']:g} mm rails, {len(p['fiducials_top'])} "
        f"fiducials per side, {len(p['tooling'])} tooling holes ({facts['tool_d']:.1f} mm).",
        "> J1 (USB-C) and J2 (TRRS) overhang the board edge into the milled slot on purpose.",
        "> J1 (USB-C, C165948): please solder its 4 through-hole shell legs (GND) too. The paste layer opens them "
        "for pin-in-paste.",
        "> Bottom side: 37 hot-swap sockets SK101-SK137 and 37 diodes D101-D137. J3 is a THT socket (hand solder).",
    ] + [f"> {line}" for line in hole_remark(facts)] + [
        "> Ship with the frame attached.",
        "",
        "## Placement preview: what to check",
        "",
        "`cpl.csv` was checked by `pcb/scripts/cpl_check.py`, which places JLC's own footprint of every part",
        "(EasyEDA / JLCEDA library) where the CPL puts it and compares it with the KiCad pads; the drawings are",
        "`docs/images/cpl-*.svg`. JLC documents only the top side, so check the bottom side by eye:",
        "",
        "- **Bottom, SK101-SK137** (hot-swap sockets): each socket's curved notch wraps the big round",
        "  switch-centre hole, and its two pads sit on the two pads. A socket turned 180° also covers its",
        "  pads but hides the centre hole under its body: rotate it 180° if you see that.",
        "- **Bottom, D101-D137**: the cathode bar on the diode is at pad 1 (the ROW side).",
        "- **U1** (RP2040): the pin-1 dot at the pin-1 corner of the silkscreen.",
        "- **U2, U3, U4, U5, Y1**: pin 1 on the pin-1 pad.",
        "- **J1** (USB-C): the two plastic pegs in the two small holes, the four shell legs in their slots,",
        "  the mouth over the back edge.",
        "- **J2** (TRRS): the two pegs in their holes, the mouth over the bump edge.",
        "- **J3**: on its five holes.",
        "",
    ] + turned_check(facts) + [
        "",
        "## After delivery",
        "",
        "Break the board out of the frame at the mouse-bite tabs and file or sand each tab flush with the",
        "board edge: the case leaves about 0.3 mm round the PCB.",
        "",
        "## Checks run on these files",
        "",
        "- `pcb/scripts/cpl_check.py`: every placement within 0.1 mm of the best fit of JLC's footprint onto",
        "  the KiCad pads, pin 1 on pin 1, every terminal on its pad, the socket bodies clear of the switch",
        "  holes.",
        "- `pcb/scripts/jlc_check.py`: file formats and headers, BOM and CPL list the same parts, exactly the",
        "  parts design.py fits (JP1, TP*, H*, STAB_* stay out), panel size, rails, fiducials, tooling holes.",
        "  `--stock 5` adds a live JLC stock check; run it on the day you order.",
        f"- `pcb/scripts/jlc_check.py facts`: no two pad holes closer than {facts['hole_gap']} mm (JLC's pad",
        "  hole-to-hole spacing) but the stabiliser pairs in the remark.",
        "- KiCad DRC on the panel, and on the board itself in the PCB pipeline.",
        ""]
    return "\n".join(lines).encode()


def main(argv: list[str]) -> int:
    if len(argv) != 5:
        print(__doc__)
        return 2
    side, panel, bare, facts_path, out = argv[0], Path(argv[1]), Path(argv[2]), Path(argv[3]), Path(argv[4])
    facts = json.loads(facts_path.read_text())
    out.mkdir(parents=True, exist_ok=True)
    (out / "bare-board").mkdir(exist_ok=True)
    for src, dst, is_bare in ((panel, out, False), (bare, out / "bare-board", True)):
        files = {"gerbers.zip": zip_bytes(gerber_files(src / "gerber")), "bom.csv": bom(src),
                 "cpl.csv": cpl(src), "README.md": readme(side, facts, is_bare)}
        for name, data in files.items():
            (dst / name).write_bytes(data)
        if not is_bare:
            (dst / f"worxboard-{side}-jlc-order.zip").write_bytes(zip_bytes(files))
    print(f"package {side}: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
