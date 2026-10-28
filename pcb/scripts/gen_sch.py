# SPDX-License-Identifier: GPL-3.0-or-later
"""Generate the flat A1 schematic of one half from design.py (spec §9 stage 3).

    python3 pcb/scripts/gen_sch.py <side>   ->  pcb/<side>/worxboard-<side>.kicad_sch (+ .kicad_pro, lib tables)

Rules: every symbol at rotation 0; every pin gets a short wire stub ending in a global
label (no pin-to-pin wires); unused pins get a no-connect flag. Parts are packed into the
grouped regions MCU / USB-POWER / TRRS / DISPLAY / MATRIX. UUIDs are derived from the
side and the element order, so the output is reproducible.

Runs in kicad/kicad:10.0.7 with kicad-sch-api 0.5.6 on PYTHONPATH (spec §9.1).
"""
from __future__ import annotations

import json
import logging
import re
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT))

import kicad_sch_api as ksa  # noqa: E402

from design import GROUPS, Part, design  # noqa: E402

STOCK_SYMBOLS = Path("/usr/share/kicad/symbols")
LOCAL_LIB = ROOT / "pcb" / "lib"
NS = uuid.UUID("2b1d7f4c-8d0e-4f57-9a43-776f72786273")

GRID = 2.54
STUB = 2.54               # wire stub from pin to label
CHAR_W = 1.0              # approximate label character width at 1.27 mm text
LABEL_PAD = 3.0           # label arrow and margin
CELL_GAP = 5.08
PAGE = (841.0, 594.0)     # A1 landscape
MARGIN = 20.32
REGION_GAP = 10.16
HEADING = 7.62
FLAGGED_NETS = ("GND", "VSYS")    # power_in pins with no power_out driver on the net

# Region columns on the A1 sheet: group -> (column x0, width); regions in one column stack
_W = PAGE[0] - 2 * MARGIN
COLUMNS = {"MCU": (MARGIN, 300.0),
           "USB-POWER": (MARGIN + 300.0 + REGION_GAP, 250.0),
           "TRRS": (MARGIN + 550.0 + 2 * REGION_GAP, _W - 550.0 - 2 * REGION_GAP),
           "MATRIX": (MARGIN, _W)}
COLUMNS["DISPLAY"] = COLUMNS["TRRS"]


def snap(v: float) -> float:
    return round(v / GRID) * GRID


def uid(*parts: object) -> str:
    return str(uuid.uuid5(NS, "/".join(map(str, parts))))


@dataclass
class PinGeo:
    number: str
    name: str
    x: float          # library frame, y up
    y: float
    dx: float         # outward unit vector on the sheet (y down)
    dy: float


def symbol_pins(lib_id: str) -> list[PinGeo]:
    sym = ksa.get_symbol_cache().get_symbol(lib_id)
    if sym is None:
        raise SystemExit(f"symbol {lib_id} not found")
    out = []
    for p in sym.pins:
        # a pin at angle a points from its connection end into the body; the stub goes the other way
        a = round(p.rotation) % 360
        dx, dy = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}[a]
        out.append(PinGeo(str(p.number), p.name, p.position.x, p.position.y, dx, dy))
    return out


def resolve(part: Part, pins: list[PinGeo]) -> dict[str, str | None]:
    """Pin number -> net, expanding pin-name keys; every symbol pin must be assigned."""
    numbers = {p.number for p in pins}
    out: dict[str, str | None] = {}
    for key, net in part.pins.items():
        hits = [key] if key in numbers else [p.number for p in pins if p.name == key]
        if not hits:
            raise SystemExit(f"{part.ref}: no pin {key!r} on {part.lib_id}")
        for n in hits:
            out[n] = net
    missing = numbers - out.keys()
    if missing:
        raise SystemExit(f"{part.ref}: unassigned pins {sorted(missing)}")
    return out


def label_len(text: str) -> float:
    return STUB + LABEL_PAD + CHAR_W * len(text)


def extent(pins: list[PinGeo], nets: dict[str, str | None]) -> tuple[float, float, float, float]:
    """Sheet-frame box (x0, y0, x1, y1) around the symbol origin, including stubs and labels."""
    x0 = y0 = -GRID
    x1 = y1 = GRID
    for p in pins:
        net = nets[p.number]
        reach = label_len(net) if net else GRID
        x, y = p.x + p.dx * reach, -p.y + p.dy * reach
        side = 1.5 if p.dx == 0 else 0.0           # text height of vertical labels
        x0, x1 = min(x0, x - side, p.x), max(x1, x + side, p.x)
        y0, y1 = min(y0, y, -p.y), max(y1, y, -p.y)
    return x0 - GRID, y0 - 2 * GRID, x1 + GRID, y1 + 2 * GRID    # room for ref/value text


def pack(parts: list[tuple[Part, list[PinGeo], dict]], x0: float, y0: float, width: float,
         group: str) -> tuple[list[tuple[Part, float, float]], float]:
    """Shelf-pack one region left to right; returns the (part, x, y) symbol origins and the bottom."""
    cx, cy, row_h = x0, y0 + HEADING, 0.0
    placed = []
    for part, pins, nets in parts:
        ex0, ey0, ex1, ey1 = extent(pins, nets)
        w, h = ex1 - ex0, ey1 - ey0
        if cx + w > x0 + width and cx > x0:
            cx, cy, row_h = x0, cy + row_h + CELL_GAP, 0.0
        placed.append((part, snap(cx - ex0), snap(cy - ey0)))
        cx += w + CELL_GAP
        row_h = max(row_h, h)
    bottom = cy + row_h
    if bottom > PAGE[1] - MARGIN or x0 + width > PAGE[0] - MARGIN + 1e-6:
        raise SystemExit(f"region {group} overflows the A1 sheet (bottom {bottom:.1f} mm)")
    return placed, bottom


# Label angle and justification for each stub direction (label body points away from the pin)
LABEL_SPIN = {(-1, 0): (180, "right"), (1, 0): (0, "left"), (0, 1): (270, "right"), (0, -1): (90, "left")}


def add_pin_label(sch, x: float, y: float, p: PinGeo, net: str | None, seen: set, labels: list) -> None:
    key = (round(x, 3), round(y, 3))
    if key in seen:            # stacked pins (RP2040 IOVDD, DVDD) share one stub
        return
    seen.add(key)
    if net is None:
        sch.no_connects.add((x, y))
        return
    ex, ey = x + p.dx * STUB, y + p.dy * STUB
    sch.add_wire((x, y), (ex, ey))
    labels.append((net, ex, ey, *LABEL_SPIN[(p.dx, p.dy)]))


def global_label(net: str, x: float, y: float, angle: int, justify: str, n: int, side: str) -> str:
    """kicad-sch-api 0.5.6 drops global labels on save, so they are written here."""
    return (f'\t(global_label "{net}" (shape passive) (at {x:g} {y:g} {angle}) (fields_autoplaced yes)\n'
            f'\t\t(effects (font (size 1.27 1.27)) (justify {justify}))\n'
            f'\t\t(uuid "{uid(side, "label", n)}")\n'
            f'\t\t(property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at {x:g} {y:g} 0)\n'
            f'\t\t\t(effects (font (size 1.27 1.27)) (hide yes)))\n\t)\n')


def build(side: str) -> str:
    cache = ksa.get_symbol_cache()
    cache.discover_libraries([str(STOCK_SYMBOLS), str(LOCAL_LIB)])
    name = f"worxboard-{side}"
    sch = ksa.create_schematic(name)
    sch.set_paper_size("A1")
    sch.set_title_block(title=f"worxboard {side} half", rev="A", company="w0rxbend/worxboard",
                        comments={1: "Generated by pcb/scripts/gen_sch.py from design.py; do not edit",
                                  2: f"Side swap: TRRS_A/B <-> UART per spec §6.2 ({side})"})

    parts = design(side)
    flags = [Part(f"#FLG0{i + 1}", "power:PWR_FLAG", "PWR_FLAG", "", "", {"1": n}, "USB-POWER", in_bom=False)
             for i, n in enumerate(FLAGGED_NETS)]
    seen: set = set()
    labels: list = []
    bottoms: dict[str, float] = {}
    for group in GROUPS:
        members = [p for p in parts + flags if p.group == group]
        geo = []
        for p in members:
            pins = symbol_pins(p.lib_id)
            geo.append((p, pins, resolve(p, pins)))
        x0, width = COLUMNS[group]
        y0 = {"DISPLAY": bottoms.get("TRRS", 0) + REGION_GAP,
              "MATRIX": max(bottoms.values(), default=0) + REGION_GAP}.get(group, MARGIN)
        placed, bottom = pack(geo, x0, snap(y0), width, group)
        bottoms[group] = bottom
        sch.add_rectangle((x0 - GRID, y0 - GRID), (x0 + width, bottom + GRID), stroke_type="dash")
        sch.add_text(group, (x0, y0 + GRID), size=2.54, bold=True)
        for (part, x, y), (_, pins, nets) in zip(placed, geo):
            props = {"LCSC": part.lcsc} if not part.ref.startswith("#") else {}
            props.update(part.extra)
            sch.components.add(part.lib_id, reference=part.ref, value=part.value, position=(x, y),
                               footprint=part.footprint or None, rotation=0, **props)
            comp = sch.components.get(part.ref)
            comp.in_bom = part.in_bom
            comp._data.hidden_properties.update(props)      # LCSC/Key fields stay off the drawing
            for p in pins:
                add_pin_label(sch, x + p.x, y - p.y, p, nets[p.number], seen, labels)
    path = ROOT / "pcb" / side / f"{name}.kicad_sch"
    path.parent.mkdir(parents=True, exist_ok=True)
    sch.save(str(path))
    return path, {p.ref for p in parts if p.dnp}, labels


def finish(path: Path, side: str, dnp: set[str], labels: list) -> None:
    """Fix-ups for kicad-sch-api 0.5.6 output, then deterministic UUIDs.

    - global labels are appended (the library drops them);
    - `(property private "K" "V")` comes out as `(property "private" "K" V)`: restored;
    - DNP flags are set (the library always writes `dnp no`).
    """
    text = path.read_text()
    text = re.sub(r'\(property "private" "([^"]*)" ([^\n]*)\n', r'(property private "\1" "\2"\n', text)
    tail = text.rindex("\t(sheet_instances")
    text = text[:tail] + "".join(global_label(*lb, i, side) for i, lb in enumerate(labels)) + text[tail:]
    ids: dict[str, str] = {}
    text = re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
                  lambda m: ids.setdefault(m.group(0), uid(side, len(ids))), text)
    for ref in dnp:
        m = re.search(r'\(property "Reference" "%s"' % re.escape(ref), text)
        start = text.rfind("(symbol\n", 0, m.start()) if m else -1
        if start < 0 or "(dnp no)" not in text[start:m.start()]:
            raise SystemExit(f"cannot set DNP on {ref}")
        i = text.index("(dnp no)", start)
        text = text[:i] + "(dnp yes)" + text[i + len("(dnp no)"):]
    path.write_text(text)


def project_files(side: str) -> None:
    d = ROOT / "pcb" / side
    name = f"worxboard-{side}"
    pro = d / f"{name}.kicad_pro"
    root = re.search(r'\(uuid "([^"]+)"\)', (d / f"{name}.kicad_sch").read_text()).group(1)
    data = json.loads(pro.read_text()) if pro.exists() else {}   # keep what place.py adds
    data.setdefault("meta", {"filename": pro.name, "version": 3})
    data["sheets"] = [[root, "Root"]]
    pro.write_text(json.dumps(data, indent=2) + "\n")
    lib = '${KIPRJMOD}/../lib'
    for table, uri in (("sym-lib-table", f"{lib}/worxboard.kicad_sym"), ("fp-lib-table", f"{lib}/worxboard.pretty")):
        (d / table).write_text(f'({table.replace("-", "_")}\n  (version 7)\n'
                               f'  (lib (name "worxboard")(type "KiCad")(uri "{uri}")(options "")(descr "worxboard"))\n)\n')


def main(argv: list[str]) -> int:
    logging.disable(logging.WARNING)
    if len(argv) != 2:
        print(__doc__)
        return 2
    side = argv[1]
    path, dnp, labels = build(side)
    finish(path, side, dnp, labels)
    project_files(side)
    print(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
