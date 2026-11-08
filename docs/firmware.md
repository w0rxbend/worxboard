# Firmware

worxboard runs [ZMK](https://zmk.dev) as a custom HWMv2 board (`worxbend/worxboard`) with an
on-board RP2040 per half and ZMK's **wired split** over the TRRS cable. The firmware lives in
[`firmware/zmk/`](../firmware/), with `zephyr/module.yml` and `build.yaml` at the repo root, so
ZMK's `build-user-config.yml` workflow can build it directly (spec §11).

> [!NOTE]
> **Built, not yet tested on hardware.** ZMK is pinned in `firmware/zmk/config/west.yml` to `main` @
> `4dd95d7840eb3d5a3f59bb29fbf1ab054715ef85` (Zephyr `v4.1.0+zmk-fixes`). All six `build.yaml` rows
> build, locally with `just fw` and in the [firmware workflow](https://github.com/w0rxbend/worxboard/actions/workflows/firmware.yml),
> with the same script, `firmware/zmk/scripts/fw_build.py`. CI mirrors ZMK's `build-user-config.yml`
> instead of calling it (deviation WS1-1). See [known issues](#known-issues) before flashing a real board.

## Builds

| Artifact | Board | Role | Status |
|---|---|---|---|
| `worxboard_left_central` | `worxboard_left//zmk` | central, enumerates on USB, ZMK Studio on | **core** |
| `worxboard_right_peripheral` | `worxboard_right//zmk` | peripheral; USB gives power and flashing only | **core** |
| `worxboard_right_central_EXPERIMENTAL` | `worxboard_right//zmk` | right half as the central (host on the right) | untested on hardware |
| `worxboard_left_peripheral_EXPERIMENTAL` | `worxboard_left//zmk` | left half as the peripheral (pair with the one above) | untested on hardware |
| `worxboard2_left_EXPERIMENTAL`, `worxboard2_right_EXPERIMENTAL` | `worxboard2_*/rp2350a/m33/zmk` | RP2350A target for a later revision; no hardware | firmware only |

A row stays in `build.yaml` only if `just fw` builds it locally. A row that fails is removed and
listed under [future work](#future-work). No row has been removed: all six build.

## Get the firmware

- **CI**: every push runs the [firmware workflow](https://github.com/w0rxbend/worxboard/actions/workflows/firmware.yml).
  Download the `worxboard-firmware` artifact from a green run; it holds one `<artifact>.uf2` per row
  (six files, under 1 MB zipped). The workflow also checks the layout dtsi, the keymap and the right
  peripheral (see below), and that the checked-out ZMK matches the pin.
- **Release**: tagged `v*-revA` releases will attach the same `.uf2` files (`release.yml`; no tag
  exists yet).
- **Locally**: `just fw` builds every row (or `just fw <artifact>…` the named ones) in Docker
  (`zmkfirmware/zmk-build-arm:stable`) into `build/fw/`. The west workspace lives in `build/fw-ws/`,
  outside the source tree (deviation WS1-2); `just fw-west` refreshes it only when `west.yml` changes.
- **Checks**:
  - `just fw-keymap-check`: 3 layers × 74 bindings, and the base layer equals the `layout.json`
    legends.
  - `just fw-layouts-check`: the generated dtsi is up to date.
  - `just fw-rotate-check`: a host test of the display's portrait-to-panel pixel map
    (`firmware/zmk/tests/rotate_test.c`).
  - `just fw-check-tests`: regression tests of the post-build gate, including both supported display
    orientations (90° and 270°), rejection of missing rotation code, and rejection of a build
    without the LED strip, the VLED switch or the brightness cap.
  - `just fw-check`, on both core rows: exactly one supported display rotation is configured and
    the rotating flush is linked; the [RGB](#rgb) strip (37 GRB LEDs on PIO0, GP22), the VLED
    ext-power switch (GP23), idle-off and `BRT_MAX` ≤ 12 are configured, and the strip, ext-power and
    `rgb_ug` code are linked. On the right peripheral it also checks that the custom screen
    and its 8 KB LVGL heap are in, that
    there are no `zmk_ble_` or battery symbols, and that flash use is at most 40 KB above the seed
    build.

  `just fw` runs all five; CI runs `fw-check` in both core jobs. `just fw-clean` removes `build/fw/`
  and keeps the west workspace.

## Flash

1. Enter the bootloader, so the **`RPI-RP2`** drive appears:
   - a new board with empty flash does this by itself;
   - otherwise **double-tap RESET**, or **hold BOOT, tap RESET, release BOOT**;
   - from a running keyboard, `&bootloader` on layer 2.
2. Drag the `.uf2` onto `RPI-RP2`. The board restarts when the copy finishes.
3. Flash **both** halves: `worxboard_left_central.uf2` on the left and
   `worxboard_right_peripheral.uf2` on the right.

The right half can be flashed through its own USB-C. With the host on the left, the right USB-C
only supplies power.

## Host behaviour

- **Plug the host into the LEFT half.** Only the central enumerates as a keyboard.
- The right USB-C gives power (it can run both halves) and UF2 flashing.
- **Never hot-plug the TRRS cable.** Unplug USB from both halves first.
- The `*_EXPERIMENTAL` role-swap pair lets the host be on the right instead. It is untested on
  hardware.

## Keymap

Three layers, 74 bindings each, in the keymap order of [matrix.md](matrix.md#keymap-order):

| Layer | Contents |
|---|---|
| 0 Base | The QMK `ergodox_ez` default layer 0 ([matrix.md](matrix.md) shows every legend). The two inner top keys of the EZ (LEFT/RGHT on layer 0) are where the displays are, so their functions move to layer 1. |
| 1 Symbols / F-keys | EZ layer 1 with its RGB keys on the thumbs ([RGB](#controls)), plus LEFT and RIGHT on the old inner-top functions |
| 2 Media / mouse | Media and mouse keys, `&bootloader`, `&sys_reset` and `&studio_unlock` |

The keymap is `firmware/zmk/config/worxboard.keymap`; the board-folder keymaps `#include` it, so
there is one keymap (deviation WS1-5). QMK keys without a ZMK equivalent are mapped as follows:
`TT(1)` is a hold-tap (`&mo` / `&tog`), `HYPER` and `MEH` are held modifier combos, the QMK
version and EEPROM keys are transparent, and the RGB keys drive ZMK underglow (`RGB_SLD` selects the
solid effect). LEFT and RIGHT sit on layer 1 at the inner 1.5u
`HYPER` / `MEH` positions. **ZMK Studio** is enabled on the left
central build over USB: unlock it with `&studio_unlock`, then edit the keymap live in the
[Studio web app](https://zmk.studio).

### Physical layout

`firmware/zmk/scripts/gen_layouts.py` (`just fw-layouts`) writes `worxboard-layouts.dtsi` from
`layout/build/layout.json`: the physical layout (100 units = 19.05 mm; the thumbs rotate ±25° about
their own centres) **and** the 6 × 14 matrix transform (deviation WS1-3), so the transform, the
physical layout and the keymap order cannot drift. CI regenerates it and fails on any diff.

## Board definition

| File | Purpose |
|---|---|
| `worxboard.dtsi` | Shared hardware: the `col2row` kscan matrix (rows GP8–GP13 with pull-downs, columns GP14–GP20), UART0 at 115 200 baud with `zmk,wired-split`, the display on PIO1 SPI, the [RGB](#rgb) strip on PIO0 and its VLED ext-power switch, USB, flash partitions, and `&xosc` `startup-delay-multiplier = <64>` (about 64 ms) for the rev A crystal (deviation WS1-9) |
| `worxboard-layouts.dtsi` | **Generated**: the 6×14 transform and the physical layout |
| `worxboard_left_rp2040_zmk.dts` | Left half: the shared definition as is |
| `worxboard_right_rp2040_zmk.dts` | Right half: `col-gpios` reversed (GP20…GP14) and `col-offset = <7>`, so both PCBs share one matrix netlist |
| `Kconfig.defconfig` | `ZMK_SPLIT` on, `ZMK_SPLIT_ROLE_CENTRAL` on the left, the W25Q flash boot stage, LVGL/ls0xx defaults, HID indicators forwarded on both halves (deviation WS1-4), the custom status screen on the right with an 8192 B LVGL heap (`LV_Z_MEM_POOL_SIZE`; the left built-in screen keeps ZMK's 4096 B; WS1-8), RGB underglow with idle-off, and settings on both halves |
| `*_defconfig` | RP2040 SoC, USB on the left only (`CONFIG_ZMK_USB` is not set on the right), the RGB brightness cap |
| `worxboard.zmk.yml` | ZMK metadata: features keys, display, underglow and studio |

The module root is [`zephyr/module.yml`](../zephyr/module.yml): it points cmake, Kconfig and
`board_root` at `firmware/zmk`. Its [`Kconfig`](../firmware/zmk/Kconfig) adds:

- `WORXBOARD_STATUS_SCREEN`, on when the custom screen is chosen on a right board;
- the choice `WORXBOARD_DISPLAY_ROTATION`: `_90` (the default, the rev A mounting) or `_270`
  (a 180° flip, the stock nice!view orientation).

Its `CMakeLists.txt` compiles `src/worx_status_screen.c` and `src/worx_display_rotation.c` when
those are on. `worxboard2/` is the experimental
RP2350A copy and includes the same generated layouts file.

## Displays

Both halves drive a Sharp LS011B7DH03 memory LCD (nice!view-compatible, 160 × 68) with the ZMK
`sharp,ls0xx` driver over a PIO SPI master (`raspberrypi,pico-spi-pio`; the RP2040 PL022 SPI cannot
send LSB-first). The stock `nice_view` shield is not used, because it does not build on RP2040.
The display is write-only, but the PIO driver still muxes a MISO pin in 4-wire mode, and without
`miso-gpios` it picks GP0, the split UART's TX. The node therefore names MOSI (GP3) as its MISO, as
ZMK's own pico-spi-pio examples do (deviation REVIEW-FIX-1).

The module stands in J3 LCD up, its header at the back of the board, the same way on both halves
(BOARD-1). LVGL therefore lays out a **68 × 160 portrait** screen, and
`src/worx_display_rotation.c` turns it onto the 160 × 68 panel with `LV_DISPLAY_ROTATION_90`:
portrait (u, v) goes to panel (v, 67 − u). Zephyr's LVGL glue cannot rotate, so after `lvgl_init()`
(SYS_INIT 91 > 90) it replaces the mono flush and rounder: each area is turned into a panel-ordered
shadow, and the lines it touches go, full width, through Zephyr's own `lvgl_flush_cb_mono()` to the
ls0xx driver. The pixel map is `src/worx_rotate.h` (deviation WS1-7).

- **Left**: the ZMK built-in status screen, portrait: USB at the top, the active layer at the bottom.
- **Right**: a custom LVGL screen (`firmware/zmk/src/worx_status_screen.c`), portrait:
  - `worx/board`;
  - a column of the Caps / Num / Scroll lock indicators, a lit one shown in upper case in a 2 px
    frame (forwarded from the central; HID indicators are on for both halves, deviation WS1-4);
  - a static `wired` label.

  It sets its own opaque paper and ink, like the left's mono theme, and runs on an 8 KB LVGL heap
  (WS1-8). It uses no Bluetooth or battery symbols (`just fw-check` checks the link map).

## RGB

Rev B puts an SK6812MINI-E under every key: one chain of 37 per half. LED101 is the first key of
`CHAIN` in [`layout/leds.py`](../layout/leds.py), a serpentine through the rows and then the thumbs,
the same on both PCBs. ZMK drives each chain as an **underglow** strip: effects run along the chain.
At the pinned revision the underglow is ZMK's only LED-strip user, so there are no per-key or
per-layer colours (ZMK's `zmk,indicator-leds` lock indicators need plain LEDs, not a strip).

### Wiring contract

From [`layout/pins.py`](../layout/pins.py). Both halves use the same nodes in `worxboard.dtsi`:

| Net | GPIO | Hardware | Firmware |
|---|---|---|---|
| `RGB_DIN` | GP22 | U7 SN74LV1T34 buffer (non-inverting, on VLED), 470 Ω, LED101 DIN | `worldsemi,ws2812-rpi_pico-pio` on **PIO0** (PIO1 is the display); `chosen { zmk,underglow = &led_strip; }` |
| `RGB_EN` | GP23 | U6 SY6280AAC load switch, VSYS → VLED, active high, 10k pull-down, limit about 0.45 A | `zmk,ext-power-generic` node `vled`, `control-gpios = <&gpio0 23 GPIO_ACTIVE_HIGH>` |

- **Strip**: `chain-length = <37>`, GRB `color-mapping`, `frequency = <800000>`, and
  `reset-delay = <500>` µs: the LEDs need more than 200 µs low between frames, and Zephyr's driver
  starts that sleep when the last word is queued, up to about 270 µs before it has been sent. The PIO node sets
  `bit-waveform = <3>, <3>, <4>`, 10 PIO cycles per bit: T0H 375 ns, T1H 750 ns, as Zephyr's own
  RP2040 boards. `pio0_ws2812_default` muxes GP22 to PIO0.
- **PIO0 holds only the strip.** The Zephyr driver loads its 4-instruction program at the top of
  an empty PIO and starts at instruction 31, so it cannot share PIO0 with another program.
- **VLED** is off until the firmware drives GP23. ZMK's ext-power driver switches it on at boot, and
  the underglow switches it with the LEDs (`CONFIG_ZMK_RGB_UNDERGLOW_EXT_POWER`, a ZMK default):
  toggle-off and idle-off cut VLED, and on restores it.

### Controls

On layer 1 (Sym), at the thumb positions where the EZ's layer 1 has its RGB keys:

| Layer 1 key (base key at that position) | Binding | Action |
|---|---|---|
| `ALT_T(APP)` | `&rgb_ug RGB_EFF` | next effect: solid, breathe, spectrum, swirl (EZ `RGB_MOD`) |
| `LALT` (right) | `&rgb_ug RGB_TOG` | on / off, VLED with it |
| `CTL_T(ESC)` | `&rgb_ug RGB_SLD` (`RGB_EFS_CMD 0`) | solid effect (EZ `RGB_SLD`) |
| `SPC` / `BSPC` | `&rgb_ug RGB_BRD` / `RGB_BRI` | brightness down / up, in steps of 10 |
| `TAB` / `ENT` | `&rgb_ug RGB_HUD` / `RGB_HUI` | hue −/+ 10° |

Saturation and speed have no keys; ZMK Studio can bind them. The LEDs start red (hue 0, saturation
100), solid, at `BRT_START`.

### Brightness cap

With one USB-C cable on the left, the left port (500 mA) feeds both halves, and the right half's
RP2040, display and LEDs run over the TRRS cable through F1 (250 mA hold,
[electrical.md](electrical.md#power-path)). One SK6812MINI-E draws about 12 mA per colour at full
duty (36 mA white) and 0.6 mA when dark. So the boards cap the LEDs:

| Option | Value | Why |
|---|---|---|
| `CONFIG_ZMK_RGB_UNDERGLOW_BRT_MAX` | 8 (`*_defconfig`) | ZMK scales brightness 0–100 onto `BRT_MIN`–`BRT_MAX` % duty, in every effect (`rgb_underglow.c` `hsb_scale_min_max` / `_zero_max`). Full white is 37 × 36 mA × 8 % ≈ 107 mA (129 mA at the datasheet's 14.5 mA per colour), plus 22 mA for 37 dark LEDs and ~30 mA for the RP2040, flash and display: at most ~181 mA per half, about 72 % of F1's 250 mA hold. The first rev B setting, 12 %, reached ~245 mA worst case, 98 % of it (independent review) |
| `CONFIG_ZMK_RGB_UNDERGLOW_BRT_MIN` | 1 (`*_defconfig`) | Keeps the LEDs visibly lit at the lowest step: ZMK limits `BRT_START` to `BRT_MAX` on the 0–100 scale, and without a floor its integer maths turns a start of 8 into 0 % (on but dark) |
| `CONFIG_ZMK_RGB_UNDERGLOW_BRT_START` | 8 (`*_defconfig`) | 1 + 7 × 8 / 100 → 1 % duty at boot; each brightness step (10) adds about 0.7 % up to 8 % |
| `CONFIG_ZMK_RGB_UNDERGLOW_AUTO_OFF_IDLE` | y (`Kconfig.defconfig`) | After 30 s without a key press (`ZMK_IDLE_TIMEOUT`) the strip goes dark and VLED switches off |
| `CONFIG_ZMK_RGB_UNDERGLOW_ON_START` | y (ZMK default) | ext-power switches VLED on at boot anyway, so the LEDs start on with it |

The cap is a `*_defconfig` setting, not a `Kconfig.defconfig` default: ZMK's `Kconfig.defaults` gives
`BRT_MAX` its default (100) before the board file is read, and the first default wins.
`just fw-check` fails any core build whose `BRT_MAX` is above 8, and any USB build whose descriptor
does not declare 500 mA, bus powered: `Kconfig.defconfig` sets `USB_MAX_POWER=250` (2 mA units) and turns
`USB_SELF_POWERED` off, so a host that budgets power by descriptor grants what the LEDs draw (Zephyr's
defaults are 100 mA and self powered).

### Raising the cap (split-power mode only)

Raise the cap **only** when each half has its own USB-C cable and JP1 is cut on **both** halves
([build guide](buildguide_en.md#3-choose-the-power-mode-jp1)): then no LED current crosses the TRRS
cable or F1. Set it in `firmware/zmk/config/worxboard.conf` (for the `worxboard2` rows, in their
`*_defconfig`):

```
CONFIG_ZMK_RGB_UNDERGLOW_BRT_MAX=20
```

Do not go above 20: full white is then 37 × 36 mA × 20 % ≈ 270 mA (320 mA at 14.5 mA per colour) plus
22 mA. U6's current limit is 6800 / 15k = 0.45 A **±25 %**, so it can be as low as 0.34 A; above it U6
limits VLED (the LEDs brown out) and, at (4.6 − 3) V × 0.45 A ≈ 0.7 W, over its 0.6 W rating, cycles on
thermal shutdown. 20 % also keeps the half inside a 500 mA port with the RP2040 and display. CI and
`just fw-check` reject a raised cap on purpose, so it is a local build:
`just fw worxboard_left_central worxboard_right_peripheral` (named rows skip `fw-check`).

### Split behaviour

Verified in the pinned ZMK source (`zmk/app/` in `build/fw-ws/`), not yet on hardware:

- **The right half follows the left over the wired split.** `&rgb_ug` has
  `BEHAVIOR_LOCALITY_GLOBAL` (`src/behaviors/behavior_rgb_underglow.c:260`). For a global behaviour
  the central calls `zmk_split_central_invoke_behavior()` for each peripheral and then runs it
  locally (`src/behavior.c:106-112`; with only the wired split there is one peripheral,
  `include/zmk/split/central.h:23-29`). That call goes to the active transport's `send_command`
  (`src/split/central.c:81-111`), and the wired transport sends the
  `ZMK_SPLIT_TRANSPORT_CENTRAL_CMD_TYPE_INVOKE_BEHAVIOR` frame over the UART
  (`src/split/wired/central.c:178-235`). The wired peripheral queues it
  (`src/split/wired/peripheral.c:423-456`) and the shared handler presses `rgb_ug` on the right
  (`src/split/peripheral.c:38-59`). No step needs BLE. `just fw-check` checks that the `rgb_ug`
  behaviour is linked into the right build.
- **The left's state decides.** Before relaying, the central turns relative commands into absolute
  ones from its own state (`behavior_rgb_underglow.c:134-208`): toggle becomes on or off, brightness
  and hue steps become an absolute colour, next effect becomes "effect n". Any press re-syncs the
  right half; if the halves ever disagree, one or two presses of the toggle bring them back in step.
- **Each half animates on its own** 50 ms timer, so breathe, spectrum and swirl are not frame-locked
  across the halves.
- **Each half idles on its own key presses**: on a peripheral, `src/activity.c:110-111` sees only
  local key and sensor events. Type only on the left and the right goes dark after 30 s; it lights
  again at its next key press.
- **Both halves keep their RGB state.** In ZMK only Studio and BLE turn on Zephyr settings, so the
  wired right half had none and would boot lit at `BRT_START` whatever the left restored. The boards
  default `SETTINGS` on with RGB (`Kconfig.defconfig`), so each half saves its own state. ZMK saves
  on/off and the effect when they change; a brightness or colour change is saved with the next save,
  because `zmk_rgb_underglow_set_hsb()`, which the relayed absolute colour uses, does not save
  (`src/rgb_underglow.c:377-385`).
- **Idle-off is saved too.** ZMK's idle-off goes through the normal off path, which saves after a
  60 s debounce. A keyboard left idle for more than about 90 s before it is unplugged boots dark;
  press the toggle.

## Known issues

- **Nothing has run on hardware yet**: the displays, the wired split, the forwarded lock indicators,
  the RGB chain (its timing through U7, VLED switching, the real current at the cap, the relayed
  commands) and the `*_EXPERIMENTAL` role-swap pair are untested.
- **Settings writes lock interrupts.** The RP2040 flash driver locks interrupts while it programs or
  erases (`zephyr/drivers/flash/flash_rpi_pico.c:227,277`). With RGB, each half writes settings about
  a minute after an RGB change or an idle transition. Whether a write can drop a frame on the
  115 200 baud split UART is unmeasured.
- **Display orientation is not checked on hardware.** Which panel end is pixel x = 0 comes from
  ZMK's nice_view widgets and the vendor's product images; no Sharp LS011B7DH03 datasheet was found.
  If the first board shows both screens upside down, set
  `CONFIG_WORXBOARD_DISPLAY_ROTATION_270=y` in `firmware/zmk/config/worxboard.conf` (the
  `worxboard2` rows would need it in their defconfigs).
- **LVGL heap on hardware.** Measured on a 64-bit host, the right screen peaks at about 5.2 KB of
  its 8 KB heap. The left built-in screen peaks at about 4.7 KB against ZMK's 4 KB default: the
  default every nice!view built-in screen runs with in ZMK. Pointers are half that size on the
  32-bit RP2040, so both should need less there, but nobody has measured it.
- **worxboard2 (RP2350A)**: Zephyr forces `FLASH_PAGE_LAYOUT`, `NVS` and `FLASH_MAP` off for this
  target at the pinned revision, so keymap edits from ZMK Studio and the RGB state would not persist
  there. The seed build had the same warnings; the target is experimental and has no hardware.
- The board-folder `worxboard.conf` files are not read when `ZMK_CONFIG` is set (they document the
  defaults only); the options that count are in `firmware/zmk/config/worxboard.conf`.
- The build image is the floating `zmkfirmware/zmk-build-arm:stable` tag, as in ZMK's own
  `build-user-config.yml`; the ZMK source itself is pinned.

## Future work

- RP2350A hardware on a later revision (needs the A4 stepping, erratum E9).
- TRRS detect on GP21 (`detect-gpios`), and runtime role swap.
- Encoders, a TFT display on TP1–TP3.
- Per-key RGB effects (layer or lock colours): ZMK at the pin has only the underglow strip.
- No `build.yaml` row has been removed so far; any row that stops building is listed here.
