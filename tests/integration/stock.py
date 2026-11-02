# SPDX-License-Identifier: GPL-3.0-or-later
"""Gate G3 stock check: every LCSC part of pcb/scripts/design.py against LCSC and the JLCPCB
assembly library, for an order of N assembled boards per half (spec §7, docs/verification.md).

    uv run python tests/integration/stock.py [--boards 5]

Needs the network and curl (both shops refuse Python's default client). Prints one row per LCSC
number and exits 1 when JLC stock cannot cover both halves or LCSC lists the part as discontinued.
Run it on the day of ordering: stock moves daily.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pcb/scripts"))

from design import design  # noqa: E402

LCSC_API = "https://wmsc.lcsc.com/ftps/wm/product/detail?productCode={}"
JLC_API = "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList"
SIDES = ("left", "right")
DISCONTINUED = {"stop_product"}


def curl(*args: str) -> dict:
    out = subprocess.run(["curl", "-sS", "--max-time", "30", *args], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def lcsc(code: str) -> dict:
    return curl(LCSC_API.format(code)).get("result") or {}


def jlc(code: str) -> dict:
    body = json.dumps({"keyword": code, "currentPage": 1, "pageSize": 25})
    rows = curl("-X", "POST", JLC_API, "-H", "Content-Type: application/json", "-d", body)
    return next((r for r in rows["data"]["componentPageInfo"]["list"] or [] if r["componentCode"] == code), {})


def bom() -> tuple[Counter, dict[str, list[str]]]:
    """Parts per board (the same on both halves) and designators per LCSC number."""
    per_board, refs = Counter(), {}
    for p in design(SIDES[0]):
        if p.in_bom and not p.dnp and p.lcsc:
            per_board[p.lcsc] += 1
            refs.setdefault(p.lcsc, []).append(p.ref)
    return per_board, refs


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--boards", type=int, default=5, help="assembled boards per half (default 5)")
    args = ap.parse_args(argv)
    per_board, refs = bom()
    short = []
    print(f"{'LCSC':10} {'qty':>4} {'need':>5} {'JLC lib':8} {'JLC stock':>10} {'LCSC stock':>10}  part")
    for code in sorted(per_board, key=lambda c: int(c[1:])):
        need = per_board[code] * args.boards * len(SIDES)
        lc, jl = lcsc(code), jlc(code)
        stock = jl.get("stockCount") or 0
        flags = [f for f, bad in (("SHORT", stock < need), ("DISCONTINUED", lc.get("productCycle") in DISCONTINUED))
                 if bad]
        short += [f"{code} {f}" for f in flags]
        print(f"{code:10} {per_board[code]:>4} {need:>5} {jl.get('componentLibraryType', '?'):8} {stock:>10} "
              f"{lc.get('stockNumber', '?'):>10}  {lc.get('brandNameEn')} {lc.get('productModel')} "
              f"({refs[code][0]}{'...' if len(refs[code]) > 1 else ''}) {' '.join(flags)}")
    print(f"{len(per_board)} LCSC numbers, {args.boards} boards per half: " + ("; ".join(short) or "all in stock"))
    return 1 if short else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
