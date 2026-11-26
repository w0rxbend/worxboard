# Goals: make worxboard production ready

This file says what "production ready" means for worxboard and when the work is done.
[`PLANS.md`](PLANS.md) holds the tasks and [`STATUS.md`](STATUS.md) says where the work stands.

## Mission

Take rev B from "designed, gates green" to a keyboard that anyone can order from the repository
and build without surprises. The first and main goal is to **verify the current board, rev B, and
fix it if it needs fixing**. Only then order it, build it, and release it.

## Definition of production ready

Four levels. Each level needs the one before it.

| Level | Name | Done when | Who closes it |
|---|---|---|---|
| L1 | **Desk-verified** | Every finding in `PLANS.md` is fixed, or the owner has accepted it in writing. CI is green on the commit. Every custom symbol and footprint has been checked against its datasheet. | Agent, with owner decisions |
| L2 | **Order-ready** | The stock check (G3) has passed on the order day. The JLC DFM and placement previews have been checked. A printed test top fits. The owner has approved the cost. | Owner (the agent prepares it) |
| L3 | **First article passed** | At least 2 kits (4 halves) pass every step of `docs/bringup.md`. Every item in `docs/verification.md#not-verified-until-a-board-is-built` is closed with a measured result. | Owner measures, agent records and fixes |
| L4 | **Released** | No open MAJOR or BLOCKER finding. The fixes from L3 are in (as rev C if the copper changed). Docs match the built board. The release is tagged and published as a full release, not a pre-release. | Agent prepares, owner tags |

## Success criteria for L1, the current target

1. Every finding `PR-*` in `PLANS.md` has an outcome: fixed (with its commit) or accepted (with the reason).
2. A datasheet check covers every part on the board that uses a custom symbol or footprint (U6, U7,
   the LEDs, J2, J3, the hot-swap socket), with the PDF page cited.
3. The full pipeline reproduces the committed boards and order packages byte for byte
   (`pcb` workflow `rebuild` and `production` jobs green).
4. No doc states a rev A value for a part that rev B changed (F1, R11, R12, C1–C3, part counts).
5. `docs/bringup.md` exists and can be followed step by step on the first boards.

## Non-goals

- Per-key colours. ZMK drives the LEDs as underglow.
- The RP2350 board (`worxboard2`). Its firmware stays experimental.
- Wireless, batteries, a new layout, or a new case design.
- Cosmetic DRC warnings (silkscreen over copper, silk clipped by the mask). JLC clips silk on its side.

## Constraints every change must respect

- **The boards are generated.** Change `layout/`, `pcb/scripts/` or `pcb/lib/` and regenerate.
  Never hand-edit a `.kicad_pcb` or `.kicad_sch`. The `rebuild` job fails if you do.
- **Rebuilds are byte-identical.** After a PCB change, run `just pcb <side>` and
  `just pcb-production <side>` for both sides, and commit the boards, the renders and `pcb/production/`
  (`git add -f pcb/production`) together.
- **Every design change gets a deviation entry** in `docs/deviations.md` and a `CHANGELOG.md` line.
- **Pinned tools.** Use the container digests in `tools/images.lock`. Do not bump KiCad or ZMK as part of a fix.
- **Order only from a commit with a green `pcb` workflow.**
- **Human gates.** Ordering, payment and hardware measurements need the owner. An agent prepares them
  and records the results. It never places an order.
