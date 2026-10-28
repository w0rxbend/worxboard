# SPDX-License-Identifier: GPL-3.0-or-later
"""Post-build checks on the right peripheral build (design.md §14 WS1).

    python3 firmware/zmk/scripts/fw_check.py [build/fw]

- its link map has no zmk_ble_ (or battery) symbols: the right screen is wired-only
- its FLASH use grew less than FLASH_BUDGET over the seed build (zmk @ 4dd95d78)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ARTIFACT = "worxboard_right_peripheral"
SEED_FLASH = 165400        # bytes, seed right build (scratchpad zmktest/right.log)
FLASH_BUDGET = 40 * 1024   # bytes of allowed growth
FORBIDDEN = re.compile(r"\bzmk_ble_\w*|\bzmk_battery_\w*")


def main(argv: list[str]) -> int:
    out = Path(argv[0] if argv else "build/fw")
    bdir = out / ARTIFACT / "zephyr"
    errors = []

    hits = sorted(set(FORBIDDEN.findall((bdir / "zmk.map").read_text())))
    if hits:
        errors.append(f"forbidden symbols in {ARTIFACT}: {', '.join(hits[:10])}")

    log = out / f"{ARTIFACT}.log"   # written by fw_build.py
    m = re.search(r"^\s*FLASH:\s+(\d+) B", log.read_text(), flags=re.M)
    used = int(m.group(1)) if m else None
    if used is None:
        errors.append(f"FLASH usage not found in {log}")
    else:
        grow = used - SEED_FLASH
        print(f"{ARTIFACT}: FLASH {used} B (seed {SEED_FLASH} B, {grow:+d} B, budget {FLASH_BUDGET} B)")
        if grow >= FLASH_BUDGET:
            errors.append(f"FLASH grew {grow} B, budget {FLASH_BUDGET} B")

    for e in errors:
        print(e, file=sys.stderr)
    if not errors:
        print(f"{ARTIFACT}: no zmk_ble_/zmk_battery_ symbols")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
