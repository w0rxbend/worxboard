# Case and plates

> [!NOTE]
> **In progress (WS3).** This page describes the rev A case as specified (spec §10). The model is
> `case/worxboard_case.py`, a port of the [w0rxbend/ergodox](https://github.com/w0rxbend/ergodox) CNC
> case. Generated files land in `case/exports/` (git-ignored) and in the CI artifacts.

The case is a two-piece CNC aluminium case, like the reference ErgoDox case: a **top shell** with the
1.5 mm switch plate milled into its key well, a **bottom tray**, and a separate 3 mm **plate spacer**
between the plate and the PCB. The PCB is clamped between bosses in the top and posts in the tray.
Every dimension is a named constant, and the outline and all positions are imported from
[`layout/`](../layout/), so the case always matches the PCB.

## Z stack

| Z (mm) | Layer |
|---|---|
| 0–3 | floor of the bottom tray |
| 3–7 | cavity (hot-swap sockets and diodes, about 2.2 mm margin) |
| 7–8.6 | PCB |
| 9.1–12.1 | plate spacer |
| 12.1–13.6 | plate |
| 13.6–17.6 | key well |
| 14.6 | pocket ceiling (back strip, TRRS bump) |

Wall 3.0 mm, top fillet 1.5 mm, seam chamfer 0.5 mm, well clearance 0.6 mm around each key cell.

## What changed from the reference ErgoDox case

| Feature | worxboard rev A |
|---|---|
| Outline | The PCB polygon from `layout.outline(side)` offset by 3.5 mm (0.5 clearance + 3.0 wall), with the reference corner radii per vertex class and r6 at the TRRS bump. The photo-measured `CASE_*` constants are gone. |
| Keys | 37 per half (the inner top key is the display). The two 2u thumb keys get plate stabiliser cut-outs. |
| Screws | 8 × M2.5 on the ErgoDox pattern, with hole 7 moved to (88.0, 37.135) for the display. |
| Display | A pocket over the module + 0.5 mm, from the PCB top (Z 8.6) to Z 16.8, through the spacer and plate, and a 26 × 12 mm viewing window (r1, 0.5 mm chamfer) through the top. The window is centred at (72.39, 60.0) (deviation WS0-2). `display_check()` asserts the window is inside the pocket. |
| USB-C | On **both** halves: a 9.4 × 3.6 mm notch (r1.6) in the back wall at x 186.0 (right frame), Z centre 10.2, with a 13 × 8 mm outside recess 1.8 mm deep so a plug seats fully. |
| TRRS | A Ø6.5 hole through the inner bump wall at y 103.0, on the jack axis; `jack_check()` asserts it matches `layout` J2 within 0.2 mm. The bump has a bezel pocket with 6 mm headroom. |
| Back strip | A relief pocket over the whole Z_BACK zone (ceiling 14.6), and Ø3 pin holes through the top skin over BOOT (176, 50) and RESET (180, 50). |
| Removed | The EZ's capacitor pocket, LED windows and reset hole, and the back-wall jack notches. |
| Halves | `build_top(side)` / `build_bottom(side)` build each half from the mirrored layout, with an engraved `L` / `R` under the tray. |

## Files

| File | What it is |
|---|---|
| `worxboard_{left,right}_{top,bottom}.step` / `.stl` | case parts |
| `worxboard_{left,right}_spacer.step` / `.stl` | plate spacers (print or mill) |
| `worxboard_leg.step` / `.stl`, `worxboard_leg_cap.stl` | tent leg and TPU foot cap |
| `worxboard_{left,right}_fitcheck.dxf` | 1:1 drawing with the outline, window, USB and TRRS notches, holes and switch cut-outs |
| `plates/worxboard-plate-{left,right}.dxf` | the plate face as a DXF, to cut a separate 1.5 mm FR4 or aluminium plate (for a printed or third-party case) |

## Build it

```sh
just setup      # .venv with build123d 0.13.0, shapely, ezdxf
just model      # STEP/STL/DXF into case/exports/
just renders    # preview images
just fitcheck   # interference check against the PCB STEP (build/<side>/worxboard-<side>.step)
```

`case/check_fit.py` loads the PCB STEP from the PCB pipeline when it exists and requires 0 mm³ of
interference with the top and bottom parts. Until then it checks against the `layout` component
zones and prints a warning.

## Fasteners

Per half: 8 × M2.5 countersunk screws (ISO 10642) from below, on the original ErgoDox hole pattern.
The reference case uses M2.5 × 14 on the bezel and edge bosses and M2.5 × 12 on the two bosses
under the key well; the build report printed by `just model` gives the lengths for this case.
4 × Ø10 mm rubber feet in 0.6 mm recesses.

## Before machining

The outline now comes from the PCB, not from photos, but print a test fit anyway:

1. 3D-print the top, bottom and spacer of one half.
2. Fit the assembled PCB, the display and a few switches.
3. Check the USB-C plug seats fully, the TRRS plug goes all the way in, the window shows the display's
   active area (gate G1), and the BOOT/RESET pin holes reach the buttons.

The reference project's [machining guide](https://github.com/w0rxbend/ergodox/blob/main/docs/machining.md)
and [JLCCNC order guide](https://github.com/w0rxbend/ergodox/blob/main/docs/jlccnc-order.md) apply to
this case too: the same setups, internal-corner radii, materials and finishes.

Tent legs: [legs.md](legs.md).
