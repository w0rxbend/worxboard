# Status

The resume point for the production-readiness workflow ([`GOALS.md`](GOALS.md),
[`PLANS.md`](PLANS.md)). Update it at the end of every task: the current state, then one log line.

## Current state

- **Level:** L0. The design passed its own gates; Phase 0 review is done. Target: L1, desk-verified.
- **Phase:** 2, applying the owner's decisions.
- **Next task:** Checkpoint 2 (L1 desk-verified): the owner merges PRs #3–#11, and CI's `rebuild` and `production` jobs pass on `main`. Then T-12 on the order day.
- **Board revision:** rev B, re-routed on `prod/T-09` for the crystal swap (REVB-10). Not built. The tag `v0.2.0-revB` is the routing before the swap.
- **Last verified commit:** `b3728c9`. CI green, DRC/ERC 0 errors, 176 tests passed (see PLANS.md Phase 0).

## Open findings

| ID | Sev | Outcome |
|---|---|---|
| PR-01 | BLOCKER | open: order-day stock check (T-12) |
| PR-02 | MAJOR | open until file confirmation: T-08 put the question in the JLC remark; JLC's answer closes it (T-12) |
| PR-03 | MAJOR | fixed: T-01 (`prod/T-01`) |
| PR-04 | VERIFY | fixed in design: T-09 (`prod/T-09`) swapped Y1 to C20625731 with 15 pF caps. Bring-up step 2.7 confirms it |
| PR-05, -06, -07, -14, -16 | MINOR / COSMETIC | deferred to rev C: D-3 = no batch, because D-1 keeps the copper |
| PR-09 | VERIFY | fixed: T-02 (`prod/T-02`). How much light reaches the cap through the slot is a T-14 bring-up check |
| PR-18 | VERIFY | open: the JLC remark asks for the cutter (T-08); JLCCNC's switch-hole corners stay for T-12 |
| PR-08, -19 | VERIFY | open: T-13, T-14 |
| PR-10 | — | withdrawn: the central relays the toggle as an absolute on/off |
| PR-11 | MINOR | documented: T-11, `firmware.md` Known issues |
| PR-12 | MINOR | fixed: T-01 (`prod/T-01`) |
| PR-15 | MINOR | fixed: T-03 (`prod/T-03`) |
| PR-13, PR-17 | MINOR / COSMETIC | accepted: documented hot-plug rule; intended pin-in-paste mismatch |
| PR-R1 | — | rejected: the datasheet keeps the current WS2812 waveform; T-04 put the window in the DTS comment and in `fw-check` |

## Crystal candidates (T-07, for D-2)

Read on 2026-11-27 from LCSC's product API (parameters) and JLC's component API (library, stock),
the same endpoints `tests/integration/stock.py` uses. The filter is 12 MHz, SMD3225-4P, CL ≤ 12 pF
and ESR ≤ 50 Ω. Load caps ≈ 2 × (CL − about 3 pF stray).

| LCSC | Part | CL | ESR | JLC | JLC stock | Caps | Verdict |
|---|---|---|---|---|---|---|---|
| [C20625731](https://jlcpcb.com/partdetail/AbraconLlc-ABM8_272T3/C20625731) | Abracon ABM8-272-T3 | 10 pF | 50 Ω | extended | 6 264 | ~15 pF | **meets both limits.** The crystal of Raspberry Pi's RP2040 reference design |
| [C5182759](https://jlcpcb.com/partdetail/C5182759) | Yajingxin TX322512M4FBCE2T | 12 pF | 60 Ω | extended | 2 458 | ~18 pF | ESR 10 Ω over: second choice |
| [C845582](https://jlcpcb.com/partdetail/C845582) | NDK NX3225GA-12.000MHz-EXS00A | 12 pF | not listed | extended | 4 810 | ~18 pF | read the datasheet's ESR first |
| [C2875246](https://jlcpcb.com/partdetail/C2875246) | JSCJ CJ13-120001210B20 | 12 pF | not listed | extended | 7 045 | ~18 pF | read the datasheet's ESR first |
| [C50430](https://jlcpcb.com/partdetail/C50430) | YXC X322512MMB4SI | 10 pF | 80 Ω | extended | 8 353 | ~15 pF | ESR as high as the current part |
| C49304726 (current) | YXC XL2EL89CRI-111YLC-12M | 18 pF | 80 Ω | extended | **1 753** | 27 pF | stock down from 13 833 on 2026-11-04 |
| C9002 (documented fallback) | YXC X322512MSB4SI | 20 pF | 80 Ω | basic | 494 953 | ~33 pF | the worst margin of the list |

Rejected for stock under 50 or high ESR: C596905, C276421, C1986854 (ESR 120 Ω), C5765982 (13 in stock),
C1986039, C2650486, C5835798, C6525564 (0 in stock), C518157 (no ESR listed, 707 in stock).

If D-2 is (b), T-09 uses C20625731 with C6/C7 at 15 pF. Check the cap value against the RP2040
hardware design guide's minimal design, and add JLC's footprint record of the part to `jlc_footprints.json`.

## Owner decisions (2026-11-27, T-06)

- D-1 = (a). Keep the LED pads. Ask JLC about the joint at file confirmation, and order spares.
- D-2 = (b). Swap the crystal to C20625731 (ABM8-272-T3) before ordering.
- D-3 = no batch. The copper fixes wait for rev C, since D-1 keeps the copper.
- D-4 = keep `RGB_TOG` (revised 2026-11-28, after PR-10 was withdrawn). Suspend stays as it is, with a doc note.

## Waiting on owner

Nothing.

## Log

- 2026-11-26. Phase 0 done at `b3728c9`: four independent reviews (electrical, layout, firmware,
  mechanical and order packages) and datasheet checks of the SK6812MINI-E, SY6280AAC and
  SN74LV1T34. No BLOCKER in the board. 19 findings and one rejected proposal recorded in PLANS.md.
  GOALS.md, PLANS.md and STATUS.md added.
- 2026-11-27. T-01 done on `prod/T-01`: rev B values for F1 and R11/R12 across the README and docs,
  rev A records labelled, rev B placement proofs in the README, PR-12 note in `electrical.md`.
  `layout.json` changed only in two GPIO notes, which the PCB seed (`place.layout_seed`) does not read.
- 2026-11-27. T-02 done on `prod/T-02`: the HanElectricity drawings of all four LCSC switches show
  a transparent top cover and a south slot (9.40 × 2.70 mm) over the LED. Cited in `shopping-list.md`.
- 2026-11-27. T-03 done on `prod/T-03`: `tests/integration/test_datasheet_pins.py` holds U3–U7 and the
  37 LEDs per half to their datasheet pin tables (pages cited), checks the LED data direction and
  the chain head at R16, and proves itself on two mutated copies. The table lives in the test, not
  a JSON file: it has one reader. 14 tests, all pass.
- 2026-11-27. T-04 done on `prod/T-04`: `fw_check.py` computes T0H/T1H/T0L/T1L from `bit-waveform` and
  `frequency` and fails outside the SK6812MINI-E window; both board DTS comments cite it. Passes on
  the Phase 0 left and right builds; 5 new test cases.
- 2026-11-27. T-05 done on `prod/T-05`: `docs/bringup.md`, six stages (inspection, first power with 20
  cold starts, firmware and split, LEDs and VLED with the current at the cap, displays and long runs,
  fit), a results table per half, and a coverage table that maps every item of verification.md's
  "Not verified" list, PR-04 and PR-19 to its steps. Linked from verification.md.
- 2026-11-27. T-07 done on `prod/T-07`: 17 crystals checked. Only C20625731 (ABM8-272-T3) meets
  CL ≤ 12 pF and ESR ≤ 50 Ω. Phase 1 is complete; Checkpoint 1 asks D-1 to D-4.
- 2026-11-27. Checkpoint 1: the owner answered D-1 (a), D-2 (b), D-3 no batch, D-4 explicit on/off.
- 2026-11-28. PR-10 withdrawn: ZMK's central relays the toggle as an absolute on/off
  (`behavior_rgb_underglow.c:146`). The owner revised D-4 to keep the toggle. T-11 done on `prod/T-11`:
  the pre-enumeration and suspend current note in `firmware.md` (PR-11).
- 2026-11-28. T-08 done on `prod/T-08`: the JLC remark (panel and bare board) asks to confirm the
  reverse-mount LED joint and to route the cutouts with a cutter of 1.0 mm or less. Both packages were
  regenerated; only the READMEs and order zips changed, and the left rebuild is byte-identical.
  The PCBWay remark (200 characters) is unchanged.
- 2026-11-28. T-09 done on `prod/T-09`: Y1 is C20625731 (ABM8-272-T3), C6/C7 are 15 pF C1548, as in
  the RP2040 hardware design guide §2.3 (REVB-10). The new schematic reseeds placement, so both
  boards were rebuilt from scratch and **re-routed**: DRC 0/0/0, `checks.py` 15/15, netcmp, CPL
  201/201, `jlc_check` 12/12, fit check 0 mm³. The first rebuild crashed in `checks.py` `GndRaster`:
  the router laid a GND track on In2, a layer the raster did not model. The raster now leaves In2
  out, which can only undercount GND copper. The deferred copper findings still hold on the new
  copper: left VBUS has 37 segments at 0.25 mm (PR-05), and there are 36/47 dangling locked vias (PR-06).
