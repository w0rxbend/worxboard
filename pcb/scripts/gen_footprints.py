# SPDX-License-Identifier: GPL-3.0-or-later
"""Write the vendored worxboard library (spec §9 stage 1). Idempotent, stdlib only.

  pcb/lib/worxboard.pretty/SW_MX_Hotswap_Kailh.kicad_mod   Kailh CPG151101S11 MX hot-swap socket
  pcb/lib/worxboard.pretty/Stab_MX_2u.kicad_mod            MX 2u plate-stabiliser NPTHs (board only)
  pcb/lib/worxboard.pretty/LED_SK6812MINI-E_ReverseMount.kicad_mod   rev B per-key LED (from stock)
  pcb/lib/worxboard.kicad_sym                              SW_Push_MX, SY6280AAC symbols

Hot-swap geometry follows the CPG151101S11 datasheet and ceoloide `switch_mx` (MIT,
Marco Massarelli). The socket is a B.Cu part: the library footprint is drawn as seen
when it is placed on F.Cu, so `place.py` flips it (left/right) onto B.Cu, where it lands
on the spec coordinates: pads (-7.085, -2.54) / (5.842, -5.08), socket holes
(-3.81, -2.54) / (2.54, -5.08). Pad 1 = COL side, pad 2 = diode anode side.
"""
from __future__ import annotations

import re
import sys
import uuid
from pathlib import Path

LIB = Path(__file__).resolve().parents[1] / "lib"
PRETTY = LIB / "worxboard.pretty"
NS = uuid.UUID("6f0c3f0e-7a51-4c55-9a43-776f72786264")   # stable UUIDs per item

FP_VERSION = 20260206      # KiCad 10 footprint format
SYM_VERSION = 20251024     # KiCad 10 symbol format

# MX switch (front view, mm)
MX_CENTRE_D = 4.0
MX_PEG_D = 1.75
MX_PEG_X = 5.08
CELL = 19.05               # 1u keycap outline on F.Fab
MX_CUT = 14.0              # plate cut-out outline on Dwgs.User
# Kailh socket, mirrored here so the flip onto B.Cu gives the spec coordinates
SOCKET_HOLE_D = 3.0
SOCKET_HOLES = ((3.81, -2.54), (-2.54, -5.08))
SOCKET_PAD = (2.55, 2.5)
SOCKET_PADS = (("1", 7.085, -2.54), ("2", -5.842, -5.08))
SOCKET_BODY = (-5.0, -7.6, 7.0, -0.4)          # x0, y0, x1, y1 of the socket body (library frame)
CRTYD_MARGIN = 0.25
# Rev B LED: KiCad's stock SK6812MINI-E reverse-mount footprint (3.4 x 3.0 mm cutout, pads at x +-2.725)
# leaves 0.247 mm from the pad corners to the cutout's corner arcs. The copy moves the four pads 0.1 mm
# outward: >= 0.3 mm to the cutout, the 1.34 mm leads (body edge 1.6 -> tip 2.94) still land 0.79 mm on
# the pads (docs/deviations.md REVB-1). Read from the pinned kicad/kicad:10.0.7 image (stage A runs there)
STOCK_LED = Path("/usr/share/kicad/footprints/LED_SMD.pretty/LED_SK6812MINI-E_3.2x2.8mm_P1.5mm_ReverseMount.kicad_mod")
LED_NAME = "LED_SK6812MINI-E_ReverseMount"
LED_PAD_X, LED_PAD_SHIFT = 2.725, 0.1
# MX 2u stabiliser (long axis along x)
STAB_X = 11.938
STAB_TOP = (-6.985, 3.05)                      # y, diameter (wire end)
STAB_BOTTOM = (8.255, 4.0)


def _u(*parts: object) -> str:
    return str(uuid.uuid5(NS, "/".join(map(str, parts))))


def _f(v: float) -> str:
    return f"{v:.4f}".rstrip("0").rstrip(".") if v != int(v) else str(int(v))


def _text(kind: str, value: str, at: tuple[float, float], layer: str, name: str, hide: bool = False) -> str:
    h = " (hide yes)" if hide else ""
    return (f'\t(property "{kind}" "{value}" (at {_f(at[0])} {_f(at[1])} 0) (layer "{layer}"){h}'
            f' (uuid "{_u(name, kind)}") (effects (font (size 1 1) (thickness 0.15))))\n')


def _rect(x0: float, y0: float, x1: float, y1: float, layer: str, width: float, name: str) -> str:
    return (f'\t(fp_rect (start {_f(x0)} {_f(y0)}) (end {_f(x1)} {_f(y1)})'
            f' (stroke (width {width}) (type solid)) (fill no) (layer "{layer}")'
            f' (uuid "{_u(name, layer, x0, y0)}"))\n')


def _npth(x: float, y: float, d: float, name: str) -> str:
    return (f'\t(pad "" np_thru_hole circle (at {_f(x)} {_f(y)}) (size {_f(d)} {_f(d)}) (drill {_f(d)})'
            f' (layers "*.Cu" "*.Mask") (uuid "{_u(name, "npth", x, y)}"))\n')


def _footprint(name: str, descr: str, attr: str, body: str) -> str:
    return (f'(footprint "{name}"\n\t(version {FP_VERSION})\n\t(generator "worxboard_gen_footprints")\n'
            f'\t(generator_version "10.0")\n\t(layer "F.Cu")\n\t(descr "{descr}")\n'
            + _text("Reference", "REF**", (0, -8.5), "F.SilkS", name)
            + _text("Value", name, (0, 8.5), "F.Fab", name)
            + f'\t(attr {attr})\n' + body + '\t(embedded_fonts no)\n)\n')


def mx_hotswap() -> str:
    n = "SW_MX_Hotswap_Kailh"
    body = _npth(0, 0, MX_CENTRE_D, n) + _npth(-MX_PEG_X, 0, MX_PEG_D, n) + _npth(MX_PEG_X, 0, MX_PEG_D, n)
    body += "".join(_npth(x, y, SOCKET_HOLE_D, n) for x, y in SOCKET_HOLES)
    for num, x, y in SOCKET_PADS:
        body += (f'\t(pad "{num}" smd rect (at {_f(x)} {_f(y)}) (size {_f(SOCKET_PAD[0])} {_f(SOCKET_PAD[1])})'
                 f' (layers "F.Cu" "F.Paste" "F.Mask") (uuid "{_u(n, "pad", num)}"))\n')
    c = CELL / 2
    body += _rect(-c, -c, c, c, "F.Fab", 0.1, n)
    body += _rect(-MX_CUT / 2, -MX_CUT / 2, MX_CUT / 2, MX_CUT / 2, "Dwgs.User", 0.1, n)
    px, py = SOCKET_PAD[0] / 2, SOCKET_PAD[1] / 2
    xs = [SOCKET_BODY[0], SOCKET_BODY[2], *(x + d for _, x, _ in SOCKET_PADS for d in (-px, px))]
    ys = [SOCKET_BODY[1], SOCKET_BODY[3], *(y + d for _, _, y in SOCKET_PADS for d in (-py, py))]
    m = CRTYD_MARGIN
    body += _rect(min(xs) - m, min(ys) - m, max(xs) + m, max(ys) + m, "F.CrtYd", 0.05, n)
    body += _rect(*SOCKET_BODY, "F.SilkS", 0.12, n)
    return _footprint(n, "Kailh CPG151101S11 MX hot-swap socket (B.Cu after flip), MX centre and peg NPTHs",
                      "smd", body)


def stab_2u() -> str:
    n = "Stab_MX_2u"
    body = ""
    for sx in (-STAB_X, STAB_X):
        for y, d in (STAB_TOP, STAB_BOTTOM):
            body += _npth(sx, y, d, n)
    return _footprint(n, "Cherry MX 2u plate-mount stabiliser holes, long axis along x",
                      "board_only exclude_from_pos_files exclude_from_bom", body)


def sk6812mini_e() -> str | None:
    """The stock reverse-mount footprint with the pads 0.1 mm further out (None outside the container)."""
    if not STOCK_LED.is_file():
        return None
    text = STOCK_LED.read_text()
    n = 0

    def out(m: re.Match) -> str:
        nonlocal n
        n += 1
        return f"(at {m.group(1)}{LED_PAD_X + LED_PAD_SHIFT:g} {m.group(2)})"
    text = re.sub(r"\(at (-?)2\.725 (-?0\.75)\)", out, text)
    if n != 4:
        raise SystemExit(f"{STOCK_LED.name}: expected 4 pads at x +-2.725, found {n}")
    text = text.replace('(footprint "LED_SK6812MINI-E_3.2x2.8mm_P1.5mm_ReverseMount"', f'(footprint "{LED_NAME}"', 1)
    return text.replace('(descr "RGB LED with integrated controller',
                        '(descr "worxboard: stock footprint, pads moved 0.1 mm out (>= 0.3 mm to the cutout). RGB LED with integrated controller', 1)


def _prop(name: str, value: str, y: float, hide: bool = True) -> str:
    h = " (hide yes)" if hide else ""
    return f'\t\t(property "{name}" "{value}" (at 0 {_f(y)} 0){h} (effects (font (size 1.27 1.27))))\n'


def _pin(num: str, x: float, angle: int) -> str:
    return (f'\t\t\t(pin passive line (at {_f(x)} 0 {angle}) (length 2.54)'
            f' (name "{num}" (effects (font (size 1.27 1.27)))) (number "{num}" (effects (font (size 1.27 1.27)))))\n')


def _pin_at(kind: str, name: str, num: str, x: float, y: float, angle: int) -> str:
    return (f'\t\t\t(pin {kind} line (at {_f(x)} {_f(y)} {angle}) (length 2.54)'
            f' (name "{name}" (effects (font (size 1.27 1.27)))) (number "{num}" (effects (font (size 1.27 1.27)))))\n')


def sy6280() -> str:
    """Silergy SY6280AAC current-limited load switch, SOT-23-5 (datasheet AN_SY6280 pinout: 1 OUT,
    2 GND, 3 ISET, 4 EN, 5 IN; Ilim = 6800 / Rset). Rev B VLED switch for the per-key RGB."""
    g = '(stroke (width 0.254) (type default)) (fill (type background))'
    return ('\t(symbol "SY6280AAC" (pin_names (offset 1.016))\n'
            '\t\t(exclude_from_sim no) (in_bom yes) (on_board yes)\n'
            + _prop("Reference", "U", 6.35, hide=False) + _prop("Value", "SY6280AAC", -6.35, hide=False)
            + _prop("Footprint", "Package_TO_SOT_SMD:SOT-23-5", -8.89)
            + _prop("Datasheet", "https://www.lcsc.com/datasheet/C55136.pdf", -8.89)
            + _prop("Description", "Current-limited high-side load switch, 2.4-5.5 V, Ilim = 6800/Rset", 0)
            + '\t\t(symbol "SY6280AAC_0_1"\n'
            f'\t\t\t(rectangle (start -5.08 5.08) (end 5.08 -5.08) {g})\n'
            '\t\t)\n\t\t(symbol "SY6280AAC_1_1"\n'
            + _pin_at("power_in", "IN", "5", -7.62, 2.54, 0) + _pin_at("input", "EN", "4", -7.62, -2.54, 0)
            + _pin_at("power_out", "OUT", "1", 7.62, 2.54, 180) + _pin_at("passive", "ISET", "3", 7.62, -2.54, 180)
            + _pin_at("power_in", "GND", "2", 0, -7.62, 90)
            + '\t\t)\n\t\t(embedded_fonts no)\n\t)\n')


def symbols() -> str:
    g = '(stroke (width 0) (type default)) (fill (type none))'
    return (f'(kicad_symbol_lib\n\t(version {SYM_VERSION})\n\t(generator "worxboard_gen_footprints")\n'
            '\t(generator_version "10.0")\n'
            '\t(symbol "SW_Push_MX" (pin_numbers (hide yes)) (pin_names (offset 1.016) (hide yes))\n'
            '\t\t(exclude_from_sim no) (in_bom yes) (on_board yes)\n'
            + _prop("Reference", "SK", 2.54, hide=False) + _prop("Value", "SW_Push_MX", -1.524, hide=False)
            + _prop("Footprint", "worxboard:SW_MX_Hotswap_Kailh", 5.08)
            + _prop("Datasheet", "", 5.08)
            + _prop("Description", "MX key switch in a Kailh hot-swap socket", 0)
            + '\t\t(symbol "SW_Push_MX_0_1"\n'
            f'\t\t\t(circle (center -2.032 0) (radius 0.508) {g})\n'
            f'\t\t\t(circle (center 2.032 0) (radius 0.508) {g})\n'
            f'\t\t\t(polyline (pts (xy 2.54 1.27) (xy -2.54 1.27)) {g})\n'
            f'\t\t\t(polyline (pts (xy 0 1.27) (xy 0 3.048)) {g})\n'
            '\t\t)\n\t\t(symbol "SW_Push_MX_1_1"\n'
            + _pin("1", -5.08, 0) + _pin("2", 5.08, 180)
            + '\t\t)\n\t\t(embedded_fonts no)\n\t)\n' + sy6280() + ')\n')


def main() -> int:
    PRETTY.mkdir(parents=True, exist_ok=True)
    out = {PRETTY / "SW_MX_Hotswap_Kailh.kicad_mod": mx_hotswap(),
           PRETTY / "Stab_MX_2u.kicad_mod": stab_2u(),
           LIB / "worxboard.kicad_sym": symbols()}
    led = sk6812mini_e()
    if led is not None:
        out[PRETTY / f"{LED_NAME}.kicad_mod"] = led
    for path, text in out.items():
        if not path.exists() or path.read_text() != text:
            path.write_text(text)
            print(f"wrote {path.relative_to(LIB.parent.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
