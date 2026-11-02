# Electrical design

Rev A, from spec §2–§9, as built in the committed boards (`pcb/left/`, `pcb/right/`). Pin-level
tables are generated: [pinout.md](pinout.md) (GPIOs, TRRS, J3, part positions) and
[matrix.md](matrix.md) (key matrix, sockets and diodes). Parts are in [bom.md](bom.md).

## Architecture

```
                LEFT half (ZMK central)                         RIGHT half (ZMK peripheral)
 host ──USB-C──► VBUS ─D1─► VSYS ─U3─► 3V3 ─► RP2040 ─┐   ┌─ RP2040 ◄─ 3V3 ◄─U3─ VSYS ◄─D1─ VBUS ◄──USB-C (power/flash)
                          │                 │ UART0  │   │ UART0 │                 │
                          JP1─F1─► VLINK ═══╪════════╪═══╪═══════╪═════ VLINK ◄─F1─JP1
                                   TRRS  Ring2 ══════════ Ring2  TRRS
                                         Tip  (TX)  ════  Tip  (RX)
                                         Ring1(RX)  ════  Ring1(TX)
                                         Sleeve GND ════  Sleeve GND
   37-key 6×7 diode matrix (col2row) · nice!view LCD on PIO1-SPI · BOOT + RESET · SWD pads   (same on both halves)
```

- **One RP2040 per half**, on the PCB (QFN-56), with the Corne v4.1 support circuit: W25Q128 QSPI
  flash, 12 MHz crystal, AP2112K 3.3 V LDO.
- **Wired split**: ZMK `zmk,wired-split` on hardware UART0 (GP0 TX, GP1 RX), full duplex at
  115 200 baud. The TX/RX crossover is in the PCB netlist, so the firmware pinctrl is the same on
  both halves.
- **Host on the left.** The left half is the central. The right USB-C gives power and UF2 flashing.
- **Two PCBs from one script**: `worxboard-left` and `worxboard-right`, 2-layer, 1.6 mm, ENIG. They
  have the same parts and references and share one matrix netlist; only R11/R12 (the TRRS data
  lines) differ.

## Reference designators

The same on both halves (deviations WS2a-1, WS2a-2):

| Function | References |
|---|---|
| RP2040, flash, crystal | U1, U2, Y1 (load caps C6/C7, XOUT series R7) |
| USB-C, ESD, CC and series resistors | J1, U4, R1/R2 (5.1 kΩ CC1/CC2), R3/R4 (27 Ω D+/D−) |
| Power: Schottky, LDO, bulk caps | D1, U3, C1/C2 (VSYS), C3/C4 (3V3) |
| Cable power: jumper, polyfuse | JP1, F1 |
| VBUS sense divider | R5, R6 |
| Decoupling | C5 (flash), C8–C15 (3V3 pins), C16/C17 (DVDD), C18/C19 (VREG_VIN/VOUT) |
| BOOT and RESET | SW1 (BOOT) with R9 1 kΩ and R8 10k QSPI_SS pull-up; SW2 (RESET) with R10 10k RUN pull-up |
| TRRS jack, ESD, series resistors, RX pull-up | J2, U5, R11/R12 (1 kΩ), R13 (10k) |
| Display socket | J3 (DNP, hand-soldered) |
| Test pads | TP1–TP3 display DC/RST/BL, TP4–TP7 GP22–GP25, TP8 SWCLK, TP9 SWDIO, TP10 GND, TP11 TRRS_DET |
| Key matrix | SK101–SK137 sockets, D101–D137 diodes ([matrix.md](matrix.md#sockets-and-diodes)) |
| Mounting holes, stabiliser holes | H1–H8, STAB_T4/STAB_T5 |

## Power path

The same on each half:

```
USB-C VBUS ──┬── U4 USBLC6-2SC6 VBUS pin (USB ESD)
             ├── R5 10k ─┬─ GP26 (VBUS_SENSE) ── R6 10k ── GND
             └── D1 B5819W (1 A Schottky, SOD-123) ──► VSYS (~4.6 V)
VSYS ── C1, C2 10 µF ── GND
VSYS ── U3 AP2112K-3.3 (EN tied to VIN) ──► 3V3 (RP2040, flash, display)   C3 10 µF + C4 1 µF out
VSYS ── JP1 SolderJumper_2_Bridged ── F1 PTC 1206, 250 mA hold ──► VLINK ── TRRS Ring2
VLINK ── U5 USBLC6-2SC6 VBUS pin (TRRS ESD; IO1 = TRRS_A, IO2 = TRRS_B)
```

- **Two hosts at once are safe.** Each VBUS reaches VSYS only through its own D1. The cable joins
  the two VSYS nets *after* both diodes, so no host is ever back-fed; the higher VBUS supplies both
  halves.
- **One cable is enough.** The far half runs from VLINK at about 4.4 V. The AP2112K dropout is about
  250 mV, which leaves margin. 1117-type regulators (about 1 V dropout) would not.
- **JP1** (bridged by default) joins VSYS to the cable. It sits on the top side in the back strip,
  next to F1 and the USB-C, under the case top. Cut it on **both** halves for split-powered mode,
  where each half needs its own USB-C ([build guide](buildguide_en.md#3-choose-the-power-mode-jp1)).
- **F1** (C70069, nSMD025-24V: 250 mA hold, 24 V; deviation WS2a-4) limits the current into VLINK.
  It protects against shorts while a plug is inserted and keeps the PJ-320 contacts below their
  roughly 300 mA rating.
- **VBUS_SENSE** (GP26 / ADC0) sees VBUS through a 10k/10k divider, about 2.5 V. Rev A firmware does
  not use it; it is there for future host detection.

## TRRS link

| Contact | Left PCB | Right PCB | Why |
|---|---|---|---|
| Tip | `TRRS_A` = UART_TX (GP0 via R11 1 kΩ) | `TRRS_A` = UART_RX (GP1 via R11 1 kΩ) | The tip wipes every spring while the plug slides in, so only 1 kΩ-limited data lines are on it |
| Ring1 | `TRRS_B` = UART_RX (via R12) | `TRRS_B` = UART_TX (via R12) | Crossed in the netlist; the firmware is identical |
| Ring2 | VLINK | VLINK | Next to the sleeve, so it can only touch the sleeve spring; that short is limited by F1 |
| Sleeve | GND | GND | |

- The 1 kΩ series resistors sit at the jack on both data lines; U5 clamps the jack side.
- R13 pulls UART_RX up to 3V3 (10 kΩ) on the MCU side, so it idles high with no cable.
- The jack is a PJ-320D-4A SMD part (C95562) on the top side, assembled by JLC. Its mouth is at the
  inner board edge in a local bump, centred at y 103.0, between the inner-column keys. The case
  leaves 0.5 mm above a 5.5 mm body (gate G2).
- Use a **straight** 4-pole cable. **Do not hot-plug it**: the silkscreen next to the jack says
  `DO NOT HOT-PLUG TRRS` and `HOST → LEFT` on both halves.

## USB-C

- HRO TYPE-C-31-M-12 (C165948) on both halves, centred at x 186.0 in the right frame (x 74.0 in the
  left frame), with its mouth flush with the back edge.
- CC1 and CC2 each have 5.1 kΩ to GND (R1, R2): the board is a USB sink and gets 5 V from any USB-C
  host.
- A6/B6 and A7/B7 are tied together, so either plug orientation works. 27 Ω series resistors (R3,
  R4) on D+ and D−. SBU is not connected; the shield goes to GND.
- U4 (USBLC6-2SC6) is within 5 mm of the receptacle.
- Full-speed USB (12 Mbps) does not need controlled impedance. The pair runs on the top side with
  0.25 mm tracks, over a B.Cu track keepout so the ground pour under it stays solid. As built
  (`checks.py`, U1 pin to J1 pin): left D+ 24.73 mm / D− 23.92 mm (skew 0.81 mm), right
  23.75 / 23.50 mm (skew 0.25 mm), inside the 25 mm and 1 mm limits. On the left half the keepout
  stops at U4, so B.Cu tracks may cross under the pair there for about 1 mm (deviation WS2b-7;
  harmless at full speed).

## MCU support circuit

Cloned from the Corne v4.1 production BOM, with these values:

- **Flash** U2 W25Q128JVSIQ, C5 100 nF decoupling, R8 10k pull-up on QSPI_SS.
- **Crystal** Y1 12 MHz 3225, 2 × 27 pF load capacitors (C6, C7), R7 1 kΩ in series on XOUT. Its
  courtyard is within 3 mm of the XIN/XOUT pads (measured by `checks.py`, 2.93 mm on both halves).
- **Decoupling**: 100 nF for the six IOVDD pins, USB_VDD and ADC_AVDD (C8–C15) and both DVDD pins
  (C16, C17); 1 µF on VREG_VIN (C18) and VREG_VOUT (C19); DVDD is tied to VREG_VOUT (net `1V1`). The
  IOVDD pins are joined inside the QFN pad ring, so their capacitors sit on the 3V3 net near the
  exits rather than one at each pin (deviation WS2b-5).
- **Buttons**: SW1 (BOOT) pulls QSPI_SS to GND through R9 1 kΩ; SW2 (RESET) pulls RUN to GND (R10
  10k pull-up). Both are TS-1088R tact switches at (176, 50) and (180, 50) in the right frame,
  reachable through Ø3 pin holes in the case top.
- **SWD**: three test pads, TP8 SWCLK, TP9 SWDIO and TP10 GND, for a debug probe. They are on the
  top side in the back strip ([pinout.md](pinout.md#part-positions)), under the case top.

## Display

- Sharp LS011B7DH03 memory LCD, 160 × 68, on a nice!view-compatible module: 3-wire SPI, 3.3 V,
  under 10 µA. It replaces the top key of the inner column on both halves.
- Plugged into J3, a 1×5 female socket (pin order MOSI, SCK, VCC, GND, CS; gate G1). J3 is DNP:
  the builder solders it.
- Driven by **PIO1** as an SPI master (`raspberrypi,pico-spi-pio`): clock GP2, data GP3, chip
  select GP5, **active high**. The RP2040's PL022 hardware SPI cannot send LSB-first, which the
  memory LCD needs. The ZMK driver is `sharp,ls0xx` at 1 MHz with serial VCOM inversion.
- GP4, GP6 and GP7 go to test pads TP1–TP3 (DC, RST, BL) for a future TFT.

## Key matrix

- 6 rows × 7 columns, `col2row`: columns are driven, rows are read with internal pull-downs.
- One 1N4148W diode per key on the bottom side next to its socket: anode on the switch net
  (`MX_<key>`), cathode on the row.
- 37 keys per half. The unused slots are (R0, C6) for the display and (R2, C6), (R4, C5), (R4, C6),
  (R5, C0).
- Both PCBs share one matrix netlist. The right `.dts` reverses `col-gpios` (GP20…GP14) and sets
  `col-offset = <7>`, which mirrors the right half into global columns 7–13. Full tables:
  [matrix.md](matrix.md).

## Spare pins

| GPIO | Use |
|---|---|
| GP21 | TP11 `TRRS_DET` (future `detect-gpios`) |
| GP22 | TP4, reserved for future RGB |
| GP23–GP25 | TP5–TP7, spare |
| GP27–GP29 | not connected |

## PCB rules

| Item | Value |
|---|---|
| Stack-up | 2 layers, 1.6 mm FR4, 1 oz copper, ENIG |
| Default netclass | 0.25 mm track, 0.2 mm clearance |
| Power netclass (VBUS, VSYS, VLINK, 3V3, GND) | 0.5 mm track, 0.2 mm clearance |
| USB netclass | 0.25 mm track, 0.2 mm gap |
| RP2040 fan-out, U1 signal nets, matrix rows/columns | 0.15–0.18 mm (deviation WS2b-3) |
| Board minimum | 0.127 mm track and clearance (JLC 2-layer, gate G3) |
| Vias | 0.3 mm drill, 0.6 mm pad |
| Board-edge clearance | 0.5 mm |
| Ground | pours on both layers; stitching vias on a 5 mm grid around U1/Y1/J1 and a 10 mm grid elsewhere, placed after routing where they land in filled GND on both layers (deviation WS2b-4) |
| Mounting holes | Ø6.5 rule area (no tracks, vias or pour) on both layers |

The stitching vias are the fix for the EMI issue reported on the Corne v4
([foostan/crkbd#265](https://github.com/foostan/crkbd/issues/265)).

## Placement zones

Top-side parts must sit in one of two zones, because the rest of the top side is under the plate
spacer (0.5 mm gap):

- **Z_BACK**: the strip along the back edge (y < 57 mm) between the key cells. It holds the USB-C,
  the RP2040 cluster, the buttons, JP1/F1, the test pads and the J3 header end.
- **Z_TRRS**: the inner-edge bump (x < 62.2, y 88–125.7 in the right frame). It holds the jack, U5
  and the TRRS resistors.

Two placements differ from the spec anchors: the left RP2040 is turned 180° and moved to
(93.4, 42.0), so its USB pins face J1 (deviation WS2b-1), and the flash U2 sits next to its QSPI
escapes, (154.6, 35.0) right and (96.0, 53.7) left (deviation WS2b-2). The case fit check runs
against the board STEP, so it covers the real positions.

The sockets and diodes are on the bottom side, in the 4 mm cavity of the bottom tray.

## How the boards are made

Every stage is a script, run headless in pinned containers (spec §9; `just pcb <side>`):

| Stage | Recipe | What it does |
|---|---|---|
| 1–6 | `just pcb-sch <side>` | footprints, `design.py` → schematic (kicad-sch-api), ERC (0 errors), netlist, `netcmp.py` against the design and `layout/pins.py` |
| 7–9 | `just pcb-place <side>` | placement from `layout.json`, locked critical routes (QFN fan-out, USB pair, matrix), DSN |
| — | `just pcb-route <side>` | Freerouting 2.5.0 |
| 10–12 | `just pcb-finish <side>` | session import, completion router with rip-up (WS2b-6), pours, stitching, DRC gate, `checks.py` |
| 11–12 | `just pcb-drc <side>` | the DRC gate and checks on the committed board only |
| 13–14 | `just pcb-fab <side>` | KiKit JLC files, renders, Edge DXF, STEP (in `kicad/kicad:10.0.7-full`) |

The gate is `kicad-cli pcb drc --schematic-parity --severity-error`: both committed boards pass
with 0 violations, 0 unconnected items and 0 parity issues. The layout stages are seeded, so a
from-scratch rebuild reproduces the committed boards byte for byte; the `pcb` workflow's `rebuild`
job checks that (deviation WS2c-4). A full rebuild takes about 20 minutes per side.
