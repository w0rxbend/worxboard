# Plan: rev B to production

Goals and the definition of done are in [`GOALS.md`](GOALS.md). Live progress is in
[`STATUS.md`](STATUS.md). This file has the review findings (`PR-*`), the owner decisions (`D-*`)
and the tasks (`T-*`), in the order they run.

## How a workflow run uses this file

1. Read `STATUS.md`. It names the current phase and the next task.
2. Take the first task that is unchecked, has all its dependencies done, and is not tagged **[owner]**.
3. Work on a branch `prod/<task-id>`. Open a PR to `main`. Each task is one PR.
4. Run the task's **Verify** commands. Then run the Definition of Done below. Both must pass.
5. Tick the task here, add a line to the `STATUS.md` log, and set the next task.
6. When the next task is **[owner]**, or a decision `D-*` is open, write the question under
   "Waiting on owner" in `STATUS.md` and stop. Stop at the same point if you find a new BLOCKER.

A new finding gets the next free `PR-` number, a row in the findings table and a task. Never
renumber the existing ones.

### Definition of done (every task)

- CI is green on the PR: `layout`, `firmware`, `pcb`, `case`.
- `just layout-check`, `just docs-check` and `uv run pytest layout/tests case/tests tests/integration -q` pass locally.
- A task that changes a board also passes `just pcb-drc <side>` and `just pcb-production-check <side>`
  for both sides, and commits the regenerated boards, renders and `pcb/production/`.
- A design change has a `docs/deviations.md` entry and a `CHANGELOG.md` line under `[Unreleased]`.

## Phase 0: baseline review (done 2026-11-26, at `b3728c9`)

Four independent reviews ran against the committed rev B: electrical, PCB layout, firmware against
hardware, and mechanical fit with the order packages. The three parts with custom symbols were
checked against their datasheets from LCSC.

| Check | Result |
|---|---|
| KiCad 10.0.8 DRC, both halves | 0 errors, 0 unconnected, 0 parity issues. Warnings only: silk (~190), dangling locked vias and tracks (L 36 + 3, R 46 + 4), J1 `lib_footprint_mismatch` |
| ERC, both halves | 0 errors. 37 `lib_symbol_mismatch` warnings (the 1N4148W symbol) |
| `pytest layout/tests case/tests` / `tests/integration` / `firmware/zmk/tests` | 48 / 118 / 10 passed, 0 skipped |
| Firmware build, offline | left central and right peripheral built; `fw-check` passed; rotation host test passed |
| Case model, fit check, corners, `production-check` | pass; 0 mm³ interference; 15 files identical; plates byte-identical |
| BOM / CPL / gerbers | 201 parts per half (53 top, 148 bottom), 1:1 designators, complete 4-layer gerber set, order zips equal the loose files |
| CI on `main` | green (layout, firmware, pcb, case, pages) |

Datasheet facts (LCSC PDFs, fetched 2026-11-26). All of these match the design:

| Part | Fact | Source |
|---|---|---|
| SK6812MINI-E, C5149201 | Pins 1 GND, 2 DIN, 3 VDD, 4 DOUT. VDD 3.7–5.5 V. VIH 0.65 × VDD | rev B/1, p. 5 and p. 6 |
| SK6812MINI-E | T0H 0.25–0.40 µs, T1H 0.70–1.00 µs, T0L ≥ 0.80 µs, T1L ≥ 0.20 µs, reset > 200 µs | p. 7 |
| SK6812MINI-E | Recommended pads 1.8 × 0.82 mm, 1.5 mm pitch, running out from the body edge | p. 5 |
| SY6280AAC, C55136 | Pins 1 OUT, 2 GND, 3 ISET, 4 EN, 5 IN. Ilim = 6800 / Rset (A, Ω). EN high = on. 150 Ω output discharge | p. 1–2 |
| SN74LV1T34DBVR, C100024 | Pins 1 NC, 2 A, 3 GND, 4 Y, 5 VCC. 5 V-tolerant input. 3.3 V to 5.0 V up-translation at VCC 5 V | p. 1 |

**Verdict: no BLOCKER in the board, the firmware or the case.** The only order blocker is the
stock check (PR-01). The highest build risks are the LED solder joints (PR-02) and the crystal
start-up (PR-04).

## Findings

Severity: **BLOCKER** stops the order. **MAJOR** is a likely failure or a misleading order doc.
**MINOR** is a reliability or margin issue. **VERIFY** can only be closed on a datasheet, at the fab
or on a built board. **COSMETIC** has no effect on function.

| ID | Sev | Area | Finding | Fix | Task |
|---|---|---|---|---|---|
| PR-01 | BLOCKER | order | The G3 stock check has never run for rev B. The G3 table in `docs/verification.md` is rev A's (C70069, 21 lines). The new lines C5149201, C55136, C100024, C19702, C70076 and C25117 have never been stock-checked | Run `just pcb-stock left 5` and `right 5` on the order day. Rewrite the G3 table | T-12 |
| PR-02 | MAJOR | PCB | LED joints. `gen_footprints.py` moves the stock pads 0.1 mm out (x 2.15–3.5) so copper stays 0.35 mm from the cutout. Only 57 % of each JLC lead (x 1.55–2.94) sits on its pad; stock gives 64 %, and `cpl_check.py` was lowered to 55 % to pass. One open DIN/DOUT joint darkens the rest of the chain | Decision D-1 | T-08 |
| PR-03 | MAJOR | docs | Rev A values left in the docs: `README.md` F1 "nSMD025-24V, 250 mA, C70069" (l. 92, 145, 159, 163, 636), TRRS "1 kΩ" (l. 169), tag list (l. 616), rev A cost (l. 307), CPL table "rev A's" (l. 334). `layout/pins.py:34-35` "1k", copied into `layout.json` and `docs/pinout.md`. `docs/buildguide_en.md:140`, `docs/bom.md:70, 111`, `docs/verification.md:51-57` (unlabelled rev A summary), `:406` (250 mA), `docs/ordering-jlcpcb.md:319` (rev A cost), `fw_check.py:12` (says idle-off) | Correct each to the rev B value. Regenerate `layout.json` and the generated docs | T-01 |
| PR-04 | VERIFY | electrical | Crystal C49304726: CL 18 pF and ESR up to 80 Ω with 27 pF caps and 1 kΩ on XOUT. The RP2040 reference is CL 10 pF and ESR 50 Ω, so the oscillator needs about 5× the gain margin. The app waits 64× (`worxboard.dtsi:157`), but the boot ROM uses its own fixed XOSC wait. If the crystal starts late, BOOTSEL never enumerates and the half cannot be flashed. Corne v4.1 runs the same caps with a 100 Ω part | Decision D-2 | T-07, T-09 |
| PR-05 | MINOR | PCB | Left VBUS has 29 segments necked to 0.25 mm within 6 mm of J1. The right half is 0.5 mm everywhere. The worst case is about 0.95 A (U6 limit plus F1 to the far half plus logic), against about 0.88 A for a 10 °C rise | `complete_routes.py:40`: no 0.25 fallback for VBUS, or a locked 0.5 mm J1 VBUS bridge in `route_critical.py` | T-10 (D-3) |
| PR-06 | MINOR | PCB | Dead locked copper: `route_critical.leds()` (`:661`) lays the DIN/DOUT via spurs even when the F.Cu lane fails. About 20 one-sided vias per half, plus pass-through COL vias. The BOARD-14 counts are stale (29/5 and 34/3, now 36/3 and 46/4) | Skip the spurs when the lane fails, or add them unlocked so `prune.py` removes them | T-10 (D-3) |
| PR-07 | MINOR | PCB | IOVDD pin 22's nearest cap (C18) is 8.23 mm away, with 11.64 mm of copper against the 12 mm gate in `checks.py:65` | Put a 100 nF next to pin 22 in `place.py` | T-10 (D-3) |
| PR-08 | VERIFY | case | The stabiliser cut-out faces the PCB's Ø4.0 holes. Nobody has checked this against Cherry's drawing | Clip a 2u stabiliser into the printed test top | T-13 |
| PR-09 | VERIFY | order | Nobody has confirmed that the shopping-list switches (C49234236–C49234238) have a south-facing LED window | Check the switch drawing, or name a known windowed switch | T-02 |
| PR-10 | MINOR | firmware | `&rgb_ug RGB_TOG` (`config/worxboard.keymap:63`) toggles each half's own saved state. One missed press leaves the halves inverted | Decision D-4 | T-11 |
| PR-11 | MINOR | firmware | VLED is on at boot and during USB suspend. That is about 105–135 mA before enumeration, against 100 mA, plus about 60 µF on the bus. No host is known to enforce either | Decision D-4 | T-11 |
| PR-12 | MINOR | electrical | Split-power mode (JP1 cut) with one half unpowered: about 3 mA flows through the TX high and 940 Ω into the dead RP2040's RX clamp and phantom-powers its 3V3 | Document it in `electrical.md` | T-01 |
| PR-13 | MINOR | electrical | TRRS hot-plug with both halves powered: Ring2 crosses the far sleeve, and a PTC does not limit microsecond surges. This is already documented, with silkscreen | Accept. A second SY6280 on VLINK is the rev C option | — |
| PR-14 | MINOR | PCB | U1's exposed pad has 9 open 0.3 mm vias. The 4 corner vias sit under paste squares, so expect voids | Move the paste windows off the vias (`gen_footprints.py`), or order plugged vias | T-10 (D-3) |
| PR-15 | MINOR | tooling | No gate holds a custom symbol (U6, U7, LED) to its datasheet pin table. Phase 0 checked them by hand | Add a test that compares the pad nets on both boards with a datasheet pin table | T-03 |
| PR-16 | COSMETIC | PCB | Footprint silk lines are 0.12 mm, below JLC's 0.15 mm | Widen them in `gen_footprints.py` | T-10 (D-3) |
| PR-17 | COSMETIC | PCB | J1 shows `lib_footprint_mismatch` because of the pin-in-paste layers (ORDER-1). This is intended | Accept | — |
| PR-18 | VERIFY | order | The LED cutouts' R0.5 dog-bones clear the body corners only with a cutter of 1.0 mm or less. The case's R0.5 switch-hole corners are exempt from the corner check | Ask JLC (PCB) and JLCCNC (case) at file confirmation | T-12 |
| PR-19 | VERIFY | electrical | Rev B power budget: F1's hold, U6's limit and the 8 % cap are all estimates until measured | Measure in bring-up (`docs/bringup.md`) | T-14 |

### Rejected finding (keep it rejected)

- **PR-R1. "Move the WS2812 waveform from `<3 3 4>` to `<3 2 5>` (T1H 625 ns)."** Two reviewers
  proposed this from memory. The SK6812MINI-E datasheet (p. 7) puts T1H at 0.70–1.00 µs, so 625 ns
  is out of spec. The current `<3>, <3>, <4>` at 800 kHz gives T0H 375 ns, T1H 750 ns, T0L 875 ns
  and T1L 500 ns, all in spec. T1H has 50 ns of margin and T0L has 75 ns. Do not change it.
  T-04 cites the datasheet in the DTS comment so the next reviewer does not try again.

## Owner decisions

Each decision blocks the tasks listed with it. Record the answer in `STATUS.md`.

- **D-1 (PR-02), LED pads.** Recommended: (a).
  - (a) Keep the pads. Ask JLC engineering about the joint at file confirmation, and order spare boards.
  - (b) Go back to the stock pads (64 %, x 2.05–3.4). Copper then comes within 0.247 mm of the cutout:
    JLC's minimum is 0.2 mm, but its routing tolerance can be about ±0.2 mm. The `.kicad_dru` rule
    and `LED_EDGE_CLEARANCE` drop to 0.24. This changes the copper.
- **D-2 (PR-04), crystal.** Recommended: (b).
  - (a) Keep C49304726 and test BOOTSEL cold-start on the first boards.
  - (b) Before ordering, switch to a 12 MHz 3225 part with CL 10–12 pF and ESR ≤ 50 Ω in JLC stock,
    with matching load caps (about 15–18 pF). This is a BOM and value change on the same footprint,
    with no new routing. T-09 finds the candidates first.
- **D-3 (PR-05, -06, -07, -14, -16), batch of copper fixes before the order?** Recommended: yes, as
  one rev B.1 re-route, if D-1 (b) or any other copper change happens. Otherwise none of them needs
  to hold the order.
- **D-4 (PR-10, -11), RGB behaviour.** Recommended: replace `RGB_TOG` with explicit `RGB_ON` and
  `RGB_OFF`, and leave suspend as it is, with a note in the docs.

## Tasks

### Phase 1: desk fixes, no copper change (agent)

- [ ] **T-01. Correct the rev A values in the docs (PR-03, PR-12).**
  - Accept: every location listed in PR-03 states the rev B value. PR-12 is in `docs/electrical.md`. `verification.md`'s rev A summary carries a "rev A" label.
  - Verify: `just layout`, `just docs-gen`, then `just layout-check` and `just docs-check`. `git grep -n -E "C70069|250 mA" -- README.md docs/buildguide_en.md docs/bom.md docs/verification.md` prints nothing. The GPIO0/GPIO1 notes in `pins.py` say 470. The XOUT "1k series" note is correct (R7) and stays.
  - Leave `docs/design.md` (the frozen rev A spec) and the history in `docs/deviations.md` alone.
  - Files: `README.md`, `layout/pins.py` (then the regenerated `layout/build/layout.json` and `docs/pinout.md`), `docs/{buildguide_en,bom,verification,electrical,ordering-jlcpcb}.md`, `firmware/zmk/scripts/fw_check.py`. Size: M.
  - Note: `pins.py` notes feed `layout.json`. Check that nothing downstream hashes them, for example `fwdt.py` or the site.
- [ ] **T-02. Confirm the switches' LED window (PR-09).**
  - Accept: `docs/shopping-list.md` names switches whose drawing shows a south-facing LED window, and cites the drawing.
  - Verify: `just docs-check`.
  - Size: XS. Depends on: none.
- [ ] **T-03. Datasheet pin gate (PR-15).**
  - Accept: a test reads both committed `.kicad_pcb` files and fails unless every pad of U6, U7, every LED, U3 and U4 carries the net its datasheet pin function implies. The datasheet table lives in one data file, with the PDF page cited.
  - Verify: `uv run pytest tests/integration -q`. The test fails if one LED's pads 1 and 3 are swapped in a scratch copy of the board.
  - Files: `tests/integration/test_datasheet_pins.py` and a pin table, for example `pcb/scripts/datasheet_pins.json`. Size: S.
- [ ] **T-04. Put the SK6812 timing in the DTS comment (PR-R1).**
  - Accept: the comment in `worxboard.dtsi:104` cites the datasheet's T0H/T1H/T0L/T1L limits and the margins. `fw-check` fails if the waveform leaves the datasheet window.
  - Verify: `just fw-check-tests`, `just fw`, `just fw-check`.
  - Files: `worxboard.dtsi`, `fw_check.py`, `firmware/zmk/tests/test_fw_check.py`. Size: S.
- [ ] **T-05. Write the bring-up procedure.**
  - Accept: `docs/bringup.md` has numbered steps with a pass value for each:
    - visual and AOI check of the LEDs and sockets;
    - power-up from a current-limited 5 V supply (expected idle current), then the rails VBUS, VSYS, 3V3 and 1V1;
    - BOOTSEL enumeration, 20 cold starts per half (PR-04);
    - flash both halves, then the matrix (every key), the split link, the displays and their orientation;
    - VLED off until GP23, then on; the U6 limit; the U7 waveform; the LED chain order and GRB;
    - the current at the 8 % cap at full white (PR-19); far-half VSYS over the cable;
    - J2 contact naming; the case fit.
  - Each step links to the item of `verification.md#not-verified-until-a-board-is-built` that it closes, and has a results table to fill in.
  - Verify: `just docs-check`. Each item of that `verification.md` section maps to at least one step.
  - Size: M. Depends on: none.

- [ ] **T-07. Crystal candidates for D-2 (PR-04).**
  - Accept: `STATUS.md` lists 12 MHz 3225 crystals in JLC's catalogue with CL ≤ 12 pF and ESR ≤ 50 Ω. For each: LCSC number, basic or extended, stock, CL, ESR, and the load cap value it needs (2 × (CL − about 3 pF stray)).
  - Verify: each row links its LCSC page. Network: yes. Size: XS.

#### Checkpoint 1

- [ ] T-01 to T-05 and T-07 are merged and CI is green on `main`.
- [ ] Ask the owner D-1 to D-4 (write them to `STATUS.md`).

### Phase 2: owner decisions, then the changes they pick

- [ ] **T-06 [owner].** Answer D-1 to D-4 in `STATUS.md`.
- [ ] **T-08. Apply D-1 (PR-02).** (a): put the ask in both order READMEs' JLC remark (`package.py`) and in `docs/ordering-jlcpcb.md`. (b): `gen_footprints.py` `LED_PAD_SHIFT = 0`, the DRU and `LED_EDGE_CLEARANCE` at 0.24, `cpl_check.py` 0.6, then the T-10 rebuild.
  - Verify: the Definition of Done, including the board steps for (b). Depends on: T-06.
- [ ] **T-09. Apply D-2 (PR-04).** Depends on: T-06, T-07.
  - If (a) is chosen: nothing to change. Bring-up's 20 cold starts close it.
  - If (b) is chosen: change `LCSC_XTAL` and the C6/C7 values in `design.py`, add the part to `jlc_footprints.json` and `mpn.json`, and add a deviation entry. Regenerate with `just pcb <side>` and `just pcb-production <side>`.
  - Verify: the Definition of Done with the board steps; `cpl_check` 201 of 201.
  - Network: yes, for LCSC lookups.
- [ ] **T-10. Rev B.1 copper batch (D-3 = yes): PR-05, PR-06, PR-07, PR-14, PR-16.**
  - Do one finding per commit on one branch, then one regeneration of both halves.
  - Accept: left VBUS is ≥ 0.5 mm everywhere. No one-sided locked via is left on the RGB nets. Pin 22 has a cap within 3 mm. The EP's paste windows avoid its vias. Silk is ≥ 0.15 mm. The BOARD-14 counts are updated.
  - Verify: the Definition of Done with the board steps. The `pcb` workflow `rebuild` job reproduces both boards.
  - Size: L. Split it by finding if the routing does not converge. The maze router is sensitive, so check `checks.py` after each change.
- [ ] **T-11. Apply D-4 (PR-10, PR-11).** Keymap bindings, and the suspend note in `docs/firmware.md`.
  - Verify: `just fw-keymap-check`, `just fw`, `just fw-check`.

#### Checkpoint 2 (L1 desk-verified)

- [ ] Every PR-* row is either fixed (with its commit) or accepted (with the reason) in `STATUS.md`.
- [ ] `pcb` workflow green, `rebuild` and `production` jobs included, on the commit to order from.
- [ ] Changelog `[Unreleased]` lists the changes. If the copper changed, the board label reads `rev B.1`.

### Phase 3: order (owner, agent prepares)

- [ ] **T-12 [owner].** On the order day:
  - run `just pcb-stock left 5` and `right 5`, and rewrite G3 in `verification.md` (PR-01);
  - get the rev B cost quote and replace the rev A estimates;
  - at file confirmation, check JLC's placement preview: the bottom-side LEDs, diodes and sockets (the thumb parts are the tell, ORDER-2), the U7 rotation, J1's pin-in-paste remark, the stabiliser hole remark (ORDER-3) and the cutter size (PR-18).
  - The agent prepares a one-page checklist of these in `docs/ordering-jlcpcb.md` beforehand.
- [ ] **T-13 [owner].** 3D-print a test top (`case.md#before-machining`) and check:
  - the 2u stabiliser (PR-08);
  - the USB-C and TRRS plugs seat fully;
  - the display fits under the window, and the C6R1 keycap clears it;
  - the BOOT and RESET holes reach the buttons.
  - Then order the CNC case.

### Phase 4: first article (owner measures, agent records)

- [ ] **T-14 [owner].** Run `docs/bringup.md` on at least 2 kits. Fill in its results tables.
- [ ] **T-15.** Record the results in `docs/verification.md`. Every failure becomes a new PR-* finding with a task.

#### Checkpoint 3 (L3 first article)

- [ ] Every item of `verification.md#not-verified-until-a-board-is-built` has a measured result.

### Phase 5: release

- [ ] **T-16.** Fix the first-article findings. A copper change makes it rev C, with the full pipeline and a new deviation section.
- [ ] **T-17.** Docs pass: the README status, the badges, "Not built" removed, the microsite status, and photos of the built board.
- [ ] **T-18 [owner].** Tag `v1.0.0-rev<X>` as a full (not pre-) release with `release.yml`.

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| A reverse-mount LED joint opens and darkens the rest of the chain | High: a dead row of LEDs, which the owner must rework | D-1. Ask JLC. Order 5+ boards. T-05's AOI step |
| The crystal does not start for the boot ROM, so a half cannot be flashed | High: the half is unusable | D-2 before ordering. 20 cold starts in bring-up |
| The maze router does not converge after a copper change | Medium: rev B.1 is delayed | One finding per commit. Fall back to ordering rev B unchanged, since none of the T-10 items blocks the order |
| JLC reads the bottom-side CPL rotation differently | High: every bottom part is rotated | Check the preview (ORDER-2). The thumb parts are the tell |
| A stock-out on the order day | Medium: delay | `pcb-stock` on the day. `design.py` documents the fallbacks |

## Skipped in Phase 0

- `checks.py` was not re-run by the reviewers: the reviewers' container lacked shapely. CI runs it green on `b3728c9`.
- Experimental firmware rows (role swap, RP2350) were not reviewed.
- The PJ-320D contact naming and the HanElectricity switch drawings have no datasheet in hand.
