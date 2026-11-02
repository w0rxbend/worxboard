# SPDX-License-Identifier: GPL-3.0-or-later
"""The WS2 connectivity the integration tests read, from either source:

    netlist(side)     build/<side>/<side>.net, exported by `just pcb-sch <side>` (pin names known)
    board(side)       pcb/<side>/worxboard-<side>.kicad_pcb, the committed board (pad nets only)

On the board the RP2040 pads are mapped to GPIOs by their QFN numbers in layout/pins.py (RP2040
datasheet pinout); the netlist names them, and a test checks that the two maps agree.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pcb/scripts"))

from netcmp import find, find_all, load, parse, val  # noqa: E402  (WS2's own netlist reader)

from layout.pins import PINS  # noqa: E402

MCU = "U1"
GPIO_NAME = re.compile(r"^GPIO(\d+)")
QFN_GPIO = {str(p.qfn): int(GPIO_NAME.match(p.name).group(1)) for p in PINS if GPIO_NAME.match(p.name)}


def netlist_path(side: str) -> Path:
    return ROOT / f"build/{side}/{side}.net"


def board_path(side: str) -> Path:
    return ROOT / f"pcb/{side}/worxboard-{side}.kicad_pcb"


@dataclass
class Part:
    value: str
    key: str | None                                       # Key field of matrix sockets and diodes
    pads: dict[str, str] = field(default_factory=dict)    # pad number -> net
    names: dict[str, str] = field(default_factory=dict)   # pad number -> symbol pin name (netlist)


@dataclass
class Pcb:
    side: str
    source: str
    parts: dict[str, Part]
    gpio_pads: dict[str, int]                             # U1 pad number -> GPIO

    def gpio(self, net: str) -> int:
        """The one RP2040 GPIO on a net."""
        hits = {g for pad, g in self.gpio_pads.items() if self.parts[MCU].pads.get(pad) == net}
        if len(hits) != 1:
            raise AssertionError(f"{self.source}: net {net} reaches GPIOs {sorted(hits)}, want exactly one")
        return hits.pop()

    def through(self, net: str, value: str) -> set[str]:
        """Nets one two-pad part of this value away from `net` (a series resistor)."""
        out = set()
        for p in self.parts.values():
            nets = list(p.pads.values())
            if p.value == value and len(p.pads) == 2 and net in nets:
                out.add(nets[1 - nets.index(net)])
        return out

    def matrix(self) -> dict[str, tuple[Part, Part]]:
        """Key id -> (socket, diode)."""
        out: dict[str, list] = {}
        for ref, p in self.parts.items():
            if p.key:
                out.setdefault(p.key, [None, None])[0 if ref.startswith("SK") else 1] = p
        return {k: tuple(v) for k, v in out.items()}


@cache
def netlist(side: str) -> Pcb:
    nl = load(netlist_path(side))
    parts = {}
    for ref, c in nl.comps.items():
        pads, names = {n: net for n, (_, net) in c.pins.items()}, {n: name for n, (name, _) in c.pins.items()}
        parts[ref] = Part(c.value, c.fields.get("Key") or None, pads, names)
    gpio_pads = {n: int(m.group(1)) for n, name in parts[MCU].names.items() if (m := GPIO_NAME.match(name))}
    return Pcb(side, f"{side} netlist", parts, gpio_pads)


@cache
def board(side: str) -> Pcb:
    root = parse(board_path(side).read_text())
    parts = {}
    for fp in find_all(root, "footprint"):
        props = {p[1]: p[2] for p in find_all(fp, "property")}
        pads = {p[1]: val(p, "net") for p in find_all(fp, "pad") if p[1] and find(p, "net")}
        parts[props["Reference"]] = Part(props.get("Value", ""), props.get("Key") or None, pads)
    return Pcb(side, f"{side} board", parts, dict(QFN_GPIO))
