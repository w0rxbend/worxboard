# Changelog

This project uses [Semantic Versioning](https://semver.org/). Hardware releases are tagged with the
board revision, `v<version>-rev<X>` (rev B is the current design), and publish gerbers, BOM/CPL, UF2
firmware and case files.

## [Unreleased]

Rev B is the order revision after the rev A pre-order review of 2026-11-04
([deviations REVB-1 to REVB-5](docs/deviations.md#revb-rev-b-per-key-rgb-display-setback-and-review-fixes-layout-pcb-firmware-case-docs)). It is designed and checked, not built; its gate results are
recorded in `docs/verification.md` once the boards are regenerated. Entries not marked rev B are
rev A's.

### Added

- **Rev B, per-key RGB** ([REVB-1](docs/deviations.md#revb-1-per-key-rgb-an-sk6812mini-e-under-every-switch-vled-switched-data-buffered-3-6-7-8-11)):
  - an SK6812MINI-E (C5149201) under every switch, 37 per half, reverse-mounted on the bottom in a
    3.4 × 3.0 mm cutout, its lens in the switch's south-facing LED window, each with its own 100 nF
    (C101–C137); one serpentine chain per half (`layout/leds.py`, `layout.json` `leds`);
  - U6 SY6280AAC (C55136) switches VSYS to VLED, enabled by GP23 with a 10k pull-down and a 0.45 A
    limit; U7 SN74LV1T34DBVR (C100024) buffers GP22 to the VLED level, with R16 470 Ω into LED101;
  - the footprint `worxboard:LED_SK6812MINI-E_ReverseMount` (KiCad's, pads 0.1 mm out) and a
    `.kicad_dru` that lets copper come within 0.3 mm of the LED cutouts;
  - checks: `netcmp.py` "per-key RGB chain" (the chain order, U6/U7 wiring, VLED's members),
    `checks.py` "per-key RGB" (each LED at its window with its cutout, turned along the chain, its
    cap near VDD), layout tests, and `cpl_check.py` gating the reverse-mount LED at 55 % of each
    terminal on its pad;
  - firmware: the chain as ZMK underglow on PIO0 / GP22 with ext-power on GP23, the RGB controls on
    the layer-1 thumbs, brightness capped at 8 % for the one-cable case (`just fw-check` fails a
    higher cap), auto-off after 30 s idle, and RGB settings kept on both halves
    ([firmware.md](docs/firmware.md#rgb)).
- **PCBWay order package** ([REVB-4](docs/deviations.md#revb-4-a-pcbway-order-package-beside-the-jlc-one-pcbscriptspcbwaypy-mpnpy-mpnjson)): stage P step P6 (`pcb/scripts/pcbway.py`) writes
  `pcb/production/<side>/pcbway/` (BOM with manufacturer part numbers, KiCad-native centroids for the
  panel and the bare board, README with the form values and a remark), byte-checked in CI.
  `pcbway.py` fails unless re-applying JLC's corrections to its centroids gives the JLC CPL.
  `mpn.json` and `mpn.py` (`just pcb-mpn`, `pcb-mpn-check`), `just pcb-pcbway`, and the guide
  `docs/ordering-pcbway.md`.
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
- **Turnkey JLCPCB order package** per half in `pcb/production/<side>/` (deviations PKG-1 to PKG-4):
  - a KiKit customer panel: rails, a milled slot, 14 mouse-bite tabs, fiducials and tooling holes;
  - Gerbers, BOM and CPL in JLC's own formats, a README, an order zip, and a `bare-board/` fallback;
  - `just pcb-production`, `pcb-production-check` and `pcb-stock`, and the CI `production` job,
    which requires a byte-identical rebuild.
- `pcb/scripts/cpl_check.py` and `jlc_footprints.py`: every CPL placement is proven against JLC's
  own footprint of the part, 119 of 119 per half. `docs/images/cpl-*.svg` are the overlays (CI
  `cpl-images` job).
- `netcmp.py --board` in stages C and D: the board must carry the `design.py` parts, LCSC numbers and
  flags, no retired part, and J3 with its pin 1 under the nice!view's pin 1 (ELEC-6, ELEC-8).
- **Case order package** in `case/production/`, case revision A3: JLCCNC STEP + PDF per part with the
  order notes, JLC3DP STLs, `hardware.csv`. `just corners` checks every internal corner against
  JLCCNC's radius-for-depth rule, and `just production-check` holds the package to the model, both
  in CI (CASE-1 to CASE-9).
- Firmware: both displays are laid out portrait and turned in the LVGL flush
  (`worx_display_rotation.c`, Kconfig `WORXBOARD_DISPLAY_ROTATION`), with the `just fw-rotate-check`
  host test (WS1-7).
- Docs: the step-by-step turnkey guide `docs/ordering-jlcpcb.md`, with a cost estimate dated
  2026-11-04; `docs/shopping-list.md`; the README "Order it" section.

### Changed

- Rev B board and case changes ([deviations REVB](docs/deviations.md#revb-rev-b-per-key-rgb-display-setback-and-review-fixes-layout-pcb-firmware-case-docs)):
  - the nice!view module, J3 (now y 38.925) and the case window move 1.0 mm back: the module ends
    about 0.2–0.3 mm short of the C6R1 key well instead of 0.6–0.8 mm into it, where the C6R1 keycap had only
    0.12–0.30 mm at bottom-out. The pocket's far end stays at y 75.125; `just model` passes
    ([REVB-2](docs/deviations.md#revb-2-the-display-moves-10-mm-back-from-the-c6r1-key-well-4-pre-order-review));
  - the matrix diodes move from 5.0 to 8.5 mm below the switch centre, under the LEDs (REVB-1);
  - GP22 and GP23 become RGB data and VLED enable; rev A's test pads TP4/TP5 are gone (REVB-1);
  - C1–C3 become 10 µF 0603 10 V X5R (C19702), and the 0402 6.3 V C15525 is retired
    ([REVB-3](docs/deviations.md#revb-3-review-notes-c1c3-0603-plug-in-capacitance-flash-size-rp2350-stepping-6-7-13));
  - 201 assembled parts per half (53 top, 148 bottom), up from 119; the board label reads
    `worxboard L rev B` / `worxboard R rev B`;
  - JLC CPL: U7 (C100024) carries a per-part `JLCPCB_CORRECTION` of 0;0;180, because JLC's footprint
    has pin 1 in the other corner from the SOT-23-5 row; the LEDs need no correction (REVB-1);
  - `jlc_footprints.json` gains the rev B parts and keeps the 2025-06-19 record of the TRRS jack
    C95562 that rev A's J2 correction was proven on ([REVB-5](docs/deviations.md#revb-5-jlcs-footprint-record-for-the-trrs-jack-c95562-is-kept-as-verified));
  - documented, not changed: about 40 µF on VSYS at plug-in, the firmware's 4 MB of the 16 MB
    flash, and the A4 stepping a future RP2350 board needs (REVB-3).
- Docs for rev B: README, microsite, both ordering guides, shopping list (switches with an LED
  window, shine-through caps), build guide, electrical, firmware, case and verification pages.
- `.gitignore` no longer ignores `/zephyr/` (the ZMK module lives at `zephyr/module.yml`). It now
  ignores `/build/`, `pcb/.tools/`, `case/exports/`, and `pcb/production/` outside hardware tags. The
  two order packages are force-added on `main` (PKG-4).
- Parts (ELEC-1 to ELEC-3):
  - hot-swap sockets C41430893, replacing the discontinued C2803348;
  - flash C97521 (basic) and crystal C49304726, replacing C113767 and C91749;
  - J3 is now fitted by JLC: the 5.0 mm THT socket C27985230, which a stock nice!view plugs into;
  - U4's clamp reference is on VSYS, so USB-C VBUS can no longer be back-driven.
- Both boards re-placed and re-routed (BOARD-1 to BOARD-14):
  - J3 turned 180° and moved to the module's header row (y 39.925);
  - C2 at U4's reference pin;
  - every U1 cap's GND return within 13 mm of the exposed pad, with a TESTEN via to the plane;
  - no unlocked dangling copper.
- CPL corrections: QFN-56 0° (was 270°) and USB-C 0;−1.394;0 (was 180°), plus new rows for the
  PJ-320D, J3 and the hot-swap sockets (PKG-2).
- Layout: the PJ-320D body is its drawing size, 14.1 × 6.1 × 5.0 mm (BOARD-13).
- Case:
  - a raised display bezel and a pocket to Z 18.6 over the 5.0 mm J3 stack;
  - blind threads per JLCCNC's guideline, with M2.5 × 12 and × 10 screws;
  - JLCCNC's corner radii;
  - a 0.75 mm TRRS relief;
  - the leg caps as one TPU tree, and the spacer without webs under 1.0 mm.
- Firmware: the right screen sets its own paper and ink and gets an 8 KB LVGL heap (WS1-8); the
  XOSC start-up waits 64× for the new crystal (WS1-9).
- Docs: G1–G3 recorded as passed; the BOM regenerated from the turnkey parts (no `[G3]` flags, one
  loading fee for basic and extended parts); the build guide without any PCB soldering; case, legs,
  electrical and firmware pages updated to match.
- README and microsite redesigned. The microsite adds specs, build, order, firmware, case Z-stack and
  pipeline sections, a filterable gallery with a lightbox and captions for every render and
  placement proof, Iso / Top / Front / Side camera presets and fullscreen; it renders only while the
  viewer is on screen. The concept sketch `docs/images/concept-annotated.png` (notes over an
  ErgoDox EZ image, not a worxboard image) is removed.

### Fixed

- Project review: case order checks compare STEP solids in both directions, STL triangle coordinates
  and winding, and PDF drawings rendered at 600 dpi; equal bulk properties or text no longer hide
  moved holes or changed drawings. Regression tests run in case CI.
- Viewer: switching between the pair and either half reuses the same scene objects, keeping GPU
  allocations and the clipping-material list bounded.
- Firmware: the post-build gate accepts either supported portrait orientation (90° or 270°), while
  still requiring the rotating flush to be linked. Regression tests run locally and in firmware CI.
- Release: the tag workflow uses the existing pixel-tolerant PCB render check so harmless raytracer
  noise does not block publishing.

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

Turnkey work (ELEC, BOARD, PKG, CASE, WS1-7 to WS1-9):

- The completion router keyed its shape cache by `id()`, so the left board differed between hosts;
  it now keys by the item (BOARD-2). `checks.py` no longer loops on a zero-length edge (BOARD-6).
- The right status screen showed nothing: no theme on an uncleared I1 buffer (WS1-8).
- The TRRS jack's far corners came within 0.022 mm of the case top; now 0.376 mm, gated (CASE-9).
- `just docs-gen` crashed on the new LCSC numbers (`KeyError: 'C97521'`).

Order review of the turnkey packages (deviations ORDER-1 to ORDER-9):

- PCB: J1's four through-hole shell legs are on the paste layer (pin-in-paste, `pin_in_paste.py`),
  and the remark asks JLC to solder them; the build guide checks them (ORDER-1).
- PCB, left half: U1's ground reached the planes through one 0.15 mm track and the TESTEN via.
  `gnd_ties.py` adds four locked GND ties, and `checks.py` gates the separate EP links and the U4
  and U2/C5 GND paths (ORDER-4).
- Order docs: the bottom-side warning names the 12 thumb parts as the tell for JLC's other
  rotation reading (ORDER-2); the remark covers the two stabiliser hole pairs under JLC's 0.45 mm
  hole spacing, which `jlc_check.py` gates (ORDER-3).
- Case: collarless DIN 653 leg thumbscrews only (ORDER-5); a stabiliser-wire channel in the plate
  spacers (ORDER-6); USB-C plugs with at least 8 mm of bare shell (ORDER-7); the stabilisers go in
  before the case is closed (ORDER-8); the Strict anodize tier (ORDER-9).

### Known issues

- Not built or tested on hardware: the displays (including their orientation), the wired split,
  the forwarded lock indicators and the crystal start-up
  ([verification.md](docs/verification.md#not-verified-until-a-board-is-built)).
- Rev B, untested on hardware: the LED chain and its timing through U7, VLED switching and U6's
  limit, the current at the 8 % cap, the relayed RGB commands and the display setback's fit. The
  right half's settings writes lock interrupts; their effect on the split UART is unmeasured
  ([firmware.md](docs/firmware.md#known-issues)). ZMK drives the LEDs as underglow: no per-key
  colours.
- The USB-C cable still needs a plug with at least 8 mm of bare shell (ORDER-7).
- JLC does not document its bottom-side CPL convention; check the sockets, diodes and LEDs in its
  placement preview. Never upload the JLC CPL to PCBWay. The hot-swap socket C41430893 has no field
  report of JLC assembling it.
- `release.yml` still packs KiKit's raw fab files instead of `pcb/production/` (PKG-4).
