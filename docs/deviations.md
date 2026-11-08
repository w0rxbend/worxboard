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

## WS1: firmware

### WS1-1. CI mirrors `build-user-config.yml` instead of calling it (§11.2)

- **Spec:** `firmware.yml` `uses: zmkfirmware/zmk/.github/workflows/build-user-config.yml@<sha>` with
  `config_path: firmware/zmk/config`.
- **Problem:** with a root `zephyr/module.yml` the reusable workflow copies the config with
  `mkdir "<tmp>/zmk-config/<config_path>"` (no `-p`, unchanged on ZMK `main`), so a nested
  `config_path` fails before any build.
- **Change:** `.github/workflows/firmware.yml` runs the same steps itself: `zmkfirmware/zmk-build-arm:stable`,
  matrix from `build.yaml` (yq), west init/update/zephyr-export, `west build -s zmk/app` with
  `-DZMK_CONFIG=firmware/zmk/config -DZMK_EXTRA_MODULES=<repo>`, one `artifact-<name>` per row merged
  into `worxboard-firmware`. The build step is `firmware/zmk/scripts/fw_build.py`, the same script
  `just fw` runs, and CI asserts the checked-out ZMK revision equals the pinned SHA.
- **Consumers:** WS5 (`release.yml` downloads the `worxboard-firmware` archive / `*.uf2`).

### WS1-2. West workspace outside the repo tree; manifest `self.path: config` (§11.2)

- **Spec:** `self: { path: firmware/zmk/config }` and `west init -l /work/firmware/zmk/config`.
- **Problem:** `west init -l` makes the *parent* of the manifest directory the workspace, so zmk,
  zephyr and ~3 GB of modules would land in `firmware/zmk/`, next to the module's own `zephyr`-named
  paths and untracked by `.gitignore`.
- **Change:** `just fw-west` copies `west.yml` to `build/fw-ws/config/` (git-ignored) and initialises
  there; CI uses `/tmp/zmk-ws/config`. `self.path` is `config` to match. West update reruns only when
  `west.yml` changes.

### WS1-3. Matrix transform generated with the physical layout (§11.2, §11.4)

- **Spec:** the 6×14 transform lives in the seed `worxboard.dtsi`; only the physical layout is generated.
- **Change:** `gen_layouts.py` writes both `default_transform` and `worxboard_layout` into
  `worxboard-layouts.dtsi` from `layout.json` `transform_order`, so the transform, the physical
  layout and the keymap order cannot drift. `worxboard2` includes the same generated file.
  The map is identical to the seed's.

### WS1-4. HID indicators forwarded from the central (§11.2, §11.6)

- **Spec:** `ZMK_SPLIT_PERIPHERAL_HID_INDICATORS default y` under `if BOARD_WORXBOARD_RIGHT` only.
- **Problem:** the option gates the *central's* sender (`hid_indicators.c`) as well as the peripheral's
  receiver, and depends on `ZMK_HID_INDICATORS`; right-only leaves the right lock row dark.
- **Change:** `ZMK_HID_INDICATORS` and `ZMK_SPLIT_PERIPHERAL_HID_INDICATORS` default y on both halves.
  The custom-screen choice stays right-only.

### WS1-5. Keymap and options single-sourced in `firmware/zmk/config` (§11.1, §11.3)

- The board-folder keymaps (`worxboard.keymap`, `worxboard2.keymap`) `#include` the user keymap
  `firmware/zmk/config/worxboard.keymap`, so there is one keymap.
- ZMK reads `<ZMK_CONFIG>/<board dir>.conf`; `worxboard2` has no `worxboard2.conf`, so its defconfigs
  set `CONFIG_ZMK_DISPLAY=y` and `CONFIG_ZMK_POINTING=y` (mouse keys on layer 2). The board-folder
  `worxboard.conf` files are kept as documented defaults only.
- Layer mapping where QMK has no ZMK equivalent: `TT(1)` is a hold-tap (`&mo`/`&tog`), `HYPER`/`MEH`
  are plain held modifier combos, `VRSN`/`EE_CLR`/RGB keys are `&trans`. LEFT/RGHT (the old inner-top
  keys) sit on layer 1 at the inner 1.5u `HYPER`/`MEH` positions, so the layer-1 `TG` keys stay
  transparent and still toggle back.

### WS1-6. Kconfig `LV_OBJ_LABEL` does not exist at the pinned ZMK (§11.6)

- ZMK's built-in screen `select`s `LV_OBJ_LABEL`, a dangling symbol at 4dd95d78. The module's
  `WORXBOARD_STATUS_SCREEN` selects `LV_USE_LABEL` (plus Montserrat 12/16) instead.

### WS1-7. Both displays are laid out portrait and turned in the LVGL flush (§4, §11.2, §11.6)

- **Spec:** the nice!view status screens as ZMK draws them, 160 × 68 landscape.
- **Problem:** the module stands in J3 LCD up, its header at the back and its flex toward the user,
  the same way on both halves (G1, BOARD-1). Laid out landscape, both screens read turned by a
  quarter. Zephyr's ls0xx driver and LVGL glue at the pinned SHA cannot rotate.
- **Source for the panel's origin:** pixel x = 0 is the header end. ZMK's nice_view widgets
  (`widgets/status.c`, `util.c`) draw their top canvas at x 92..159 and turn it a quarter clockwise,
  and nicekeyboards.com's product images show that screen upright with the header at the bottom.
  worxboard shows the module turned 180° from that view. No Sharp LS011B7DH03 datasheet was found.
- **Change** (`firmware/zmk`, commit 876847c):
  - LVGL lays out a 68 × 160 portrait screen.
  - `src/worx_display_rotation.c` uses `LV_DISPLAY_ROTATION_90`: portrait (u, v) maps to panel
    (v, 67 − u), with the map in `src/worx_rotate.h`.
  - At SYS_INIT 91, after `lvgl_init()`, it replaces Zephyr's mono flush and rounder: each area is
    turned into a panel-ordered shadow, and the lines it touches go, full width, through
    `lvgl_flush_cb_mono()`.
  - The Kconfig choice `WORXBOARD_DISPLAY_ROTATION` is `_90` (the default) or `_270` (a 180° flip,
    the stock nice!view orientation).
  - Left: ZMK's built-in screen, portrait. Right: the custom screen laid out portrait
    (`worx/board`, the lock column, `wired`).
- **Checks:** `tests/rotate_test.c` (`just fw-rotate-check`, in `just fw` and the CI checks job)
  tests the pixel map against the panel facts and LVGL's `lv_display_rotate_area()`. `fw_check.py`
  runs on both core rows and fails if the rotation is not configured or not linked. Firmware CI run
  41757564608 passed, 9 of 9 jobs.
- **Not checked on hardware:** that the screens read upright. If the first board shows them upside
  down, set `CONFIG_WORXBOARD_DISPLAY_ROTATION_270=y` in `firmware/zmk/config/worxboard.conf`.

### WS1-8. The right screen sets its own paper and ink and gets an 8 KB LVGL heap (§11.6)

- **Problem:** ZMK applies its mono theme only to the built-in screen. The custom right screen had a
  transparent background and black text, and LVGL never clears an I1 draw buffer. On the panel its
  text had the colour of the uncleared buffer, so the right screen showed nothing. This was found by
  rendering the screen on the host with the pinned LVGL 9.3 and Zephyr's own mono flush. The screen
  also ran on Zephyr's default 2048 B LVGL heap.
- **Change** (commit 4769d4d): the screen sets an opaque paper and its ink like the left's mono theme
  (`ZMK_DISPLAY_INVERT` swaps them). `LV_Z_MEM_POOL_SIZE` defaults to 8192 B when the custom screen
  is chosen, as ZMK's nice_view shield sets it. The left built-in screen keeps ZMK's 4096 B. RAM:
  left central 46 206 B (17.2 %), right peripheral 30 460 B (11.3 %). Right flash: 170 872 B,
  +5 472 B against the 40 KB budget.
- **Not measured:** heap use on 32-bit ARM. On a 64-bit host the right screen peaks at 5 240 B and
  the left built-in screen at 4 672 B.

### WS1-9. XOSC start-up is 64× for the rev A crystal (§6.4; ELEC-1)

- **Problem:** Y1 is now the YXC XL2EL89CRI-111YLC-12M (C49304726, ESR 80 Ω max), not the Pico's
  Abracon ABM8-272-T3, which the Pico SDK's 1 ms XOSC start-up delay is tuned for.
- **Change** (commit 5fd74ae): rev A `worxboard.dtsi` sets `&xosc` `startup-delay-multiplier = <64>`
  (about 64 ms), as Zephyr's RP2040 boards with other crystals do (xiao_rp2040, qt_py_rp2040,
  kb2040). The RP2350A `worxboard2` target is unchanged. A future Y1 change needs no firmware change.

## WS2a: schematic and electrical data (`pcb/scripts/design.py`, `gen_sch.py`, `netcmp.py`)

### WS2a-1. Matrix and button reference designators (§7, §9)

- **Spec:** sockets `SK_xx`, diodes `D_xx`, buttons `SW_BOOT` / `SW_RST`.
- **Problem:** kicad-sch-api 0.5.6 (the pinned generator) only accepts references of the form
  `[A-Z]+[0-9]*`, and KiCad annotation splits a reference at its trailing number, so `SK_C0R0` is not a
  usable designator.
- **Change:** key n (0-based, in `layout.keys()` order: main block, then T0–T5) is socket
  **`SK<101+n>`** and diode **`D<101+n>`** (SK101/D101 = C0R0 … SK137/D137 = T5). Both carry a hidden
  **`Key`** field with the layout key id, which is what `place.py` should use. The buttons are
  **SW1** (value `BOOT`) and **SW2** (value `RESET`). `D1` stays the B5819W.
- **Consumers:** WS2 placement (`place.py` places by the `Key` field), WS4 (`bom.md`, build guide).

### WS2a-2. TRRS_DET test pad TP11 (§3, §7)

- **Spec:** §3 gives GP21 (`TRRS_DET`) a test pad; §7 counts only TP1–TP7 + SWD×3 = 10 pads.
- **Change:** an eleventh pad **TP11** on `TRRS_DET`, in the TRRS group (excluded from BOM/POS like
  the others). SWD pads are TP8 SWCLK, TP9 SWDIO, TP10 GND.
- **Consumers:** WS2 placement (TP11 in Z_TRRS or Z_BACK), WS4.

### WS2a-3. Hot-swap footprint is drawn for a flip onto B.Cu (§9 stage 1)

- **Spec:** `SW_MX_Hotswap_Kailh` with B.Cu pads at (−7.085, −2.54) / (5.842, −5.08) and socket holes at
  (−3.81, −2.54) / (2.54, −5.08); §9 stage 7 flips B-side parts.
- **Clarification:** the spec numbers are the coordinates **on the board**. So that JLC sees the
  socket as a bottom-side part (POS file) the library footprint is the front-side mirror (pads on F.Cu at
  (7.085, −2.54) / (−5.842, −5.08)). `place.py` flips it left/right (`FLIP_DIRECTION_LEFT_RIGHT`), which
  puts the pads on B.Cu exactly at the spec coordinates (checked with pcbnew 10.0.7). Pad 1 = COL,
  pad 2 = diode anode. `Stab_MX_2u` has its long axis along x and the `board_only` attribute (no symbol).
- **Consumers:** WS2 placement (`place.py`).

### WS2a-4. F1 part choice (§7)

- **Spec:** F1 "chosen by WS2 from JLC parts".
- **Choice:** **C70069**, nSMD025-24V: 1206 PTC, 250 mA hold, 24 V. LCSC listed 9640 in stock on
  2026-10-29. It is a [G3] part.
- **Consumers:** WS4 (`bom.md`), WS5 (G3).

## WS3: case and plates (`case/worxboard_case.py`)

### WS3-1. Outline corner radii follow the derived PCB outline (§10 change 1)

- **Spec:** case outer = PCB + 3.5 mm (mitre), then the reference radii by vertex class: convex back 10,
  front-outer 12, thumb 8, concave 6 / 14.
- **Problem:** the five 45° PCB corner chamfers (3.2–9.5 mm legs) leave too little room for a r10
  case corner: the cavity (outer − 3.0) would clear the PCB by only 0.05 mm at the back corners.
- **Change:** chamfers shorter than 15 mm collapse into one sharp corner before the offset (the case
  corner is then filleted, as on the EZ). Convex radii are reduced in 0.5 mm steps until the cavity
  keeps 0.3 mm (`CAVITY_MIN_CLEAR`) to the PCB: the two back corners become **r8**; front-outer 12,
  thumb 8 and concave 6 / 14 are unchanged. The model checks the clearance (`pcb_check`).

### WS3-2. TRRS bump corners r5, not r6 (§10 change 1)

- **Problem:** the bump's top edge is 10.1 mm long between a convex and a concave corner; two r6
  fillets need 12 mm. **Change:** `R_BUMP = 5.0`. The model now fails if neighbouring fillets overlap.

### WS3-3. Tent legs on the derived walls; shorter M3 threads at the outer and thumb legs (§10 kept list)

- **Positions kept:** y 64 on the outer and inner main walls, v = 0.56 along the thumb end wall. The
  walls come from the derived outline, so the outer boss face is at x 209.42 (photo value 210.6) and
  the thumb leg sits on the PCB thumb edge + 3.5 mm.
- **Problem:** the outer and thumb walls are now 3.1 mm from the key well, so the reference rule that
  stops the M3 drill short of the well floor gives 5.5 mm (reference 7.5). The thumb pad is 1.75 mm
  deep (T0 housing). **Change:** none to the rule; a new check requires ≥ 5.0 mm of drill depth
  (`LEG_MIN_DRILL`, > 1.5 D engagement). Inner leg: pad clamped to 5.0 mm, drill 7.5 mm, 1.29 mm from
  the display pocket.

### WS3-4. Key well clipped to keep 2.0 mm of wall at the T0 / T3 corners (WS0-3)

- **Change:** the well (cells + 0.6) is intersected with the outer outline − 2.0 mm (`WELL_MIN_WALL`),
  so the 1.5 mm top-edge fillet cannot break into it. The model checks that every keycap (18.15 mm)
  stays inside the clipped well.

### WS3-5. Display pocket kept as specified where it meets the C6R1 well (WS0-2 note)

- **Spec:** pocket = module + 0.5 (y up to 75.125), Z 8.6–16.8, cutting the spacer and plate.
- **Note:** the C6R1 well starts at y 74.025, so the pocket opens a 1.1 mm strip of the well floor
  (plate) next to the switch. The module itself fills it to within 0.5 mm (module edge y 74.625).
  Clipping the pocket instead would need gate **G1** to guarantee the module underside ≥ Z 13.6 at its
  far end; kept as specified. Window (WS0-2, y 47–73): 1.0 mm of top skin to the well, 0.8 mm thick.

### WS3-6. Relief and spacer around the component zones (§10 change 7, §8.3)

- **Change:** the relief pocket (ceiling 14.6) covers Z_BACK and Z_TRRS except a 1.0 mm well wall
  (`RELIEF_WELL_SKIN`); there the headroom is the 3.5 mm under the plate. The spacer is kept 0.5 mm off
  both zones and the display pocket.
- **Keepouts for WS2:** the five top-part boss webs (and their R1 wall fillets) reach down to the PCB
  top inside Z_BACK / Z_TRRS. `just fitcheck` prints them (right frame: (88.1, 33.4), (118.3, 33.4),
  (204.0, 37.2), (204.3, 140.1), (106.6, 160.4)); top-side parts must stay off them.

### WS3-7. Smaller items

- `BOTTOM_FRONT_INSET` (reference photo correction) is dropped: the cavity is 0.5 mm from the PCB on
  every side.
- Rubber foot 3 moves from (198, 150) to (196, 148) to stay 1.5 mm inside the outline.
- The USB-C plug recess (Z 6.2–14.2) continues 0.8 mm into the bottom part.
- `STABILIZERS = True` (§5 plate stab cuts); the spacer has matching openings.
- `overlay.py` draws the case over the PCB layout instead of an EZ photo (there is none to calibrate).
- `check_fit.py` places the KiCad STEP by matching the board solid's bbox to the layout outline (Y up,
  board bottom at Z 0), so any export origin works.
- Render tools need trimesh / matplotlib / pillow, which are not in the `case` group (pyproject is
  WS0's): `case.just` pins them with `uv run --with`.

## WS2b: placement and routing (`pcb/scripts/place.py`, `route_critical.py`, `export_dsn.py`, `import_ses.py`, `complete_routes.py`, `checks.py`)

### WS2b-1. The left RP2040 is turned 180° and moved 0.6 mm toward J1 and 2 mm back (§8.3, §9 stage 7)

- **Spec:** U1 at the anchor (166, 44) (left 94, 44); left parts use rot_L = −rot_R.
- **Problem:** a QFN cannot be mirrored. With the same rotation on both halves, the left USB pins
  face away from J1 and the D+/D− pair would have to cross the QSPI and supply escapes.
- **Change:** right U1 at (166, 44) rot 0; left U1 at **(93.4, 42.0) rot 180**. The fan-out, inner
  joins and USB start are laid in the U1 frame, so they are identical on both halves. The shift keeps
  the left USB path within 25 mm. Without it the path runs from the turned U1 to J1 past SW1/SW2,
  which stay at their anchors because the case has pin holes over them.
- **Consumers:** WS3 (`check_fit.py` uses the STEP; the U1 envelope is 1 mm high, below the 1.2 mm
  zone allowance anywhere in Z_BACK).

### WS2b-2. The flash U2 is moved next to its QSPI escapes (§8.3)

- **Spec:** U2 at (152, 42) / (108, 42).
- **Problem:** at the anchor the flash sits across U1's west escapes on the right and beyond the
  east escapes on the left, so six QSPI lines would cross the display, UART and row lines.
- **Change:** right U2 at **(154.6, 35.0)** (north-west of U1), left at **(96.0, 53.7) rot 180**
  (beside the turned U1's QSPI side). Both are inside Z_BACK.
- **Consumers:** WS3 (`web_check` keeps webs off `part_rect("U2")` at the layout anchor; the
  actual body is checked by `check_fit.py` against the STEP).

### WS2b-3. Routing flow: locked critical routes, Freerouting, then a completion router (§9 stages 8–10)

- **Spec:** `route_critical.py` lays the QFN fan-out, USB, crystal, QSPI, decoupling, power and TRRS
  routes; Freerouting does the rest.
- **Problem:** Freerouting 2.5.0 cannot finish a route into a 0.4 mm-pitch QFN pad with 0.2 mm
  clearance (its debug log: `insert trace failed`), it never tries a 0.5 mm 3V3 track that cannot
  enter the pad, and rotated or any-angle items degrade its search. Each run stopped at 25–60 open
  connections however the rules were tuned.
- **Change:**
  - `route_critical.py` lays, locked: a **45° corner fan-out** of every U1 signal pin
    (0.15 mm, the spec's QFN fan-out width). Each half-side bends toward a corner, one pin after the
    other 0.3 mm further out. COL0 and COL4–COL6 end in vias, so they can cross under U1 on B.Cu
    toward their columns. It also lays the **inner joins** between the pad ring and the exposed
    pad (3V3 pins 42/43/44/33/22 and 1/10, 1V1 pins 45/50, TESTEN), three 3V3 exits, the GND via
    array, XIN into Y1, the **USB pair** with the J1 ties and escape vias, and the **key matrix**
    (switch→diode links, rows on F.Cu, columns on B.Cu, vias at the 25° thumb pads).
  - `export_dsn.py` takes U1's pins out of the DSN nets so routes end on the fan-out. It puts the
    U1 signal nets in a 0.18 mm class, rounds pin offsets to 1 µm (with a 2 µm clearance margin)
    and writes rounded-rectangle pads as rectangles.
  - `complete_routes.py` (new, called by `import_ses.py`) routes what Freerouting leaves open: a
    two-layer A* router (0.1/0.05 mm grid, 45° moves, vias). Obstacles are dilated by half-width +
    clearance. If no clean route exists it may cross unlocked tracks, which it then rips up and
    reroutes. After the pours are filled it repeats against them, which also joins GND pads the
    pours left isolated.
  - Crystal (XOUT), QSPI, decoupling, power trunks and TRRS lines are autorouted, not scripted.
- **Result:** U1 signal nets, the matrix rows/columns and the thumb links run at **0.15–0.18 mm**,
  not the Default 0.25 mm. They are still above the 0.127 mm board minimum (JLC 2-layer). The
  netclass table in the project file is as specified. DRC (`--schematic-parity --severity-error`) is
  the gate for all copper.
- **Consumers:** WS5 (G3: 0.127 mm minimum track already listed).

### WS2b-4. GND stitching vias are placed after routing (§8.4)

- **Spec:** `place.py` adds the stitching vias before autorouting.
- **Change:** `import_ses.py` adds them after the routes (5 mm grid near U1/Y1/J1 in Z_BACK, 10 mm
  elsewhere) wherever a via clears every other net. It keeps only vias that land in filled GND
  on both layers. Freerouting therefore never has to route around them.

### WS2b-5. Smaller rule and check details

- **Y1 (§6.4, §9 stage 12):** `checks.py` measures from the XIN/XOUT pads to Y1's courtyard
  (≤ 3.0 mm). The pad ring's fan-out leaves no room for the crystal body closer than that.
- **USB length (§6.3):** the copper path from the U1 pin to the nearest J1 pin of the net (tracks,
  plus the R3/R4 pad pitch) is ≤ 25 mm, and D+/D− differ by ≤ 1 mm. The A6/B6 and A7/B7 ties are
  not counted. The pair runs on F.Cu on both halves.
- **USB keepout:** the B.Cu track keepout runs under the pair from U1 to U4. On the right it stops
  at the J1 pad row: there, the VBUS/CC2 pads the pair encloses drop to B.Cu through vias.
- **Decoupling (§6.4):** the IOVDD pins are joined inside the pad ring, so their 100 nF caps
  (C8–C15) sit on the 3V3 net near the exits rather than one at each pin.
- **Mounting holes (§8.2):** the Ø6.5 copper keepout is a rule area (no tracks, vias or pour) on
  both layers.
- **J2 (§8.3):** its courtyard (sleeve pad and snout) may extend 1.4 mm past Z_TRRS. The body stays
  inside it.
- **DRC severities:** schematic-parity items (missing/extra footprint, net conflict, symbol
  mismatch, duplicates) are raised to error. Silk overlap, text size, library-footprint warnings and
  `npth_inside_courtyard` are warnings. The last one is set because on the left half SK117's
  rectangular courtyard corner reaches hole 4; the nearest socket copper/body is 1.8 mm outside
  the Ø6.5 boss.
- **Project file:** `place.py` writes the netclasses and rules into `pcb/<side>/*.kicad_pro`
  (`gen_sch.py` keeps those keys).

### WS2b-6. Last gaps closed by a transactional rip-up (§9 stages 10–11)

- **Problem:** after Freerouting and the plain completion pass, 10 (left) and 11 (right)
  connections stayed open. Most were RP2040 fan-out stubs walled in by other nets' autorouted
  tracks, and the stub ends sit about 0.3 mm from the next via. The completion grid's 0.6-step
  safety margin closed those exits. Rip-up without a check made the routes oscillate.
- **Change:** `complete_routes.negotiate()` (called by `import_ses.py` when gaps remain):
  - routes the gap across other nets' **unlocked** copper (a crossing cost per cell), rips that
    copper up and reroutes the ripped nets, up to five levels deep;
  - uses a 0.1-step margin and then checks the path exactly (shapely) against the pads, locked
    copper, holes, keepouts and edge, so tight stub exits can be used without DRC errors;
  - avoids a 2 mm lane straight on from other nets' locked stub ends, so a new route does not
    wall in the next stub;
  - judges GND on a fresh pour fill;
  - keeps a change only if the open-island count of the whole board falls, and otherwise
    restores the board exactly. Locked copper (fan-out, USB, matrix) is never touched.
- Freerouting tracks narrower than the 0.127 mm board minimum are deleted after the session
  import and rejoined by the completion router. Copper is removed with `BOARD.Delete`, because
  `BOARD.Remove` followed by garbage collection corrupted the board in KiCad 10.0.7's bindings.
- **Result:** both halves pass `kicad-cli pcb drc --schematic-parity --severity-error` with
  0 violations, 0 unconnected items and 0 parity issues, and `checks.py` passes.
  `just pcb-finish <side>` exits 0.

### WS2b-7. Left half: no B.Cu USB keepout across U4 (§6.3, §8.4)

- **Spec:** B.Cu track keepout under the USB pair (WS2b-5).
- **Problem:** on the left half U4 sits on the diagonal pair run, and its pins 2/5 lie between
  the split rows. The VBUS via from pin 5 lands inside the keepout and is fenced in on F.Cu by
  D+/D−, so U4's VBUS pin could never connect.
- **Change:** the left keepout stops 0.3 mm past U4's row jogs on each side (`U4_KEEPOUT_GAP`).
  Through U4 the pair already runs ±0.95 mm apart. A B.Cu track there passes the pair over
  the GND-poured B.Cu for about 1 mm, which is harmless at USB full speed (12 Mbit/s). The right
  half is unchanged.

## WS2c: fab outputs, renders, exports and CI (`pcb/scripts/stage_d.sh`, `pcb.just`, `.github/workflows/pcb.yml`)

### WS2c-1. Not-assembled parts are excluded by footprint attributes, not `kikit --ignore` (§9 stage 13)

- **Spec:** JP1, the test pads, the holes and J3 are excluded from assembly with `--ignore`.
- **Problem:** kikit 1.8.1 implements `--ignore` by deleting the footprints from the loaded board.
  Under KiCad 10.0.7 this corrupts the bindings (the same `BOARD.Remove` issue as WS2b-6): the
  following gerber plot fails with `'SwigPyObject' object has no attribute 'SetOutputDirectory'`
  and Python segfaults. Whether it fails depends on the ignore list.
- **Change:** `place.py` already marks those footprints `exclude_from_bom exclude_from_pos_files`
  (J3 `dnp`), and kikit honours that, so stage 13 runs without `--ignore`. `--missingError` still
  fails on any assembled part without an LCSC field.
- **Safeguard:** `stage_d.sh` then fails, naming the part, if JP1, J3, TP*, H* or STAB_* appears
  anywhere in `bom.csv` (each name in a quoted designator list counts) or `pos.csv`. It reads the
  designators into a variable and only then greps them. The first version piped them into
  `grep -q`, which stops at the first match. The writer then died of SIGPIPE, and under `pipefail`
  the pipeline returned 141, so most `bom.csv` hits went unreported (25 to 56 caught in 300 runs).
  Test, run 300 times per case on the left stage 13 outputs: JP1 at the top of `bom.csv`, TP3
  inside a quoted list, STAB_2U on the last line and H1 at the end of `pos.csv` each fail
  300/300. Both real outputs pass 300/300. A second guard also applies: every not-assembled
  schematic symbol has an empty LCSC field, so `--missingError` also fails if one reaches the BOM.
  The STAB_* footprints exist only on the board.

### WS2c-2. Renders use the `-full` image too (§9 stage 14)

- **Spec:** `kicad/kicad:10.0.7-full` only for the STEP; renders in the base image.
- **Change:** stage 14 runs entirely in the `-full` image (`pcb-fab`), so the committed renders
  show the stock 3D models (RP2040, passives, buttons) instead of a bare board. The output is
  otherwise the same command; renders are byte-identical between runs.
- **Pin:** `kicad/kicad:10.0.7-full` = `kicad/kicad@sha256:347d5b7d5d88207ba4217cdf594eeccd142279600d023e7a7e426f8599c77708`
  (the `tools/images.lock` line still needs this digest; that file is outside WS2c's paths).
- **Gap:** KiCad's library has no 3D model for J1 (HRO TYPE-C-31-M-12) or J2 (PJ-320D), and the
  hot-swap socket footprint has none, so the STEP lacks those bodies (export warns, does not fail).

### WS2c-3. Edge DXF in single-file mode, mm (§9 stage 14)

- `kicad-cli pcb export dxf -o <file>` treats `-o` as a directory in KiCad 10 (deprecated multi
  mode). The stage passes `--mode-single --output-units mm`, so `build/<side>/edge.dxf` is one file
  in mm (the default unit is inches).

### WS2c-4. The layout stages are seeded, so a clean rebuild reproduces the committed boards (§9 stages 7–12)

- **Spec:** `just pcb <side>` runs every stage; the committed boards are its output.
- **Problem:** the rebuild was not reproducible. KiCad gives every new item a random KIID and
  saves items sorted by KIID, so each `place.py` run wrote the footprints, and then the DSN, in a
  different order. Freerouting is deterministic for a given DSN, but a reordered DSN routes
  differently, and the completion router then closed every gap on some runs and left 1–2 items
  unconnected on others (2 of 2 CI rebuilds and 1 local clean run ended with 1 unconnected).
- **Change:** `place.py`, `route_critical.py` and `import_ses.py` seed KiCad's generator
  (`KIID.SeedGenerator`) from a CRC of the stage inputs (schematic and `layout.json`, or the board
  and session files) and a per-side base seed `KIID_SEED`. `pcb.just` runs every container with
  `PYTHONHASHSEED=0` so set iteration is fixed too. Two runs give byte-identical boards.
- **Seeds:** left 0x2, right 0x1. Each was tried with two others; these route to 0 unconnected
  and finish fastest (about 20 min per side). The committed boards are their output, re-made
  for this change: the footprint positions are unchanged, the copper is a new route. If a rule
  or placement change leaves items unconnected, try another base seed before retuning the router.
- **CI:** the `rebuild` job runs stages 1–12 from scratch and requires the result to equal the
  committed board (`git diff --exit-code -- pcb/<side>/`).

### WS2c-5. The STEP leaves out DNP parts, so J3's stock socket stays out of the case fit check (§9 stage 14, §4 G1)

- **Spec:** stage 14 exports the board STEP with its 3D models, and WS3's `fitcheck` requires
  0 mm³ between it and the case (§14). J3 is a low-profile socket, hand-soldered and DNP (§7), and
  socket + module + glass stay ≤ 8.2 mm above the PCB top (§4, G1).
- **Problem:** the J3 footprint carries the stock `PinSocket_1x05_P2.54mm_Vertical` model, a
  full-height socket 8.5 mm tall. Its top (Z 17.1) is 0.3 mm above the display-pocket ceiling
  (Z 16.8), so `just fitcheck` failed on each half with 8.265 mm³ (`left top hits solid 28`,
  `right top hits solid 13`). KiCad's library has no low-profile 1×5 socket model.
- **Change:** `kicad-cli pcb export step --no-dnp`. J3 is the only DNP footprint on either board,
  so the STEP loses exactly that body (81 → 80). The display stack's height belongs to gate G1,
  which sizes the case pocket. `stage_d.sh` fails if the socket model still reaches the STEP. The
  renders still show J3.
- **Result:** `just model && just fitcheck` in a fresh clone with these STEPs: 80 bodies and
  0.0000 mm³ on each half.
- **CI:** the new `fit` job in `pcb.yml` downloads both STEPs from the `board` job and runs
  `just model && just fitcheck` against them. `case.yml` has no STEP and checks the layout
  envelopes only.

## WS4: docs and microsite (`docs/`, `site/`, `README.md`, `.github/workflows/pages.yml`)

### WS4-1. Generated docs and the viewer also read the PCB design data and the committed boards (§14 WS4)

- **Spec:** `pinout.md` and `matrix.md` are generated from `layout`; the microsite reads only
  `layout` and the exported files.
- **Problem:** the as-built boards differ from the `layout` anchors where WS2 had to (WS2a-1
  references, WS2a-2 TP11, WS2b-1/WS2b-2 the left RP2040 and the flash). Docs and a viewer built
  from the anchors alone would show U1/U2 in the wrong place and could not name the parts.
- **Change:** `site/pcbdata.py` (stdlib) reads `pcb/scripts/design.py` and the footprint poses and
  Fab outlines of the committed `pcb/<side>/worxboard-<side>.kicad_pcb`.
  - `site/gen_docs.py` adds generated sections from them: part positions (`pinout.md`), sockets
    and diodes (`matrix.md`), and the JLC BOM and not-assembled tables in `bom.md`, between
    `GENERATED` markers. It fails if a design part's value or footprint differs from either board.
    `just docs-gen` / `docs-check` cover all three files.
  - `site/build_site.py` puts every assembled part of the boards into `manifest.json`, and the
    viewer draws them at their real positions. The keys, sockets, jacks, display and outline still
    come from `layout.json`.
- **Consumers:** none. When a board changes, `just docs-gen` refreshes the three files; the
  `pages` workflow's `gen_docs.py --check` fails until it is run.

### WS4-2. Pages are deployed by hand only (§14 WS4 acceptance)

- **Spec:** "the Pages site builds and deploys".
- **Change:** `pages.yml` runs only on `workflow_dispatch` (orchestration rule), so the site builds
  locally (`just site`) and in that workflow, but it has not been deployed. Deploying is one manual
  run from the Actions tab once Pages is enabled for the repository.

## WS5: integration and release (`tests/integration/`, `.github/workflows/release.yml`, `docs/verification.md`)

### WS5-1. No `v0.1.0-revA` tag and no release (§14 WS5)

- **Spec:** tag `v0.1.0-revA`; acceptance "all six workflows green on the tag" and "the release
  contains every artifact".
- **Change:** no tag or release was created (orchestration rule), and the gates fail
  ([verification.md](verification.md)), so a hardware tag would publish boards that cannot be
  ordered yet. `release.yml` is written and only triggers on a `v*` tag push. It was checked with
  actionlint and `test_release.py`, and its assembly step was run locally on a clean-clone
  `just all`. Acceptance is measured on `main` instead: the four push workflows are green there.

### WS5-2. Release assets are packed by `tests/integration/release.py`; `release.yml` builds them itself (§12, §14 WS5)

- **Spec:** `release.yml` attaches the gerbers/BOM/CPL zips, UF2s and case STEP/STL; it names no
  packing script.
- **Change:** WS5 owns only `tests/integration/` and `release.yml`, so the packing script lives in
  `tests/integration/` and is tested there. `firmware.yml`, `pcb.yml` and `case.yml` belong to other
  streams and have no `workflow_call` trigger, and reading another run's artifacts would race it, so
  `release.yml` runs the same recipes (`just fw`, `just pcb-sch` / `pcb-drc` / `pcb-fab`,
  `just model`) in its own jobs.
- **Assets:** `worxboard-<tag>-pcb-{left,right}.zip` (JLC `gerbers.zip`, `bom.csv`, `pos.csv` as the
  CPL, the board STEP, the Edge DXF), the six UF2s one by one under their `build.yaml` names (the
  names `docs/firmware.md` uses), `worxboard-<tag>-case-{step,stl}.zip` and `SHA256SUMS.txt`, as a
  pre-release. `pcb/production/<side>/` (§9: committed on hardware tags only) is filled by
  `release.py --production` before tagging, not by CI.

### WS5-3. Gate failures are recorded as strict expected failures, not fixed here (§14 WS5)

- **Spec:** G1–G3 "researched and recorded, with any fixes sent back to the owning stream".
- **Change:** the G1 and G2 fixes need WS0 geometry, WS2 re-placement and re-routing, and WS3 case
  changes. They are listed in [verification.md](verification.md#open-items-that-block-ordering)
  and checked by `tests/integration/test_gates.py` as strict xfails, which turn into errors once a
  fix lands so the marker is removed with it.

## REVIEW-FIX: fixes from the post-integration review

### REVIEW-FIX-1. The display SPI node names a `miso-gpios` pin (§4, §11.2)

- **Spec:** `nice_view_spi` (`raspberrypi,pico-spi-pio`) with clk GP2, mosi GP3 and cs GP5.
- **Problem:** the display is write-only, so the node had no `miso-gpios`. The pinned Zephyr driver
  (`drivers/spi/spi_rpi_pico_pio.c`, `spi_pico_pio_configure`) still sets up a MISO pin in 4-wire
  mode: with the property missing its spec is `{NULL, 0}`, and on the first transfer
  (`ls0xx_init` → `ls0xx_clear`, POST_KERNEL) it muxes **GP0 to PIO1** as an input. GP0 is UART0 TX,
  the wired-split TX line, and nothing re-applies the UART pins (no `detect-gpios`), so neither half
  could transmit over TRRS on any of the six builds.
- **Change:** `miso-gpios = <&gpio0 3 GPIO_ACTIVE_HIGH>` on both targets, reusing MOSI as ZMK's
  pico-spi-pio examples do (the PIO then sets GP3 as an output, after the input). Checked in the
  compiled `spi_pico_pio_config_0` of the right peripheral and left central: miso is now
  `{gpio0, 3}`. `tests/integration/fwdt.py` reads a missing `miso-gpios` as GP0, the driver's
  default, and `test_display_spi_keeps_off_uart_and_matrix` fails if any PIO SPI pin is a UART,
  row or column pin, or if miso is neither MOSI nor a spare pin.
- **Also:** `ZMK_KEYBOARD_NAME` now defaults to `worxboard` on both halves, so the
  `worxboard_right_central_EXPERIMENTAL` build no longer enumerates with an empty USB product name.

### REVIEW-FIX-2. Decoupling caps sit at the U1 exits on locked copper (§6.4; supersedes the WS2b-5 decoupling note)

- **Spec:** 100 nF on every IOVDD pin, USB_VDD, ADC_AVDD and both DVDD pins; 1 µF on VREG_IN and
  VREG_VOUT, placed at the pins (RP2040 hardware design guide).
- **Problem:** WS2b-5 put the 3V3 caps "near the exits", but they were placed 4–13 mm away (east of
  U1 on the right, and on the far side of U1 on the left) and joined by whatever the autorouter and
  the rip-up left: on the left half C8–C13 and C18 reached U1 only through a 75–86 mm detour under the
  key field. DVDD pin 23 had no cap within 31–34 mm, VREG_VOUT's 1 µF was 13–17 mm from pin 45, and
  netcmp only checked that a cap was on the net.
- **Change:** the caps are in `place.CLUSTER` (U1 frame, the same on both halves) at the three 3V3
  exits and the two 1V1 fan ends, and `route_critical.decoupling()` joins each one to its exit and
  its GND pad to its own via with locked copper:
  - north bus from the 48/49 exit: C14, C15, C13, C10 (USB_VDD 48, IOVDD 49);
  - east bus from the pin-42 exit: C18 (1 µF VREG_VIN), C11, C12 (IOVDD 42, ADC_AVDD 43,
    VREG_VIN 44, and IOVDD 33 / 22 on the inner join);
  - pin-1 exit: C8, C9 (IOVDD 1, and 10 on the inner join);
  - pin-50 fan end: C16 and C19 (1 µF) for DVDD 50 and VREG_VOUT 45 (inner join); pin-23 fan end: C17.
- **Remaining gap:** IOVDD 10, 22, 33 and VREG_VOUT 45 have no outward escape between the 0.4 mm
  fan-out, so they still reach their caps through the joins inside the pad ring.
- **Check:** `checks.py` measures the copper path pin → nearest cap and cap → nearest U1 supply pin
  per net, and each cap's GND via (limits `PIN_CAP_MAX_MM`, `CAP_PIN_MAX_MM`, `CAP_GND_VIA_MM`).

### REVIEW-FIX-3. No vias in SMD pads (§8.4)

- **Problem:** the completion router treated a same-net SMD pad as free for a via, and Freerouting
  could leave one too: 13 (right) and 15 (left) vias touched SMD pads (0402 caps, the flash, the
  LDO, the ESD arrays, SOD-123 diodes, socket pads, test points, U1 pins 15, 43 and 44), and one
  drill cut 0.15 mm into U1 pin 43. The vias are not plugged, so solder wicks into them, and JLC's
  DFM check flags drill hits on SMD pads.
- **Change:** `complete_routes` keeps vias off every SMD pad of any net (grid and exact checks), and
  `import_ses.py` deletes session vias that touch an SMD pad so the completion router rejoins those
  nets outside the pads. `checks.py` fails on any via overlapping an SMD pad; the thermal via array
  in the RP2040 exposed pad (locked, by design) is the only exception. Vias may still end close to a
  pad edge (a few within 0.05 mm); the boards tent vias on both sides, so the mask keeps solder
  out of them.

### REVIEW-FIX-4. The fit check adds the layout envelopes of parts the STEP lacks (§10.10)

- **Spec:** `check_fit.py` loads the PCB STEP when it exists, else the `layout` envelopes.
- **Problem:** the STEP has no body for J1, J2 or the 37 hot-swap sockets (WS2c-2) and leaves out
  J3 (WS2c-5), so once it existed the check could not see a jack, USB-C, display or socket clash.
- **Change:** with the STEP, `check_fit.py` also checks the `layout` envelopes of J1, J2, J3 + module
  and the bottom-side sockets (`STEP_GAPS`). The envelopes are the layout's part sizes, so gate
  G1/G2 fixes to those sizes reach the check automatically.

### REVIEW-FIX-5. JLC CPL rotation corrections (§9 stage 13)

- **Problem:** `pos.csv` held raw KiCad rotations; JLC's library uses another zero orientation for
  several packages.
- **Change:** stage 13 passes `pcb/scripts/jlc_rotations.csv` to kikit (`--correctionpatterns`):
  QFN-56 and SOIC-8 +270°, SOT-23-5/6 −90°, HRO TYPE-C-31-M-12 +180°, from the JLCKicadTools table
  of 2024-09. These community tables have changed over time (SOT-23 was +180°), so
  `docs/ordering-jlcpcb.md` keeps the placement preview as the check for every IC, diode and
  connector.

### REVIEW-FIX-6. The display window is centred on the LCD viewing area (§4, §10 change 4; supersedes WS0-2)

- **Problem:** WS0-2 centred the window at y 60.0. Gate G1 found the viewing area at y 43.9–69.2, so
  the window (47.0–73.0) hid the header end, and its far edge left a 1.0 mm wide, 0.8 mm thick bar of
  top skin over the display pocket to the C6R1 well, unsupported for 15 mm (a CNC chatter risk).
- **Change:** `layout/display.py` centres the window on the viewing area from the header position
  (header y − 1.3 + 4.6 + 25.28 / 2 = 56.54): window y 43.54–69.54. The bar to the C6R1 well is now
  4.5 mm, and the layout test keeps it ≥ 3.0 mm. G1 open item 3 is closed; if the header moves (item
  2), the window follows.

### REVIEW-FIX-7. Stabiliser cut-outs: Cherry spec, oriented with the PCB holes (§5, §10.8)

- **Problem:** the plate cut-outs' long half pointed away from the PCB's Ø4.0 stabiliser holes on all
  four 2u keys (1.2 mm off for a PCB-mount stabiliser), they were plain 12.3 × 6.65 rectangles without
  the Cherry side and end notches, and the left top was not the mirror of the right
  (`MIRROR_TOL_MM = 0.1` let it pass). `layout.stab_holes()` gave no orientation, so the PCB and the
  case each chose one.
- **Change:** `layout.stab_dir(key, side)` is the direction of the stabiliser housings (Ø4.0 holes),
  −U on the right and its mirror on the left, exported as `stab_dir` in `layout.json`. `place.py`
  turns `Stab_MX_2u` to it (the left footprints turn 180° from before), and `case.stab_cuts` builds
  the Cherry cut-out (−5.53…+6.77 across, 6.65 along, side notch −2.3…+0.5, end notch 3.3 × 1.2) on
  that side. The 0.875 mm side notch is 1.0 mm for a 1 mm end mill; outside corners are R0.5. The
  halves are now mirror images, and `MIRROR_TOL_MM` is 0.005.

### REVIEW-FIX-8. Crystal: R7 beside Y1, short XOUT, no copper under Y1 (§6.4)

- **Spec:** Y1 within 3 mm of XIN/XOUT, a GND guard and no traces underneath; 1 kΩ in series on XOUT.
- **Problem:** COL0 (and on the right COL1 and XOUT) ran on B.Cu under Y1; XOUT was 13 mm long with
  two vias, because the pin-21 fan end was boxed in by Y1's GND pad and the pin-23 fan.
- **Change:** Y1 moves 0.7 mm away from pin 23 in the U1 frame (still 2.93 mm from XIN/XOUT), R7
  sits between Y1 and the pin-23 fan end, and `route_critical.crystal()` lays XOUT → R7 → Y1 pad 3
  locked (about 5 mm of XOUT, no via). A B.Cu rule area over Y1's courtyard + 0.25 mm forbids tracks and
  vias, so both pours stay solid under the crystal; F.Cu cannot pass between its pads. `checks.py`
  fails on any B.Cu track or via under Y1. The left C6 moves 0.5 mm out to keep its courtyard clear.

## ELEC: parts, power path and display socket for a turnkey JLCPCB order (`pcb/scripts/design.py`, `netcmp.py`, `stage_d.sh`, `pcb/lib/`, `tests/integration/stock.py`)

Stock and library data below are from the JLC component-detail and LCSC product endpoints on
2026-11-02 23:35 UTC (`tests/integration/stock.py` reproduces them). For 5 + 5 boards every line
now has more than 50 at JLC and covers the order with JLC's attrition.

### ELEC-1. Discontinued and low-stock parts replaced (§7, gate G3)

- **Problem:** the hot-swap socket C2803348 (Kailh CPG151101S11) is discontinued: 0 at JLC and
  LCSC, LCSC `stop_product`, JLC "no longer manufactured". JLC flags the flash C113767 "no longer
  manufactured" (163 left, LCSC 0). The crystal C91749 is down to 19 at JLC against 10 needed.
- **Change** (`design.py`, same footprints, values and nets):

  | Ref | Was | Now | JLC | Stock JLC / LCSC | Why it fits |
  |---|---|---|---|---|---|
  | SK101–SK137 | C2803348 | **C41430893** HanElectricity CPG151101S11-16 | extended, SMT | 231 751 / 168 680 | drawing: Ø3.00 holes 6.35 × 2.54 apart, pads 2.55 × 2.5, terminals 14.5 mm, body 1.85 mm: the `SW_MX_Hotswap_Kailh` land pattern. Second source **C49352235** (CPG151101S11-2, 30 973) |
  | U2 | C113767 | **C97521** Winbond W25Q128JVSIQ | **basic**, SMT | 76 588 / 865 | the same chip in the same SOIC-8 208 mil package |
  | Y1 | C91749 | **C49304726** YXC XL2EL89CRI-111YLC-12M | extended, SMT | 13 833 / 13 790 | 12 MHz 3225, CL 18 pF (the 27 pF caps give 13.5 pF + about 4 pF stray), ±10 ppm, ESR 80 Ω max (was 100 Ω), pins 1/3 crystal and 2/4 GND as `Crystal_GND24`. Basic fallback **C9002** (CL 20 pF: tens of ppm, far inside USB's ±2500 ppm) |

- **Checked, unchanged:** every other line (C2040 7 062, C51118 6 190, C95562 5 743 are the
  thinnest). Basic: C1525, C11702, C25744, C52923, C25905, C8598, C15525, C81598 and now C97521;
  everything else is extended. In Standard PCBA JLC charges the same feeder fee for basic and
  extended parts, so the swaps buy stock, not fees.
- **Not checked by a build:** that JLC solders C41430893 cleanly (no field report of this copy).
- **Consumers:** FAB (corrected in ELEC-7: the new parts need the same correction *values* as the old
  ones, but `jlc_rotations.csv` has no row for `worxboard:SW_MX_Hotswap_Kailh`, so all 37 sockets per
  half go out uncorrected, 3.9 mm off and turned 180°; it needs `0.635;3.81;180`. The SOIC-8 row (270°)
  and no row for the 3225 crystal are right), DOCS (`bom.md`, `ordering-jlcpcb.md`, verification G3).

### ELEC-2. U4's clamp reference is VSYS: the USB-C VBUS can no longer be back-driven (§6.3)

- **Spec:** USBLC6-2SC6 (U4) on the USB data lines, its VBUS pin on VBUS.
- **Problem** (docs/electrical.md): the VBUS pin is the cathode of U4's two upper steering diodes
  and of its TVS. When a half runs from VLINK with no host but its USB device enabled (the left
  central, or the UF2 bootloader), the RP2040's 1.5 kΩ D+ pull-up to 3.3 V forward-biases the
  I/O1-to-VBUS diode, and with only R5 + R6 (20 kΩ) as load VBUS sits near 2.5 V: J1's VBUS is
  back-driven (about 0.13 mA, above vSafe0V) and VBUS_SENSE reads 1.25 V without a host. The cause
  is the topology, not a part value: with the reference on VBUS, any D+ pull-up drives VBUS
  whenever no host holds it at 0 V.
- **Analysis:** the reference pin needs a rail that (1) is at or above every normal I/O level
  whenever the I/Os can be driven, so the upper diodes never conduct (D± ≤ 3.6 V, the pull-up
  3.3 V), (2) stays under the 5.25 V stand-off, (3) can absorb the clamp current, and (4) cannot
  carry that current back out to the connector. VSYS meets all four: it is the diode-OR output,
  4.2–5.2 V whenever the half has power from either source (VBUS − D1, or VLINK through the two
  F1s), it carries 2 × 10 µF, and D1 blocks any path from it back to J1. 3V3 would meet (1)–(3) but
  puts ESD energy straight on the RP2040 rail (abs. max 3.63 V) instead of in front of the LDO. The
  connector VBUS fails (1) whenever the half runs from VLINK, so it cannot be made back-drive free.
- **Change:** U4 pin 5 (VBUS) on **VSYS**. VBUS now reaches only J1, D1's anode and R5. With no
  host, VBUS sits at D1's reverse leakage across R5 + R6: about 5 µA at 4.5 V and 25 °C (CJ
  B5819W curve), 0.1 V; it reaches vSafe0V (0.8 V) only above about 60 °C. VBUS_SENSE is now a
  clean host-presence signal. `netcmp.py` fails if anything else lands on VBUS or if U4's
  reference leaves VSYS (or U5's leaves VLINK); a mutation run of each case fails as intended.
- **Trade-off:** U4's TVS no longer clamps the VBUS line itself. A positive surge on VBUS goes
  through D1 into VSYS, where U4's TVS and the bulk caps clamp it; a negative one is blocked by D1
  and reaches GP26 only through R5 (10 kΩ). The VBUS contacts sit inside the receptacle, so
  discharges land on the grounded shell first. A VBUS TVS is a rev B option, not added here.
- **Re-checked, unchanged:** D1 B5819W (1 A, 40 V, 9 A surge); AP2112K (VIN ≤ 6 V, 250 mV dropout
  at 600 mA: the far half's VSYS of 4.2 V or more leaves margin); F1 nSMD025-24V (0.35 Ω, R1 max
  2.5 Ω: two in series drop under 0.1 V at the 40 mA of a half); C1–C3 10 µF 6.3 V on ≤ 5.2 V;
  U5's reference on VLINK (4.2–5.2 V, or floating with JP1 cut on both halves, where the TVS still
  clamps and nothing reaches a USB connector); two hosts at once still meet only behind their own D1.
- **Consumers:** PCB (re-route U4 pin 5 to VSYS and keep it short: ST asks for a short track from
  the rail to the VBUS pin, and the nearest VSYS parts today, D1, C1 and C2, are 11–20 mm from it), DOCS (`electrical.md` power path, the VBUS note).

### ELEC-3. J3 is JLC-assembled: a 5.0 mm THT socket, with its own 3D model (§4 G1, §7; amends WS2c-1, supersedes WS2c-5)

- **Spec:** J3 is a low-profile 1×5 socket, DNP, hand-soldered by the builder.
- **Problem:** a turnkey order leaves nothing to solder on the PCB. JLC hand-solders THT parts
  (THT, `manualWeld`). Its 1×5 2.54 mm THT female sockets in stock are 5.0 mm (C27985230), 5.7 mm
  (C46061764, C55218875) and 8.5 mm (C50950, C54876727); there is no 3.5 mm part, so the G1 stack
  of 6.0–6.3 mm under today's case cannot be met with a stock male header.
- **Choice:** **C27985230**, Hong Cheng HC-PM254-5.0H-1x5PZ (extended, THT, 6 399 at JLC): 5.0 ±0.15
  mm tall, square contacts for 0.64 mm pins, 3.0 mm tails, Ø1.02 recommended hole (the footprint's
  1.0 mm drill fits the 0.64 × 0.4 tail). The nice!view ships with a 5-pin socket **5 mm** tall and a
  male header that adds 2 mm, "a height of 7mm" (nicekeyboards.com, typeractive.xyz "5-Pin Sockets":
  "the same sockets that come with the nice!view"). So a stock nice!view with its own header soldered
  on, unmodified, plugs into J3 and sits as its maker intends. Fallback C46061764 (5.7 mm, stack
  +0.7 mm). The lowest-stack option was chosen because every extra millimetre has to come out of
  the case top over the display.
- **Change:**
  - `design.py`: J3 `dnp=False`, LCSC C27985230, value `HC-PM254-5.0H-1x5PZ` (the BOM comment JLC
    sees), footprint **`worxboard:PinSocket_1x05_P2.54mm_Vertical_H5.0mm`**. Reference, symbol,
    pins and nets are unchanged.
  - `pcb/lib/worxboard.pretty/PinSocket_1x05_P2.54mm_Vertical_H5.0mm.kicad_mod`: KiCad's
    `PinSocket_1x05_P2.54mm_Vertical` with identical pads, silk, courtyard and origin (pin 1, pins
    along +y at 0°), only the name and the 3D model differ. `place.py` loads it like the other
    `worxboard` footprints. The JLC CPL correction worked out for the stock footprint (X 0, Y 5.08,
    rotation 270) is the right value for this one too, but kikit matches rows by footprint name and
    `jlc_rotations.csv` has no row under either name: J3 goes out uncorrected until FAB adds one
    (corrected in ELEC-7).
  - `pcb/lib/worxboard.3dshapes/PinSocket_1x05_P2.54mm_Vertical_H5.0mm.step`, written by
    `pcb/lib/gen_models.py` (build123d, deterministic): body 13.4 × 2.55 × 5.15 mm and 0.64 × 0.4
    tails 3.2 mm below the PCB top, the drawing's upper tolerances, so the fit check sees the
    largest socket JLC can fit. Referenced as `${KIPRJMOD}/../lib/worxboard.3dshapes/…`.
  - `stage_d.sh`: J3 leaves `NOT_ASSEMBLED` and must be in both `bom.csv` and `pos.csv`; the STEP
    must carry `PinSocket_1x05_P2.54mm_Vertical_H5.0mm` and must not carry KiCad's 8.5 mm
    `PinSocket_1x05_P2.54mm_Vertical`. `--no-dnp` stays (no DNP part is left).
- **Checked** on a scratch copy (stages 1–9, then stage 13–14 on the placed, unrouted left board):
  `bom.csv` has 22 lines (21 LCSC numbers) with `HC-PM254-5.0H-1x5PZ,J3,…,C27985230`, `pos.csv` 119
  parts with J3, `--missingError` passes, and the STEP's J3 body spans 13.4 × 2.55 mm around pin 3 at
  Z 0–5.15 mm above the PCB top. The committed boards still carry the old J3 until the re-placement.
- **Display stack** (PCB top = case Z 8.6), for the case pocket and window:

  | Item | Above the PCB top | Case Z |
  |---|---|---|
  | J3 body top | 5.0 (model 5.15) | 13.6 (13.75) |
  | module PCB underside: 5 mm socket + stock header | 7.0 nominal (vendor), 7.5 with a 2.5 mm carrier | 15.6–16.1 |
  | lowest module parts (1.0 below its PCB) | 6.0–6.5: above the plate top (5.0) | 14.6–15.1 |
  | module PCB top | 8.0–8.5 | 16.6–17.1 |
  | glass top (0.9) | **8.9 nominal, 9.4 with a 2.5 mm carrier, 9.75 at full tolerance** | 17.5–18.35 |

  The pocket ceiling must be at least **Z 18.4** (9.8 above the PCB top), 1.6 mm above today's 16.8
  and 0.8 mm above `Z_TOP` (17.6): the case top needs a raised bezel over the display (or the window
  opened to the glass). The module now clears the plate, so only the J3 body (13.4 × 2.55, Z up to
  13.75) has to pass through the plate and spacer. Two G1 items still apply: the header's soldered
  pin tips can stand up to about 2 mm above the module PCB over the header row unless they are
  trimmed flush, and the module far end must stay inside the pocket (G1 open item 2, J3 row to y 39.925),
  because past y 75.125 it reaches over the edge of the C6R1 keycap.
- **Consumers:** PCB (J3 footprint name; G1 items 1 and 2 when re-placing), FAB (`jlc_rotations.csv`
  row `^worxboard:PinSocket_1x05_P2\.54mm_Vertical_H5\.0mm$` → 0, 5.08, 270), CASE (the stack
  above; `check_fit.py`'s J3 + module envelope), DOCS (`bom.md` and `site/gen_docs.py` list J3 as
  not assembled; build guide: no socket to solder).

### ELEC-4. The G3 stock check reads JLC's component record and has a 50-unit floor (§7)

- **Change:** `tests/integration/stock.py` reads JLC's component detail (library type, SMT/THT,
  stock, attrition, the "no longer manufactured" note) and LCSC's record, needs
  max(50, 2 × (per board × boards + attrition)) per LCSC number, and fails on a short, discontinued
  (either shop), unknown or retired part (C2803348, C113767, C91749). `tests/integration/test_stock.py`
  checks offline that every part with a body is in the JLC BOM with an LCSC number, J3 included,
  none is DNP, both halves share one BOM, no retired part is back, and the verdicts on canned records.

### ELEC-5. Hand-offs: the boards, the docs part table and the CPL still follow the old parts (§9, §14)

ELEC-1 to ELEC-3 change only the schematic side. Three consumers must follow before CI is green
and the docs build again. Checked on 2026-11-03, 00:10–00:50 UTC.

- **Boards (PCB), CI is red until they are re-placed and re-routed.** `kicad-cli pcb drc
  --schematic-parity` on both committed boards gives 0 violations, 0 unconnected and the same four
  parity errors on each half:
  1. U4 pad 5: `net_conflict`, VBUS on the board, VSYS in the schematic (ELEC-2);
  2. J3 footprint: `Connector_PinSocket_2.54mm:PinSocket_1x05_P2.54mm_Vertical` on the board,
     `worxboard:PinSocket_1x05_P2.54mm_Vertical_H5.0mm` in the schematic (ELEC-3);
  3. J3 value: `nice!view` on the board, `HC-PM254-5.0H-1x5PZ` in the schematic;
  4. J3 attributes: DNP on the board, fitted in the schematic.

  So the pcb workflow's `board` jobs fail at `just pcb-drc` from 0b86596 on (one error there, four
  from 171c62d), and the `fit` job is skipped. The `rebuild` jobs fail from f5f051d on, by design:
  `place.seed_kiids` seeds the KIIDs from the schematic bytes, so any schematic edit, an LCSC field
  included, changes the rebuilt board (WS2c-4). `tests/integration/test_pins.py::
  test_netlist_equals_committed_board` fails on U4 pad 5 of both halves (only `release.yml` runs
  it). The schematic side cannot clear any of this: both halves have to be re-placed and re-routed
  from the current schematics, and committed with their renders (`docs/images/pcb-<side>-*.png`,
  which the `board` job compares).

  The pipeline takes the new schematics as they are. CI run 41548543572 (b077f78) rebuilt both
  halves from scratch, and both reached `just pcb-finish`'s DRC gate with 0 violations, 0
  unconnected and 0 parity errors (artifacts `worxboard-pcb-rebuild-left` / `-right`; Freerouting
  left 29 / 41 connections, the completion router closed them). The right job then failed only at
  the comparison with the committed board. The left job failed in `checks.py` first: killed for
  memory (exit 137) after 6 minutes. That is a `checks.py` bug, not a board fault, and it can hit
  any board: `copper_graph()` adds the edge weight `math.dist(c, d) - s`, which comes out at about
  -3e-17 when `project()` lands on a segment end, and `dijkstra()` then loops on the negative
  cycle and fills the heap. The rebuilt left board has 166 such edges on 3V3 (the committed one
  62, the rebuilt right 10), and the search from C14 runs into one. Clamping the weight in `copper_graph`'s
  `edge()` to `max(0.0, w)` fixes it: `checks.py left` then passes 7 of 7 in 1 s (USB D+ 24.73 mm,
  D− 23.92 mm, skew 0.81). On a scratch copy with both rebuilt boards and that clamp, `just
  pcb-drc` passes on both halves, `just pcb-fab` passes on both (`bom.csv` 22 lines with J3 as
  C27985230, `pos.csv` 119 parts, the STEP carries the 5.0 mm J3 body) and `just fitcheck` gives
  0 mm³ against today's case. That fit check still models the module and glass with the old
  8.2 mm stack (`Z_DISPLAY_TOP` 16.8); the 9.75 mm one of ELEC-3 is for CASE.

  In the rebuilt right board U4 pin 5 reaches VSYS over 17.6 mm of track (JP1), 21.9 mm to D1 and
  22.5 mm to C1. U4's own TVS clamps pin 5 to GND inside the package, so this works, but a shorter
  run is better (ELEC-2). Do G1 open items 1 (J3 turned 180°, pin 1 at high x) and 2 (J3 row at
  y 39.925) in the same re-placement.
- **Docs part table (DOCS).** The hand-kept `LCSC` table in `site/gen_docs.py` lacks the four new
  numbers and `NOT_ASSEMBLED` still lists J3. Today `_check_boards()` stops `docs-gen` and
  `docs-check` first, because J3 differs from the board. Once the boards are rebuilt,
  `bom_assembled()` raises `KeyError: 'C97521'`, so `just docs-gen`, `just docs-check` and the
  pages workflow (`gen_docs.py --check`) crash until the table is fixed:
  - add, library type from JLC's record:
    `"C97521": ("W25Q128JVSIQ, 16 MB QSPI flash", "[J]", False)` (basic),
    `"C49304726": ("12 MHz crystal, 18 pF, 3225", "[J]", True)`,
    `"C41430893": ("MX hot-swap socket CPG151101S11-16", "[J]", True)`,
    `"C27985230": ("1×5 2.54 mm female socket, 5.0 mm, THT", "[J]", True)`;
  - drop C113767, C91749 and C2803348 (no longer in the design), and the `J3` row of
    `NOT_ASSEMBLED` (it would list J3 among the parts JLC does not fit);
  - three existing rows say basic where JLC says extended (`componentLibraryType` `expand`):
    C51118, C1557 and C2909343 need `True`.
- **CPL (FAB).** This bullet understated the gap; ELEC-7 lists every row. `pcb/scripts/jlc_rotations.csv`
  needs J3's row under the new footprint name,
  `"^worxboard:PinSocket_1x05_P2\.54mm_Vertical_H5\.0mm$",".*",0,5.08,270`, worked out on
  C27985230's own EasyEDA footprint (5 of 5 pins, 0.0 mm pad error). The swaps change no correction
  *value*: on each new part's own EasyEDA footprint, C41430893 and C49352235 need what C2803348
  needed on `worxboard:SW_MX_Hotswap_Kailh` (pads within 0.28 mm), C97521 what C113767 needed
  (SOIC-8, 270°) and C49304726 what C91749 needed (none). But the table never had the socket row,
  `0.635;3.81;180`, so every socket goes out uncorrected (ELEC-7).
- **Checked while here, Y1 start-up.** The part research left the crystal's start-up margin open.
  C49304726 has the same 18 pF load and a lower ESR (80 Ω against 100 Ω, LCSC parameters) than
  C91749, the Corne v4.1 production crystal that §6.4 clones with the same 27 pF caps and 1 kΩ on
  XOUT. The gain the oscillator needs scales with ESR × (C0 + CL)², so with equal CL and a shunt
  capacitance of the same order it needs no more than in that proven circuit. The Pico's reference
  crystal (lower load and ESR) has more margin still but would need other load caps; not changed.

### ELEC-6. The board must carry the parts it is ordered with; G3 re-checked on 2026-11-03 (§7, §9 stages 12–13)

- **Problem:** both committed boards still carry C2803348 on SK101–SK137, C113767 on U2, C91749 on Y1
  and the DNP `nice!view` J3 on the stock footprint, and nothing compared a board's part numbers with
  `design.py`: KiCad's schematic parity checks value, footprint and DNP but not the LCSC field.
  kikit 1.8.1 (`kikit/fab/jlcpcb.py`, `fab/common.py`) builds the order from two files. `bom.csv`
  comes from the **schematic** (`extractComponents(schematic)`: value, footprint, LCSC, DNP,
  in-BOM). `pos.csv`, its rotation corrections and the gerbers come from the **board**: the
  corrections are matched on the board footprint's library id. So `just pcb-fab right` on the
  committed board writes a correct BOM today (C41430893, C97521, C49304726, J3 as C27985230; checked
  on a scratch clone). But it places J3 from the board's stock `PinSocket_1x05_P2.54mm_Vertical`,
  uncorrected at 90°, over copper that still takes U4 pin 5 to VBUS. The two halves of the order
  describe different boards, and a board that was not re-placed after an LCSC-only swap passes
  parity.
- **Change:**
  - `design.py`: `RETIRED` (C2803348, C113767, C91749), moved from `tests/integration/stock.py`,
    which imports it.
  - `netcmp.py --board <kicad_pcb> <side> [<kikit dir>]` checks the board:
    - every footprint is a `design.py` part with its footprint, value, LCSC number and DNP /
      `exclude_from_bom` / `exclude_from_pos_files` flags, or a `board_only` footprint (STAB_*) with
      no LCSC that stays out of the BOM and CPL;
    - no retired number is on the board.

    With the kikit directory, `bom.csv` and `pos.csv` must each list the 119 fitted parts exactly
    once, and every `bom.csv` designator must have its `design.py` LCSC number. The netlist mode now
    also fails on a retired number.
  - `stage_d.sh` runs it on the board and kikit's output right after step 13. It replaces the
    `NOT_ASSEMBLED` / `ASSEMBLED_THT` grep checks (WS2c safeguard, ELEC-3), which it covers.
    `stage_c.sh` runs the board half after `checks.py`, so `pcb-finish` and the CI `rebuild` job
    fail when a board's fields drift from `design.py`.
  - `tests/integration/test_stock.py::test_committed_board_orders_the_design_parts` runs the same
    check on both committed boards. Two offline tests show that it catches a stale board, and that it
    catches a wrong kikit BOM / CPL (canned CRLF files as kikit writes them).
- **Checked** on 2026-11-03:
  - The committed boards fail with 7 errors per half: J3 DNP, footprint, value and LCSC;
    SK101..SK137 on C2803348; U2 on C113767; Y1 on C91749. On a scratch clone, `just pcb-fab right`
    on the committed board now stops at this step.
  - The CI-rebuilt boards of run 41548543572 (b077f78, the same schematics) pass `just pcb-fab left`
    and `just pcb-fab right` end to end. That covers the board check and bom/pos, 119 parts, plus
    renders, DXF and STEP with the 5.0 mm J3. Stage C's call passes on both halves in the
    `kicad/kicad:10.0.7` container (Python 3.13).
  - Mutation runs each fail with the expected message: a retired socket in `bom.csv`; J3 missing
    from bom/pos; JP1 in a CRLF `pos.csv`; a designator twice; SK101 DNP on the board; a STAB_ with an
    LCSC field; C113767 in a netlist.
  - `just pcb-sch-all`: ERC 0 and netcmp 10/10 on both halves; the schematics and `pcb/lib` are
    unchanged.
  - `pytest tests/integration`: 101 passed, 6 xfailed and 4 failed. The four failures are
    `test_pins.py::test_netlist_equals_committed_board` (U4 pad 5) and the new
    `test_committed_board_orders_the_design_parts`, on both halves. With the rebuilt boards in place
    `test_stock.py` passes 17 of 17. Only `release.yml` runs these tests, so a release cannot ship
    the stale boards.
- **G3 re-checked**, `stock.py --boards 5`, 2026-11-03 01:09 UTC (JLC stock; all 21 pass, need ≥ 50):

  | LCSC | Refs | JLC library | JLC stock |
  |---|---|---|---|
  | C1525 | C5, C8–C17 | basic | 34 934 485 |
  | C1557 | C6, C7 | extended | 299 790 |
  | C2040 | U1 | extended | 7 057 |
  | C7519 | U4, U5 | extended | 39 942 |
  | C8598 | D1 | basic | 959 043 |
  | C11702 | R7, R9, R11, R12 | basic | 21 096 589 |
  | C15525 | C1–C3 | basic | 9 925 980 |
  | C25744 | R5, R6, R8, R10, R13 | basic | 16 124 475 |
  | C25905 | R1, R2 | basic | 4 951 019 |
  | C51118 | U3 | extended | 6 174 |
  | C52923 | C4, C18, C19 | basic | 10 649 098 |
  | C70069 | F1 | extended | 18 960 |
  | C81598 | D101–D137 | basic | 3 727 207 |
  | C95562 | J2 | extended | 5 743 |
  | C97521 | U2 | basic | 76 364 |
  | C165948 | J1 | extended | 175 775 |
  | C455280 | SW1, SW2 | extended | 127 983 |
  | C2909343 | R3, R4 | extended | 274 894 |
  | C27985230 | J3 (THT) | extended | 6 399 |
  | C41430893 | SK101–SK137 | extended | 231 751 |
  | C49304726 | Y1 | extended | 13 833 |

  Fallbacks: C49352235 (socket, extended, 30 873), C9002 (crystal, basic, 302 814), C46061764
  (5.7 mm J3, extended THT, 4 487). Still retired: C2803348 (0 at JLC and LCSC, `stop_product`),
  C113767 (163 at JLC, "no longer manufactured"), C91749 (19).
- **CI stays red until PCB commits the re-placed boards.** No ELEC path can turn it green. The
  `pcb` workflow's `board` jobs fail at `just pcb-drc`: four parity errors per half, ELEC-5. The
  `rebuild` jobs fail too: the left in `checks.py` (exit 137), the right at the comparison with the
  committed board. Both clear only with one PCB commit that holds:
  1. both halves re-placed and re-routed from the current schematics, with G1 items 1 and 2 (J3
     turned 180° so pin 1, MOSI, sits at high x under the module's pin 1, and the J3 row at y
     39.925);
  2. their renders `docs/images/pcb-<side>-{top,bottom}.png`;
  3. `checks.py`'s `copper_graph()` edge weight clamped to `max(0.0, w)` (ELEC-5);
  4. FAB's rows in `jlc_rotations.csv`: J3, and, as ELEC-7 sets out, the hot-swap sockets and J2
     added and U1 and J1 corrected. CI does not need them to pass, but without them the CPL that
     commit builds misplaces 41 parts per half (U1, J1, J2, J3, SK101–SK137); neither CI nor this
     check tests rotations.

  ELEC keeps J3 pin *n* = nice!view pin *n* (1 MOSI, 2 SCK, 3 3V3, 4 GND, 5 CS). The G1 pin order is
  fixed by rotating the footprint, not by renumbering the pins.

### ELEC-7. The CPL corrections FAB owes, in full (§9 stage 13; corrects ELEC-1, ELEC-3, ELEC-5)

- **Problem** (verifier, 2026-11-03): ELEC-1, ELEC-3 and ELEC-5 said the corrections "apply
  unchanged" and that the swaps "leave the other corrections as they were". That holds for the values
  only. kikit applies a `jlc_rotations.csv` row by the board footprint's library id and falls back
  to 0, 0, 0 (`applyCorrectionPattern`). The table has no row for `worxboard:SW_MX_Hotswap_Kailh` (it
  never had), none for J3 under either footprint name and none for the PJ-320D, and its QFN-56 and
  USB-C rows are wrong. In the `pos.csv` that `just pcb-fab right` builds from the CI-rebuilt board
  of run 41548543572, SK101 sits at its switch centre (191.45, −67.01, B, 0°), 3.86 mm from the
  midpoint of its pads and turned 180° from the way its body clears the switch post. J3 sits at its
  pin 1 (90°), U1 at 270° and J1 at 0°. 41 of the 119 parts per half would be placed wrong: U1, J1,
  J2, J3 and SK101–SK137.
- **The rows FAB needs.** These come from the research `corrections.json` (2026-11-02), re-derived by
  the CPL review from the raw EasyEDA records with KiKit 1.8.1's own functions. Each ELEC part was
  checked on its own LCSC footprint:

  | kikit footprint pattern | X;Y;rotation | Refs (LCSC) | Committed table | Evidence |
  |---|---|---|---|---|
  | `^Package_DFN_QFN:QFN-56-1EP_7x7mm_P0\.4mm_EP3\.2x3\.2mm$` | 0;0;0 | U1 (C2040) | 270: **wrong**, U1 90° off, pin 1 on pad 43 | 57 of 57 pins agree only at 0 |
  | `^Package_SO:SOIC-8_5\.3x5\.3mm_P1\.27mm$` | 0;0;270 | U2 (C97521) | 270: right | 8 of 8 |
  | `^Package_TO_SOT_SMD:SOT-23-[56]$` | 0;0;−90 | U3 (C51118), U4, U5 (C7519) | −90: right | 5 of 5, 6 of 6 |
  | `^Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12$` | 0;−1.394;0 | J1 (C165948) | 0;0;180: **wrong**, reversed and 4.4 mm off | locating pegs. The SMD pads alone give −1.572, 0.18 mm apart (a land-pattern difference). EasyEDA's footprint changed in 2026-08, so the 2024 community 180° no longer applies |
  | `^Connector_Audio:Jack_3\.5mm_PJ320D_Horizontal$` | 0.776;0;90 | J2 (C95562) | no row: **wrong**, 90° and up to 7.3 mm off | peg holes exact |
  | `^worxboard:SW_MX_Hotswap_Kailh$` | 0.635;3.81;180 | SK101–SK137 (C41430893, also C49352235 and C2803348) | no row: **wrong**, 3.9 mm off and 180° | holes exact, pads 0.26 mm rms. 0° and 180° fit the two pads alike; at 180° the body's notch wraps the Ø4 switch post (outline 2.64 mm from its centre, 0.73 mm at 0°) |
  | `^worxboard:PinSocket_1x05_P2\.54mm_Vertical_H5\.0mm$` | 0;5.08;270 | J3 (C27985230, also the C46061764 fallback) | no row: **wrong**, 5.08 mm off | 5 of 5 pins; unchanged when J3 is turned 180° |
  | (no row) | 0;0;0 | 0402 R and C, D1 and D101–D137 (SOD-123), Y1 (C49304726), SW1, SW2, F1 | right | pads, pin 1 and cathode agree |

  For a B.Cu part kikit writes rotation 180 − θ + r and does not mirror the offset, so the
  bottom-side sockets take +3.81. SK101 then goes to (190.83, −63.20, B, 180°), the midpoint of its
  two pads. JLC does not document its bottom-side convention, so its placement preview of the bottom
  side stays the final check (`docs/ordering-jlcpcb.md`). An earlier review pass gave 0° for the
  sockets: it matched pads only, and pads alone cannot tell 0° from 180°.
- **Why ELEC does not change the CPL itself:** FAB owns `jlc_rotations.csv`. ELEC could set the same
  values per part through the `JLCPCB_CORRECTION` symbol field, which kikit prefers to the table,
  but that would make a second source of corrections that silently overrides the first. A stage D
  check that every CPL footprint has a row is also left out for now: it would turn the PCB stream's
  re-placement commit red over a file that stream does not own. Once FAB's rows are in, that check
  belongs in `netcmp.py --board`'s kikit mode: a row for every CPL footprint, or one of the no-row
  footprints above.

### ELEC-8. J3's pin-1 end is a gate in stages C and D; G3 re-checked (§4 G1, §7, §9 stages 12–13)

- **Problem** (verifier, 2026-11-03): G1 item 1 (J3 pin 1 at the wrong end, so a plugged-in
  nice!view gets SCK on GND and MOSI on CS) was only a strict xfail in `test_gates.py`, which push CI
  does not run: nothing stopped an order.
- **Change** (`netcmp.py --board`, run by stages C and D): `check_display()` reads
  J3's five pads from the board. It takes the module's direction as J3 to the case window centre
  (`layout.display`), turns the front view (header at the bottom; MOSI, SCK, VCC, GND, CS from left
  to right) to it, and fails unless pad *n* lies within 0.05 mm of module pin *n*. So `just
  pcb-finish` (and the CI `rebuild` jobs) and `just pcb-fab` (the CI `board` jobs) stop on a board
  whose J3 is the wrong way round. The check covers the turn, not the row position, so G1 item 2
  (the J3 row at y 39.925) stays open to PCB.
  - Checked: the committed boards and the CI-rebuilt boards of run 41548543572 fail with "J3 pad 1
    at (67.31, 40.60) meets the nice!view's pin 5 (CS); its pin 1 (MOSI) is at (77.47, 40.60).
    Turn J3 by 180 deg…" (left 182.53 / 192.69). The same rebuilt boards with only J3 turned (pin 1
    at x 192.69 left and 77.47 right, footprint at 270°) pass, also in the `kicad/kicad:10.0.7`
    container. A quarter turn fails ("meets no nice!view pin … Turn J3 by 90 deg"), and so does a J3
    without its pads.
  - End to end on a scratch clone, `just pcb-fab` passes on both turned boards: board, J3 and
    bom/pos sections, 119 parts, renders and the STEP checks. On the rebuilt right board as placed
    today it stops at this check.
  - `test_gates.py::test_g1_module_pins_land_on_their_nets` agrees: on the turned boards it XPASSes
    on both halves, and being strict it then fails `release.yml` until its marker goes (WS5 tests).
  - For PCB: in `place.py`, put J3's origin (pin 1) on `header_pins[-1]` at 270° (or reverse the
    order in `layout.display()`), then re-route the display nets.
- **G3 re-checked** with `stock.py --boards 5` on 2026-11-03 at 01:52 UTC: all 21 LCSC numbers pass, and
  library types are as in ELEC-6. Thinnest at JLC: C95562 5 743, C51118 6 111, C27985230 6 399 (THT),
  C2040 7 052. Fallbacks: C49352235 30 873, C9002 302 757 (basic), C46061764 4 487 (THT). Retired,
  unchanged: C2803348 0 (discontinued at both shops), C113767 163 ("no longer manufactured"), C91749
  19.
- **CI is still red**, for the reasons in ELEC-6, none of them in an ELEC path. Run 41563465072
  (c2845d6): the schematic job and the layout, firmware and case workflows pass. The `board` jobs
  stop at `just pcb-drc` with 4 parity errors per half. The left `rebuild` job is killed for memory
  in `checks.py` (exit 137, the `copper_graph()` bug of ELEC-5). The right `rebuild` job reaches DRC
  0 / 0 / 0 and passes `checks.py` and the board part check, then stops at this J3 check inside
  `pcb-finish`, where it used to stop at the comparison with the committed board. Its board is
  byte-identical to the rebuild of run 41548543572. The PCB commit list of ELEC-6 still applies,
  with two changes: item 1 (J3 turned) is now also required by stages C and D, and item 4 now covers
  all of FAB's rows (ELEC-7).
- **Acceptance** (this change): `just pcb-sch-all` gives ERC 0 and netcmp 10/10 on both halves, with
  the schematics and `pcb/lib` unchanged. `pytest tests/integration` gives 101 passed, 6 xfailed and
  4 failed, the same stale-board tests as in ELEC-6.

## BOARD: re-placed and re-routed boards for the turnkey order (`pcb/scripts/`, `pcb/left`, `pcb/right`, `layout/display.py`, `tools/images.lock`)

Both halves were re-placed and re-routed from scratch on 2026-11-03 from the ELEC schematics (ELEC-1
to ELEC-3: C41430893 sockets, C97521 flash, C49304726 crystal, U4 pin 5 on VSYS, J3 as the fitted
5.0 mm C27985230 socket). The schematics and `pcb/lib` are unchanged.

### BOARD-1. J3 turned 180° and moved onto the module's header row (§4 G1 items 1 and 2)

- **Source:** the nice!view pinout and dimension drawings (nicekeyboards.com, re-read 2026-11-03).
  The front view (LCD side, flex at the top, header at the bottom) reads MOSI, SCK, VCC, GND, CS from
  left to right; the header row is 1.3 mm in from the module's short edge, its pins centred across
  the 14 mm width (1.92 + 4 × 2.54 + 1.92).
- **Derivation:** on both halves the module lies LCD up with its header at the back (low y): the
  front view turned 180°, so MOSI (J3 pin 1, design.py pin n = module pin n) is at **high x** in each
  half's own frame. The module spans y 38.625–74.625 (`layout.display.MODULE_RECT`), so its header
  row is at 38.625 + 1.3 = **39.925**.
- **Change:**
  - `layout/display.py`: `HEADER` is derived from the module rectangle (y 39.925, was 40.6), and
    `header_pins()` lists the pins in pin order, pin 1 first at high x; `layout.display()` keeps
    that order on both halves. The window follows the header: centre y 55.865 (was 56.54).
  - `place.py`: J3's origin (pin 1) on `header_pins[0]` at 270°, so its pins run toward −x.
  - `layout/tests/test_layout.py`: the header position and "pin 1 at high x on both halves".
- **Result:** J3 pad 1 (`DISP_MOSI`) at (77.47, 39.925) on the right and (192.69, 39.925) on the left,
  pads 2–5 at −2.54 mm steps: SCK, 3V3, GND, CS. The stage C/D gate of ELEC-8 (`netcmp.py --board`)
  passes on both. A module plugged in spans y 38.625–74.825 with the V-cut, inside the pocket
  (38.125–75.125). `just model` and `just fitcheck` pass with today's case (`plates/` unchanged).
- **Consumers:** CASE (window and pocket follow `layout.json`; the display stack of ELEC-3 is
  unchanged), DOCS (`site/gen_docs.py` now gets pin 1 at high x from `header_pins`, but its J3 prose
  still says low x; `verification.md` G1 items 1 and 2 are done), WS5 tests
  (`test_g1_module_pins_land_on_their_nets` and `test_g1_module_fits_the_pocket` now XPASS on both
  halves, so their strict markers must go or `release.yml` fails).

### BOARD-2. The completion router no longer depends on the host (§9 stages 10–11)

- **Problem** (review fixes, `verification.md`): `complete_routes.Index.dilated` cached dilated copper
  under `id()` of the item. Once a rip-up freed an item, Python handed its id to new copper, which then
  got the old item's shape (over 6 000 such hits in one left rebuild): the router saw ripped copper
  where none was and missed new copper. Which ids come back depends on the allocator, so the left
  board differed between this host and the CI runners, and the committed left board was the CI build.
- **Change:** the cache key holds the item itself. `Item` is `eq=False`, so it hashes by identity, and
  the cache keeps every keyed item alive for the life of the index: no id can be reused under it.
- **Left GND island:** the review expected this fix to leave the left U1-area GND pour island open (3
  DRC unconnected items with the old placement and seed 0x2). With the new placement the plain
  completion and the transactional rip-up close every gap, GND included, so no routing or pour rule
  changed. As WS2c-4 prescribes for a placement change, the left base seed was re-chosen: of 0x2, 0x3,
  0x4 and 0x5 (all with this placement), 0x3 closed every gap first, in 9.3 min of `pcb-finish`; 0x2
  was still negotiating after 27 min and 0x4 and 0x5 after 11 min, when they were stopped. The right
  keeps 0x1 (0 open, 3.8 min).
- **Check:** repeated from-scratch runs in separate clones gave byte-identical Freerouting sessions
  and boards, and on the CI runners (run 41577492203, bf7a642) both `rebuild` jobs built boards equal
  to the committed ones, the left included (23 min left, 20 min right).

### BOARD-3. The boards are seeded from the layout data they are built from (§9 stage 7; amends WS2c-4)

- **Problem:** `place.py` seeded the KIIDs with the bytes of the whole `layout.json`, so a change only
  the case reads (a jack body, the display pocket or window) re-seeded the board, re-routed it and made
  the committed boards stale.
- **Change:** `place.layout_seed()` hashes only what the board uses: the keys, holes, outline, zones
  and the J3 pins. The jack bodies and the display rectangles can change without touching the boards.

### BOARD-4. Dangling copper is cleaned up after routing (§9 stage 11)

- **Problem:** the rip-up of `complete_routes.negotiate()` left unlocked stubs, and Freerouting runs
  some segments past the point where the rest of their net joins them: about 90 (left) and 70 (right)
  `track_dangling` / `via_dangling` DRC warnings on the old boards, copper that carries no current.
- **Change:** `pcb/scripts/prune.py`, run by `stage_c.sh` after the DRC gate, then the gate again.
  Each round runs the DRC and, for every unlocked item it names: deletes it if its net keeps its
  island count without it (then whatever that leaves loose); else cuts a track with one loose end back
  to the last point where copper of its net joins it; else replaces a via that joins copper on one
  layer only by short tracks on that layer inside its own pad. Every change is checked against the
  net's island count (the completion router's copper model) and the pours are refilled per round.
  It is seeded like the other stages, so the result is reproducible.
- **Result:** left 61 deleted, 6 trimmed, 2 vias replaced; right 121 deleted, 8 trimmed, 4 replaced.
  What KiCad still flags is locked copper from `route_critical.py`: the column vias at the keys, where
  the column line and the socket link both run on B.Cu (WS2b-3), two column fan-out vias at U1, and a
  few U1 fan-out stubs the router joined mid-stub (left 33 items, right 37). Plus, on the right, 2
  unlocked items that carry a junction (a COL1 segment and a VBUS_SENSE via). DRC stays at 0
  violations and 0 unconnected throughout.

### BOARD-5. U4's VSYS reference has its own 10 µF at the pin (§6.3; ELEC-2)

- **Problem** (ELEC-2, ELEC-5): with U4 pin 5 on VSYS, the nearest VSYS copper was 11–20 mm away
  (D1, C1, C2, JP1); the CI rebuild of b077f78 reached VSYS over 17.6 mm of track. ST asks for a short
  connection from the clamp reference to its rail.
- **Change:** C2, one of the two 10 µF VSYS caps, moves from beside C1 to U4: `place.py` puts it in
  U4's frame across the D+ row from the pin-5 via (`U4_CAP_Y`), pad 1 toward U4, and
  `route_critical.u4_cap()` lays locked copper pin 5 → via → B.Cu → via → C2 pad 1, and C2 pad 2 →
  GND via. C1 stays at D1 and U3's input (the AP2112K needs 1 µF there). VSYS keeps its 2 × 10 µF.
- **Check:** `checks.py` measures the copper path from U4 pin 5 to a VSYS cap (≤ `U4_CAP_MAX_MM`,
  5.0): 4.07 mm on both halves. C2 sits at (179.79, 36.00, 90°) on the right and (74.41, 44.39,
  241.46° in the CPL) on the left.
- **Consumers:** FAB (C2 is an 0402 like before: no correction row), DOCS (`electrical.md` still
  groups C1/C2 at D1).

### BOARD-6. `checks.py` cannot loop on a zero-length edge (§9 stage 12; ELEC-5)

- `copper_graph()` clamps each edge weight to `max(0.0, w)`. `project()` on a segment end gave
  −3e-17, a negative cycle that `dijkstra()` never left: the left CI rebuild was killed for memory
  (exit 137). `checks.py` now runs in about 1 s on both halves.

### BOARD-7. JLC fabrication and assembly rules (§9 stage 13)

JLC figures as in `verification.md` G3 (JLCPCB PCB capabilities page).

| Rule | JLC | Left | Right |
|---|---|---|---|
| Track | ≥ 0.10 | rule 0.127; narrowest 0.135 (2 segments), signals 0.15–0.18 | rule 0.127; narrowest 0.135 (3 segments) |
| Clearance | ≥ 0.10 | rule 0.127, netclasses 0.2 | same |
| Vias | ≥ 0.15 drill / 0.25 pad; no fee at 0.3 drill | 321, all 0.3 / 0.6 | 341, all 0.3 / 0.6 |
| Via in an SMD pad | flagged by JLC DFM | none (`checks.py`; the U1 exposed-pad thermal array excepted) | none |
| Copper to a routed edge | ≥ 0.2 | 0.5 rule | 0.5 rule |

- **Component bodies near the edge.** JLC's assembly terms want bodies ≥ 2.5 mm from the board edge
  unless the board gets rails. Courtyards closer than that (mm):
  - right: J1 and J2 past the edge by design (USB-C and TRRS mouths), SK132 touching, SK134 and SK135
    1.10, U2 1.50, C5 1.70, R8 and R9 1.88, SK133 2.01;
  - left: J1 and J2 past the edge, Y1 0.40, SK132 0.83, C7 1.09, C6 1.49, SK133 2.01, R7 2.07, C17
    2.09, SK134 and SK135 2.34.

  J1, J2 and the thumb sockets cannot move (the connector mouths are the case notches, the sockets
  sit under their switches), so placement cannot meet a 2.5 mm rule and the order needs **assembly
  rails attached with a routed gap and mouse-bites, no V-cut, and no tab in front of J1 (back edge,
  y 30.6, x 181.5–190.5 right / 69.5–78.5 left) or J2 (bump edge, y 99.95–106.05, x 49.0 right /
  211.0 left)**. That holds for the parts that could move too (U2, C5, R8, R9; Y1 cannot without
  breaking its 3 mm rule), so they stay. The rails, fiducials and tooling holes are PACKAGE's panel.
- **Silkscreen:** about 185 `silk_over_copper` and 5 `silk_edge_clearance` warnings per half (library
  outlines over pads, J1/J2 outlines over the edge); JLC clips silk off pads and the edge.

### BOARD-8. Result

| Check | Left | Right |
|---|---|---|
| `just pcb-sch-all` | ERC 0, netcmp 10/10 | ERC 0, netcmp 10/10 |
| Freerouting 2.5.0 (30 passes), open after | 25 connections, 6.9 min | 40 connections, 11.3 min |
| `just pcb-finish` (completion, rip-up, pours, clean-up, gates) | 8.1 min | 3.8 min |
| DRC `--schematic-parity --severity-error` | 0 violations, 0 unconnected, 0 parity | same |
| `checks.py` | 8/8: USB D+ 24.73, D− 23.92, skew 0.81 mm; Y1 2.93 mm; worst supply pin 11.64 mm (IOVDD 22) | 8/8: USB 23.75 / 23.50, skew 0.25 mm; Y1 2.93 mm; IOVDD 22 11.64 mm |
| `netcmp.py --board` + kikit BOM/CPL (stage D) | 3/3, 119 fitted parts | 3/3, 119 fitted parts |
| `just model && just fitcheck` with both STEPs | 90 bodies, 0 mm³ | 90 bodies, 0 mm³ |

- CI on bf7a642: `layout`, `firmware`, `case` and `pcb` (schematics, both `board` jobs with the
  renders current, `fit`, both `rebuild` jobs) all pass, run 41577492203 for `pcb`.
- `pytest layout`: 32 passed. `pytest tests/integration` (no firmware build): 80 passed, 25 skipped,
  2 xfailed (G2), and 4 strict XPASSes, the G1 tests of BOARD-1. The stale-board tests of ELEC-6
  (`test_netlist_equals_committed_board`, `test_committed_board_orders_the_design_parts`) pass.
- **Decoupling, unchanged:** IOVDD 10, 22, 33 and VREG_VOUT 45 still reach their caps through the
  joins inside the pad ring (REVIEW-FIX-2, worst 11.64 mm). Shortening them needs caps on B.Cu under
  U1, fed by vias in the ring, which would cut the B.Cu GND pour under the exposed pad and the column
  crossings there: a rev B change.
- `tools/images.lock` now records the `kicad/kicad:10.0.7-full` digest (WS2c-2).

### BOARD-9. U1's exposed pad joins the main B.Cu GND plane through a locked spoke to the board edge (§6.4, §9 stages 8 and 12; corrects BOARD-2)

- **Problem** (post-BOARD review of 4e5fc30): on the left board, U1's exposed pad (pad 57, the
  RP2040's only GND pin) sat on a 57.7 mm² B.Cu GND island. That island reached the rest of GND through
  one unlocked completion via at (89.0, 43.8), an 18.7 mm² F.Cu island and the vias at
  (85.35 / 83.85, 43.64): with that via deleted, DRC reports 1 unconnected item. Most left cap GND vias
  sat in small B.Cu islands (C10/C13–C15 in 3.7 mm², C11/C18 in 9.4, C16/C19 in 21.5, C8/C9 in 35.1).
  **BOARD-2's statement that the left GND island did not reappear was wrong.** DRC's 0 unconnected
  hid a join through a single via, and seed 0x3 was kept only because its router happened to close the
  gap. The right half had the pad and 7 of the 12 U1 cap GND vias in its main plane, by the same luck.
- **Cause:** B.Cu routes under and around U1 can ring the pad's B.Cu copper off from the plane. On the
  left, U1 is turned 180° (WS2b), so its cap side faces U2 and the matrix, where the fan-out runs. On
  the right, that side faces the back edge.
- **Change** (`route_critical.py`, `EP_LINK`): a locked 0.5 mm B.Cu GND spoke runs from the pad's via
  array to the board edge, on the side of U1 that faces the back edge, where no fan-out runs. It stops
  0.05 mm short of the copper-to-edge clearance, or of a keepout whose fill reaches the edge, so no
  route can pass between:
  - **right** (`ep_north`): from the north-east EP via, up under the 3V3 north exit (U1 frame x 0.6),
    into a B.Cu row through the north caps' GND vias (C14/C15/C13/C10, with C16/C19 on its west end),
    then on from C19's via to the back edge (y 31.35). The east caps' GND vias (C18/C11/C12) are joined
    in a row and fed into the GND fill under the USB pair (`USB_KEEPOUT`, fills allowed), which meets
    the spoke at the keepout's west end. 22.2 mm of locked copper.
  - **left** (`ep_south`): from the south-west EP via, down under XIN into the GND fill under Y1
    (`Y1_KEEPOUT`), which reaches the back edge. 5.4 mm.

  Freerouting and the completion router treat the spoke as fixed copper, so it is in place before any
  route.
- **Gate** (`checks.py`, run by stage C and by the CI `board` and `rebuild` jobs): every thermal via
  of the exposed pad must lie in the main B.Cu GND plane (the largest filled B.Cu GND area), and so
  must the GND via of every cap the spoke joins (`GND_LINKED_CAPS`: right C10, C11–C16, C18, C19;
  left none). "Lie in" means joined to the plane over B.Cu alone, with no hop through an F.Cu island.
  The other caps are listed. On 4e5fc30 the gate fails both halves: the left on its EP vias (0 of 9),
  the right on C11, C12 and C18.
- **Tried and dropped** (same placement, base seeds 0x1–0x4; one round is 20–80 min per half):
  - Spokes from the pad to every cap group (north, east, west) on both halves. The left never
    completed (COL4 open). The right lost QSPI_SD0 with the west spoke in place, and on
    another round its whole spoked cluster was ringed off (0/9 EP vias in the plane). A spoke that stops
    short of the edge only moves the ring outward.
  - North and south spokes together. Then no route can cross under U1, which the columns and 1V1 need
    (COL2–COL6 leave the south-east fan for the west; 1V1 runs from the north moat to pin 23). The left
    left 3 to 7 nets open.
  - On the left, also joining the north and east cap rows into the USB GND strip (short links). ROW5
    stayed open, and the caps still did not reach the plane (2/12).
  - A post-route pass that lays a B.Cu GND track from each walled-off island into the plane, ripping
    and rerouting the nets in its way (the `complete_routes` rip-up machinery). The rerouted nets ring
    the island again one step further out. It did not converge on the left (1/12 caps) and was dropped.
- **Result:** both halves route to 0 unconnected with their old base seeds (left 0x3, right 0x1). The
  boards are rebuilt from scratch, and the DSNs and boards are byte-identical between runs.
  - left: all 9 EP vias are in the main B.Cu plane (14 717 mm²); none of the 12 cap GND vias is.
  - right: EP plus 11 of 12 caps are in the main plane (14 669 mm²). C17 (DVDD 23) is not (30.4 mm²).
- **Open, left caps:** the left's U1 cap GND vias still land in small B.Cu islands: C10/C13–C16/C19
  in one of 60.9 mm² (9 vias to F.Cu islands), C8/C9 50.4, C11/C18 24.0, C12 23.1, C17 1.0. Every
  island is joined to GND (DRC 0 unconnected), but the cap-to-pad return is long. On this placement any B.Cu
  link from those vias to the pad or the plane walls in the fan-out the left's completion needs (see
  above). Fixing it is a placement change for rev B: put the left cap rows on U1's back-edge side, or
  stop turning the left U1.

### BOARD-10. G2 (TRRS body length) is not landed: it needs CASE's relief cut in the same commit (§4 G2)

- **Layout half, ready:** `layout/jacks.py` `TRRS_BODY = (14.1, 6.1)` and `TRRS_HEIGHT = 5.0` (HRO
  drawing: 2.00 barrel + 12.10 body, 6.10 wide, 5.00 tall). `layout/tests/test_layout.py`
  `test_j2_inside_z_trrs` becomes "J2 is the drawing size, inside the PCB, its last 0.9 mm past Z_TRRS
  (x 62.2) and ≥ 3.5 mm from every switch housing". The real body is 3.57 mm from C6R1's housing and
  3.93 mm from C6R2's. Then `layout.json`/`layout.svg` are regenerated. `pytest layout` passes with it
  (32). The boards do not change: `place.layout_seed()` leaves the jack bodies out (BOARD-3), and the
  footprint is unchanged.
- **Why not landed:** with it, `just model` stops at `jack_check`: "J2 body is not under the relief
  pocket". `relief_poly()` is `Z_BACK ∪ Z_TRRS` minus the key well plus 1 mm of well skin, so it ends at
  x 61.27. The body runs to 63.1, under the plate between the C6R1 and C6R2 cut-outs (plate bottom
  Z 12.1 = PCB + 3.5, plate top 13.6 = PCB + 5.0). The `case` and `pcb` `fit` workflows would go red,
  and `case/` is CASE's.
- **What CASE needs to cut** (one commit with the layout half): relieve the jack body plus clearance,
  x 49.0–63.6 (right frame) by y 99.45–106.55, through the spacer and up to at least PCB + 5.3 in the
  top part. Over x 61.3–63.6 that means through the 1.0 mm well skin and the plate, because the jack
  top is flush with the plate top. `check_fit` reads the new envelope (`PART_H["J2"]` = 5.0) from the
  layout itself. No case change was made or tried here, so whether those cuts pass `jack_check` and
  `check_fit` is unverified.
- **Integration tests:** `tests/integration/test_gates.py::test_g2_layout_body_holds_the_jack` is a
  strict xfail. It XPASSes once the layout half lands, so its marker must go in that commit.

### BOARD-11. Result after BOARD-9 (supersedes the BOARD-8 numbers)

| Check | Left | Right |
|---|---|---|
| `just pcb-sch-all` | ERC 0, netcmp 10/10 | ERC 0, netcmp 10/10 |
| Freerouting 2.5.0 (30 passes), open after | 30 connections, 7.8 min | 36 connections, 11.2 min |
| `just pcb-finish` (completion, rip-up, pours, clean-up, gates) | 13.4 min | 5.4 min |
| DRC `--schematic-parity --severity-error` | 0 violations, 0 unconnected, 0 parity | same |
| `checks.py` | 9/9: USB D+ 24.73, D− 23.92, skew 0.81 mm; Y1 2.93 mm; worst supply pin 11.64 mm (IOVDD 22); U1 GND: EP 9/9 in the plane | 9/9: USB 23.75 / 23.50, skew 0.25 mm; Y1 2.93 mm; IOVDD 22 11.53 mm; U1 GND: EP 9/9, caps 11/12 (C17 out) |
| `netcmp.py --board` + kikit BOM/CPL (stage D) | 3/3, 119 fitted parts | 3/3, 119 fitted parts |
| Copper | 2417 tracks, 320 vias (all 0.3 / 0.6), narrowest 0.135 (2 segments) | 2874 tracks, 369 vias (0.3 / 0.6), narrowest 0.135 (6) |
| Dangling copper (`prune.py`), left by locked copper | 97 deleted, 5 trimmed, 2 vias replaced; 30 via / 6 track warnings | 150, 9, 5; 35 / 6 |

- `pytest layout`: 32 passed. `pytest tests/integration` (no firmware build): 109 passed, 2 xfailed
  (G2, BOARD-10).
- The JLC rules and edge distances of BOARD-7 are unchanged (same placement; the right's edge spoke
  keeps the 0.5 mm copper-to-edge rule, and DRC checks it).

### BOARD-12. The committed renders are compared pixel by pixel, not byte by byte (§9 stage 14; pcb workflow)

- **Problem:** on d640d7c the `board` job for the left failed at "Committed renders are current".
  The CI render of `pcb-left-top.png` was 117 331 bytes against 117 328 committed. KiCad 10.0.7's 3D
  raytracer is not bit-exact: rendered six times on one host, the left top view differs from run to
  run in 0 to 4 of its 1.6 million pixels, by 1 or 2 levels. Pinning the container to one CPU
  (`--cpuset-cpus=0`) does not change that. The right views and the left bottom view came out
  identical each time, which is why the byte check held on earlier boards.
- **Change:** `just pcb-render-check <side>` (`pcb/scripts/render_check.py`, run by the CI `board`
  job after `pcb-fab`) takes the committed PNGs from HEAD. It requires the same size and at most 64
  pixels differing by at most 8 levels per view. A changed board moves thousands of pixels.
  `docs/images/pcb-*.png` are still regenerated and committed with every board change.

### BOARD-13. G2 landed: the PJ-320D envelope is the drawing size and the case relieves it (§4 G2; supersedes BOARD-10)

- **Layout** (`layout/jacks.py`): `TRRS_BODY = (14.1, 6.1)`, `TRRS_HEIGHT = 5.0` (HRO drawing, LCSC
  C95562: 2.00 barrel + 12.10 body, 6.10 wide, 5.00 tall; was 12.0 × 6.0 × 5.5). J2's body now runs
  x 49.0–63.1 by y 99.95–106.05 (right frame; left 196.9–211.0), 0.9 mm past Z_TRRS (x 62.2), 3.57 mm
  from the C6R1 switch housing. `layout.json` and `layout.svg` are regenerated; only the two J2 entries
  change. The boards do not: `place.layout_seed()` leaves the jack bodies out (BOARD-3).
- **Case cut** (`case/worxboard_case.py`, the one CASE-owned change, made here so G2 lands in one green
  commit): `jack_relief_poly(side)` is J2's body + `J2_RELIEF_CLEAR` (0.5 mm, mitred), its corners
  rounded to `TOOL_R` (1.0): x 48.5–63.6 by y 99.45–106.55 right frame (left x 196.4–211.5), the
  0.5 mm clearance kept at the body corners too (0.29 mm on the diagonal). It is cut:
  - in the **top part**, as part of `relief_poly()` (prism Z 12.09–14.6, `Z_PLATE_BOT` to
    `Z_POCKET_CEIL`, i.e. up to PCB + 6.0): through the 1.0 mm well skin and the plate between the
    C6R1 and C6R2 cut-outs over x 61.3–63.6. Over the well (x ≥ 62.27) the plate is gone and the well
    is open above it; over the skin, 3.0 mm of skin stays above Z 14.6 as a bridge. The jack top is at
    Z 13.6, flush with the plate top, 1.0 mm under the pocket ceiling (`jack_check` headroom);
  - in the **spacer** (`spacer_face()`), which already stops 0.5 mm short of Z_TRRS; `spacer_check()`
    now also fails if the spacer overlaps J2's body;
  - in the **plate face** (`plate_face()`), so the stand-alone FR4 / aluminium plate DXF
    (`plates/worxboard-plate-{left,right}.dxf`, regenerated) has the same notch as the milled plate.
  The plate keeps ≥ 3 mm between the notch and the C6R1 / C6R2 switch cut-outs.
- **Checks:** `just model` passes (`jack_check`: J2 body under the relief, 1.0 mm headroom; spacer,
  mirror and web checks), `just fitcheck` 0 mm³ both against the layout envelopes alone (the `case`
  workflow) and against the PCB STEPs + the layout J2 envelope (the `pcb` `fit` job). Before this
  change the real body hit the top part with 16.8 mm³ and the spacer with 7.3 mm³ per half
  (`verification.md` G2). `pytest layout`: `test_j2_inside_z_trrs` becomes
  `test_j2_is_the_drawing_size_past_z_trrs` (drawing size, inside the PCB, exactly 0.9 mm past Z_TRRS,
  ≥ 3.5 mm from every switch housing).
- **Integration tests** (`tests/integration/test_gates.py`): the strict xfail on
  `test_g2_layout_body_holds_the_jack` is removed (it passes now), and
  `test_g2_jack_height_and_axis` checks the part height against the spec limit and the layout height
  against the part (5.0 ≥ 5.0) instead of requiring the layout to carry the 5.5 mm spec limit.
  `pytest tests/integration`: all pass, no xfails left.
- **Consumers:** CASE builds on `jack_relief_poly()` and must keep it (or an equivalent cut) in the
  top part, spacer and plate. DOCS: `verification.md` G2 (summary row, the Length and Height rows, open
  item 4) and `docs/case.md` (the relief and plate rows) still describe the old envelope and the failure.
  `case/renders/*.png` are regenerated.

### BOARD-14. Every U1 cap's GND reaches the exposed pad within 13 mm; TESTEN ties the pad to the plane; no unlocked dangling copper (§6.4, §9 stages 8, 11, 12; supersedes the BOARD-9 left spoke and gate, corrects BOARD-11)

- **Problem** (verifier on 68f812e, a 0.1 mm raster of all GND copper of both layers, 1.6 mm per via
  hop):
  - **Left:** the GND return of 11 of the 12 U1 caps to U1's exposed pad (EP, the RP2040's only GND
    pin) was 125.7–179.9 mm of copper. The straight-line distances are 6–9 mm. Only C17 was short
    (29.5 mm). C19, the internal regulator's output cap, was at 135.5 mm. The BOARD-9 gate passed only
    because its left cap list was empty, and BOARD-9 deferred the caps to rev B.
  - **Right:** 9–12 mm, C17 22.9 mm.
  - **Right, dangling copper:** prune.py left 5 unlocked items. Three were vias that join F.Cu only
    (3V3 (148.176, 46.358), DISP_DC (83.92, 42.848), ROW1 (160.108, 47.0)). One was a ROW2 B.Cu jog
    (160.765, 58.0)–(160.665, 57.9). One was a TP5 B.Cu overhang (170.376, 52.064)–(170.376, 47.192).
    **BOARD-11 said every remaining dangling warning came from locked copper. That was wrong for the
    right half** (the left had 0 unlocked items).
- **Cause, left:** the left U1 is turned 180°, so its cap rows face U2 and the matrix, where the
  fan-out runs. Three walls box in the region west of U1 (TP4–TP11, SWD, RUN, the COL4–COL6 fan-out
  vias):
  - the USB pair from R3/R4 to J1, with its B.Cu keepout;
  - the B.Cu spoke from the EP under XIN to the GND fill under Y1, which reaches the back edge
    (BOARD-9), walling off every B.Cu route under U1's south side;
  - any B.Cu link from the EP to the north caps' GND vias, which walls off the B.Cu passage under U1's
    north side, between the EP and the pair's keepout.

  With the spoke and the cap links both in place, that region's only B.Cu ways out are the gaps in the
  pair's keepout at R3/R4 and at U4, and the completion router never closed its nets.
- **Change** (`route_critical.py`):
  - **`testen_via()`, both halves.** TESTEN (U1 pin 19) is GND, and `qfn_inner` already joins its pad
    to the EP on F.Cu. A locked 0.2 mm F.Cu track now runs on out of that pad, between pin 18's
    fan-out and XIN (0.225 mm clear of both on the 0.4 mm pitch), past pin 18's bend. It ends at a
    locked 0.3/0.6 GND via just short of the Y1 keepout, at U1 frame (−1.195, 5.96). The keepout's
    GND fill reaches the back edge.
    - This ties the EP to the plane at the back edge without walling off a B.Cu route.
    - On the left it replaces the B.Cu spoke under XIN; `EP_LINK` and `ep_south()` are gone.
    - The right keeps its B.Cu spine from the EP to the back edge (`EDGE_SPOKE`).
  - **`ep_caps()`, both halves (was `ep_north()`, right only).** Locked 0.5 mm B.Cu spurs run from
    the EP's vias to every U1 cap's GND via. Each one ends at a cap or in a fill:
    - the spine and the north row (C14/C15/C13/C10, with C16/C19);
    - the east row (C18/C11/C12), stubbed into the USB pair's GND fill, which meets the spine. On the
      left it is stubbed into the keepout piece under the pair's first run;
    - a diagonal from the EP's north-west via to the C8/C9 via (new);
    - C17's via, stubbed into the Y1 fill, which the TESTEN via joins (new).
  - **Left base seed 0x4** (was 0x3), re-chosen per WS2c-4 because the locked copper changed. With
    this copper, 0x4 closed every gap in 10 min of stage C. 0x2, 0x3, 0x5, 0x6 and 0x7 were still
    negotiating (3–15 nets open) after 14–44 min and were stopped. The right keeps 0x1.
- **Tried and dropped, left** (each one placed, Freerouted and finished from scratch):
  - **No B.Cu edge link** (seeds 0x2 and 0x3, with and without the east row).
  - **The spoke moved west of COL0's fan-out via** (seeds 0x2–0x4). It had to clear that via by
    0.2 mm. On 68f812e the plain spoke trapped COL0, which then ringed the EP's B.Cu: that ring was
    the left GND island.

  Both were still negotiating after about 40 min, with 3–7 nets open. Before this round, the
  duplicate BOARD agent ran 6 variants with the old spoke and the north and east links; they never
  closed TP4–TP7, RUN, SWD, COL2–COL6 and QSPI_SD1. On the right, the TESTEN via and C17 stub without
  the C8/C9 diagonal let the reroute cut C8/C9 off (39 mm). With the diagonal, every cap is ≤ 13 mm.
- **Gate** (`checks.py`, replacing the BOARD-9 gate). The raster is 0.1 mm over the GND copper of both
  layers (pour fill, tracks, vias, pads) within ±16 mm of U1, with 1.6 mm charged per layer change:
  - each U1 cap's GND pad reaches the EP within 20 mm (`GND_RET_MAX_MM`);
  - the EP reaches the main B.Cu GND plane within 8 mm (`EP_PLANE_MAX_MM`).

  Which EP and cap GND vias sit in the main plane over B.Cu alone is now printed, not gated. On the
  left, the EP's B.Cu (148 mm²: the EP vias, the spine and the cap rows) reaches the plane through the
  TESTEN via over F.Cu, which is 5.7 mm. A path that would leave the window counts as failed, so
  every figure is an upper bound on the whole-board value. **ORDER-4:** that via, behind a 0.15 mm
  track, was the left domain's only link to the planes; this gate could not see it.
- **Dangling copper** (`prune.py`): three more repairs, each kept only if its net keeps its island
  count.
  - A one-layer via is replaced by joins that may pass the copper they replace by 1e-3 mm. A join
    that would poke out is narrowed, to 0.15 mm at the least.
  - An overhang is trimmed as KiCad's own test judges it: the end is joined once other copper of
    the net lies within the track's half width.
  - A track whose end meets another unlocked track part-way along is split there (a T junction).

  `MAX_ROUNDS` is 30; a chain of stubs goes a few items per round. prune.py now exits 1 if any
  **unlocked** item still dangles, so stage C fails on it. What KiCad still flags is locked copper
  only, as listed in BOARD-4.
- **Commits:** 0d361b7 lands `prune.py` with the right board it gives. A from-scratch rebuild of the
  left with it gives the committed left board unchanged. 3b9209c lands the U1 GND change, the seed
  and the gate with both boards.
- **CI:** on both commits every job of `layout`, `firmware`, `case` and `pcb` passes, including the
  render compare, the fit check against both STEPs and both from-scratch `rebuild` jobs (`pcb` runs
  41746645589 and 41746675999). On 3b9209c the rebuilds took 26 min (left) and 35 min (right).
- **Result** (both boards rebuilt from scratch with the committed scripts, twice each: the
  experiment and a fresh clone gave byte-identical sessions and boards):

| Check | Left | Right |
|---|---|---|
| `just pcb-sch-all` | ERC 0, netcmp 10/10 | ERC 0, netcmp 10/10 |
| Freerouting 2.5.0 (30 passes), open after | 30 connections, 6.8 min | 36 connections, 11.3 min |
| `just pcb-finish` (completion, rip-up, pours, clean-up, gates) | 10.2 min | 15.3 min (host loaded) |
| DRC `--schematic-parity --severity-error` | 0 violations, 0 unconnected, 0 parity | same |
| `checks.py` | 10/10: USB D+ 24.73, D− 23.92, skew 0.81 mm; Y1 2.93 mm; worst supply pin 11.64 mm (IOVDD 22); U4 VSYS 4.07 mm | 10/10: USB 23.75 / 23.50, skew 0.25 mm; Y1 2.93 mm; IOVDD 22 11.64 mm; U4 VSYS 4.07 mm |
| EP → main B.Cu GND plane | 5.7 mm (TESTEN via) | 1.6 mm (EP vias in the plane) |
| U1 cap GND → EP, mm | C8 9.3, C9 9.5, C10 10.9, C11 11.0, C12 12.5, C13 10.4, C14 9.4, C15 9.9, C16 11.4, C17 13.0, C18 10.5, C19 10.3 | C8 9.3, C9 9.6, C10 11.0, C11 9.1, C12 10.6, C13 10.5, C14 9.5, C15 10.0, C16 11.0, C17 13.0, C18 8.6, C19 10.3 |
| EP / cap GND vias in the main plane over B.Cu alone (printed) | 0/9, 1/12 (C17) | 9/9, 11/12 (all but C17) |
| `netcmp.py --board` + kikit BOM/CPL (stage D) | 3/3, 119 fitted parts, J3 pin 1 gate | same |
| Copper | 2620 tracks (498 locked), 331 vias (all 0.3 / 0.6), narrowest 0.135 (2 segments) | 3160 tracks (501 locked), 389 vias (0.3 / 0.6), narrowest 0.135 (3) |
| Dangling copper (`prune.py`) | 92 deleted, 9 trimmed, 4 vias replaced; 0 unlocked left; locked: 29 via / 5 track warnings | 176, 20, 11; 0 unlocked; locked: 34 via / 3 track |

- `pytest layout`: 32 passed. `pytest tests/integration` (no firmware build): 111 passed.
- The placement, parts and outline are unchanged, so BOARD-7 still holds: the JLC rules, the edge
  distances and the rails with a routed gap and mouse-bites. The TESTEN via is an ordinary 0.3/0.6
  via outside any pad, and its track is 0.2 mm.
- **Consumers:**
  - **FAB:** BOM and CPL are unchanged: same parts, positions and rotations.
  - **DOCS:** `verification.md` and `electrical.md` should describe U1's GND as above. The
    `verification.md` note on dangling stubs (about 90 / 70 warnings) is out of date.
  - **PACKAGE:** the outline is unchanged, and the renders are regenerated.

## CASE: the orderable case (`case/`, `plates/`, `.github/workflows/case.yml`)

The case was made orderable at JLCCNC (machined parts) and JLC3DP (printed parts) on 2026-11-04, case
revision **A1**. The order package is committed in [`case/production/`](../case/production/README.md).

### CASE-1. The display pocket rises over the stock nice!view stack under a raised bezel (§4 G1, §10.4; ELEC-3; supersedes the pocket height of WS3-5)

- **Spec:** pocket over the module + 0.5 mm from Z 8.6 to Z 16.8, so socket + module + glass ≤ 8.2 mm
  above the PCB top; a 0.8 mm skin and the window in the top face (Z 17.6).
- **Problem:** ELEC-3 made J3 the 5.0 mm socket JLC fits (C27985230), with a stock nice!view on its
  own male header. The glass top is then 8.9 mm above the PCB top nominally, 9.4 mm with a 2.5 mm
  header carrier and **9.75 mm at full tolerance: Z 18.35, above the top face**.
- **Change** (`case/worxboard_case.py`):
  - `Z_DISPLAY_TOP` = PCB top + 9.75 + 0.25 = **Z 18.6** (`DISPLAY_STACK_MAX`, `DISPLAY_GLASS_CLEAR`).
    It is now a case constant; the case no longer reads `layout.display.Z_POCKET_TOP` (16.8).
  - **Raised bezel B1**: the pocket + 2.0 mm (`BEZEL_WALL`), Z 17.6–**19.6** (1.0 mm skin,
    `BEZEL_SKIN`), R2 plan corners, 0.5 × 45° top edges. Where the key well is nearer, the bezel
    edge is pulled back to it and meets it flush (`bezel_rect`): in front at the C6R1 well
    (y 74.023; the pocket's front strip lies in that well, as in WS3-5) and at the C5 column
    (x 81.315 right frame, 178.685 left), where the wall between pocket and well is 1.425 mm thick
    and stands 6.0 mm above the key-well floor. Right frame x 62.89–81.315, y 36.125–74.023.
  - The window W1 (12 × 26, unchanged in plan) goes through the bezel skin, chamfer at Z 19.6.
  - The pocket is 11.6 mm deep from the parting face. JLCCNC's CNC Machining Design Guideline asks
    for R = H/10 + 0.5 (a tool of Ø H/5), and its tool table gives the Ø2 tool at most 10 mm of
    reach and the Ø3 tool a Min R of 2, so the pocket's corners need **R2**. A plain R2 corner would
    hit the module's corners, which stand 0.5 mm from both walls (√2 × (2 − 0.5) = 2.12 > 2).
    `pocket_cut()` relieves the two back (header-end) corners with R2 dog-bones (a circle of the
    cutter through the corner, 0.59 mm into the walls). The two front corners lie in the C6R1 key
    well: their walls are only the plate, under the module, so they get R2 there. *Corrected in
    CASE-8:* this entry and the 8458d1b commit first gave R1.5 from "depth / 10", which is not
    JLCCNC's rule. The old pocket was modelled with sharp corners.
  - The top part is 12.6 mm tall (was 10.6), 140.1 g (was 139.2).
- **Checks:** `display_check` fails if the ceiling is below the stack + 0.25, the skin is under
  1.0 mm, the pocket runs out from under the bezel (outside the well), the window comes within
  1.0 mm of the bezel edge, or the bezel runs over the key well or the top-edge fillet; on the
  built part it probes the pocket corners open up to the ceiling and the bezel skin and walls
  solid. `check_fit.py`'s `J3 + display` envelope (`display_envelope`) is now the J3 body
  (13.4 × 2.55) up to 5.8 mm above the PCB, then the module (14 × 36 + 0.2 V-cut at its far end)
  from 5.8 to 9.75 mm. Against the new top it gives 0 mm³; against a top with the old 16.8 ceiling
  138 mm³, and with the glass 0.3 mm higher 9.2 mm³, so the check has teeth. `section.png` adds a
  cut across the bezel and outlines that envelope.
- **What the build must do:** the nice!view header pins must be **trimmed flush on the display's
  top side** (no higher than its glass, 0.9 mm above the module PCB). Untrimmed pins stand about
  2 mm up and reach Z 18.6–19.1, the pocket ceiling (`case/production/README.md`).
- **Open (G1):** the module's far end (y 74.625, 74.825 with the V-cut) lies in the C6R1 well strip
  and now stands up to Z 18.35, beside the C6R1 keycap's back edge at y 75.075 (0.25 mm, 0.125 mm
  with an 18.4 mm cap). A keycap skirt at bottom-out (about Z 16.6–17.6 for Cherry profile) passes
  beside it. Check it on the test print with the chosen keycaps.
- **Consumers:** LAYOUT: `layout/display.py` `Z_POCKET_TOP` (16.8) and `layout.json` `pocket_z` are
  stale; set them to 18.6 or drop them. DOCS: `design.md` §4, `case.md` (Z stack, size 17.6 →
  19.6 at the bezel, display row, the 8.2 mm envelope), `verification.md` G1 (stack row: the limit
  is now 9.75 mm), `bom.md` line 86 and the build guide (trim the nice!view pins; no low-profile
  socket or spacer needed).

### CASE-2. TRRS relief: BOARD-13's cut kept and re-checked (§4 G2)

- `jack_relief_poly()` (J2 body 14.1 × 6.1 + 0.5 mm, in the top, the spacer and the plate DXF) is
  unchanged. `jack_check` passes with the J2 body under the relief and 1.0 mm of headroom, and the
  fit check reports 0 mm³ against the layout J2 envelope on both halves. `plates/` is unchanged.

### CASE-3. Tapped holes follow the JLCCNC threaded-hole guideline; shorter screws (§10 fasteners; supersedes the thread depths in `case.md` and `bom.md`)

- **Guideline** (<https://jlccnc.com/help/article/threaded-hole-guideline>, read 2026-11-04): a
  blind hole leaves at least half its diameter unthreaded at the bottom; the effective thread is at
  most 3 D; holes are modelled at bottom-hole size and the threads given on the 2D drawing.
- **Problem:** the drawings asked for full thread to 0.4 mm of the bottom (T holes 6.0 and 3.9 mm
  deep, M3 holes to depth − 0.5). With D/2 unthreaded, the M2.5 × 14 and × 12 screws would bottom
  0.65–0.75 mm before their heads seat. The STEP holes were flat-bottomed, so the "1.1 mm skin"
  under the key well ignored the 0.62 mm point of the Ø2.05 drill: 0.48 mm in reality.
- **Change** (`TAP_HOLE`, `tap_hole()`, `tap_cut()`; drill points modelled at 118°):

  | Holes | Drill (full Ø) | Min full thread | Screw | Engagement | Tip reach (head 0.2 deep) | Skin at the drill point |
  |---|---|---|---|---|---|---|
  | T2–T4, T6–T8 (edge bosses) | 6.0 | 4.5 | M2.5 × 12 (was × 14) | 3.4 | 3.6, 0.9 short of the thread end | 2.38 to the top face |
  | T1, T5 (under the key well) | 3.6 (was 3.9) | 2.3 | M2.5 × 10 (was × 12) | 1.4 | 1.6, 0.7 short | 0.78 to the key-well floor |
  | L1, L3 / L2 (M3 leg bosses) | 5.5 / 7.5 (unchanged) | 4.0 / 6.0 | M3 thumbscrew | | ≤ 3.7 / 5.7 past the boss face | |

- **Why T1/T5 are not deeper or through:** only 5.0 mm of metal lie between the boss face and the
  key-well floor. An M2.5 × 12 needs ≥ 3.9 mm of thread there, so a drill ≥ 5.15 mm: a through
  hole. Both holes sit in keycap gaps (0.42 and 0.44 mm outside the nearest keycap), so a through
  hole would show on the key-well floor. 1.4 mm of engagement (3 threads) in 6061 holds about 1 kN,
  above the preload of a snug M2.5; `hardware.csv` says "snug only".
- **Check:** `tap_check` fails if a hole leaves < D/2 unthreaded, threads > 3 D, its screw reaches
  past the thread − 0.3, engages < 1.4 mm, or the drill point leaves < 0.75 mm of skin; on the
  built part it probes each hole open to its depth and solid from the drill point to the face.
- **Leg thumbscrews:** the stock EZ screw's length is unknown. `hardware.csv` names an M3 × 12
  knurled thumbscrew (DIN 653 only, no collar, head bearing on the leg's back face: 4.0 mm reach)
  with a 0.5–1.0 mm friction washer under the hub (3.0–3.5 mm reach), or the stock screw measured
  first. This said "DIN 464/653" until ORDER-5: a DIN 464 cannot clamp the leg.
- **Consumers:** DOCS: `case.md` (Fasteners, threads row), `bom.md` lines 92–93 (now 12 × M2.5 × 12
  and 4 × M2.5 × 10), `legs.md` (thread table: full thread and reach), build guide. PACKAGE / the
  shopping list: `case/production/hardware.csv`.

### CASE-4. The leg caps are ordered as one TPU tree from JLC3DP

- **Problem:** the cap (Ø9 × 8.5 mm) must be flexible to grip the desk. JLC3DP's only flexible
  material, TPU 95A, is FDM only, with a minimum part of 30 × 30 × 10 mm (design guideline
  build-size table; its TPU page says 30 × 30 × 15). Its MJF, SLA and SLS materials accept
  5 × 5 × 5 mm parts but are all rigid.
- **Change:** `build_leg_cap_tree()`: 8 caps (6 + 2 spares) upright on their open ends on a 3 × 3
  grid (12.5 mm pitch), joined at the base by 1.6 × 1.6 mm runners and spokes to a Ø8 × 16 mm tag
  post: 34 × 34 × 16 mm, one part (`worxboard_leg_cap_tree.stl`). `cap_tree_check` fails unless it
  is one solid, at least 30 × 30 × 15 mm, with every bore open and every dome in place. The single
  cap (`worxboard_leg_cap.stl`) stays the fallback to print yourself.

### CASE-5. The plate spacer loses its webs under 1.0 mm (JLC3DP MJF)

- **Problem:** the spacer had 35 mm² of slivers under 0.8 mm wide in 13 places (46 mm² under 1.0).
- **Change:** `spacer_face()` opens the outline by `SPACER_MIN_WEB` = 1.0 mm (offset −0.5 / +0.5;
  it only removes material): 21.02 → 20.88 cm³, still one piece per half; `spacer_check` and the
  mirror check pass. It is ordered in MJF PA12 (`jlc3dp/ORDER_NOTES.md`).

### CASE-6. The order package is committed in `case/production` and checked in CI

- **Layout:** `jlccnc/` (STEP + PDF per machined part, `hole_table.csv`, `ORDER_NOTES.md`),
  `jlc3dp/` (the spacers and the cap tree as STL, `ORDER_NOTES.md`), `hardware.csv` and
  `README.md`. Only the README and the two order notes are hand-written. `case/ORDER_NOTES.md` is
  now a pointer to them. `just order` builds the same tree in `case/exports/order/` (it was flat)
  plus `plates/`.
- **Reproducible:** the STEP files carry the part name and `CASE_REVISION_DATE` instead of the
  export time; the PDFs have no creation date; the title block shows `CASE_REVISION` (A1) and its
  date instead of `git describe` and today. Two local rebuilds gave byte-identical packages.
- **CI:** `case.yml` runs `just case-tests`, `just order` and `just production-check`
  (`case/production.py`). CSVs must be identical. For files whose bytes differ, STEP solids are
  subtracted in both directions (at most 0.0001 mm³ total difference), STL oriented triangles are
  compared within 0.0001 mm per coordinate, and PDF page sizes and drawings rendered at 600 dpi must
  match. File metadata and STL facet order may differ. This replaces the original checks of bulk
  properties and PDF text, which could miss moved holes or changed drawings.
- **Size:** 14 MB committed; the two top STEPs are 4.72 and 4.74 MB (4.88 and 4.90 at A2, CASE-8), under the 5 MB limit. The
  assembly STEP (8 MB) and the printed parts' STEPs stay in the `worxboard-case` artifact.
- **Consumers:** `tests/integration/release.py` reads `case/exports/*.step|stl` only, so the new
  `worxboard_leg_cap_tree.{step,stl}` join the case zips; nothing reads `case/exports/order`.
  DOCS: `docs/ordering-jlcpcb.md` and `case.md` should point to `case/production/README.md`.

### CASE-7. Result

- **Clean tree** (`git archive 8458d1b`, `just pcb-fab left` and `right` in kicad/kicad:10.0.7, then
  `just model fitcheck order production-check`): every case check passes; the fit check reports
  **0.0000 mm³** on both halves against the fresh PCB STEPs (90 bodies each, with J3's 5.0 mm
  socket model) plus the layout envelopes of J1, J2, J3 + display and the bottom-side parts; the
  15 generated files of `case/production` are byte-identical.
- **Model** (both halves): outline, legs (full M3 thread 4.0 / 6.0 / 4.0, reach ≤ 3.7 / 5.7 / 3.7),
  webs, feet, display (pocket Z 8.6–18.6, glass ≤ 18.35, bezel Z 17.6–19.6), jacks (J2 1.0 mm
  headroom), taps (8 per half as in CASE-3, probed on the built part), spacer, mirror
  (top dV 4.7e-6), cap tree 34 × 34 × 16 mm; every part valid and one solid.

  | Part | Size (mm) | Mass (6061) |
  |---|---|---|
  | top, per half | 192.4 × 165.6 × 12.6 | 140.1 g |
  | bottom, per half | 189.7 × 165.6 × 7.0 | 208.1 g |
  | spacer, per half | 182.7 × 136.6 × 3.0 | 20.9 cm³ |
  | leg (× 6) | 10.4 × 48.7 × 8.0 | 4.9 g |
  | leg cap tree (TPU) | 34.0 × 34.0 × 16.0 | 3.9 cm³ |

- **CI** (`case` workflow): runs 41758898662 (2d3d66b), 41758936908 (18cd3b9) and 41759846889
  (8458d1b) pass: model, plates unchanged, fit check (layout envelopes), renders, order package
  and `production-check`. On 18cd3b9 all 15 files were byte-identical to the committed ones; on
  8458d1b the two top PDFs differed in bytes only (same pages and text), which the original check allowed.
- `pytest layout` 32 passed, `pytest tests/integration` passed.

### CASE-8. Every internal corner meets JLCCNC's radius-for-depth rule; case revision A2 (§10; corrects CASE-1, supersedes the J2 relief radius of BOARD-13)

- **Rule** (<https://jlccnc.com/help/article/CNC-Machining-Design-Guideline>, read 2026-11-04): an
  internal corner H deep (from the face the cutter enters by) needs R ≥ H/10 + 0.5, with a tool of
  Ø H/5; R0.5 is possible to 3 mm. The tool table gives Ø2 / Ø3 / Ø4 tools a maximum length of
  10 / 15 / 20 mm and a Min R of 1.5 / 2 / 2.5. Its 0.8 mm minimum wall for metal also applies.
- **Problem:** `corner_r()` took the rule to be "depth / 10, rounded up to 0.5". That put these
  corners below JLCCNC's minimum (the key well's R1.0 at 4.0 mm and the cavity's R2 and larger
  were already right):
  - **D1 dog-bones** were R1.5 at 11.6 mm. Past the Ø2 tool's 10 mm the Ø3 tool cuts it, Min R 2.
    If JLCCNC had left its R2 as a plain corner, the nice!view's two header-end corners would hit it.
  - **Wall fillets** were R1.0 where webs and leg pads meet the wall, at 5.1–7.6 mm from the parting
    face (the rule gives 1.01–1.26, so R1.5 with the Ø2 tool). The bottom's web fillets were R0.5 at
    4.0 mm (rule 0.9, so R1.0).
  - **Relief pockets above the plate** were R1.0 (`TOOL_R`) at 7.6 mm. Clipping them against the
    cavity, the bosses and the leg pads also left sharp corners: wedge crevices of 40–167° where
    boss T4 and the inner leg pad crossed the relief edge.

  Measuring the built parts turned up two older defects as well:
  - Boss T2 (right frame (59.7, 121.7), Z to 14.6) reached 0.67 mm into the key well. It stood
    1.0 mm above the plate there as a 3.3 mm² crescent island.
  - One clipped key-well corner (right frame (22.4, 137.8)) stayed sharp, because its 0.81 mm edge
    was shorter than R1.0 and `_filleted_polygon_face()` skipped it.
- **Change** (`case/worxboard_case.py`):
  - **`corner_r(H)`:** R0.5 to 3 mm; to 10 mm, H/10 + 0.5 rounded up to 0.5 (R1.0 to 5 mm, R1.5 to
    10 mm, the Ø1 / Ø2 tools); past 10 mm, the Min R of the smallest tool in `JLCCNC_TOOLS` that
    reaches.

    | Radius | Was | Now |
    |---|---|---|
    | Top wall fillets: webs (5.1 / 7.6 deep) and leg pads (7.6 deep) | R1.0 | R1.5 |
    | Bottom web fillets (4.0 deep) | R0.5 | R1.0 |
    | Leg arm-to-hub joint (6.0 thick) | R1.0 | R1.5 |
    | `check_fit` web keep-out | 1.05 | 1.55 |

    The leg boss root fillet is a floor fillet (the end mill's corner on the wall face), not a
    vertical corner, so it stays R0.5 (`LEG_BOSS_ROOT_R`).
  - **D1** (`pocket_corners`, `pocket_reliefs`, `pocket_footprint`, `pocket_cut`):
    - The two back corners, walled up to the ceiling, get **R2 dog-bones** (`pocket_corner_r()`),
      which cut 0.586 mm into each wall.
    - The two front corners lie 1.103 mm inside the C6R1 well. They are walled only in the plate
      (Z 12.1–13.6, below the module at Z ≥ 14.4), and get R2 fillets there. Above the plate they
      are open into the well, so they need no dog-bones, and the C5-side wall there keeps its
      1.425 mm.
    - The bosses, webs and leg pads keep their clearances to the pocket including the reliefs.
    - The fit-check DXF draws the reliefs.
  - **Relief pockets** (`relief_poly`):
    - The union of main relief, zones and J2 relief is clipped to the cavity.
    - It keeps `RELIEF_ISLAND_CLEAR` = 0.3 mm off everything that stands in the band
      (`relief_islands`: the bosses rising to Z 14.6 with their webs and fillets, and the leg pads
      with theirs).
    - Only then is it opened by `relief_r()` = R1.5, so every corner the clipping leaves is a
      cutter's arc.
    - The J2 relief is R1.5, and the fit check gives 0 mm³. This changes the plate DXFs and the
      spacers. *Corrected by CASE-9:* the J2 body's corners kept 0.084 mm only to
      `jack_relief_poly()` (the spacer and the plate DXF). In the top, `relief_poly()` opens the union
      a second time with 4-chord arcs, which left **0.022 mm** at J2's two far corners on both halves
      (A1: 0.28). No gate checked a margin. CASE-9 makes it 0.38 mm and gates it.
    - The relief arcs are 4 chords per quarter circle (`RELIEF_QUAD_SEGS`, 0.03 mm off a true R1.5).
      At 16 chords the top STEPs were 5.7 MB; now they are 4.88 and 4.90 MB.
  - **Key well:**
    - Cut a second time after the bosses, webs and pads, up to Z 15.1 and below the bezel, so
      nothing stands in it.
    - `_filleted_polygon_face()` also fillets a corner whose edge is shorter than the radius when
      R·tan(turn/2) fits in half of it.
  - `CASE_REVISION` A2.
- **Checks:**
  - **`display_check`** also fails if:
    - the pocket radius is below `corner_r(11.6)`;
    - a corner other than the two far-end ones lies in the key well;
    - a far corner is within `TOOL_R` of the well edge;
    - a relief leaves less than 0.8 mm of wall to the key well or the bezel outside.

    It now reports R2.0, 2 dog-bones and a 0.84 mm thinnest wall: the raised bezel on the C5 side,
    Z 17.6–18.6, under the skin. On the built part it probes each relief open at three heights,
    the wall behind it solid, and each far corner open over the plate and filleted in it.
  - **New gate `case/corner_check.py`** (`just corners`, a step of the `case` workflow):
    - Reads the five machined STEPs and finds every vertical internal corner: a concave Z-cylinder
      face that is not a hole, a sharp concave vertical edge (turn ≥ 30°), or a vertex of a
      polygonised arc, with its radius taken from the longer chord.
    - Ray casts give the face it opens to, so its depth from the top face (Z 17.6) or the parting
      face, and it fails if R < `corner_r(depth)`.
    - Exempt and listed: the switch and stabiliser cut-outs (R0.5, a 1 mm end mill, through the
      1.5 mm plate at the bottom of the open key well), the engraved side mark and side
      operations (the USB-C recess).
    - On the A1 package it fails 192 corners:

      | A1 corners failed | Count |
      |---|---|
      | D1 R1.5 | 4 |
      | Top fillets R1.0 | 32 |
      | Bottom fillets R0.5 | 4 |
      | Sharp | 18 |
      | Relief-arc vertices at R1.0 | 134 |

    - On A2 it passes. Each top: 287 / 288 arc vertices and 53 fillets pass; 180 cut-out fillets and 2
      side-operation edges are exempt. Each bottom: 11 fillets pass, 5 engraving edges are exempt.
      Leg: 2 fillets pass.
  - **Fit check teeth:** a top with plain R2 pocket corners instead of the dog-bones gives
    0.1127 mm³ against the J3 + display envelope; with the dog-bones, 0.
- **Text:**
  - Drawings: the D1 row, a general note listing the radii per depth (key well R1.0, reliefs and
    wall fillets R1.5, D1 R2, exceptions), the bottom's fillets and the leg's joint.
  - `jlccnc/ORDER_NOTES.md`: the R2 dog-bones and the corner rule in the top remarks, the "sharp
    internal corners" and bezel-wall answers, and what changed in A2.
  - The production README and `jlc3dp/ORDER_NOTES.md` say A2, and `just corners` is part of the
    rebuild.
- **Result** (both halves):
  - **Model:** every case check passes. Parts are valid, one solid each; top mirror dV 6.4e-6.

    | Part | Volume | Mass |
    |---|---|---|
    | Top | 52.08 cm³ | 140.6 g (was 140.1) |
    | Bottom | | 208.2 / 208.1 g |
    | Leg | | 4.9 g |

    Leg cap tree and `hardware.csv` are unchanged.
  - **Fit check:** 0.0000 mm³ against both PCB STEPs. The STEPs came from `just pcb-fab left` and
    `right` on a clean `git archive` of 73ec186 (kicad/kicad:10.0.7 images): 90 bodies each, with the
    layout envelopes. Also 0.0000 mm³ against the layout envelopes alone (CI mode).
  - `just corners` passes. `just order production production-check`: 15 generated files are
    identical to the committed ones.
  - `pytest layout` 32 passed, `pytest tests/integration` 111 passed.
  - **CI:**
    - `case` runs 41769047882 (9d51b34) and 41769062487 (fa3f4ca, with the new `just corners` step)
      pass. The gate gives the same counts as locally.
    - `production-check`: 14 files are byte-identical; the right top PDF differs in bytes only
      (same pages and text).
    - The `pcb` workflow's fit job against the CI-built PCB STEPs passes on 9d51b34
      (run 41769048082).
- **Consumers:**
  - DOCS: `case.md` should give the corner radii per depth and the relief pockets' R1.5. The
    `corner_r` line in `design.md` §10 is still right.
  - BOARD-13's "J2 relief rounded to `TOOL_R` (1.0)" is now R1.5.
  - No other stream's files change: the PCB, layout and STEP envelopes are as before.

### CASE-9. The TRRS jack keeps 0.38 mm to the top at its corners, and a gate holds every jack ≥ 0.3 mm clear; case revision A3 (§4 G2, §10.6; corrects CASE-8, supersedes the J2 clearance of BOARD-13 and CASE-2)

- **Problem** (verifier, on the committed A2 package): at plate level (Z 12.1–13.6, the top 1.5 mm
  of the 5.0 mm jack body), the top's J2 relief came within **0.022 mm** of the J2 body's two far
  corners, on both halves. These are KiCad (63.1, 99.95) and (63.1, 106.05) on the right and
  (196.9, 99.95) and (196.9, 106.05) on the left. A1 had 0.28.
  - `jack_relief_poly()` (body + 0.5 mm, mitred, opened by R1.5) left 0.084 mm at the corners:
    r − √2 (r − c) = 1.5 − 1.414 = 0.086, less 4-chord arc error.
  - `relief_poly()` then opens the whole union a second time, with 4-chord arcs again, which pulls
    the corners another 0.06 mm in.
  - CASE-8's "0.08 mm" held only for the spacer and the plate DXF. No gate checked any margin:
    `jack_check` only asked that the relief contain the body, and the 0 mm³ fit check is nominal.
  - The case is ISO 2768-m, JLC places the jack by SMT, and the PCB floats in the cavity as far as
    its screw holes allow. So the plate edge would likely land on the jack's corners when the case is
    screwed shut, loading the SMD joints of the split link.
- **Change** (`case/worxboard_case.py`):
  - **`J2_RELIEF_CLEAR` 0.5 → 0.75.** At R1.5 that gives 0.44 at a body corner on a true arc.
  - **New `JACK_MIN_CLEAR` = 0.3 mm.** It is the least plan clearance from a jack body (layout
    envelope) to anything that cuts round it.
  - **`jack_check`** now fails, for J1 and J2, if the body is closer than that to:
    - the top's relief (`relief_poly`, as `sp_faces` simplifies it);
    - for J2, its own relief (`jack_relief_poly`, the spacer cut-out) and the plate DXF's notch
      (`plate_face`).
  - On the built top, `jack_check` also takes the solid's least 3D distance to the body
    (`jack_body()`, a box from the PCB top to the jack height). That is the plate edge, the relief,
    the wall at the mouth or the ceiling, whichever is nearest.
  - **`spacer_check`** does the same for the spacer solid.
  - `CASE_REVISION` **A3**.
  - Not changed: `RELIEF_QUAD_SEGS` (finer arcs would push the top STEPs past 5 MB). The double
    opening also stays, since the gate now bounds what it costs.
- **Result** (both halves identical):

  | Clearance to the J2 body | A1 (73ec186) | A2 | A3 |
  |---|---|---|---|
  | Top part, built STEP (3D, = plan at plate level) | 0.283 | **0.022** | **0.376** |
  | Spacer (`jack_relief_poly`; committed STL section) | ≈ 0.29 | 0.084 | 0.431 |
  | Plate DXF notch (committed DXF) | ≈ 0.29 | 0.084 | 0.431 |
  | Body sides | 0.5 | 0.5 | 0.75 |

  - J1 keeps 0.49 to the relief and 0.50 to the built top, limited by the back wall at its mouth,
    the same as before.
  - The plate keeps 4.39 / 4.72 mm between the notch and the C6R1 / C6R2 switch cut-outs (A2:
    4.74 / 5.07). The notch now spans x 48.25–63.85 by y 99.2–106.8 (right frame; left
    196.15–211.75).
  - **Independent probes:**
    - Sections of the committed top STEPs at Z 12.15, 12.85 and 13.55 give 0.376 on both halves
      (A2: 0.022).
    - `is_inside` finds no solid at the far corners 0.03–0.35 mm out, along the diagonal or in x or y.
      On A2 it found solid at 0.03 on the diagonal and 0.04 in x or y.
  - **Negative test:** with `J2_RELIEF_CLEAR` = 0.5, `jack_check` stops with "right J2 body is
    0.022 mm from the top relief". The built-part measure gives 0.0223 mm on the A2 right top STEP.
- **Checks:**
  - `just model`: every case check passes; the parts are valid, one solid each; top mirror dV
    6.4e-6. The top is 52.08 cm³ (140.6 g) and the spacer 20.88 cm³.
  - `just fitcheck`: 0.0000 mm³ on both halves, against the PCB STEPs of the committed boards plus
    the layout envelopes of J1, J2, J3 + display and the bottom-side parts (90 bodies each). The
    PCB STEPs were built by `just pcb-fab` in kicad/kicad:10.0.7 from a tree whose boards,
    `pcb/lib` and `layout.json` are byte-identical to HEAD's.
  - `just corners` passes: per top, 288 / 287 arc vertices and 53 fillets.
  - `just order production production-check`: 15 files match.
  - Top STEPs: 4,884,988 (right) and 4,901,054 (left) bytes, still under 5 MB.
  - `pytest layout` 32 passed; `pytest tests/integration` 111 passed.
  - **CI on dec5f7b:**
    - The `case` run 41773758643 passes, with the same clearances as locally. All 15 files of
      `case/production` are byte-identical, and the plates are unchanged.
    - The `pcb` workflow's fit job (run 41773758599, job 126390418543) gives 0.0000 mm³ on both
      halves against the CI-built PCB STEPs.
- **Files that change:**
  - The two tops (STEP, PDF), the two spacers (STL) and `plates/*.dxf`.
  - The bottom and leg PDFs, for the revision letter only. Their STEPs and `hole_table.csv` are
    byte-identical.
  - The renders.
  - The production README and both `ORDER_NOTES.md`, which say A3. The JLCCNC notes' "What changed"
    section explains the change.
- **Consumers:**
  - BOARD-13's and CASE-2's "J2 body + 0.5 mm" is now + 0.75 mm. Its "≥ 3 mm to the C6R1 / C6R2
    cut-outs" still holds (4.39).
  - DOCS: `case.md`'s TRRS row still describes the pre-G2 relief (0.5 mm over a 5.5 mm body; 14.1 mm
    "2.1 mm longer than the relief"). It should say: the J2 body 14.1 × 6.1 × 5.0 with 0.75 mm round
    it (corners ≥ 0.38) in the top, the spacer and the plate; 1.0 mm headroom; gated by
    `JACK_MIN_CLEAR`.
  - No other stream's files change: the PCB, `layout` and the STEP envelopes are as before.

## PKG: the JLC turnkey order package (`pcb/scripts/stage_p.sh`, `package.py`, `panel.json`, `panel_tabs.py`, `jlc_check.py`, `cpl_check.py`, `jlc_footprints.py`, `jlc_rotations.csv`, `pcb/production/`)

Written by DOCS from the PKG commits (4396f6c, 653659a, 0c692a9, 73ec186) on 2026-11-04.

### PKG-1. The order is a customer panel with rails, tabs, fiducials and tooling holes (§9 stage 13; BOARD-7)

- **Spec:** KiKit's bare-board JLC files, with JLC adding the rails.
- **Problem:** Standard PCBA needs rails and fiducials. JLC's terms want parts at least 2.5 mm from
  the board edge. J1 and J2 overhang the edge, and several thumb sockets sit closer than 2.5 mm
  (BOARD-7). Rails that JLC adds on its own judgement could land a tab or a V-cut in front of a
  connector.
- **Change:** stage P (`stage_p.sh`, `just pcb-production <side>`) panelizes the committed board
  with KiKit (`panel.json`, `panel_tabs.py`):
  - the board in a solid frame, 198.84 × 174.75 mm (JLC's Standard PCBA limit is 250 × 250);
  - rails of 6 mm or more, and a 2 mm milled slot round the board;
  - 14 mouse-bite tabs per half, each with six Ø0.6 mm holes 1 mm apart, a third of each hole in
    the board, as JLC's mouse-bite guide asks. Tabs are ≥ 1.4 mm from every courtyard and ≥ 2.1 mm
    from J1 and J2, with no tab in front of either;
  - 3 fiducials per side: Ø1.0 mm copper in a Ø2.0 mm opening, centres 4.0 mm from the edges
    (JLC: 3.85);
  - 4 non-plated Ø2.0 mm tooling holes. JLC's SMT guideline of 2026-09 asks for 2 mm, its older FAQ
    for 1.152 mm, and JLC adds its own on the rails if it needs them.

  Panel DRC: 0 errors, 0 unconnected. `bare-board/` keeps the unpanelled files and a remark for an
  order where JLC adds the rails.
- **Consequence:** the board must be broken out and every tab nub sanded flush, because the case
  leaves about 0.3 mm round the PCB (build guide, step 1).

### PKG-2. Every CPL correction is derived from JLC's own footprint and proven by `cpl_check.py` (§9 stage 13; supersedes REVIEW-FIX-5, ELEC-7)

- **Problem:** the REVIEW-FIX-5 table came from a community list of 2024. Its U1 (QFN-56, 270) and
  J1 (USB-C, 180) rows were wrong, and it had no row for J2, J3 or the hot-swap sockets: 41 of 119
  parts per half would have been misplaced (ELEC-7). Nothing tested a rotation.
- **Source:** `jlc_footprints.py` fetches JLC's footprint of each LCSC part (the EasyEDA / JLCEDA
  library, through the lceda.cn API; easyeda.com returned 403) into `jlc_footprints.json`. It covers
  the 21 BOM parts and the fallbacks C49352235, C9002 and C46061764. Every pad matched LCSC's
  footprint SVG to within 0.0025 mm.
- **Change:** `jlc_rotations.csv` holds a row for every footprint whose JLC origin or zero angle
  differs from KiCad's:
  - QFN-56 0;0;0;
  - SOIC-8 0;0;270;
  - SOT-23-5/6 0;0;−90;
  - USB-C 0;−1.394;0, anchored on the locating pegs (the SMD pads alone give −1.572);
  - PJ320D 0.776;0;90;
  - `SW_MX_Hotswap_Kailh` 0.635;3.81;180. Y is entered as is because KiKit does not mirror the
    offset on B.Cu, and 180 is decided by the body notch;
  - the J3 socket 0;5.08;270.
- **Check:** `cpl_check.py` (stage D, on the bare-board CPL) places each JLC footprint where the CPL
  puts it, top or bottom, every orientation included (the 155°/205° thumbs). It requires:
  - the part within 0.1 mm of the best fit on its pegs, barrels or pads;
  - pin 1 on KiCad pin 1;
  - every terminal on its pad, and THT pins inside their holes;
  - the body clear of the footprint's other holes.

  Result: 119 of 119 per half, worst 0.033 mm, terminals 89–100 % on pad, socket bodies 0.70 mm
  clear of the switch post. The wrong values fail it: U1 at 270 (6.1 mm off), USB-C at −1.572 (pegs
  0.18 mm off), a socket at 0° (body 1.13 mm into the post hole), Y not negated (6.4 mm off).
  `just pcb-cpl-images` draws the overlays `docs/images/cpl-*.svg`, and the CI `cpl-images` job
  requires them current.
- **Not documented by JLC:** its bottom-side CPL convention. The rows follow the one that KiKit,
  kicad-jlcpcb-tools and KiBot use (top-view X/Y, 180° minus the KiCad angle plus the correction).
  The placement preview is the last check ([ordering-jlcpcb.md](ordering-jlcpcb.md#placement-preview-checklist)).

### PKG-3. The order files use JLC's own formats and are reproducible (§9 stage 13)

- **Formats:**
  - The BOM header is `Comment,Designator,Footprint,LCSC Part #`, JLC's name, not KiKit's `LCSC`.
  - The CPL layer is written `Top` / `Bottom`, as on JLC's help page, not KiKit's `T` / `B`.
  - The CSVs use LF line endings (`.gitattributes` stores text as LF).
  - `gerbers.zip` leaves out KiKit's `Cmts.User` layer, which holds the mounting-hole circles under
    KiKit's "V-CUT" layer name. It also leaves out the drill maps, the drill report and the gbrjob.
- **Determinism:** KiCad's creation dates are stripped from the Gerbers, and the zips are built with
  fixed entries. `just pcb-production-check <side>` rebuilds the package and diffs it byte for byte.
  The CI `production` job runs it per half.
- **`jlc_check.py`** checks:
  - formats and headers;
  - BOM = CPL = the 119 parts `design.py` fits;
  - the panel size, rails, fiducials, tooling holes and tab clearances;
  - that the panel carries the board's copper unchanged (footprints, tracks, vias, zone fills).

  `--stock N` adds the live JLC stock check (`just pcb-stock <side>`).

### PKG-4. `pcb/production/` is committed on `main`, not only on hardware tags (§12, §14 WS5)

- **Spec / WS0:** `pcb/production/` is filled only on `v*-revA` tags. `.gitignore` ignores
  `pcb/production/*`, and `layout/tests/test_repo.py` checks that.
- **Change:** the two order packages are force-added (`git add -f`) and tracked on `main`, so the
  order is reviewable and CI can hold it to the board. A new file there still needs `git add -f`.
  The owner of `.gitignore` and the repo test should decide whether to un-ignore the directory.
- **Open, WS5 / release:** `release.yml` still packs `build/<side>/jlc` (KiKit's raw bare-board
  files). It should ship `pcb/production/<side>/` or `worxboard-<side>-jlc-order.zip` instead.

## DOCS: the ordering documentation (`docs/`, `README.md`, `CHANGELOG.md`, `site/` status text)

### DOCS-1. The ordering docs follow the order package; no drop-in alternate for J3 (§7, §14 WS4)

- `docs/ordering-jlcpcb.md` is a step-by-step turnkey order from `pcb/production/`: every form
  field, the parts-page and placement-preview checks per part type, the customs description, the
  likely engineering questions, out-of-stock alternates and a cost estimate dated 2026-11-04.
  `docs/shopping-list.md` lists the four orders and every off-board part.
- **J3 alternates:** ELEC-3 named C46061764 (5.7 mm) as J3's fallback. The case pocket clears the
  glass at 9.75 mm above the PCB, the full tolerance of the 5.0 mm socket, with the ceiling at
  10.0 mm (CASE-1). A 5.7 mm socket raises the glass by 0.7 mm, to 10.45 mm at full tolerance, so
  the docs list **no** drop-in alternate for J3. If C27985230 is out of stock: wait, or leave J3
  off the order and solder the nice!view's own 5 mm socket by hand.
- **Status flags:** `site/gen_docs.py` keeps no `[G3]` flag. The former `[G3]` lines are `[J]`:
  checked against JLC's record and, through `cpl_check.py`, its footprint. The fee text follows
  JLC's price page (updated 2026-10-22): in Standard PCBA basic and extended parts pay the same
  $1.53 loading fee.
- **Cost estimate inputs, not quoted:** the bare-PCB price and shipping (no public formula; given
  as ranges), and whether JLC charges the fixture fee ($16.42 per design) and a loading fee for the
  THT J3.

## ORDER: fixes from the order review of the turnkey package (`pcb/`, `case/`, `docs/`)

The review of 2026-11-04 checked the PCB and case order packages against JLCPCB's, JLCCNC's and
JLC3DP's published rules and the parts they hold. Each defect below was confirmed before it was fixed.

### ORDER-1. J1's four shell legs are on the paste layer: pin-in-paste, and a remark (§9 stages 12–13)

- **Problem:** J1 (HRO TYPE-C-31-M-12, C165948) is held by four GND shell legs in plated slots. The
  stock footprint puts them on `*.Cu` and `*.Mask` only, so both PasteTop gerbers had no aperture
  at the four slots (the copper and mask openings were there). JLC's stencil standard
  (opening-process-standard-of-stencil, section 5): "the apertures for through-hole components will
  not be open in stencil as default. Please design it on the solder paste layer correctly or leave a
  remark when you ordering." JLC's own footprint of C165948 also makes these pads through-hole.
  Nothing in the order asked for them, and the build guide did not check them. Unsoldered, the
  receptacle's retention and its shield-to-GND path would rest on the 0.3 mm signal pads.
- **Change:**
  - **`pin_in_paste.py`** (new, stage C after `prune.py`, before the last DRC gate) adds F.Paste to
    the four `SH` pads, so the stencil opens a 1.0 × 2.1 mm or 1.0 × 1.6 mm oval over each slot and
    the legs reflow with J1's SMD pins. `checks.py` fails if a pad lacks paste. It runs after
    routing on purpose. Adding the paste layer in `place.py` was tried first: the stages seed their
    KIIDs from the board bytes, so the right board then routed differently and stage C ended with
    QSPI_SD0 open. After routing the step changes only those four pad lines, and both boards are
    otherwise byte-identical to their previous versions.
  - **Remark** (`package.py`, both READMEs, `ordering-jlcpcb.md`): "J1 (USB-C, C165948): please
    solder its 4 through-hole shell legs (GND) too. The paste layer opens them for pin-in-paste."
    The likely-questions table answers it too.
  - **Build guide:** check that each of the four slots shows solder round its leg, and solder a
    bare one before going on.
- **Result:** the PasteTop gerbers of both panels and bare boards have the four ovals at the J1
  slots (left panel: X 23.598 / 32.238, Y −10.6 / −14.78). DRC 0 / 0 / 0 and `checks.py` 14/14 on
  both halves. The copper, drills, BOM and CPL are unchanged. The renders change only round J1. The
  cost table already counted the 4 legs among J1's 16 SMT joints.

### ORDER-2. The bottom-side warning names the thumb parts as the tell (§9 stage 13; amends PKG-2)

- **Problem:** the warning in `ordering-jlcpcb.md` and in the generated READMEs said that, if JLC's
  viewer used another bottom-side convention, every bottom socket and diode would show turned by
  180°, and that a single part off was more likely a viewer slip. That covers only a viewer that
  mirrors about the other axis. KiKit's reading, which `cpl_check.py` checks, is `Mx · Rot(r)`:
  in the top view, mirror and then turn clockwise by r. A viewer that mirrors and then turns
  counter-clockwise differs from it by twice the angle, 2r. It shows the 62 parts at 180° exactly
  as before. Only the 12
  thumb parts, SK132–SK137 and D132–D137 at 205° (left) or 155° (right), come out about 50° off,
  the sockets up to 5.8 mm and the diodes 1.5 mm off their pads (JLC's footprints from
  `jlc_footprints.json` placed both ways). A builder following the old warning would not have
  recognised that.
- **Change:** `jlc_check.py facts` lists the bottom parts at an angle other than 0° or 180°, and
  `package.py` writes the preview check from it: the thumb parts tell the two readings apart; if
  only they are off by about 50°, they need 360° minus the CPL value (155° left, 205° right); if
  every bottom part is off by 180°, the viewer mirrors the other way; in either case ask for the
  correction in the placement confirmation. `ordering-jlcpcb.md` says the same. The CPL is
  unchanged.

### ORDER-3. Two stabiliser hole pairs per half are closer than JLC's 0.45 mm hole spacing (§9 stage 13)

- **Problem:** where the two 2u thumb keys meet, the Ø3.05 mm hole of `STAB_T4` and the Ø4.0 mm
  hole of `STAB_T5` leave 0.285 mm of board between them, twice per half. JLC's PCB capabilities
  give "Pad Hole-to-Hole Spacing 0.45mm". The board rule `min_hole_to_hole` is 0.25 mm, so KiCad's
  DRC passes it, and nothing told JLC. Expect an engineering question that holds the order.
- **Change:** the holes stay: they are non-plated clearance holes for the plate-mounted
  stabilisers, with no copper near, so a broken web between them does no harm, and moving or
  shrinking them would change the routed boards and the Cherry stabiliser footprint. Instead
  `jlc_check.py facts` measures every pair of pad holes (`close_holes`, `HOLE_GAP` = 0.45 mm) and
  fails if any pair but two `STAB_*` holes is closer, and `package.py` writes the pairs it finds
  into the remark of both READMEs (panel and bare board): "NPTH: 2 pairs of stabiliser clearance
  holes (STAB_T4/STAB_T5) leave 0.28 mm between them ... they may break into each other".
  `ordering-jlcpcb.md` has the same remark and a row in the likely-questions table. The panel
  README now has the whole remark to paste (it was only in `ordering-jlcpcb.md`).

### ORDER-4. Left half: U1's ground reaches the planes by ties, not one 0.15 mm neck (§6.4, §9 stages 11–12; corrects BOARD-14)

- **Problem** (left board only; the review's island analysis of all GND copper on both layers):
  U1's whole ground domain met the board's GND planes through one 0.15 mm × 2.24 mm F.Cu track under
  the QFN (EP to TESTEN), a 0.2 mm × 2.6 mm F.Cu track and the single TESTEN via at (94.595, 36.0385).
  The domain was the exposed pad (EP, the RP2040's only GND pin), 11 of the 12 U1 caps, flash U2
  pin 4, USB ESD U4 pin 2, SW1 and R1, with the EP's 148 mm² B.Cu island. Deleting that via alone,
  fills untouched, made `kicad-cli pcb drc` report 1 unconnected GND item (re-checked here). On the
  host-facing half, the USB ESD clamp's current ran through the MCU's ground. Shortest GND copper,
  0.1 mm raster: U4 pin 2 to a J1 GND pad 49.2 mm (straight 5.1; right 19.1), and C5, the flash's
  only cap, to U2 pin 4 110.1 mm (straight 10.1; right 18.0). DC drop was negligible (about 15 mΩ),
  so not dead on arrival, but a ground-integrity and ESD defect. The BOARD-14 gate measured only the
  shortest EP-to-plane path (5.7 mm), not its width, the number of parallel links, or U2's and U4's
  ground, and BOARD-14 reported it as a pass.
- **Gates** (`checks.py`, both halves; the shortest-path raster is now `GndRaster`):
  - **links:** the EP reaches the edge of a window 24 mm either side of U1 by at least
    `GND_LINKS_MIN` = 2 separate paths, each ≤ 50 mm, over GND copper about 0.4 mm wide or wider
    (the raster eroded by `GND_NECK_ERODE`, so a 0.3 mm track breaks up). Each next path keeps
    0.2 mm clear of the earlier ones, so two links never share a via or a neck;
  - **pin paths:** U4 pin 2 to a J1 GND pad, and C5's GND pad to U2 pin 4, each ≤ 30 mm of GND copper.

  On the committed boards before the fix, the left failed all three (0 links; both pin paths not
  reachable within the raster window) and the right passed (6 links of 32.9–38.6 mm; 17.4 and
  18.0 mm).
- **Change** (`gnd_ties.py`, new, run in stage C after the DRC gate and before `prune.py`): while a
  gate fails, it routes locked 0.5 mm GND ties with the completion router's A*, which may rip other
  nets' unlocked copper and route them again. A tie is kept only if every net closes and the gates
  improve; otherwise the board is restored. The kinds, in order: links from the EP's own B.Cu copper
  to the main F.Cu/B.Cu pour near U4 pin 2, C5, U2 and U2 pin 4; pad-to-pad (U2 pin 4 to C5); a
  pad's own via into the main B.Cu plane; links in eight wedges round the EP. A board that passes
  is not touched, so the right board is unchanged. On the left it keeps four ties:
  - near U4 pin 2: 4.8 mm with 1 via, (81.12, 46.40)–(84.12, 49.80); and 0.8 mm,
    (79.92, 45.50)–(79.42, 46.10), which rips and re-routes COL0;
  - near U2: 6.3 mm with 1 via, (93.50, 50.62)–(88.40, 51.32), which re-routes a piece of 3V3;
  - U2 pin 4 to C5's GND pad: 14.4 mm on F.Cu round the north end of U2. It re-routes 16 items of
    3V3, QSPI_SD2, QSPI_SD3 and QSPI_SS. U2's VCC is still 2.53 mm of copper from C5.

  Tried and dropped: requiring 3 links (in a trial on the committed board, no wedge tie closed every
  net: each was rejected or longer than 12 mm); pad ties alone for U2 (C5's own via gave no gain, U2 pin 4's needed 11.9 mm and
  3 vias); pair ties at the link-tie costs (22.3 mm with 4 vias). The pair tie is allowed to rip
  more (first cost 0.5 mm per cell instead of 2.0).
- **Result** (left; the right is unchanged):

  | Check | Before (BOARD-14) | After |
  |---|---|---|
  | EP vias / cap GND vias in the main B.Cu plane over B.Cu alone | 0/9, 1/12 | 9/9, 12/12 |
  | EP to the main B.Cu plane | 5.7 mm, through the TESTEN via | 1.6 mm |
  | Separate links ≥ 0.4 mm wide, ≤ 50 mm | 0 | 2 (27.0, 31.9 mm) |
  | U4 pin 2 → J1 GND | none within the gate's window (the review: 49.2 mm) | 22.3 mm |
  | C5 → U2 pin 4 | none within the gate's window (the review: 110.1 mm) | 11.4 mm |
  | Delete the TESTEN via, fills untouched | 1 unconnected | 0 unconnected |
  | U1 cap GND → EP | 9.3–13.0 mm | 9.3–13.0 mm |
  | `checks.py` | 10/10 (the new gates did not exist) | 13/13 |
  | DRC with schematic parity | 0 / 0 / 0 | 0 / 0 / 0 |
  | Copper | 2620 tracks (498 locked), 331 vias | 2647 tracks (525 locked), 328 vias, all 0.3 / 0.6, narrowest 0.135 mm |

  The USB pair (D+ 24.73, D− 23.92 mm), Y1, the decoupling distances, U4's VSYS reference
  (4.07 mm), the outline and every part position are unchanged, so BOM and CPL are unchanged.
  `prune.py` then leaves 0 unlocked dangling items (34 locked, as before). `netcmp --board`,
  `cpl_check` (119/119) and `jlc_check` (12/12) pass. The left renders and order package are
  regenerated; the CPL overlay drawings are unchanged.

### ORDER-5. Leg thumbscrews: a collarless DIN 653 only (§10 fasteners; corrects CASE-3)

- **Problem:** `hardware.csv`, the shopping list, `legs.md` and CASE-3 allowed "DIN 464 or DIN 653".
  A DIN 464 M3 (high type) has a Ø5.7–6.0 × 5.0 mm collar under its Ø12 knurled head, and its length
  is measured under the collar. The leg has a Ø6.5 × 4.0 mm counterbore in its back face
  (`LEG_CBORE`), so the collar drops into it and bears on its floor, 4.0 mm from the hub face, with
  the knurl 1 mm proud. An M3 × 12 then reaches 12 − 4.0 = 8.0 mm past the boss face (7.0–7.5 with
  the washer), against at most 3.7 mm at L1/L3 and 5.7 mm at L2: it bottoms in the blind hole before
  the leg is clamped.
- **Change:** `case/drawings.py` (`hardware_rows`) names a thumbscrew **without a collar (DIN 653)**
  and warns against DIN 464 and other shouldered thumbscrews; `hardware.csv` is regenerated. The
  DIN 653 head is flat underneath and Ø12, so it bears on the back face round the counterbore: 4.0 mm
  of reach, 3.0–3.5 mm with the washer, as before. Docs: `legs.md`, `shopping-list.md`, build guide,
  `case/production/README.md`.

### ORDER-6. The plate spacer has a channel for each stabiliser wire (§5, §10.8; amends CASE-5)

- **Problem:** a Cherry-style plate-mount stabiliser's wire bar runs under the plate, between plate
  and PCB, from one housing to the other, beside the switch. `spacer_face()` cut only the 15 mm
  switch opening and each stabiliser cut-out + 0.5 mm, and the spacer fills Z 9.1–12.1 with 0.5 mm
  over the PCB. The review's probe found the spacer solid on 161 of 161 samples between the housings
  at 7.75 mm or more from the switch centre, on both sides of all four 2u keys. The merged switch and
  stabiliser opening reached only about 6.9 mm, inside the 14 mm switch housing. The stabilisers
  could not be fitted with the spacer in place, or the wire would be pinched against the PCB. The
  fit check has no stabiliser body, so CI could not see it.
- **Change** (`case/worxboard_case.py`): `stab_wire_cuts()` cuts a channel `STAB_WIRE_U` = 6.5–10.0 mm
  across the key from its centre, on **both** sides (the wire side of a clone is not certain), along
  the key from one stabiliser to the other (2 × 11.938 mm; the stabiliser cut-outs open its ends),
  R1.0 corners. `spacer_check()` now fails if spacer material lies anywhere along either channel (126
  probe points per key). Each spacer is still one piece: 20.88 → 20.17 cm³. The machined parts are
  unchanged, so the case revision stays A3 and only the two spacer STLs change.
- **Result:** the review's probe (`stab_wire.py`) finds 0 of 161 samples solid at u = ±7.5 to ±9.0
  on all four keys; `just model`, `just fitcheck` (0 mm³), `just corners` and
  `just production-check` pass.

### ORDER-7. The USB-C cable needs a plug with at least 8 mm of bare shell (§10.5)

- **Problem:** J1's mouth is flush with the PCB back edge (`layout/jacks.py`; footprint front at
  y 30.6). The case leaves 0.5 mm, then the 3.0 mm wall with a 13 × 8 mm recess 1.8 mm deep
  (`USB_RECESS_DEPTH`; notch centre y 28.6), so the recess floor is 1.7 mm in front of the mouth and
  only the plug's bare metal shell passes the 9.4 × 3.6 mm notch. The USB Type-C receptacle-shell ECN
  asks the system for an effective shell length equivalent to the 6.20 mm reference; here it is
  about 7.9 mm. A plug with the common ~6.6 mm exposed shell stops about 1.2 mm short: the latches
  do not engage and the contacts are marginal. The shopping list asked only that the overmould fit
  the recess and said "slim plugs fit", which does not help.
- **Change:** docs only. The shopping list, `case.md` and the build guide ask for a plug with **at
  least 8 mm of bare metal shell** in front of the overmould (sold as "extended tip" or "long neck"),
  and the test-print checklist checks that the plug latches. The recess was not deepened: that would
  change the four machined parts, and 1.2 mm of wall is left there.

### ORDER-8. The stabilisers go into the top shell before the case is closed (build guide)

- **Problem:** the build guide closed the case (section 6) and then clipped the stabilisers into the
  plate (section 7, step 1). The plate is milled into the top shell, and the wire clips in from
  underneath, which the PCB and the tray close off.
- **Change:** section 6, step 2 fits the assembled stabilisers (housing, stem and wire) into the
  upturned top shell, before the PCB and spacer go in; steps 4 and 5 note the spacer's wire channels
  (ORDER-6). Section 7 starts with the switches.

### ORDER-9. Anodizing: ask for the Strict appearance tier, not only a remark (JLCCNC)

- **Problem:** `jlccnc/ORDER_NOTES.md` asked for a remark about a uniform anodize colour across the
  10 parts. JLCCNC's Appearance Standard Guidelines allow "slight anodizing color variation among
  some products" in the Standard tier; Strict and Premium allow "no visible color variation". A
  remark does not change the tier.
- **Change:** the form-settings table has an "Appearance standard: Strict (or Premium), if the form
  offers it" row, and the remark paragraph says why.

## REVB: rev B, per-key RGB, display setback and review fixes (`layout/`, `pcb/`, `firmware/`, `case/`, `docs/`)

Rev B is the order revision after the rev A pre-order review (2026-11-04). It adds an RGB LED under
every switch (assembled by the fab), moves the display back from the C6R1 key well, folds in the
review's minor points, and adds a PCBWay order package beside the JLCPCB one. Nothing of rev B has
been built yet.

### REVB-1. Per-key RGB: an SK6812MINI-E under every switch, VLED switched, data buffered (§3, §6, §7, §8, §11)

- **Spec:** no LEDs; GP22 a test pad "reserved for future RGB" (§3), RGB under future work (§13).
- **Change, layout** (`layout/leds.py`, `layout.leds()`, `layout.json` `leds` / `diodes`): the
  switches face south, so the MX LED window is at (0, +5.08) mm in the key frame, opposite the switch
  pins. LED<n> (n = 101 + chain index) sits there with its 100 nF C<n>; the chain is a serpentine (row 0
  inward, row 1 outward, row 2 inward, C6R2, row 3 outward, row 4 inward, thumbs T5, T4, T3, T2, T0,
  T1), the same key ids on both halves, every hop to a neighbour (longest about 30 mm). The matrix
  diode moves from (0, 5.0) to (0, 8.5), below the LED.
- **Change, circuit** (`design.py` `_rgb`, group RGB): U6 SY6280AAC (C55136) switches VSYS to VLED,
  EN on GP23 (RGB_EN) with R15 10k to GND, ISET R14 15k (C25756): Ilim = 6800 / 15k = 0.45 A, its 0.4 A
  minimum; C21 10 µF 0603 at IN (the datasheet "strongly recommends" 10 µF: input ringing on an output
  short), C20 10 µF 0603 at OUT. U7 SN74LV1T34DBVR (C100024, VCC on VLED, VIH 2.0 V
  at 5 V) buffers GP22 (RGB_DIN): the LED's own threshold is 0.65 × VDD, about 3.0 V at VSYS, which
  3.3 V logic meets with no margin. R16 470 Ω (C25117) feeds LED101 DIN, as the datasheet's series
  resistor. LED137's DOUT is open. VLED joins the Power netclass. TP4/TP5 (GP22/GP23) are gone.
- **Change, footprint** (`gen_footprints.py`): KiCad's stock
  `LED_SK6812MINI-E_3.2x2.8mm_P1.5mm_ReverseMount` has a 3.4 × 3.0 mm cutout with dog-bone corners
  (to ±1.817 × ±1.617) and leaves 0.247 mm from its pads to the cutout. The vendored copy
  `worxboard:LED_SK6812MINI-E_ReverseMount` moves the four pads 0.1 mm out: 0.348 mm. The `.kicad_dru`
  (`place.py` `DRU`) lets any copper come within 0.3 mm of the LED cutouts (JLC and PCBWay route to
  that); the outline keeps 0.5 mm.
- **Change, placement and routing:** `place.py` turns each LED (key rot or key rot + 180) so its DIN
  -> DOUT runs along the chain, and puts its cap beside the VDD pad. `route_critical.py`'s matrix
  links now reach the diode at 8.5 mm: the row via sits 1.55 mm west of the cathode and the F.Cu row
  line runs at the diode's height, under the LED cutout. Each locked link is checked against pads,
  holes, keepouts, the LED cutouts and the outline (0.5 mm); one that is not clear (next to a mounting
  hole: one switch link and one row run per half) is left to Freerouting instead of failing.
  KiCad exports the LED cutouts to the DSN as keepouts, and Freerouting keeps only its 0.2 mm track
  clearance from a keepout (not its 0.5 mm copper-to-edge setting): its wires came within 0.003 mm of
  a cutout. `export_dsn.py` grows each LED keepout by 0.11 mm, so its copper stays 0.31 mm from the
  cutout while the LED pads (0.348 mm) stay clear of it. `complete_routes.py` and the GND stitching
  (`import_ses.py`) keep 0.3 mm from the cutouts too.
- **Checks:** `netcmp.py` "per-key RGB chain" (GP22 -> U7 -> R16 -> LED101, each DOUT net shared only
  with the next DIN, the chain in `layout.leds` order, VLED from U6 OUT to exactly the LEDs, their
  caps, C20, C22 and U7, U6 EN with its pull-down, 15k ISET; mutation-tested). `checks.py` "per-key
  RGB" (each LED on B.Cu at its window with its cutout, turned along the chain, its cap within 8 mm
  of VLED copper of the VDD pad). Layout tests: chain, mirror, LED and diode clear of the switch holes.
- **JLC placement:** JLC's footprint of C100024 has pin 1 in the other corner from the SOT-23-5 row
  of `jlc_rotations.csv` (AP2112K, SY6280): U7 carries a `JLCPCB_CORRECTION` field `0;0;180`, which
  KiKit uses before the pattern file. The LEDs need no row. `cpl_check.py` gates the reverse-mount LED
  at 55 % of each terminal on its pad (`LEAD_AREA_MIN_BY`): JLC's leads run x 1.55–2.94, the first
  0.15 mm over the cutout, so no pad holds 75 %; KiCad's stock pads hold 64 %, ours 57 %, 0.79 mm of
  the lead on the pad and 0.56 mm of pad past its toe. The lead centre must still be on the pad.
- **Firmware** (`docs/firmware.md`): WS2812 driver on PIO0, GP22, 37 LEDs, GRB; ext-power on GP23;
  brightness capped at 8 % with a 1 % floor (full white about 107 mA per half, 129 mA worst case, plus
  22 mA of dark LEDs and ~30 mA of logic: ~181 mA, 72 % of F1's 250 mA hold), the USB descriptor at
  500 mA bus powered, `reset-delay` 500 µs. The right half now keeps its own RGB
  settings.

### REVB-2. The display moves 1.0 mm back from the C6R1 key well (§4; pre-order review)

- **Problem:** the module's far end lay on the old C6R0 cell boundary (y 74.625), 0.6 mm into the open
  C6R1 key well (well clearance 0.6 mm), so the C6R1 keycap had only 0.12–0.30 mm at bottom-out.
- **Change** (`layout/display.py` `SETBACK = 1.0`): the module, J3 header (now y 38.925), window and the
  pocket's back end move 1.0 mm towards the back edge. A 36.0 mm module ends 0.3975 mm short of the
  well; the nice!view is 36 mm plus 0.1–0.2 mm of V-cut, so about 0.2–0.3 mm
  (`test_display_clears_c6r1_well`). The pocket's far end stays at y 75.125, 1.1 mm into the well: its
  two far corners must lie a cutter radius inside the well (CASE-8), so the setback only shortens the
  module inside the pocket. `just model` passes (pocket y 37.125–75.125, window 2.92 mm from the well).

### REVB-3. Review notes: C1–C3 0603, plug-in capacitance, flash size, RP2350 stepping (§6, §7, §13)

- **C1–C3** become 10 µF 0603 10 V X5R (C19702, JLC basic) from 0402 6.3 V (C15525, now in
  `design.RETIRED`): at the ~5 V of VSYS the 0402 kept only about 2–3 µF. C2, at U4's VSYS via
  (BOARD-5), moves 0.295 mm further out (`place.U4_CAP_Y` -3.695) so the longer 0603 pad 1 sits where the
  0402's did: at the old spot the VSYS via landed 0.125 mm inside it (`checks.py` "no via in an SMD
  pad"). The left half's U7, C22 and R16 moved (`PLACE_L`) to clear the larger C2.
- **Plug-in capacitance:** about 40 µF nominal directly on VSYS across both halves, above USB's 10 µF;
  documented, not changed (almost every host copes). The rev B VLED capacitance sits behind U6.
- **Flash:** the firmware declares 4 MB of the 16 MB part; documented as safe.
- **RP2350:** a future RP2350 board needs the A4 stepping (erratum E9, internal pull-downs).

### REVB-4. A PCBWay order package beside the JLC one (`pcb/scripts/pcbway.py`, `mpn.py`, `mpn.json`)

- **Problem:** the JLC CPL carries JLC-only corrections (`jlc_rotations.csv`, per-part
  `JLCPCB_CORRECTION`) and JLC's bottom-side convention; uploaded to PCBWay it misplaces the sockets by
  3.9 mm, J3 by 5.1 mm and turns U2–U5. PCBWay also wants manufacturer part numbers.
- **Change:** stage P step P6 writes `pcb/production/<side>/pcbway/` (MPN BOM, KiCad-native centroids
  for the panel and the bare board, README with the form values and a remark), byte-checked in CI.
  `pcbway.py` fails unless re-applying the JLC corrections (the per-part field first, as KiKit does)
  to its centroids reproduces the JLC CPL. `mpn.json` maps every LCSC number to its manufacturer part
  number (LCSC, 2026-11-07); `mpn.py check` fails offline if one is missing. Guide:
  [ordering-pcbway.md](ordering-pcbway.md).

### REVB-5. JLC's footprint record for the TRRS jack C95562 is kept as verified

- **Problem:** re-fetching `jlc_footprints.json` for the rev B parts returned a different record for
  C95562 (`AUDIO-SMD_PJ-320D-4A`, dated 2021-10-18) than the one rev A's J2 correction and its CPL
  proof were built on (`AUDIO-SMD_PJ-320D`, 2025-06-19).
- **Change:** the committed 2025-06-19 record stays; only the six rev B parts were added and the
  retired C15525 dropped. The placement confirmation at order time is the backstop for J2, as for every
  part (the README's checklist names J2).

### REVB-6. Independent review before ordering (2026-11-07)

A fresh-context review of the whole rev B change set (circuit against the SK6812MINI-E, SY6280AAC and
SN74LV1T34 datasheets; LED geometry from the boards' real switch-pin holes; KiKit and `cpl_check` run on
copies of both boards; the firmware's built configs and devicetree) found no blocker. Its findings and
what was done:

- **MAJOR, fixed (firmware):** at the first cap, 12 %, full white plus the dark LEDs plus the RP2040,
  flash and display reached ~245 mA worst case on the cable-fed right half, 98 % of F1's 250 mA hold,
  which falls when warm. The cap is now 8 % (~181 mA, 72 %) with `BRT_MIN = 1` so the LEDs still boot
  lit; `fw_check` enforces 8.
- **MINOR, fixed (firmware):** the USB descriptor declared Zephyr's 100 mA, self powered; it now declares
  500 mA, bus powered on every USB build (`fw_check` enforces it).
- **MINOR, fixed (docs):** "raise the cap to 30 %" could hold U6 in its current limit (0.45 A ±25 %) and
  over its 0.6 W; the docs now say 20 % at most.
- **MINOR, fixed (board):** U6's input cap is now 10 µF 0603 (the datasheet's strong recommendation),
  not 1 µF.
- **MINOR, fixed (docs):** rev A leftovers; the generated pages are regenerated from the final boards.
- **NOTE, fixed:** `reset-delay` 500 µs (the driver sleeps from the last queued word, not the last sent).
- **NOTE, fixed (comment):** the SN74LV1T34 datasheet specifies no Ioff; driving its input with VLED off
  is still safe (no positive input clamp, 5.5 V tolerant input, U6 discharges VLED).
- **NOTE, fixed (docs):** the display clears the well by about 0.2–0.3 mm with the nice!view's V-cut, not
  0.4 mm.
- **NOTE, documented:** a weak bus-powered hub can leave the cable-fed right half's LEDs at their 3.7 V
  minimum; the RP2350 target saves no RGB state (known).

### REVB-7. Two board-check rules adjusted for the rev B boards (`checks.py`, `place.py` `DRU`)

- **U1's main B.Cu GND plane.** `checks.py` asked that U1's exposed pad reach *the largest* filled B.Cu
  GND island within 8 mm. Rev A had one 14 623 mm² B.Cu plane; rev B's B.Cu LED routing splits the pour
  into large islands (right half, seed 1: 4 334 and 3 254 mm², U1 on the second), each stitched to the
  F.Cu plane, so the check read "inf" on a sound board. `main_plane()` now takes every B.Cu GND island of
  at least `MAIN_PLANE_MIN_MM2` (2 000 mm²); U1 still has to reach one within 8 mm. The other U1 ground
  gates (cap returns, two or more separate links 24 mm out, U4 and C5 paths) are unchanged.
- **LED-cutout DRC tolerance.** The routers keep 0.3 mm from the LED cutouts (`LED_EDGE_CLEARANCE`), but
  the cutout arcs are polygons in the DSN and in the completion grids: a VLED track landed 0.298 mm from
  LED133's cutout. The `.kicad_dru` rule is now 0.29 mm (`LED_EDGE_DRC_TOL` 0.01). Routing is unchanged.
- **Left U7 cluster moved.** With U7, R16 and C22 south of U4 and C2 (where the larger 0603 C2 had pushed
  them), the left half's GND pour there was cut: in three of five seeds `gnd_ties.py` could not join U4's
  clamp GND (pin 2) to J1's GND (ORDER-4's gate) and stage C stopped. They now sit west of D1 beside U6
  (`PLACE_L`: U7 (65.6, 49.0, 180), R16 (63.65, 46.64), C22 (63.51, 51.31)), leaving the J1/U4 area to the
  pour as in rev A. The right half's cluster is not between its J1/U4 and the plane and passed (10.3 mm).
- **Seeds.** As in rev A (WS2c-4, BOARD-2), each half's `KIID_SEED` is one whose seeded rebuild routes to
  0 unconnected and passes every stage C gate: the right half keeps 0x1; the left half's is recorded with
  the final boards. On 2026-11-08 the moved U7 placement was routed. Seed 0x1 (`leftB-1`) reached DRC
  0/0/0 with U4 pin 2 to J1 GND at 13.2 mm, then failed: one U1 ground link of the two required, and no
  copper path from C5 to U2 pin 4. Seeds 0x2–0x5 of that placement did not finish stage C (the machine
  went down at 05:20). The left seed is still unset.

