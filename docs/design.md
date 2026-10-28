# worxboard: Final Design Specification, rev A

| | |
|---|---|
| Status | **Frozen for implementation**: the work-streams in §14 build to this document |
| Repo | `/home/worxbend/Projects/Github/worxboard` → public `w0rxbend/worxboard` (HEAD `a1e3471`: concept sketch, GPL-3.0 `LICENSE`, `.gitignore`) |
| Reference | `/home/worxbend/Projects/Github/ergodox` @ v0.6.1 (`cad/ergodox_case.py`, `docs/`, `justfile`, `.github/workflows/build.yml`) |
| Firmware seed | `/tmp/claude-1000/-home-worxbend-Projects-Github-worxboard/95591c11-7956-4fac-9461-c2ab7c7ed528/scratchpad/zmktest/firmware/`. It compiled against ZMK `main` @ 4dd95d78 / Zephyr `v4.1.0+zmk-fixes`. |
| Coordinate frame | KiCad frame of the **right** half, in mm. +x points outward (pinky side), +y points toward the user, and positive rotation is CCW on screen. The left half uses **x_L = 260 − x_R, y_L = y_R, rot_L = −rot_R**. |

---

## 0. Proposal scoring

Each criterion is scored 1–5.

| Criterion | P1 buildability | P2 corne-v4-like | P3 automation |
|---|---|---|---|
| Feasibility for an agent with the tested toolchain | 3. A 4-layer board with plane layers was never tested with Freerouting. The PJ-320A THT jack has no stock footprint. | 4. Uses a 2-layer board, but the "90 Ω pair on 2-layer 1.6 mm" target cannot be met. | 3. Putting all SMT on B.Cu, USB-C included, forces the USB notch into the bottom tray and changes the Z-stack. Its fit was never checked. |
| Electrical correctness | 5. VSYS on Ring2 next to the sleeve, diode-OR, PTC, jumper, and one ESD part reused for USB and TRRS. | 3. **VLINK on the tip**: the tip wipes every spring during insertion, which is the worst hot-plug case. The 90 Ω claim is wrong. | 4. Correct pinout, but the inbound/outbound PTC path is muddled, and it uses 2× TPD4E05U06, which has no stock footprint. |
| ZMK compatibility | 5. Matches the compiled firmware exactly. | 5 | 5. Adds **reversed col-gpios on the right**, so both PCBs can share one matrix netlist. This is the best idea in the three proposals. |
| Fidelity to the sketch | 5 | 5 | 4. Moves the inner tent leg off the stock EZ position. |
| Repo quality | 4 | 4 | 5. Fixes `.gitignore /zephyr/`, respects the existing GPL licence, adds THIRD_PARTY, and uses a layout package with exporters and a pins contract. |
| **Total** | **22** | **21** | **21** |

**Decision.** The spec is built on **P1**, with these grafts:
- From **P3**: one matrix netlist on both PCBs with the right `.dts` reversing col-gpios, the `.gitignore` fix, the licence handling, `layout/pins.py` as a frozen contract, and `build.yaml` at the repo root.
- From **P2**: a **2-layer** board, JLC assembly on both sides, and an exact vertex comparison of the outline.
- Rejected: 4-layer (P1), Tip = VLINK (P2), all-SMT-on-bottom (P3), the 90 Ω target (P2), and moving the inner leg (P3).

**Verified for this spec.** These were checked inside `kicad/kicad:10.0.7`:
- The stock symbols exist: `MCU_RaspberryPi:RP2040`, `Power_Protection:USBLC6-2SC6`, `Regulator_Linear:AP2112K-3.3`, `Memory_Flash:W25Q128JVS` (its default footprint is `Package_SO:SOIC-8_5.3x5.3mm_P1.27mm`), `Connector_Audio:AudioJack4`, `Connector:USB_C_Receptacle_USB2.0_16P`, `Device:Polyfuse`, `Device:Crystal_GND24`, `Device:D_Schottky`, `Diode:1N4148W`, `Switch:SW_Push`, `Jumper:SolderJumper_2_Bridged` and `Connector_Generic:Conn_01x05`.
- The stock footprints exist: `Jack_3.5mm_PJ320D_Horizontal`, `USB_C_Receptacle_HRO_TYPE-C-31-M-12`, `SW_SPST_TS-1088-xR020`, `Crystal_SMD_3225-4Pin_3.2x2.5mm`, `QFN-56-1EP_7x7mm_P0.4mm_EP3.2x3.2mm`, `PinSocket_1x05_P2.54mm_Vertical`, `SolderJumper-2_P1.3mm_Bridged_RoundedPad1.0x1.5mm` and `TestPoint_Pad_D1.0mm`.
- **There is no stock MX hot-swap footprint.** It has to be vendored (§9).
- `B5819W` is not a stock symbol. Use `Device:D_Schottky` with value `B5819W`.

---

## 1. Requirements traceability

| # | User requirement (sketch / request) | Where it is met |
|---|---|---|
| R1 | Layout identical to the ErgoDox EZ: same stagger, 6-key thumb cluster at 25° | §5 key table (exact original-PCB centres) and `layout/keys.py` (WS0) |
| R2 | The top key of the inner column is replaced by a vertical display, on both halves, mirrored | §4 display: C6R0 deleted, module at x 65.39–79.39, y 38.625–74.625 (right frame) |
| R3 | "LCD" | Sharp LS011B7DH03 memory LCD (nice!view-compatible), §4 |
| R4 | USB-C on both halves at the top edge near the outer corner, each half powered and connectable | §6 USB-C at right-frame x 186.0 (left-frame x 74.0); every half has full D+/D− |
| R5 | TRRS mini-jack on the inner edge between the inner column and the thumb cluster, wired split | §6 PJ-320D at y 103.0 in a local inner-edge bump; ZMK `zmk,wired-split` |
| R6 | Thumb cluster kept; the case outline follows it | §8 outline keeps the original thumb vertices |
| R7 | Tent/tilt legs like the EZ | §10: reference leg design with three mounts per half, positions unchanged |
| R8 | RP2040 or newer | RP2040 on-board (rev A). RP2350A firmware target compiled and kept as experimental (§13). |
| R9 | ZMK compatible | §11 custom HWMv2 board, already compiled; CI via `build-user-config.yml` |
| R10 | Custom PCB (open source) and custom frame | §8–§9 KiCad 10 generated PCB; §10 build123d case |
| R11 | Repo structured like crkbd (Corne) v4 | §12: `pcb/`, `case/`, `plates/`, `docs/` with build guides, `firmware/`, production files on tags |
| R12 | Public repo; commit and push sequentially through the process | §14: stream-owned directories, Conventional Commits, push after each acceptance gate |
| R13 | Corne v4 as electrical reference | §2 support circuit cloned from the Corne v4.1 production BOM, with fixes |

---

## 2. Architecture

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

- **MCU:** RP2040 QFN-56 on the PCB, one per half, assembled by JLC PCBA.
- **Split link:** ZMK `zmk,wired-split`, full duplex on hardware UART0 (GP0 TX, GP1 RX) at 115200 baud, interrupt mode, which ZMK selects automatically. The **TX/RX crossover is done in the PCB netlist**, so firmware pinctrl is the same on both halves.
- **Host:** the **left half is the central** and is where the host plugs in. The right USB-C gives power and UF2 flashing. A right-central / left-peripheral firmware pair is shipped as an `EXPERIMENTAL` artifact.
- **PCB:** two boards (`worxboard-left`, `worxboard-right`), 2-layer, 1.6 mm, ENIG. Both are generated by one script from one layout source.
- **Case:** a port of the reference build123d CNC case. Its outline is derived from the PCB polygon.

---

## 3. GPIO map (`layout/pins.py`, owned by WS0, frozen; identical on both PCBs)

| GPIO | QFN pin | Net | Function / notes |
|---|---|---|---|
| GP0 | 2 | `UART_TX` | UART0 TX → 1 kΩ → `TRRS_A`/`TRRS_B` (see §6) |
| GP1 | 3 | `UART_RX` | UART0 RX ← 1 kΩ ← jack; 10 kΩ pull-up to 3V3 on the MCU side |
| GP2 | 4 | `DISP_SCK` | PIO1 SPI clock |
| GP3 | 5 | `DISP_MOSI` | PIO1 SPI data |
| GP4 | 6 | `DISP_DC` | Test pad TP1 (future TFT) |
| GP5 | 7 | `DISP_CS` | Display CS, **active high** |
| GP6 | 8 | `DISP_RST` | Test pad TP2 (future TFT) |
| GP7 | 9 | `DISP_BL` | Test pad TP3 (future TFT backlight) |
| GP8–GP13 | 11–16 | `ROW0`–`ROW5` | Matrix rows: inputs, internal pull-down |
| GP14–GP20 | 17, 18, 27–31 | `COL0`–`COL6` | Matrix columns: outputs. **COLn = physical column Cn (C0 outer, C6 inner) on both PCBs** |
| GP21 | 32 | `TRRS_DET` | Test pad (future `detect-gpios`) |
| GP22–GP25 | 34–37 | — | Test pads TP4–TP7 (spare; GP22 is reserved for future RGB) |
| GP26 / ADC0 | 38 | `VBUS_SENSE` | VBUS (before D1) → 10k/10k divider, about 2.5 V. Not used by rev-A firmware. |
| GP27–GP29 | 39–41 | — | Spare, no connection |
| QSPI_SS | 56 | `QSPI_SS` | Flash CS, 10k pull-up; BOOT button through 1 kΩ to GND |
| RUN | 26 | `RUN` | 10k pull-up; RESET button to GND |
| SWCLK / SWDIO | 24 / 25 | SWD | 3 test pads: GND, SWCLK, SWDIO |
| TESTEN | 19 | GND | |
| XIN / XOUT | 20 / 21 | crystal | 1 kΩ in series on XOUT |
| USB_DM / USB_DP | 46 / 47 | `USB_DM`/`USB_DP` | 27 Ω in series on each |

The QFN pin numbers are informational. The symbol pin **names** are the authority, and `netcheck.py` checks against them.

---

## 4. Display

- **Part:** a nice!view module or an equivalent LS011B7DH03 breakout: 160×68, 3-wire SPI, 3.3 V, under 10 µA. It is assumed to measure 36 × 14 × 2.9 mm, which is gate **G1**.
- **Connector:**
  - J3 is `Connector_PinSocket_2.54mm:PinSocket_1x05_P2.54mm_Vertical`, hand-soldered and marked DNP for JLC.
  - Pin order is 1 MOSI, 2 SCK, 3 VCC (3V3), 4 GND, 5 CS (G1).
  - TP1–TP3 carry DC, RST and BL for a future TFT.
- **Placement (right frame; mirror it for the left):**
  - The module sits vertically over **x 65.39–79.39, y 38.625–74.625**.
  - Its bottom edge lies on the old C6R0 cell boundary, so **no key moves**.
  - The header is at the top end, centred at (72.39, 40.6), with pins running along x.
  - Clearances: 4.25 mm to the C5R0 and C6R1 housings, 6.8 mm to the inner wall.
- **Mounting hole #7 moves** from (67.41, 37.13) to **(88.0, 37.135)**, the old TRRS spot.
- **Viewing window:** 26 × 12 mm centred at (72.39, 62.5), with 1 mm corner radius and a 0.5 mm chamfer.
- **Height:** the case pocket runs from Z 8.6 (PCB top) to Z 16.8. Socket plus module plus glass must therefore stay **≤ 8.2 mm** above the PCB top (G1).
- **Firmware:** PIO1 SPI (`raspberrypi,pico-spi-pio`), because the PL022 hardware SPI rejects LSB-first transfers. Driver `sharp,ls0xx` at 1 MHz with `serial-vcom-inversion`.
  - Left: ZMK built-in status screen (the layer widget works).
  - Right: custom LVGL screen (§11.6).
  - The stock `nice_view` shield is **not used**: it does not build on RP2040.

---

## 5. Key positions and matrix (37 keys per half, 74 total)

**Wiring.**
- 6 rows × 7 columns, `col2row`. Diode anode on the switch/COL side, cathode on the ROW net. Diodes are 1N4148W SOD-123 on B.Cu.
- The **net assignment is the same on both PCBs.**
- Global ZMK map is 6×14:
  - **Left:** RC(r, n), where n is the physical column (C0 = 0).
  - **Right:** RC(r, 13 − n). This comes from `col-offset = <7>` together with col-gpios reversed to GP20…GP14 in the right `.dts`.
- R0 C6 is the display on both halves and is not mapped.
- Legends follow the QMK `ergodox_ez` default layer 0. The two inner-top keys (LEFT / RGHT) move to layer 1.

| Key id | x_R | y_R | rot_R | size (w×h u) | Row | Col net | Left RC | Left legend | Right RC | Right legend |
|---|---|---|---|---|---|---|---|---|---|---|
| C0R0 | 191.4525 | 67.0052 | 0 | 1.5×1 | ROW0 | COL0 | (0,0) | `=` | (0,13) | `-` |
| C1R0 | 167.6400 | 67.0052 | 0 | 1×1 | ROW0 | COL1 | (0,1) | `1` | (0,12) | `0` |
| C2R0 | 148.5900 | 63.82766 | 0 | 1×1 | ROW0 | COL2 | (0,2) | `2` | (0,11) | `9` |
| C3R0 | 129.5400 | 62.23 | 0 | 1×1 | ROW0 | COL3 | (0,3) | `3` | (0,10) | `8` |
| C4R0 | 110.4900 | 63.82766 | 0 | 1×1 | ROW0 | COL4 | (0,4) | `4` | (0,9) | `7` |
| C5R0 | 91.4400 | 65.1002 | 0 | 1×1 | ROW0 | COL5 | (0,5) | `5` | (0,8) | `6` |
| ~~C6R0~~ | 72.39 | 65.1002 | — | — | — | — | — | **DISPLAY** | — | **DISPLAY** |
| C0R1 | 191.4525 | 86.0527 | 0 | 1.5×1 | ROW1 | COL0 | (1,0) | `DEL` | (1,13) | `\` |
| C1R1 | 167.6400 | 86.05266 | 0 | 1×1 | ROW1 | COL1 | (1,1) | `Q` | (1,12) | `P` |
| C2R1 | 148.5900 | 82.87766 | 0 | 1×1 | ROW1 | COL2 | (1,2) | `W` | (1,11) | `O` |
| C3R1 | 129.5400 | 81.28 | 0 | 1×1 | ROW1 | COL3 | (1,3) | `E` | (1,10) | `I` |
| C4R1 | 110.4900 | 82.87766 | 0 | 1×1 | ROW1 | COL4 | (1,4) | `R` | (1,9) | `U` |
| C5R1 | 91.4400 | 84.14766 | 0 | 1×1 | ROW1 | COL5 | (1,5) | `T` | (1,8) | `Y` |
| C6R1 | 72.3900 | 88.91016 | 0 | 1×1.5 | ROW1 | COL6 | (1,6) | `TG(1)` | (1,7) | `TG(1)` |
| C0R2 | 191.4525 | 105.1027 | 0 | 1.5×1 | ROW2 | COL0 | (2,0) | `BSPC` | (2,13) | `GUI_T(')` |
| C1R2 | 167.6400 | 105.10266 | 0 | 1×1 | ROW2 | COL1 | (2,1) | `A` | (2,12) | `LT(2,;)` |
| C2R2 | 148.5900 | 101.92766 | 0 | 1×1 | ROW2 | COL2 | (2,2) | `S` | (2,11) | `L` |
| C3R2 | 129.5400 | 100.33 | 0 | 1×1 | ROW2 | COL3 | (2,3) | `D` | (2,10) | `K` |
| C4R2 | 110.4900 | 101.92766 | 0 | 1×1 | ROW2 | COL4 | (2,4) | `F` | (2,9) | `J` |
| C5R2 | 91.4400 | 103.19766 | 0 | 1×1 | ROW2 | COL5 | (2,5) | `G` | (2,8) | `H` |
| C0R3 | 191.4525 | 124.1527 | 0 | 1.5×1 | ROW3 | COL0 | (3,0) | `LSFT` | (3,13) | `RSFT` |
| C1R3 | 167.6400 | 124.15266 | 0 | 1×1 | ROW3 | COL1 | (3,1) | `CTL_T(Z)` | (3,12) | `CTL_T(/)` |
| C2R3 | 148.5900 | 120.97766 | 0 | 1×1 | ROW3 | COL2 | (3,2) | `X` | (3,11) | `.` |
| C3R3 | 129.5400 | 119.38 | 0 | 1×1 | ROW3 | COL3 | (3,3) | `C` | (3,10) | `,` |
| C4R3 | 110.4900 | 120.97766 | 0 | 1×1 | ROW3 | COL4 | (3,4) | `V` | (3,9) | `M` |
| C5R3 | 91.4400 | 122.24766 | 0 | 1×1 | ROW3 | COL5 | (3,5) | `B` | (3,8) | `N` |
| C6R2 | 72.3900 | 117.48516 | 0 | 1×1.5 | ROW3 | COL6 | (3,6) | `HYPER` | (3,7) | `MEH` |
| C0R4 | 186.6900 | 143.2027 | 0 | 1×1 | ROW4 | COL0 | (4,0) | `LT(1,`)` | (4,13) | `TT(1)` |
| C1R4 | 167.6400 | 143.20266 | 0 | 1×1 | ROW4 | COL1 | (4,1) | `'` | (4,12) | `]` |
| C2R4 | 148.5900 | 140.02766 | 0 | 1×1 | ROW4 | COL2 | (4,2) | `LA(LSFT)` | (4,11) | `[` |
| C3R4 | 129.5400 | 138.43 | 0 | 1×1 | ROW4 | COL3 | (4,3) | `LEFT` | (4,10) | `DOWN` |
| C4R4 | 110.4900 | 140.02766 | 0 | 1×1 | ROW4 | COL4 | (4,4) | `RGHT` | (4,9) | `UP` |
| T0 (u0,v0) | 34.69894 | 143.2687 | 25 | 1×1 | ROW5 | COL6 | (5,6) | `LGUI` | (5,7) | `LALT` |
| T1 (u1,v0) | 51.9641 | 135.2178 | 25 | 1×1 | ROW5 | COL5 | (5,5) | `ALT_T(APP)` | (5,8) | `CTL_T(ESC)` |
| T2 (u0,v1) | 42.7498 | 160.5339 | 25 | 1×1 | ROW5 | COL4 | (5,4) | `HOME` | (5,9) | `PGUP` |
| T3 (u0,v2) | 50.8007 | 177.7990 | 25 | 1×1 | ROW5 | COL3 | (5,3) | `END` | (5,10) | `PGDN` |
| T4 (u1,v1.5) | 64.0404 | 161.1156 | 25 | 1×2 | ROW5 | COL2 | (5,2) | `BSPC` | (5,11) | `TAB` |
| T5 (u2,v1.5) | 81.3056 | 153.0647 | 25 | 1×2 | ROW5 | COL1 | (5,1) | `SPC` | (5,12) | `ENT` |

**Count.** Per row: 6 + 7 + 6 + 7 + 5 + 6 = **37**.

**Unused matrix slots.** (R0, C6) is the display. (R2, C6), (R4, C5), (R4, C6) and (R5, C0) are empty.

**Thumb formula.**
- `thumb_pt(u,v) = T0 + 19.05·(u·(cos25°, −sin25°) + v·(sin25°, cos25°))` in the right frame.
- `layout` asserts every thumb position matches the original PCB to within 0.002 mm.
- T4/T5 get MX 2u stabiliser NPTHs at ±11.938 mm along the key's long axis (Ø3.05 / Ø4.0) and plate stab cuts.

**Order rule.** The keymap order, transform order and physical-layout order are all the order of the compiled `worxboard.dtsi` map: 12 / 14 / 12 / 14 / 10, then the thumbs (5,5) (5,6) (5,7) (5,8) / (5,4) (5,9) / (5,1) (5,2) (5,3) (5,10) (5,11) (5,12).

---

## 6. Power, TRRS, USB-C, ESD

### 6.1 Power path (same on each half)

```
USB-C VBUS ──┬── U4 USBLC6-2SC6 VBUS pin (USB ESD)
             ├── R 10k ─┬─ GP26 (VBUS_SENSE) ── R 10k ── GND
             └── D1 B5819W (1 A Schottky, SOD-123) ──► VSYS (~4.6 V)
VSYS ── C 10 µF ── GND
VSYS ── U3 AP2112K-3.3 (EN tied to VIN) ──► 3V3 (RP2040, flash, display)   10 µF in, 10 µF + 1 µF out
VSYS ── JP1 SolderJumper_2_Bridged ── F1 Polyfuse 1206, 250 mA hold ──► VLINK ── TRRS Ring2
VLINK ── U5 USBLC6-2SC6 VBUS pin (TRRS ESD; IO1 = TRRS_A, IO2 = TRRS_B)
```

**Why this topology**
- **Two hosts at once:** each VBUS reaches VSYS only through its own D1. The cable joins the two VSYS nets *downstream* of both diodes, so no host is ever back-fed. Whichever VBUS is higher supplies both halves.
- **One cable:** the far half runs from VLINK at about 4.4 V. The AP2112K dropout is about 250 mV, which leaves margin. NCP1117 and AMS1117 are rejected because their roughly 1 V dropout leaves none.
- **JP1:** cutting it on both halves gives "split-powered mode". The cable then carries no power and each half needs its own USB-C.
- **F1:** limits current into VLINK to protect against plug-insertion shorts, and keeps the PJ-320 contacts under their roughly 300 mA rating.

### 6.2 TRRS pinout (straight 4-pole cable)

| Contact | Left PCB | Right PCB | Rationale |
|---|---|---|---|
| Tip | `TRRS_A` = **UART_TX** (GP0 via 1 kΩ) | `TRRS_A` = **UART_RX** (GP1 via 1 kΩ) | The tip wipes every spring during insertion. Only 1 kΩ-limited data lines are exposed. |
| Ring1 | `TRRS_B` = **UART_RX** | `TRRS_B` = **UART_TX** | Crossed in the netlist, so firmware stays identical |
| Ring2 | VLINK | VLINK | Sits next to the sleeve and can only touch the sleeve spring. That short is limited by F1. |
| Sleeve | GND | GND | |

- 1 kΩ series resistors sit at the jack on both data lines. U5 clamps the jack side.
- The RX line has a 10 kΩ pull-up to 3V3 on the MCU side, so it idles high when the cable is unplugged.
- **Jack:** PJ-320D-4A SMD (Hroparts, **C95562**, Extended), using the stock footprint `Connector_Audio:Jack_3.5mm_PJ320D_Horizontal`. It is SMD and assembled by JLC on F.Cu. Gate **G2** covers checking its height (≤ 5.5 mm) and the pad map against the datasheet.
- **Placement:** the jack body runs along x with its mouth at the PCB edge x 49.0 (right frame), centred at **y 103.0**, between the C6R1 housing (y ≤ 96.71) and the C6R2 housing (y ≥ 109.69).
- **Silkscreen** next to the jack on both halves: `DO NOT HOT-PLUG TRRS` and `HOST → LEFT`.

### 6.3 USB-C (both halves)

- **Part:** HRO TYPE-C-31-M-12, 16-pin (**C165948**, to be verified at G3), stock footprint `Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12`.
- **Position:** F.Cu, centred at right-frame **x 186.0** (left frame x 74.0). The mouth is flush with the PCB back edge at y 30.6.
- **Connections:**
  - CC1 and CC2 each have 5.1 kΩ to GND, so the board is a sink.
  - A6/B6 and A7/B7 are tied together, with 27 Ω in series on DP and DM.
  - SBU is not connected.
  - The shield is tied directly to GND.
- **ESD:** U4 USBLC6-2SC6 within 5 mm of the receptacle.
- **Routing:** full-speed (12 Mbps), so impedance is not controlled. Use 0.25 mm tracks with a 0.2 mm gap on F.Cu, total length ≤ 25 mm, matched within 1 mm. The B.Cu area under the pair is a **track keepout** so the GND pour stays solid there.

### 6.4 MCU support circuit (cloned from Corne v4.1)

- **Flash:** U2 W25Q128JVSIQ, decoupled with 100 nF. QSPI_SS has a 10k pull-up.
- **Crystal:** Y1 12 MHz 3225, 18 pF, with 2× 27 pF load caps and 1 kΩ in series on XOUT. Place it within 3 mm of XIN/XOUT, with a GND guard and no traces underneath.
- **Decoupling:**
  - 100 nF on every IOVDD pin (6), USB_VDD, ADC_AVDD and both DVDD pins.
  - 1 µF on VREG_IN and on VREG_VOUT; DVDD is tied to VREG_VOUT.
- **Buttons:** TS-1088R. SW_BOOT goes QSPI_SS → 1 kΩ → GND. SW_RST goes RUN → GND, with RUN pulled up by 10k.

---

## 7. Parts list (per half)

Status key: **[C]** verified from the Corne v4.1 JLC BOM, **[J]** verified on the JLC part page, **[G3]** must be verified before ordering.

| Ref | Qty | Part | LCSC | Symbol | Footprint | Status | Side / assembly |
|---|---|---|---|---|---|---|---|
| U1 | 1 | RP2040 | C2040 | MCU_RaspberryPi:RP2040 | Package_DFN_QFN:QFN-56-1EP_7x7mm_P0.4mm_EP3.2x3.2mm | [C] | F / JLC |
| U2 | 1 | W25Q128JVSIQ | C113767 | Memory_Flash:W25Q128JVS | Package_SO:SOIC-8_5.3x5.3mm_P1.27mm | [C] | F / JLC |
| Y1 | 1 | 12 MHz 18 pF 3225 | C91749 | Device:Crystal_GND24 | Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm | [C] | F / JLC |
| U3 | 1 | AP2112K-3.3TRG1 | C51118 | Regulator_Linear:AP2112K-3.3 | Package_TO_SOT_SMD:SOT-23-5 | [G3] | F / JLC |
| U4, U5 | 2 | USBLC6-2SC6 | C7519 | Power_Protection:USBLC6-2SC6 | Package_TO_SOT_SMD:SOT-23-6 | [J] | F / JLC |
| D1 | 1 | B5819W | C8598 | Device:D_Schottky | Diode_SMD:D_SOD-123 | [G3] | F / JLC |
| F1 | 1 | PTC 1206, 250 mA hold, ≥ 6 V | chosen by WS2 from JLC parts, recorded in the BOM | Device:Polyfuse | Fuse:Fuse_1206_3216Metric | [G3] | F / JLC |
| J1 | 1 | TYPE-C-31-M-12 | C165948 | Connector:USB_C_Receptacle_USB2.0_16P | Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12 | [G3] | F / JLC |
| J2 | 1 | PJ-320D-4A | C95562 | Connector_Audio:AudioJack4 | Connector_Audio:Jack_3.5mm_PJ320D_Horizontal | [J] | F / JLC |
| J3 | 1 | 1×5 2.54 female socket, low profile | — (builder) | Connector_Generic:Conn_01x05 | Connector_PinSocket_2.54mm:PinSocket_1x05_P2.54mm_Vertical | G1 | F / hand, DNP |
| SW_BOOT, SW_RST | 2 | TS-1088R-02026 | C455280 | Switch:SW_Push | Button_Switch_SMD:SW_SPST_TS-1088-xR020 | [C] | F / JLC |
| R (CC) | 2 | 5.1 kΩ 0402 | C25905 | Device:R | Resistor_SMD:R_0402_1005Metric | [C] | F / JLC |
| R (USB) | 2 | 27 Ω 0402 | C2909343 | Device:R | R_0402 | [C] | F / JLC |
| R (XOUT, BOOT, UART×2) | 4 | 1 kΩ 0402 | C11702 | Device:R | R_0402 | [C] | F / JLC |
| R (QSPI_SS, RUN, RX pull-up, VBUS divider ×2) | 5 | 10 kΩ 0402 | C25744 | Device:R | R_0402 | [C] | F / JLC |
| C (decoupling) | 11 | 100 nF 0402 | C1525 | Device:C | Capacitor_SMD:C_0402_1005Metric | [C] | F / JLC |
| C | 3 | 1 µF 0402 | C52923 | Device:C | C_0402 | [C] | F / JLC |
| C | 3 | 10 µF 0402 | C15525 | Device:C | C_0402 | [C] | F / JLC |
| C (load) | 2 | 27 pF 0402 | C1557 | Device:C | C_0402 | [C] | F / JLC |
| D_xx | 37 | 1N4148W | C81598 | Diode:1N4148W | Diode_SMD:D_SOD-123 | [G3] | **B / JLC** |
| SK_xx | 37 | Kailh MX hot-swap CPG151101S11 | C2803348 | worxboard:SW_Push_MX | worxboard:SW_MX_Hotswap_Kailh | [G3] | **B / JLC** |
| JP1 | 1 | solder jumper, bridged | — | Jumper:SolderJumper_2_Bridged | Jumper:SolderJumper-2_P1.3mm_Bridged_RoundedPad1.0x1.5mm | — | excluded from BOM/POS |
| TP1–TP7, SWD×3 | 10 | test pads | — | Connector:TestPoint | TestPoint:TestPoint_Pad_D1.0mm | — | excluded from BOM/POS |
| H1–H8 | 8 | M2.5 NPTH Ø2.7 | — | Mechanical:MountingHole | MountingHole:MountingHole_2.7mm_M2.5 | — | excluded from BOM/POS |
| Display | 1 | nice!view (LS011B7DH03 module) | — | — | — | G1 | builder |

**Builder parts** (in `docs/bom.md`):
- 37 MX switches per half (74 total)
- 2× 2u plate-mount stabilisers per half
- 1 TRRS 4-pole straight cable
- 2 USB-C cables
- M2.5 screws per the reference case
- stock EZ leg thumbscrews

**Fees.** Extended-part fees apply to C2040, C113767, C91749, C7519, C95562, C165948, C2803348, C455280 and the PTC. `docs/ordering-jlcpcb.md` lists them.

**Gates (WS5 records the results in `docs/verification.md`):**
- **G1:** nice!view dimensions, pin order and header stack ≤ 8.2 mm.
- **G2:** PJ-320D height and the footprint pad map.
- **G3:** every [G3] LCSC number and its stock, and the JLC 2-layer minimum track (0.127 mm).

These gates block **ordering**, not the repo.

---

## 8. PCB physical design

### 8.1 Outline (`layout/outline.py`, owned by WS0)

The outline is derived from the original ErgoDox Edge.Cuts. The jack tabs are removed, the back edge is straightened, the inner edge is moved to the case clearance line, and the TRRS bump is added. Right frame, in order:

```
(62.275, 30.6) → (202.7428, 30.6) → (205.9178, 33.775) → (205.9178, 143.383) → (196.3928, 152.908)
→ (127.1524, 152.908) → (48.9839, 189.35192) → (44.76496, 187.81776) → (23.08098, 141.31544)
→ (24.61768, 137.0965) → (49.0, 125.7267)            # original 25° thumb top edge, extended to the bump
→ (49.0, 88.0) [fillet r4] → (59.1, 88.0) [fillet r4] → (59.1, 33.775) → back to (62.275, 30.6)
```

- Every key cell stays inside it. The outermost C0 cell edge is 205.74 < 205.918.
- The left outline is the mirror image: x → 260 − x, with the vertex order reversed.
- The overall size shrinks about 1–2 mm compared with the photo-measured EZ case. That is accepted: the derived outline supersedes the photo constants.

### 8.2 Mounting holes

There are 8 M2.5 NPTH holes, Ø2.7. Each has a copper and component keepout of Ø6.5.

| # | x_R | y_R |
|---|---|---|
| 0 | 53.899 | 165.837 |
| 1 | 59.665 | 121.666 |
| 2 | 105.435 | 157.759 |
| 3 | 201.778 | 140.056 |
| 4 | 139.040 | 91.592 |
| 5 | 201.143 | 37.135 |
| 6 | 118.212 | 37.135 |
| **7** | **88.000** | **37.135** (moved) |

### 8.3 Component zones (computed by `layout`; top-side parts must lie inside them)

- **Z_BACK:** the PCB ∩ y < 57.0, minus (key cells buffered 0.6 mm), minus hole keepouts. It contains:
  - USB-C at x 186.0
  - MCU cluster: U1 at (166, 44), U2 at (152, 42), Y1 within 3 mm of U1, U3/D1/F1/U4 between J1 and U1
  - SW_BOOT at (176, 50), SW_RST at (180, 50)
  - J3 header end at (72.39, 40.6)
- **Z_TRRS:** the PCB ∩ x < 62.2 ∩ y 88–125.7, minus cells buffered 0.6 mm. It contains J2 (x 49.0–61.0, y 100–106), U5, and the two 1 kΩ resistors.
- **Everything else on top** is under the plate spacer, 0.5 mm above the PCB. No top-side parts there, only the switch holes.
- **Bottom (B.Cu):** the 37 sockets and 37 diodes. The 4 mm cavity under the PCB leaves about 2.2 mm of margin.

### 8.4 Rules and board

- **Board:** 2 layers, 1.6 mm FR4, 1 oz copper, ENIG.
- **Netclasses:**

  | Netclass | Track | Clearance | Notes |
  |---|---|---|---|
  | Default | 0.25 | 0.2 | |
  | Power (VBUS, VSYS, VLINK, 3V3, GND) | 0.5 | 0.2 | |
  | USB | 0.25 | 0.2 | |
  | Board minimum | 0.127 | 0.127 | |
  | QFN fan-out | 0.15 | — | scripted |

- **Vias:** 0.3 mm drill / 0.6 mm pad. Board-edge clearance 0.5 mm.
- **GND:** pours on F.Cu and B.Cu.
  - Stitching vias are placed by `place.py` on a 5 mm grid inside Z_BACK around U1/Y1/J1, and on a 10 mm grid elsewhere in clear areas, before autorouting.
  - This is the mitigation for the Corne v4 EMI issue (#265).
- **Silkscreen:** `worxboard L|R rev A`, `DO NOT HOT-PLUG TRRS`, `HOST → LEFT`, a JP1 label, and diode cathode bars.

---

## 9. PCB pipeline (headless, Docker, versions verified)

### 9.1 Pinned tools

| Tool | Pin |
|---|---|
| KiCad | `kicad/kicad:10.0.7` (WS2 records the digest in `tools/images.lock`). `kicad/kicad:10.0.7-full` is used only for STEP export with 3D models. |
| Java | `eclipse-temurin:25-jre` |
| Freerouting | `freerouting-2.5.0.jar`, sha256 `f6f51bb02245e8e717f9359bd260cc9c5c0b1bc0acc8b7cb2cd5b8ffeb5de3c7`. Fetched by `tools/fetch_freerouting.sh` (`gh release download v2.5.0 -R freerouting/freerouting -p freerouting-2.5.0.jar -D pcb/.tools/`, then the sha check). |
| Python deps for the container (Python 3.13) | `uv pip install --python-version 3.13 --target pcb/.tools/site313 kikit==1.8.1 kicad-sch-api==0.5.6 shapely==2.2.0` |

- Every run uses `--network none -u $(id -u):$(id -g) -e HOME=/tmp -v $PWD:/w -w /w -e PYTHONPATH=/w:/w/pcb/.tools/site313`.
- `tools/kicad_env.sh` runs first in every KiCad container. It copies `/usr/share/kicad/template/*-lib-table` to `$HOME/.config/kicad/10.0/` and adds `worxboard` entries pointing at `${KIPRJMOD}/../lib`.

### 9.2 Stages (`pcb/scripts/`; `just pcb <side>` runs all three containers)

**Container A** (`kicad/kicad:10.0.7`, `bash pcb/scripts/stage_a.sh <side>`)

1. `gen_footprints.py` writes `pcb/lib/worxboard.pretty/`. It is idempotent.
   - `SW_MX_Hotswap_Kailh`:
     - MX centre NPTH Ø4.0, pegs NPTH Ø1.75 at (±5.08, 0)
     - socket NPTH Ø3.0 at (−3.81, −2.54) and (2.54, −5.08)
     - B.Cu SMD pads 2.55 × 2.5 at (−7.085, −2.54) and (5.842, −5.08)
     - check against the CPG151101S11 datasheet and the ceoloide `switch_mx` footprint (MIT)
   - `Stab_MX_2u`: NPTHs Ø3.05 / Ø4.0 at ±11.938.
   - `pcb/lib/worxboard.kicad_sym` holds `SW_Push_MX`.
2. `design.py <side>` holds the parts and nets as Python data, taken from `layout/pins.py` and `layout` keys. Its `side` argument applies **only** the TRRS_A/B ↔ TX/RX swap.
3. `gen_sch.py <side>` uses kicad-sch-api 0.5.6.
   - **Every symbol at rotation 0.** Every pin gets a short wire stub and a local/global label. No pin-to-pin wires.
   - Output is one **flat A1 sheet per side**, `pcb/<side>/worxboard-<side>.kicad_sch`, with grouped regions MCU / USB-POWER / TRRS / DISPLAY / MATRIX.
   - Each symbol carries an `LCSC` property.
4. ERC gate: `kicad-cli sch erc --format json --severity-error --exit-code-violations -o build/<side>/erc.json pcb/<side>/worxboard-<side>.kicad_sch`
5. Netlist: `kicad-cli sch export netlist --format kicadsexpr -o build/<side>/<side>.net pcb/<side>/worxboard-<side>.kicad_sch`
6. `netcmp.py build/<side>/<side>.net <side>` parses the netlist as s-expressions (KiCad 10 format "E") and checks it against `design.py`. It asserts:
   - each of the 37 diodes has its anode on the switch/COL side and its cathode on a ROW net
   - the (row, col) of every key matches §5
   - every GPIO net matches `layout/pins.py`
   - Tip/Ring1 map to TX/RX on the left and RX/TX on the right
   - CC1/CC2 each have 5.1k to GND
   - every RP2040 supply pin has a capacitor on its net
   - every BOM part has a non-empty LCSC field
   - the matrix nets of left and right are identical
7. `place.py <side>` uses pcbnew.
   - It loads footprints and sets `SetReference`, `SetFPID` and `SetPath(KIID_PATH)`, which is what makes schematic parity pass.
   - It places parts from `layout/build/layout.json`: left = mirrored coordinates, rot_L = −rot_R, B-side parts flipped.
   - It draws Edge.Cuts from the outline, and adds the holes, netclasses, GND zones on F and B, the USB keepout, stitching vias and silkscreen.
   - It asserts every top-side footprint courtyard lies within Z_BACK ∪ Z_TRRS.
8. `route_critical.py <side>` lays locked `PCB_TRACK`s: the QFN fan-out to vias (0.15 mm), the USB pair, crystal, QSPI, decoupling stubs, power trunks and the TRRS lines.
9. `export_dsn.py` → `build/<side>/<side>.dsn`

**Container B** (Java)

```
docker run --rm --network none --read-only --tmpfs /tmp -e HOME=/tmp -u $(id -u):$(id -g) \
  -v $PWD/pcb/.tools:/fr:ro -v $PWD/build/<side>:/w -w /w eclipse-temurin:25-jre \
  java -Djava.awt.headless=true -jar /fr/freerouting-2.5.0.jar -de <side>.dsn -do <side>.ses -mp 30 --gui.enabled=false
```

**Container C** (`kicad/kicad:10.0.7`, `bash pcb/scripts/stage_c.sh <side>`)

10. `import_ses.py`: `pcbnew.ImportSpecctraSES`, then `ZONE_FILLER(board).Fill(board.Zones())`, then save.
11. DRC gate: `kicad-cli pcb drc --schematic-parity --severity-error --exit-code-violations --format json -o build/<side>/drc.json pcb/<side>/worxboard-<side>.kicad_pcb`
12. `checks.py` runs the scripted checks:
    - USB pair length ≤ 25 mm and mismatch ≤ 1 mm
    - Y1 within 3 mm of the XIN/XOUT pins
    - the Edge.Cuts vertices equal `layout` within 0.01 mm
    - 0 unconnected items, read from `drc.json`
13. Fab outputs: `python3 -m kikit.ui fab jlcpcb --assembly --missingError --no-drc --schematic pcb/<side>/worxboard-<side>.kicad_sch --field LCSC pcb/<side>/worxboard-<side>.kicad_pcb build/<side>/jlc`. This writes `gerbers.zip`, `bom.csv` and `pos.csv`. JP1, test pads, holes and J3 are excluded with `--ignore`.
14. Renders and exports:
    - `kicad-cli pcb render --side top --width 1600 --height 1000 --quality basic -o docs/images/pcb-<side>-top.png …` (and the same for `--side bottom`)
    - `kicad-cli pcb export dxf --layers Edge.Cuts -o build/<side>/edge.dxf …`
    - STEP, in the `-full` image: `kicad-cli pcb export step --subst-models -f -o build/<side>/worxboard-<side>.step …`

**Committed vs generated**
- Committed: `pcb/lib/**`, `pcb/<side>/*.kicad_{pro,sch,pcb}`, `fp-lib-table`, `sym-lib-table` (using `${KIPRJMOD}/../lib`), and the renders in `docs/images/`.
- On `v*-revA` hardware tags only: `pcb/production/<side>/{gerbers.zip,bom.csv,pos.csv}`, crkbd style. Otherwise they are CI artifacts.

**Fallbacks (decided):**
- If Freerouting leaves nets unrouted: re-run with `-mp 60`, then report the remaining nets. A board with unrouted items fails acceptance.
- If kicad-cli 10.0.7 regresses: use `kicad/kicad:9.0.9` with `~/.config/kicad/9.0` and the Python 3.11 site dir.

---

## 10. Case (`case/worxboard_case.py`, port of `ergodox_case.py`)

Pins: build123d 0.13.0, shapely 2.2.0, ezdxf 1.4.5, Python 3.12. All geometry is imported from `layout`.

**Kept unchanged**
- Z stack:

  | Z (mm) | Layer |
  |---|---|
  | 0–3 | floor |
  | 3–7 | cavity |
  | 7–8.6 | PCB |
  | 9.1–12.1 | spacer |
  | 12.1–13.6 | plate |
  | 13.6–17.6 | key well |
  | 14.6 | pocket ceiling |

- Wall 3.0, top fillet 1.5, seam chamfer 0.5, well clearance 0.6.
- `well_face`, `switch_cut`, `stab_cuts`.
- M2.5 bosses and webs, rubber feet, CNC `corner_r` and `RELIEF_MIN_W`.
- Legs: `build_leg`, `build_leg_cap`, M3 mounts at Z 12.0, the stock thumbscrew, `DETENT_TEETH=False`, with the three stock positions: outer (210.6, 64), inner (55.6, 64), thumb end.
- The fit-check DXF, renders and drawings.

**Changes**
1. **Outline:** case outer = PCB polygon offset by 3.5 mm (0.5 clearance + 3.0 wall), mitre join. The reference radii are then applied by vertex class: convex back 10, front-outer 12, thumb 8, concave 6 / 14, and r6 at the TRRS bump corners. All photo `CASE_*` constants are deleted.
2. **KEYS** has 37 entries (`assert len(KEYS) == 37`). **SCREWS** come from `layout` with #7 moved.
3. **Removed:** `CAPS`, `cap_pocket`, `cap_check`, `LEDS`, the EZ `RESET`, and the back-wall `TRRS`/`USB` tuples.
4. **Display:**
   - pocket at the module rectangle + 0.5 mm (x 64.89–79.89, y 38.125–75.125), from Z 8.6 to Z 16.8, cutting the spacer and plate
   - 26 × 12 window through the top, centred at (72.39, 62.5), r1, 0.5 mm chamfer
   - the display rectangle is a keepout in `_in_housing`, `spacer_face`, `boss_webs` and `leg_pad_depth`
   - the inner leg pad is clamped to **5.0 mm** depth (x ≤ 63.6), giving ≥ 1.2 mm clearance to the pocket
   - new `display_check()` asserts the window is inside the pocket
5. **USB-C on both halves:**
   - back-wall notch 9.4 × 3.6 mm, r1.6, at x 186.0 (right frame), Z centre = 8.6 + 1.6 = 10.2
   - outside recess 13 × 8 mm, 1.8 mm deep, so the wall is 1.2 mm locally
   - the `[USB] if right` rule is removed
6. **TRRS:**
   - new `side_notch(face, y, z, d)`: a Ø6.5 hole through the inner bump wall at y 103.0, Z = PCB top + the jack axis height from the G2 datasheet (default 2.5 mm)
   - the bump bezel pocket over Z_TRRS has a ceiling of 14.6 (6.0 mm headroom), raised locally if G2 gives a jack taller than 5.5 mm
   - new `jack_check()`: the notch axis is within ±0.2 mm of `layout` J2
7. **Back-strip relief** over all of Z_BACK, ceiling 14.6. **Ø3 pin-holes** through the top skin over SW_BOOT (176, 50) and SW_RST (180, 50).
8. **Halves:** `build_top(side)` / `build_bottom(side)` are built explicitly from the mirrored layout data, with an engraved `L` / `R` on the bottom. The geometry stays mirror-equal and an assertion checks this.
9. **Plates:** `plates/worxboard-plate-{left,right}.dxf` (1.5 mm FR4 or aluminium) is exported from the plate face.
10. **Fit check:** `case/check_fit.py` loads `build/<side>/worxboard-<side>.step` when it exists and asserts 0 mm³ interference with the top and bottom. Until WS2 lands it falls back to the `layout` component zones and prints a warning.
11. `drawings.py` and `overlay.py` (from the reference `cad/` and `tools/`) move into `case/` and are ported in the same commit.

---

## 11. ZMK firmware

### 11.1 File list

```
zephyr/module.yml                         # repo ROOT (required by build-user-config.yml)
build.yaml                                # repo ROOT
firmware/zmk/CMakeLists.txt  firmware/zmk/Kconfig
firmware/zmk/src/worx_status_screen.c     # custom right-half LVGL screen
firmware/zmk/scripts/gen_layouts.py       # port of gen_layout.py; imports `layout`, writes worxboard-layouts.dtsi
firmware/zmk/config/west.yml  firmware/zmk/config/worxboard.conf  firmware/zmk/config/worxboard.keymap
firmware/zmk/boards/worxbend/worxboard/   # RP2040 (seed files, compiled)
  board.yml board.cmake Kconfig.worxboard_left Kconfig.worxboard_right Kconfig.defconfig
  worxboard.dtsi worxboard-pinctrl.dtsi worxboard-layouts.dtsi(GENERATED)
  worxboard_left_rp2040_zmk.dts worxboard_right_rp2040_zmk.dts
  worxboard_left_rp2040_zmk_defconfig worxboard_right_rp2040_zmk_defconfig
  worxboard.keymap (MUST match the folder name) worxboard.zmk.yml worxboard.conf
firmware/zmk/boards/worxbend/worxboard2/  # RP2350A, EXPERIMENTAL, firmware only (seed files, compiled)
firmware/firmware.just
.github/workflows/firmware.yml
```

### 11.2 Key snippets

`zephyr/module.yml`:
```yaml
name: zmk-keyboard-worxboard
build:
  cmake: firmware/zmk
  kconfig: firmware/zmk/Kconfig
  settings:
    board_root: firmware/zmk
```

`firmware/zmk/config/west.yml`. WS1 resolves the full SHA with `gh api repos/zmkfirmware/zmk/commits/4dd95d78 --jq .sha`.
```yaml
manifest:
  remotes: [{ name: zmkfirmware, url-base: https://github.com/zmkfirmware }]
  projects: [{ name: zmk, remote: zmkfirmware, revision: <full sha of 4dd95d78>, import: app/west.yml }]
  self: { path: firmware/zmk/config }
```

`worxboard.dtsi` (seed, already compiled):
- `kscan0`: `zmk,kscan-gpio-matrix`, `col2row`, rows GP8–13 `(GPIO_ACTIVE_HIGH | GPIO_PULL_DOWN)`, cols GP14–20
- the 6×14 transform from §5
- `&uart0` on `UART0_TX_P0` / `UART0_RX_P1` at 115200, plus `wired_split { compatible = "zmk,wired-split"; device = <&uart0>; };`
- `&pio1` `nice_view_spi` (`raspberrypi,pico-spi-pio`, clk GP2, mosi GP3, cs GP5 active-high), with `ls0xx@0` (`sharp,ls0xx`, 160×68, `serial-vcom-inversion`, `serial-vcom-interval = <33>`)
- `zephyr_udc0: &usbd`, `&timer`, `&rtc`, `&vreg`
- boot-mode retention
- flash: code `0x100..0x380000`, `storage_partition` 512 KB at `0x380000`

`worxboard_right_rp2040_zmk.dts` adds the delta that lets both PCBs share one netlist:
```dts
#include "worxboard.dtsi"
/ { model = "worxboard right"; compatible = "worxbend,worxboard-right"; };
&kscan0 {
    col-gpios = <&gpio0 20 GPIO_ACTIVE_HIGH>, <&gpio0 19 GPIO_ACTIVE_HIGH>, <&gpio0 18 GPIO_ACTIVE_HIGH>,
                <&gpio0 17 GPIO_ACTIVE_HIGH>, <&gpio0 16 GPIO_ACTIVE_HIGH>, <&gpio0 15 GPIO_ACTIVE_HIGH>,
                <&gpio0 14 GPIO_ACTIVE_HIGH>;   /* COL6(inner)..COL0(outer) -> logical 0..6 -> global 7..13 */
};
&default_transform { col-offset = <7>; };
```

`Kconfig.defconfig`, additions to the seed:
```kconfig
if BOARD_WORXBOARD_RIGHT
choice ZMK_DISPLAY_STATUS_SCREEN
    default ZMK_DISPLAY_STATUS_SCREEN_CUSTOM
endchoice
config ZMK_SPLIT_PERIPHERAL_HID_INDICATORS
    default y
endif
```
The seed already has the rest: `ZMK_SPLIT` default y, `ZMK_SPLIT_ROLE_CENTRAL` default y on the left only, `RP2_FLASH_W25Q080` default y, and the LVGL/ls0xx defaults under `if ZMK_DISPLAY` (`LV_Z_BITS_PER_PIXEL 1`, `LV_COLOR_DEPTH_1`, `LV_DPI_DEF 161`, `LV_Z_VDB_SIZE 100`, `LS0XX_VCOM_THREAD_PRIO 11`, `ZMK_DISPLAY_WORK_QUEUE_DEDICATED`, `ZMK_DISPLAY_BLANK_ON_IDLE n`).

Other board settings:
- `CONFIG_ZMK_USB` is removed from `worxboard_right_rp2040_zmk_defconfig`.
- `worxboard.conf`: `CONFIG_ZMK_DISPLAY=y`.

`build.yaml` (repo root):
```yaml
include:
  - { board: worxboard_left//zmk,  snippet: studio-rpc-usb-uart, cmake-args: -DCONFIG_ZMK_STUDIO=y, artifact-name: worxboard_left_central }
  - { board: worxboard_right//zmk, artifact-name: worxboard_right_peripheral }
  - { board: worxboard_right//zmk, snippet: studio-rpc-usb-uart, cmake-args: -DCONFIG_ZMK_SPLIT_ROLE_CENTRAL=y -DCONFIG_ZMK_USB=y -DCONFIG_ZMK_STUDIO=y, artifact-name: worxboard_right_central_EXPERIMENTAL }
  - { board: worxboard_left//zmk,  cmake-args: -DCONFIG_ZMK_SPLIT_ROLE_CENTRAL=n, artifact-name: worxboard_left_peripheral_EXPERIMENTAL }
  - { board: worxboard2_left/rp2350a/m33/zmk,  snippet: studio-rpc-usb-uart, cmake-args: -DCONFIG_ZMK_STUDIO=y, artifact-name: worxboard2_left_EXPERIMENTAL }
  - { board: worxboard2_right/rp2350a/m33/zmk, artifact-name: worxboard2_right_EXPERIMENTAL }
```
**Rule:** a row stays in `build.yaml` only if `just fw` compiles it locally. A row that fails is removed and recorded in `docs/firmware.md` as future work.

`.github/workflows/firmware.yml`:
```yaml
on: [push, pull_request, workflow_dispatch]
jobs:
  build:
    uses: zmkfirmware/zmk/.github/workflows/build-user-config.yml@<same full sha as west.yml>
    with: { config_path: firmware/zmk/config, build_matrix_path: build.yaml, archive_name: worxboard-firmware }
```

Local build (`firmware/firmware.just` → `just fw`; this is the dossier recipe, run once per `build.yaml` row):
```sh
docker run --rm -u $(id -u):$(id -g) -e HOME=/tmp -v $PWD:/work -w /work/build/fw-ws zmkfirmware/zmk-build-arm:stable sh -c '
  west init -l /work/firmware/zmk/config && west update --fetch-opt=--filter=tree:0 && west zephyr-export &&
  west build -p -s zmk/app -d /work/build/fw/left -b worxboard_left//zmk -S studio-rpc-usb-uart -- \
    -DZMK_CONFIG=/work/firmware/zmk/config -DZMK_EXTRA_MODULES=/work -DCONFIG_ZMK_STUDIO=y'
```

### 11.3 Keymap

Three layers, 74 bindings each:
- **0 base:** §5 legends.
- **1 symbols / F-keys:** EZ layer 1, plus LEFT/RGHT on the old inner-top functions.
- **2 media / mouse:** includes `&bootloader`, `&sys_reset` and `&studio_unlock`.

### 11.4 Physical layout

`gen_layouts.py` reads `layout/build/layout.json`:
- 100 units = 19.05 mm
- thumbs rotate about their own key centres: left `2500`, right `(-2500)`
- the right half is placed to the right of the left half
- keys are emitted in transform order

CI regenerates the file and fails on `git diff --exit-code`.

### 11.5 Host behaviour (documented)

- Only the central (left) enumerates as a keyboard.
- The right USB-C gives power and UF2 flashing: double-tap RESET, or hold BOOT and tap RESET, to get the `RPI-RP2` drive.
- `*_EXPERIMENTAL` role-swap artifacts let either half be the host. They are untested on hardware.

### 11.6 Custom right screen

`worx_status_screen.c` implements `zmk_display_status_screen()` and shows:
- a `worxboard` logo label
- a Caps / Num / Scroll lock row, from `zmk_hid_indicators_changed` events
- a static `wired` label

It must not reference any `zmk_ble_*` or battery symbols. It is compiled only when `CONFIG_ZMK_DISPLAY_STATUS_SCREEN_CUSTOM` is set.

---

## 12. Repo layout

```
worxboard/
├── README.md  CHANGELOG.md  THIRD_PARTY.md  .editorconfig  .gitattributes  .gitignore  .python-version(3.12)
├── LICENSE                 # existing GPL-3.0: code (layout/, pcb/scripts/, case/*.py, firmware/, tools/, site/)
├── LICENSE-HARDWARE        # CERN-OHL-S-2.0: pcb/ (KiCad files, lib), case/ geometry outputs, plates/, docs/ (flagged in README for maintainer confirmation)
├── justfile                # imports */*.just; recipes: setup, all
├── pyproject.toml uv.lock  # groups: layout(shapely), case(build123d==0.13.0, shapely==2.2.0, ezdxf==1.4.5), dev(pytest)
├── layout/                 # SINGLE SOURCE OF TRUTH
│   ├── __init__.py keys.py thumbs.py display.py jacks.py holes.py outline.py zones.py pins.py export.py
│   ├── layout.just  tests/  build/layout.json (committed)
├── tools/                  # kicad_env.sh fetch_freerouting.sh images.lock
├── pcb/
│   ├── lib/{worxboard.kicad_sym, worxboard.pretty/}
│   ├── scripts/{gen_footprints,design,gen_sch,netcmp,place,route_critical,export_dsn,import_ses,checks}.py stage_a.sh stage_c.sh
│   ├── left/worxboard-left.{kicad_pro,kicad_sch,kicad_pcb} fp-lib-table sym-lib-table
│   ├── right/worxboard-right.{…}
│   ├── production/{left,right}/   # hardware tags only
│   └── pcb.just
├── case/                   # worxboard_case.py drawings.py overlay.py check_fit.py case.just  exports/(ignored) renders/
├── plates/                 # worxboard-plate-{left,right}.dxf
├── firmware/               # zmk/… (§11) firmware.just
├── zephyr/module.yml
├── build.yaml
├── docs/                   # buildguide_en.md bom.md firmware.md design.md(=this spec) electrical.md pinout.md matrix.md
│                           #   case.md legs.md ordering-jlcpcb.md verification.md sources.md images/
├── site/                   # build_site.py site.just
├── tests/integration/      # test_pins.py (DT pins vs netlist), test_release.py
└── .github/workflows/      # layout.yml firmware.yml pcb.yml case.yml pages.yml release.yml
```

**`.gitignore` changes (WS0):**
- **Remove `/zephyr/`.**
- Keep `/zmk/`, `/modules/`, `/.west/`.
- Add `/build/`, `pcb/.tools/`, `case/exports/`, `*-backups/`, `fp-info-cache`, `*.kicad_prl`.
- Add `pcb/production/` with a `!` exception policy: production files are force-added on tags.

---

## 13. Future (not rev A)

- RP2350A hardware (rev B, needs the A4 stepping).
- A TFT display using TP1–TP3.
- RGB on GP22.
- Encoders.
- TRRS detect on GP21.
- 4-layer variant.
- Hierarchical schematics.
- FR4 plate as a KiCad board.
- Runtime role swap.

---

## 14. Implementation plan

**Rules for every stream**
- A stream stages **only its own paths** (`git add <owned dirs>`).
- Commits use Conventional Commits and end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Before pushing to `main`: `git pull --rebase`.
- The orchestrator serialises pushes and pushes after each acceptance gate passes.
- Each stream adds recipes only in its own `*.just` file. The root `justfile` (WS0) `import`s them all, and WS0 creates empty stubs up front.

**Shared contracts, frozen by WS0 before the parallel phase:**
- `layout/build/layout.json` and its schema
- `layout/pins.py`
- the `layout.outline(side)` and `layout.zones(side)` functions
- the footprint names in §7, which WS2 produces and WS3 consumes only through the STEP file

### WS0: Foundations and layout (sequential, first)

- **Owns:** the root files (`README` skeleton, `CHANGELOG`, `THIRD_PARTY`, `LICENSE-HARDWARE`, `.gitignore`, `.editorconfig`, `.gitattributes`, `justfile`, `pyproject.toml`, `uv.lock`, `.python-version`), `layout/`, `tools/`, `.github/workflows/layout.yml`, and empty stub `*.just` files for the other streams.
- **Deliverables:**
  - the exact key table, thumb formula, display, J1/J2/U1 anchors, holes (#7 moved), outline (§8.1) and zones (§8.3), for both sides
  - `pins.py`
  - `export.py` writing `layout.json`, `docs/images/layout.svg` and `build/kle.json`
- **Acceptance** (`just layout-check` = `uv run pytest layout`, plus an idempotency check):
  - 37 keys per half, 74 total
  - main keys equal §5 to 1e-4, thumbs equal the original PCB within 0.002
  - no housing overlaps (15.6 mm)
  - display ≥ 4.0 mm from every housing and ≥ 1.0 mm from every boss (Ø6.5)
  - USB-C body ≥ 2 mm from boss #5
  - J2 body inside Z_TRRS
  - outline valid and simple, containing every cell
  - left = mirror(right)
  - `git diff --exit-code` clean after `just layout`
  - `/zephyr/` no longer ignored
  - CI `layout.yml` green

### WS1: Firmware (after WS0)

- **Owns:** `firmware/`, `zephyr/`, `build.yaml`, `.github/workflows/firmware.yml`.
- **Deliverables:**
  - the seed module copied in
  - right `.dts` reversed col-gpios
  - `west.yml` pinned to the SHA
  - generated `worxboard-layouts.dtsi`
  - 74-key, 3-layer keymap
  - the custom right screen
  - `firmware.just`
- **Acceptance:**
  - `just fw` builds every `build.yaml` row with a `zmk.uf2` (rows that fail are removed, per the §11.2 rule; the two core rows must pass)
  - keymap has 74 bindings per layer
  - layouts dtsi regenerates with no diff
  - `nm`/map of the right build has no `zmk_ble_` symbols
  - right flash grows less than 40 KB compared with the seed
  - GitHub Actions run green with artifacts

### WS2: Electrical, schematic and PCB (after WS0; sequential inside the stream)

- **Owns:** `pcb/`, `.github/workflows/pcb.yml`.
- **Deliverables:** §9 stages 1–14 for both sides, committed KiCad files, renders in `docs/images/pcb-*.png` (WS2 owns only those files), and `pcb.just` (`pcb <side>`, `pcb-all`).
- **Acceptance (both sides):**
  - ERC 0 errors
  - `netcmp.py` passes
  - DRC `--schematic-parity --severity-error` exits 0 with 0 unconnected
  - `checks.py` passes
  - `kikit … --missingError` exits 0
  - STEP and Edge DXF exported
  - CI uploads `jlc/` and the STEP as artifacts

### WS3: Case and plates (after WS0; parallel with WS1/WS2)

- **Owns:** `case/`, `plates/`, `.github/workflows/case.yml`.
- **Deliverables:** §10, plus `case.just` (`model`, `renders`, `fitcheck`).
- **Acceptance:**
  - `just model` exports STEP/STL for top, bottom, spacer, legs and caps of both halves, plus the 1:1 fit-check DXF showing the window, USB and TRRS notches
  - every check passes: clearance, boss_webs, leg, web, spacer, `display_check`, `jack_check`
  - USB and TRRS notch centres equal the `layout` anchors within 0.2 mm
  - `check_fit.py` reports 0 mm³ once WS2's STEP exists (a warning beforehand)
  - CI `case.yml` green

### WS4: Docs and site (after WS0; can start in parallel, final pass after WS1–WS3)

- **Owns:** `docs/` except the `pcb-*.png` renders, `site/`, `README.md` body sections, `.github/workflows/pages.yml`.
- **Deliverables:**
  - this spec as `docs/design.md`
  - `electrical.md`, `pinout.md`, `matrix.md` (generated from `layout`), `bom.md` with [G3] flags, `ordering-jlcpcb.md`, `case.md`, `legs.md`, `sources.md` (with attribution)
  - `buildguide_en.md` in crkbd style: parts table, hot-swap/display-socket build, flashing BOOT+RESET → `RPI-RP2` → drag the `.uf2`, **plug the host into the LEFT half**, **never hot-plug TRRS**, JP1 modes
  - the microsite, which reads only `layout` and the exported files
- **Acceptance:**
  - lychee link check green
  - `pinout.md` and `matrix.md` regenerate with no diff
  - the Pages site builds and deploys

### WS5: Integration and release (last)

- **Owns:** `tests/integration/`, `.github/workflows/release.yml`, `CHANGELOG.md` release entries, `docs/verification.md`.
- **Deliverables:**
  - `test_pins.py`: the firmware DT pins and the right col-gpios order cross-checked against the WS2 netlist and `layout/pins.py`
  - gates G1–G3 researched and recorded, with any fixes sent back to the owning stream
  - `just all` (layout-check → fw → pcb-all → model → site) run from a clean clone
  - tag `v0.1.0-revA`
  - `release.yml` attaching the gerbers/BOM/CPL zips, UF2s and case STEP/STL
- **Acceptance:**
  - all six workflows green on the tag
  - the release contains every artifact
  - `docs/verification.md` lists G1–G3 as PASS, or as an open item that blocks ordering

**Order.** WS0 runs first, alone. Then {WS1, WS2, WS3, WS4} run in parallel; WS3's `fitcheck` and WS4's final pass consume WS2's outputs. WS5 runs last.

**Dependency summary**

| Contract | Owned by | Consumed by |
|---|---|---|
| `layout.json`, `pins.py`, outline/zones | WS0 | all streams |
| `build/<side>/*.step` and netlist | WS2 | WS3, WS5 |
| UF2 artifacts | WS1 | WS5 |
| renders | WS2 / WS3 | WS4 |