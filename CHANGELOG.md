# Changelog

This project uses [Semantic Versioning](https://semver.org/). Hardware releases are tagged
`v<version>-revA` and publish gerbers, BOM/CPL, UF2 firmware and case files.

## [Unreleased]

### Added

- `layout/`, the single source of truth for both halves:
  - 37 keys per half from the original ErgoDox PCB, with the 25° thumb cluster
  - the nice!view display in the old C6R0 slot
  - USB-C and TRRS anchors, the mounting holes (#7 moved), the PCB outline and the top-side zones
  - the frozen RP2040 GPIO map (`pins.py`)
- `python -m layout.export` writes `layout/build/layout.json`, `docs/images/layout.svg` and
  `build/kle.json`. `just layout-check` runs the WS0 acceptance tests and the no-diff check.
- Root `justfile` that imports each stream's `*.just`. `pyproject.toml` and `uv.lock`
  (Python 3.12; groups `layout`, `case`, `dev`).
- `tools/kicad_env.sh`, `tools/fetch_freerouting.sh` and `tools/images.lock`.
- CI: `.github/workflows/layout.yml`.
- `LICENSE-HARDWARE` (CERN-OHL-S-2.0), `THIRD_PARTY.md` and `docs/deviations.md`.
- Firmware: a ZMK module for the on-board RP2040 halves (`zephyr/module.yml`, `firmware/zmk/`) with
  wired split over TRRS, the right half's reversed `col-gpios` and `col-offset`, a 74-key 3-layer
  keymap, the physical layout generated from `layout.json`, the nice!view on PIO1 SPI and a custom
  right-half screen. `build.yaml` builds six UF2s: left central, right peripheral, two
  `_EXPERIMENTAL` role swaps and two `_EXPERIMENTAL` RP2350A (`worxboard2`) rows. `just fw`, CI
  `firmware.yml`.
- PCB: both halves generated headless in KiCad 10 (`pcb/`): vendored MX hot-swap and 2u stabiliser
  footprints, schematics with netlist checks against `design.py`, seeded placement, Freerouting and a
  completion router, DRC with schematic parity at 0 violations / 0 unconnected, and JLCPCB gerbers,
  BOM, CPL, STEP, Edge DXF and renders. `just pcb-all`, CI `pcb.yml` (it also rebuilds both boards
  from scratch and requires them to equal the committed ones).
- Case and plates: a build123d port of the ErgoDox CNC case (`case/`) with the display pocket and
  window, USB-C on both halves, the TRRS side notch, the tent legs, the fit check against the PCB
  STEPs and the plate DXFs (`plates/`). `just model`, `just fitcheck`, CI `case.yml`.
- Docs and microsite: build guide, generated BOM, pinout and matrix, electrical, ordering, case,
  legs and firmware pages (`docs/`), and a three.js viewer (`site/`). `pages.yml` deploys by hand.
- Integration (`tests/integration/`): every switch is traced from its PCB socket and diode through
  the RP2040 GPIOs to its firmware matrix position and keymap slot, plus the TRRS TX/RX crossover,
  the display header and the RP2350A pinout, against the committed boards, the WS2 netlists and the
  built `zephyr.dts` files. Gates G1 and G2 are checked against the part drawings.
- `tests/integration/release.py` packs the `just all` outputs into `dist/`; `stock.py` checks every
  LCSC line against JLCPCB stock for an order (gate G3).
- `.github/workflows/release.yml`: on a `v*` tag, builds the firmware, both PCBs and the case,
  runs the integration tests and publishes a GitHub pre-release with the per-half PCB zips
  (gerbers, BOM, CPL, STEP), the six UF2s, the case STEP/STL zips and `SHA256SUMS.txt`.
- `docs/verification.md`: integration results, the clean-clone `just all` run and gates G1–G3.

### Changed

- `.gitignore` no longer ignores `/zephyr/` (the ZMK module lives at `zephyr/module.yml`). It now
  ignores `/build/`, `pcb/.tools/`, `case/exports/`, and `pcb/production/` outside hardware tags.

### Fixed

Post-integration review (deviations REVIEW-FIX-1 to -8):

- Firmware: the display's PIO SPI no longer takes GP0 (UART0 TX, the wired-split link) on its first
  transfer; `nice_view_spi` names MOSI as its `miso-gpios`. The integration tests now fail if a PIO
  SPI pin lands on a UART, row or column pin. The right-central build has a USB product name again.
- PCB, decoupling: every RP2040 supply cap sits at the exit of the pins it serves and is joined to it
  and to its own GND via with locked copper; DVDD pin 23 has its own 100 nF and VREG_VOUT's 1 µF sits
  at the 1V1 exit. On the left half seven 3V3 caps had reached U1 only through a 75–86 mm detour.
  `checks.py` now measures the pin-to-cap copper paths.
- PCB: no via in an SMD pad any more (router, session import and a check); a B.Cu keepout under the
  crystal, with R7 beside it and a short locked XOUT; the left stabiliser holes face the same way as
  the case cut-outs; JLC CPL rotation corrections for the QFN, SOIC, SOT-23 and USB-C parts.
- Case: Cherry-spec stabiliser cut-outs on the PCB holes' side (left = mirror of right, checked to
  0.005 mm); the display window is centred on the LCD viewing area (G1 open item 3), which also
  widens the skin bar to the C6R1 well from 1.0 to 4.5 mm; the fit check covers the USB-C, TRRS,
  display and socket envelopes the PCB STEP has no body for; drawing and order-note feature ids
  match the PCB parts (J1 USB-C, J2 TRRS).
- Docs: the display-socket build steps (pin-1 end per half, a 6.0–6.3 mm socket stack), the TRRS
  plug-head limit, the VBUS back-drive note, the leg bearing faces and fold limit, and the README,
  BOM, case, ordering and microsite status brought in line with verification.md, which now records
  the re-checks of these fixes.

### Known issues

- Not built or tested on hardware.
- Gates G1–G3 fail and block ordering ([verification.md](docs/verification.md)): the display socket
  J3 has pin 1 at the wrong end and the module and window are offset from the drawing (G1); the
  PJ-320D body is longer than the case allows for (G2); the hot-swap socket C2803348 is discontinued
  (G3).
