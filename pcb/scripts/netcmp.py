# SPDX-License-Identifier: GPL-3.0-or-later
"""Check an exported KiCad netlist, a board and its JLC BOM / CPL against design.py (spec §9
stages 6, 12, 13). Stdlib + layout only.

    python3 pcb/scripts/netcmp.py build/<side>/<side>.net <side>
    python3 pcb/scripts/netcmp.py --board pcb/<side>/worxboard-<side>.kicad_pcb <side> [build/<side>/jlc]

Parses the s-expression netlist (KiCad 10, version "E") and asserts:
  - every design.py part is present with its symbol, value, footprint and LCSC, and every
    pin sits on its design net (None = an unconnected single-pin net), and nothing else exists
  - each of the 37 diodes has its anode on the switch/COL side and its cathode on a ROW net
  - the (row, col) of every key matches §5 (`layout.keys`)
  - every GPIO net matches layout/pins.py (by RP2040 symbol pin name)
  - Tip/Ring1 reach TX/RX on the left and RX/TX on the right through 1 kΩ
  - CC1/CC2 each have 5.1k to GND
  - every RP2040 supply pin has a capacitor to GND on its net
  - the USB-C VBUS reaches only J1, D1's anode and the R5 sense divider (nothing can back-drive it),
    and the ESD arrays take their clamp reference from VSYS (U4) and VLINK (U5)
  - every BOM part has a non-empty LCSC field, and none is a part this design retired
  - the matrix nets are identical to the other half (design.py, and its netlist when built)

With --board it checks that the board agrees with design.py, as the order needs: kikit takes bom.csv
from the schematic but pos.csv, its rotation corrections (by board footprint name) and the gerbers
from the board, and KiCad's schematic parity ignores the LCSC field (docs/deviations.md ELEC-6):
  - every board footprint is a design.py part with its footprint, value, LCSC number and
    DNP / BOM / CPL attributes, or a board-only part (stabiliser holes) kept out of BOM and CPL
  - no retired LCSC number (design.RETIRED) is on the board
  - J3 meets the nice!view the right way round: pad n where module pin n plugs in (gate G1)
  - with the kikit output directory: bom.csv and pos.csv list exactly the parts JLC fits, each
    bom.csv line with the design.py LCSC number of every designator on it
"""
from __future__ import annotations

import csv
import math
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT))

import layout  # noqa: E402
from design import RETIRED, SUPPLY_PIN_NAMES, Part, design, switch_net  # noqa: E402
from layout.display import HEADER_PIN_ORDER  # noqa: E402
from layout.pins import PINS, TRRS  # noqa: E402

TOKEN = re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+')
MATRIX_NET = re.compile(r"^(ROW\d|COL\d|MX_\w+)$")
UNCONNECTED = "unconnected-"


def parse(text: str) -> list:
    """S-expression -> nested lists of str (quotes removed)."""
    stack: list[list] = [[]]
    for tok in TOKEN.findall(text):
        if tok == "(":
            stack.append([])
        elif tok == ")":
            done = stack.pop()
            stack[-1].append(done)
        else:
            stack[-1].append(tok[1:-1].replace('\\"', '"') if tok.startswith('"') else tok)
    return stack[0][0]


def find(node: list, key: str) -> list | None:
    return next((c for c in node[1:] if isinstance(c, list) and c and c[0] == key), None)


def find_all(node: list, key: str) -> list[list]:
    return [c for c in node[1:] if isinstance(c, list) and c and c[0] == key]


def val(node: list, key: str, default: str = "") -> str:
    c = find(node, key)
    return c[1] if c and len(c) > 1 and isinstance(c[1], str) else default


@dataclass
class Comp:
    ref: str
    value: str
    footprint: str
    lib_id: str
    fields: dict[str, str]
    props: dict[str, str]
    pins: dict[str, tuple[str, str]] = field(default_factory=dict)   # number -> (name, net)

    @property
    def in_bom(self) -> bool:
        return "exclude_from_bom" not in self.props and "dnp" not in self.props and not self.ref.startswith("#")

    def pin_net(self, key: str) -> list[str]:
        """Nets of the pin with this number, else of every pin with this name."""
        if key in self.pins:
            return [self.pins[key][1]]
        return [net for name, net in self.pins.values() if name == key]


@dataclass
class Netlist:
    comps: dict[str, Comp]
    nets: dict[str, set[tuple[str, str]]]      # net -> {(ref, pin number)}

    def others(self, net: str, ref: str) -> list[tuple[Comp, str]]:
        return [(self.comps[r], p) for r, p in self.nets[net] if r != ref]


def load(path: Path) -> Netlist:
    root = parse(path.read_text())
    if val(root, "version") != "E":
        raise SystemExit(f"{path}: expected netlist version E")
    comps = {}
    for c in find_all(find(root, "components"), "comp"):
        lib = find(c, "libsource")
        fields = {val(f, "name"): (f[2] if len(f) > 2 else "") for f in find_all(find(c, "fields") or ["fields"], "field")}
        props = {val(p, "name"): val(p, "value") for p in find_all(c, "property")}
        comps[val(c, "ref")] = Comp(val(c, "ref"), val(c, "value"), val(c, "footprint"),
                                    f"{val(lib, 'lib')}:{val(lib, 'part')}", fields, props)
    nets: dict[str, set] = {}
    for n in find_all(find(root, "nets"), "net"):
        name = val(n, "name")
        nets[name] = set()
        for node in find_all(n, "node"):
            ref, pin = val(node, "ref"), val(node, "pin")
            fn = val(node, "pinfunction")
            fn = fn[: -len(pin) - 1] if fn.endswith(f"_{pin}") else fn      # KiCad suffixes _<number>
            comps[ref].pins[pin] = (fn, name)
            nets[name].add((ref, pin))
    return Netlist(comps, nets)


class Checker:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.passed: list[str] = []

    def section(self, title: str, errs: list[str]) -> None:
        if errs:
            self.errors += [f"{title}: {e}" for e in errs]
        else:
            self.passed.append(title)


def check_design(nl: Netlist, parts: list[Part]) -> list[str]:
    errs = []
    want = {p.ref for p in parts}
    have = {r for r in nl.comps if not r.startswith("#")}
    errs += [f"missing {r}" for r in sorted(want - have)] + [f"unexpected {r}" for r in sorted(have - want)]
    for p in parts:
        c = nl.comps.get(p.ref)
        if c is None:
            continue
        for attr, exp, got in (("symbol", p.lib_id, c.lib_id), ("value", p.value, c.value),
                               ("footprint", p.footprint, c.footprint), ("LCSC", p.lcsc, c.fields.get("LCSC", ""))):
            if exp != got:
                errs.append(f"{p.ref} {attr} {got!r} != {exp!r}")
        if p.dnp != ("dnp" in c.props) or p.in_bom == ("exclude_from_bom" in c.props):
            errs.append(f"{p.ref} BOM/DNP flags differ from design")
        assigned = set()
        for key, net in p.pins.items():
            nets = c.pin_net(key)
            if not nets:
                errs.append(f"{p.ref} pin {key} not in netlist")
            for got in nets:
                ok = got.startswith(UNCONNECTED) and len(nl.nets[got]) == 1 if net is None else got == net
                if not ok:
                    errs.append(f"{p.ref}.{key} on {got!r}, design {net!r}")
            assigned |= {n for n, (name, _) in c.pins.items() if n == key or name == key}
        errs += [f"{p.ref} pin {n} not in design" for n in sorted(set(c.pins) - assigned)]
    return errs


def check_matrix(nl: Netlist, side: str) -> tuple[list[str], list[str]]:
    diode_errs, key_errs = [], []
    keys = layout.keys(side)
    by_key = {c.fields.get("Key"): c for c in nl.comps.values() if c.lib_id == "Diode:1N4148W"}
    sockets = {c.fields.get("Key"): c for c in nl.comps.values() if c.lib_id == "worxboard:SW_Push_MX"}
    if len(by_key) != layout.KEYS_PER_HALF or len(sockets) != layout.KEYS_PER_HALF:
        diode_errs.append(f"{len(by_key)} diodes / {len(sockets)} sockets, want {layout.KEYS_PER_HALF}")
    rcs = set()
    for k in keys:
        d, s = by_key.get(k.id), sockets.get(k.id)
        if d is None or s is None:
            key_errs.append(f"key {k.id} has no socket/diode")
            continue
        (anode,), (cathode,) = d.pin_net("A"), d.pin_net("K")
        members = nl.nets[anode]
        sw_side = {(r, nl.comps[r].pins[p][0]) for r, p in members}
        if anode != switch_net(k.id) or sw_side != {(d.ref, "A"), (s.ref, "2")}:
            diode_errs.append(f"{d.ref} anode net {anode} is not the {s.ref} switch node")
        if not re.fullmatch(r"ROW\d", cathode):
            diode_errs.append(f"{d.ref} cathode on {cathode}, not a ROW net")
        (col,) = s.pin_net("1")
        row = int(cathode[3:]) if cathode.startswith("ROW") else -1
        if (row, col) != (k.row, f"COL{k.col}"):
            key_errs.append(f"{k.id}: ROW{row}/{col}, want ROW{k.row}/COL{k.col}")
        rcs.add(k.rc(side))
    if len(rcs) != layout.KEYS_PER_HALF:
        key_errs.append("duplicate (row, col) matrix positions")
    return diode_errs, key_errs


def check_gpio(nl: Netlist) -> list[str]:
    u1 = nl.comps["U1"]
    errs = []
    for p in PINS:
        nets = u1.pin_net(p.name)
        if len(nets) != 1:
            errs.append(f"{p.name}: {len(nets)} pins")
            continue
        got = nets[0]
        ok = got.startswith(UNCONNECTED) if p.net is None else got == p.net
        if not ok:
            errs.append(f"{p.name} on {got}, pins.py says {p.net}")
    return errs


def via_resistor(nl: Netlist, net: str, value: str) -> set[str]:
    """Nets reached from `net` through one resistor of the given value."""
    out = set()
    for c, pin in nl.others(net, ""):
        if c.lib_id == "Device:R" and c.value == value:
            other = "2" if pin == "1" else "1"
            out.add(c.pins[other][1])
    return out


def check_trrs(nl: Netlist, side: str) -> list[str]:
    j2, t = nl.comps["J2"], TRRS[side]
    errs = []
    for contact in ("T", "R1", "R2", "S"):
        (net,) = j2.pin_net(contact)
        if net != t[contact]:
            errs.append(f"J2.{contact} on {net}, want {t[contact]}")
    for contact in ("T", "R1"):
        (jack,) = j2.pin_net(contact)
        uart = t[t[contact]]
        if via_resistor(nl, jack, "1k") != {uart}:
            errs.append(f"{contact} ({jack}) does not reach {uart} through 1k")
    return errs


def check_cc(nl: Netlist) -> list[str]:
    j1 = nl.comps["J1"]
    return [f"{cc} lacks 5.1k to GND" for cc in ("CC1", "CC2")
            if "GND" not in via_resistor(nl, j1.pin_net(cc)[0], "5.1k")]


def check_decoupling(nl: Netlist) -> list[str]:
    u1, errs = nl.comps["U1"], []
    for num, (name, net) in sorted(u1.pins.items()):
        if name not in SUPPLY_PIN_NAMES:
            continue
        caps = [c for c, pin in nl.others(net, "U1")
                if c.lib_id == "Device:C" and c.pins["2" if pin == "1" else "1"][1] == "GND"]
        if not caps:
            errs.append(f"U1.{num} {name} ({net}) has no capacitor to GND")
    return errs


# USB-C VBUS loads that cannot source current into it, and the ESD clamp references (deviation ELEC-2)
VBUS_LOADS = {("J1", "VBUS"), ("D1", "A"), ("R5", None)}
ESD_REFERENCE = {"U4": "VSYS", "U5": "VLINK"}


def check_power(nl: Netlist) -> list[str]:
    errs = []
    members = {(r, nl.comps[r].pins[p][0]) for r, p in nl.nets.get("VBUS", set())}
    loads = {(r, None if (r, None) in VBUS_LOADS else name) for r, name in members}
    errs += [f"VBUS reaches {r}.{name}" for r, name in sorted(loads - VBUS_LOADS, key=str)]
    errs += [f"VBUS misses {r}{'.' + n if n else ''}" for r, n in sorted(VBUS_LOADS - loads, key=str)]
    for ref, net in ESD_REFERENCE.items():
        got = nl.comps[ref].pin_net("VBUS") if ref in nl.comps else []
        if got != [net]:
            errs.append(f"{ref} VBUS (clamp reference) on {got}, want {net}")
    return errs


def retired(code: str) -> str:
    return f"retired {code} ({RETIRED[code]})"


def check_lcsc(nl: Netlist) -> list[str]:
    errs = [f"{c.ref} has no LCSC" for c in nl.comps.values() if c.in_bom and not c.fields.get("LCSC", "").strip()]
    return errs + [f"{c.ref} carries {retired(c.fields['LCSC'])}" for c in nl.comps.values()
                   if c.fields.get("LCSC", "").strip() in RETIRED]


def matrix_of(nl: Netlist) -> dict[str, frozenset]:
    """Matrix nets keyed by name, members as (ref, pin name) for a side-independent compare."""
    return {n: frozenset((r, nl.comps[r].pins[p][0] or p) for r, p in m) for n, m in nl.nets.items()
            if MATRIX_NET.match(n)}


def design_matrix(parts: list[Part]) -> dict[str, frozenset]:
    """design.py matrix nets in the same form (matrix pin keys equal the pin names)."""
    nets: dict[str, set] = defaultdict(set)
    for p in parts:
        for key, net in p.pins.items():
            if net and MATRIX_NET.match(net):
                nets[net].add((p.ref, key))
    return {n: frozenset(v) for n, v in nets.items()}


def check_mirror(nl: Netlist, side: str, path: Path) -> list[str]:
    other = "right" if side == "left" else "left"
    mine = matrix_of(nl)
    errs = []
    if mine != design_matrix(design(other)):
        errs.append(f"matrix nets differ from design.py {other}")
    other_net = path.parent.parent / other / f"{other}.net"
    if other_net.exists():
        if mine != matrix_of(load(other_net)):
            errs.append(f"matrix nets differ from {other_net}")
    else:
        print(f"note: {other_net} not built yet; compared with design.py {other} only")
    return errs


# --- The board and the JLC BOM / CPL kikit builds from it (stages 12-13) --------------------------

BOARD_FLAGS = ("dnp", "exclude_from_bom", "exclude_from_pos_files")


@dataclass
class BoardPart:
    ref: str
    footprint: str              # library id, e.g. worxboard:SW_MX_Hotswap_Kailh
    value: str
    lcsc: str
    attrs: frozenset[str]       # smd / through_hole / board_only / dnp / exclude_from_* ...
    pads: dict[str, tuple[float, float]] = field(default_factory=dict)   # pad number -> board x, y


def pad_positions(fp: list) -> dict[str, tuple[float, float]]:
    """Board x, y of each numbered pad. KiCad keeps pad positions in the footprint frame; the footprint
    angle turns them counter-clockwise on screen (y down)."""
    x, y, *rot = map(float, find(fp, "at")[1:])
    a = math.radians(rot[0] if rot else 0.0)
    out = {}
    for pad in find_all(fp, "pad"):
        if pad[1]:
            u, v = map(float, find(pad, "at")[1:3])
            out[pad[1]] = (x + u * math.cos(a) + v * math.sin(a), y - u * math.sin(a) + v * math.cos(a))
    return out


def load_board(path: Path) -> list[BoardPart]:
    out = []
    for fp in find_all(parse(path.read_text()), "footprint"):
        props = {p[1]: (p[2] if len(p) > 2 else "") for p in find_all(fp, "property")}
        attr = find(fp, "attr") or ["attr"]
        out.append(BoardPart(props.get("Reference", ""), fp[1], props.get("Value", ""),
                             props.get("LCSC", "").strip(), frozenset(a for a in attr[1:] if isinstance(a, str)),
                             pad_positions(fp)))
    return out


def natural(ref: str) -> tuple[str, int]:
    m = re.fullmatch(r"(\D*)(\d*)", ref)
    return (m.group(1), int(m.group(2) or 0)) if m else (ref, 0)


def check_board(board: list[BoardPart], parts: list[Part]) -> list[str]:
    errs = [f"{r} is on the board {n} times" for r, n in Counter(b.ref for b in board).items() if n > 1]
    want = {p.ref: p for p in parts}
    have = {b.ref: b for b in board}
    errs += [f"{r} missing from the board" for r in sorted(set(want) - set(have))]
    wrong: dict[tuple[str, str, str], list[str]] = defaultdict(list)    # (attr, board, design) -> refs
    for ref, b in sorted(have.items(), key=lambda kv: natural(kv[0])):
        p = want.get(ref)
        if p is None:
            if "board_only" not in b.attrs:
                errs.append(f"{ref} ({b.footprint}) is on the board but not in design.py")
            elif b.lcsc or not {"exclude_from_bom", "exclude_from_pos_files"} <= b.attrs:
                errs.append(f"{ref} is board-only: it needs no LCSC and must stay out of the BOM and CPL")
            continue
        for attr, exp, got in (("footprint", p.footprint, b.footprint), ("value", p.value, b.value),
                               ("LCSC", p.lcsc, b.lcsc)):
            if exp != got:
                wrong[(attr, got, exp)].append(ref)
        if b.lcsc == p.lcsc and b.lcsc in RETIRED:
            errs.append(f"{ref} carries {retired(b.lcsc)}")
        flags = frozenset(f for f in BOARD_FLAGS if f in b.attrs)
        exp_flags = frozenset(f for f, on in zip(BOARD_FLAGS, (p.dnp, not p.in_bom, not p.in_bom)) if on)
        if flags != exp_flags:
            errs.append(f"{ref} is {flag_text(flags)} on the board, {flag_text(exp_flags)} in design.py")
    for (attr, got, exp), refs in wrong.items():
        note = f": {retired(got)}" if attr == "LCSC" and got in RETIRED else ""
        errs.append(f"{ref_text(refs)} {attr} {got!r} on the board, {exp!r} in design.py{note}")
    return errs


# nice!view (gate G1, docs/verification.md): seen from the LCD side with its header at the bottom, the
# module's pins are MOSI, SCK, VCC, GND, CS from left to right (nicekeyboards.com pinout drawing), and
# J3 pin n carries module pin n (design.py). Plugged in LCD up, the module runs from J3 over the case
# window: turning the front view so its header-to-LCD direction (screen up) points there turns its
# left-to-right pin direction alike, a quarter turn clockwise on screen from the header-to-LCD one.
J3_PINS = 5
J3_PITCH = 2.54
PAD_TOL = 0.05


def check_display(board: list[BoardPart], side: str) -> list[str]:
    """J3 pad n sits where pin n of a nice!view plugged in LCD up meets the board."""
    j3 = next((b for b in board if b.ref == "J3"), None)
    pads = [j3.pads.get(str(n)) for n in range(1, J3_PINS + 1)] if j3 else []
    if not pads or None in pads:
        return [f"J3 must have pads 1-{J3_PINS} on the board"]
    cx, cy = (sum(p[i] for p in pads) / J3_PINS for i in (0, 1))
    wx, wy = layout.display(side)["window_centre"]
    norm = math.hypot(wx - cx, wy - cy)
    ux, uy = (wx - cx) / norm, (wy - cy) / norm        # header -> LCD (KiCad screen frame, y down)
    ex, ey = -uy, ux                                   # module pin 1 -> pin 5
    mid = (J3_PINS + 1) / 2
    want = [(cx + (n - mid) * J3_PITCH * ex, cy + (n - mid) * J3_PITCH * ey) for n in range(1, J3_PINS + 1)]
    if all(math.dist(p, w) <= PAD_TOL for p, w in zip(pads, want)):
        return []
    names = HEADER_PIN_ORDER
    over = [i for i in range(J3_PINS) if math.dist(pads[0], want[i]) <= PAD_TOL]
    meets = f"the nice!view's pin {over[0] + 1} ({names[over[0]]})" if over else "no nice!view pin"
    ax, ay = pads[-1][0] - pads[0][0], pads[-1][1] - pads[0][1]
    turn = round(math.degrees(abs(math.atan2(ax * ey - ay * ex, ax * ex + ay * ey))))
    return [f"J3 pad 1 at ({pads[0][0]:.2f}, {pads[0][1]:.2f}) meets {meets}; its pin 1 ({names[0]}) is at "
            f"({want[0][0]:.2f}, {want[0][1]:.2f}). Turn J3 by {turn} deg so pad n sits under module pin n "
            f"(docs/verification.md G1 item 1)"]


def ref_text(refs: list[str]) -> str:
    """SK101 or "SK101..SK137 (37 parts)": one error line per wrong value, not per designator."""
    return refs[0] if len(refs) == 1 else f"{refs[0]}..{refs[-1]} ({len(refs)} parts)"


def flag_text(flags: frozenset[str]) -> str:
    return " ".join(f for f in BOARD_FLAGS if f in flags) or "fitted"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return [{k.strip(): (v or "").strip() for k, v in row.items() if k} for row in csv.DictReader(f)]


def check_fab(jlc: Path, parts: list[Part]) -> list[str]:
    """kikit's bom.csv (Comment, Designator, Footprint, LCSC) and pos.csv (Designator, ...)."""
    missing = [f"{jlc / f} missing" for f in ("bom.csv", "pos.csv") if not (jlc / f).is_file()]
    if missing:
        return missing
    fitted = {p.ref: p.lcsc for p in parts if p.in_bom and not p.dnp}
    errs, bom = [], Counter()
    wrong: dict[tuple[str, str], list[str]] = defaultdict(list)          # (bom.csv, design) -> refs
    for row in read_csv(jlc / "bom.csv"):
        code, refs = row.get("LCSC", ""), [r.strip() for r in row.get("Designator", "").split(",") if r.strip()]
        if code in RETIRED:
            errs.append(f"bom.csv line {ref_text(refs)} carries {retired(code)}")
        for r in refs:
            bom[r] += 1
            if r not in fitted:
                errs.append(f"bom.csv lists {r}, which JLC must not fit")
            elif code != fitted[r]:
                wrong[(code, fitted[r])].append(r)
    errs += [f"bom.csv gives {ref_text(refs)} {code!r}, design.py {exp!r}" for (code, exp), refs in wrong.items()]
    pos = Counter(row.get("Designator", "") for row in read_csv(jlc / "pos.csv"))
    for name, got in (("bom.csv", bom), ("pos.csv", pos)):
        errs += [f"{name} lists {r} {n} times" for r, n in sorted(got.items()) if n > 1]
        errs += [f"{name} lacks {r}" for r in sorted(set(fitted) - set(got))]
    errs += [f"pos.csv places {r}, which JLC must not fit" for r in sorted(set(pos) - set(fitted))]
    return errs


def report(ck: Checker, what: str) -> int:
    for t in ck.passed:
        print(f"PASS  {t}")
    for e in ck.errors:
        print(f"FAIL  {e}")
    print(f"netcmp {what}: {len(ck.passed)} passed, {len(ck.errors)} errors")
    return 1 if ck.errors else 0


def main_board(argv: list[str]) -> int:
    if len(argv) not in (2, 3) or argv[1] not in layout.SIDES:
        print(__doc__)
        return 2
    path, side = Path(argv[0]), argv[1]
    parts, board = design(side), load_board(path)
    ck = Checker()
    ck.section(f"{path.name} footprint/value/LCSC/DNP per design.py", check_board(board, parts))
    ck.section("J3 pad n under nice!view pin n (G1)", check_display(board, side))
    if len(argv) == 3:
        jlc = Path(argv[2])
        n = sum(p.in_bom and not p.dnp for p in parts)
        ck.section(f"{jlc}/bom.csv + pos.csv: the {n} parts JLC fits, design.py LCSC", check_fab(jlc, parts))
    return report(ck, f"--board {side} ({len(board)} footprints)")


def main(argv: list[str]) -> int:
    if len(argv) > 1 and argv[1] == "--board":
        return main_board(argv[2:])
    if len(argv) != 3 or argv[2] not in layout.SIDES:
        print(__doc__)
        return 2
    path, side = Path(argv[1]), argv[2]
    nl = load(path)
    ck = Checker()
    ck.section("design.py parts and nets", check_design(nl, design(side)))
    diode_errs, key_errs = check_matrix(nl, side)
    ck.section("37 diodes anode on switch/COL side, cathode on ROW", diode_errs)
    ck.section("key (row, col) per §5", key_errs)
    ck.section("GPIO nets per layout/pins.py", check_gpio(nl))
    ck.section(f"TRRS Tip/Ring1 -> {TRRS[side]['TRRS_A']}/{TRRS[side]['TRRS_B']} ({side})", check_trrs(nl, side))
    ck.section("CC1/CC2 5.1k to GND", check_cc(nl))
    ck.section("RP2040 supply pins decoupled", check_decoupling(nl))
    ck.section("VBUS only J1/D1/R5; ESD references U4 VSYS, U5 VLINK", check_power(nl))
    ck.section("LCSC on every BOM part, none retired", check_lcsc(nl))
    ck.section("matrix nets identical left/right", check_mirror(nl, side, path))
    return report(ck, f"{side} ({len(nl.comps)} symbols, {len(nl.nets)} nets)")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
