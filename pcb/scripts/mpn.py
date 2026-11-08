# SPDX-License-Identifier: GPL-3.0-or-later
"""Manufacturer and part number of every LCSC number in design.py: pcb/scripts/mpn.json.

    python3 pcb/scripts/mpn.py check              # offline: every LCSC number has an entry (CI, stage P)
    python3 pcb/scripts/mpn.py fetch [C...]       # network: (re)write mpn.json from LCSC

JLC orders by LCSC number; PCBWay (pcbway.py) buys by manufacturer part number, so its BOM takes them
from mpn.json. `fetch` asks LCSC's product API (https://wmsc.lcsc.com/ftps/wm/product/detail, curl
with a browser User-Agent: LCSC refuses Python's own client) for:
  - every LCSC number design.py names: its parts on both halves, and every number in its strings and
    comments (the documented fallbacks and second sources), less the numbers it retired (RETIRED);
  - every number already in mpn.json (parts kept for a coming revision or as alternates);
  - the numbers given on the command line (add new parts before design.py has them).
It refreshes all of them; `--missing` fetches only those without an entry. Each entry keeps LCSC's
brandNameEn, productModel, productIntroEn and encapStandard as manufacturer, mpn, description and
package, and the date it was read.

`check` needs no network and no third-party module: it fails if a number design.py names has no entry
or an entry lacks a manufacturer or part number. Run `fetch` after adding a part to design.py.
"""
from __future__ import annotations

import ast
import datetime
import io
import json
import re
import subprocess
import sys
import tokenize
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DESIGN = HERE / "design.py"
MPN_JSON = HERE / "mpn.json"
LCSC_API = "https://wmsc.lcsc.com/ftps/wm/product/detail?productCode={}"
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"
LCSC = re.compile(r"\bC[1-9]\d{3,}\b")      # LCSC numbers (4+ digits here); not C0402 or a designator
FIELDS = {"manufacturer": "brandNameEn", "mpn": "productModel", "description": "productIntroEn",
          "package": "encapStandard"}


def _retired(source: str) -> set[str]:
    """design.RETIRED's keys, read without importing design.py (it needs shapely through layout)."""
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "RETIRED" for t in node.targets):
            return set(ast.literal_eval(node.value))
    raise SystemExit(f"{DESIGN}: no RETIRED dict")


def named_in_source() -> dict[str, str]:
    """LCSC number -> where design.py names it, from its string literals and comments."""
    source = DESIGN.read_text(encoding="utf-8")
    retired = _retired(source)
    out: dict[str, str] = {}
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type in (tokenize.STRING, tokenize.COMMENT):
            for code in LCSC.findall(tok.string):
                if code not in retired:
                    out.setdefault(code, f"design.py line {tok.start[0]}")
    return out


def fitted() -> dict[str, str]:
    """LCSC number -> first designator, over the parts design(side) has fitted on both halves. Needs
    design.py importable (shapely: the KiCad container's site313 or the uv venv)."""
    sys.path.insert(0, str(HERE))
    sys.path.insert(0, str(ROOT))
    from design import design
    out: dict[str, str] = {}
    for side in ("left", "right"):
        for p in design(side):
            if p.in_bom and not p.dnp and p.lcsc:
                out.setdefault(p.lcsc, f"{p.ref} ({side})")
    return out


def required(with_parts: bool = True) -> dict[str, str]:
    """Every LCSC number design.py names: its fitted parts (both halves) and its strings and comments."""
    req = named_in_source()
    if with_parts:
        for code, where in fitted().items():
            req.setdefault(code, where)
    return dict(sorted(req.items(), key=lambda kv: int(kv[0][1:])))


def load() -> dict[str, dict[str, str]]:
    return json.loads(MPN_JSON.read_text(encoding="utf-8"))["parts"] if MPN_JSON.is_file() else {}


def problems(parts: dict[str, dict[str, str]], req: dict[str, str]) -> list[str]:
    errs = [f"{code} ({where}) has no entry in {MPN_JSON.name}: run `just pcb-mpn`" for code, where in req.items()
            if code not in parts]
    errs += [f"{code}: empty {f}" for code, e in parts.items() for f in ("manufacturer", "mpn")
             if not (e.get(f) or "").strip()]
    return errs


def cmd_check(argv: list[str]) -> int:
    try:
        req, how = required(), "parts of both halves, strings and comments"
    except ModuleNotFoundError as e:           # design.py needs shapely; its source names every number
        req, how = required(with_parts=False), f"strings and comments ({e.name} missing: parts not imported)"
    parts = load()
    errs = problems(parts, req)
    for e in errs:
        print(f"FAIL  {e}")
    extra = sorted(set(parts) - set(req), key=lambda c: int(c[1:]))
    print(f"mpn check: {len(req)} LCSC numbers in design.py ({how}), {len(parts)} entries"
          + (f" ({len(extra)} not in design.py: {' '.join(extra)})" if extra else "") + f", {len(errs)} errors")
    return 1 if errs else 0


def lcsc(code: str) -> dict:
    out = subprocess.run(["curl", "-sS", "--max-time", "40", "--retry", "2", "-A", USER_AGENT,
                          "-H", "Accept: application/json", LCSC_API.format(code)],
                         capture_output=True, text=True, check=True)
    return json.loads(out.stdout).get("result") or {}


def cmd_fetch(argv: list[str]) -> int:
    missing_only = "--missing" in argv
    asked = [a for a in argv if a != "--missing"]
    bad = [a for a in asked if not LCSC.fullmatch(a)]
    if bad:
        raise SystemExit(f"not LCSC numbers: {bad}")
    parts = load()
    try:
        req = required()
    except ModuleNotFoundError:
        req = required(with_parts=False)
    codes = sorted(set(req) | set(parts) | set(asked), key=lambda c: int(c[1:]))
    if missing_only:
        codes = [c for c in codes if c not in parts]
    today = datetime.date.today().isoformat()
    errs = []
    for code in codes:
        r = lcsc(code)
        if r.get("productCode") != code:
            errs.append(f"{code}: LCSC returned no product")
            continue
        entry = {k: " ".join(str(r.get(src) or "").split()) for k, src in FIELDS.items()}
        entry["fetched"] = today
        parts[code] = entry
        print(f"  {code:10} {entry['manufacturer']} {entry['mpn']} ({entry['package']}): {entry['description']}")
    doc = {"_about": "LCSC number -> manufacturer, part number, description, package (LCSC product API). "
                     "Written by `python3 pcb/scripts/mpn.py fetch` (just pcb-mpn); do not edit.",
           "parts": dict(sorted(parts.items(), key=lambda kv: int(kv[0][1:])))}
    MPN_JSON.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    errs += problems(parts, req)
    for e in errs:
        print(f"FAIL  {e}")
    print(f"mpn fetch: {len(codes)} read, {len(parts)} entries in {MPN_JSON.relative_to(ROOT)}")
    return 1 if errs else 0


def main(argv: list[str]) -> int:
    if argv[:1] == ["check"] and len(argv) == 1:
        return cmd_check(argv[1:])
    if argv[:1] == ["fetch"]:
        return cmd_fetch(argv[1:])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
