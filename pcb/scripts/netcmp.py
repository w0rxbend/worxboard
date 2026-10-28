# SPDX-License-Identifier: GPL-3.0-or-later
"""Check an exported KiCad netlist against design.py (spec §9 stage 6). Stdlib + layout only.

    python3 pcb/scripts/netcmp.py build/<side>/<side>.net <side>

Parses the s-expression netlist (KiCad 10, version "E") and asserts:
  - every design.py part is present with its symbol, value, footprint and LCSC, and every
    pin sits on its design net (None = an unconnected single-pin net), and nothing else exists
  - each of the 37 diodes has its anode on the switch/COL side and its cathode on a ROW net
  - the (row, col) of every key matches §5 (`layout.keys`)
  - every GPIO net matches layout/pins.py (by RP2040 symbol pin name)
  - Tip/Ring1 reach TX/RX on the left and RX/TX on the right through 1 kΩ
  - CC1/CC2 each have 5.1k to GND
  - every RP2040 supply pin has a capacitor to GND on its net
  - every BOM part has a non-empty LCSC field
  - the matrix nets are identical to the other half (design.py, and its netlist when built)
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT))

import layout  # noqa: E402
from design import SUPPLY_PIN_NAMES, Part, design, switch_net  # noqa: E402
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


def check_lcsc(nl: Netlist) -> list[str]:
    return [f"{c.ref} has no LCSC" for c in nl.comps.values() if c.in_bom and not c.fields.get("LCSC", "").strip()]


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


def main(argv: list[str]) -> int:
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
    ck.section("LCSC on every BOM part", check_lcsc(nl))
    ck.section("matrix nets identical left/right", check_mirror(nl, side, path))
    for t in ck.passed:
        print(f"PASS  {t}")
    for e in ck.errors:
        print(f"FAIL  {e}")
    print(f"netcmp {side}: {len(ck.passed)} passed, {len(ck.errors)} errors "
          f"({len(nl.comps)} symbols, {len(nl.nets)} nets)")
    return 1 if ck.errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
