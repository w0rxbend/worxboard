# SPDX-License-Identifier: GPL-3.0-or-later
"""RP2040 GPIO map (spec §3). FROZEN contract, identical on both PCBs.

Pin names are the KiCad 10 `MCU_RaspberryPi:RP2040` symbol names (the authority);
QFN numbers are informational.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Pin:
    name: str            # RP2040 symbol pin name
    qfn: int
    net: str | None      # None = no connection
    note: str = ""


ROW_GPIOS = tuple(range(8, 14))          # ROW0..ROW5, inputs with pull-down
COL_GPIOS = tuple(range(14, 21))         # COL0 (outer)..COL6 (inner), outputs
RIGHT_COL_GPIOS = COL_GPIOS[::-1]        # right .dts lists GP20..GP14 (col-offset 7)
UART_TX, UART_RX = 0, 1
UART_BAUD = 115200
DISP_SCK, DISP_MOSI, DISP_CS = 2, 3, 5   # PIO1 SPI; CS is active high

_COL_QFN = (17, 18, 27, 28, 29, 30, 31)

PINS: list[Pin] = [
    Pin("GPIO0", 2, "UART_TX", "UART0 TX -> 1k -> jack"),
    Pin("GPIO1", 3, "UART_RX", "UART0 RX <- 1k <- jack; 10k pull-up to 3V3"),
    Pin("GPIO2", 4, "DISP_SCK", "PIO1 SPI clock"),
    Pin("GPIO3", 5, "DISP_MOSI", "PIO1 SPI data"),
    Pin("GPIO4", 6, "DISP_DC", "TP1 (future TFT)"),
    Pin("GPIO5", 7, "DISP_CS", "display CS, active high"),
    Pin("GPIO6", 8, "DISP_RST", "TP2 (future TFT)"),
    Pin("GPIO7", 9, "DISP_BL", "TP3 (future TFT backlight)"),
    *(Pin(f"GPIO{g}", 11 + i, f"ROW{i}", "matrix row, pull-down") for i, g in enumerate(ROW_GPIOS)),
    *(Pin(f"GPIO{g}", q, f"COL{i}", "matrix column") for i, (g, q) in enumerate(zip(COL_GPIOS, _COL_QFN))),
    Pin("GPIO21", 32, "TRRS_DET", "test pad (future detect-gpios)"),
    Pin("GPIO22", 34, "TP4", "spare; reserved for RGB"),
    Pin("GPIO23", 35, "TP5", "spare"),
    Pin("GPIO24", 36, "TP6", "spare"),
    Pin("GPIO25", 37, "TP7", "spare"),
    Pin("GPIO26/ADC0", 38, "VBUS_SENSE", "VBUS 10k/10k divider, unused by rev A"),
    Pin("GPIO27/ADC1", 39, None),
    Pin("GPIO28/ADC2", 40, None),
    Pin("GPIO29/ADC3", 41, None),
    Pin("~{QSPI_SS}", 56, "QSPI_SS", "flash CS, 10k pull-up; BOOT -> 1k -> GND"),
    Pin("RUN", 26, "RUN", "10k pull-up; RESET -> GND"),
    Pin("SWCLK", 24, "SWCLK", "SWD test pad"),
    Pin("SWDIO", 25, "SWDIO", "SWD test pad"),
    Pin("TESTEN", 19, "GND"),
    Pin("XIN", 20, "XIN", "12 MHz crystal"),
    Pin("XOUT", 21, "XOUT", "1k series to crystal"),
    Pin("USB_DM", 46, "USB_DM", "27R series"),
    Pin("USB_DP", 47, "USB_DP", "27R series"),
]

BY_NET = {p.net: p for p in PINS if p.net}

# TRRS contacts per side (spec §6.2): the TX/RX crossover is in the netlist
TRRS = {
    "left": {"T": "TRRS_A", "R1": "TRRS_B", "R2": "VLINK", "S": "GND",
             "TRRS_A": "UART_TX", "TRRS_B": "UART_RX"},
    "right": {"T": "TRRS_A", "R1": "TRRS_B", "R2": "VLINK", "S": "GND",
              "TRRS_A": "UART_RX", "TRRS_B": "UART_TX"},
}


def gpio(net: str) -> int:
    """GPIO number of a GPIO net, e.g. gpio('COL3') == 17."""
    name = BY_NET[net].name
    return int(name[4:].split("/")[0])
