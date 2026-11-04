# SPDX-License-Identifier: GPL-3.0-or-later
"""Post-build checks on the core builds (design.md §14 WS1).

    python3 firmware/zmk/scripts/fw_check.py [build/fw]

Checks every core artifact present under the output directory (CI builds one row per job and
runs this in the two core jobs); at least one must be there:
- both core rows: the display is turned to portrait for the J3 mounting (header at the back):
  CONFIG_WORXBOARD_DISPLAY_ROTATION_90 and the rotating flush (src/worx_display_rotation.c) linked
- right peripheral: its link map has no zmk_ble_ (or battery) symbols, the custom screen is in,
  its LVGL heap is at least CUSTOM_HEAP, and its FLASH use grew less than FLASH_BUDGET over the
  seed build (zmk @ 4dd95d78)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

LEFT = "worxboard_left_central"
RIGHT = "worxboard_right_peripheral"
SEED_FLASH = 165400        # bytes, seed right build (scratchpad zmktest/right.log)
FLASH_BUDGET = 40 * 1024   # bytes of allowed growth
CUSTOM_HEAP = 8192         # bytes, CONFIG_LV_Z_MEM_POOL_SIZE with the custom screen (Kconfig.defconfig)
FORBIDDEN = re.compile(r"\bzmk_ble_\w*|\bzmk_battery_\w*")
ROTATION_SYMBOLS = ("worx_display_rotation_init", "flush_rotated")


def kconfig(bdir: Path) -> dict[str, str]:
    lines = (bdir / ".config").read_text().splitlines()
    return dict(line.split("=", 1) for line in lines if line.startswith("CONFIG_"))


def check_display(name: str, bdir: Path) -> list[str]:
    errors = []
    if kconfig(bdir).get("CONFIG_WORXBOARD_DISPLAY_ROTATION_90") != "y":
        errors.append(f"{name}: CONFIG_WORXBOARD_DISPLAY_ROTATION_90 is not set")
    link_map = (bdir / "zmk.map").read_text()
    missing = [s for s in ROTATION_SYMBOLS if not re.search(rf"\b{s}\b", link_map)]
    if missing:
        errors.append(f"{name}: display rotation not linked ({', '.join(missing)} missing)")
    return errors


def check_right(out: Path, bdir: Path) -> list[str]:
    errors = []
    hits = sorted(set(FORBIDDEN.findall((bdir / "zmk.map").read_text())))
    if hits:
        errors.append(f"forbidden symbols in {RIGHT}: {', '.join(hits[:10])}")

    cfg = kconfig(bdir)
    if cfg.get("CONFIG_WORXBOARD_STATUS_SCREEN") != "y":
        errors.append(f"{RIGHT}: CONFIG_WORXBOARD_STATUS_SCREEN is not set")
    heap = int(cfg.get("CONFIG_LV_Z_MEM_POOL_SIZE", "0"))
    if heap < CUSTOM_HEAP:
        errors.append(f"{RIGHT}: CONFIG_LV_Z_MEM_POOL_SIZE {heap} < {CUSTOM_HEAP}")

    log = out / f"{RIGHT}.log"   # written by fw_build.py
    m = re.search(r"^\s*FLASH:\s+(\d+) B", log.read_text(), flags=re.M)
    used = int(m.group(1)) if m else None
    if used is None:
        errors.append(f"FLASH usage not found in {log}")
    else:
        grow = used - SEED_FLASH
        print(f"{RIGHT}: FLASH {used} B (seed {SEED_FLASH} B, {grow:+d} B, budget {FLASH_BUDGET} B)")
        if grow >= FLASH_BUDGET:
            errors.append(f"FLASH grew {grow} B, budget {FLASH_BUDGET} B")
    return errors


def main(argv: list[str]) -> int:
    out = Path(argv[0] if argv else "build/fw")
    present = [a for a in (LEFT, RIGHT) if (out / a / "zephyr" / ".config").exists()]
    errors = [] if present else [f"neither {LEFT} nor {RIGHT} is built under {out}"]

    for name in present:
        bdir = out / name / "zephyr"
        found = check_display(name, bdir)
        if name == RIGHT:
            found += check_right(out, bdir)
        if not found:
            what = "portrait display" + (", no zmk_ble_/zmk_battery_ symbols" if name == RIGHT else "")
            print(f"{name}: {what}")
        errors += found

    for e in errors:
        print(e, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
