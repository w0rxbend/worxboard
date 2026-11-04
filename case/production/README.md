# Case order package (case revision A1)

Everything needed to order the worxboard case for one keyboard (both halves). The files are
generated from the model; only this page and the two `ORDER_NOTES.md` are written by hand.

| Order | Where | Folder |
|---|---|---|
| 2 top shells, 2 bottom trays, 6 tent legs (aluminium 6061-T6, bead blast + anodize) | [JLCCNC](https://jlccnc.com) | [`jlccnc/`](jlccnc/ORDER_NOTES.md): STEP + PDF drawing per part, `hole_table.csv` |
| 2 plate spacers (MJF PA12), 1 tree of 8 leg foot caps (FDM TPU 95A) | [JLC3DP](https://jlc3dp.com) | [`jlc3dp/`](jlc3dp/ORDER_NOTES.md): STL |
| 12 × M2.5×12 and 4 × M2.5×10 countersunk screws, 8 rubber feet, 6 M3 leg thumbscrews, 6 friction washers | any hardware shop | [`hardware.csv`](hardware.csv) |

The PCBs, the switches, keycaps, the two nice!view displays and the TRRS and USB-C cables are not
part of this package.

## Before ordering

1. The PCB order must be final: `just fitcheck` reports 0 mm³ against both PCB STEPs (the `fit` job
   of the `pcb` workflow runs it on every push, with the J3 socket and the layout envelopes of the
   USB-C, TRRS, nice!view and hot-swap socket bodies).
2. `just model order production-check` passes: this folder matches the model (the `case` workflow
   runs it on every push).
3. Read the two `ORDER_NOTES.md` and paste their remarks into the order forms.

## What the case expects from the parts it holds

- **Display.** J3 is the 5.0 mm socket JLCPCB fits (C27985230). Plug a stock nice!view into it on the
  male header it ships with; the bezel's pocket clears the glass up to 9.75 mm above the PCB (full
  tolerance; 8.9 nominal). **Trim the header pins flush on the display's top side** (no higher than
  its glass, 0.9 mm above the module PCB): untrimmed pins stand about 2 mm up and would hit the
  pocket ceiling.
- **Screws.** M2.5 × 12 in the six edge bosses (T2–T4, T6–T8), M2.5 × 10 in the two bosses under
  the key well (T1, T5; tighten those only snug). A longer screw would reach past the end of the
  blind thread and stop before its head seats.
- **Legs.** The M3 thumbscrew may reach at most 3.7 mm past the boss face at the outer and thumb
  legs (L1, L3) and 5.7 mm at the inner leg (L2). An M3 × 12 knurled thumbscrew whose head bears on
  the leg's back face reaches 4.0 mm, so it needs the 0.5–1.0 mm friction washer between hub and
  boss. Measure a stock ErgoDox EZ spring thumbscrew before using it.
- **Foot caps.** Snip the caps off the tree at their base and push them onto the leg spigots.

## Files and sizes

| File | Size | Notes |
|---|---|---|
| `jlccnc/worxboard_{right,left}_top.step` | 4.7 MB each | committed (under the 5 MB limit for committed STEPs) |
| `jlccnc/worxboard_{right,left}_bottom.step`, `worxboard_leg.step` | 0.2–0.5 MB | |
| `jlccnc/*.pdf` | 50–110 kB | A3 drawings: views, thread tables, notes, detail C through the display bezel |
| `jlc3dp/*.stl` | 0.6–2.0 MB | |

Not committed: the STEP versions of the printed parts and the right-half assembly with legs
(`worxboard_right_assembly_with_legs.step`, 8 MB, and its STL, not ordered). They are in
`case/exports` after `just model` and in the `worxboard-case` artifact of the `case` workflow, with
every other export, the renders and this package.

## Rebuild

```sh
just model        # case/exports: STEP/STL/DXF, every case check
just order        # case/exports/order: this package, plus the plate DXFs
just production   # copy the generated files into case/production
just production-check
```

The package is reproducible: the STEP files carry the revision date instead of the export time and
the PDFs have no creation date. Bump `CASE_REVISION` / `CASE_REVISION_DATE` in
`case/worxboard_case.py` with any change to the ordered geometry.
