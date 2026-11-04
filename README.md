<div align="center">

# worxboard

**An ErgoDox EZ-style split keyboard with an on-board RP2040, ZMK wired split, a nice!view-class LCD
on each half and USB-C on both halves. Every part of it is generated from one layout package.**

[![layout](https://github.com/w0rxbend/worxboard/actions/workflows/layout.yml/badge.svg)](https://github.com/w0rxbend/worxboard/actions/workflows/layout.yml)
[![firmware](https://github.com/w0rxbend/worxboard/actions/workflows/firmware.yml/badge.svg)](https://github.com/w0rxbend/worxboard/actions/workflows/firmware.yml)
[![pcb](https://github.com/w0rxbend/worxboard/actions/workflows/pcb.yml/badge.svg)](https://github.com/w0rxbend/worxboard/actions/workflows/pcb.yml)
[![case](https://github.com/w0rxbend/worxboard/actions/workflows/case.yml/badge.svg)](https://github.com/w0rxbend/worxboard/actions/workflows/case.yml)
<br>
[![ZMK](https://img.shields.io/badge/firmware-ZMK-5f3dc4)](https://zmk.dev)
[![KiCad 10](https://img.shields.io/badge/PCB-KiCad_10-314cb0?logo=kicad&logoColor=white)](https://www.kicad.org/)
[![build123d](https://img.shields.io/badge/CAD-build123d-3776ab?logo=python&logoColor=white)](https://github.com/gumyr/build123d)
[![License: GPL v3](https://img.shields.io/badge/code-GPLv3-blue.svg)](LICENSE)
[![License: CERN-OHL-S-2.0](https://img.shields.io/badge/hardware-CERN--OHL--S--2.0-blue.svg)](LICENSE-HARDWARE)

[Order it](#order-it) ·
[Build guide](docs/buildguide_en.md) ·
[BOM](docs/bom.md) ·
[Shopping list](docs/shopping-list.md) ·
[Firmware](docs/firmware.md) ·
[Case](docs/case.md) ·
[Design spec](docs/design.md)

![Both halves in the 3D viewer](docs/images/site-viewer.png)

</div>

worxboard keeps the exact ErgoDox key positions and the 25° six-key thumb cluster. The top key of
the inner column on each half is replaced by a vertical memory LCD. The two halves link over TRRS
with ZMK's wired split. Everything is generated from one layout package ([`layout/`](layout/)): the
KiCad schematics and PCBs, the build123d case, the ZMK physical layout, the docs tables and the 3D
viewer. CI rebuilds all of it on every push.

> [!WARNING]
> **Status: rev A, designed, checked and orderable, not yet built.** Gates **G1–G3** pass
> ([verification.md](docs/verification.md)). The JLCPCB turnkey order of both PCBs and the case order
> are committed and checked in CI on every push ([Order it](#order-it)). No board has been made or
> tested on hardware yet, so order 2 assembled boards per side and test them before you machine the
> case. The frozen design is [`docs/design.md`](docs/design.md); every change from it is in
> [`docs/deviations.md`](docs/deviations.md).

| Part | State |
|---|---|
| Layout (`layout/`) | **Done.** Keys, thumbs, display, jacks, holes, outline, zones and the GPIO map; `just layout-check` |
| PCB (`pcb/`) | **Orderable.** Both halves are generated in KiCad 10. ERC is clean, and DRC with schematic parity gives 0 violations and 0 unconnected. The USB pair, crystal, decoupling and U1 ground-return, via-in-pad and outline checks pass. A seeded from-scratch rebuild reproduces the committed boards in CI. The JLC turnkey package (panel, BOM, CPL proven against JLC's footprints) is committed in [`pcb/production/`](pcb/production/). |
| Firmware (`firmware/`, `zephyr/`, `build.yaml`) | **Builds.** All six `build.yaml` rows (left central, right peripheral, two role-swap and two RP2350A rows) build locally and in CI. Both screens are laid out portrait for the upright display. Untested on hardware. |
| Case and plates (`case/`, `plates/`) | **Orderable.** Every case check and JLCCNC's internal-corner rule pass. `just fitcheck` reports 0 mm³ against both PCB STEPs plus the layout envelopes. The JLCCNC / JLC3DP package, case revision A3, is committed in [`case/production/`](case/production/README.md). Not printed or machined yet. |
| Docs and microsite (`docs/`, `site/`) | **Done.** The turnkey ordering guide and shopping list, build guide, generated BOM, pinout and matrix, electrical, case, legs, firmware; the viewer |
| Gates and release | **Pass.** [`docs/verification.md`](docs/verification.md) records the integration tests, CI, the order package checks and gates G1–G3. `release.yml` is written; no tag or release exists yet. |

## Order it

Everything for one keyboard is committed and rebuilt in CI on every push:

| Order | Where | Files | How |
|---|---|---|---|
| Left and right PCBs, fully assembled (2 designs: 5 PCBs, 2 assembled each) | [JLCPCB](https://jlcpcb.com), Standard PCBA, both sides | [`pcb/production/left/`](pcb/production/left/README.md), [`pcb/production/right/`](pcb/production/right/README.md): `gerbers.zip`, `bom.csv`, `cpl.csv` | [ordering-jlcpcb.md](docs/ordering-jlcpcb.md) |
| 2 top shells, 2 bottom trays, 6 tent legs (6061, anodized) | [JLCCNC](https://jlccnc.com) | [`case/production/jlccnc/`](case/production/jlccnc/ORDER_NOTES.md) | the order notes |
| 2 plate spacers (MJF PA12), 1 tree of 8 leg caps (TPU) | [JLC3DP](https://jlc3dp.com) | [`case/production/jlc3dp/`](case/production/jlc3dp/ORDER_NOTES.md) | the order notes |
| Switches, keycaps, stabilisers, 2 nice!view, cables, screws, feet, thumbscrews | keyboard and hardware shops | [`case/production/hardware.csv`](case/production/hardware.csv) | [shopping-list.md](docs/shopping-list.md) |

JLC fits every part on the PCB, including the display socket, so nothing is soldered on the board.
The only soldering is the displays' own header pins. Estimated on 2026-11-04, the JLCPCB order
comes to about **$307–425** for both halves with 2 assembled each, shipping included and import duty
not ([cost estimate](docs/ordering-jlcpcb.md#cost-estimate)). Run `just pcb-stock left 5` on the day
you order. Then follow the [build guide](docs/buildguide_en.md).

## Spin it in your browser

[![The viewer, right half exploded](docs/images/site-viewer-exploded.png)](site/)

The microsite in [`site/`](site/) has a three.js viewer, adapted from the
[ErgoDox CNC case](https://github.com/w0rxbend/ergodox) viewer. It builds both halves straight from
`layout/build/layout.json`: PCB, switches, keycaps with legends and the displays. It places every
assembled part of the committed KiCad boards at its real position and adds the case STLs when the
case model has been built. You can explode the stack, sweep a section plane, swing the legs, hover a
key to see its matrix position, or a part to see its reference, and download the STLs. Build it
with `just site` and serve it with `just site-serve` (port 8000). The `pages` workflow deploys it to
GitHub Pages, on demand only; it has not been deployed yet.

## Features

- **Exact ErgoDox layout.** Switch centres, column stagger and the 25° thumb cluster come from the
  original ErgoDox PCB and are checked to 0.002 mm. 37 keys per half, 74 in total.
- **A display on each half.** A Sharp LS011B7DH03 memory LCD on a nice!view-compatible module sits
  where the inner top key was, behind a window in the case. The left shows the ZMK status screen,
  the right a custom screen with the lock indicators.
- **On-board RP2040, assembled by JLCPCB.** No controller daughterboard. The support circuit (flash,
  crystal, LDO, ESD) is cloned from the Corne v4.1 production BOM. The 37 hot-swap sockets and
  diodes per half are assembled on the bottom side, and the display socket on the top: nothing is
  soldered on the PCB.
- **USB-C on both halves.** Plug the host into the **left** half. The right USB-C powers and flashes;
  Schottky diodes let both be plugged in at once.
- **A careful wired split.** ZMK `zmk,wired-split` on UART0 over a straight TRRS cable. The tip
  carries only 1 kΩ-limited data, power sits on Ring2 behind a 250 mA polyfuse, and a solder jumper
  (JP1) turns cable power off. **Never hot-plug the TRRS cable.**
- **One matrix netlist on both PCBs.** The right `.dts` reverses the column GPIOs, so the two boards
  share the same netlist and only the TRRS crossover resistors differ.
- **Tent legs like the EZ.** Three mounts per half at the stock positions, taking the stock M3 spring
  thumbscrews ([legs.md](docs/legs.md)).
- **Generated, not drawn.** Schematic, placement, routing, DRC, fab files, case, physical layout and
  docs tables are all scripts, run headless in pinned containers. The PCB pipeline is seeded, so a
  rebuild gives byte-identical boards.

| | |
|---|---|
| Keys | 74 (37 per half): 6 × 7 matrix per half, `col2row`, ZMK 6 × 14 transform |
| Controller | RP2040 + W25Q128 16 MB QSPI flash per half |
| Display | 160 × 68 Sharp memory LCD per half, PIO1 SPI |
| Split link | TRRS 3.5 mm, UART 115 200 baud, full duplex |
| USB | USB-C 2.0 full speed on both halves (host on the left) |
| PCB | 2 layers, 1.6 mm FR4, ENIG, 182.8 × 158.8 mm per half; 119 JLC-assembled parts per half, 74 of them on the bottom |
| Switches | MX-compatible, Kailh hot-swap sockets; 2u plate-mount stabilisers on two thumb keys |
| Firmware | ZMK (HWMv2 board `worxbend/worxboard`), ZMK Studio on the left central |
| Case | Two-piece CNC 6061 case with integrated plate, 192.4 × 165.6 × 17.6 mm (19.6 at the display bezel) and about 349 g per half; 8 × M2.5 screws and three tent legs per half |

## How it fits together

```mermaid
flowchart LR
    L["layout/<br/>keys · thumbs · display · jacks<br/>holes · outline · zones · pins"] -->|just layout| J["layout.json<br/>layout.svg · kle.json"]
    J -->|just pcb-sch / pcb-place| P["KiCad 10 schematics + PCBs<br/>ERC · Freerouting · DRC"]
    P -->|just pcb-production| F["pcb/production<br/>panel gerbers · BOM · CPL<br/>(JLCPCB turnkey)"]
    P -->|just pcb-fab| S["PCB STEP · renders"]
    J -->|just model| C["build123d case<br/>STEP · STL · DXF · plates"]
    S -->|just fitcheck| C
    J -->|just fw-layouts| Z["ZMK physical layout<br/>+ matrix transform"]
    Z -->|just fw| U["UF2 firmware<br/>left central · right peripheral"]
    J -->|just docs-gen| D["pinout.md · matrix.md · bom.md"]
    P --> D
    J -->|just site| W["3D viewer<br/>(GitHub Pages)"]
    P --> W
    C --> W
```

The stack from the bottom up (spec §10): the **bottom tray** (Z 0–7) with the hot-swap sockets and
diodes in its 4 mm cavity, the **PCB** (Z 7–8.6), the 3 mm **plate spacer**, and the **top shell**
with the 1.5 mm plate milled into its key well, the display window and pin holes over BOOT and RESET.

## Get the files

Every push to `main` rebuilds everything. Download the artifacts of a green run:

| Workflow | Artifact | Contents |
|---|---|---|
| [firmware](https://github.com/w0rxbend/worxboard/actions/workflows/firmware.yml) | `worxboard-firmware` | six `.uf2` files: `worxboard_left_central`, `worxboard_right_peripheral` and the `*_EXPERIMENTAL` rows ([firmware.md](docs/firmware.md)) |
| [pcb](https://github.com/w0rxbend/worxboard/actions/workflows/pcb.yml) | `worxboard-pcb-left`, `worxboard-pcb-right` | KiKit's raw bare-board fab files, the board STEP, the Edge.Cuts DXF, the DRC report, the renders. For an order use the committed [`pcb/production/`](pcb/production/) instead ([ordering-jlcpcb.md](docs/ordering-jlcpcb.md)) |
| [pcb](https://github.com/w0rxbend/worxboard/actions/workflows/pcb.yml) | `worxboard-pcb-erc`, `worxboard-pcb-rebuild-*` | ERC reports and netlists; the from-scratch rebuilds and their Freerouting logs |
| [case](https://github.com/w0rxbend/worxboard/actions/workflows/case.yml) | `worxboard-case` | case STEP/STL/DXF, plates, renders, build report and the order package, also committed in [`case/production/`](case/production/README.md) ([case.md](docs/case.md)) |

Tagged `v*-revA` releases with the same files are planned (WS5); no release exists yet.

## Previews

The committed boards, rendered by KiCad (`just pcb-fab <side>`):

| | Top | Bottom |
|---|---|---|
| Left | ![Left PCB, top](docs/images/pcb-left-top.png) | ![Left PCB, bottom](docs/images/pcb-left-bottom.png) |
| Right | ![Right PCB, top](docs/images/pcb-right-top.png) | ![Right PCB, bottom](docs/images/pcb-right-bottom.png) |

The case (`just renders`):

![Both top shells](case/renders/pair_top_iso.png)

| Top shell, underside | Bottom tray |
|---|---|
| ![](case/renders/right_top_underside.png) | ![](case/renders/right_bottom_tray.png) |

| Right half with the tent legs | Leg mount section |
|---|---|
| ![](case/renders/right_with_legs.png) | ![](case/renders/leg_section.png) |

More in [docs/case.md](docs/case.md#previews), and the generated layout in
[docs/images/layout.svg](docs/images/layout.svg).

## Build from source

You need [uv](https://docs.astral.sh/uv/), [just](https://just.systems/) and Docker (for KiCad
10.0.7, Freerouting, the ZMK toolchain and lychee).

```sh
just setup          # .venv with every Python group (Python 3.12)
just layout-check   # layout tests + no-diff check of the committed contracts
just fw             # ZMK firmware for every build.yaml row -> build/fw/artifacts/*.uf2 (Docker)
just pcb-drc left   # DRC gate (schematic parity, 0 unconnected) + scripted checks on the committed board
just pcb-fab left   # KiKit fab files, CPL check, renders, Edge DXF, STEP -> build/left/ (Docker, -full image)
just pcb-production left   # the JLC order package -> pcb/production/left/ (panel, BOM, CPL)
just pcb-stock left 5      # package checks + live JLC stock for 5 + 5 boards (network)
just pcb-all        # both PCBs from scratch: schematic, placement, routing, DRC, fab (~20 min per side)
just model          # case STEP/STL/DXF -> case/exports/, plates/*.dxf
just production     # the case order package -> case/production/
just fitcheck       # case vs build/<side>/worxboard-<side>.step: 0 mm3
just docs-check     # generated docs up to date + link check
just site           # microsite into _site/ (just site-serve serves it on :8000)
just all            # layout-check -> fw -> pcb-all -> model -> site
just --list         # every recipe
```

Recipes come from each area's own file: [`layout/layout.just`](layout/layout.just),
[`firmware/firmware.just`](firmware/firmware.just), [`pcb/pcb.just`](pcb/pcb.just),
[`case/case.just`](case/case.just) and [`site/site.just`](site/site.just). The PCB stages run in
`kicad/kicad:10.0.7` (`-full` for STEP and renders) with `--network none`; `just pcb-deps` installs
their pinned Python packages into `pcb/.tools/` once.

## Known open issues

- **Not built yet.** No board has been made. The displays, the wired split, the lock-indicator
  forwarding, the role-swap firmware and the XOSC start-up of the new crystal are untested on
  hardware ([verification.md](docs/verification.md#not-verified-until-a-board-is-built)).
- **Display orientation.** Both screens are laid out portrait and turned by the firmware. Which panel
  end is pixel 0 comes from ZMK's code and the vendor's images, not a datasheet. If they read upside
  down, set `CONFIG_WORXBOARD_DISPLAY_ROTATION_270=y` ([firmware.md](docs/firmware.md#known-issues)).
- **JLC placement.** Every CPL placement is proven against JLC's own footprints, but JLC does not
  document its bottom-side convention. Check the sockets and diodes in JLC's placement preview
  ([ordering-jlcpcb.md](docs/ordering-jlcpcb.md#placement-preview-checklist)). The hot-swap socket
  C41430893 is a second-source part with no field report of JLC assembling it yet.
- **Stock** moves daily. Run `just pcb-stock left 5` on the day you order. J3 (C27985230) has no
  drop-in alternate that fits the case ([alternates](docs/ordering-jlcpcb.md#if-a-part-is-out-of-stock)).
- **3D models.** KiCad has no model for the USB-C, the TRRS jack or the hot-swap socket, so the board
  STEP lacks those bodies; the case fit check adds their layout envelopes.
- **Release packaging.** `release.yml` still packs KiKit's raw fab files, not `pcb/production/`
  (deviation PKG-4).
- **RP2350A target** (`worxboard2`): settings do not persist (flash map and NVS are forced off).
- **Licence split** (below) awaits the maintainer's confirmation.

## Repository layout

```
layout/              single source of truth; layout/build/layout.json is the committed contract
pcb/                 KiCad 10 projects per half (left/, right/), worxboard symbol/footprint library (lib/),
                     generator scripts (scripts/: design, schematic, placement, routing, checks, fab, panel),
                     the JLC turnkey order packages (production/)
firmware/zmk/        ZMK board module (RP2040 worxboard, RP2350A worxboard2), keymap, custom screen, scripts
zephyr/module.yml    Zephyr module entry point for the ZMK build
build.yaml           ZMK build matrix
case/                build123d case, drawings, fit check, overlay, renders/, the JLCCNC/JLC3DP order package
                     (production/; exports/ is git-ignored)
plates/              plate DXFs
docs/                build guide, BOM, electrical, pinout, matrix, ordering, case, legs, firmware, spec
site/                microsite: web/ (three.js viewer), build_site.py, gen_docs.py, pcbdata.py
tools/               container helpers and pinned image digests
.github/workflows/   layout, firmware, pcb, case on every push; pages.yml deploys the microsite (manual)
```

## Documentation

| Document | Contents |
|---|---|
| [docs/buildguide_en.md](docs/buildguide_en.md) | Build guide: board check, bare-board flashing, JP1 power modes, displays, assembly, troubleshooting |
| [docs/bom.md](docs/bom.md) | Bill of materials with LCSC numbers (generated), JLC fees, the ordering gates |
| [docs/shopping-list.md](docs/shopping-list.md) | The four orders and every off-board part for one keyboard |
| [docs/electrical.md](docs/electrical.md) | Power path, TRRS link, USB-C, MCU support circuit, display, reference designators, PCB rules and pipeline |
| [docs/pinout.md](docs/pinout.md) | RP2040 GPIO map, TRRS contacts, display header, part positions, holes (generated) |
| [docs/matrix.md](docs/matrix.md) | Key matrix per half, sockets and diodes, ZMK 6 × 14 transform, keymap order (generated) |
| [docs/firmware.md](docs/firmware.md) | ZMK builds, flashing, host behaviour, keymap, displays, known issues |
| [docs/ordering-jlcpcb.md](docs/ordering-jlcpcb.md) | The turnkey JLCPCB order step by step: form fields, placement checks, alternates, cost estimate |
| [docs/case.md](docs/case.md) | The case: Z stack, changes from the ErgoDox case, the order package, fasteners, previews |
| [docs/legs.md](docs/legs.md) | Tent/tilt legs: mounts, positions, the custom leg |
| [docs/design.md](docs/design.md) | The frozen rev A specification |
| [docs/deviations.md](docs/deviations.md) | Every change from the specification, by work-stream |
| [docs/verification.md](docs/verification.md) | Integration results, CI, the order package checks and gates G1–G3; what only a built board can confirm |
| [docs/sources.md](docs/sources.md) | Prior art, tools and attribution |

`docs/pinout.md`, `docs/matrix.md` and the BOM tables in `docs/bom.md` are generated by
`site/gen_docs.py` from `layout/build/layout.json`, `pcb/scripts/design.py` and the committed
boards; run `just docs-gen` after a layout or PCB change (`just docs-check` fails if they are stale).

## License

- Code (`layout/`, `pcb/scripts/`, `case/*.py`, `firmware/`, `tools/`, `site/`): [GPL-3.0](LICENSE).
- Hardware (`pcb/` KiCad files and libraries, case geometry outputs, `plates/`, `docs/`):
  [CERN-OHL-S-2.0](LICENSE-HARDWARE). **Maintainer to confirm** this split before the first hardware tag.
- Third-party material: [`THIRD_PARTY.md`](THIRD_PARTY.md); attribution in [docs/sources.md](docs/sources.md).

The key and mounting-hole coordinates come from the original ErgoDox PCB by Fredrik Atmer and
contributors (GPL-3.0). "ErgoDox EZ" is a product of ZSA Technology Labs and "nice!view" of Nice
Keyboards; this project is not affiliated with or endorsed by either.
