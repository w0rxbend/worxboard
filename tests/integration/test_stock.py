# SPDX-License-Identifier: GPL-3.0-or-later
"""Gate G3 offline: the JLC BOM that design.py gives, that the committed boards carry it (kikit pairs
the schematic's bom.csv with the board's pos.csv and copper), and the verdicts of stock.py on canned
shop records (stock.py itself needs the network; run it on the day of ordering)."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

import stock  # first: puts pcb/scripts on sys.path
import netcmp  # noqa: I001
from design import design

ROOT = Path(__file__).resolve().parents[2]
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


@pytest.mark.parametrize("side", SIDES)
def test_committed_board_orders_the_design_parts(side):
    """kikit takes bom.csv from the schematic but pos.csv, its rotation corrections and the gerbers from
    the board, and KiCad's parity ignores LCSC: the committed board must carry design.py's footprints,
    values, LCSC numbers and DNP flags, and no retired part. Fails until both halves are re-placed
    from the ELEC schematics (docs/deviations.md ELEC-5, ELEC-6)."""
    errs = netcmp.check_board(netcmp.load_board(ROOT / f"pcb/{side}/worxboard-{side}.kicad_pcb"), design(side))
    assert not errs, "\n".join(errs)


def as_board(side: str) -> list[netcmp.BoardPart]:
    """The board design.py asks for, with one board-only stabiliser."""
    out = [netcmp.BoardPart(p.ref, p.footprint, p.value, p.lcsc, frozenset(
        ["smd"] + ["dnp"] * p.dnp + ["exclude_from_bom", "exclude_from_pos_files"] * (not p.in_bom)))
        for p in design(side)]
    return out + [netcmp.BoardPart("STAB_T5", "worxboard:Stab_MX_2u", "Stab_MX_2u", "",
                                   frozenset({"board_only", "exclude_from_bom", "exclude_from_pos_files"}))]


def test_board_check_catches_a_stale_board():
    assert netcmp.check_board(as_board("left"), design("left")) == []
    stale = [replace(b, lcsc="C2803348") if b.ref.startswith("SK") else
             replace(b, attrs=b.attrs | {"dnp"}) if b.ref == "J3" else b for b in as_board("left")]
    errs = netcmp.check_board(stale, design("left"))
    assert len(errs) == 2 and "SK101..SK137 (37 parts) LCSC 'C2803348'" in errs[1] and "retired" in errs[1]
    assert errs[0] == "J3 is dnp on the board, fitted in design.py"


def write_fab(path: Path, side: str, swap: dict[str, str] | None = None, extra_pos: str = "") -> Path:
    """bom.csv / pos.csv as kikit writes them (CRLF, quoted designator lists)."""
    swap, lines = swap or {}, {}
    for p in design(side):
        if p.in_bom and not p.dnp:
            lines.setdefault((p.value, p.footprint, swap.get(p.ref, p.lcsc)), []).append(p.ref)
    bom = ["Comment,Designator,Footprint,LCSC"] + [f'{v},"{",".join(r)}",{f},{c}' for (v, f, c), r in lines.items()]
    pos = ["Designator,Mid X,Mid Y,Layer,Rotation"] + [f"{r},0,0,T,0" for rs in lines.values() for r in rs]
    path.mkdir(parents=True, exist_ok=True)
    (path / "bom.csv").write_text("\r\n".join(bom) + "\r\n", newline="")
    (path / "pos.csv").write_text("\r\n".join(pos + [extra_pos] * bool(extra_pos)) + "\r\n", newline="")
    return path


def test_fab_check_on_kikit_outputs(tmp_path):
    assert netcmp.check_fab(write_fab(tmp_path / "ok", "right"), design("right")) == []
    errs = netcmp.check_fab(write_fab(tmp_path / "bad", "right", {"U2": "C113767"}, "JP1,0,0,T,0"), design("right"))
    assert errs == ["bom.csv line U2 carries retired C113767 (" + stock.RETIRED["C113767"] + ")",
                    "bom.csv gives U2 'C113767', design.py 'C97521'",
                    "pos.csv places JP1, which JLC must not fit"]


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
