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
| [nice!view](https://nicekeyboards.com/nice-view/) by Nice Keyboards | The display module format (Sharp LS011B7DH03 memory LCD) and its pinout |
| [KiCad](https://www.kicad.org/) and its [libraries](https://gitlab.com/kicad/libraries) (CC-BY-SA-4.0 with the library exception) | Schematic and PCB tools; stock symbols, footprints and 3D models |
| [Freerouting](https://github.com/freerouting/freerouting) (GPL-3.0) | Autorouter, run as a tool |
| [KiKit](https://github.com/yaqwsx/KiKit) (MIT) | JLCPCB fabrication outputs |

## Firmware

| Source | What it gave this project |
|---|---|
| [ZMK Firmware](https://github.com/zmkfirmware/zmk) (MIT) | The firmware, wired split, ZMK Studio, the board conventions and the `build-user-config.yml` CI workflow |
| [ZMK documentation](https://zmk.dev/docs) | New-board (HWMv2) guide, physical layouts and the `sharp,ls0xx` display setup |
| [Zephyr RTOS](https://www.zephyrproject.org/) (Apache-2.0) | RP2040 support, the PIO SPI driver |

## Tools

| Source | Use |
|---|---|
| [build123d](https://github.com/gumyr/build123d) (Apache-2.0) | CAD kernel for the case |
| [Shapely](https://github.com/shapely/shapely) (BSD-3-Clause) | 2D geometry in `layout/` and `case/` |
| [ezdxf](https://github.com/mozman/ezdxf) (MIT) | DXF export |
| [three.js](https://threejs.org/) (MIT) | The microsite's 3D viewer |
| [lychee](https://github.com/lycheeverse/lychee) | Link checking of these docs |

Trademarks (ErgoDox EZ, nice!view, Cherry MX, Kailh, Raspberry Pi) belong to their owners.
