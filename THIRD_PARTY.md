# Third-party material

worxboard is licensed under the GPL-3.0 (code: [`LICENSE`](LICENSE)) and the CERN-OHL-S-2.0
(hardware: [`LICENSE-HARDWARE`](LICENSE-HARDWARE)). The material below comes from other projects,
under their own licences. Nothing here is copied wholesale unless it says so.

| Project | Licence | Used for | Where |
|---|---|---|---|
| [bishboria/ErgoDox](https://github.com/bishboria/ErgoDox), original ErgoDox PCB (Fredrik Atmer and contributors) | GPL-3.0 | Switch centres, thumb cluster, mounting-hole pattern and Edge.Cuts vertices (numbers only) | `layout/keys.py`, `layout/thumbs.py`, `layout/holes.py`, `layout/outline.py` |
| [w0rxbend/ergodox](https://github.com/w0rxbend/ergodox) v0.6.1, ErgoDox EZ CNC case | GPL-3.0 | Base of the build123d case, drawings, overlay, CI and microsite | `case/`, `site/` |
| [QMK `ergodox_ez` default keymap](https://github.com/qmk/qmk_firmware) | GPL-2.0-or-later | Key legends (layer 0) and layer layout | `layout/keys.py`, `firmware/zmk/config/worxboard.keymap` |
| [ZMK Firmware](https://github.com/zmkfirmware/zmk) | MIT | Firmware framework, board/shield conventions and `build-user-config.yml` CI | `firmware/`, `zephyr/`, `build.yaml` |
| [foostan/crkbd](https://github.com/foostan/crkbd) (Corne v4) | MIT | Electrical reference (RP2040 support circuit and BOM parts), repo structure | `pcb/`, `docs/` |
| [ceoloide/ergogen-footprints](https://github.com/ceoloide/ergogen-footprints) `switch_mx` | MIT | Cross-check of the Kailh MX hot-swap footprint geometry | `pcb/scripts/gen_footprints.py` |
| [KiCad libraries](https://gitlab.com/kicad/libraries) | CC-BY-SA-4.0 with the KiCad library exception | Stock symbols, footprints and 3D models | referenced by `pcb/` |
| [Freerouting](https://github.com/freerouting/freerouting) | GPL-3.0 | Autorouter, run as a tool (not distributed) | `tools/fetch_freerouting.sh` |
| [KiKit](https://github.com/yaqwsx/KiKit) | MIT | JLCPCB fabrication outputs, run as a tool | `pcb/` |
| [build123d](https://github.com/gumyr/build123d) | Apache-2.0 | CAD kernel for the case | `case/` |
| [Shapely](https://github.com/shapely/shapely) | BSD-3-Clause | 2D geometry in `layout/` and `case/` | `layout/`, `case/` |
| [ezdxf](https://github.com/mozman/ezdxf) | MIT | DXF export of plates and fit-check drawings | `case/` |

Trademarks (ErgoDox EZ, nice!view, Cherry MX, Kailh) belong to their owners. worxboard is not
affiliated with any of them.
