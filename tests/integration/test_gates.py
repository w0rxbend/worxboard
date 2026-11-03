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

# nice!view: nicekeyboards.com/docs/nice-view/pinout-schematic (pinout and dimension drawings);
# viewing area of the Sharp LS011B7DH03 from its DigiKey listing
NV_FRONT_PINS = ("MOSI", "SCK", "VCC", "GND", "CS")   # LCD side up, header at the bottom, left to right
NV_SIZE = (14.0, 36.0)
NV_VCUT = 0.2                  # "PCB V-Cut may add 0.1-0.2" to the 36 mm length
NV_PIN_EDGE = 1.3              # header row to the module's header-end edge
NV_VIEW_START = 4.6            # header-end edge to the viewing area (1.3 + 1.7 to the glass + 1.6)
NV_VIEW = (10.74, 25.28)       # viewing area across x along
J3_NETS = {"MOSI": "DISP_MOSI", "SCK": "DISP_SCK", "VCC": "3V3", "GND": "GND", "CS": "DISP_CS"}

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
    y0 = display(side)["header"][1] - NV_PIN_EDGE
    return y0, y0 + NV_SIZE[1] + NV_VCUT


def j2(side: str) -> dict:
    return next(j for j in LAYOUT["sides"][side]["jacks"] if j["ref"] == "J2")


# ---- G1: nice!view ------------------------------------------------------------------------------

@pytest.mark.parametrize("side", SIDES)
def test_g1_header_is_at_the_back_end(side):
    d = display(side)
    assert d["header"][1] < (d["module"][1] + d["module"][3]) / 2


@pytest.mark.parametrize("side", SIDES)
def test_g1_j3_pin_order_is_the_module_order(side):
    """Pin 1..5 carry MOSI, SCK, VCC, GND, CS: the module's order, read from one end or the other."""
    j3 = pcbdata.board(side).parts["J3"]
    assert [j3.pads[str(n)] for n in range(1, 6)] == [J3_NETS[p] for p in NV_FRONT_PINS]


@pytest.mark.parametrize("side", SIDES)
def test_g1_module_pins_land_on_their_nets(side):
    """LCD side up with the header at the back is the front view turned 180°: CS is at low x."""
    j3 = pcbdata.board(side).parts["J3"]
    by_x = sorted(j3.pads, key=lambda p: j3.at[p][0])
    assert [j3.pads[p] for p in by_x] == [J3_NETS[p] for p in reversed(NV_FRONT_PINS)]


@pytest.mark.parametrize("side", SIDES)
def test_g1_module_fits_the_pocket(side):
    y0, y1 = module_span(side)
    pocket = display(side)["pocket"]
    assert pocket[1] <= y0 and y1 <= pocket[3], f"module y {y0:.2f}-{y1:.2f}, pocket {pocket[1]}-{pocket[3]}"


@pytest.mark.parametrize("side", SIDES)
def test_g1_window_shows_the_viewing_area(side):
    d = display(side)
    v0 = module_span(side)[0] + NV_VIEW_START
    cx = d["header"][0]
    view = (cx - NV_VIEW[0] / 2, v0, cx + NV_VIEW[0] / 2, v0 + NV_VIEW[1])
    w = d["window"]
    assert w[0] <= view[0] and w[1] <= view[1] and view[2] <= w[2] and view[3] <= w[3], \
        f"viewing area y {view[1]:.2f}-{view[3]:.2f}, window y {w[1]}-{w[3]}"


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
