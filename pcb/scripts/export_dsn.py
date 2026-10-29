# SPDX-License-Identifier: GPL-3.0-or-later
"""Export the Specctra DSN for Freerouting (spec §9 stage 9).

    python3 pcb/scripts/export_dsn.py <side>   pcb/<side>/worxboard-<side>.kicad_pcb -> build/<side>/<side>.dsn

Post-processing of KiCad's export:
- the GND pours are left out, so Freerouting routes GND as tracks (a pour cut up by the
  matrix wiring cannot be relied on to join the MCU and TRRS areas); import_ses.py fills them;
- the U1 signal nets move to a FANOUT_W class (0.4 mm pitch: 0.21 mm to the next pad): Freerouting cannot neck a 0.25 mm track down
  between 0.4 mm-pitch QFN pads (docs/deviations.md WS2b);
- the 0.5 mm copper-to-edge rule is passed to Freerouting on its command line (pcb.just).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pcbnew  # noqa: E402

from route_critical import Router  # noqa: E402

UM = 1000.0                  # DSN units per mm (resolution um)
FANOUT_CLASS = "fanout"
FANOUT_W = 0.18              # mm; Freerouting necks tracks to 75 % at pins: 0.135 >= the 0.127 minimum
DROP_PLANES = False
CLEARANCE_MARGIN = 2         # um added to every DSN clearance
STRIP_REFS = ("U1",)         # parts whose pins Freerouting reaches only through locked tracks


def drop_planes(text: str) -> tuple[str, int]:
    """Remove every top-level `(plane ...)` block of the structure section."""
    out, i, n = [], 0, 0
    while (j := text.find("(plane ", i)) >= 0:
        out.append(text[i:j])
        depth, k = 0, j
        while True:
            depth += {"(": 1, ")": -1}.get(text[k], 0)
            k += 1
            if depth == 0:
                break
        i, n = k, n + 1
    out.append(text[i:])
    return "".join(out), n


def snap_pins(text: str) -> tuple[str, int]:
    """Round footprint pin offsets to whole microns.

    Freerouting snaps its insertion target to 1 um, so a pin at a half-micron offset (the
    QFN-56 pad rows at 3.4375 mm) can never take the last segment of a route. The rounding
    moves a pin by <= 0.5 um, which CLEARANCE_MARGIN covers."""
    n = 0

    def sub(m: re.Match) -> str:
        nonlocal n
        x, y = float(m.group(3)), float(m.group(4))
        if x != round(x) or y != round(y):
            n += 1
        return f"{m.group(1)}{m.group(2)} {round(x)} {round(y)})"
    return re.sub(r"(\(pin \S+ (?:\(rotate [-\d.]+\) )?)(\S+) ([-\d.]+) ([-\d.]+)\)", sub, text), n


def strip_pins(text: str, refs: tuple[str, ...]) -> tuple[str, int]:
    """Take the pins of `refs` out of every net.

    Every used U1 pin already carries a locked track (route_critical.py), and the routes must
    attach to those tracks: when Freerouting targets a 0.2 mm QFN pad itself it cannot insert
    the last segment (a 0.5 mm 3V3 track can never enter it), so it would leave the net open.
    The pads stay in the DSN as obstacles; the session import works by net name, so the board's
    pads keep their nets."""
    n = 0

    def sub(m: re.Match) -> str:
        nonlocal n
        pins = m.group(1).split()
        keep = [p for p in pins if p.rsplit("-", 1)[0] not in refs]
        n += len(pins) - len(keep)
        return f"(pins {' '.join(keep)})"
    return re.sub(r"\(pins ([^)]*)\)", sub, text), n


def margin(text: str) -> str:
    """Every DSN clearance + CLEARANCE_MARGIN (covers the pin rounding)."""
    return re.sub(r"\(clearance (\d+)", lambda m: f"(clearance {int(m.group(1)) + CLEARANCE_MARGIN}", text)


def rect_pads(text: str) -> tuple[str, int]:
    """Replace KiCad's rounded-rectangle pad polygons by their nominal rectangles.

    The exported polygons are 0.19 um oversize, so 0.4 mm-pitch pads overlap the 0.2 mm
    clearance and Freerouting cannot leave them; the rectangle contains the real pad, so the
    router still keeps its clearance to the copper."""
    n = 0

    def sub(m: re.Match) -> str:
        nonlocal n
        name, w, h = m.group(1), float(m.group(2)), float(m.group(3))
        shapes = re.findall(r"\(shape \(polygon (\S+) 0 ", m.group(4))
        n += 1
        body = "".join(f"      (shape (rect {layer} {-w / 2:g} {-h / 2:g} {w / 2:g} {h / 2:g}))\n" for layer in shapes)
        return f"    (padstack {name}\n{body}      (attach off)\n    )\n"
    pat = r"    \(padstack (RoundRect\S*Pad_([\d.]+)x([\d.]+)_\S*)\n(.*?)      \(attach off\)\n    \)\n"
    return re.sub(pat, sub, text, flags=re.S), n


def fanout_class(text: str, nets: list[str]) -> str:
    """Move `nets` out of their classes into a new FANOUT_W-wide class."""
    def quote(n: str) -> str:
        return f'"{n}"' if re.search(r'[\s(){}"/-]', n) else n
    wanted = {quote(n) for n in nets}
    for m in list(re.finditer(r"\(class (\S+) (.*?)\n\s*\(circuit", text, re.S)):
        names = re.findall(r'"[^"]*"|\S+', m.group(2))
        keep = [n for n in names if n not in wanted]
        text = text.replace(m.group(0), f"(class {m.group(1)} {' '.join(keep)}\n      (circuit", 1)
    via = re.search(r'\(use_via "([^"]+)"\)', text).group(1)
    block = (f"    (class {FANOUT_CLASS} {' '.join(sorted(wanted))}\n      (circuit\n        (use_via \"{via}\")\n"
             f"      )\n      (rule\n        (width {FANOUT_W * UM:.0f})\n        (clearance 200)\n      )\n    )\n")
    i = text.index("(class ")
    i = text.rindex("\n", 0, i) + 1
    return text[:i] + block + text[i:]


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    side = argv[1]
    board = pcbnew.LoadBoard(str(ROOT / "pcb" / side / f"worxboard-{side}.kicad_pcb"))
    out = ROOT / "build" / side / f"{side}.dsn"
    out.parent.mkdir(parents=True, exist_ok=True)
    if not pcbnew.ExportSpecctraDSN(board, str(out)):
        raise SystemExit(f"DSN export failed: {out}")
    text = out.read_text()
    planes = 0
    if DROP_PLANES:
        text, planes = drop_planes(text)
    nets = Router.fanout_nets(board)
    text, rects = rect_pads(fanout_class(text, nets))
    text, snapped = snap_pins(text)
    text, stripped = strip_pins(text, STRIP_REFS)
    out.write_text(margin(text))
    print(f"{rects} rounded-rectangle padstacks as rectangles, {snapped} pins snapped to 1 um, "
          f"{stripped} {'/'.join(STRIP_REFS)} pins routed through their locked tracks")
    print(f"dropped {planes} copper pour plane(s); {len(nets)} nets in the {FANOUT_W} mm '{FANOUT_CLASS}' class")
    print(f"wrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
