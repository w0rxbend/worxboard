# Electrical design

Rev A, from spec §2–§9. Pin-level tables are generated: [pinout.md](pinout.md) (GPIOs, TRRS, J3,
anchors) and [matrix.md](matrix.md) (key matrix). Parts are in [bom.md](bom.md).

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
  share the same matrix netlist; only the TRRS data lines differ.

## Power path

The same on each half:

```
USB-C VBUS ──┬── U4 USBLC6-2SC6 VBUS pin (USB ESD)
             ├── R 10k ─┬─ GP26 (VBUS_SENSE) ── R 10k ── GND
             └── D1 B5819W (1 A Schottky, SOD-123) ──► VSYS (~4.6 V)
VSYS ── C 10 µF ── GND
VSYS ── U3 AP2112K-3.3 (EN tied to VIN) ──► 3V3 (RP2040, flash, display)   10 µF in, 10 µF + 1 µF out
VSYS ── JP1 SolderJumper_2_Bridged ── F1 Polyfuse 1206, 250 mA hold ──► VLINK ── TRRS Ring2
VLINK ── U5 USBLC6-2SC6 VBUS pin (TRRS ESD; IO1 = TRRS_A, IO2 = TRRS_B)
```

- **Two hosts at once are safe.** Each VBUS reaches VSYS only through its own D1. The cable joins
  the two VSYS nets *after* both diodes, so no host is ever back-fed; the higher VBUS supplies both
  halves.
- **One cable is enough.** The far half runs from VLINK at about 4.4 V. The AP2112K dropout is about
  250 mV, which leaves margin. 1117-type regulators (about 1 V dropout) would not.
- **JP1** (bridged by default) joins VSYS to the cable. Cut it on **both** halves for
  split-powered mode, where each half needs its own USB-C ([build guide](buildguide_en.md#3-choose-the-power-mode-jp1)).
- **F1** limits the current into VLINK. It protects against shorts while a plug is inserted and keeps
  the PJ-320 contacts below their roughly 300 mA rating.
- **VBUS_SENSE** (GP26 / ADC0) sees VBUS through a 10k/10k divider, about 2.5 V. Rev A firmware does
  not use it; it is there for future host detection.

## TRRS link

| Contact | Left PCB | Right PCB | Why |
|---|---|---|---|
| Tip | `TRRS_A` = UART_TX (GP0 via 1 kΩ) | `TRRS_A` = UART_RX (GP1 via 1 kΩ) | The tip wipes every spring while the plug slides in, so only 1 kΩ-limited data lines are on it |
| Ring1 | `TRRS_B` = UART_RX | `TRRS_B` = UART_TX | Crossed in the netlist; the firmware is identical |
| Ring2 | VLINK | VLINK | Next to the sleeve, so it can only touch the sleeve spring; that short is limited by F1 |
| Sleeve | GND | GND | |

- 1 kΩ series resistors sit at the jack on both data lines; U5 clamps the jack side.
- The RX line has a 10 kΩ pull-up to 3V3 on the MCU side, so it idles high with no cable.
- The jack is a PJ-320D-4A SMD part (C95562) on the top side, assembled by JLC. Its mouth is at the
  inner board edge in a local bump, centred at y 103.0, between the inner-column keys.
- Use a **straight** 4-pole cable. **Do not hot-plug it**: the silkscreen says so on both halves.

## USB-C

- HRO TYPE-C-31-M-12 (C165948) on both halves, centred at x 186.0 in the right frame (x 74.0 in the
  left frame), with its mouth flush with the back edge.
- CC1 and CC2 each have 5.1 kΩ to GND: the board is a USB sink and gets 5 V from any USB-C host.
- A6/B6 and A7/B7 are tied together, so either plug orientation works. 27 Ω series resistors on D+
  and D−. SBU is not connected; the shield goes to GND.
- U4 (USBLC6-2SC6) is within 5 mm of the receptacle.
- Full-speed USB (12 Mbps) does not need controlled impedance. The pair is routed on the top side
  with 0.25 mm tracks and a 0.2 mm gap, at most 25 mm long and matched within 1 mm, over a solid
  ground pour (the bottom side under the pair is a track keepout).

## MCU support circuit

Cloned from the Corne v4.1 production BOM, with these values:

- **Flash** U2 W25Q128JVSIQ, 100 nF decoupling, 10k pull-up on QSPI_SS.
- **Crystal** Y1 12 MHz 3225, 2 × 27 pF load capacitors, 1 kΩ in series on XOUT, within 3 mm of the
  XIN/XOUT pins, with a ground guard and no traces underneath.
- **Decoupling**: 100 nF on every IOVDD pin, USB_VDD, ADC_AVDD and both DVDD pins; 1 µF on VREG_IN
  and VREG_VOUT; DVDD tied to VREG_VOUT.
- **Buttons**: SW_BOOT pulls QSPI_SS to GND through 1 kΩ; SW_RST pulls RUN to GND (10k pull-up).
  Both are TS-1088R tact switches near the USB-C, reachable through pin holes in the case top.
- **SWD**: three test pads (GND, SWCLK, SWDIO) for a debug probe.

## Display

- Sharp LS011B7DH03 memory LCD, 160 × 68, on a nice!view-compatible module: 3-wire SPI, 3.3 V,
  under 10 µA. It replaces the top key of the inner column on both halves.
- Plugged into J3, a 1×5 female socket (pin order MOSI, SCK, VCC, GND, CS; gate G1).
- Driven by **PIO1** as an SPI master (`raspberrypi,pico-spi-pio`): clock GP2, data GP3, chip
  select GP5, **active high**. The RP2040's PL022 hardware SPI cannot send LSB-first, which the
  memory LCD needs. The ZMK driver is `sharp,ls0xx` at 1 MHz with serial VCOM inversion.
- GP4, GP6 and GP7 go to test pads TP1–TP3 (DC, RST, BL) for a future TFT.

## Key matrix

- 6 rows × 7 columns, `col2row`: columns are driven, rows are read with internal pull-downs.
- 1N4148W diode per key on the bottom side: anode on the switch/column side, cathode on the row.
- 37 keys per half. The unused slots are (R0, C6) for the display and (R2, C6), (R4, C5), (R4, C6),
  (R5, C0).
- Both PCBs share one matrix netlist. The right `.dts` reverses `col-gpios` (GP20…GP14) and sets
  `col-offset = <7>`, which mirrors the right half into global columns 7–13. Full tables:
  [matrix.md](matrix.md).

## Spare pins

| GPIO | Use |
|---|---|
| GP21 | `TRRS_DET` test pad (future `detect-gpios`) |
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
| QFN fan-out | 0.15 mm (scripted) |
| Board minimum | 0.127 mm track and clearance |
| Vias | 0.3 mm drill, 0.6 mm pad |
| Board-edge clearance | 0.5 mm |
| Ground | pours on both layers, stitching vias on a 5 mm grid around U1/Y1/J1 and a 10 mm grid elsewhere |

The stitching vias are the fix for the EMI issue reported on the Corne v4
([foostan/crkbd#265](https://github.com/foostan/crkbd/issues/265)).

## Placement zones

Top-side parts must sit in one of two zones, because the rest of the top side is under the plate
spacer (0.5 mm gap):

- **Z_BACK**: the strip along the back edge (y < 57 mm) between the key cells. It holds the USB-C,
  the RP2040 cluster, the buttons and the J3 header end.
- **Z_TRRS**: the inner-edge bump (x < 62.2, y 88–125.7 in the right frame). It holds the jack, U5 and
  the two 1 kΩ resistors.

The sockets and diodes are on the bottom side, in the 4 mm cavity of the bottom tray.

The PCB pipeline (KiCad 10 in Docker, Freerouting, KiKit) is described in spec §9 and run by
`just pcb <side>`.
