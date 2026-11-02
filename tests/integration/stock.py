# SPDX-License-Identifier: GPL-3.0-or-later
"""Gate G3 stock check: every LCSC part of pcb/scripts/design.py against LCSC and the JLCPCB
assembly library, for an order of N assembled boards per half (spec §7, docs/verification.md).

    uv run python tests/integration/stock.py [--boards 5]

Needs the network and curl (both shops refuse Python's default client). Prints one row per LCSC
number (JLC library basic/extended, assembly process SMT/THT, stock) and exits 1 when a part is
short, discontinued at either shop, retired from this design, or unknown to JLC. Run it on the day
of ordering: stock moves daily.

"Need" is per_board x boards for each half plus JLC's attrition (lossNumber) on each of the two
designs, and never less than MIN_STOCK.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pcb/scripts"))

from design import design  # noqa: E402

LCSC_API = "https://wmsc.lcsc.com/ftps/wm/product/detail?productCode={}"
JLC_API = "https://cart.jlcpcb.com/shoppingCart/smtGood/getComponentDetail?componentCode={}"
SIDES = ("left", "right")
MIN_STOCK = 50                 # floor per LCSC number at JLC, whatever the order size
LCSC_DISCONTINUED = {"stop_product"}
JLC_DISCONTINUED = "no longer manufactur"      # JLC's noBuyReason text
LIBRARY = {"base": "basic", "expand": "extended"}
# Parts this design dropped (docs/deviations.md ELEC-1); the check fails if one comes back
RETIRED = {
    "C2803348": "Kailh CPG151101S11 hot-swap socket: discontinued (JLC and LCSC 0, 2026-11-02)",
    "C113767": "W25Q128JVSIQ: no longer manufactured per JLC; same part is the basic C97521",
    "C91749": "Epson 12 MHz crystal: 19 left at JLC on 2026-11-02",
}


def curl(url: str) -> dict:
    out = subprocess.run(["curl", "-sS", "--max-time", "40", "--retry", "2", url],
                         capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def lcsc(code: str) -> dict:
    return curl(LCSC_API.format(code)).get("result") or {}


def jlc(code: str) -> dict:
    return curl(JLC_API.format(code)).get("data") or {}


def bom() -> tuple[Counter, dict[str, list[str]]]:
    """Parts per board (the same on both halves) and designators per LCSC number."""
    per_board, refs = Counter(), {}
    for p in design(SIDES[0]):
        if p.in_bom and not p.dnp and p.lcsc:
            per_board[p.lcsc] += 1
            refs.setdefault(p.lcsc, []).append(p.ref)
    return per_board, refs


@dataclass
class Row:
    code: str
    qty: int
    need: int
    library: str
    process: str
    jlc_stock: int
    lcsc_stock: object
    part: str
    flags: list[str]


def assess(code: str, qty: int, boards: int, jl: dict, lc: dict) -> Row:
    """One BOM line against the shops' records (pure: the tests feed it canned records)."""
    loss = int(jl.get("lossNumber") or 0)
    need = max(MIN_STOCK, len(SIDES) * (qty * boards + loss))
    stock = int(jl.get("stockCount") or 0)
    gone = (lc.get("productCycle") in LCSC_DISCONTINUED
            or JLC_DISCONTINUED in (jl.get("noBuyReason") or "").lower())
    flags = [f for f, bad in (("UNKNOWN-AT-JLC", not jl), ("SHORT", stock < need), ("DISCONTINUED", gone),
                              ("RETIRED", code in RETIRED)) if bad]
    part = f"{jl.get('componentBrandEn') or lc.get('brandNameEn')} {jl.get('componentModelEn') or lc.get('productModel')}"
    return Row(code, qty, need, LIBRARY.get(jl.get("componentLibraryType"), "?"), jl.get("assemblyProcess") or "?",
               stock, lc.get("stockNumber", "?"), part, flags)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--boards", type=int, default=5, help="assembled boards per half (default 5)")
    args = ap.parse_args(argv)
    per_board, refs = bom()
    bad = []
    print(f"{'LCSC':10} {'qty':>4} {'need':>5} {'library':9} {'proc':4} {'JLC stock':>10} {'LCSC stock':>10}  part")
    for code in sorted(per_board, key=lambda c: int(c[1:])):
        r = assess(code, per_board[code], args.boards, jlc(code), lcsc(code))
        bad += [f"{code} {f}" for f in r.flags]
        many = "..." if len(refs[code]) > 1 else ""
        print(f"{code:10} {r.qty:>4} {r.need:>5} {r.library:9} {r.process:4} {r.jlc_stock:>10} {r.lcsc_stock!s:>10}  "
              f"{r.part} ({refs[code][0]}{many}) {' '.join(r.flags)}")
    verdict = "; ".join(bad) or "all in stock"
    print(f"{len(per_board)} LCSC numbers, {args.boards} boards per half: {verdict}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
