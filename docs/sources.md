# Sources, prior art and attribution

worxboard builds on the work below. The licence terms and where each piece is used are in
[`THIRD_PARTY.md`](../THIRD_PARTY.md).

## Layout and case

| Source | What it gave this project |
|---|---|
| [ErgoDox](https://www.ergodox.io/) by Dominic Beauchamp, and the original PCB [bishboria/ErgoDox](https://github.com/bishboria/ErgoDox) (Fredrik Atmer and contributors, GPL-3.0) | Switch centres, the 25° thumb cluster, the mounting-hole pattern and the Edge.Cuts vertices of the outline (numbers only) |
| [ErgoDox EZ](https://ergodox-ez.com) by ZSA Technology Labs, and [zsa/docs](https://github.com/zsa/docs) | The product this keyboard follows: layout, tent legs, the default keymap. worxboard is not affiliated with or endorsed by ZSA. |
| [QMK `ergodox_ez` default keymap](https://github.com/qmk/qmk_firmware) (GPL-2.0-or-later) | Key legends of layer 0 and the layer layout |
| [w0rxbend/ergodox](https://github.com/w0rxbend/ergodox) v0.6.1 (GPL-3.0) | The build123d CNC case, its legs, drawings, CI layout and the three.js microsite this repo ports |
| [rothgar/ergodox-ez-tent-kit](https://github.com/rothgar/ergodox-ez-tent-kit) | Prior art and tooth count of the EZ tent legs |

## Electronics

| Source | What it gave this project |
|---|---|
| [foostan/crkbd](https://github.com/foostan/crkbd), Corne v4 (MIT) | The electrical reference: RP2040 support circuit and production BOM part numbers (marked [C] in [bom.md](bom.md)), the repo structure and the build-guide format. The ground-stitching mitigation answers [crkbd#265](https://github.com/foostan/crkbd/issues/265). |
| [Raspberry Pi: Hardware design with RP2040](https://datasheets.raspberrypi.com/rp2040/hardware-design-with-rp2040.pdf) and the [RP2040 datasheet](https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf) | Crystal, flash, decoupling and USB recommendations |
| [ceoloide/ergogen-footprints](https://github.com/ceoloide/ergogen-footprints) `switch_mx` (MIT) | Cross-check of the Kailh MX hot-swap footprint geometry |
| [nice!view](https://nicekeyboards.com/nice-view/) by Nice Keyboards | The rev A display format before DISP-1 (Sharp LS011B7DH03 memory LCD) and its pinout |
| Sellers' listings of the 0.91" 128 × 32 SSD1306 I2C OLED module (AliExpress, DFRobot and others) | The display since DISP-1: its size, header and pin orders (G1) |
| [KiCad](https://www.kicad.org/) 10.0.7 and its [libraries](https://gitlab.com/kicad/libraries) (CC-BY-SA-4.0 with the library exception) | Schematic and PCB tools (`kicad-cli`, the `pcbnew` Python API, the official `kicad/kicad` Docker images); stock symbols, footprints and 3D models |
| [kicad-sch-api](https://github.com/circuit-synth/kicad-sch-api) 0.5.6 (MIT) | Writes the schematics from `pcb/scripts/design.py` |
| [Freerouting](https://github.com/freerouting/freerouting) 2.5.0 (GPL-3.0) | Autorouter, run as a tool in an `eclipse-temurin` container |
| [KiKit](https://github.com/yaqwsx/KiKit) 1.8.1 (MIT) | JLCPCB fabrication outputs (gerbers, BOM, CPL) |
| [JLCPCB](https://jlcpcb.com) / [LCSC](https://www.lcsc.com) part pages | Part numbers, stock and basic/extended status in [bom.md](bom.md) |

## Firmware

| Source | What it gave this project |
|---|---|
| [ZMK Firmware](https://github.com/zmkfirmware/zmk) (MIT) | The firmware, wired split, ZMK Studio, the board conventions, the `zmk-build-arm` build image and the `build-user-config.yml` workflow that the firmware CI mirrors |
| [ZMK documentation](https://zmk.dev/docs) | New-board (HWMv2) guide, physical layouts and the display setup (the 128 × 32 SSD1306 settings of its Corne board) |
| [Zephyr RTOS](https://www.zephyrproject.org/) (Apache-2.0) | RP2040 support, the I2C and `solomon,ssd1306fb` display drivers and LVGL |

## Tools

| Source | Use |
|---|---|
| [build123d](https://github.com/gumyr/build123d) (Apache-2.0) | CAD kernel for the case |
| [Shapely](https://github.com/shapely/shapely) (BSD-3-Clause) | 2D geometry in `layout/` and `case/` |
| [ezdxf](https://github.com/mozman/ezdxf) (MIT) | DXF export |
| [three.js](https://threejs.org/) (MIT) | The microsite's 3D viewer |
| [NumPy](https://numpy.org/) (BSD-3-Clause) | STL statistics in the site builder |
| [trimesh](https://github.com/mikedh/trimesh), [Matplotlib](https://matplotlib.org/), [Pillow](https://python-pillow.org/) | Case render, section and overlay images (`just renders`) |
| [uv](https://docs.astral.sh/uv/) and [just](https://just.systems/) | Python environments and the build recipes |
| [lychee](https://github.com/lycheeverse/lychee) | Link checking of these docs |

Trademarks (ErgoDox EZ, nice!view, Cherry MX, Kailh, Raspberry Pi, JLCPCB) belong to their owners.
worxboard is not affiliated with or endorsed by any of them.
