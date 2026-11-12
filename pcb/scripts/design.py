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

GROUPS = ("MCU", "USB-POWER", "TRRS", "DISPLAY", "RGB", "MATRIX")

# Footprints
R0402 = "Resistor_SMD:R_0402_1005Metric"
C0402 = "Capacitor_SMD:C_0402_1005Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"
SOD123 = "Diode_SMD:D_SOD-123"
TESTPAD = "TestPoint:TestPoint_Pad_D1.0mm"
HOLE_FP = "MountingHole:MountingHole_2.7mm_M2.5"
MX_FP = "worxboard:SW_MX_Hotswap_Kailh"
STAB_FP = "worxboard:Stab_MX_2u"

# Value -> LCSC (spec §7; [G3] parts are re-checked before ordering)
LCSC_R = {"5.1k": "C25905", "27": "C2909343", "1k": "C11702", "10k": "C25744",
          "15k": "C25756", "470": "C25117"}
# Rev B: the 10 uF caps are 0603 10 V X5R (CL10A106KP8NNNC, JLC basic). The 0402 6.3 V part (C15525)
# kept only ~2-3 uF at the ~5 V of VSYS (DC bias); 0603 10 V keeps more (docs/deviations.md REVB-3)
LCSC_C = {"100n": "C1525", "1u": "C52923", "10u": "C19702", "27p": "C1557"}
C_FP = {"10u": C0603}           # every other value is 0402
LCSC_F1 = "C70076"        # nSMD050-24V: 1206 PTC, 500 mA hold, 24 V. Rev B feeds the far half's LEDs through
                          # two of them in series: the 250 mA C70069 ran at 78 % of hold (deviations REVB-9)
# Replacements for discontinued / low-stock parts (docs/deviations.md ELEC-1), JLC stock 2026-11-02
LCSC_SOCKET = "C41430893"   # HanElectricity CPG151101S11-16 MX hot-swap socket (Kailh C2803348 discontinued);
                            # second source C49352235 (CPG151101S11-2), same land pattern
LCSC_FLASH = "C97521"       # W25Q128JVSIQ SOIC-8 208 mil, JLC basic (C113767 no longer manufactured)
LCSC_XTAL = "C49304726"     # YXC XL2EL89CRI-111YLC-12M: 12 MHz 3225, CL 18 pF (27 pF caps), ESR 80 ohm
                            # (C91749 down to 19 at JLC); basic fallback C9002, CL 20 pF
# J3: JLC-assembled THT 1x5 2.54 mm female socket, 5.0 mm tall: with the nice!view's own 5-pin male
# header the module sits 7.0 mm above the PCB, as on its stock 5 mm socket (docs/deviations.md ELEC-3)
LCSC_J3 = "C27985230"       # Hong Cheng HC-PM254-5.0H-1x5PZ; 5.7 mm fallback C46061764 (stack 7.7 mm)
J3_FP = "worxboard:PinSocket_1x05_P2.54mm_Vertical_H5.0mm"   # stock pads, 5.0 mm 3D model
# LCSC numbers this design dropped: netcmp.py fails on one in a netlist, a board or the JLC BOM, and
# tests/integration/stock.py in the stock check (docs/deviations.md ELEC-1, ELEC-6)
RETIRED = {
    "C2803348": "Kailh CPG151101S11 hot-swap socket: discontinued (JLC and LCSC 0, 2026-11-02)",
    "C113767": "W25Q128JVSIQ: no longer manufactured per JLC; same part is the basic C97521",
    "C91749": "Epson 12 MHz crystal: 19 left at JLC on 2026-11-02",
    "C15525": "10 uF 0402 6.3 V: replaced by the 0603 10 V C19702 for DC-bias margin (rev B, REVB-3)",
}
# Per-key RGB (rev B, docs/deviations.md REVB-1): SK6812MINI-E under every switch, VLED from VSYS through
# a current-limited switch the firmware enables, data through a 3.3 V -> VLED buffer
LCSC_LED = "C5149201"       # OPSCO SK6812MINI-E, reverse mount through a 3.4 x 3.0 mm cutout
LCSC_VLED_SW = "C55136"     # Silergy SY6280AAC: Ilim = 6800 / Rset; R14 15k -> 0.45 A (its 0.4 A minimum)
LCSC_BUF = "C100024"        # TI SN74LV1T34DBVR: VIH 2.0 V at 5 V VCC, 5.5 V tolerant input (no positive input
                            # clamp, so GP22 may drive it while VLED is off; U6 discharges VLED through 150 ohm)
LED_FP = "worxboard:LED_SK6812MINI-E_ReverseMount"   # stock, pads 0.1 mm out (gen_footprints.py)

# Matrix references: SK<n> socket + D<n> diode, n = KEY_REF0 + index in layout.keys()
# (the spec's SK_xx / D_xx names are not valid KiCad references; deviation WS2a-1)
KEY_REF0 = 101

# Power nets (netclass Power, spec §8.4)
POWER_NETS = ("VBUS", "VSYS", "VLINK", "VLED", "3V3", "GND")
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
    dnp: bool = False              # True: on the board but not fitted by JLC (no such part on rev A)
    key: str = ""                  # layout key id of a matrix SK/D part (also its "Key" field)
    extra: dict[str, str] = field(default_factory=dict)   # further symbol fields


def R(ref: str, value: str, a: str, b: str, group: str) -> Part:
    return Part(ref, "Device:R", value, R0402, LCSC_R[value], {"1": a, "2": b}, group)


def C(ref: str, value: str, net: str, group: str, **kw) -> Part:
    return Part(ref, "Device:C", value, C_FP.get(value, C0402), LCSC_C[value], {"1": net, "2": "GND"}, group, **kw)


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
        # U4's VBUS pin is its clamp reference, on VSYS: on VBUS, the RP2040's D+ pull-up back-drove
        # J1 VBUS to ~2.5 V through U4 whenever the half ran from VLINK (docs/deviations.md ELEC-2)
        Part("U4", "Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6", "C7519",
             {"I/O1": "USB_C_DP", "I/O2": "USB_C_DM", "VBUS": "VSYS", "GND": "GND"}, g),
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
        Part("F1", "Device:Polyfuse", "500mA", "Fuse:Fuse_1206_3216Metric", LCSC_F1,
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
        Part("U2", "Memory_Flash:W25Q128JVS", "W25Q128JVSIQ", "Package_SO:SOIC-8_5.3x5.3mm_P1.27mm", LCSC_FLASH,
             {"~{CS}": "QSPI_SS", "CLK": "QSPI_SCLK", "DI/IO_{0}": "QSPI_SD0", "DO/IO_{1}": "QSPI_SD1",
              "~{WP}/IO_{2}": "QSPI_SD2", "~{HOLD}/~{RESET}/IO_{3}": "QSPI_SD3", "VCC": "3V3", "GND": "GND"}, g),
        C("C5", "100n", "3V3", g),
        Part("Y1", "Device:Crystal_GND24", "12MHz", "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm", LCSC_XTAL,
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
    parts += [TP(f"TP{6 + i}", f"TP{6 + i}", g) for i in range(2)]       # GP24, GP25 spares (GP22/23: RGB)
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
        R("R11", "470", "TRRS_A", t["TRRS_A"], g),     # the side swap lives here. 470: with R13 the RX low level
        R("R12", "470", "TRRS_B", t["TRRS_B"], g),     # is 0.28 V, not the 0.55 V of 2 x 1k (deviations REVB-9)
        R("R13", "10k", "UART_RX", "3V3", g),
        TP("TP11", "TRRS_DET", g),
    ]


def _display() -> list[Part]:
    g = "DISPLAY"
    pins = dict(zip(map(str, range(1, 6)), ("DISP_MOSI", "DISP_SCK", "3V3", "GND", "DISP_CS")))
    return [
        Part("J3", "Connector_Generic:Conn_01x05", "HC-PM254-5.0H-1x5PZ", J3_FP, LCSC_J3, pins, g),
        TP("TP1", "DISP_DC", g), TP("TP2", "DISP_RST", g), TP("TP3", "DISP_BL", g),
    ]


def _rgb(side: str) -> list[Part]:
    """VLED switch, data buffer, and one SK6812MINI-E + 100 nF per key in chain order (layout.leds)."""
    g = "RGB"
    parts = [
        Part("U6", "worxboard:SY6280AAC", "SY6280AAC", "Package_TO_SOT_SMD:SOT-23-5", LCSC_VLED_SW,
             {"IN": "VSYS", "EN": "RGB_EN", "OUT": "VLED", "ISET": "VLED_ISET", "GND": "GND"}, g),
        R("R14", "15k", "VLED_ISET", "GND", g),
        R("R15", "10k", "RGB_EN", "GND", g),                 # LEDs off until the firmware enables VLED
        C("C21", "10u", "VSYS", g),                          # U6 IN: the SY6280 datasheet "strongly recommends"
                                                             # 10 uF at VIN (input ringing on an output short)
        C("C20", "10u", "VLED", g),                          # U6 OUT bulk
        # JLC's footprint of C100024 has pin 1 in the other corner from the SOT-23-5 row of
        # jlc_rotations.csv (AP2112K, SY6280): kikit takes this per-part correction instead (cpl_check)
        Part("U7", "74xGxx:74LVC1G34", "SN74LV1T34DBVR", "Package_TO_SOT_SMD:SOT-23-5", LCSC_BUF,
             {"1": None, "2": "RGB_DIN", "3": "GND", "4": "RGB_BUF", "5": "VLED"}, g,
             extra={"JLCPCB_CORRECTION": "0;0;180"}),
        C("C22", "100n", "VLED", g),                         # U7 VCC
        R("R16", "470", "RGB_BUF", "RGB_D101", g),           # the datasheet's input series resistor
    ]
    chain = layout.leds(side)
    for n, d in enumerate(chain):
        din = f"RGB_D{101 + n}"
        dout = f"RGB_D{102 + n}" if n + 1 < len(chain) else None
        key = {"Key": d["key"]}
        parts.append(Part(d["ref"], "LED:SK6812MINI-E", "SK6812MINI-E", LED_FP, LCSC_LED,
                          {"VDD": "VLED", "VSS": "GND", "DIN": din, "DOUT": dout}, g, key=d["key"], extra=key))
        parts.append(C(d["cap"], "100n", "VLED", g, key=d["key"], extra=key))
    return parts


def switch_net(key_id: str) -> str:
    return f"MX_{key_id}"


def _matrix(side: str) -> list[Part]:
    g = "MATRIX"
    parts = []
    for n, k in enumerate(layout.keys(side), KEY_REF0):
        key = {"Key": k.id}
        parts.append(Part(f"SK{n}", "worxboard:SW_Push_MX", "MX", MX_FP, LCSC_SOCKET,
                          {"1": f"COL{k.col}", "2": switch_net(k.id)}, g, key=k.id, extra=key))
        parts.append(Part(f"D{n}", "Diode:1N4148W", "1N4148W", SOD123, "C81598",
                          {"A": switch_net(k.id), "K": f"ROW{k.row}"}, g, key=k.id, extra=key))
    parts += [Part(f"H{i + 1}", "Mechanical:MountingHole", "MountingHole", HOLE_FP, "", {}, g, in_bom=False,
                   extra={"Hole": str(i)}) for i in range(len(layout.holes(side)))]
    return parts


def design(side: str) -> list[Part]:
    if side not in layout.SIDES:
        raise ValueError(f"side must be one of {layout.SIDES}")
    parts = [*_mcu(), *_usb_power(), *_trrs(side), *_display(), *_rgb(side), *_matrix(side)]
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
