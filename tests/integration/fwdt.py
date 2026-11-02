# SPDX-License-Identifier: GPL-3.0-or-later
"""The firmware devicetree facts that must agree with the PCB: matrix GPIOs, transform, UART, display.

    source(dts)       a committed board .dts with its quoted #includes inlined (later nodes win)
    compiled(dts)     a built build/fw/<artifact>/zephyr/zephyr.dts (what the firmware really has)

Both return the same `FwPins`, so the tests compare the two readers too.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

GPIO_FLAGS = {"GPIO_ACTIVE_HIGH": 0x0, "GPIO_ACTIVE_LOW": 0x1, "GPIO_PULL_UP": 0x10, "GPIO_PULL_DOWN": 0x20}
PULL_DOWN = GPIO_FLAGS["GPIO_PULL_DOWN"]
ACTIVE_LOW = GPIO_FLAGS["GPIO_ACTIVE_LOW"]

# Zephyr RP2XXX_PINMUX(pin, func) = pin << 5 | func (dt-bindings/pinctrl/rpi-pico-pinctrl-common.h)
PINMUX_PIN_POS, PINMUX_FUNC_MASK = 5, 0x1F
PINMUX_FUNCS = {2: "UART", 6: "PIO0", 7: "PIO1"}
PINMUX_MACRO = re.compile(r"^(UART|PIO)(\d)_(?:\w+_)?P(\d+)$")      # UART0_TX_P0, PIO1_P2

# RC(row, col) = row << 8 | col (zmk dt-bindings/zmk/matrix_transform.h)
RC_ROW_SHIFT, RC_COL_MASK = 8, 0xFF

COMMENT = re.compile(r"/\*.*?\*/|//[^\n]*", re.S)
INCLUDE = re.compile(r'^#include\s+"([^"]+)"', re.M)
GPIO_CELL = re.compile(r"<\s*&gpio0\s+(\w+)\s*([^>]*)>")


def rp2040_uart(gpio: int) -> tuple[int, str]:
    """(instance, role) of the UART function on a GPIO: RP2040 datasheet §1.4.3 function table.
    UART0 TX/RX sit on GP0/1, 12/13, 16/17, 28/29 and UART1 on GP4/5, 8/9, 20/21, 24/25."""
    return ((gpio + 4) // 8) % 2, ("TX", "RX", "CTS", "RTS")[gpio % 4]


@dataclass(frozen=True)
class Gpio:
    pin: int
    flags: int


@dataclass(frozen=True)
class FwPins:
    rows: tuple[Gpio, ...]
    cols: tuple[Gpio, ...]
    col_offset: int
    transform: tuple[tuple[int, int], ...]   # global (row, col) per keymap position
    uart: dict[str, int]                     # role -> GPIO of the wired-split UART0 pinctrl
    uart_input: frozenset[int]               # UART pins with input-enable
    spi: dict[str, Gpio]                     # clk / mosi / cs of the PIO1 display SPI
    pio1: frozenset[int]                     # GPIOs muxed to PIO1


def _flatten(path: Path) -> str:
    """The file with its quoted #includes inlined, recursively (system <...> includes are left out)."""
    text = path.read_text()
    return INCLUDE.sub(lambda m: _flatten((path.parent / m.group(1)).resolve()), text)


def _blocks(text: str, label: str) -> list[str]:
    """Bodies of every node defined as `label: name {` or referenced as `&label {`, in order."""
    out = []
    for m in re.finditer(rf"(?:\b{label}:\s*[\w@,-]+|&{label})\s*\{{", text):
        depth, i = 1, m.end()
        while depth:
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            i += 1
        out.append(text[m.end():i - 1])
    if not out:
        raise ValueError(f"no node labelled {label}")
    return out


def _prop(blocks: list[str], name: str, default: str | None = None) -> str:
    """Value of a property; a later block overrides an earlier one, as in dtc."""
    found = [m.group(1) for b in blocks for m in re.finditer(rf"(?<![\w-]){name}\s*=\s*([^;]*);", b)]
    if found:
        return found[-1]
    if default is None:
        raise ValueError(f"property {name} not found")
    return default


def _int(tok: str) -> int:
    return int(tok.strip(" <>()"), 0)


def _gpios(value: str) -> tuple[Gpio, ...]:
    out = []
    for pin, flags in GPIO_CELL.findall(value):
        flags = flags.strip()
        bits = _int(flags) if re.fullmatch(r"\(?\s*(0x[0-9a-fA-F]+|\d+)\s*\)?", flags or "0") else \
            sum(GPIO_FLAGS[f] for f in re.findall(r"GPIO_\w+", flags))
        out.append(Gpio(_int(pin), bits))
    return tuple(out)


def _pinmux(token: str) -> tuple[int, str]:
    """(gpio, function) of one pinmux cell: a Zephyr macro (source) or its number (compiled)."""
    m = PINMUX_MACRO.match(token)
    if m:
        return int(m.group(3)), m.group(1) if m.group(1) == "UART" else f"PIO{m.group(2)}"
    v = _int(token)
    return v >> PINMUX_PIN_POS, PINMUX_FUNCS.get(v & PINMUX_FUNC_MASK, f"func{v & PINMUX_FUNC_MASK}")


def _groups(block: str) -> list[tuple[list[tuple[int, str]], bool]]:
    """pinctrl groups: (pinmux cells, input-enable)."""
    out = []
    for body in re.findall(r"group\d+\s*\{([^}]*)\}", block):
        cells = re.findall(r"<\s*([^>]+?)\s*>", _prop([body], "pinmux"))
        out.append(([_pinmux(t) for c in cells for t in c.split()], "input-enable" in body))
    return out


def parse(text: str) -> FwPins:
    text = COMMENT.sub("", text)
    kscan, transform = _blocks(text, "kscan0"), _blocks(text, "default_transform")
    spi = _blocks(text, "nice_view_spi")
    cells = _prop(transform, "map")
    rc = [(int(r), int(c)) for r, c in re.findall(r"RC\(\s*(\d+)\s*,\s*(\d+)\s*\)", cells)] or \
        [(v >> RC_ROW_SHIFT, v & RC_COL_MASK) for v in map(_int, cells.strip(" <>").split())]
    uart, uart_input = {}, set()
    for mux, inp in (g for b in _blocks(text, "uart0_default") for g in _groups(b)):
        for gpio, func in mux:
            inst, role = rp2040_uart(gpio)
            if func != "UART" or inst != 0:
                raise ValueError(f"uart0_default GP{gpio} is {func}, not UART0")
            uart[role] = gpio
            if inp:
                uart_input.add(gpio)
    pio1 = {g for b in _blocks(text, "pio1_spi_default") for mux, _ in _groups(b)
            for g, f in mux if f == "PIO1"}
    return FwPins(
        rows=_gpios(_prop(kscan, "row-gpios")),
        cols=_gpios(_prop(kscan, "col-gpios")),
        col_offset=_int(_prop(transform, "col-offset", "0")),
        transform=tuple(rc),
        uart=uart,
        uart_input=frozenset(uart_input),
        spi={k: _gpios(_prop(spi, f"{k}-gpios"))[0] for k in ("clk", "mosi", "cs")},
        pio1=frozenset(pio1),
    )


def source(dts: Path) -> FwPins:
    return parse(_flatten(dts))


def compiled(dts: Path) -> FwPins:
    return parse(dts.read_text())
