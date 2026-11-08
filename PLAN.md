# Continue worxboard rev B

Paused 2026-11-08 17:50 Europe/Kyiv at the user's request. This file is the resume prompt.
`build/HANDOFF-revB.md` is older: its "do not commit" line and its list of running left jobs are
superseded by this file. The commit that added this file is a work in progress. It is not an
orderable rev B.

## Prompt

You are continuing worxboard rev B (per-key RGB, split ErgoDox-style keyboard) in
`/home/worxbend/Projects/Github/worxboard` on branch `main`. The goal is a repo that can be sent
for PCBA and for case manufacture: JLCPCB and PCBWay assembly packages for both halves, and case
files for CNC milling and 3D printing. The board is not orderable until a left half passes and
the gates below have been run on the main tree.

Do not commit or push unless the user asks. Do not delete
`.claude/worktrees/agent-ae9104e520e25a544`. Do not stop Docker containers other than this
repo's `kicad/kicad:10.0.7` and `eclipse-temurin` Freerouting jobs. Leave kafka, kui,
lofi-radio, and twitch-screen alone. The shell is zsh: do not write an unquoted `for` list
over a variable. Do not use `pkill -f`. Never weaken `pcb/scripts/checks.py` (do not raise
`TIE_MAX_MM` or `GND_PIN_MAX_MM`, and do not lower `GND_LINKS_MIN`). Do not move the display,
the LEDs, or the brightness cap. Do not edit `docs/design.md`. Do not upload the current
`pcb/production/` files as rev B; those tracked files are still the rev A package (119 parts).
`pcb/production/` is gitignored except the force-tracked files already in git. `build/` is
gitignored, so the seed-trial trees exist only on this machine.

## Where the work stopped

Rev B content already in this commit:

- SK6812MINI-E under every switch (37 per half), 100 nF per LED, diodes at +8.5 mm.
- U6 SY6280AAC (VSYS to VLED, EN = GP23, 10k pull-down, ISET 15k = 0.45 A), C21/C20 10 uF.
  Data is GP22 to U7 SN74LV1T34 (VCC = VLED) to R16 470 ohm to LED101.
- Display and J3 moved 1.0 mm back (case revision A4). C1–C3 are 10 uF 0603 10 V (C19702).
- Firmware: ZMK underglow on PIO0/GP22, ext-power GP23, BRT_MAX = 8, BRT_MIN = 1, USB 500 mA,
  reset-delay 500 us. Expect 201 parts per half (53 top, 148 bottom) once a board is packaged.
- Host checks that already passed on this machine before the pause: layout pytest,
  `layout.export --check`, ZMK layout/keymap/rotation, 9 firmware regressions. Offline MPN
  scan: 29 LCSC numbers, 0 errors. `just pcb-mpn-check` inside KiCad is still part of the gates.

Routing is seed-dependent. `KIID_SEED` in `pcb/scripts/place.py` is still
`{"left": 0x4, "right": 0x1}`. Change the left seed only when adopting a winner. The committed
`pcb/left` and `pcb/right` boards are placed plus locked critical routes, not autorouted.
A routed board is thousands of segments. `PYTHONHASHSEED=0` and seeded KIIDs make a rebuild
byte-identical only when the scripts and the placement match. A schematic edit reseeds both
halves. Confirm with a from-scratch `cmp`. Do not assume.

Right half is a real pass, on this machine only:

- `build/seedtrials/right-1`, seed 0x1.
- DRC 0/0/0, `checks right: 15 passed, 0 failed`, `netcmp --board` 2/2 (221 footprints).
- U4 pin 2 to J1 GND is 10.3 mm. Its `.kicad_dru` uses the 0.29 mm LED edge rule.
- Adopt this board with the left winner. Do not reroute the right half unless a script change
  moves its copper. Re-laying critical routes after `u4_gnd_left` moved no right-half geometry.

Left half is not a pass. The repeating failure on otherwise clean boards is the USB-clamp
ground, U4 pin 2 to J1 GND. The left is the same circuit as the right and is not a geometric
mirror: U1 is turned, and U6/U7 cannot be mirrored. `usb_right` calls `j1_escapes`. `usb_left`
must not call `j1_escapes` unchanged. The pin-2 via sits between the front-copper USB pair, so
the escape leaves on back copper.

The fix is already in `pcb/scripts/route_critical.py` as `u4_gnd_left`, called from `usb_left`.
It draws a locked 0.5 mm B.Cu track from the U4 pin-2 via, out on U4 +y (the side opposite C2),
into the nearest J1 shell pad. It stays inside the USB keepout gap. On a placed left board that
track is three segments, about 9.1 mm, and `kicad-cli pcb drc` reported 0 violations. The
unconnected count on that unrouted board is the matrix, which the autorouter still draws.
`U4_GND_SIDE` is 1.85 mm. Do not undo the U7 move to `(65.6, 49.0, 180)`.

Left results, all failures, none adopted:

- Old U7 placement `left-1`..`left-9`: do not resume. `left-6` was DRC-clean with U4 at 20.5 mm
  and C5 at 38.8 mm. `left-7`..`left-9` were killed by the 05:20 shutdown.
- `leftB-1` seed 0x1, U7 moved: DRC 0/0/0, U4 13.2 mm, links 1/2, C5 infinite.
- `leftB-2`: COL6, RGB_EN, TP7 open.
- `leftB-3`: COL5 and RUN open.
- `leftB-4`: COL2 open.
- `leftB-5`: DRC 0/0/0, links 2, C5 20.0 mm, U4 infinite.
- `leftB-6`: DRC 0/0/0, links 2, C5 19.0 mm, U4 infinite. Same shape as leftB-5.
- `leftB-7`: COL3 and ROW5 open.
- `leftB-8`: TP6 open.
- `leftB-9`: stopped on purpose during cleanup (exit 137) while COL4, COL6, and QSPI_SD2
  were still open. Cleanup cannot add the clamp ground.
- `leftB-10` seed 0xA and `leftB-11` seed 0xB: placed with the stitch (`left: 495 locked track
  segments`), then stopped during Freerouting at this pause. No `left.ses`. No `trial.done`
  until this pause wrote one that says PAUSED. Those files are not routing results.

`build/seedtrials/right-1` and `leftB-*` are local. They are not in git. If they are gone,
reroute the right half from seed 0x1 before adopting, and start the left seeds again.

A DRC line in `checks.py` can print "0 unconnected" when `kicad-cli` reports unconnected
items. Trust `Found N unconnected` and `still open after completion`. If stage C still has
unconnected items, it runs checks and exits before `gnd_ties` and pin-in-paste. Paste, C5,
and U4 lines on that path are consequences of an open net.

Some early `trial.done` files say `exit 0` because `if ! cmd; then rc=$?` inverted the status.
Trust `pcb-finish failed` in the log. `resume_finish.sh` and `boot_resume.sh` were fixed after
those files were written. `rerun_leftC.sh` writes real exit codes.

## What was stopped

- Freerouting containers for leftB-10 and leftB-11 were stopped. Their process group was
  `run_leftD.sh` PID 2329903. No KiCad or Freerouting container for this repo should be running.
- User timer `worxboard-revb.timer` was disabled and is inactive. The unit files may still
  exist under `~/.config/systemd/user/`. Do not enable the timer until a new batch is launched
  on purpose. `boot_resume.sh` restarts any `build/seedtrials/leftB-*` directory that has no
  `trial.done`. The pause markers exist so a timer start does not resume a partial route.
- The 15-minute Grok scheduler `WORXBOARD-REVB-FACTORY` was deleted.
- The watcher for leftB-10/11 was killed. The watcher for leftB-6..9 already exited: all four
  failed.

## What to do next

1. Read this file. Confirm `u4_gnd_left` is still called from `usb_left` and that
   `KIID_SEED` is still `{"left": 0x4, "right": 0x1}`.
2. Do not `pcb-finish` leftB-10 or leftB-11. There is no session file. On this machine, either
   delete `build/left/left.ses` if a partial one appears, delete `trial.done`, and rerun
   `just pcb-route left && just pcb-finish left` inside those two trees, or start fresh copies
   `leftB-12` and `leftB-13` (seeds `0xC` and `0xD`) with `rsync` as in
   `build/seedtrials/run_leftD.sh`. Copy `build/left/left.net` into each tree. `pcb-place`
   needs that netlist; rsync excludes `/build`. Touch `WANT_FULL` only when a boot resume
   should restart a full place+route+finish.
3. Launch with `setsid nohup`. One trial is about half an hour of Freerouting plus one to
   three hours of cleanup. Run two, not four.
4. A pass is `exit 0` and `checks left: 15 passed, 0 failed`, and `netcmp --board` clean.
   U7 in the winner must be `(65.6, 49.0, 180)`.
5. If the only miss on a DRC-clean board is still U4 pin 2 to J1 GND infinite, the stitch
   missed. Fix the track before any further seed.
6. If the only miss on a DRC-clean board is C5 to U2 pin 4, add one locked GND track that
   does not rip the QSPI fanout, then two new seeds. C5 is `(90.0, 55.4)`, U2 is
   `(96.0, 53.7)`.
7. If the misses are open signal nets, launch two more seeds of the same scripts. Do not
   change copper for that.
8. On a pass, adopt before any new route. From this machine, `build/seedtrials/adopt_winner.sh`
   copies the winner's `pcb`, `pro`, and `dru` for the left and `right-1` for the right, and
   sets the left seed. It refuses a winner whose U7 is not 65.6, and it refuses to overwrite
   a main left board that already has more than 800 segment lines. If that script is gone,
   do the same copies by hand. Right seed stays `0x1`.
9. Then run the gates in order, both halves, and do not parallelize the from-scratch rebuild
   (the halves share `pcb/.tools`):
   - `just pcb-drc <side>`: 0 violations, 0 unconnected, 0 parity, checks 15/15
   - `netcmp.py --board` per side
   - `just pcb-fab <side>`: 201/201 placements; LED terminal gate 55%; U7 correction `0;0;180`
   - `just pcb-production <side>` and `just pcb-production-check <side>`
   - `just pcb-cpl-images`
   - `just fitcheck` (expect 0), then `just model && just corners && just order && just production-check`
   - fresh copy, `just pcb-sch <side> && just pcb-place <side> && just pcb-route <side> && just pcb-finish <side>`, then `cmp` the board to the adopted board
   - `just docs-gen`, `just docs-check`, `uv run pytest layout -q`, `uv run pytest tests/integration -q --deselect tests/integration/test_stock.py`, `just pcb-mpn-check`, `uv run python -m layout.export --check`
10. Record the numbers you actually saw in `docs/verification.md` (Rev B results at the top),
    the README PCB and Gates rows, and the left seed in `docs/deviations.md` REVB-7. The
    verification section from the pause commit still says the design is not orderable; replace
    it only with measured results. Do not edit `docs/design.md`.
11. Case README says do not machine until PCB fitcheck passes. Hardware confirmation (LED
    chain, 0.45 A cap, current at 8% brightness, display setback, plug seating) stays listed
    and does not block the order files.
12. Commit and push only if the user asks.

## Local files that are not in git

- `build/seedtrials/CAMPAIGN.md` is the campaign log through this pause.
- `build/seedtrials/adopt_winner.sh`, `run_gates.sh`, `boot_resume.sh`, `run_leftD.sh`.
- `~/.config/systemd/user/worxboard-revb.service` and `worxboard-revb.timer` (timer disabled).
- Passing right board: `build/seedtrials/right-1`.
