# SPDX-License-Identifier: GPL-3.0-or-later
"""Parts and nets of one worxboard half as Python data (spec §3, §5, §6, §7; §9 stage 2).

`design(side)` returns the same parts, references and pin maps on both halves. The side
argument applies ONLY the TRRS_A/B <-> UART_TX/RX swap of spec §6.2 (`layout.pins.TRRS`).

Pin keys are a symbol pin number, else a pin name (a name connects every pin carrying it,
e.g. the six stacked RP2040 IOVDD pins). A net of None places a no-connect flag.

    python3 pcb/scripts/design.py <side>     # print the part list and net summary
"""
from __future__ import annotations

import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import layout  # noqa: E402
from layout.pins import PINS, TRRS  # noqa: E402

GROUPS = ("MCU", "USB-POWER", "TRRS", "DISPLAY", "MATRIX")

# Footprints
R0402 = "Resistor_SMD:R_0402_1005Metric"
C0402 = "Capacitor_SMD:C_0402_1005Metric"
SOD123 = "Diode_SMD:D_SOD-123"
TESTPAD = "TestPoint:TestPoint_Pad_D1.0mm"
HOLE_FP = "MountingHole:MountingHole_2.7mm_M2.5"
MX_FP = "worxboard:SW_MX_Hotswap_Kailh"
STAB_FP = "worxboard:Stab_MX_2u"

# Value -> LCSC (spec §7; [G3] parts are re-checked before ordering)
LCSC_R = {"5.1k": "C25905", "27": "C2909343", "1k": "C11702", "10k": "C25744"}
LCSC_C = {"100n": "C1525", "1u": "C52923", "10u": "C15525", "27p": "C1557"}
LCSC_F1 = "C70069"        # nSMD025-24V: 1206 PTC, 250 mA hold, 24 V (WS2 choice, spec §7 F1)

# Matrix references: SK<n> socket + D<n> diode, n = KEY_REF0 + index in layout.keys()
# (the spec's SK_xx / D_xx names are not valid KiCad references; deviation WS2a-1)
KEY_REF0 = 101

# Power nets (netclass Power, spec §8.4)
POWER_NETS = ("VBUS", "VSYS", "VLINK", "3V3", "GND")
SUPPLY_PIN_NAMES = ("IOVDD", "USB_VDD", "ADC_AVDD", "DVDD", "VREG_VIN", "VREG_VOUT")


@dataclass(frozen=True)
class Part:
    ref: str
    lib_id: str
    value: str
    footprint: str
    lcsc: str                      # "" only for parts kept out of the JLC BOM
    pins: dict[str, str | None]    # pin number or name -> net (None = no connect)
    group: str
    in_bom: bool = True            # False: JP1, test pads, holes (spec §7)
    dnp: bool = False              # True: J3, hand-soldered by the builder
    key: str = ""                  # layout key id of a matrix SK/D part (also its "Key" field)
    extra: dict[str, str] = field(default_factory=dict)   # further symbol fields


def R(ref: str, value: str, a: str, b: str, group: str) -> Part:
    return Part(ref, "Device:R", value, R0402, LCSC_R[value], {"1": a, "2": b}, group)


def C(ref: str, value: str, net: str, group: str) -> Part:
    return Part(ref, "Device:C", value, C0402, LCSC_C[value], {"1": net, "2": "GND"}, group)


def TP(ref: str, net: str, group: str) -> Part:
    return Part(ref, "Connector:TestPoint", net, TESTPAD, "", {"1": net}, group, in_bom=False)


def _usb_power() -> list[Part]:
    g = "USB-POWER"
    return [
        Part("J1", "Connector:USB_C_Receptacle_USB2.0_16P", "TYPE-C-31-M-12",
             "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12", "C165948",
             {"VBUS": "VBUS", "GND": "GND", "SHIELD": "GND", "CC1": "CC1", "CC2": "CC2",
              "D+": "USB_C_DP", "D-": "USB_C_DM", "SBU1": None, "SBU2": None}, g),
        R("R1", "5.1k", "CC1", "GND", g),
        R("R2", "5.1k", "CC2", "GND", g),
        R("R3", "27", "USB_C_DP", "USB_DP", g),
        R("R4", "27", "USB_C_DM", "USB_DM", g),
        Part("U4", "Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6", "C7519",
             {"I/O1": "USB_C_DP", "I/O2": "USB_C_DM", "VBUS": "VBUS", "GND": "GND"}, g),
        R("R5", "10k", "VBUS", "VBUS_SENSE", g),
        R("R6", "10k", "VBUS_SENSE", "GND", g),
        Part("D1", "Device:D_Schottky", "B5819W", SOD123, "C8598", {"A": "VBUS", "K": "VSYS"}, g),
        C("C1", "10u", "VSYS", g),
        C("C2", "10u", "VSYS", g),
        Part("U3", "Regulator_Linear:AP2112K-3.3", "AP2112K-3.3", "Package_TO_SOT_SMD:SOT-23-5", "C51118",
             {"VIN": "VSYS", "EN": "VSYS", "GND": "GND", "VOUT": "3V3", "NC": None}, g),
        C("C3", "10u", "3V3", g),
        C("C4", "1u", "3V3", g),
        Part("JP1", "Jumper:SolderJumper_2_Bridged", "VLINK",
             "Jumper:SolderJumper-2_P1.3mm_Bridged_RoundedPad1.0x1.5mm", "",
             {"A": "VSYS", "B": "VLINK_JP"}, g, in_bom=False),
        Part("F1", "Device:Polyfuse", "250mA", "Fuse:Fuse_1206_3216Metric", LCSC_F1,
             {"1": "VLINK_JP", "2": "VLINK"}, g),
    ]


def _mcu() -> list[Part]:
    g = "MCU"
    u1 = {p.name: p.net for p in PINS}
    u1.update({"IOVDD": "3V3", "USB_VDD": "3V3", "ADC_AVDD": "3V3", "VREG_VIN": "3V3",
               "VREG_VOUT": "1V1", "DVDD": "1V1", "GND": "GND",
               "QSPI_SCLK": "QSPI_SCLK", "QSPI_SD0": "QSPI_SD0", "QSPI_SD1": "QSPI_SD1",
               "QSPI_SD2": "QSPI_SD2", "QSPI_SD3": "QSPI_SD3"})
    parts = [
        Part("U1", "MCU_RaspberryPi:RP2040", "RP2040", "Package_DFN_QFN:QFN-56-1EP_7x7mm_P0.4mm_EP3.2x3.2mm",
             "C2040", u1, g),
        Part("U2", "Memory_Flash:W25Q128JVS", "W25Q128JVSIQ", "Package_SO:SOIC-8_5.3x5.3mm_P1.27mm", "C113767",
             {"~{CS}": "QSPI_SS", "CLK": "QSPI_SCLK", "DI/IO_{0}": "QSPI_SD0", "DO/IO_{1}": "QSPI_SD1",
              "~{WP}/IO_{2}": "QSPI_SD2", "~{HOLD}/~{RESET}/IO_{3}": "QSPI_SD3", "VCC": "3V3", "GND": "GND"}, g),
        C("C5", "100n", "3V3", g),
        Part("Y1", "Device:Crystal_GND24", "12MHz", "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm", "C91749",
             {"1": "XIN", "3": "XTAL_OUT", "G": "GND"}, g),
        R("R7", "1k", "XTAL_OUT", "XOUT", g),
        C("C6", "27p", "XIN", g),
        C("C7", "27p", "XTAL_OUT", g),
        R("R8", "10k", "QSPI_SS", "3V3", g),
        R("R9", "1k", "QSPI_SS", "BOOT", g),
        Part("SW1", "Switch:SW_Push", "BOOT", "Button_Switch_SMD:SW_SPST_TS-1088-xR020", "C455280",
             {"1": "BOOT", "2": "GND"}, g),
        R("R10", "10k", "RUN", "3V3", g),
        Part("SW2", "Switch:SW_Push", "RESET", "Button_Switch_SMD:SW_SPST_TS-1088-xR020", "C455280",
             {"1": "RUN", "2": "GND"}, g),
    ]
    # 100 nF on each IOVDD (6), USB_VDD, ADC_AVDD and both DVDD; 1 uF on VREG_VIN and VREG_VOUT
    parts += [C(f"C{8 + i}", "100n", "3V3", g) for i in range(8)]
    parts += [C("C16", "100n", "1V1", g), C("C17", "100n", "1V1", g),
              C("C18", "1u", "3V3", g), C("C19", "1u", "1V1", g)]
    parts += [TP(f"TP{4 + i}", f"TP{4 + i}", g) for i in range(4)]       # GP22..GP25 spares
    parts += [TP("TP8", "SWCLK", g), TP("TP9", "SWDIO", g), TP("TP10", "GND", g)]
    return parts


def _trrs(side: str) -> list[Part]:
    g = "TRRS"
    t = TRRS[side]
    return [
        Part("J2", "Connector_Audio:AudioJack4", "PJ-320D-4A", "Connector_Audio:Jack_3.5mm_PJ320D_Horizontal",
             "C95562", {"T": t["T"], "R1": t["R1"], "R2": t["R2"], "S": t["S"]}, g),
        Part("U5", "Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6", "C7519",
             {"I/O1": "TRRS_A", "I/O2": "TRRS_B", "VBUS": "VLINK", "GND": "GND"}, g),
        R("R11", "1k", "TRRS_A", t["TRRS_A"], g),      # the side swap lives here
        R("R12", "1k", "TRRS_B", t["TRRS_B"], g),
        R("R13", "10k", "UART_RX", "3V3", g),
        TP("TP11", "TRRS_DET", g),
    ]


def _display() -> list[Part]:
    g = "DISPLAY"
    pins = dict(zip(map(str, range(1, 6)), ("DISP_MOSI", "DISP_SCK", "3V3", "GND", "DISP_CS")))
    return [
        Part("J3", "Connector_Generic:Conn_01x05", "nice!view", "Connector_PinSocket_2.54mm:PinSocket_1x05_P2.54mm_Vertical",
             "", pins, g, dnp=True),
        TP("TP1", "DISP_DC", g), TP("TP2", "DISP_RST", g), TP("TP3", "DISP_BL", g),
    ]


def switch_net(key_id: str) -> str:
    return f"MX_{key_id}"


def _matrix(side: str) -> list[Part]:
    g = "MATRIX"
    parts = []
    for n, k in enumerate(layout.keys(side), KEY_REF0):
        key = {"Key": k.id}
        parts.append(Part(f"SK{n}", "worxboard:SW_Push_MX", "MX", MX_FP, "C2803348",
                          {"1": f"COL{k.col}", "2": switch_net(k.id)}, g, key=k.id, extra=key))
        parts.append(Part(f"D{n}", "Diode:1N4148W", "1N4148W", SOD123, "C81598",
                          {"A": switch_net(k.id), "K": f"ROW{k.row}"}, g, key=k.id, extra=key))
    parts += [Part(f"H{i + 1}", "Mechanical:MountingHole", "MountingHole", HOLE_FP, "", {}, g, in_bom=False,
                   extra={"Hole": str(i)}) for i in range(len(layout.holes(side)))]
    return parts


def design(side: str) -> list[Part]:
    if side not in layout.SIDES:
        raise ValueError(f"side must be one of {layout.SIDES}")
    parts = [*_mcu(), *_usb_power(), *_trrs(side), *_display(), *_matrix(side)]
    refs = [p.ref for p in parts]
    assert len(refs) == len(set(refs)), "duplicate reference"
    return parts


def matrix_nets(parts: list[Part]) -> dict[str, frozenset[tuple[str, str]]]:
    """ROW/COL/MX_ nets -> {(ref, pin key)} over the matrix parts."""
    nets: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for p in parts:
        if p.group == "MATRIX":
            for pin, net in p.pins.items():
                nets[net].add((p.ref, pin))
    return {n: frozenset(v) for n, v in nets.items()}


def main(argv: list[str]) -> int:
    side = argv[1] if len(argv) > 1 else "right"
    parts = design(side)
    nets = {n for p in parts for n in p.pins.values() if n}
    for g in GROUPS:
        print(f"{g}: {' '.join(p.ref for p in parts if p.group == g)}")
    print(f"{len(parts)} parts, {len(nets)} nets, {sum(p.in_bom and not p.dnp for p in parts)} BOM lines")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
