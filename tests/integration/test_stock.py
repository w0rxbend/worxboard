# SPDX-License-Identifier: GPL-3.0-or-later
"""Gate G3 offline: the JLC BOM that design.py gives, and the verdicts of stock.py on canned shop
records (stock.py itself needs the network; run it on the day of ordering)."""
from __future__ import annotations

import pytest

import stock
from design import design

SIDES = ("left", "right")
COPPER_ONLY = ("JP", "TP", "H")          # solder jumper, test pads, mounting holes: nothing to fit


@pytest.mark.parametrize("side", SIDES)
def test_jlc_fits_every_part(side):
    """Turnkey: every part with a body is in the JLC BOM with an LCSC number; nothing is DNP."""
    for p in design(side):
        assert not p.dnp, f"{p.ref} is DNP"
        if p.in_bom:
            assert p.lcsc, f"{p.ref} has no LCSC number"
        else:
            assert p.ref.rstrip("0123456789") in COPPER_ONLY and not p.lcsc, f"{p.ref} left out of the BOM"


def test_display_socket_is_assembled():
    per_board, refs = stock.bom()
    j3 = next(p for p in design("right") if p.ref == "J3")
    assert refs[j3.lcsc] == ["J3"] and j3.footprint.endswith("_H5.0mm")


def test_no_retired_part_is_back():
    per_board, _ = stock.bom()
    assert not set(per_board) & set(stock.RETIRED)


def test_both_halves_share_one_bom():
    lines = [sorted((p.ref, p.lcsc) for p in design(s) if p.in_bom) for s in SIDES]
    assert lines[0] == lines[1]


GOOD = {"stockCount": 5000, "lossNumber": 2, "componentLibraryType": "expand", "assemblyProcess": "SMT"}


@pytest.mark.parametrize("jl, lc, flags", [
    (GOOD, {"productCycle": "normal"}, []),
    ({**GOOD, "stockCount": 49}, {}, ["SHORT"]),                       # under the floor of 50
    ({**GOOD, "stockCount": 300}, {}, ["SHORT"]),                      # 2 x (37 x 5 + 2) = 374 needed
    ({**GOOD, "noBuyReason": "This product is no longer manufactured."}, {}, ["DISCONTINUED"]),
    (GOOD, {"productCycle": "stop_product"}, ["DISCONTINUED"]),
    ({}, {}, ["UNKNOWN-AT-JLC", "SHORT"]),
])
def test_assess_flags(jl, lc, flags):
    qty = 37 if jl.get("stockCount") == 300 else 1
    assert stock.assess("C41430893", qty, 5, jl, lc).flags == flags


def test_assess_need_counts_both_designs_and_attrition():
    r = stock.assess("C1525", 11, 5, {**GOOD, "lossNumber": 10, "componentLibraryType": "base"}, {})
    assert (r.need, r.library, r.process, r.flags) == (2 * (11 * 5 + 10), "basic", "SMT", [])


def test_assess_flags_a_retired_part():
    assert stock.assess("C2803348", 37, 5, {**GOOD, "stockCount": 10**6}, {}).flags == ["RETIRED"]
