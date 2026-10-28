# Firmware

worxboard runs [ZMK](https://zmk.dev) as a custom HWMv2 board (`worxbend/worxboard`) with an
on-board RP2040 per half and ZMK's **wired split** over the TRRS cable. The firmware lives in
[`firmware/zmk/`](../firmware/), with `zephyr/module.yml` and `build.yaml` at the repo root, so
ZMK's `build-user-config.yml` workflow can build it directly (spec §11).

> [!NOTE]
> **In progress (WS1).** ZMK is pinned in `firmware/zmk/config/west.yml` to `main` @
> `4dd95d7840eb3d5a3f59bb29fbf1ab054715ef85` (Zephyr `v4.1.0+zmk-fixes`). The firmware workflow and
> `just fw` build every `build.yaml` row with the same script, `firmware/zmk/scripts/fw_build.py`.
> CI mirrors ZMK's `build-user-config.yml` instead of calling it (deviation WS1-1).

## Builds

| Artifact | Board | Role | Status |
|---|---|---|---|
| `worxboard_left_central` | `worxboard_left//zmk` | central, enumerates on USB, ZMK Studio on | **core** |
| `worxboard_right_peripheral` | `worxboard_right//zmk` | peripheral; USB gives power and flashing only | **core** |
| `worxboard_right_central_EXPERIMENTAL` | `worxboard_right//zmk` | right half as the central (host on the right) | untested on hardware |
| `worxboard_left_peripheral_EXPERIMENTAL` | `worxboard_left//zmk` | left half as the peripheral (pair with the one above) | untested on hardware |
| `worxboard2_left_EXPERIMENTAL`, `worxboard2_right_EXPERIMENTAL` | `worxboard2_*/rp2350a/m33/zmk` | RP2350A target for a future rev B; no hardware | firmware only |

A row stays in `build.yaml` only if `just fw` builds it locally. A row that fails is removed and
listed under [future work](#future-work).

## Get the firmware

- **CI**: every push runs the [firmware workflow](https://github.com/w0rxbend/worxboard/actions/workflows/firmware.yml).
  Download the `worxboard-firmware` artifact; it holds one `.uf2` per row.
- **Release**: tagged releases attach the same `.uf2` files.
- **Locally**: `just fw` builds every row (or `just fw <artifact>…` the named ones) in Docker
  (`zmkfirmware/zmk-build-arm:stable`) into `build/fw/`. The west workspace lives in `build/fw-ws/`,
  outside the source tree (deviation WS1-2); `just fw-west` refreshes it only when `west.yml` changes.
- **Checks**: `just fw-keymap-check` (3 layers × 74 bindings, base layer equals the `layout.json`
  legends), `just fw-layouts-check` (generated dtsi up to date) and `just fw-check` (no BLE symbols in
  the right peripheral, flash growth within budget).

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
| 1 Symbols / F-keys | EZ layer 1, plus LEFT and RIGHT on the old inner-top functions |
| 2 Media / mouse | Media and mouse keys, `&bootloader`, `&sys_reset` and `&studio_unlock` |

The keymap is `firmware/zmk/config/worxboard.keymap`; the board-folder keymaps `#include` it, so
there is one keymap (deviation WS1-5). QMK keys without a ZMK equivalent are mapped as follows:
`TT(1)` is a hold-tap (`&mo` / `&tog`), `HYPER` and `MEH` are held modifier combos, and the QMK
version, EEPROM and RGB keys are transparent. LEFT and RIGHT sit on layer 1 at the inner 1.5u
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
| `worxboard.dtsi` | Shared hardware: the `col2row` kscan matrix (rows GP8–GP13 with pull-downs, columns GP14–GP20), UART0 at 115 200 baud with `zmk,wired-split`, the display on PIO1 SPI, USB, flash partitions |
| `worxboard-layouts.dtsi` | **Generated**: the 6×14 transform and the physical layout |
| `worxboard_left_rp2040_zmk.dts` | Left half: the shared definition as is |
| `worxboard_right_rp2040_zmk.dts` | Right half: `col-gpios` reversed (GP20…GP14) and `col-offset = <7>`, so both PCBs share one matrix netlist |
| `Kconfig.defconfig` | `ZMK_SPLIT` on, `ZMK_SPLIT_ROLE_CENTRAL` on the left, the W25Q flash boot stage, LVGL/ls0xx defaults, the custom status screen on the right |
| `worxboard.zmk.yml` | ZMK metadata: features keys, display and studio |

## Displays

Both halves drive a Sharp LS011B7DH03 memory LCD (nice!view-compatible, 160 × 68) with the ZMK
`sharp,ls0xx` driver over a PIO SPI master (`raspberrypi,pico-spi-pio`; the RP2040 PL022 SPI cannot
send LSB-first). The stock `nice_view` shield is not used, because it does not build on RP2040.

- **Left**: the ZMK built-in status screen (active layer, output).
- **Right**: a custom LVGL screen (`firmware/zmk/src/worx_status_screen.c`) with a `worxboard` logo,
  the Caps / Num / Scroll lock indicators (forwarded from the central; HID indicators are on for
  both halves, deviation WS1-4) and a static `wired` label. It uses
  no Bluetooth or battery symbols.

## Future work

- RP2350A hardware (rev B, needs the A4 stepping).
- TRRS detect on GP21 (`detect-gpios`), and runtime role swap.
- RGB on GP22, encoders, a TFT display on TP1–TP3.
- Rows removed from `build.yaml` because they did not build locally are listed here by WS1.
