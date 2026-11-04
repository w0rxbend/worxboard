# Case and plates

The case is `case/worxboard_case.py`, a [build123d](https://github.com/gumyr/build123d) port of the
[w0rxbend/ergodox](https://github.com/w0rxbend/ergodox) CNC case (spec §10). Every dimension is a
named constant, and the outline and all positions are imported from [`layout/`](../layout/), so
the case always matches the PCB.

> [!NOTE]
> **Modelled, checked and orderable, not yet made.** The order package is committed in
> [`case/production/`](../case/production/README.md), case revision **A3**: JLCCNC for the machined
> parts, JLC3DP for the printed ones, and `hardware.csv`. `just model` builds both halves and passes
> every case check. `just corners` checks every internal corner against JLCCNC's radius-for-depth
> rule. `just fitcheck` reports **0 mm³** of interference against both PCB STEPs. Those STEPs carry
> J3's own 5.0 mm socket model, and the `layout` envelopes are added for the parts they have no body
> for: J1 (USB-C), J2 (TRRS, at its drawing size), the display module up to its full-tolerance
> height, and the hot-swap sockets. The `fit` job of the
> [`pcb` workflow](https://github.com/w0rxbend/worxboard/actions/workflows/pcb.yml) runs it on every
> push. Gates G1 and G2 pass ([verification.md](verification.md#summary)). Nothing has been printed
> or machined: print a test top first ([below](#before-machining)).

![Both top shells](../case/renders/pair_top_iso.png)

The case has three parts per half, like the reference ErgoDox case: a **top shell** with the
1.5 mm switch plate milled into its key well, a **bottom tray**, and a separate 3 mm **plate
spacer** between the plate and the PCB. The PCB is clamped between bosses in the top and posts in
the tray.

| | Per half |
|---|---|
| Size | 192.4 × 165.6 × 17.6 mm, 19.6 mm at the display bezel (top 12.6 + tray 7.0; including the leg bosses) |
| Mass (6061-T6) | about 349 g: top 140.6 g, tray 208.1 g |
| Plate spacer | 182.7 × 136.6 × 3.0 mm, 20.2 cm³, MJF PA12 at JLC3DP (CASE-5), with a channel for each stabiliser wire (ORDER-6) |
| Fasteners | 6 × M2.5 × 12 and 2 × M2.5 × 10 countersunk, 90° head ≤ Ø5.2 (CASE-3) |
| Threads in the top | 8 × M2.5, all blind: drill 6.0 / full thread 4.5 mm in the edge bosses, 3.6 / 2.3 mm under the key well; 3 × M3 for the legs |
| Feet | 4 × Ø10 mm rubber feet in 0.6 mm recesses |
| Tent legs | 3 custom legs (4.9 g each in 6061) with TPU foot caps (one printed tree of 8, CASE-4) and M3 × 12 thumbscrews with friction washers ([legs.md](legs.md)) |

## Z stack

| Z (mm) | Layer |
|---|---|
| 0–3 | floor of the bottom tray |
| 3–7 | cavity (hot-swap sockets and diodes, about 2.2 mm margin) |
| 7–8.6 | PCB |
| 9.1–12.1 | plate spacer |
| 12.1–13.6 | plate |
| 13.6–17.6 | key well |
| 14.6 | pocket ceiling over the back strip and the TRRS bump |
| 17.6–19.6 | display bezel B1, raised 2.0 mm above the top face |
| 18.6 | display pocket ceiling, under a 1.0 mm skin with the window (the glass is at most Z 18.35) |

Wall 3.0 mm, top fillet 1.5 mm, seam chamfer 0.5 mm, well clearance 0.6 mm around each key cell.

## What changed from the reference ErgoDox case

| Feature | worxboard rev A |
|---|---|
| Outline | The PCB polygon from `layout.outline(side)` offset by 3.5 mm (0.5 clearance + 3.0 wall). Short PCB corner chamfers collapse into one filleted corner. Radii by vertex class: back corners r8 (r10 left too little cavity clearance), front-outer r12, thumb r8, concave r6 / r14, TRRS bump r5 (deviations WS3-1, WS3-2). The cavity keeps ≥ 0.3 mm to the PCB everywhere. |
| Keys | 37 per half (the inner top key is the display). The two 2u thumb keys get Cherry-spec plate stabiliser cut-outs (6.65 × 12.3 mm with the side and end notches; the 0.875 mm side notch is 1.0 mm for a 1 mm end mill). Each cut-out's long half points the same way as the PCB's Ø4.0 stabiliser holes: both read `layout.stab_dir`, and the left half is the mirror image (deviation REVIEW-FIX-7). The stabiliser wire runs under the plate, so the spacer has a 3.5 mm channel on both sides of each 2u switch, 6.5–10 mm from the key centre, from one stabiliser to the other (`STAB_WIRE_U`, checked by `spacer_check()`; ORDER-6). Clip the stabilisers into the top shell before the case is closed ([build guide](buildguide_en.md#6-assemble-the-case)). The key well is clipped to keep 2.0 mm of wall at the T0/T3 cap corners (WS3-4). |
| Screws | 8 × M2.5 on the ErgoDox pattern, with hole 7 moved to (88.0, 37.135) for the display. |
| Display | A pocket over the module + 0.5 mm, from the PCB top (Z 8.6) to **Z 18.6**, through the spacer and plate, under a **raised bezel** B1 (the pocket + 2.0 mm, Z 17.6–19.6, 1.0 mm skin, R2 plan corners; CASE-1). It holds a stock nice!view on the 5.0 mm J3 socket: the glass is 8.9 mm above the PCB nominally and 9.75 mm at full tolerance, 0.25 mm under the ceiling. The 26 × 12 mm viewing window (r1, 0.5 mm chamfer) is centred on the LCD viewing area and follows the J3 header (y 55.865). The pocket's two back corners have R2 dog-bones for JLCCNC's Ø3 tool (CASE-8). `display_check()` checks the ceiling, the skin, the window, the corners and the walls on the built part. |
| USB-C | On **both** halves: a 9.4 × 3.6 mm notch (r1.6) in the back wall at x 186.0 (right frame), Z centre 10.2, with a 13 × 8 mm outside recess 1.8 mm deep for the plug's overmould. The recess continues 0.8 mm into the tray. J1's mouth is flush with the PCB edge, 0.5 mm inside the wall, so the recess floor is **1.7 mm in front of the mouth**: only the plug's bare metal shell passes the notch, and it must stick out of the overmould by **at least 8 mm** for the plug to mate fully (a common plug's 6.5–6.6 mm shell stops about 1.2 mm short; ORDER-7). See [USB-C cable](shopping-list.md#cables). |
| TRRS | A Ø6.5 hole through the inner bump wall at y 103.0, on the jack axis (Z 11.1); `jack_check()` asserts it matches `layout` J2 within 0.2 mm. The J2 body (14.1 × 6.1 × 5.0, the HRO drawing) is relieved by **0.75 mm** all round, with R1.5 corners and at least 0.38 mm at the body's corners, in the top, the spacer and the plate DXF, with 1.0 mm headroom. `jack_check()` fails if any jack body comes closer than `JACK_MIN_CLEAR` = 0.3 mm (G2; BOARD-13, CASE-9). The plug has to pass 3.65 mm of Ø6.5 hole before it seats (see [TRRS cable](#trrs-cable)). |
| Back strip | A relief pocket over Z_BACK and Z_TRRS (ceiling 14.6), with a 1 mm wall kept to the key well (WS3-6), and Ø3 pin holes through the top over BOOT (176, 50) and RESET (180, 50). |
| Legs | The three stock positions on the derived walls; M3 drill 5.5 mm at the outer and thumb legs, 7.5 mm at the inner leg (WS3-3), with 4.0 / 6.0 mm of full thread (CASE-3). |
| Internal corners | Every internal corner has at least JLCCNC's radius for its depth, R = H/10 + 0.5 (CASE-8): key well R1.0 (4.0 deep), relief pockets and wall fillets R1.5, bottom web fillets R1.0, display pocket R2 (11.6 deep). The switch and stabiliser cut-outs are R0.5 for a 1 mm end mill through the 1.5 mm plate. `just corners` (`case/corner_check.py`) checks every corner of the machined STEPs. |
| Removed | The EZ's capacitor pocket, LED windows and reset hole, and the back-wall jack notches. |
| Halves | `build_top(side)` / `build_bottom(side)` build each half from the mirrored layout, with an engraved `L` / `R` under the tray. The model asserts left = mirror(right). |

Coordinates are in the right-half KiCad frame; [`overlay.png`](../case/renders/overlay.png) draws
the case over the PCB layout.

## Files

The order package is committed in [`case/production/`](../case/production/README.md); CI fails if it
drifts from the model:

| Folder | What | Order at |
|---|---|---|
| [`jlccnc/`](../case/production/jlccnc/ORDER_NOTES.md) | STEP + PDF drawing per machined part (2 tops, 2 bottoms, the leg), `hole_table.csv`, the form settings, the remarks to paste and prepared answers | JLCCNC |
| [`jlc3dp/`](../case/production/jlc3dp/ORDER_NOTES.md) | the two plate spacers and the leg-cap tree as STL, with their settings | JLC3DP |
| [`hardware.csv`](../case/production/hardware.csv) | screws, feet, thumbscrews and washers | any shop ([shopping-list.md](shopping-list.md)) |

`just model` writes everything else to `case/exports/` (git-ignored); the `case` workflow uploads it
as the `worxboard-case` artifact, together with the renders:

| File | What it is |
|---|---|
| `worxboard_{left,right}_{top,bottom}.step` / `.stl` | case parts |
| `worxboard_{left,right}_spacer.step` / `.stl` | plate spacers |
| `worxboard_leg.step` / `.stl`, `worxboard_leg_cap.step` / `.stl`, `worxboard_leg_cap_tree.step` / `.stl` | tent leg, one TPU foot cap (to print yourself) and the tree of 8 that JLC3DP prints |
| `worxboard_right_assembly_with_legs.step` / `.stl` | the right half with its legs, for previews |
| `worxboard_{left,right}_fitcheck.dxf` | 1:1 drawing with the outline, window, USB and TRRS notches, holes and switch cut-outs |
| [`plates/worxboard-plate-{left,right}.dxf`](../plates/) | the plate face, to cut a separate 1.5 mm FR4 or aluminium plate (committed; CI fails if they change) |

## Build it

```sh
just setup      # .venv with build123d 0.13.0, shapely, ezdxf
just model      # STEP/STL/DXF into case/exports/, plates/*.dxf; prints the build report
just fitcheck   # interference against build/<side>/worxboard-<side>.step
just corners    # every internal corner of the machined STEPs vs JLCCNC's radius-for-depth rule
just renders    # case/renders/*.png
just order      # PDF drawings + the order package in case/exports/order
just production         # copy the generated package into case/production
just production-check   # case/production equals the model
```

`just model` prints the screw-to-switch clearances, every case check (outline, legs, webs, display,
jacks, taps, spacer, mirror, cap tree) and each part's volume, mass and validity, and exits non-zero
if a check fails. `case/check_fit.py` places the KiCad STEP by matching the board outline and
requires 0 mm³ of interference with the top, bottom and spacer. The STEP carries J3's own 5.0 mm
socket model (ELEC-3) but no body for J1, J2 or the hot-swap sockets (KiCad ships no model), so the
`layout` envelopes of those parts are checked with it (deviation REVIEW-FIX-4): the USB-C and TRRS
bodies, the J3 body up to 5.8 mm and the display module above it up to 9.75 mm (CASE-1), and a
1.8 mm slab under the board. Without a STEP it checks only the `layout` envelopes and prints a
warning: run `just pcb-fab left` and `just pcb-fab right` first. `fitcheck` also prints the boss
webs that top-side PCB parts must stay off.

## TRRS cable

The jack mouth is 3.65 mm inside the case: the plug passes the Ø6.5 hole in the 3.0 mm bump wall
and the 0.65 mm gap to the PJ-320D barrel (case outer face x 45.5, barrel front x 49.15, right
frame). A plug whose head (overmould or metal shell) is wider than **Ø6.3 mm within 3.7 mm of
the shaft** stops short of full insertion: tip, ring and VLINK contacts then sit on the wrong
springs. Use a cable with a slim straight plug (most keyboard TRRS cables with a thin metal shell
fit); check one with calipers before ordering.

## Fasteners

Per half: 8 × M2.5 countersunk screws from below, on the original ErgoDox hole pattern, into blind
threads in the top (CASE-3, after JLCCNC's threaded-hole guideline: at least D/2 unthreaded at the
bottom of a blind hole).

| Holes | Drill / full thread | Screw | Engagement |
|---|---|---|---|
| T2–T4, T6–T8 (edge bosses) | 6.0 / 4.5 mm | **M2.5 × 12** | 3.4 mm |
| T1, T5 (under the key well; holes 0 and 4 in [pinout.md](pinout.md#mounting-holes)) | 3.6 / 2.3 mm, 0.78 mm of metal left under the key-well floor | **M2.5 × 10**, snug only | 1.4 mm |

A longer screw reaches past the end of the thread and stops before its head seats. The heads are
90°, at most Ø5.2 (DIN 7991 hex socket or ISO 7046 cross recess). 4 × Ø10 mm rubber feet go in
0.6 mm recesses. The full list is [`case/production/hardware.csv`](../case/production/hardware.csv).

## Previews

| Top shell, underside | Bottom tray |
|---|---|
| ![](../case/renders/right_top_underside.png) | ![](../case/renders/right_bottom_tray.png) |

| Back wall: USB-C notch | Plate spacer |
|---|---|
| ![](../case/renders/right_back_usb.png) | ![](../case/renders/spacer.png) |

Sections through the key columns, the display pocket, the back-edge screws, the USB-C notch and the
TRRS row:

![Sections](../case/renders/section.png)

The case over the PCB layout: red the case outline, green the PCB, blue the key well, purple the
display pocket and window, yellow the component zones, magenta the holes:

![Overlay](../case/renders/overlay.png)

## Before machining

The outline comes from the PCB, not from photos, but print a test fit anyway:

1. 3D-print the top, bottom and spacer of one half from the STLs in `case/exports` (or the CI
   artifact).
2. Fit an assembled PCB, its display and a few switches.
3. Check that:
   - the USB-C plug seats fully and latches (a plug with at least 8 mm of bare metal shell, ORDER-7);
   - the TRRS plug goes all the way in;
   - the display glass sits under the bezel skin, and the window shows its active area;
   - the BOOT/RESET pin holes reach the buttons;
   - the C6R1 keycap clears the display module's far end (CASE-1).

Then order from [`case/production/`](../case/production/README.md). The JLCCNC
[`ORDER_NOTES.md`](../case/production/jlccnc/ORDER_NOTES.md) has the form settings, the remarks to
paste and the answers to likely engineering questions. The JLC3DP
[notes](../case/production/jlc3dp/ORDER_NOTES.md) cover the spacers and the cap tree. The reference
project's [machining guide](https://github.com/w0rxbend/ergodox/blob/main/docs/machining.md) still
applies for the setups, materials and finishes.

Tent legs: [legs.md](legs.md).
