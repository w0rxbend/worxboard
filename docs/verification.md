# Verification

This page records the rev A integration results and the ordering gates of spec §7: G1 (display),
G2 (TRRS jack) and G3 (parts). WS5 first checked them on 2026-11-02, and all three failed. The
turnkey work of 2026-11-03 and 2026-11-04 fixed them (deviations ELEC, BOARD, PKG, CASE and WS1-7
to WS1-9). This page was re-checked on **2026-11-04** at `f4c95bb`, the last commit before these
docs. The gates block **ordering**, not the repository.

> [!NOTE]
> **Rev B** (per-key RGB, the display setback and the review fixes, [deviations REVB](deviations.md#revb-rev-b-per-key-rgb-display-setback-and-review-fixes-layout-pcb-firmware-case-docs)) changes
> both boards and their order packages. Everything recorded below is **rev A's**. The rev B results
> (integration tests, CI, the order packages, the boards and gates G1–G3) are recorded on this page
> after the boards are regenerated; until then, nothing here is a rev B result. What only a built
> rev B board can confirm is listed under [Not verified until a board is built](#not-verified-until-a-board-is-built).

## Rev B results (2026-11-08)

**Not orderable.** No left board has passed stage C, so the rev B fab outputs, order packages, from-scratch rebuild, and gate table were not run. The files in `pcb/production/` are still rev A. Main-tree `KIID_SEED` is still `{"left": 0x4, "right": 0x1}`, and `pcb/left/worxboard-left.kicad_pcb` is the placed board (492 segments), not a routed one. Commit under the working tree is `ff4449a`. Nothing was committed.

| Half | Seed | Result |
|---|---|---|
| Right | `0x1`, `build/seedtrials/right-1` | **Pass.** DRC 0 violations / 0 unconnected / 0 parity, `checks.py` 15/15, `netcmp --board` 2/2 (221 footprints). U4 pin 2 to J1 GND is 10.3 mm. |
| Left | `0x1` with U7 at (65.6, 49.0), `leftB-1` | **Fail.** DRC ended 0/0/0. U4 pin 2 to J1 GND is 13.2 mm (the move opened that path). U1 ground links 1 of 2. C5 to U2 pin 4 has no copper path. Stage C stopped in `gnd_ties.py`. |
| Left | `0x3`, `0x4`, `0x5`, old U7 at (73.35, 48.19) | **Fail.** `0x3` and `0x5` lost the U4 clamp-ground path. `0x4` left COL2 unconnected and missed an LED cutout by 0.002 mm under the old 0.30 mm rule. |
| Left | `0x6`, old U7, `left-6` | **Fail.** DRC 0/0/0. U4 path 20.5 mm, U1 links 2. C5 to U2 pin 4 stayed 38.8 mm (limit 30). |
| Left | `0x2`, `0x3`, `0x4`, `0x5` with U7 moved (`leftB-2` .. `leftB-5`), and old-placement `0x7` .. `0x9` | **No result.** Freerouting had finished (54–64 connections left, against 67 on the clean right board). Stage C was still running when the machine went down at 05:20. No `trial.done`. |

The 11:00 Europe/Kyiv stop arrived with those jobs dead. They were not restarted: a finish plus the order gates cannot complete in the time that was left, and a new seed was already out of bounds after 09:15. `leftB-2`, `leftB-3`, and `leftB-5` still have their Freerouting session files and an unrouted placed board, so `just pcb-finish left` in those trees is the resume. `leftB-4`'s board file was already imported and still had COL2 open; do not finish that copy in place.

Host checks that do not read copper had already passed on this working tree before the route: layout pytest, `layout.export --check`, the ZMK layout and keymap checks, the display-rotation host test, and 9 firmware regressions. `just pcb-mpn-check` inside the KiCad container was not run. Hardware items below are unchanged: no board has been built.

## Summary

| Check | Result |
|---|---|
| [Integration tests](#integration-tests) (`tests/integration/`) | **PASS**: 111 passed, 0 expected failures, 0 skipped |
| [CI on `main`](#ci) | **PASS**: layout, firmware, case and pcb on `f4c95bb`, every job, both from-scratch board rebuilds included |
| [Order package](#order-package) (`pcb/production/`) | **PASS**: `jlc_check` on both halves, 119 of 119 placements per half proven against JLC's footprints, and the package rebuilds byte for byte |
| [Boards](#boards-after-the-turnkey-re-placement) | **PASS**: DRC with schematic parity 0 / 0 / 0, `checks.py` 14 of 14 per half |
| [G1 display](#g1-niceview-display) | **PASS** |
| [G2 TRRS jack](#g2-pj-320d-trrs-jack) | **PASS** |
| [G3 parts, rules and placement](#g3-parts-stock-and-track-width) | **PASS**: every line in stock on 2026-11-04 at 05:17 UTC; re-check on the order day |
| [Hardware](#not-verified-until-a-board-is-built) | **not built**: the items only a real board can confirm are listed |

Nothing blocks the order now ([open items](#open-items-that-block-ordering)). Order 2 assembled
boards per side and test them before ordering the aluminium case
([ordering-jlcpcb.md](ordering-jlcpcb.md)).

## How to re-run

```sh
just all                                   # layout-check -> fw -> pcb-all -> model -> site
uv run pytest tests/integration -rxs       # pins, gates, stock logic, release assembly
just pcb-production-check left             # the order package equals a rebuild (also: right)
just pcb-stock left 5                      # package checks + live JLC stock for 5 + 5 boards (network)
uv run python tests/integration/stock.py --boards 5   # the same stock check, with LCSC too
just model corners fitcheck                # case checks, JLCCNC corner rule, fit against the PCB STEPs
```

## Integration tests

`tests/integration/test_pins.py` reads the firmware devicetree (the committed board files of both
targets, and every built `build/fw/<artifact>/zephyr/zephyr.dts`), the PCB (the committed boards,
and the netlists `just pcb-sch` exports) and `layout/pins.py`:

- **Every switch reaches its keymap slot.** The chain is checked for each of the 37 keys per half:
  1. the socket's COL net and the diode cathode's ROW net;
  2. the RP2040 GPIO on each net;
  3. the firmware row and column for those GPIOs, plus `col-offset`;
  4. the transform position of that (row, col), and the key `layout.json` puts there.

  This proves the right half's reversed `col-gpios` (GP20…GP14, `col-offset = 7`) against the
  shared matrix netlist.
- **TRRS crossover.** This follows each jack's 1 kΩ resistors to the UART pins. With a straight
  cable, the left TX meets the right RX and the reverse. Ring2 is VLINK and Sleeve is GND on both
  halves.
- **Display header.** J3 pins 1–5 carry the firmware's PIO1 SPI MOSI, SCK and CS GPIOs, 3V3 and
  GND.
- **Firmware vs `pins.py`.** These must hold for the board files and all six compiled builds:
  - rows GP8–GP13 with pull-down;
  - columns GP14–GP20 (reversed on the right);
  - UART0 TX GP0 / RX GP1, with input enabled;
  - SPI on GP2/GP3/GP5, with CS active high.

  Every compiled `zephyr.dts` equals its board files, and the RP2350A target has the same pinout.
- **Netlist vs board.** Each netlist part has the same pad nets on the committed board, and the
  RP2040 pin names in the netlist give the QFN numbers that `pins.py` lists.
- **The checks catch what they are for.** Mutated firmware must fail the chain and crossover
  checks: right columns not reversed, no `col-offset`, rows rotated, UART roles swapped.

The other test files:

- `test_gates.py` checks G1 and G2 against the drawings (below). Its strict expected failures came
  off as the fixes landed (`b5c0f60` for G1, `68f812e` for G2).
- `test_stock.py` checks offline that every part with a body is in the JLC BOM with an LCSC number,
  J3 included. It also checks that no part is DNP, that both halves share one BOM, that no retired
  part is back, that the committed boards order the `design.py` parts, and the stock verdicts on
  canned records (ELEC-4, ELEC-6).
- `test_stabs.py` checks that the PCB's Ø4.0 stabiliser holes sit on the side `layout.json` names,
  and that the halves are mirror images.
- `test_release.py` checks the release assembly.

Result on 2026-11-04 at `f4c95bb`: **111 passed**, nothing skipped, no expected failures.

## Order package

`pcb/production/<side>/` holds the JLC order of each half. The panel is the default; `bare-board/`
is the fallback. See [ordering-jlcpcb.md](ordering-jlcpcb.md).

| Check | Left | Right |
|---|---|---|
| `jlc_check.py` (`just pcb-stock left 5` and `jlc_check.py check right`, 2026-11-04 05:17 UTC) | 11 of 11, with live stock | 10 of 10 |
| Panel Gerbers | 9 layers + PTH/NPTH drills, no dates, 198.84 × 174.75 mm | same |
| `bom.csv` / `cpl.csv` | `Comment,Designator,Footprint,LCSC Part #`, 21 LCSC numbers / `Designator,Mid X,Mid Y,Layer,Rotation`, 119 placements, 74 bottom | same |
| BOM = CPL = the parts `design.py` fits | 119; not fitted on purpose: H1–H8, JP1, TP1–TP11 | same |
| `cpl_check.py`: JLC's footprint placed from the CPL over the KiCad pads | 119 of 119 within 0.033 mm, pin 1 on pin 1, terminals 89–100 % on their pads, socket bodies 0.70 mm clear of the switch posts | same |
| Package equals a rebuild (`just pcb-production-check`) | CI job 126391534598 | CI job 126391534636 |
| CPL overlays `docs/images/cpl-*.svg` current | CI job 126391534388 | |

The panel holds the board in a frame. It has rails of 6 mm or more and a 2 mm milled slot round the
board. There are 14 mouse-bite tabs, each 1.4 mm or more from every courtyard and 2.1 mm or more
from J1 and J2. There are 3 fiducials per side and 4 Ø2.0 mm tooling holes. Panel DRC gives 0
errors and 0 unconnected items, and `jlc_check` confirms that the panel carries the board's copper
unchanged (deviations PKG-1 to PKG-4).

## Boards after the turnkey re-placement

Both halves were re-placed and re-routed from the ELEC schematics (BOARD-1 to BOARD-14), and the
left one got its U1 GND ties (ORDER-4). Numbers are from BOARD-14 and ORDER-4; CI rebuilds both
boards from scratch on every push and requires them to equal the committed ones.

| Check | Left | Right |
|---|---|---|
| `just pcb-sch-all` | ERC 0, netcmp 10/10 | ERC 0, netcmp 10/10 |
| DRC `--schematic-parity --severity-error` | 0 violations, 0 unconnected, 0 parity | same |
| `checks.py` | 14/14: USB D+ 24.73, D− 23.92, skew 0.81 mm; Y1 2.93 mm; worst supply pin 11.64 mm (IOVDD 22); U4 to VSYS 4.07 mm | 14/14: USB 23.75 / 23.50, skew 0.25 mm; Y1 2.93 mm; IOVDD 22 11.64 mm; U4 to VSYS 4.07 mm |
| U1 cap GND return to the exposed pad (gate ≤ 20 mm) | 9.3–13.0 mm | 8.6–13.0 mm |
| Exposed pad to the main B.Cu GND plane (gate ≤ 8 mm) | 1.6 mm (9/9 EP vias in the plane) | 1.6 mm |
| Separate EP links ≥ 0.4 mm wide (gate ≥ 2) | 2: 27.0, 31.9 mm | 6: 32.9–38.6 mm |
| U4 pin 2 → J1 GND; C5 → U2 pin 4 (gate ≤ 30 mm) | 22.3; 11.4 mm | 17.4; 18.0 mm |
| `netcmp.py --board` + kikit BOM/CPL (stage D) | 3/3, 119 fitted parts, J3 pin-1 gate | same |
| Copper | 328 vias, all 0.3 / 0.6; narrowest track 0.135 mm | 389 vias, all 0.3 / 0.6; narrowest 0.135 mm |
| Dangling copper | 0 unlocked; 34 locked warnings (column vias at the keys, U1 fan-out stubs) | 0 unlocked; 37 locked |

- **U1 ground (BOARD-14).** U1's only GND pin is the exposed pad. Every one of its 12 caps has a
  short GND return to it:
  - locked 0.5 mm B.Cu spurs run from the pad's vias to each cap's GND via, or into a GND fill
    that meets them;
  - TESTEN (pin 19, GND) runs out on a locked 0.2 mm track to a via in the Y1 keepout's GND fill,
    which reaches the back edge;
  - on the left, four locked GND ties from `gnd_ties.py` join the pad's B.Cu to the main plane
    and U2's GND pin to its cap C5 (ORDER-4). Before them, the TESTEN via behind a 0.15 mm track
    was the left pad's only link to the planes;
  - `checks.py` gates the cap returns, the pad-to-plane distance, the number of separate links
    and the U4 and U2 GND paths.
- **Host independence.** The completion router keys its shape cache by the item, not by `id()`
  (BOARD-2), so the boards are the same on every host.
- **U4's clamp reference** is VSYS, with its own 10 µF at the pin (ELEC-2, BOARD-5). VBUS can no
  longer be back-driven.

## `just all` from a clean clone

WS5 ran this on 2026-11-02 at `d1f2d77`. It has not been repeated as one run since. On every push,
CI rebuilds what it covers: the six UF2s, both boards from scratch (byte-identical), the order
packages, the case and the fit check.

`git clone https://github.com/w0rxbend/worxboard` at `d1f2d77` into an empty scratch directory,
then `just all` with nothing built or cached, exited 0 after **34 min 44 s**:

| Stage | Result then |
|---|---|
| `just layout-check` | 31 passed; `layout.json` and `layout.svg` regenerate with no diff |
| `just fw` | all six `build.yaml` rows built a UF2; the right peripheral had no `zmk_ble_` / `zmk_battery_` symbols |
| `just pcb-all` | per half: ERC 0, Freerouting, DRC with schematic parity 0 / 0 / 0, `checks.py`, KiKit fab outputs, renders, STEP |
| `just model` | every case check passed |
| `just site` | `_site/` 6.6 MB |

Afterwards `git status` in the clone was empty: both boards rebuilt byte-identical.

## CI

The four workflows that run on a push to `main` all pass. At `f4c95bb`:

| Workflow | Run | Result |
|---|---|---|
| layout | [41774485217](https://github.com/w0rxbend/worxboard/actions/runs/41774485217) | success |
| firmware (six UF2s, the rotation host test, right-half checks) | [41774485258](https://github.com/w0rxbend/worxboard/actions/runs/41774485258) | success |
| pcb | [41774485196](https://github.com/w0rxbend/worxboard/actions/runs/41774485196) | success, all 10 jobs |
| case (model, JLCCNC corner check, plates, fit check, renders, order package, production check) | [41774485198](https://github.com/w0rxbend/worxboard/actions/runs/41774485198) | success |

The pcb run's 10 jobs:

- schematics, ERC and netcmp;
- both board jobs (DRC gate, fab outputs, render compare);
- both from-scratch rebuilds;
- both order-package jobs;
- the CPL overlay drawings;
- the case fit check against the CI-built PCB STEPs.

`release.yml` runs only on a `v*` tag push and has not run: no tag or release exists. `pages.yml`
is manual and has not run.

## G1: nice!view display

**Sources:**

- the nice!view pinout, dimension and schematic drawings
  ([nicekeyboards.com](https://nicekeyboards.com/docs/nice-view/pinout-schematic), re-read
  2026-11-03);
- the splitkb [FAQ](https://docs.splitkb.com/product-guides/nice-view/frequently-asked-questions):
  36 × 14 × 2.9 mm, five pins, socket and pins included;
- the viewing area of the Sharp LS011B7DH03, from its
  [DigiKey listing](https://www.digikey.com/en/products/detail/sharp-microelectronics/LS011B7DH03/25953418).

| Item | Drawing | Design | Result |
|---|---|---|---|
| Size | 36 (+0.1–0.2 V-cut) × 14 × 2.9: glass 0.9, PCB 1.0, parts below 1.0 | 36 × 14 × 2.9 | PASS |
| Pin order | MOSI, SCK, VCC, GND, CS | J3 pins 1–5: `DISP_MOSI`, `DISP_SCK`, `3V3`, `GND`, `DISP_CS` | PASS |
| Pin-1 end | Front (LCD) view with the header at the bottom: MOSI at the left. Mounted LCD up with the header at the back (low y), MOSI is at **high x** | J3 pad 1 (`DISP_MOSI`) at **high x** on both halves: right (77.47, 39.925), left (192.69, 39.925) (BOARD-1) | PASS, and a gate: `netcmp.py --board` stops stages C and D otherwise (ELEC-8) |
| Header row to the module edge | 1.3 mm, pins centred across the 14 mm width | 1.3: header y 39.925, module y 38.625–74.625 | PASS |
| Module in the pocket | 36.2 mm with the V-cut | module y 38.625–74.825; pocket 38.125–75.125 | PASS |
| Viewing area | 25.28 × 10.74, starting 4.6 mm from the header-end edge | 26 × 12 window centred on it (y 55.865), following the header | PASS |
| Stack above the PCB | J3 5.0 (C27985230, ELEC-3) + the stock header 2.0 + PCB 1.0 + glass 0.9 | glass 8.9 nominal, 9.4 with a 2.5 mm header carrier, **9.75 at full tolerance**; pocket ceiling at Z 18.6 = PCB + 10.0, under a 1.0 mm skin in a raised bezel (CASE-1) | PASS |
| Fit | | `just fitcheck`: the J3 body to 5.8 mm, then the module to 9.75 mm, against both case tops: **0 mm³**. A top with the old 16.8 ceiling gives 138 mm³, so the check has teeth | PASS |
| CS polarity | active high (LS011B7DH03) | `cs-gpios … GPIO_ACTIVE_HIGH` | PASS |
| Screen orientation | the module stands LCD up, header at the back | both screens are laid out portrait and turned by the firmware (`LV_DISPLAY_ROTATION_90`, WS1-7) | on hardware |

- **J3 is fitted by JLC.** It is C27985230, a 5.0 mm THT socket and the same height as the socket
  that ships with the nice!view. A stock nice!view plugs in on its own header. The header pins must
  be **trimmed flush** on the glass side: untrimmed, they reach the pocket ceiling (CASE-1).
- **Integration tests.** `test_g1_header_is_at_the_back_end`, `…_j3_pin_order_is_the_module_order`,
  `…_module_pins_land_on_their_nets`, `…_module_fits_the_pocket` and
  `…_window_shows_the_viewing_area` all pass on both halves.
- **Firmware orientation.** The panel end that is pixel x = 0 comes from ZMK's nice_view widgets
  and the vendor's product images. No Sharp datasheet was found. If the first board shows the
  screens upside down, set `CONFIG_WORXBOARD_DISPLAY_ROTATION_270=y` in
  `firmware/zmk/config/worxboard.conf` ([firmware.md](firmware.md#known-issues)).

## G2: PJ-320D TRRS jack

**Source:** HRO PJ-320D drawing (rev B, drawn 2016-05-03), the
[LCSC C95562 datasheet](https://www.lcsc.com/datasheet/C95562.pdf).

| Item | Drawing | Design | Result |
|---|---|---|---|
| Height | 5.00 (Ø5.00 barrel, 6.10 × 5.00 body) | ≤ 5.5 (spec); layout 5.0 | PASS |
| Plug axis | centred, 2.50 above the PCB | `axis_z` 2.5, case hole on it | PASS |
| Land pattern | pads 1.20 × 2.50 at 3.20 (pin 4), 6.20 (pin 3), 10.20 (pin 2) behind the barrel face on one side and 11.30 (pin 1) on the other, rows ±3.25 off the axis; peg holes Ø1.00 at 1.60 and 8.60 | KiCad `Jack_3.5mm_PJ320D_Horizontal`: R2, R1, T and S at the same positions and sizes; peg holes Ø1.5 (a looser fit) | PASS |
| Contacts | schematic PJ-320D-A: pin 1 is the sleeve; the spring contacts run 4, 3, 2 from the mouth, so 4 = Ring2, 3 = Ring1, 2 = Tip | pads named S, R2, R1, T at those places | PASS, see the note |
| Body | 2.00 barrel + 12.10 body = 14.10 long, 6.10 wide | layout body 14.1 × 6.1 × 5.0: x 49.0–63.1 by y 99.95–106.05 (right frame) (BOARD-13) | PASS |
| Case relief | | the body + 0.75 mm, R1.5 corners, in the top, the spacer and the plate DXF; 0.376 mm at the far corners in the built top, 0.431 in the spacer and the plate; 1.0 mm headroom (CASE-9) | PASS, and a gate: `jack_check` fails under `JACK_MIN_CLEAR` = 0.3 mm |
| Fit | | `just fitcheck` against both PCB STEPs and the J2 envelope: **0 mm³** (CI job 126392436085) | PASS |

**Contacts.** The drawing numbers the contacts but does not print T/R1/R2/S. The order above
follows its schematic and matches the KiCad names. A community library entry (Flux) gives 2 = R1,
3 = R2, 4 = T instead. The link works either way, because both halves use the same footprint on a
straight cable. Only the §6.2 hot-plug argument (VLINK on Ring2, next to the sleeve) depends on it.
Check one jack with a plug and a meter before relying on that argument.

## G3: parts, stock and track width

**Sources:**

- JLC's component records (`getComponentDetail`: library type, SMT or THT, stock, attrition, the
  "no longer manufactured" note), read by `pcb/scripts/jlc_check.py --stock` through
  `tests/integration/stock.py`;
- JLC's [PCB capabilities](https://jlcpcb.com/capabilities/pcb-capabilities) and
  [PCBA price page](https://jlcpcb.com/help/article/pcb-assembly-price) (updated 2026-10-22).

Stock on **2026-11-04 at 05:17 UTC**, for 5 assembled boards per half. Both halves draw on the
same stock. "Need" is the quantity for both designs, plus JLC's attrition, and never less than 50:

| LCSC | Refs | Part | JLC library | Process | Need | JLC stock | Result |
|---|---|---|---|---|---|---|---|
| C2040 | U1 | RP2040 | extended | SMT | 50 | 58 844 | PASS |
| C97521 | U2 | W25Q128JVSIQ | basic | SMT | 50 | 74 052 | PASS |
| C49304726 | Y1 | YXC XL2EL89CRI-111YLC-12M, 12 MHz | extended | SMT | 50 | 13 833 | PASS |
| C51118 | U3 | AP2112K-3.3TRG1 | extended | SMT | 50 | 12 075 | PASS |
| C7519 | U4, U5 | USBLC6-2SC6 | extended | SMT | 50 | 28 267 | PASS |
| C8598 | D1 | B5819W | basic | SMT | 50 | 826 670 | PASS |
| C70069 | F1 | nSMD025-24V | extended | SMT | 50 | 18 951 | PASS |
| C165948 | J1 | HRO TYPE-C-31-M-12 | extended | SMT | 50 | 165 043 | PASS |
| C95562 | J2 | HRO PJ-320D-4A | extended | SMT | 50 | 5 513 | PASS |
| C27985230 | J3 | HC-PM254-5.0H-1x5PZ socket | extended | **THT** | 50 | 6 294 | PASS |
| C455280 | SW1, SW2 | TS-1088R-02026 | extended | SMT | 50 | 124 616 | PASS |
| C41430893 | SK101–SK137 | HanElectricity CPG151101S11-16 | extended | SMT | 374 | 229 543 | PASS |
| C81598 | D101–D137 | 1N4148W | basic | SMT | 398 | 3 815 633 | PASS |
| C25905 | R1, R2 | 5.1 kΩ 0402 | basic | SMT | 50 | 4 789 167 | PASS |
| C2909343 | R3, R4 | 27 Ω 0402 | extended | SMT | 50 | 252 149 | PASS |
| C11702 | R7, R9, R11, R12 | 1 kΩ 0402 | basic | SMT | 60 | 21 052 308 | PASS |
| C25744 | R5, R6, R8, R10, R13 | 10 kΩ 0402 | basic | SMT | 70 | 15 634 607 | PASS |
| C1525 | C5, C8–C17 | 100 nF 0402 | basic | SMT | 130 | 33 658 574 | PASS |
| C52923 | C4, C18, C19 | 1 µF 0402 | basic | SMT | 50 | 10 144 033 | PASS |
| C15525 | C1–C3 | 10 µF 0402 | basic | SMT | 50 | 9 704 103 | PASS |
| C1557 | C6, C7 | 27 pF 0402 | extended | SMT | 50 | 294 001 | PASS |

- **Replaced parts (ELEC-1).** C2803348, the Kailh socket, was discontinued at both shops. C113767,
  the flash, was "no longer manufactured", and C91749, the crystal, was down to 19. Their
  replacements are C41430893, C97521 and C49304726. `stock.py` and `netcmp.py` fail if a retired
  number comes back.
- **Alternates**, re-checked on 2026-11-04: C49352235 (socket, 26 943), C9002 (crystal, basic,
  286 104) and C46061764 (5.7 mm socket, 4 487). C46061764 does not fit the display pocket at full
  tolerance; see [ordering-jlcpcb.md](ordering-jlcpcb.md#if-a-part-is-out-of-stock).
- **PTC.** C70069 is WS2's choice for the spec's "PTC 1206, 250 mA hold" (WS2a-4): 250 mA hold,
  500 mA trip, 24 V.
- **Fees.** In Standard PCBA, JLC charges every unique part the same $1.53 loading fee, basic or
  extended. The spec's extended-part list no longer prices anything.
- **Track width and rules.** JLC makes 1–2 layer boards down to 0.10 mm track and 0.10 mm space,
  vias down to 0.15 mm drill and 0.25 mm pad, and needs copper ≥ 0.2 mm from a routed edge. The boards use a 0.127 mm minimum track and clearance rule. The
  narrowest track is 0.135 mm, signal tracks are 0.15–0.18 mm, every via is 0.3 / 0.6 mm (331 left,
  389 right), and the copper-to-edge rule is 0.5 mm: **PASS** (BOARD-7, BOARD-14).
- **Placement file.** `cpl_check.py` places JLC's own footprint of every part, both sides, where
  the CPL puts it: **119 of 119 per half** ([order package](#order-package), PKG-2). JLC does not
  document its bottom-side CPL convention, so its placement preview is the last check
  ([checklist](ordering-jlcpcb.md#placement-preview-checklist)).
- **Assembly rules.** Several parts sit closer than 2.5 mm to the board edge (J1 and J2 overhang
  it), so the order uses the customer panel with rails, a routed slot and mouse-bites, and no tab
  in front of J1 or J2 (BOARD-7, PKG-1).

## Review fixes

A post-integration review on 2026-11-02 found defects that the checks above did not catch. They
were fixed on `main` (deviations REVIEW-FIX-1 to -8). The later turnkey changes kept or superseded
them:

| Finding | Fix | Since then |
|---|---|---|
| The display's PIO SPI took GP0 (UART0 TX) on its first transfer: no TRRS link on any build | `miso-gpios` = MOSI on both targets (REVIEW-FIX-1) | unchanged; `test_pins.py` fails a PIO SPI pin on a UART, row or column |
| Right-central build had no USB product name | `ZMK_KEYBOARD_NAME` on both halves | unchanged |
| Left 3V3 caps reached U1 only through a 75–86 mm detour | caps at the five U1 supply exits on locked copper (REVIEW-FIX-2) | kept; their GND returns are now gated too (BOARD-14) |
| Vias in SMD pads | router, session import and a check keep them out (REVIEW-FIX-3) | unchanged |
| The fit check ignored J1, J2, J3 + module and the sockets | their layout envelopes join the STEP (REVIEW-FIX-4) | J3 has its own STEP model now (ELEC-3); J2's envelope is the drawing size (BOARD-13) |
| CPL had no JLC rotation corrections | `jlc_rotations.csv` from a community table (REVIEW-FIX-5) | **superseded**: the U1 and J1 rows were wrong and 3 rows were missing. Every row is now derived from JLC's own footprints and proven by `cpl_check.py` (PKG-2) |
| Window hid the header end of the viewing area | window centred on the viewing area (REVIEW-FIX-6) | kept; it follows the moved header |
| Stabiliser cut-outs faced away from the PCB holes | `layout.stab_dir` for both, Cherry cut-out (REVIEW-FIX-7) | unchanged |
| COL0/COL1/XOUT on B.Cu under Y1 | R7 beside Y1, locked XOUT, B.Cu keepout (REVIEW-FIX-8) | unchanged |

The two notes this page used to carry are closed. The completion router no longer depends on the
host (BOARD-2), and `prune.py` leaves no unlocked dangling copper (BOARD-4, BOARD-14).

## Open items that block ordering

None. The five items WS5 listed are done:

| # | Gate | Item | Done in |
|---|---|---|---|
| 1 | G1 | J3 pin 1 at high x on both halves | BOARD-1 (`bf7a642`), gated by ELEC-8 |
| 2 | G1 | J3 row at y 39.925, so the module stays inside the pocket | BOARD-1 |
| 3 | G1 | Window centred on the viewing area | REVIEW-FIX-6 |
| 4 | G2 | TRRS body at the drawing size, relieved in the case | BOARD-13 (`68f812e`), CASE-9 (`dec5f7b`) |
| 5 | G3 | Discontinued socket replaced; flash and crystal swapped | ELEC-1 (`f5f051d`), boards re-placed in BOARD-1 |

## Not verified until a board is built

Nothing below blocks the order. Each item can only be confirmed on the first assembled boards:

- **JLC assembly.** Whether JLC solders the C41430893 sockets cleanly: there is no field report of
  this second-source part. Whether JLC's viewer applies the bottom-side CPL as KiKit writes it:
  check it in the preview.
- **Firmware on hardware.** That the displays light up and read upright (else use
  `CONFIG_WORXBOARD_DISPLAY_ROTATION_270`), the wired split, the forwarded lock indicators, the
  role-swap builds, and the XOSC start-up with the YXC crystal (64× delay, WS1-9). The LVGL heap use
  on 32-bit ARM has not been measured (WS1-8).
- **J2 contacts.** Check the T/R1/R2/S naming with a plug and a meter (G2 note).
- **Case.** That the USB-C and TRRS plugs seat fully, the BOOT/RESET pin holes reach the buttons,
  and the C6R1 keycap clears the display module's far end. Check these on a 3D-printed test top
  first ([case.md](case.md#before-machining)).

Rev B adds these ([deviations REVB-1 and REVB-2](deviations.md#revb-rev-b-per-key-rgb-display-setback-and-review-fixes-layout-pcb-firmware-case-docs),
[electrical.md](electrical.md#per-key-rgb-rev-b), [firmware.md](firmware.md#known-issues)):

- **LED assembly.** That the fab places all 37 reverse-mount SK6812MINI-E per half in their cutouts,
  flat and on their pads: `cpl_check.py` accepts 55 % of each terminal on its pad for this part, not
  the usual 75 %, because JLC's leads start over the cutout. Whether the fab's viewer shows the
  bottom-side LEDs as the placement file means them: check them in the placement preview.
- **LED chain.** That every LED lights, in chain order (row 0 inward, row 1 outward, row 2 inward,
  C6R2, row 3 outward, row 4 inward, then the thumbs T5, T4, T3, T2, T0, T1), in the right colour
  order (GRB).
- **VLED switch and limit.** That U6 keeps VLED off until the firmware drives GP23, switches it with
  the underglow (toggle-off and idle-off), and limits a short or the inrush into the 37 × 100 nF and
  C20 to about 0.45 A (±25 %), as R14 15k sets it.
- **U7 waveform.** That GP22's 800 kHz signal (T0H 375 ns, T1H 750 ns) reaches LED101 with clean
  edges through U7 at the VLED level and R16's 470 Ω, on USB (VSYS about 4.6 V) and over the cable
  (about 4.4 V).
- **Brightness and current.** The real current per half at the 8 % cap, at full white and with the
  LEDs dark (estimated at about 107–129 mA plus 22 mA and ~30 mA of logic), against the right half's 250 mA through F1 and
  the left port's 500 mA for both halves; and that the cap holds in every effect.
- **RGB over the split.** That a press on the left half sets the right half, and that one or two
  presses of the toggle bring the halves back in step if they ever disagree.
- **Right-half settings writes.** The right half now keeps its own RGB state in flash. The RP2040
  flash driver locks interrupts while it writes, about a minute after an RGB change or an idle
  transition; whether that drops a frame on the 115 200 baud split UART is unmeasured. Also that both
  halves restore their state after a power cycle.
- **Display setback fit.** That the nice!view, set 1.0 mm back, plugs into J3 and lies in the pocket
  under the moved window, and that the C6R1 keycap clears it at bottom-out (the module now ends
  about 0.2–0.3 mm short of the key well). Check it on the 3D-printed test top.
- **Plug-in capacitance.** That the hosts you use accept about 40 µF on VSYS at plug-in (both
  halves together, above USB's nominal 10 µF); almost every host does (REVB-3).
