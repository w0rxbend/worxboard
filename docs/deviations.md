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
