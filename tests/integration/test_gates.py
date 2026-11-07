# SPDX-License-Identifier: GPL-3.0-or-later
"""Gates G1 and G2 (spec §4, §6.2, §7) as checks of the committed boards and layout.json against
the part drawings. docs/verification.md records the sources and the results.

A check that fails today is a strict xfail naming its gate: once the owning stream fixes the
design it passes, the strict marker turns that into an error, and the fix removes the marker.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import pcbdata

ROOT = Path(__file__).resolve().parents[2]
LAYOUT = json.loads((ROOT / "layout/build/layout.json").read_text())
SIDES = ("left", "right")
TOL = 0.05

# 0.91" 128 x 32 SSD1306 I2C OLED module (gate G1; sellers' listings, docs/verification.md): 38 x 12 mm,
# 1x4 header at one short end, 22.38 x 5.58 active area on the glass. Seen glass up with its header on
# the left, the pins read GND, VCC, SCL, SDA from the top; some sellers swap GND and VCC, which JP2 /
# JP3 absorb (docs/deviations.md DISP-1)
OLED_PINS = ("GND", "VCC", "SCL", "SDA")
OLED_SIZE = (12.0, 38.0)
OLED_VCUT = 0.2                # a V-cut edge may add this to the 38 mm length
OLED_PIN_EDGE = 1.3            # header row to the module's header-end edge
OLED_VIEW_CENTRE = 20.0        # header-end edge to the active-area centre, nominal
OLED_VIEW_SPREAD = (1.2, 2.8)  # sellers' drawings put that centre within this (across, along)
OLED_VIEW = (5.58, 22.38)      # active area across x along
J3_NETS = {"GND": "DISP_P1", "VCC": "DISP_P2", "SCL": "DISP_SCL", "SDA": "DISP_SDA"}
JUMPERS = {"DISP_P1": ("JP2", "GND"), "DISP_P2": ("JP3", "3V3")}   # J3 net -> jumper, pad 1 as shipped

# HRO PJ-320D-4A (LCSC C95562 drawing): 2.00 barrel + 12.10 body, 6.10 wide, 5.00 high, axis centred
PJ_BARREL, PJ_BODY, PJ_WIDTH, PJ_HEIGHT = 2.0, 12.1, 6.1, 5.0
PJ_AXIS = PJ_HEIGHT / 2
PJ_PADS = {"R2": 3.2, "R1": 6.2, "T": 10.2, "S": 11.3}   # pad centres behind the barrel-end face
PJ_PAD_ROW = 3.25              # pad centres off the axis; S on the other side from T, R1, R2
SPEC_JACK_HEIGHT = 5.5         # §6.2 G2 limit


def display(side: str) -> dict:
    return LAYOUT["sides"][side]["display"]


def module_span(side: str) -> tuple[float, float]:
    """y extent of a module plugged into J3 (header at the back end, as on both boards)."""
    y0 = display(side)["header"][1] - OLED_PIN_EDGE
    return y0, y0 + OLED_SIZE[1] + OLED_VCUT


def j2(side: str) -> dict:
    return next(j for j in LAYOUT["sides"][side]["jacks"] if j["ref"] == "J2")


# ---- G1: OLED ----------------------------------------------------------------------------------

@pytest.mark.parametrize("side", SIDES)
def test_g1_header_is_at_the_back_end(side):
    d = display(side)
    assert d["header"][1] < (d["module"][1] + d["module"][3]) / 2


@pytest.mark.parametrize("side", SIDES)
def test_g1_j3_pin_order_is_the_module_order(side):
    """Pin 1..4 carry GND, VCC, SCL, SDA (the power pins through JP2 / JP3 as shipped)."""
    board = pcbdata.board(side)
    j3 = board.parts["J3"]
    assert [j3.pads[str(n)] for n in range(1, 5)] == [J3_NETS[p] for p in OLED_PINS]
    for net, (jp, shipped) in JUMPERS.items():
        assert board.parts[jp].pads["2"] == net and board.parts[jp].pads["1"] == shipped
    assert {board.parts[jp].pads["3"] for jp, _ in JUMPERS.values()} == {"GND", "3V3"}


@pytest.mark.parametrize("side", SIDES)
def test_g1_module_pins_land_on_their_nets(side):
    """Glass up with the header at the back is the header-left view turned a quarter clockwise: GND
    (pin 1) is at high x, SDA at low x."""
    j3 = pcbdata.board(side).parts["J3"]
    by_x = sorted(j3.pads, key=lambda p: j3.at[p][0])
    assert [j3.pads[p] for p in by_x] == [J3_NETS[p] for p in reversed(OLED_PINS)]


@pytest.mark.parametrize("side", SIDES)
def test_g1_module_fits_the_pocket(side):
    y0, y1 = module_span(side)
    d = display(side)
    pocket, cx = d["pocket"], d["header"][0]
    assert pocket[1] <= y0 and y1 <= pocket[3], f"module y {y0:.2f}-{y1:.2f}, pocket {pocket[1]}-{pocket[3]}"
    assert pocket[0] <= cx - OLED_SIZE[0] / 2 and cx + OLED_SIZE[0] / 2 <= pocket[2]


@pytest.mark.parametrize("side", SIDES)
@pytest.mark.parametrize("dx, dy", [(0, 0), (-1, -1), (-1, 1), (1, -1), (1, 1)])
def test_g1_window_shows_the_active_area(side, dx, dy):
    """The window shows the whole active area wherever the sellers' drawings put it."""
    d = display(side)
    cy = module_span(side)[0] + OLED_VIEW_CENTRE + dy * OLED_VIEW_SPREAD[1]
    cx = d["header"][0] + dx * OLED_VIEW_SPREAD[0]
    view = (cx - OLED_VIEW[0] / 2, cy - OLED_VIEW[1] / 2, cx + OLED_VIEW[0] / 2, cy + OLED_VIEW[1] / 2)
    w = d["window"]
    assert w[0] <= view[0] + 1e-9 and w[1] <= view[1] + 1e-9 and view[2] <= w[2] + 1e-9 and view[3] <= w[3] + 1e-9, \
        f"active area {view}, window {w}"


# ---- G2: PJ-320D --------------------------------------------------------------------------------

@pytest.mark.parametrize("side", SIDES)
def test_g2_jack_pads_match_the_datasheet(side):
    jack, pads = j2(side), pcbdata.board(side).parts["J2"]
    for name, depth in PJ_PADS.items():
        x, y = pads.at[name]
        behind = abs(x - jack["x"]) - PJ_BARREL
        assert abs(behind - depth) < TOL, f"{name} {behind:.3f} behind the barrel"
        assert abs(abs(y - jack["y"]) - PJ_PAD_ROW) < TOL, f"{name} {y - jack['y']:.3f} off the axis"
    row = {n: pads.at[n][1] > jack["y"] for n in PJ_PADS}
    assert row["T"] == row["R1"] == row["R2"] != row["S"], "S must sit across the jack from T, R1, R2"


@pytest.mark.parametrize("side", SIDES)
def test_g2_jack_height_and_axis(side):
    """The part is within the spec limit and the layout envelope (which the case clears) holds it."""
    jack = j2(side)
    assert PJ_HEIGHT <= SPEC_JACK_HEIGHT
    assert jack["height"] >= PJ_HEIGHT
    assert jack["axis_z"] == PJ_AXIS


@pytest.mark.parametrize("side", SIDES)
def test_g2_layout_body_holds_the_jack(side):
    x0, y0, x1, y1 = j2(side)["body"]
    assert x1 - x0 >= PJ_BARREL + PJ_BODY - TOL and y1 - y0 >= PJ_WIDTH - TOL
