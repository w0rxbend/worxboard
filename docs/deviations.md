# Deviations from the rev A specification

[`design.md`](design.md) is frozen. When a stream finds a part of it impossible or wrong, it makes the
smallest sound change and records it here under its stream id. Each entry names the spec section,
what changed, why, and who consumes it.

## WS0: foundations and layout

### WS0-1. Thumb centres use the original PCB values, not the grid formula (§5)

- **Spec:** "thumbs equal the original PCB within 0.002" and the §5 table lists the `thumb_pt(u, v)`
  formula values.
- **Problem:** the formula misses the original ErgoDox PCB centres of T4 by 0.0026 mm and T5 by
  0.0028 mm (T5 x: formula 81.30558, PCB 81.30286). The two requirements cannot both hold at 0.002.
- **Change:** `layout/thumbs.py` stores the original PCB centres (from bishboria/ErgoDox
  `ErgoDOX.kicad_pcb`) and asserts that `thumb_pt()` agrees within 0.003 mm (`FORMULA_TOL`).
  The (u, v) grid, 25° rotation and sizes are unchanged. Every thumb now equals the original PCB exactly.
- **Consumers:** none affected in practice (3 µm).

### WS0-2. Display viewing window centred at y 60.0, not 62.5 (§4, §10 change 4)

- **Spec:** 26 × 12 mm window centred at (72.39, 62.5).
- **Problem:** the window then spans y 49.5–75.5. That runs past the module (y ≤ 74.625), past the
  case pocket (y ≤ 75.125, so `display_check()` would fail), and into the C6R1 key well
  (cell + 0.6 starts at y 74.025), leaving no top skin between window and well.
- **Change:** window centre (72.39, 60.0), so y 47.0–73.0: inside the module and pocket and
  1.0 mm clear of the C6R1 well (`test_window_clear_of_key_well`). Size, radius and chamfer are unchanged.
  The glass sits below the header end of the module, so the active area is nearer y ~58.6 than 62.5;
  gate **G1** must confirm the active-area position.
- **Consumers:** WS3 (`display_check`, window cut), WS4 (docs). Read it from `layout.display(side)["window"]`.
- **Note for WS3 (not changed here):** the spec pocket (y up to 75.125, Z 8.6–16.8) overlaps the C6R1
  well footprint (y ≥ 74.025) above the plate top (Z 13.6). The pocket must be clipped to the
  well wall there, or the well floor gets a hole.

### WS0-3. Keycap cells overhang the original thumb corner chamfers (§8.1, §14 "outline containing every cell")

- **Spec:** the outline contains every key cell.
- **Problem:** the outline keeps the original ErgoDox thumb vertices (R6), including two 45° corner
  chamfers: (23.08, 141.32)–(24.62, 137.10) and (48.98, 189.35)–(44.76, 187.82). The 19.05 mm cells of
  T0 and T3 cross them, by up to 1.9 mm and 2.0 mm at the corners. On the original board the keycap
  corners also overhang the PCB there.
- **Change:** the outline is unchanged. The acceptance test now requires every **switch housing**
  (15.6 mm) to be at least 0.4 mm inside the PCB edge, every cell except T0/T3 to be fully inside,
  and T0/T3 to be inside the outline grown by 2.0 mm (`CAP_OVERHANG`).
- **Consumers:** WS3: the case outer is PCB + 3.5 mm, so those two cap corners are about 1.5 mm inside
  the outer face, and the well (cell + 0.6) leaves about 0.9 mm of wall at the two corners. WS3
  either accepts a local thin wall there or clips the well to keep `WALL`.

### WS0-4. Hole keepouts are removed from Z_TRRS too (§8.3)

- **Spec:** Z_TRRS = PCB ∩ x < 62.2 ∩ y 88–125.7, minus cells grown by 0.6.
- **Change:** the Ø6.5 hole keepouts (§8.2) are also subtracted, as for Z_BACK. Hole #1
  (59.665, 121.666) lies inside the TRRS window. This only enforces the §8.2 component keepout.
  Z_TRRS becomes two pieces: the main bump (440 mm²) and a 4 mm² sliver below hole #1.

### WS0-5. J3 header pin order is not mirrored (§4, frame rule)

- **Spec:** the left half uses rot_L = −rot_R.
- **Clarification:** the display module is one physical part, mounted face-up the same way on both
  halves. `layout.display(side)["header_pins"]` therefore lists pin 1 at **low x on both halves**.
  The J3 footprint is placed at the same rotation on both PCBs, not mirrored. The pin-1 end is
  provisional until gate **G1** confirms the nice!view pinout.
- **Consumers:** WS2 (`place.py`, `design.py`).
