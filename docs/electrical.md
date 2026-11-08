# Electrical design

Rev B, from spec §2–§9 and the rev B changes in [deviations.md](deviations.md#revb-rev-b-per-key-rgb-display-setback-and-review-fixes-layout-pcb-firmware-case-docs), as built in the committed boards (`pcb/left/`, `pcb/right/`). Pin-level
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
   37-key 6×7 diode matrix (col2row) · nice!view LCD on PIO1-SPI · 37 SK6812MINI-E per-key RGB on PIO0
   (GP22 → U7 buffer → LED101…LED137, VLED from VSYS through U6, enabled by GP23) · BOOT + RESET · SWD pads
   (same on both halves)
```

- **One RP2040 per half**, on the PCB (QFN-56), with the Corne v4.1 support circuit: W25Q128 QSPI
  flash, 12 MHz crystal, AP2112K 3.3 V LDO. JLCPCB fits every part, on both sides
  ([ordering-jlcpcb.md](ordering-jlcpcb.md)).
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
| Power: Schottky, LDO, bulk caps | D1, U3, C1 (VSYS, at D1 and U3), C2 (VSYS, at U4's reference pin), C3/C4 (3V3); C1–C3 are 10 µF 0603 10 V (rev B) |
| Cable power: jumper, polyfuse | JP1, F1 |
| VBUS sense divider | R5, R6 |
| Decoupling | C5 (flash), C8–C15 (3V3 pins), C16/C17 (DVDD), C18/C19 (VREG_VIN/VOUT) |
| BOOT and RESET | SW1 (BOOT) with R9 1 kΩ and R8 10k QSPI_SS pull-up; SW2 (RESET) with R10 10k RUN pull-up |
| TRRS jack, ESD, series resistors, RX pull-up | J2, U5, R11/R12 (1 kΩ), R13 (10k) |
| Display socket | J3 (1×5 2.54 mm, 5.0 mm THT socket C27985230, fitted by JLC) |
| Per-key RGB (rev B) | U6 SY6280AAC VLED switch (R14 15k ISET, R15 10k EN pull-down, C21 10 µF in, C20 10 µF out), U7 SN74LV1T34 data buffer (C22 100 nF, R16 470 Ω out), LED101–LED137 SK6812MINI-E with C101–C137 100 nF |
| Test pads | TP1–TP3 display DC/RST/BL, TP6/TP7 GP24/GP25, TP8 SWCLK, TP9 SWDIO, TP10 GND, TP11 TRRS_DET (rev A's TP4/TP5 on GP22/GP23 became the RGB lines) |
| Key matrix | SK101–SK137 sockets, D101–D137 diodes ([matrix.md](matrix.md#sockets-and-diodes)) |
| Mounting holes, stabiliser holes | H1–H8, STAB_T4/STAB_T5 |

## Power path

The same on each half:

```
USB-C VBUS ──┬── R5 10k ─┬─ GP26 (VBUS_SENSE) ── R6 10k ── GND
             └── D1 B5819W (1 A Schottky, SOD-123) ──► VSYS (~4.6 V)
VSYS ── C1 10 µF ── GND                        (at D1 and U3's input)
VSYS ── U4 USBLC6-2SC6 VBUS pin (USB ESD clamp reference) ── C2 10 µF ── GND   (C2 at the pin)
VSYS ── U3 AP2112K-3.3 (EN tied to VIN) ──► 3V3 (RP2040, flash, display)   C3 10 µF + C4 1 µF out
VSYS ── JP1 SolderJumper_2_Bridged ── F1 PTC 1206, 250 mA hold ──► VLINK ── TRRS Ring2
VLINK ── U5 USBLC6-2SC6 VBUS pin (TRRS ESD; IO1 = TRRS_A, IO2 = TRRS_B)
VSYS ── C21 10 µF ── U6 SY6280AAC (EN = GP23, R15 10k to GND; ISET R14 15k: 0.45 A) ──► VLED   C20 10 µF
VLED ── U7 SN74LV1T34 VCC (C22 100 nF), every LED VDD (each with its own 100 nF, C101–C137)
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
- **VBUS is a clean presence signal.** U4's clamp reference (its "VBUS" pin) is on **VSYS**, not
  on the connector's VBUS (deviation ELEC-2). VBUS reaches only J1, D1's anode and R5. With the
  reference on VBUS, the RP2040's 1.5 kΩ D+ pull-up forward-biased U4's I/O1-to-VBUS diode whenever a
  half ran from VLINK with its USB device enabled. J1's VBUS was then back-driven to about 2.5 V. Now,
  with no host, VBUS sits at D1's reverse leakage across R5 + R6, about 0.1 V. VSYS meets all four
  needs of a clamp reference:
  - it is at or above every I/O level whenever the I/Os can be driven;
  - it stays under the 5.25 V stand-off;
  - it carries 2 × 10 µF;
  - D1 blocks any path from it back to J1.

  `netcmp.py` fails if U4's reference leaves VSYS. C2 sits at U4's pin, 4.07 mm of copper away
  (BOARD-5, `checks.py`). The trade-off: U4's TVS no longer clamps the VBUS line itself. A positive
  surge goes through D1 into VSYS, where U4 and the bulk caps clamp it, and a negative one is
  blocked by D1.

### Review notes kept (rev B, deviations REVB-3)

- **C1–C3 are 10 µF 0603 10 V X5R** (CL10A106KP8NNNC, JLC basic C19702). Rev A's 0402 6.3 V part kept
  only about 2–3 µF at the ~5 V of VSYS (DC bias, an estimate): still above the AP2112K's 1 µF
  minimum, but with little margin. The 0603 10 V part keeps more.
- **Plug-in capacitance is above USB's nominal 10 µF.** Each half has 20 µF directly on VSYS (C1, C2),
  and the cable joins both halves' VSYS, so the host sees about 40 µF nominal (less after DC bias),
  plus what U3 charges behind it on each half. Almost every host tolerates this, and many split
  keyboards do the same. The rev B LEDs add nothing here: their 37 × 100 nF and C20 sit behind U6,
  which is off until the firmware enables it, and U6 limits that inrush to 0.45 A.
- **The firmware uses 4 MB of the 16 MB flash.** `worxboard.dtsi` declares 4 MB with the settings
  partition at 3.5 MB (an RP2040 board with 4 MB or more can run the same image); the other 12 MB go
  unused. That is safe.
- **RP2350 erratum E9.** The experimental RP2350A firmware target reads the matrix rows with internal
  pull-downs, which early RP2350 steppings get wrong (E9). A future RP2350 board must use the A4
  stepping, which fixes it; keep that requirement.

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
  inner board edge in a local bump, centred at y 103.0, between the inner-column keys. Its body,
  14.1 × 6.1 × 5.0 mm, is relieved in the case by 0.75 mm all round, with 1.0 mm headroom (gate G2;
  CASE-9).
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
- **Crystal** Y1 12 MHz 3225, YXC XL2EL89CRI-111YLC-12M (C49304726): CL 18 pF, ±10 ppm, ESR 80 Ω
  maximum (ELEC-1). It has 2 × 27 pF load capacitors (C6, C7) and R7, 1 kΩ in series on XOUT. The
  firmware waits 64× longer than the Pico SDK default for it to start (WS1-9). Its
  courtyard is within 3 mm of the XIN/XOUT pads (measured by `checks.py`, 2.93 mm on both halves).
  R7 sits beside the crystal, so XOUT runs about 5 mm without a via, and a B.Cu keepout over Y1
  keeps tracks and vias out from under it: both GND pours are solid there (deviation REVIEW-FIX-8).
- **Decoupling**: 100 nF for the six IOVDD pins, USB_VDD and ADC_AVDD (C8–C15) and both DVDD pins
  (C16, C17); 1 µF on VREG_VIN (C18) and VREG_VOUT (C19); DVDD is tied to VREG_VOUT (net `1V1`).
  Several supply pins are joined inside the QFN pad ring, so the caps sit at the five places where
  the supplies leave it, each joined to that exit and to its own GND via by locked copper
  (deviation REVIEW-FIX-2):

  | Exit | Caps | Pins served |
  |---|---|---|
  | North, pins 48/49 | C14, C15, C13, C10 | USB_VDD 48, IOVDD 49 |
  | East, pin 42 | C18 (1 µF), C11, C12 | IOVDD 42, ADC_AVDD 43, VREG_VIN 44; IOVDD 33 and 22 on the inner join |
  | West, pin 1 | C8, C9 | IOVDD 1; IOVDD 10 on the inner join |
  | Pin-50 fan end | C16, C19 (1 µF) | DVDD 50; VREG_VOUT 45 on the inner join |
  | Pin-23 fan end | C17 | DVDD 23 |

  `checks.py` measures the copper path from every supply pin to its nearest cap and from every cap
  to its nearest pin, and fails above 12 mm and 7 mm.
- **Ground return** (BOARD-14, ORDER-4). U1's only GND pin is its exposed pad (EP). Locked 0.5 mm
  B.Cu spurs run from the pad's vias to every cap's GND via, or into a GND fill that meets them.
  TESTEN (pin 19, tied to GND) runs out on a locked 0.2 mm track to a via in the Y1 keepout's GND
  fill, which reaches the back edge. On the left, where routing had left the pad's B.Cu on that one
  via, `gnd_ties.py` adds four locked 0.5 mm GND ties: two near U4 (the USB ESD clamp), one near
  U2, and one from U2's GND pin 4 to its cap C5. `checks.py` measures the shortest GND copper path
  on both layers, 1.6 mm per via hop, and gates:
  - each cap's GND pad to the EP, at most 20 mm: as built 9.3–13.0 mm on the left and 8.6–13.0 mm
    on the right;
  - the EP to the main B.Cu GND plane, at most 8 mm: 1.6 mm on both halves (all 9 EP vias sit in
    the plane);
  - at least 2 separate links from the EP to the planes, each over copper about 0.4 mm wide or
    wider: 2 on the left, 6 on the right;
  - U4 pin 2 to a J1 GND pad and C5 to U2 pin 4, at most 30 mm each: 22.3 and 11.4 mm on the left,
    17.4 and 18.0 mm on the right.
- **Buttons**: SW1 (BOOT) pulls QSPI_SS to GND through R9 1 kΩ; SW2 (RESET) pulls RUN to GND (R10
  10k pull-up). Both are TS-1088R tact switches at (176, 50) and (180, 50) in the right frame,
  reachable through Ø3 pin holes in the case top.
- **SWD**: three test pads, TP8 SWCLK, TP9 SWDIO and TP10 GND, for a debug probe. They are on the
  top side in the back strip ([pinout.md](pinout.md#part-positions)), under the case top.

## Display

- Sharp LS011B7DH03 memory LCD, 160 × 68, on a nice!view-compatible module: 3-wire SPI, 3.3 V,
  under 10 µA. It replaces the top key of the inner column on both halves.
- Plugged into J3, a 1×5 female socket 5.0 mm tall (C27985230), fitted by JLC as its only
  through-hole part. The pin order is MOSI, SCK, VCC, GND, CS: pin *n* is the module's pin *n*.
  Pin 1 is at high x in each half's frame, so the module lies LCD up with its header at the back
  on both halves (gate G1, BOARD-1). `netcmp.py --board` fails stages C and D if J3 is turned
  (ELEC-8). A stock nice!view plugs in on its own header, and its glass ends at most 9.75 mm above
  the PCB (CASE-1). The firmware lays both screens out portrait (WS1-7).
- Driven by **PIO1** as an SPI master (`raspberrypi,pico-spi-pio`): clock GP2, data GP3, chip
  select GP5, **active high**. The RP2040's PL022 hardware SPI cannot send LSB-first, which the
  memory LCD needs. The ZMK driver is `sharp,ls0xx` at 1 MHz with serial VCOM inversion.
- GP4, GP6 and GP7 go to test pads TP1–TP3 (DC, RST, BL) for a future TFT.
- Rev B moves the module, J3 and the case window 1.0 mm back (`layout/display.py` `SETBACK`): its far
  end is now about 0.2–0.3 mm short of the open C6R1 key well (0.4 mm for a bare 36.0 mm module, less its V-cut) instead of 0.6–0.8 mm into it, so the C6R1 keycap
  cannot reach it at bottom-out (pre-order review, deviations REVB-2).

## Per-key RGB (rev B)

One SK6812MINI-E under every switch, 37 per half, in one chain per half (deviations REVB-1).

- **Where:** the switches face south, so the MX LED window is 5.08 mm below the switch centre
  (`layout/leds.py`). The LED is a reverse-mount part on B.Cu: its body sits in a 3.4 × 3.0 mm
  cutout (dog-bone corners to 3.63 × 3.23) and its lens looks up into the switch. The footprint is
  KiCad's stock one with the pads moved 0.1 mm out, 0.35 mm from the cutout (`gen_footprints.py`);
  the `.kicad_dru` lets copper come within 0.3 mm of the LED cutouts, the outline keeps 0.5 mm. The
  matrix diode moved from 5.0 to 8.5 mm below the switch centre, under the LED.
- **Chain:** GP22 → U7 SN74LV1T34 (VCC on VLED; VIH 2.0 V at 5 V, so 3.3 V logic switches it cleanly,
  where the LED's own threshold of 0.65 × VDD ≈ 3.0 V would not) → R16 470 Ω → LED101 DIN → … →
  LED137 DOUT (open). The order is a serpentine: row 0 inward, row 1 outward, row 2 inward, C6R2,
  row 3 outward, row 4 inward, then the thumbs T5, T4, T3, T2, T0, T1 (`layout/leds.py` `CHAIN`), the
  same key ids on both halves. Each LED is turned so DIN → DOUT runs towards the next one.
- **Supply:** VLED is VSYS (about 4.6 V on USB, 4.4 V over the cable; the LEDs run from 3.7 V)
  through U6 SY6280AAC: active-high EN on GP23 with R15 pulling it low, so the LEDs stay dark (and
  draw nothing: 0.6 mA each when dark) until the firmware enables them (ZMK `ext-power`). R14 15k
  sets the current limit to 6800 / 15k = 0.45 A (±25 %), the part's 0.4 A minimum: it is a short
  and inrush guard, not the budget. U6 also keeps the 37 × 100 nF + 10 µF of VLED off VBUS when a
  cable is plugged in.
- **Budget:** one LED draws 12 mA per colour, 36 mA at full white. The binding limit is a right half
  fed over the cable: its 250 mA F1 hold, and the left USB port's 500 mA for both halves. The
  firmware caps brightness at 8 % (`CONFIG_ZMK_RGB_UNDERGLOW_BRT_MAX=8`): full white is about 107 mA
  per half (129 mA at the datasheet's 14.5 mA per colour) plus 22 mA for the dark LEDs and ~30 mA for the
  RP2040, flash and display, at most ~181 mA: about 72 % of F1's 250 mA hold (a PTC's hold falls when
  warm; both F1s carry it), and ~360 mA from the left port for both halves. The USB descriptor declares
  500 mA, bus powered. On a weak bus-powered hub (4.4 V) the cable-fed right half sees ~3.6–3.8 V at its
  LEDs, at their 3.7 V minimum: use a 5 V port or split-power mode. Raise it only with both halves on their own USB-C
  and JP1 cut on both (split-power mode); see [firmware.md](firmware.md).
- **Checks:** `netcmp.py` (the chain, U6/U7 wiring, VLED's members) and `checks.py` (each LED in its
  switch window with its cutout, turned along the chain, its 100 nF within 8 mm of VLED copper).

## Key matrix

- 6 rows × 7 columns, `col2row`: columns are driven, rows are read with internal pull-downs.
- One 1N4148W diode per key on the bottom side, 8.5 mm below the switch centre (under the LED,
  rev B): anode on the switch net (`MX_<key>`), cathode on the row.
- 37 keys per half. The unused slots are (R0, C6) for the display and (R2, C6), (R4, C5), (R4, C6),
  (R5, C0).
- Both PCBs share one matrix netlist. The right `.dts` reverses `col-gpios` (GP20…GP14) and sets
  `col-offset = <7>`, which mirrors the right half into global columns 7–13. Full tables:
  [matrix.md](matrix.md).

## Spare pins

| GPIO | Use |
|---|---|
| GP21 | TP11 `TRRS_DET` (future `detect-gpios`) |
| GP22 | per-key RGB data (rev B, U7) |
| GP23 | VLED enable (rev B, U6 EN) |
| GP24, GP25 | TP6, TP7, spare |
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
| 13–14 | `just pcb-fab <side>` | KiKit JLC files, the board part and J3 checks (`netcmp.py --board`), `cpl_check.py`, renders, Edge DXF, STEP (in `kicad/kicad:10.0.7-full`) |
| P | `just pcb-production <side>` | the JLC order package in `pcb/production/<side>/`: panel, Gerbers, BOM, CPL, README ([ordering-jlcpcb.md](ordering-jlcpcb.md)) |

The gate is `kicad-cli pcb drc --schematic-parity --severity-error`: both committed boards pass
with 0 violations, 0 unconnected items and 0 parity issues. The layout stages are seeded, so a
from-scratch rebuild reproduces the committed boards byte for byte; the `pcb` workflow's `rebuild`
job checks that (deviation WS2c-4). A full rebuild takes about 20 minutes per side.
