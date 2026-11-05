<div align="center">

# ⌨️ worxboard

**An ErgoDox-style split keyboard, generated from one layout package.**

On-board RP2040 · ZMK wired split · a memory LCD on each half · USB-C on both halves · MX hot-swap, fully JLC-assembled · CNC aluminium case

<sub>🚧 <b>rev A is designed, checked and orderable, but not yet built or tested on hardware.</b></sub>

[![rev A not yet built](https://img.shields.io/badge/rev_A-not_yet_built-orange)](docs/verification.md#not-verified-until-a-board-is-built) [![layout](https://github.com/w0rxbend/worxboard/actions/workflows/layout.yml/badge.svg)](https://github.com/w0rxbend/worxboard/actions/workflows/layout.yml) [![firmware](https://github.com/w0rxbend/worxboard/actions/workflows/firmware.yml/badge.svg)](https://github.com/w0rxbend/worxboard/actions/workflows/firmware.yml) [![pcb](https://github.com/w0rxbend/worxboard/actions/workflows/pcb.yml/badge.svg)](https://github.com/w0rxbend/worxboard/actions/workflows/pcb.yml) [![case](https://github.com/w0rxbend/worxboard/actions/workflows/case.yml/badge.svg)](https://github.com/w0rxbend/worxboard/actions/workflows/case.yml)<br>
[![ZMK](https://img.shields.io/badge/firmware-ZMK-5f3dc4)](https://zmk.dev) [![KiCad 10](https://img.shields.io/badge/PCB-KiCad_10-314cb0?logo=kicad&logoColor=white)](https://www.kicad.org/) [![build123d](https://img.shields.io/badge/CAD-build123d-3776ab?logo=python&logoColor=white)](https://github.com/gumyr/build123d) [![License: GPL v3](https://img.shields.io/badge/code-GPLv3-blue.svg)](LICENSE) [![License: CERN-OHL-S-2.0](https://img.shields.io/badge/hardware-CERN--OHL--S--2.0-blue.svg)](LICENSE-HARDWARE)

**[🌐 Live 3D viewer](https://w0rxbend.github.io/worxboard/) · [🛒 Order it](#-order-it) · [🚀 Zero to typing](#-from-zero-to-typing) · [🔧 Build guide](docs/buildguide_en.md) · [📋 BOM](docs/bom.md) · [🧾 Shopping list](docs/shopping-list.md)**<br>**[💾 Firmware](docs/firmware.md) · [🧱 Case](docs/case.md) · [📐 Design spec](docs/design.md) · [🧪 Verification](docs/verification.md)**

<a href="docs/images/site-viewer.png"><img src="docs/images/site-viewer.png" alt="Both worxboard halves in the browser 3D viewer, with legends on the keycaps and the black case finish" width="880"></a>

<sub>🖥️ Both halves in the browser 3D viewer, built from <a href="layout/build/layout.json">layout.json</a>: ErgoDox stagger, 25° thumbs, the display in the inner top slot, the tent legs. A render, not a photo, committed on 2026-11-02, before case revision A3, so the case has no raised display bezel yet.</sub>

</div>

worxboard keeps the exact ErgoDox key positions and the 25° six-key thumb cluster. On each half, the top key of the inner column is replaced by a vertical memory LCD, and the two halves link over TRRS with ZMK's wired split. Everything is generated from one layout package, [`layout/`](layout/): the KiCad schematics and PCBs, the build123d case, the ZMK physical layout, the docs tables and the 3D viewer. On every push to `main` and every pull request, CI rebuilds and checks the layout, the firmware, both PCBs with their order packages, and the case with its order package. The generated docs tables are checked by `just docs-check`, and the viewer is built by `just site`. Both also run in the manual `pages` workflow.

> [!WARNING]
> **Status: rev A is designed, checked and orderable, but not yet built.** Gates **G1–G3** are recorded as passed in [verification.md](docs/verification.md). The JLCPCB turnkey order for both PCBs and the case order are committed, and CI checks them ([Order it](#-order-it)). No board has been made, and nothing has been tested on hardware. Order 2 assembled boards per side and test them before you machine the case. The frozen design is [`docs/design.md`](docs/design.md), and every change from it is listed in [`docs/deviations.md`](docs/deviations.md). Read the [known open issues](#-known-open-issues) before you order.

| ⌨️ Keys | 🧠 MCU | 📟 Display | 🔗 Split link | 🏭 Assembly | 🧱 Case |
|:-:|:-:|:-:|:-:|:-:|:-:|
| **74**, 37 per half | **RP2040** on each PCB | **160 × 68** memory LCD per half | **115 200** baud UART over TRRS | **119** JLC-assembled parts per half | **≈ 349 g** of 6061-T6 per half |

<details>
<summary>🚦 Status by part</summary>

| Part | State |
|---|---|
| 🧬 Layout (`layout/`) | ✅ **Done.** Keys, thumbs, display, jacks, holes, outline, zones and the GPIO map; checked by `just layout-check` |
| 🟩 PCB (`pcb/`) | ✅ **Orderable.** Both halves are generated in KiCad 10. ERC is clean. DRC with schematic parity reports 0 violations and 0 unconnected items. The checks on the USB pair, crystal, decoupling, U1 ground return and GND links, via-in-pad, J1 pin-in-paste and outline all pass. A seeded from-scratch rebuild in CI reproduces the committed boards. The JLC turnkey package (panel, BOM, and a CPL proven against JLC's own footprints) is committed in [`pcb/production/`](pcb/production/). |
| 💾 Firmware (`firmware/`, `zephyr/`, `build.yaml`) | 🔨 **Builds.** All six `build.yaml` rows build locally and in CI: left central, right peripheral, two role-swap rows and two RP2350A rows. Both screens are laid out portrait for the upright display. Nothing has run on hardware. |
| 🧱 Case and plates (`case/`, `plates/`) | ✅ **Orderable.** Every case check passes, and so does JLCCNC's internal-corner rule. `just fitcheck` reports 0 mm³ of interference against both PCB STEPs plus the layout envelopes. The JLCCNC / JLC3DP package for case revision A3 is committed in [`case/production/`](case/production/README.md). Nothing has been printed or machined. |
| 📚 Docs and microsite (`docs/`, `site/`) | ✅ **Done.** The turnkey ordering guide, shopping list, build guide, generated BOM, pinout and matrix, and the electrical, case, legs and firmware docs. The site has the 3D viewer. |
| 🧪 Gates and release | ✅ **Pass.** [`docs/verification.md`](docs/verification.md) records the integration tests (111 passed), CI, the order-package checks and gates G1–G3. [`release.yml`](.github/workflows/release.yml) is written, but no tag or release exists yet. |
| 🛠️ Hardware | ⏳ **Not built.** What only a real board can confirm is [listed](docs/verification.md#not-verified-until-a-board-is-built). |

</details>

## 🧭 Contents

| 👀 See it | 🛠️ Make it | 📖 Know it |
|---|---|---|
| [📸 Gallery](#-gallery) | [🚀 From zero to typing](#-from-zero-to-typing) | [🤖 Generated, not drawn](#-generated-not-drawn) |
| [✨ Features](#-features) | [🛒 Order it](#-order-it) | [🐛 Known open issues](#-known-open-issues) |
| [📊 Specs](#-specs) | [🔧 Build it](#-build-it) | [🔭 Future work](#-future-work) |
| [📐 Layout and matrix](#-layout-and-matrix) | [💾 Firmware](#-firmware) | [🌳 Repository layout](#-repository-layout) |
| [🌐 Spin it in your browser](#-spin-it-in-your-browser) | [🧱 Case](#-case) | [📚 Documentation](#-documentation) |
| | [🧰 Build from source](#-build-from-source) | [🙏 Credits](#-credits) |
| | [📦 Get the files](#-get-the-files) | [📜 License](#-license) |

## 📸 Gallery

> [!NOTE]
> Every image in this README is a render, a CAD drawing or a screenshot. No photos exist yet, because rev A has not been built. The two viewer screenshots were committed on 2026-11-02, before case revision A3, so the case they show is older (for example, it has no raised display bezel). They also predate the re-placed turnkey boards (BOARD-1), so the parts drawn on the PCBs are from the older layout. KiCad has no 3D model for the USB-C, the TRRS jack or the hot-swap sockets, so the PCB renders show only their footprints.

<table>
<tr><td align="center" width="50%"><a href="docs/images/site-viewer-exploded.png"><img src="docs/images/site-viewer-exploded.png" alt="Right half exploded in the 3D viewer, silver finish" width="100%"></a><br><sub>💥 Right half exploded in the viewer: tray, PCB, printed spacer, top shell, switches, keycaps</sub></td><td align="center" width="50%"><a href="case/renders/right_with_legs.png"><img src="case/renders/right_with_legs.png" alt="CAD render of the closed right-half case with its three tent legs" width="100%"></a><br><sub>🦵 Closed right-half case with its three custom tent legs (CAD render)</sub></td></tr>
<tr><td align="center"><a href="docs/images/pcb-left-top.png"><img src="docs/images/pcb-left-top.png" alt="KiCad render of the left PCB, top side" width="100%"></a><br><sub>🟩 Left PCB, top: RP2040, flash, USB-C J1, BOOT/RESET, JP1 (“cut = split power”), display socket J3, TRRS jack J2 on the inner bump</sub></td><td align="center"><a href="docs/images/pcb-right-top.png"><img src="docs/images/pcb-right-top.png" alt="KiCad render of the right PCB, top side" width="100%"></a><br><sub>🟩 Right PCB, top: mirrored, same netlist; both boards print DO NOT HOT-PLUG TRRS and HOST → LEFT by J2</sub></td></tr>
<tr><td align="center"><a href="docs/images/pcb-left-bottom.png"><img src="docs/images/pcb-left-bottom.png" alt="KiCad render of the left PCB, bottom side" width="100%"></a><br><sub>🟩 Left PCB, bottom: 37 hot-swap socket footprints and 37 diodes</sub></td><td align="center"><a href="docs/images/pcb-right-bottom.png"><img src="docs/images/pcb-right-bottom.png" alt="KiCad render of the right PCB, bottom side" width="100%"></a><br><sub>🟩 Right PCB, bottom: 37 socket footprints and 37 diodes, all fitted by JLC</sub></td></tr>
<tr><td align="center" colspan="2"><a href="case/renders/pair_top_iso.png"><img src="case/renders/pair_top_iso.png" alt="CAD render of both CNC top shells side by side" width="100%"></a><br><sub>🧱 Both CNC top shells: the plate is milled into the key well, with 2u stabiliser cut-outs and a display window on each half</sub></td></tr>
</table>

## ✨ Features

<table>
<tr><td width="33%" valign="top">

**📐 Exact ErgoDox layout**<br>The switch centres, the column stagger and the 25° thumb cluster come from the original ErgoDox PCB. The thumb keys match it within 0.002 mm, and the main keys match the spec table within 0.0001 mm. 37 keys per half, 74 in total.

</td><td width="33%" valign="top">

**📟 A display on each half**<br>A Sharp LS011B7DH03 memory LCD (160 × 68) on a nice!view-class module sits where the inner top key was, behind a window in the case. The left half shows the ZMK status screen. The right half shows a custom lock-indicator screen.

</td><td width="33%" valign="top">

**🧠 On-board RP2040**<br>There is no controller daughterboard. The support circuit is derived from the [Corne v4.1](https://github.com/foostan/crkbd): QSPI flash, a 12 MHz crystal, an LDO and ESD arrays. JLCPCB fits all 119 parts per half, on both sides.

</td></tr>
<tr><td valign="top">

**🔌 USB-C on both halves**<br>Plug the host into the **left** half. The right USB-C gives power and UF2 flashing. Schottky diodes let you plug in both at once without back-feeding either host.

</td><td valign="top">

**🔗 A careful wired split**<br>ZMK `zmk,wired-split` runs on UART0 at 115 200 baud over a straight TRRS cable. The tip carries only 1 kΩ-limited data. Power sits on Ring2 behind a 250 mA polyfuse, and solder jumper JP1 turns cable power off.

</td><td valign="top">

**🔥 Hot-swap, no PCB soldering**<br>MX hot-swap sockets of the CPG151101S11 type sit on the bottom, with 2u plate-mount stabilisers on two thumb keys per half. JLC fits every PCB part, display socket included; you solder only the displays' header pins (and any J1 shell leg that arrives bare).

</td></tr>
<tr><td valign="top">

**🧱 CNC aluminium case**<br>Each half has a 6061-T6 top shell with the 1.5 mm plate milled into it, a 6061-T6 tray and a printed 3 mm spacer. The finish is bead blast plus anodize. A raised bezel covers the display.

</td><td valign="top">

**🦵 Tent legs like the EZ**<br>Each half has three mounts at the stock ErgoDox EZ positions. Every mount takes one custom aluminium leg with a TPU foot cap, clamped by an M3 × 12 collarless thumbscrew and a friction washer.

</td><td valign="top">

**🤖 Generated, not drawn**<br>The schematic, placement, routing, DRC, fab files, case, physical layout and docs tables are all scripts. The PCB stages run headless in version-pinned KiCad and Freerouting containers and are seeded, so a rebuild gives byte-identical boards.

</td></tr>
</table>

## 📊 Specs

| Spec | rev A |
|---|---|
| ⌨️ **Keys** | 74 (37 per half). Each half has a 6 × 7 `col2row` matrix; ZMK sees one 6 × 14 transform |
| 🧠 **Controller** | RP2040 (QFN-56) per half, with W25Q128JVSIQ 16 MB QSPI flash and a 12 MHz crystal |
| 📟 **Display** | Sharp LS011B7DH03, 160 × 68 memory LCD on a nice!view-class module, driven over PIO1 SPI at 1 MHz |
| 🔗 **Split link** | 3.5 mm TRRS, ZMK wired split on UART0 at 115 200 baud, full duplex |
| 🔌 **USB** | USB-C 2.0 full speed on both halves (HRO TYPE-C-31-M-12); the host goes on the left |
| 🟩 **PCB** | 2 layers, 1.6 mm FR4, 1 oz, ENIG, 182.84 × 158.75 mm per half. JLC places 119 parts per half: 45 on top, and 74 on the bottom (37 sockets + 37 diodes) |
| 🎹 **Switches** | 74 MX-compatible plate-mount switches, 3- or 5-pin, in hot-swap sockets; 4 × 2u plate-mount stabilisers |
| 💾 **Firmware** | ZMK, HWMv2 board `worxbend/worxboard`, pinned at `4dd95d78`; ZMK Studio on the left central |
| 🧱 **Case** | 3 parts per half (CNC top and tray, printed spacer); 192.4 × 165.6 × 17.6 mm, 19.6 mm at the display bezel; about 349 g per half |
| 🦵 **Legs** | 3 per half, held by M3 × 12 DIN 653 thumbscrews with friction washers |

<details>
<summary>🔬 Full specs: key parts, power path, TRRS contacts, GPIO map</summary>

**🧩 Key parts per half** (the full generated table is in [docs/bom.md](docs/bom.md)):

| Ref | Part | LCSC | Ref | Part | LCSC |
|---|---|---|---|---|---|
| U1 | RP2040, QFN-56 | [C2040](https://jlcpcb.com/partdetail/C2040) | U2 | W25Q128JVSIQ, 16 MB QSPI flash | [C97521](https://jlcpcb.com/partdetail/C97521) |
| Y1 | 12 MHz 3225 crystal, YXC XL2EL89CRI-111YLC-12M | [C49304726](https://jlcpcb.com/partdetail/C49304726) | U3 | AP2112K-3.3, 600 mA LDO | [C51118](https://jlcpcb.com/partdetail/C51118) |
| U4, U5 | USBLC6-2SC6 ESD arrays (USB, TRRS) | [C7519](https://jlcpcb.com/partdetail/C7519) | D1 | B5819W, 1 A Schottky | [C8598](https://jlcpcb.com/partdetail/C8598) |
| F1 | nSMD025-24V PTC, 250 mA hold | [C70069](https://jlcpcb.com/partdetail/C70069) | J1 | HRO TYPE-C-31-M-12 USB-C receptacle | [C165948](https://jlcpcb.com/partdetail/C165948) |
| J2 | PJ-320D-4A TRRS jack, SMD | [C95562](https://jlcpcb.com/partdetail/C95562) | J3 | 1×5 2.54 mm female socket, 5.0 mm tall (the only through-hole part) | [C27985230](https://jlcpcb.com/partdetail/C27985230) |
| SW1, SW2 | TS-1088R tact switches (BOOT, RESET) | [C455280](https://jlcpcb.com/partdetail/C455280) | SK101–SK137 | MX hot-swap socket, HanElectricity CPG151101S11-16 | [C41430893](https://jlcpcb.com/partdetail/C41430893) |
| D101–D137 | 1N4148W matrix diodes | [C81598](https://jlcpcb.com/partdetail/C81598) |  |  |  |

The BOM has 22 lines with 21 LCSC numbers. The retired parts C2803348 (socket), C113767 (flash) and C91749 (crystal) fail `stock.py` and `netcmp.py` if they come back.

**⚡ Power path**, the same on each half ([electrical.md](docs/electrical.md#power-path)):

```mermaid
flowchart LR
    USB["USB-C VBUS"] --> D1["D1 B5819W<br/>Schottky"] --> VSYS["VSYS ≈ 4.6 V"] --> U3["U3 AP2112K-3.3"] --> V33["3V3<br/>RP2040 · flash · display"]
    VSYS --> JP1["JP1<br/>bridged by default"] --> F1["F1 PTC<br/>250 mA hold"] --> VLINK["VLINK<br/>TRRS Ring2"]
```

One cable is enough: the far half runs from VLINK at about 4.4 V. Each VBUS reaches VSYS only through its own D1, so two hosts at once never back-feed each other. VBUS also reaches GP26 through a 10k/10k divider; rev A firmware does not use it.

**🔗 TRRS contacts** ([electrical.md](docs/electrical.md#trrs-link)):

| Contact | Left PCB | Right PCB |
|---|---|---|
| Tip | `TRRS_A` = UART TX (GP0, via 1 kΩ) | `TRRS_A` = UART RX (GP1, via 1 kΩ) |
| Ring1 | `TRRS_B` = UART RX | `TRRS_B` = UART TX |
| Ring2 | VLINK | VLINK |
| Sleeve | GND | GND |

**📍 GPIO map**, identical on both PCBs (every pin is in [pinout.md](docs/pinout.md)):

| GPIO | Use |
|---|---|
| GP0 / GP1 | UART0 TX / RX, the wired split |
| GP2 / GP3 / GP5 | Display SCK / MOSI / CS (PIO1 SPI, CS active high) |
| GP8–GP13 | Matrix rows ROW0–ROW5 (inputs, pull-down) |
| GP14–GP20 | Matrix columns COL0–COL6 (outputs) |
| GP21 | TRRS detect test pad TP11 (not used in rev A) |
| GP22 | Reserved for RGB (TP4) |
| GP26 | VBUS sense through a 10k/10k divider (not used by rev A firmware) |
| SWCLK / SWDIO | SWD test pads TP8 / TP9, with GND on TP10 |

</details>

## 📐 Layout and matrix

<p align="center">
<a href="docs/images/layout.svg"><img src="docs/images/layout.svg" alt="Generated plan view of both worxboard halves" width="880"></a><br><sub>🗺️ The generated rev A layout (layout/export.py): ErgoDox stagger, 25° thumbs, the display in the C6R0 slot, the jacks, the holes and the component zones. Click to open it full size.</sub>
</p>

On each half, the inner top key C6R0 is replaced by a vertical 14 × 36 mm display module. Its bottom edge lies on the old C6R0 cell boundary, so no other key moves. Each half has a 6 × 7 `col2row` matrix with rows on GP8–GP13 and columns on GP14–GP20. **Both PCBs share one matrix netlist**: the right `.dts` reverses `col-gpios` and sets `col-offset = <7>`, so the two netlists differ only in the TRRS TX/RX crossover at R11/R12.

| What changed from an ErgoDox EZ | worxboard rev A |
|---|---|
| 📟 Inner top key | Replaced by the display, so each half has 37 keys |
| ✂️ Outline | Jack tabs removed, back edge straightened, a TRRS bump added on the inner edge |
| 🔩 Mounting hole #7 | Moved from under the display to (88.0, 37.135) |
| 🔌 Connectors | USB-C on both halves at the back edge; TRRS on the inner edge |
| 🧠 Controller | An on-board RP2040 per half |
| 💾 Firmware | ZMK, with the base layer taken from QMK `ergodox_ez` layer 0; the two inner-top functions (LEFT / RGHT) move to layer 1 |
| 🎹 Switches | Kailh-type MX hot-swap sockets on the bottom |
| 🧱 Case | CNC 6061-T6. It drops the EZ's capacitor pocket, LED windows, reset hole and back-wall jack notches, and comes out about 1–2 mm smaller than the photo-measured EZ case |

> [!TIP]
> **🎹 What goes on top:** 74 MX-compatible plate-mount switches, 3- or 5-pin (Choc and Alps do not fit). Keycaps: 58 × 1u, 12 × 1.5u (8 horizontal in the outer columns, 4 vertical in the inner columns) and 4 × 2u vertical thumbs. **A standard 76-key ErgoDox keycap set covers it, with 2 × 1u spare.** Add 4 Cherry-style clip-in 2u plate-mount stabilisers for a 1.5 mm plate; screw-in PCB-mount stabilisers do not fit.

<details>
<summary>🧮 The ZMK 6 × 14 transform and the three layers</summary>

This is the global map that the keymap and ZMK Studio see. Left columns 0–6 are physical C0–C6, and right columns 7–13 are physical C6–C0 ([matrix.md](docs/matrix.md)).

**Left half** (global columns 0–6 = physical C0–C6)

| Row | 0 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|---|
| 0 | `=` | `1` | `2` | `3` | `4` | `5` | 📟 LCD |
| 1 | `DEL` | `Q` | `W` | `E` | `R` | `T` | `TG(1)` |
| 2 | `BSPC` | `A` | `S` | `D` | `F` | `G` | · |
| 3 | `LSFT` | `CTL_T(Z)` | `X` | `C` | `V` | `B` | `HYPER` |
| 4 | `` LT(1,`) `` | `'` | `LA(LSFT)` | `LEFT` | `RGHT` | · | · |
| 5 | · | `SPC` | `BSPC` | `END` | `HOME` | `ALT_T(APP)` | `LGUI` |

**Right half** (global columns 7–13 = physical C6–C0)

| Row | 7 | 8 | 9 | 10 | 11 | 12 | 13 |
|---|---|---|---|---|---|---|---|
| 0 | 📟 LCD | `6` | `7` | `8` | `9` | `0` | `-` |
| 1 | `TG(1)` | `Y` | `U` | `I` | `O` | `P` | `\` |
| 2 | · | `H` | `J` | `K` | `L` | `LT(2,;)` | `GUI_T(')` |
| 3 | `MEH` | `N` | `M` | `,` | `.` | `CTL_T(/)` | `RSFT` |
| 4 | · | · | `UP` | `DOWN` | `[` | `]` | `TT(1)` |
| 5 | `LALT` | `CTL_T(ESC)` | `PGUP` | `PGDN` | `TAB` | `ENT` | · |

| Layer | Contents |
|---|---|
| 0 Base | The QMK `ergodox_ez` default layer 0 |
| 1 Sym | F1–F12, symbols, a right-hand numpad, and LEFT / RIGHT on the inner 1.5u `HYPER` / `MEH` keys |
| 2 Media | Mouse movement and clicks, media keys, `&bootloader`, `&sys_reset` and `&studio_unlock` |

Each layer has 74 bindings, in the order 12 / 14 / 12 / 14 / 10 and then the 12 thumb keys.

</details>

## 🌐 Spin it in your browser

> [!NOTE]
> **Live at [w0rxbend.github.io/worxboard](https://w0rxbend.github.io/worxboard/).** The manual [`pages`](.github/workflows/pages.yml) workflow deploys it from `main`, so the site shows `main` as of its last run. Run it locally with `just site-serve` (port 8000). GitHub also opens the committed STLs, such as [`worxboard_left_spacer.stl`](case/production/jlc3dp/worxboard_left_spacer.stl), in its own 3D viewer.

The microsite in [`site/`](site/) has a three.js viewer, adapted from the [ErgoDox CNC case](https://github.com/w0rxbend/ergodox) viewer (the hero shot and the exploded view above are screenshots of it). It builds both halves straight from `layout/build/layout.json`: the PCB, switches, keycaps with legends and the displays. It places every assembled part of the committed KiCad boards at its real position, and it adds the case STLs if `just model` ran before `just site`.

| Feature | What it does |
|---|---|
| 🎬 **Scenes** | Pair / Left / Right, plus six case finishes: Black, Silver, Space grey, Blue, Red, Orange |
| 🎥 **Camera** | Iso, Top, Front and Side presets, fullscreen, auto-rotate |
| 💥 **Explode, cut, swing** | Pull the stack apart (tray, PCB, spacer, top shell, switches, keycaps), sweep a section plane along Y, swing the three tent legs per half from 0° to 180° |
| 🖱️ **Hover** | Shows a key's legend and ZMK matrix position, or a part's reference, value and footprint |
| 📥 **Downloads** | The case STLs and `layout.json`; a Screenshot button; deep links such as `#scene=left&finish=silver&view=top` |

Around the viewer, the page carries the specs, the build journey, the order packages, the case Z stack, the open issues and a filterable gallery of every render and placement proof, with a lightbox.

## 🚀 From zero to typing

> [!TIP]
> Follow the steps in this order. Rev A has not been built, so one assembled PCB is flashed and tested before any aluminium is machined.

| Step | What you do | Docs and files |
|---|---|---|
| 1️⃣ 🟩 **Order the PCBs** | Two designs at JLCPCB: 5 PCBs each, 2 assembled, both sides. | 📄 [ordering-jlcpcb.md](docs/ordering-jlcpcb.md), [placement checklist](docs/ordering-jlcpcb.md#placement-preview-checklist)<br>📂 [`pcb/production/left/`](pcb/production/left/README.md), [`pcb/production/right/`](pcb/production/right/README.md) |
| 2️⃣ 🛍️ **Buy the parts** | 74 MX switches, keycaps, 4 stabilisers, 2 nice!view, cables, case hardware. | 📄 [shopping-list.md](docs/shopping-list.md)<br>📂 [`case/production/hardware.csv`](case/production/hardware.csv) |
| 3️⃣ ⚡ **Flash and test the bare boards** | Flash both UF2s, test every socket with tweezers, set JP1, fit the displays. | 📄 [build guide §1–4](docs/buildguide_en.md#1-check-the-assembled-pcbs), [firmware.md](docs/firmware.md#flash)<br>📦 the `worxboard-firmware` artifact of a green [firmware run](https://github.com/w0rxbend/worxboard/actions/workflows/firmware.yml) |
| 4️⃣ 🧱 **Order the case** | Print a test top, then order from JLCCNC and JLC3DP. | 📄 [case.md](docs/case.md#before-machining), [build guide §5](docs/buildguide_en.md#5-prepare-the-case)<br>📂 [`jlccnc/`](case/production/jlccnc/ORDER_NOTES.md), [`jlc3dp/`](case/production/jlc3dp/ORDER_NOTES.md) |
| 5️⃣ 🔩 **Assemble** | Stabilisers into the top shell first, then PCB, spacer, top shell and screws; then switches, caps and legs. | 📄 [build guide §6–8](docs/buildguide_en.md#6-assemble-the-case), [legs.md](docs/legs.md) |
| 6️⃣ ⌨️ **Type** | TRRS in while both halves are unpowered, host into the **left** half, remap in ZMK Studio. | 📄 [build guide §9](docs/buildguide_en.md#9-connect-and-use), [keymap](docs/firmware.md#keymap) |

## 🛒 Order it

Every order file for one keyboard is committed, and CI rebuilds and checks the PCB and case packages on every push:

| Order | Where | Files | How |
|---|---|---|---|
| 🟩 Left and right PCBs, fully assembled (2 designs: 5 PCBs each, 2 of them assembled) | [JLCPCB](https://jlcpcb.com), Standard PCBA, both sides | [`pcb/production/left/`](pcb/production/left/README.md), [`pcb/production/right/`](pcb/production/right/README.md): `gerbers.zip`, `bom.csv`, `cpl.csv` | [ordering-jlcpcb.md](docs/ordering-jlcpcb.md) |
| 🧱 2 top shells, 2 bottom trays, 6 tent legs (6061-T6, bead blast + anodize, Strict tier if the form offers it) | [JLCCNC](https://jlccnc.com) | [`case/production/jlccnc/`](case/production/jlccnc/ORDER_NOTES.md) | the order notes |
| 🖨️ 2 plate spacers (MJF PA12), 1 tree of 8 leg foot caps (TPU 95A) | [JLC3DP](https://jlc3dp.com) | [`case/production/jlc3dp/`](case/production/jlc3dp/ORDER_NOTES.md) | the order notes |
| 🎹 Switches, keycaps, stabilisers, 2 nice!view displays, cables; 🔩 screws, feet, thumbscrews, washers | keyboard and hardware shops | [`case/production/hardware.csv`](case/production/hardware.csv) (the case hardware) | [shopping-list.md](docs/shopping-list.md) |

JLC fits every part on the PCB. That includes the display socket J3, which JLC hand-solders, and J1's shell legs, which are pin-in-paste. You only solder the displays' own header pins. The build guide still asks you to check that all four J1 shell-leg slots show solder, and to solder any bare leg yourself ([step 1](docs/buildguide_en.md#1-check-the-assembled-pcbs)).

> [!IMPORTANT]
> **💰 About \$307–425** for the JLCPCB order of both halves with 2 assembled each, shipping included, before import duty and VAT. This was estimated on 2026-11-04. The PCBA subtotal is \$246.72; the fabrication and shipping lines are ranges, not quotes ([cost estimate](docs/ordering-jlcpcb.md#cost-estimate)). JLCCNC and JLC3DP quote the case when you upload the files.
>
> **📦 Stock moves daily.** Run `just pcb-stock left 5` on the day you order. Then order 2 assembled boards per side, test them, and only then order the aluminium case.

> [!CAUTION]
> **🔌 The cables are the main gotcha.**
> - **USB-C:** a USB 2.0 data cable (not charge-only) whose bare metal plug shell sticks out of the overmould by **at least 8 mm**. These are sold as "extended tip" or "long neck". A common 6.5–6.6 mm shell stops about 1.2 mm short and does not latch, so measure with calipers.
> - **TRRS:** 3.5 mm, **4-pole**, wired straight 1:1 (the crossover is on the PCB). The plug head must be **at most Ø6.3 mm for its first 3.7 mm** behind the metal shaft.

<details>
<summary>🧾 The JLCPCB form at a glance, and what is in each order package</summary>

| PCB | PCBA |
|---|---|
| FR-4, 2 layers, qty 5, Panel by Customer | Standard (Economic places one side only), both sides, qty 2 |
| 1.6 mm, ENIG, 1 oz, tented vias | Tooling holes and rails: Added by Customer; Confirm parts placement: Yes |

Do it once for the left side and once for the right, so the cart holds two designs, and paste the remark from each side's README into the order. The remark also answers JLC's likely question about the two pairs of stabiliser holes, 0.28 mm apart (deviation ORDER-3), so it doesn't hold the order. Every field is in [ordering-jlcpcb.md](docs/ordering-jlcpcb.md#step-by-step).

- **`pcb/production/<side>/`**: `gerbers.zip` (the 198.84 × 174.75 mm panel: 14 mouse-bite tabs, 3 fiducials per side, 4 tooling holes, panel DRC 0 / 0), `bom.csv` (22 lines, 21 LCSC numbers), `cpl.csv` (119 placements, 74 on the bottom, JLC rotation and centre corrections applied), `README.md` (the order form), `worxboard-<side>-jlc-order.zip` (the same files plus that README) and `bare-board/` (a 182.84 × 158.75 mm fallback in case JLC refuses the panel).
- **`case/production/`** (case revision A3): `jlccnc/` (STEP + PDF drawings for the left and right tops, the left and right bottoms and the leg, plus `hole_table.csv` and `ORDER_NOTES.md`), `jlc3dp/` (`worxboard_{left,right}_spacer.stl`, `worxboard_leg_cap_tree.stl`, `ORDER_NOTES.md`), `hardware.csv` and the package [README](case/production/README.md). CI fails if any of it drifts from the model.

</details>

<details>
<summary>🎯 JLC placement proofs: 238 of 238 placements pass, one drawing per part type over the KiCad pads</summary>

`cpl_check.py` places JLC's own EasyEDA footprint for each CPL row and compares it with the KiCad pads: 119 of 119 per half pass, within 0.033 mm. Legend: grey is KiCad copper, white the holes, red JLC's pads, blue the part's terminals, green its body and gold the board edge. A red ring marks JLC pin 1, and a cross marks KiCad pad 1. JLC does not document its bottom-side convention. The tell is the 12 thumb parts (SK132–SK137, D132–D137), which sit at 205° on the left and 155° on the right; every other bottom part sits at 180° ([checklist](docs/ordering-jlcpcb.md#placement-preview-checklist)). Redraw the proofs with `just pcb-cpl-images`.

<table>
<tr><td align="center" width="50%"><a href="docs/images/cpl-sk-hotswap-socket.svg"><img src="docs/images/cpl-sk-hotswap-socket.svg" alt="CPL proof: hot-swap sockets" width="100%"></a><br><sub>Hot-swap sockets, bottom: 74 placed, 74 pass</sub></td><td align="center" width="50%"><a href="docs/images/cpl-d101-diode-sod123f.svg"><img src="docs/images/cpl-d101-diode-sod123f.svg" alt="CPL proof: matrix diodes" width="100%"></a><br><sub>Matrix diodes, bottom: 74 placed, 74 pass</sub></td></tr>
<tr><td align="center"><a href="docs/images/cpl-u1-rp2040-qfn56.svg"><img src="docs/images/cpl-u1-rp2040-qfn56.svg" alt="CPL proof: U1 RP2040" width="100%"></a><br><sub>U1 RP2040, QFN-56: both halves pass</sub></td><td align="center"><a href="docs/images/cpl-u2-flash-soic8.svg"><img src="docs/images/cpl-u2-flash-soic8.svg" alt="CPL proof: U2 flash" width="100%"></a><br><sub>U2 QSPI flash, SOIC-8: both halves pass</sub></td></tr>
<tr><td align="center"><a href="docs/images/cpl-u3-ldo-sot23-5.svg"><img src="docs/images/cpl-u3-ldo-sot23-5.svg" alt="CPL proof: U3 LDO" width="100%"></a><br><sub>U3 3.3 V LDO, SOT-23-5: both halves pass</sub></td><td align="center"><a href="docs/images/cpl-u4-u5-esd-sot23-6.svg"><img src="docs/images/cpl-u4-u5-esd-sot23-6.svg" alt="CPL proof: U4 and U5 ESD" width="100%"></a><br><sub>U4, U5 ESD arrays: 4 placed, 4 pass</sub></td></tr>
<tr><td align="center"><a href="docs/images/cpl-y1-crystal-3225.svg"><img src="docs/images/cpl-y1-crystal-3225.svg" alt="CPL proof: Y1 crystal" width="100%"></a><br><sub>Y1 12 MHz crystal: both halves pass</sub></td><td align="center"><a href="docs/images/cpl-d1-schottky-sod123.svg"><img src="docs/images/cpl-d1-schottky-sod123.svg" alt="CPL proof: D1 Schottky" width="100%"></a><br><sub>D1 Schottky on the USB power path: both halves pass</sub></td></tr>
<tr><td align="center"><a href="docs/images/cpl-c-0402.svg"><img src="docs/images/cpl-c-0402.svg" alt="CPL proof: 0402 capacitors" width="100%"></a><br><sub>0402 capacitors: 38 placed, 38 pass</sub></td><td align="center"><a href="docs/images/cpl-r-0402.svg"><img src="docs/images/cpl-r-0402.svg" alt="CPL proof: 0402 resistors" width="100%"></a><br><sub>0402 resistors: 26 placed, 26 pass</sub></td></tr>
<tr><td align="center"><a href="docs/images/cpl-f1-ptc-1206.svg"><img src="docs/images/cpl-f1-ptc-1206.svg" alt="CPL proof: F1 PTC" width="100%"></a><br><sub>F1 polyfuse on the TRRS power line: both halves pass</sub></td><td align="center"><a href="docs/images/cpl-j1-usb-c.svg"><img src="docs/images/cpl-j1-usb-c.svg" alt="CPL proof: J1 USB-C" width="100%"></a><br><sub>J1 USB-C, mouth over the back edge: both halves pass</sub></td></tr>
<tr><td align="center"><a href="docs/images/cpl-j2-trrs-pj320d.svg"><img src="docs/images/cpl-j2-trrs-pj320d.svg" alt="CPL proof: J2 TRRS jack" width="100%"></a><br><sub>J2 TRRS jack on the inner bump: both halves pass</sub></td><td align="center"><a href="docs/images/cpl-j3-display-socket.svg"><img src="docs/images/cpl-j3-display-socket.svg" alt="CPL proof: J3 display socket" width="100%"></a><br><sub>J3 display socket: five contacts in five holes</sub></td></tr>
<tr><td align="center" colspan="2"><a href="docs/images/cpl-sw-tact-ts1088.svg"><img src="docs/images/cpl-sw-tact-ts1088.svg" alt="CPL proof: BOOT and RESET tact switches" width="50%"></a><br><sub>SW1, SW2 BOOT and RESET tact switches: 4 placed, 4 pass</sub></td></tr>
</table>

</details>

## 🔧 Build it

> [!WARNING]
> **Plug the host into the LEFT half**, the ZMK central. **Never plug or unplug the TRRS cable while either half is powered**: the jack shorts its contacts against each other while the plug slides in. Unplug USB from both halves first.

The [build guide](docs/buildguide_en.md) has nine steps plus a [troubleshooting table](docs/buildguide_en.md#troubleshooting):

1. 🔍 [**Check the assembled PCBs.**](docs/buildguide_en.md#1-check-the-assembled-pcbs) Break each board out at its 14 mouse-bite tabs and file the nubs flush, because the case leaves only about 0.3 mm around the PCB.
2. ⚡ [**Flash and test the bare boards**](docs/buildguide_en.md#2-flash-and-test-the-bare-boards) before anything is fitted.
3. ✂️ [**Choose the power mode (JP1)**](docs/buildguide_en.md#3-choose-the-power-mode-jp1) before you close the case.
4. 📟 [**Plug in the displays.**](docs/buildguide_en.md#4-plug-in-the-displays) Trim the header pins flush on the glass side, and do not raise the module on an extra spacer.
5. 🖨️ [**Prepare the case**](docs/buildguide_en.md#5-prepare-the-case) by fitting a 3D-printed test top first.
6. 🧱 [**Assemble the case.**](docs/buildguide_en.md#6-assemble-the-case) Clip the 2u stabilisers into the upturned top shell **before** you close it.
7. 🎹 [**Fit the switches and keycaps.**](docs/buildguide_en.md#7-switches-stabilisers-and-keycaps) The stabilisers went in at step 6.
8. 🦵 [**Fit the tent legs**](docs/buildguide_en.md#8-tent-legs): friction washer, leg hub, then the M3 × 12 thumbscrew.
9. 🚀 [**Connect and use.**](docs/buildguide_en.md#9-connect-and-use)

| Power mode | JP1 on both halves | Cables |
|---|---|---|
| 🔗 **Linked power** (default) | bridged | one USB-C, into the left half; the right half runs from the TRRS cable |
| 🔌 **Split-powered** | cut on **both** halves | one USB-C per half; the TRRS cable carries only data and ground |

Tools: a soldering iron (for the display headers, and for a bare J1 shell leg or re-bridging JP1 if needed), flush cutters, tweezers (to short each socket's pads in the bare-board test), a file or sandpaper, a craft knife (to cut JP1), a 1.5 mm hex key or a Phillips driver, a Ø2.5 mm pin for BOOT/RESET, a multimeter, calipers and, optionally, an SWD debug probe for TP8–TP10 ([tools](docs/buildguide_en.md#tools)).

## 💾 Firmware

worxboard runs [ZMK](https://zmk.dev) as a custom HWMv2 board, `worxbend/worxboard`. ZMK is pinned in `firmware/zmk/config/west.yml` to `4dd95d7840eb3d5a3f59bb29fbf1ab054715ef85`, and CI asserts that pin. `zephyr/module.yml` and `build.yaml` sit at the repo root, so ZMK's user-config flow can build the repo directly. Every row compiles locally and in CI. None has run on hardware.

| Artifact | Board | Role | Status |
|---|---|---|---|
| ⭐ `worxboard_left_central` | `worxboard_left//zmk` | central; enumerates on USB; ZMK Studio on | **core** |
| ⭐ `worxboard_right_peripheral` | `worxboard_right//zmk` | peripheral; its USB gives power and flashing only | **core** |
| 🧪 `worxboard_right_central_EXPERIMENTAL` | `worxboard_right//zmk` | the right half as the central (host on the right) | untested on hardware |
| 🧪 `worxboard_left_peripheral_EXPERIMENTAL` | `worxboard_left//zmk` | the left half as the peripheral (pair it with the row above) | untested on hardware |
| 🧪 `worxboard2_left_EXPERIMENTAL`, `worxboard2_right_EXPERIMENTAL` | `worxboard2_*/rp2350a/m33/zmk` | RP2350A target for a future rev B | firmware only, no hardware |

**⚡ Flash it**

1. Download `worxboard-firmware` from a green [firmware run](https://github.com/w0rxbend/worxboard/actions/workflows/firmware.yml).
2. Get the **`RPI-RP2`** drive. A blank board shows it by itself. Otherwise double-tap <kbd>RESET</kbd>, or hold <kbd>BOOT</kbd>, tap <kbd>RESET</kbd> and release <kbd>BOOT</kbd>. On a running keyboard, `&bootloader` on layer 2 does the same.
3. Drag `worxboard_left_central.uf2` onto the left half and `worxboard_right_peripheral.uf2` onto the right half. The right half flashes through its own USB-C. If a board never shows `RPI-RP2`, a debug probe connects to the SWD pads TP8, TP9 and TP10.

**📟 The displays.** Both screens are laid out as 68 × 160 portrait and rotated onto the 160 × 68 panel. The left shows ZMK's built-in status screen, with USB at the top and the active layer at the bottom. The right shows a custom LVGL screen. The sketch below is drawn from the source comment in `worx_status_screen.c`; it is not a capture:

```
┌────────────┐
│  worx      │  ← logo
│  board     │
│ [ CAPS ]   │  ← lit lock: upper case in a 2 px frame
│   num      │  ← unlit: lower case
│   scrl     │
│  wired     │  ← static: the link is TRRS, no BLE or battery
└────────────┘
```

If both screens read upside down on the first board, set `CONFIG_WORXBOARD_DISPLAY_ROTATION_270=y` in `firmware/zmk/config/worxboard.conf`.

**🎛️ ZMK Studio** is enabled on the left central over USB. Unlock it with `&studio_unlock` on layer 2, then edit the keymap live in the [Studio web app](https://zmk.studio). The keymap is [`firmware/zmk/config/worxboard.keymap`](firmware/zmk/config/worxboard.keymap), with 3 layers × 74 bindings ([firmware.md](docs/firmware.md#keymap)). Build locally with `just fw`, or `just fw worxboard_left_central` for one row.

## 🧱 Case

`case/worxboard_case.py` is a build123d port of the [w0rxbend/ergodox](https://github.com/w0rxbend/ergodox) CNC case. Every dimension is a named constant, and the outline and every position come from `layout/`. Status: **modelled, checked and orderable, not yet made** ([case.md](docs/case.md)).

| Spec | Per half |
|---|---|
| 🧩 **Parts** | A CNC top shell with the 1.5 mm plate milled into its key well, a CNC bottom tray, and a separate 3 mm plate spacer (182.7 × 136.6 × 3.0 mm, MJF PA12) with a channel for each stabiliser wire |
| ✨ **Finish** | Aluminium 6061-T6, anodize **with** bead blasting, Strict (or Premium) appearance tier, if JLCCNC's form offers it, so the 2 halves and 6 legs match |
| 📏 **Size, mass** | 192.4 × 165.6 × 17.6 mm, 19.6 mm at the raised display bezel; about 349 g (top 140.6 g, tray 208.1 g) |
| 🔩 **Screws** | 8 × M2.5 countersunk from below into blind threads tapped in the top (no inserts): 6 × M2.5 × 12 at the edge bosses, 2 × M2.5 × 10 under the key well (snug only) |
| 🦶 **Feet** | 4 × Ø10 mm rubber feet in 0.6 mm recesses; an L or R mark engraved under each tray |
| 🦵 **Legs** | 3 mounts, one symmetric 6061 leg (4.9 g) with a TPU 95A foot cap, held by an M3 × 12 thumbscrew and a friction washer ([legs.md](docs/legs.md)); friction only, no click stops ([limits](docs/legs.md#known-limitations)) |
| ✅ **Checks** | `just model` passes every case check, `just corners` applies JLCCNC's radius-for-depth rule, and `just fitcheck` reports 0 mm³ against both PCB STEPs |

> [!WARNING]
> **🔩 Screw lengths matter.** Every thread in the top shell is blind: never use a screw longer than 12 mm in the edge bosses or 10 mm in T1/T5, or it stops before its head seats. The leg thumbscrews are **M3 × 12 without a collar (DIN 653)**, each with its friction washer, or the stock EZ spring thumbscrew once you have measured it. **Never DIN 464**: its collar sits in the leg's counterbore and the screw reaches 8.0 mm past the boss face, into the bottom of the blind thread.

> [!TIP]
> **🖨️ Print a test top first.** 3D-print the top, bottom and spacer of one half, fit an assembled PCB, its display and a few switches, and check the USB-C latch, the TRRS plug, the glass under the bezel, the BOOT/RESET holes and the C6R1 keycap ([before machining](docs/case.md#before-machining)).

**The Z stack**, from the top down ([case.md](docs/case.md#z-stack)):

| Z (mm) | Layer |
|---|---|
| 17.6 – 19.6 | 🔲 display bezel B1, 2.0 mm proud of the top face; the display pocket ceiling is at 18.6, under a 1.0 mm skin with the 26 × 12 mm window |
| 13.6 – 17.6 | ⌨️ key well; the pocket ceiling over the back strip and the TRRS bump is at 14.6 |
| 12.1 – 13.6 | 🔳 1.5 mm switch plate, milled into the top shell |
| 9.1 – 12.1 | 🟧 3 mm plate spacer, floating 0.5 mm above the PCB |
| 7.0 – 8.6 | 🟩 PCB, clamped between bosses in the top and posts in the tray |
| 3.0 – 7.0 | 🟨 cavity for the hot-swap sockets and diodes, about 2.2 mm margin |
| 0 – 3.0 | ⬛ floor of the bottom tray |

<table>
<tr><td align="center" width="50%" valign="top"><a href="case/renders/right_top_underside.png"><img src="case/renders/right_top_underside.png" alt="Underside of the right top shell" width="100%"></a><br><sub>🔳 Right top shell, underside: plate webbing, screw bosses, display pocket</sub></td><td align="center" width="50%" valign="top"><a href="case/renders/right_bottom_tray.png"><img src="case/renders/right_bottom_tray.png" alt="Right bottom tray from above" width="100%"></a><br><sub>⬛ Right bottom tray: the socket cavity and the eight M2.5 screw posts</sub></td></tr>
<tr><td align="center" valign="top"><a href="case/renders/right_back_usb.png"><img src="case/renders/right_back_usb.png" alt="Back wall of the right half with the USB-C notch" width="100%"></a><br><sub>🔌 Back wall of the right half, with the USB-C notch, the BOOT/RESET pin holes and the display bezel</sub></td><td align="center" valign="top"><a href="case/renders/spacer.png"><img src="case/renders/spacer.png" alt="Right plate spacer" width="100%"></a><br><sub>🟧 3D-printed plate spacer, right half. This render predates the stabiliser-wire channels (ORDER-6)</sub></td></tr>
</table>

<table>
<tr><td align="center" width="33%" valign="top"><a href="case/renders/leg.png"><img src="case/renders/leg.png" alt="Custom aluminium tent leg with foot cap" width="260"></a><br><sub>🦵 Custom 6061 tent leg with its TPU foot cap</sub></td><td align="center" width="33%" valign="top"><a href="case/renders/leg_cap_tree.png"><img src="case/renders/leg_cap_tree.png" alt="Tree of eight TPU foot caps" width="260"></a><br><sub>🌲 The TPU print: 8 foot caps on one tree (6 + 2 spares)</sub></td><td align="center" width="33%" valign="top"><a href="case/renders/leg_section.png"><img src="case/renders/leg_section.png" alt="Cross-section through the outer leg mount" width="200"></a><br><sub>📐 Outer leg mount section: M3 tapped pad and Ø10 boss</sub></td></tr>
</table>

<details>
<summary>🔬 Engineering views: case over PCB, and six cross-sections</summary>

<p align="center">
<a href="case/renders/overlay.png"><img src="case/renders/overlay.png" alt="Right-half case outline drawn over the PCB layout" width="720"></a><br><sub>The right-half case over the PCB layout. Red is the case outline, green the PCB, blue the key well, purple the display pocket, magenta the window, yellow the component zones, and maroon circles the screw bosses.</sub>
</p>

<p align="center">
<a href="case/renders/section.png"><img src="case/renders/section.png" alt="Six cross-sections through the right half of the case" width="880"></a><br><sub>Six sections through the right half: a key column, the display column, across the display, the back-edge screws, the USB-C notch and the TRRS row.</sub>
</p>

</details>

The plate DXFs in [`plates/`](plates/) are for cutting an optional separate 1.5 mm FR4 or aluminium plate. The ordered case does not need them, because its plate is milled into the top shell. The inner leg cannot fold flat forwards: it hits the TRRS bump at about 75°, and a plugged-in TRRS cable stops it even earlier.

## 🤖 Generated, not drawn

```mermaid
flowchart TB
    L["layout/<br/>keys · thumbs · display · jacks<br/>holes · outline · zones · pins"] -->|just layout| J["layout.json · layout.svg<br/>kle.json (not committed)"]
    J -->|just pcb-sch / pcb-place| P["KiCad 10 schematics + PCBs<br/>ERC · Freerouting · DRC"]
    P -->|just pcb-production| F["pcb/production<br/>panel gerbers · BOM · CPL<br/>(JLCPCB turnkey)"]
    P -->|just pcb-fab| S["PCB STEP · renders"]
    J -->|just model| C["build123d case<br/>STEP · STL · DXF · plates"]
    S -->|just fitcheck| C
    C -->|just order / production| O["case/production<br/>JLCCNC · JLC3DP"]
    J -->|just fw-layouts| Z["ZMK physical layout<br/>+ matrix transform"]
    Z -->|just fw| U["UF2 firmware<br/>left central · right peripheral"]
    J -->|just docs-gen| D["pinout.md · matrix.md · bom.md"]
    P --> D
    J -->|just site| W["3D viewer<br/>GitHub Pages"]
    P --> W
    C --> W
```

`layout/` is the single source of truth. `just layout-check` runs its tests, regenerates the outputs and fails if a committed `layout.json` or `layout.svg` is stale.

<details>
<summary>🧬 Inside layout/: the modules and what they write</summary>

| Module | Defines |
|---|---|
| `__init__.py` | The right-half KiCad frame; the left half is its mirror, x → 260 − x |
| `keys.py` | Main-block centres from the original ErgoDox PCB, 1u = 19.05 mm, 7 columns per half, the layer-0 legends |
| `thumbs.py` | The 25° six-key cluster around T0 (34.69894, 143.2687), with stabiliser holes on the 2u keys T4 and T5 |
| `display.py` | The 14 × 36 mm module over the old C6R0 cell, the J3 header, the 12 × 26 mm window |
| `jacks.py` | J1 USB-C flush with the back edge, J2 TRRS on the inner bump at y 103.0 |
| `holes.py` | 8 × M2.5 NPTH on the ErgoDox pattern, hole #7 moved to (88.0, 37.135) for the display |
| `outline.py` | The Edge.Cuts polygon from the original ErgoDox outline: jack tabs removed, back edge straight, TRRS bump added |
| `zones.py`, `pins.py` | Top-side component zones and part anchors; the RP2040 GPIO map, a frozen contract identical on both PCBs |

| Output | Committed | Used for |
|---|:-:|---|
| [`layout/build/layout.json`](layout/build/layout.json) (schema 1) | ✅ | PCB placement, the case, the ZMK layout, the generated docs, the viewer |
| [`docs/images/layout.svg`](docs/images/layout.svg) | ✅ | the plan view in [Layout and matrix](#-layout-and-matrix) |
| `build/kle.json` (keyboard-layout-editor) | ❌ git-ignored | only from the `worxboard-layout` CI artifact or a local `just layout` |

`just layout` (`python -m layout.export`) writes all three. On every push, CI fails if the committed `layout.json`/`layout.svg`, the ZMK layout dtsi, the PCB renders, the CPL drawings, `plates/*.dxf`, `pcb/production/` or `case/production/` drift from what the scripts generate. The generated docs are checked by `just docs-check` (run locally or in the manual `pages` workflow). The committed case renders and viewer screenshots are not checked.

</details>

Each PCB goes through this chain. Every stage is a script, run headless in a version-pinned container whose digest is recorded in [`tools/images.lock`](tools/images.lock):

> footprints → schematic → **ERC** → **netcmp** → placement → locked critical routes → Freerouting 2.5.0 → completion router → **DRC + schematic parity** → **checks.py** → KiKit fab → **cpl_check** → panel → **jlc_check** → order package

<details>
<summary>🏗️ The PCB pipeline, stage by stage</summary>

| Stage | Recipe | Container | What runs | Gate |
|---|---|---|---|---|
| 1–6 | `just pcb-sch <side>` | `kicad/kicad:10.0.7` | footprints, `design.py` → schematic, netlist | ERC 0 errors, `netcmp` |
| 7–9 | `just pcb-place <side>` | `kicad/kicad:10.0.7` | placement from `layout.json`, locked critical routes, DSN export | |
| B | `just pcb-route <side>` | Freerouting 2.5.0 on `eclipse-temurin:25-jre` | autoroute | |
| 10–12 | `just pcb-finish <side>` | `kicad/kicad:10.0.7` | SES import, A* completion router with rip-up, GND ties, prune, pin-in-paste, pours, stitching | DRC with schematic parity 0 / 0 / 0, `checks.py` 14 / 14 |
| 13–14 | `just pcb-fab <side>` | `kicad/kicad:10.0.7-full` | KiKit JLC files, renders, Edge DXF, STEP | `netcmp --board`, `cpl_check` |
| P | `just pcb-production <side>` | `kicad/kicad:10.0.7` | KiKit panel and its DRC, panel and bare-board gerbers/BOM/CPL | `cpl_check`, `jlc_check`; `pcb-production-check` compares byte for byte |

Every stage runs with `--network none`; the KiCad stages also set `PYTHONHASHSEED=0` and seed the KIIDs, so the same inputs give byte-identical boards. The scripts are in [`pcb/scripts/`](pcb/scripts/), and [electrical.md](docs/electrical.md#how-the-boards-are-made) walks through them.

</details>

| Gate (per half) | Recorded result |
|---|---|
| 🔌 ERC · 🧬 netcmp | 0 errors · 10 / 10 |
| 📏 DRC with schematic parity | 0 violations · 0 unconnected · 0 parity issues |
| ✅ `checks.py` | 14 / 14 (USB length and skew, crystal, decoupling, U1 GND return, via-in-pad, J1 pin-in-paste, outline and more) |
| 🎯 `cpl_check` | 119 / 119 placements, within 0.033 mm |
| 📦 `jlc_check` | left 11 / 11 with live stock, right 10 / 10 |
| ♻️ Rebuild | a seeded from-scratch rebuild matches the committed board byte for byte (CI `rebuild` job; about 20 min per side) |
| 🚦 Gates | G1 display, G2 TRRS jack and G3 parts all **PASS**; 111 integration tests passed |

These results are recorded in [verification.md](docs/verification.md): the integration tests and CI runs at `f4c95bb` (2026-11-04), and the board figures after the ORDER-1 and ORDER-4 fixes. The badges at the top show the live state of `main`.

## 🧰 Build from source

You need [uv](https://docs.astral.sh/uv/), [just](https://just.systems/) and Docker (for KiCad 10.0.7, Freerouting, the ZMK toolchain and lychee). The firmware checks also call `python3` and a C compiler (`cc`) on the host. `just pcb-route` and `just pcb-all` fetch Freerouting with an authenticated GitHub CLI (`gh`). Python is pinned to 3.12.

```sh
just setup                    # .venv with every Python group (Python 3.12)
just layout-check             # layout tests + no-diff check of the committed contracts
just fw                       # every build.yaml row, in Docker -> build/fw/artifacts/*.uf2
just pcb-drc left             # DRC gate (schematic parity, 0 unconnected) + scripted checks
just pcb-fab left             # KiKit fab files, CPL check, renders, DXF, STEP -> build/left/
just pcb-production left      # the JLC order package -> pcb/production/left/ (panel, BOM, CPL)
just pcb-stock left 5         # package checks + live JLC stock for 5 + 5 boards (network)
just pcb-all                  # both PCBs from scratch, schematic to fab (~20 min per side)
just model order production   # case STEP/STL/DXF -> order package -> case/production/
just fitcheck                 # case vs build/<side>/worxboard-<side>.step: 0 mm3
just docs-check               # generated docs up to date + link check
just site                     # microsite into _site/ (just site-serve serves it on :8000)
just all                      # layout-check -> fw -> pcb-all -> model -> site
just --list                   # every recipe
```

The PCB stages run in `kicad/kicad:10.0.7` (`-full` for STEP and renders) with `--network none`; `just pcb-deps` installs their pinned Python packages into `pcb/.tools/` once.

<details>
<summary>📜 All 42 recipes, by area</summary>

Recipes come from each area's own file: the root [`justfile`](justfile), [`layout/layout.just`](layout/layout.just), [`firmware/firmware.just`](firmware/firmware.just), [`pcb/pcb.just`](pcb/pcb.just), [`case/case.just`](case/case.just) and [`site/site.just`](site/site.just).

| Area | Recipes | What they do, in the same order |
|---|---|---|
| 🏠 root | `default` · `setup` · `all` · `clean` | list the recipes · create `.venv` (Python 3.12) with the layout, case and dev groups · the full pipeline from a clean clone: layout-check, fw, pcb-all, model, site · remove Python caches and build outputs |
| 🧬 layout | `layout` · `layout-check` | regenerate `layout.json`, `layout.svg` and `build/kle.json` · tests, then regenerate and require no diff in the committed outputs |
| 💾 firmware | `fw [artifacts…]` · `fw-west` · `fw-clean` | build every `build.yaml` row, or the named ones, in Docker · create or refresh the west workspace (`west update` only when `west.yml` changed) · remove the firmware build outputs, keep the west workspace |
| 💾 firmware checks | `fw-layouts` / `fw-layouts-check` · `fw-keymap-check` · `fw-rotate-check` · `fw-check` | regenerate the physical-layout and transform dtsi, or fail if it is stale · 3 layers × 74 bindings, base layer equal to the `layout.json` legends · host test of the displays' portrait-to-panel pixel map · post-build: rotation on both core rows; on the right, no BLE/battery symbols and the flash budget |
| 🟩 pcb stages | `pcb-deps` · `pcb-sch <side>` / `pcb-sch-all` · `pcb-place <side>` · `pcb-route <side>` · `pcb-finish <side>` | install the pinned container Python deps once · stages 1–6: footprints, schematic, ERC, netlist, netcmp (`-all` also requires no diff) · stages 7–9: placement, locked critical routes, DSN · Freerouting autoroute (container B) · SES import, stitching, zone fill, DRC gate, scripted checks |
| 🟩 pcb outputs | `pcb-drc <side>` · `pcb-fab <side>` · `pcb-render-check <side>` · `pcb <side>` / `pcb-all` | DRC gate and scripted checks on the committed board · stages 13–14: JLC files, renders, Edge DXF, STEP · after `pcb-fab`, the committed renders are current (pixel compare) · every stage for one side, or both |
| 🟩 pcb order | `pcb-package <side>` · `pcb-production <side>` · `pcb-production-check <side>` · `pcb-cpl-images` · `pcb-stock <side> [boards]` | stage P into `build/<side>/production` · stage P, then make it the committed `pcb/production/<side>/` · stage P, then require a byte-for-byte match · redraw `docs/images/cpl-*.svg` · live JLC stock for the committed package (network; run it on order day) |
| 🧱 case | `model` · `fitcheck` · `corners` · `renders` | STEP / STL of both halves, legs, fit-check DXFs and `plates/*.dxf`, failing on any case check · interference with the PCB STEPs (or the layout zones until they exist) · every internal corner meets JLCCNC's radius-for-depth rule (needs model) · regenerate the PNGs in `case/renders` (needs model) |
| 🧱 case order | `order` · `production` / `production-check` | the order package in `case/exports/order` (needs model) · copy it into `case/production`, or fail if that differs (needs model + order) |
| 📚 docs and site | `docs-gen` · `docs-check` · `docs-links [args]` · `site` / `site-serve` | regenerate `docs/pinout.md`, `docs/matrix.md` and the BOM tables in `docs/bom.md` · generated docs up to date, then every local link and anchor resolves · link check with lychee in Docker (`--offline` skips external URLs) · build the microsite into `_site/`, or build it and serve it on port 8000 |

Pinned versions: KiCad `10.0.7`, Freerouting `2.5.0`, kikit `1.8.1`, kicad-sch-api `0.5.6`, shapely `2.2.0`, build123d `0.13.0`, lychee `0.24.2`; image digests are in [`tools/images.lock`](tools/images.lock).

</details>

## 📦 Get the files

These files are committed, so you can open them straight from the repo. GitHub shows the PDFs and the STLs in the browser:

| What | Files |
|---|---|
| 🟩 KiCad 10 projects | [`pcb/left/`](pcb/left/) · [`pcb/right/`](pcb/right/) (`.kicad_pro`, `.kicad_sch`, `.kicad_pcb`) |
| 🏭 JLCPCB order zips | [left](pcb/production/left/worxboard-left-jlc-order.zip) · [right](pcb/production/right/worxboard-right-jlc-order.zip) |
| 📐 Machining drawings (PDF) | [left top](case/production/jlccnc/worxboard_left_top.pdf) · [right top](case/production/jlccnc/worxboard_right_top.pdf) · [left tray](case/production/jlccnc/worxboard_left_bottom.pdf) · [right tray](case/production/jlccnc/worxboard_right_bottom.pdf) · [leg](case/production/jlccnc/worxboard_leg.pdf) |
| 🧊 CAD (STEP) | the `.step` files next to those PDFs in [`case/production/jlccnc/`](case/production/jlccnc/) |
| 🖨️ Printable STLs | [left spacer](case/production/jlc3dp/worxboard_left_spacer.stl) · [right spacer](case/production/jlc3dp/worxboard_right_spacer.stl) · [foot-cap tree](case/production/jlc3dp/worxboard_leg_cap_tree.stl) |
| ✂️ Plate DXFs | [left](plates/worxboard-plate-left.dxf) · [right](plates/worxboard-plate-right.dxf) |
| 🧬 Layout and keymap | [`layout.json`](layout/build/layout.json) · [`worxboard.keymap`](firmware/zmk/config/worxboard.keymap) |

The top-shell and tray STLs are not committed (`case/exports/` is git-ignored); they come from the `worxboard-case` artifact or `just model`.

The layout, firmware, pcb and case workflows run on every push to `main`, on pull requests and on `v*` tags. Download the artifacts of a green run:

| Workflow | Artifact | Contents |
|---|---|---|
| [layout](https://github.com/w0rxbend/worxboard/actions/workflows/layout.yml) | `worxboard-layout` | `layout.json`, `layout.svg` and `kle.json`. The KLE file is not committed, so this artifact (or `just layout`) is the only way to get it |
| [firmware](https://github.com/w0rxbend/worxboard/actions/workflows/firmware.yml) | `worxboard-firmware` | six `.uf2` files: `worxboard_left_central`, `worxboard_right_peripheral` and the four `*_EXPERIMENTAL` rows ([firmware.md](docs/firmware.md)) |
| [pcb](https://github.com/w0rxbend/worxboard/actions/workflows/pcb.yml) | `worxboard-pcb-left`, `worxboard-pcb-right` | KiKit's raw bare-board fab files, the board STEP, the Edge.Cuts DXF, the DRC report and the renders. To order, use the committed [`pcb/production/`](pcb/production/) instead ([ordering-jlcpcb.md](docs/ordering-jlcpcb.md)) |
| [pcb](https://github.com/w0rxbend/worxboard/actions/workflows/pcb.yml) | `worxboard-pcb-production-left`, `worxboard-pcb-production-right` | the rebuilt order package, which must equal `pcb/production/<side>/` |
| [pcb](https://github.com/w0rxbend/worxboard/actions/workflows/pcb.yml) | `worxboard-pcb-erc`, `worxboard-pcb-rebuild-*` | ERC reports and netlists; the from-scratch rebuilds and their Freerouting logs |
| [case](https://github.com/w0rxbend/worxboard/actions/workflows/case.yml) | `worxboard-case` | case STEP/STL/DXF, plates, renders, the build report and the order package, also committed in [`case/production/`](case/production/README.md) ([case.md](docs/case.md)) |

[`release.yml`](.github/workflows/release.yml) publishes a GitHub pre-release when a `v*` tag is pushed. It attaches the PCB and case zips, one `.uf2` per `build.yaml` row and `SHA256SUMS.txt`. Hardware releases are meant to be tagged `v*-revA`. **No tag or release exists yet.**

<details>
<summary>⚙️ The six workflows: triggers, jobs and artifacts</summary>

| Workflow | Runs on | Jobs | Artifacts |
|---|---|---|---|
| [layout](https://github.com/w0rxbend/worxboard/actions/workflows/layout.yml) | push to `main`, `v*` tags, PRs, manual | `uv sync --locked`, `just layout-check` | `worxboard-layout` |
| [firmware](https://github.com/w0rxbend/worxboard/actions/workflows/firmware.yml) | same | ZMK SHA pin, dtsi regen, keymap, rotation host test → one build per `build.yaml` row (`fw_check.py` on the core rows) → merge | `worxboard-firmware` |
| [pcb](https://github.com/w0rxbend/worxboard/actions/workflows/pcb.yml) | same | schematics · board × 2 (DRC, fab, render compare) · order package × 2 · CPL overlays · case fit · rebuild × 2 | `worxboard-pcb-*` |
| [case](https://github.com/w0rxbend/worxboard/actions/workflows/case.yml) | same | model, plates no-diff, fitcheck, corners, renders, order, production-check | `worxboard-case` |
| [pages](.github/workflows/pages.yml) | manual only | generated-docs check, offline link check, optional case model, `just site`, deploy | the [GitHub Pages site](https://w0rxbend.github.io/worxboard/) |
| [release](.github/workflows/release.yml) | `v*` tag only | firmware, pcb × 2, case, integration tests, GitHub pre-release | no tag exists yet |

</details>

## 🐛 Known open issues

- 🧪 **Not built yet.** No board has been made. The displays, the wired split, the forwarding of the lock indicators, the role-swap firmware and the XOSC start-up with the new crystal are untested on hardware ([verification.md](docs/verification.md#not-verified-until-a-board-is-built)). The J2 contact naming and the case fit (USB-C and TRRS plug seating, the BOOT/RESET pin holes, C6R1 keycap clearance) also wait for a real board; check the fit on a 3D-printed test top.
- 🔄 **Display orientation.** Both screens are laid out portrait and turned by the firmware. Which panel end is pixel 0 comes from ZMK's code and the vendor's images, not from a datasheet. If the screens read upside down, set `CONFIG_WORXBOARD_DISPLAY_ROTATION_270=y` ([firmware.md](docs/firmware.md#known-issues)).
- 🎯 **JLC placement.** Every CPL placement is proven against JLC's own footprints, but JLC does not document its bottom-side convention. Check the sockets and diodes in JLC's placement preview ([ordering-jlcpcb.md](docs/ordering-jlcpcb.md#placement-preview-checklist)). The hot-swap socket C41430893 is a second-source part, and nobody has reported JLC assembling it yet.
- 📦 **Stock** moves daily. Re-check it on the day you order ([Order it](#-order-it)). J3 (C27985230) has no drop-in alternate that fits the case ([alternates](docs/ordering-jlcpcb.md#if-a-part-is-out-of-stock)).
- 🧊 **3D models.** KiCad has no model for the USB-C, the TRRS jack or the hot-swap socket, so the board STEP lacks those bodies. The case fit check adds their layout envelopes instead.
- 📤 **Release packaging.** [`release.yml`](.github/workflows/release.yml) still packs KiKit's raw fab files, not `pcb/production/` (deviation PKG-4).
- 🐳 **Build image.** The firmware builds in the floating `zmkfirmware/zmk-build-arm:stable` image, as ZMK's own workflow does; only the ZMK source is pinned ([firmware.md](docs/firmware.md#known-issues)).
- 💾 **RP2350A target** (`worxboard2`): settings do not persist, because the flash map and NVS are forced off.
- 🧠 **LVGL heap.** Heap use has not been measured on hardware. On a 64-bit host the right screen peaks at about 5.2 KB of its 8 KB heap, and the left at about 4.7 KB against ZMK's 4 KB default.
- 🖼️ **Stale previews.** The viewer screenshots predate case revision A3, and `spacer.png` predates the stabiliser-wire channels. CI re-renders the case into the `worxboard-case` artifact.
- 📜 **Licence split** ([below](#-license)): it still needs the maintainer's confirmation.

## 🔭 Future work

Listed in [firmware.md](docs/firmware.md#future-work):

- 🧠 RP2350A hardware for a rev B (needs the A4 stepping). The `worxboard2` firmware rows already build.
- 🔗 TRRS detect on GP21 (TP11) and a runtime role swap.
- 🌈 RGB on GP22, encoders, a TFT display on TP1–TP3.

## 🌳 Repository layout

<details>
<summary>📂 Show the tree</summary>

```
layout/              single source of truth; layout/build/layout.json is the committed contract
pcb/                 KiCad 10 projects per half (left/, right/), worxboard symbol/footprint
                     library (lib/), generator scripts (scripts/: design, schematic, placement,
                     routing, checks, fab, panel), the JLC turnkey order packages (production/)
firmware/zmk/        ZMK board module (RP2040 worxboard, RP2350A worxboard2), keymap,
                     custom screen, scripts
zephyr/module.yml    Zephyr module entry point for the ZMK build
build.yaml           ZMK build matrix
case/                build123d case, drawings, fit check, overlay, renders/, the JLCCNC/JLC3DP
                     order package (production/; exports/ is git-ignored)
plates/              plate DXFs, for cutting an optional separate 1.5 mm plate
docs/                build guide, BOM, electrical, pinout, matrix, ordering, case, legs,
                     firmware, spec; images/ (PCB renders, layout.svg, viewer screenshots,
                     CPL proofs)
site/                microsite: web/ (three.js viewer), build_site.py, gen_docs.py, pcbdata.py
tests/integration/   integration tests: pins, gates, stock, stabilisers, release assembly
tools/               container helpers and pinned image digests
.github/workflows/   layout, firmware, pcb, case (push, PR, tags); pages (manual); release (v* tags)
```

</details>

## 📚 Documentation

| | Document | Contents |
|---|---|---|
| 🔧 **Build** | [buildguide_en.md](docs/buildguide_en.md) | board check, bare-board flashing, JP1 power modes, displays, assembly, troubleshooting |
| | [shopping-list.md](docs/shopping-list.md) | the four orders and every off-board part for one keyboard |
| | [ordering-jlcpcb.md](docs/ordering-jlcpcb.md) | the turnkey JLCPCB order step by step: form fields, placement checks, alternates, cost estimate |
| | [bom.md](docs/bom.md) | bill of materials with LCSC numbers (generated), JLC fees, the ordering gates |
| 📖 **Reference** | [electrical.md](docs/electrical.md) | power path, TRRS link, USB-C, MCU support circuit, display, reference designators, PCB rules and pipeline |
| | [pinout.md](docs/pinout.md) | RP2040 GPIO map, TRRS contacts, display header, part positions, holes (generated) |
| | [matrix.md](docs/matrix.md) | key matrix per half, sockets and diodes, the ZMK 6 × 14 transform, keymap order (generated) |
| | [firmware.md](docs/firmware.md) | ZMK builds, flashing, host behaviour, keymap, displays, known issues |
| | [case.md](docs/case.md) | the Z stack, changes from the ErgoDox case, the order package, fasteners, previews |
| | [legs.md](docs/legs.md) | tent/tilt legs: mounts, positions, the custom leg |
| 🧪 **Design and QA** | [design.md](docs/design.md) | the frozen rev A specification |
| | [deviations.md](docs/deviations.md) | every change from the specification, by work-stream |
| | [verification.md](docs/verification.md) | integration results, CI, the order-package checks, gates G1–G3, and what only a built board can confirm |
| | [sources.md](docs/sources.md) | prior art, tools and attribution |

Order sheets: [`pcb/production/left/README.md`](pcb/production/left/README.md), [`pcb/production/right/README.md`](pcb/production/right/README.md), [`case/production/README.md`](case/production/README.md) and its two `ORDER_NOTES.md`. History is in [`CHANGELOG.md`](CHANGELOG.md). `site/gen_docs.py` generates `docs/pinout.md`, `docs/matrix.md` and the BOM tables in `docs/bom.md` from `layout/build/layout.json`, `pcb/scripts/design.py` and the committed boards. Run `just docs-gen` after a layout or PCB change; `just docs-check` fails if they are stale.

## 🙏 Credits

- ⌨️ [ErgoDox](https://www.ergodox.io/) by Dominic Beauchamp, and the original PCB [bishboria/ErgoDox](https://github.com/bishboria/ErgoDox) by Fredrik Atmer and contributors: switch centres, thumb cluster, holes and outline.
- 🦵 [ErgoDox EZ](https://ergodox-ez.com) by ZSA: the product this keyboard follows (layout, tent legs, default keymap). Not affiliated.
- 🧠 [foostan/crkbd](https://github.com/foostan/crkbd) (Corne v4): the RP2040 support circuit, the BOM parts and the build-guide format.
- 🧱 [w0rxbend/ergodox](https://github.com/w0rxbend/ergodox) v0.6.1: the CNC case, legs, drawings and the three.js viewer.
- 💾 [ZMK](https://github.com/zmkfirmware/zmk) and the [QMK](https://github.com/qmk/qmk_firmware) `ergodox_ez` default keymap.
- 🛠️ KiCad, Freerouting, KiKit, build123d, three.js.

Full list: [docs/sources.md](docs/sources.md); licences: [THIRD_PARTY.md](THIRD_PARTY.md).

## 📜 License

- Code (`layout/`, `pcb/scripts/`, `case/*.py`, `firmware/`, `tools/`, `site/`): [GPL-3.0](LICENSE).
- Hardware (`pcb/` KiCad files and libraries, case geometry outputs, `plates/`, `docs/`): [CERN-OHL-S-2.0](LICENSE-HARDWARE). **Maintainer to confirm** this split before the first hardware tag.
- Per-file headers under `firmware/zmk/`: the board files, keymaps and C sources say `SPDX-License-Identifier: MIT`, and the Python scripts say GPL-3.0-or-later. The confirmation above covers them too.
- Third-party material: [`THIRD_PARTY.md`](THIRD_PARTY.md); attribution in [docs/sources.md](docs/sources.md).

The key and mounting-hole coordinates come from the original ErgoDox PCB by Fredrik Atmer and contributors (GPL-3.0). ErgoDox EZ is a product of ZSA Technology Labs and nice!view of Nice Keyboards; Cherry MX, Kailh, Raspberry Pi and JLCPCB are trademarks of their owners. This project is not affiliated with or endorsed by any of them.

<div align="center">

<a href="#-contents">⬆️ Back to contents</a>

<sub>⌨️ worxboard rev A · designed, checked and orderable, not yet built · KiCad 10 · build123d · ZMK</sub>

</div>
