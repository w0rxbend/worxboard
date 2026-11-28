# Status

The resume point for the production-readiness workflow ([`GOALS.md`](GOALS.md),
[`PLANS.md`](PLANS.md)). Update it at the end of every task: the current state, then one log line.

## Current state

- **Level:** L0. The design passed its own gates; Phase 0 review is done. Target: L1, desk-verified.
- **Phase:** 1, desk fixes with no copper change.
- **Next task:** T-04 (SK6812 timing in the DTS comment and in `fw-check`).
- **Board revision:** rev B, as committed at `b3728c9` (tag `v0.2.0-revB`, a pre-release). Not built.
- **Last verified commit:** `b3728c9`. CI green, DRC/ERC 0 errors, 176 tests passed (see PLANS.md Phase 0).

## Open findings

| ID | Sev | Outcome |
|---|---|---|
| PR-01 | BLOCKER | open: order-day stock check (T-12) |
| PR-02 | MAJOR | open: waiting on D-1 |
| PR-03 | MAJOR | fixed: T-01 (`prod/T-01`) |
| PR-04 | VERIFY | open: T-07, then D-2 |
| PR-05, -06, -07, -14, -16 | MINOR / COSMETIC | open: waiting on D-3 |
| PR-09 | VERIFY | fixed: T-02 (`prod/T-02`). How much light reaches the cap through the slot is a T-14 bring-up check |
| PR-08, -18, -19 | VERIFY | open: T-13, T-12, T-14 |
| PR-10, -11 | MINOR | open: waiting on D-4 |
| PR-12 | MINOR | fixed: T-01 (`prod/T-01`) |
| PR-15 | MINOR | fixed: T-03 (`prod/T-03`) |
| PR-13, PR-17 | MINOR / COSMETIC | accepted: documented hot-plug rule; intended pin-in-paste mismatch |
| PR-R1 | — | rejected: the datasheet keeps the current WS2812 waveform; T-04 records it |

## Waiting on owner

Ask these at Checkpoint 1. Recommendations and trade-offs are in PLANS.md "Owner decisions".

- D-1. LED pads: keep and ask JLC (recommended), or go back to stock pads (copper change)?
- D-2. Crystal: keep and test, or switch to a CL 10–12 pF, ESR ≤ 50 Ω part before ordering (recommended)?
- D-3. Batch the MINOR copper fixes into a rev B.1 re-route before ordering?
- D-4. RGB: explicit on/off instead of toggle (recommended)? LEDs during USB suspend?

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
