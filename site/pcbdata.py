# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only views of the WS2 PCB data for the docs and the microsite.

- `footprints(side)`: every footprint of the committed `pcb/<side>/worxboard-<side>.kicad_pcb`
  (reference, value, footprint, layer, position, rotation, Fab-layer body box). Stdlib only.
- `design(side)`: the parts and nets of `pcb/scripts/design.py` (needs the `layout` package).
"""
from __future__ import annotations

import importlib.util
import math
import re
import sys
from dataclasses import dataclass
from functools import cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SIDES = ("left", "right")

_FOOTPRINT = re.compile(r'^\t\(footprint "([^"]+)"$', re.M)
_AT = re.compile(r'^\t\t\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)$', re.M)
_LAYER = re.compile(r'^\t\t\(layer "([^"]+)"\)$', re.M)
_PROP = re.compile(r'^\t\t\(property "(Reference|Value)" "([^"]*)"$', re.M)
_ITEM = re.compile(r'^\t\t\(fp_(line|rect|poly|circle|arc)$', re.M)
_XY = re.compile(r'\((?:start|end|mid|center|xy) ([-\d.]+) ([-\d.]+)\)')


@dataclass(frozen=True)
class Footprint:
    ref: str
    value: str
    lib: str                 # library:footprint
    side: str                # "top" (F.Cu) or "bottom" (B.Cu)
    x: float                 # KiCad frame of the half, mm
    y: float
    rot: float               # degrees, CCW on screen
    body: tuple[float, float, float, float] | None   # Fab-layer box in the footprint frame


def board_path(side: str) -> Path:
    return ROOT / f"pcb/{side}/worxboard-{side}.kicad_pcb"


def _body(block: str) -> tuple[float, float, float, float] | None:
    """Bounding box of the Fab-layer graphics (the part body outline), footprint frame."""
    pts = []
    items = list(_ITEM.finditer(block))
    for m, nxt in zip(items, items[1:] + [None]):
        item = block[m.start():nxt.start() if nxt else len(block)]
        if not re.search(r'\(layer "[FB]\.Fab"\)', item):
            continue
        xy = [(float(x), float(y)) for x, y in _XY.findall(item)]
        if m.group(1) == "circle":           # (center) (end): a point on the circle
            (cx, cy), (ex, ey) = xy[:2]
            r = math.hypot(ex - cx, ey - cy)
            xy = [(cx - r, cy - r), (cx + r, cy + r)]
        pts += xy
    if not pts:
        return None
    xs, ys = zip(*pts)
    return min(xs), min(ys), max(xs), max(ys)


@cache
def footprints(side: str) -> dict[str, Footprint]:
    text = board_path(side).read_text()
    out = {}
    for h in _FOOTPRINT.finditer(text):
        block = text[h.end():text.index("\n\t)\n", h.end())]      # up to the footprint's closing paren
        x, y, rot = _AT.search(block).groups()
        props = dict(_PROP.findall(block))
        layer = _LAYER.search(block).group(1)
        out[props["Reference"]] = Footprint(props["Reference"], props["Value"], h.group(1),
                                            "bottom" if layer == "B.Cu" else "top",
                                            float(x), float(y), float(rot or 0), _body(block))
    return out


@cache
def _design_module():
    spec = importlib.util.spec_from_file_location("worxboard_design", ROOT / "pcb/scripts/design.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod          # dataclasses look their module up while the file runs
    spec.loader.exec_module(mod)
    return mod


def design(side: str) -> list:
    """`pcb/scripts/design.py` parts of one half (Part dataclasses, schematic order)."""
    return _design_module().design(side)


def ref_key(ref: str) -> tuple[str, int]:
    """Sort key: letters, then number (C2 before C10)."""
    m = re.match(r"([A-Z_]+?)(\d*)$", ref)
    return (m.group(1), int(m.group(2) or 0)) if m else (ref, 0)
