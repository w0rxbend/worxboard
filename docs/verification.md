# Verification

Rev A integration results and the ordering gates of spec §7 (G1 display, G2 TRRS jack, G3 parts).
WS5 checked everything below on **2026-11-02**: `just all` at `d1f2d77` (the last commit before WS5,
which adds only tests, CI and docs), the integration tests at `184671a`, stock at 03:59 UTC. The
gates block **ordering**, not the repository.

## Summary

| Check | Result | Blocks |
|---|---|---|
| [Integration tests](#integration-tests) (`tests/integration/`) | **PASS**: 68 passed, 8 expected failures (the gate findings below), 0 skipped | |
| [`just all` from a clean clone](#just-all-from-a-clean-clone) | **PASS** in 34 min 44 s; both boards rebuilt byte-identical | |
| [CI on `main`](#ci) | **PASS**: every workflow green | |
| [G1 display](#g1-niceview-display) | **FAIL**: pin order right, but J3 pin 1 is at the wrong end; the module and the viewing area sit 0.7 mm and 3.5 mm off the model | PCB and case |
| [G2 TRRS jack](#g2-pj-320d-trrs-jack) | Pad map and height **PASS**; the body is 2.1 mm longer than the case allows for: **FAIL** | case |
| [G3 parts and rules](#g3-parts-stock-and-track-width) | **FAIL**: the hot-swap socket C2803348 is discontinued; track width **PASS** | PCB assembly |

Fixes go back to the owning streams; each row under [Open items](#open-items-that-block-ordering)
names one. The failing gate checks are strict expected failures in `tests/integration/test_gates.py`,
so a fix makes them pass and the marker has to come off with it.

## How to re-run

```sh
just all                                          # layout-check -> fw -> pcb-all -> model -> site
uv run pytest tests/integration -rxs              # pins, gates, release assembly (build outputs optional)
uv run python tests/integration/stock.py --boards 5   # G3 stock on the day of ordering (network)
uv run python tests/integration/release.py        # release assets into dist/
```

Without build outputs the integration tests read the committed boards and board files and skip the
netlist, compiled-devicetree and real-asset cases; after `just all` nothing is skipped.

## Integration tests

`tests/integration/test_pins.py` reads the firmware devicetree (the committed board files of both
targets, and every built `build/fw/<artifact>/zephyr/zephyr.dts`), the PCB (the committed boards,
and the netlists `just pcb-sch` exports) and `layout/pins.py`:

- **Every switch reaches its keymap slot.** For each of the 37 keys per half: the socket's COL net
  and the diode cathode's ROW net, the RP2040 GPIO on each net, the firmware row and column for those
  GPIOs plus `col-offset`, the transform position of that (row, col) and the key `layout.json` puts
  there. This is what proves the right half's reversed `col-gpios` (GP20…GP14, `col-offset = 7`)
  against the shared matrix netlist.
- **TRRS crossover.** Through each jack's 1 kΩ resistors to the UART pins: with a straight cable the
  left TX meets the right RX and the reverse; Ring2 is VLINK and Sleeve GND on both halves.
- **Display header.** J3 pins 1–5 carry the firmware's PIO1 SPI MOSI, SCK and CS GPIOs, 3V3 and GND.
- **Firmware vs `pins.py`.** Rows GP8–GP13 with pull-down, columns GP14–GP20 (reversed on the right),
  UART0 TX GP0 / RX GP1 with input enabled, SPI on GP2/GP3/GP5 with CS active high, for the board
  files and all six compiled builds. Every compiled `zephyr.dts` equals its board files, and the
  RP2350A target has the same pinout.
- **Netlist vs board.** Each netlist part has the same pad nets on the committed board, and the
  RP2040 pin names in the netlist give the QFN numbers that `pins.py` lists.
- **The checks catch what they are for.** Mutated firmware (right columns not reversed, no
  `col-offset`, rows rotated, UART roles swapped) must fail the chain and crossover checks.

`test_gates.py` checks G1 and G2 against the drawings (below). `test_release.py` checks the release
assembly on a synthetic tree and, after `just all`, on the real outputs (gerber zip contents, CPL
header, BOM LCSC column, STEP and UF2 magic numbers), and that `release.yml` runs only on `v*` tags.

Result on the clean-clone outputs below: **68 passed, 8 xfailed** (the 8 gate findings), nothing
skipped. Without any build outputs: 38 passed, 30 skipped, 8 xfailed.

## `just all` from a clean clone

`git clone https://github.com/w0rxbend/worxboard` at `d1f2d77` into an empty scratch directory,
then `just all` with nothing built or cached in the clone: the west workspace, the Freerouting jar,
the container Python packages and the uv environment were created fresh (uv from its local package
cache; the Docker images were already pulled).

`just all` exited 0 after **34 min 44 s** (03:36–04:11 UTC; most of it Freerouting and the
completion router):

| Stage | Result |
|---|---|
| `just layout-check` | 31 passed; `layout.json` and `layout.svg` regenerate with no diff |
| `just fw` | west workspace fetched; all six `build.yaml` rows built a UF2; right peripheral has no `zmk_ble_` / `zmk_battery_` symbols, FLASH 169 196 B (seed + 3 796 B, budget 40 960 B) |
| `just pcb-all` | per half: ERC 0, netcmp 9/9, Freerouting 2.5.0 (25 / 31 nets left for the completion router), DRC with schematic parity 0 violations / 0 unconnected / 0 parity issues, `checks.py` 4/4 (USB pair left 24.73 / 23.92 mm, skew 0.81; right 23.75 / 23.50 mm, skew 0.25; Y1 2.93 mm), `kikit --missingError` gerbers, BOM, CPL, renders, Edge DXF, STEP |
| `just model` | every case check passed; STEP, STL and fit-check DXFs for both halves, legs and caps |
| `just site` | `_site/` 6.6 MB: 8 case parts, 158 PCB components |

Afterwards `git status` in the clone was empty: the rebuilt schematics, **both boards** (placement,
Freerouting, completion), `plates/` and the renders are byte-identical to the committed files. On
those outputs `just fitcheck` reported 0 mm³ against both PCB STEPs, the integration tests passed as
above, and `tests/integration/release.py --version v0.1.0-revA` packed `dist/`: both PCB zips, the
six UF2s, both case zips and `SHA256SUMS.txt`.

## CI

The four workflows that run on a push to `main` passed on every WS5 commit. At `184671a`:

| Workflow | Run | Result |
|---|---|---|
| layout | [41387161014](https://github.com/w0rxbend/worxboard/actions/runs/41387161014) | success |
| firmware (six UF2s, right-half checks) | [41387160982](https://github.com/w0rxbend/worxboard/actions/runs/41387160982) | success |
| pcb (schematics, DRC gate, fab outputs, fit check, from-scratch rebuild of both boards) | [41387161050](https://github.com/w0rxbend/worxboard/actions/runs/41387161050) | success |
| case (model, plates, fit check, renders, order package) | [41387161080](https://github.com/w0rxbend/worxboard/actions/runs/41387161080) | success |

`release.yml` runs only on a `v*` tag push and has not run: no tag or release exists. `pages.yml`
is manual and was not run.

## G1: nice!view display

**Sources:** nice!view pinout, dimension and schematic drawings
([nicekeyboards.com](https://nicekeyboards.com/docs/nice-view/pinout-schematic)); splitkb
[FAQ](https://docs.splitkb.com/product-guides/nice-view/frequently-asked-questions) (36 × 14 × 2.9 mm,
five pins, socket and pins included); viewing area of the Sharp LS011B7DH03 from its
[DigiKey listing](https://www.digikey.com/en/products/detail/sharp-microelectronics/LS011B7DH03/25953418).

| Item | Drawing | Design | Result |
|---|---|---|---|
| Size | 36 (+0.1–0.2 V-cut) × 14 × 2.9: glass 0.9, PCB 1.0, parts below 1.0 | 36 × 14 × 2.9 | PASS |
| Pin order | MOSI, SCK, VCC, GND, CS (schematic J2: SI, SCLK, 3V3, GND, SCS) | J3 pins 1–5: `DISP_MOSI`, `DISP_SCK`, `3V3`, `GND`, `DISP_CS` | PASS |
| Pin-1 end | Front (LCD) view with the header at the bottom: MOSI at the left. Mounted LCD up with the header at the back (low y), MOSI is at **high x** | J3 pad 1 (`DISP_MOSI`) at **low x** on both halves (right x 67.31, left x 182.53) | **FAIL** |
| Header row to the module edge | 1.3 mm; the pins are centred across the 14 mm width | 1.975 mm (header y 40.6, module y 38.625–74.625) | **FAIL** |
| Viewing area | 25.28 × 10.74, starting 4.6 mm from the header-end edge (1.3 + 1.7 to the glass + 1.6) | window 26 × 12 at y 47.0–73.0 | **FAIL** |
| Stack above the PCB | socket body + header spacer + 1.0 + 0.9 | ≤ 8.2 mm (pocket ceiling Z 16.8) | socket + spacer ≤ 6.3 mm |
| CS polarity | active high (LS011B7DH03) | `cs-gpios … GPIO_ACTIVE_HIGH` | PASS |

**Pin-1 end.** With the module plugged in face up, its pins meet J3 reversed: module CS on
`DISP_MOSI` (GP3), GND on `DISP_SCK` (GP2), VCC on 3V3, SCK on GND and MOSI on `DISP_CS` (GP5).
VCC is the middle pin, so nothing is shorted, but the module's clock is tied to ground and no
firmware change can recover it. The display cannot work on the boards as routed.

**Module length.** A module plugged into J3 at y 40.6 (right frame) spans y 39.3–75.3, up to 75.5
with the V-cut, against the pocket's far wall at 75.125. Intersecting a module-sized solid with the
exported case parts (both halves) gives 7.3 mm³ of top-part interference with a 3.0 mm socket +
spacer stack and 7.9 mm³ at 4.5 mm. It clears only when the module underside is above the plate top
(Z 13.6), which needs a 6.0–6.3 mm stack, for example a 3.5 mm low-profile socket and a standard
2.5 mm male-header spacer. A standard 8.5 mm socket breaks the 8.2 mm limit. The board STEP leaves J3
out (WS2c-5), so `just fitcheck` does not see any of this.

**Window.** The viewing area runs y 43.9–69.2 (right frame) and the window 47.0–73.0: the 3.1 mm
nearest the header (about 20 of the 160 pixels along it) is hidden, and 3.8 mm of bezel shows at the far end.
Across, the window is 0.6 mm wider than the viewing area on each side, which is fine. Separately, both
screens are laid out landscape (160 × 68) for an upright module (WS1 open item).

## G2: PJ-320D TRRS jack

**Source:** HRO PJ-320D drawing (rev B, drawn 2016-05-03), the
[LCSC C95562 datasheet](https://www.lcsc.com/datasheet/C95562.pdf).

| Item | Drawing | Design | Result |
|---|---|---|---|
| Height | 5.00 (Ø5.00 barrel, 6.10 × 5.00 body) | ≤ 5.5 (spec), layout 5.5 | PASS |
| Plug axis | centred, 2.50 above the PCB | `axis_z` 2.5, case side notch at 2.5 | PASS |
| Land pattern | pads 1.20 × 2.50 at 3.20 (pin 4), 6.20 (pin 3), 10.20 (pin 2) behind the barrel face on one side and 11.30 (pin 1) on the other, rows ±3.25 off the axis; peg holes Ø1.00 at 1.60 and 8.60 | KiCad `Jack_3.5mm_PJ320D_Horizontal`: R2, R1, T and S at the same positions and sizes; peg holes Ø1.5 (a looser fit) | PASS |
| Contacts | schematic PJ-320D-A: pin 1 is the sleeve; the spring contacts run 4, 3, 2 from the mouth, so 4 = Ring2, 3 = Ring1, 2 = Tip | pads named S, R2, R1, T at those places | PASS, see note |
| Length | 2.00 barrel + 12.10 body = 14.10, 6.10 wide | layout body 12.0 × 6.0 (x 49.0–61.0 right frame) | **FAIL** |

**Contacts.** The drawing numbers the contacts but does not print T/R1/R2/S. The order above follows
its schematic and matches the KiCad names. A community library entry (Flux) gives 2 = R1, 3 = R2,
4 = T instead. The link works either way, because both halves use the same footprint on a straight
cable; only the §6.2 hot-plug argument (VLINK on Ring2 next to the sleeve) depends on it. Check one
jack with a plug and a meter before relying on that argument.

**Length.** The board places the jack correctly (mouth on the x 49.0 edge, pads as drawn), but the
real body runs to x 63.1 (right frame), past Z_TRRS (x < 62.2) and the layout envelope that the case
relief is cut for. Intersecting a 14.1 × 6.1 × 5.0 mm body with the exported case parts gives
16.8 mm³ with the top part and 7.3 mm³ with the spacer, on each half. The board STEP has no model
for J2 (WS2c-2), so the fit check cannot see it.

## G3: parts, stock and track width

**Sources:** the LCSC product API and the JLCPCB assembly-library search (re-run with
`tests/integration/stock.py`), and the JLCPCB
[PCB capabilities](https://jlcpcb.com/capabilities/pcb-capabilities). Stock at 2026-11-02 03:59 UTC
for 5 assembled boards per half (both halves draw on the same stock):

| LCSC | Part | Per board | JLC library | JLC stock | LCSC stock | Result |
|---|---|---|---|---|---|---|
| C2040 | RP2040 | 1 | extended | 63 302 | 54 849 | PASS |
| C113767 | W25Q128JVSIQ | 1 | extended | 163 | 0 | PASS, low; see below |
| C91749 | 12 MHz 3225 crystal (Epson Q22FA23V00418) | 1 | extended | 34 | 30 | PASS for one order; see below |
| C51118 | AP2112K-3.3TRG1 **[G3]** | 1 | extended | 8 430 | 2 780 | PASS |
| C7519 | USBLC6-2SC6 | 2 | extended | 44 941 | 40 640 | PASS |
| C8598 | B5819W **[G3]** | 1 | basic | 981 220 | 510 380 | PASS |
| C70069 | nSMD025-24V PTC, 250 mA hold, 24 V **[G3]** | 1 | extended | 19 363 | 18 780 | PASS |
| C165948 | HRO TYPE-C-31-M-12 **[G3]** | 1 | extended | 198 765 | 179 210 | PASS |
| C95562 | HRO PJ-320D-4A | 1 | extended | 5 743 | 5 620 | PASS |
| C455280 | TS-1088R-02026 | 2 | extended | 133 395 | 126 490 | PASS |
| C81598 | 1N4148W **[G3]** | 37 | basic | 3 755 702 | 2 264 050 | PASS |
| C2803348 | Kailh CPG151101S11 hot-swap socket **[G3]** | 37 | extended | **0** | **0**, discontinued | **FAIL** |
| C25905 | 5.1 kΩ 0402 | 2 | basic | 4 978 661 | 1 954 900 | PASS |
| C2909343 | 27 Ω 0402 | 2 | extended | 285 234 | 252 500 | PASS; extended, see below |
| C11702 | 1 kΩ 0402 | 4 | basic | 21 222 988 | 9 038 500 | PASS |
| C25744 | 10 kΩ 0402 | 5 | basic | 16 412 787 | 0 | PASS (JLC stock) |
| C1525 | 100 nF 0402 | 11 | basic | 35 162 152 | 20 297 100 | PASS |
| C52923 | 1 µF 0402 | 3 | basic | 10 180 553 | 5 925 500 | PASS |
| C15525 | 10 µF 0402 | 3 | basic | 9 991 546 | 5 319 700 | PASS |
| C1557 | 27 pF 0402 | 2 | extended (preferred) | 316 012 | 121 400 | PASS; extended, see below |

- **Hot-swap socket.** LCSC lists C2803348 as discontinued and neither shop has any. JLC stocks
  CPG151101S11-16 as **C41430893** (241 636; brand "HanElectricity") and CPG151101S11-2 as
  C49352235 (36 107). Check the drawing against `SW_MX_Hotswap_Kailh` before switching.
- **Flash.** **C97521** is the same W25Q128JVSIQ (SOIC-8 208 mil) as a JLC **basic** part with
  83 436 in stock: no extended-part fee and no stock risk.
- **Crystal.** 34 at JLC covers one order of 5 + 5 boards. **C9002** (YXC X322512MSB4SI, 12 MHz,
  3225, basic, 314 645) fits the same footprint. Its 20 pF load against the 18 pF the 27 pF caps
  give pulls it by tens of ppm, far inside the ±2500 ppm USB full speed allows.
- **Fees.** C2909343 and C1557 are extended parts too, which the extended-part list in spec §7 and
  `docs/bom.md` leaves out. JLC marks C1557 as a preferred extended part.
- **Track width.** JLCPCB makes 1–2 layer boards down to 0.10 mm track / 0.10 mm space, vias down
  to 0.15 mm drill / 0.25 mm pad, and copper ≥ 0.2 mm from a routed edge. The boards use a 0.127 mm
  minimum track and clearance rule; the narrowest track is 0.135 mm (three segments on the right
  half), signal tracks are 0.15–0.18 mm, all 702 vias are 0.3 / 0.6 mm and the edge clearance is
  0.5 mm: **PASS**.

## Open items that block ordering

| # | Gate | Fix | Owner |
|---|---|---|---|
| 1 | G1 | Put J3 pin 1 at **high x** on both halves (turn J3 by 180°: pad 1 at right-frame x 77.47, left-frame x 192.69) and re-route the display nets. `layout.display()["header_pins"]` lists pin 1 at low x (WS0-5 left this end provisional). | WS0, WS2 |
| 2 | G1 | Move the J3 row to y **39.925** (module edge + 1.3) so the module spans the modelled y 38.625–74.625, in the same re-placement; or lengthen the case pocket to y ≥ 75.8 below the plate top. | WS0, WS2 (or WS3) |
| 3 | G1 | Centre the window on the viewing area: y = header + 15.94 (55.87 with fix 2, 56.54 without), window y 42.9–68.9 with fix 2. | WS0, WS3 |
| 4 | G2 | Set the TRRS body to 14.1 × 6.1 mm (height 5.0) in `layout/jacks.py` and cut the case relief and spacer over it; the plate between the C6R1 and C6R2 switch cut-outs (y 95.9–110.5) is free. The PCB is unchanged. | WS0, WS3 |
| 5 | G3 | Replace C2803348 (see above) and re-check stock on the order day with `stock.py`. Switching U2 to C97521 and Y1 to C9002 is advised. | WS2, WS4 (BOM) |

Not blocking, for the owning streams: `docs/bom.md` (gates section) and the README status row still
call G1–G3 unchecked and WS5 not started (WS4); both screens need a rotation for the upright module
(WS1).
