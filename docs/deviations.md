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
  fails on any assembled part without an LCSC field. `stage_d.sh` then fails if any of JP1, J3,
  TP*, H* or STAB_* appears in `bom.csv` or `pos.csv`.

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
