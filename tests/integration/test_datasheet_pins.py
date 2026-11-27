# SPDX-License-Identifier: GPL-3.0-or-later
"""The committed boards against the datasheet pin tables (PLANS.md PR-15).

netcmp.py proves the board carries design.py's nets by symbol pin name, and cpl_check.py proves
JLC's pad 1 lands on KiCad's pad 1. Neither checks that a symbol numbers its pins as the part's
datasheet does: U6 is a custom symbol, and a swapped IN/OUT there would put VSYS on the LED plane
with no limit. This table is written from the datasheets, not from design.py, and each pad of the
committed boards must carry the net its datasheet function implies.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

import pcbdata

SIDES = ("left", "right")
UNCONNECTED = "unconnected-"
NO_NET = None

# ref -> (part value, datasheet and page, {pad: (datasheet function, net)}). LCSC PDFs, read 2026-11-26.
DATASHEET_PINS = {
    "U3": ("AP2112K-3.3", "Diodes AP2112, LCSC C51118, p. 2 Pin Descriptions (SOT25)", {
        "1": ("VIN", "VSYS"), "2": ("GND", "GND"), "3": ("EN", "VSYS"), "4": ("NC", NO_NET), "5": ("VOUT", "3V3")}),
    "U4": ("USBLC6-2SC6", "ST USBLC6-2, LCSC C7519, p. 1 pin-out (SOT23-6L)", {
        "1": ("I/O1", "USB_C_DP"), "2": ("GND", "GND"), "3": ("I/O2", "USB_C_DM"),
        "4": ("I/O2", "USB_C_DM"), "5": ("VBUS", "VSYS"), "6": ("I/O1", "USB_C_DP")}),
    "U5": ("USBLC6-2SC6", "ST USBLC6-2, LCSC C7519, p. 1 pin-out (SOT23-6L)", {
        "1": ("I/O1", "TRRS_A"), "2": ("GND", "GND"), "3": ("I/O2", "TRRS_B"),
        "4": ("I/O2", "TRRS_B"), "5": ("VBUS", "VLINK"), "6": ("I/O1", "TRRS_A")}),
    "U6": ("SY6280AAC", "Silergy SY6280, LCSC C55136, p. 2 pin table", {
        "1": ("OUT", "VLED"), "2": ("GND", "GND"), "3": ("ISET", "VLED_ISET"), "4": ("EN", "RGB_EN"), "5": ("IN", "VSYS")}),
    "U7": ("SN74LV1T34DBVR", "TI SN74LV1T34, LCSC C100024, p. 1 DBV pin-out", {
        "1": ("N.C.", NO_NET), "2": ("A", "RGB_DIN"), "3": ("GND", "GND"), "4": ("Y", "RGB_BUF"), "5": ("VCC", "VLED")}),
}

# OPSCO SK6812MINI-E-012 rev B/1, LCSC C5149201, p. 5 Pin Function Description: 1 GND, 2 DIN, 3 VDD, 4 DOUT
LED_VALUE = "SK6812MINI-E"
LED_GND, LED_DIN, LED_VDD, LED_DOUT = "1", "2", "3", "4"
LED_DATA_PREFIX = "RGB_D"                   # RGB_D<n> runs from LED<n-1> DOUT to LED<n> DIN
CHAIN_FEED = "R16"                          # its RGB_D net is the chain's first DIN


def wrong_pads(part: pcbdata.Part, pins: dict[str, tuple[str, str | None]]) -> list[str]:
    """Each pad whose net differs from its datasheet function's net."""
    errors = []
    for pad, (function, want) in pins.items():
        got = part.pads.get(pad, "")
        if want is NO_NET and not got.startswith(UNCONNECTED):
            errors.append(f"pad {pad} ({function}) is on {got}, want no net")
        elif want is not NO_NET and got != want:
            errors.append(f"pad {pad} ({function}) is on {got or 'no net'}, want {want}")
    return errors


def data_index(net: str) -> int | None:
    """n of an RGB_D<n> net, or None for any other net."""
    tail = net.removeprefix(LED_DATA_PREFIX)
    return int(tail) if tail != net and tail.isdigit() else None


def led_errors(pcb: pcbdata.Pcb) -> list[str]:
    """Supply pads, data direction (each DOUT feeds the next DIN) and the chain head at R16."""
    leds = {ref: p for ref, p in pcb.parts.items() if p.value == LED_VALUE}
    errors = []
    for ref, led in sorted(leds.items()):
        errors += [f"{ref}: {e}" for e in wrong_pads(led, {LED_GND: ("GND", "GND"), LED_VDD: ("VDD", "VLED")})]
        din, dout = data_index(led.pads.get(LED_DIN, "")), led.pads.get(LED_DOUT, "")
        if din is None:
            errors.append(f"{ref}: pad {LED_DIN} (DIN) is on {led.pads.get(LED_DIN)}, want an {LED_DATA_PREFIX} net")
        elif not (dout.startswith(UNCONNECTED) or data_index(dout) == din + 1):
            errors.append(f"{ref}: pad {LED_DOUT} (DOUT) is on {dout}, want {LED_DATA_PREFIX}{din + 1} or no net")
    feed = {net for net in pcb.parts[CHAIN_FEED].pads.values() if data_index(net) is not None}
    heads = {ref for ref, led in leds.items() if led.pads.get(LED_DIN) in feed}
    if len(heads) != 1:
        errors.append(f"{CHAIN_FEED} feeds DIN of {sorted(heads)}, want exactly one LED")
    return errors


@pytest.mark.parametrize("side", SIDES)
@pytest.mark.parametrize("ref", sorted(DATASHEET_PINS))
def test_part_pads_match_datasheet(side: str, ref: str) -> None:
    value, source, pins = DATASHEET_PINS[ref]
    part = pcbdata.board(side).parts[ref]
    assert part.value == value, f"{side} {ref} is {part.value}, the table is for {value}"
    assert not (errors := wrong_pads(part, pins)), f"{side} {ref} against {source}: " + "; ".join(errors)


@pytest.mark.parametrize("side", SIDES)
def test_leds_match_datasheet(side: str) -> None:
    pcb = pcbdata.board(side)
    assert sum(p.value == LED_VALUE for p in pcb.parts.values()) == 37
    assert not (errors := led_errors(pcb)), f"{side}: " + "; ".join(errors)


def test_led_check_catches_swapped_supply_pads() -> None:
    pcb = pcbdata.board("left")
    led = pcb.parts["LED101"]
    swapped = {**led.pads, LED_GND: led.pads[LED_VDD], LED_VDD: led.pads[LED_GND]}
    mutated = replace(pcb, parts={**pcb.parts, "LED101": replace(led, pads=swapped)})
    assert any(e.startswith("LED101: pad 1") for e in led_errors(mutated))


def test_led_check_catches_reversed_data_pads() -> None:
    pcb = pcbdata.board("left")
    led = pcb.parts["LED101"]
    reversed_data = {**led.pads, LED_DIN: led.pads[LED_DOUT], LED_DOUT: led.pads[LED_DIN]}
    mutated = replace(pcb, parts={**pcb.parts, "LED101": replace(led, pads=reversed_data)})
    assert led_errors(mutated)
