# SPDX-License-Identifier: GPL-3.0-or-later
"""Post-build checks on the core builds (design.md §14 WS1).

    python3 firmware/zmk/scripts/fw_check.py [build/fw]

Checks every core artifact present under the output directory (CI builds one row per job and
runs this in the two core jobs); at least one must be there:
- both core rows: one portrait orientation (90 or 270 degrees) is selected and the rotating
  flush (src/worx_display_rotation.c) is linked
- both core rows, per-key RGB (docs/firmware.md#rgb): the zmk,underglow strip is a 37-LED GRB
  ws2812 PIO strip on PIO0 at the RGB_DATA GPIO, a zmk,ext-power-generic node switches the RGB_EN
  GPIO (layout/pins.py), underglow drives ext-power and turns off when idle, BRT_MAX is at most
  BRT_CAP, and the strip, ext-power and rgb_ug behaviour (which the central relays) are linked
- right peripheral: its link map has no zmk_ble_ (or battery) symbols, the custom screen is in,
  its LVGL heap is at least CUSTOM_HEAP, and its FLASH use grew less than FLASH_BUDGET over the
  seed build (zmk @ 4dd95d78)
"""
from __future__ import annotations

import importlib.util
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

# Per-key RGB (rev B). layout/pins.py is the GPIO contract; it is loaded on its own because the
# layout package imports shapely.
PINS_PY = Path(__file__).resolve().parents[3] / "layout/pins.py"
_spec = importlib.util.spec_from_file_location("worxboard_pins", PINS_PY)
pins = sys.modules[_spec.name] = importlib.util.module_from_spec(_spec)   # @dataclass looks it up
_spec.loader.exec_module(pins)
BRT_CAP = 8                # %, CONFIG_ZMK_RGB_UNDERGLOW_BRT_MAX in the board *_defconfig files
LED_COUNT = 37             # SK6812MINI-E per half, one per key (layout/leds.py CHAIN)
GRB = [2, 1, 3]            # LED_COLOR_ID_GREEN, _RED, _BLUE
RGB_KCONFIG = ("CONFIG_ZMK_RGB_UNDERGLOW", "CONFIG_WS2812_STRIP_RPI_PICO_PIO", "CONFIG_ZMK_EXT_POWER",
               "CONFIG_ZMK_RGB_UNDERGLOW_EXT_POWER")
IDLE_OFF = "CONFIG_ZMK_RGB_UNDERGLOW_AUTO_OFF_IDLE"   # saves "off": the board would boot dark
RGB_SYMBOLS = ("ws2812_led_strip_update_rgb", "ext_power_generic_init", "zmk_rgb_underglow_init",
               "behavior_rgb_underglow_driver_api")


def kconfig(bdir: Path) -> dict[str, str]:
    lines = (bdir / ".config").read_text().splitlines()
    return dict(line.split("=", 1) for line in lines if line.startswith("CONFIG_"))


def check_display(name: str, bdir: Path) -> list[str]:
    errors = []
    cfg = kconfig(bdir)
    rotations = [angle for angle in (90, 270) if cfg.get(f"CONFIG_WORXBOARD_DISPLAY_ROTATION_{angle}") == "y"]
    if len(rotations) != 1:
        errors.append(f"{name}: select exactly one display rotation (90 or 270 degrees)")
    link_map = (bdir / "zmk.map").read_text()
    missing = [s for s in ROTATION_SYMBOLS if not re.search(rf"\b{s}\b", link_map)]
    if missing:
        errors.append(f"{name}: display rotation not linked ({', '.join(missing)} missing)")
    return errors


def dt_nodes(dts: str) -> list[dict]:
    """The nodes of a generated zephyr.dts: name, labels, parent and raw property values."""
    nodes, stack = [], []
    for line in dts.splitlines():
        s = line.strip()
        if s.endswith("{"):
            *labels, name = s[:-1].split()
            node = {"name": name, "labels": [lb.rstrip(":") for lb in labels],
                    "parent": stack[-1] if stack else None, "props": {}}
            nodes.append(node)
            stack.append(node)
        elif s == "};" and stack:
            stack.pop()
        elif stack and s.endswith(";"):
            key, _, value = s[:-1].partition("=")
            stack[-1]["props"][key.strip()] = value.strip()
    return nodes


def cells(node: dict, prop: str) -> list:
    """`< &gpio0 0x16 0x0 >` -> ['&gpio0', 22, 0]; [] when the property is missing."""
    raw = node["props"].get(prop, "").replace("<", " ").replace(">", " ").replace(",", " ")
    return [tok if tok.startswith("&") else int(tok, 0) for tok in raw.split()]


def okay(node: dict | None, compatible: str) -> bool:
    return (node is not None and f'"{compatible}"' in node["props"].get("compatible", "")
            and node["props"].get("status", '"okay"') == '"okay"')


def check_rgb(name: str, bdir: Path) -> list[str]:
    errors = []
    cfg = kconfig(bdir)
    errors += [f"{name}: {key} is not set" for key in RGB_KCONFIG if cfg.get(key) != "y"]
    if cfg.get(IDLE_OFF) == "y":
        errors.append(f"{name}: {IDLE_OFF} is set, the keyboard would boot dark after an idle spell")
    brt = cfg.get("CONFIG_ZMK_RGB_UNDERGLOW_BRT_MAX")
    if brt is None or int(brt) > BRT_CAP:
        errors.append(f"{name}: CONFIG_ZMK_RGB_UNDERGLOW_BRT_MAX is {brt or 'unset'}, cap {BRT_CAP} %")
    if cfg.get("CONFIG_USB_DEVICE_STACK") == "y" and (cfg.get("CONFIG_USB_MAX_POWER") != "250"
                                                      or cfg.get("CONFIG_USB_SELF_POWERED") == "y"):
        errors.append(f"{name}: the USB descriptor must declare 500 mA, bus powered (USB_MAX_POWER=250, "
                      f"USB_SELF_POWERED off), got {cfg.get('CONFIG_USB_MAX_POWER')} / {cfg.get('CONFIG_USB_SELF_POWERED')}")

    nodes = dt_nodes((bdir / "zephyr.dts").read_text())
    by_label = {lb: n for n in nodes for lb in n["labels"]}
    chosen = next((n for n in nodes if n["name"] == "chosen"), {"props": {}})
    strip = by_label.get(chosen["props"].get("zmk,underglow", "").lstrip("&"))
    if strip is None:
        errors.append(f"{name}: no zmk,underglow LED strip in the devicetree")
    else:
        pio = strip["parent"]
        if not (okay(pio, "worldsemi,ws2812-rpi_pico-pio") and "pio0" in pio["parent"]["labels"]):
            errors.append(f"{name}: the underglow strip is not a ws2812-rpi_pico-pio strip on &pio0")
        want = {"chain-length": [LED_COUNT], "gpios": ["&gpio0", pins.RGB_DATA, 0], "color-mapping": GRB}
        errors += [f"{name}: underglow strip {prop} is {cells(strip, prop)}, want {value}"
                   for prop, value in want.items() if cells(strip, prop) != value]
    ext = [n for n in nodes if okay(n, "zmk,ext-power-generic")]
    if [cells(n, "control-gpios") for n in ext] != [["&gpio0", pins.RGB_EN, 0]]:
        errors.append(f"{name}: want one zmk,ext-power-generic node on GP{pins.RGB_EN}, active high")

    link_map = (bdir / "zmk.map").read_text()
    missing = [s for s in RGB_SYMBOLS if not re.search(rf"\b{s}\b", link_map)]
    if missing:
        errors.append(f"{name}: RGB not linked ({', '.join(missing)} missing)")
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
        found = check_display(name, bdir) + check_rgb(name, bdir)
        if name == RIGHT:
            found += check_right(out, bdir)
        if not found:
            what = f"portrait display, {LED_COUNT}-LED RGB strip with ext-power, BRT_MAX <= {BRT_CAP}"
            what += ", no zmk_ble_/zmk_battery_ symbols" if name == RIGHT else ""
            print(f"{name}: {what}")
        errors += found

    for e in errors:
        print(e, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
