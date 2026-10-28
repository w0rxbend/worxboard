# worxboard rev A build guide

This guide follows the [Corne (crkbd) build guides](https://github.com/foostan/crkbd/tree/main/docs):
check the parts, test the bare boards, then build up from the PCB. JLCPCB assembles every SMD part,
including the RP2040, the USB-C and TRRS connectors, the hot-swap sockets and the diodes. You only
hand-solder the display socket.

> [!IMPORTANT]
> Rev A has **not been built yet**. Gates G1–G3 in [bom.md](bom.md#gates) must pass before you order
> boards. Read [electrical.md](electrical.md) once before you start.

> [!WARNING]
> - **Plug the host into the LEFT half.** The left half is the ZMK central. The right USB-C gives power
>   and UF2 flashing only.
> - **Never plug or unplug the TRRS cable while either half is powered.** Unplug USB first. The
>   jack shorts its contacts against each other while the plug slides in.

## Contents

- [Parts](#parts)
- [Tools](#tools)
- [1. Check the assembled PCBs](#1-check-the-assembled-pcbs)
- [2. Flash and test the bare boards](#2-flash-and-test-the-bare-boards)
- [3. Choose the power mode (JP1)](#3-choose-the-power-mode-jp1)
- [4. Fit the display socket](#4-fit-the-display-socket)
- [5. Prepare the case](#5-prepare-the-case)
- [6. Assemble the case](#6-assemble-the-case)
- [7. Switches, stabilisers and keycaps](#7-switches-stabilisers-and-keycaps)
- [8. Tent legs](#8-tent-legs)
- [9. Connect and use](#9-connect-and-use)
- [Troubleshooting](#troubleshooting)

## Parts

For one keyboard (both halves). Part numbers and the assembled parts are in [bom.md](bom.md).

| Part | Qty | Notes |
|---|---|---|
| worxboard-left PCB, JLC-assembled | 1 | RP2040, USB-C, TRRS jack, 37 hot-swap sockets and 37 diodes fitted |
| worxboard-right PCB, JLC-assembled | 1 | the same circuit with the TRRS data lines crossed |
| nice!view display (or an LS011B7DH03 breakout with the same pinout) | 2 | one per half, gate G1 |
| 1×5 2.54 mm female socket, low profile | 2 | J3; the display module plugs into it |
| MX-compatible switches, 3- or 5-pin | 74 | 37 per half |
| 2u plate-mount stabilisers | 4 | thumb keys T4 and T5 on each half |
| Keycaps | 74 | 1.5u × 8 (outer column), vertical 1.5u × 4 (inner column), 2u × 4 (thumbs), 1u × 58 |
| Case: top shell, bottom tray and plate spacer per half | 1 set | [case.md](case.md); CNC aluminium or 3D-printed |
| M2.5 countersunk screws | 16 | 8 per half; lengths in [case.md](case.md#fasteners) |
| Rubber feet, Ø10 mm | 8 | 4 per half |
| Tent legs, foot caps, stock ErgoDox EZ M3 spring thumbscrews | 6 each | [legs.md](legs.md) |
| TRRS cable, 4-pole, **straight** (not crossed) | 1 | 3.5 mm |
| USB-C cable | 1–2 | the second is only needed in split-powered mode or for flashing the right half |

## Tools

- Soldering iron and solder (only for J3).
- Flush cutters, tweezers.
- A multimeter, for the power-mode and continuity checks.
- A Ø2.5 mm or smaller pin (paper clip) to reach the BOOT and RESET buttons through the case.
- A 1.5 mm hex key or a Phillips #0, depending on the M2.5 screws you buy.

## 1. Check the assembled PCBs

Lay out both boards and compare them with the renders in [`docs/images/`](images/):

- The **top side** (F.Cu) carries the RP2040 (U1), flash (U2), crystal (Y1), regulator (U3), the
  USB-C receptacle (J1) at the back edge, the BOOT and RESET buttons, and the TRRS jack (J2) in the
  bump on the inner edge.
- The **bottom side** (B.Cu) carries the 37 Kailh hot-swap sockets and the 37 diodes.
- The silkscreen next to the jack reads `DO NOT HOT-PLUG TRRS` and `HOST → LEFT`. The board label
  reads `worxboard L rev A` or `worxboard R rev A`.

Look for solder bridges on the QFN and the USB-C pins with a loupe. Check that every socket sits
flat.

## 2. Flash and test the bare boards

Test each board on its own, before anything is fitted, so any fault is easy to reach.

1. Plug a USB-C cable into the board. A new board with empty flash starts the RP2040 boot ROM
   by itself and a USB drive called **`RPI-RP2`** appears.
2. Download the firmware: the `worxboard-firmware` artifact from the latest
   [firmware workflow run](https://github.com/w0rxbend/worxboard/actions/workflows/firmware.yml), or a
   release. Details are in [firmware.md](firmware.md).
3. Drag the right `.uf2` onto `RPI-RP2`:
   - left board: `worxboard_left_central.uf2`
   - right board: `worxboard_right_peripheral.uf2`

   The drive ejects itself and the board restarts with the new firmware.
4. To flash again later, enter the bootloader with either:
   - **double-tap RESET**, or
   - **hold BOOT, tap RESET, release BOOT**.

   `RPI-RP2` appears again. On the keyboard, `&bootloader` on layer 2 does the same.
5. Test the left board on its own: open a key tester, plug the board in, and short each socket's two
   pads with tweezers. Each position must type its key. The right board alone types nothing: it is
   the peripheral and sends its keys over TRRS.
6. With both boards **unpowered**, connect them with the TRRS cable. Then plug the host into the
   **left** board and test every right-hand socket the same way.

## 3. Choose the power mode (JP1)

JP1 is a solder jumper next to the TRRS jack. It joins the half's own supply (VSYS) to the cable's
power wire (VLINK, on Ring2) through a 250 mA polyfuse (F1). It is **bridged by default**.

| Mode | JP1 on both halves | Cables | Behaviour |
|---|---|---|---|
| **Linked power** (default) | bridged | one USB-C, into the left half | The right half runs from the TRRS cable. Either USB-C can also be plugged in at the same time; Schottky diodes stop the two hosts from back-feeding each other. |
| **Split-powered** | cut on **both** | one USB-C per half | The TRRS cable carries only data and ground. Use this if you never want power on the jack. |

To cut JP1, scratch through the thin trace between the two pads with a craft knife, then check with
a multimeter that the pads are no longer connected. To restore it, bridge the pads with solder.
Do not run one half bridged and the other cut.

## 4. Fit the display socket

The display module (nice!view or compatible) plugs into a 1×5 female socket J3 at the back end of
the display area, so it can be removed.

1. Solder the 1×5 male header to the display module if it has none.
2. Put the **female socket** J3 on the top side of the PCB at the `J3` footprint. Plug the display
   into it first so the socket is held square, with the module lying flat over the inner column
   where the top key would be.
3. Solder the five pins from the bottom side. Trim them flush: the hot-swap sockets are nearby on
   the bottom side, and the bottom tray has only 4 mm of cavity.
4. Check the stack height: from the PCB top to the top of the display glass must be **≤ 8.2 mm**
   (gate G1). Use the lowest socket you can find, or solder the module directly if it is too tall.
5. Pin 1 (MOSI) is at the outer end of the socket on both halves; see the
   [J3 table in pinout.md](pinout.md#display-header-j3). The module mounts face-up the same way on
   both halves.

Plug the board in again. The left display shows the ZMK status screen (layer and output); the right
display shows the `worxboard` logo, the lock indicators and `wired`.

## 5. Prepare the case

The case files are built by `just model` ([case.md](case.md)). If you machine aluminium, 3D-print a
test fit first and check it against your PCB:

- The display sits under the window in the top shell and its pocket clears the header.
- The USB-C notch on the back wall lines up with J1 on **both** halves.
- The TRRS hole in the inner bump lines up with the jack mouth.
- The BOOT and RESET pin holes in the top skin sit over the two buttons.

## 6. Assemble the case

1. Fit the four rubber feet into the recesses under each bottom tray.
2. Lay the PCB, top side up, on the posts of the bottom tray.
3. Lay the plate spacer over the PCB: each switch goes through its own opening.
4. Put the top shell on, so its bosses meet the PCB. Feed the display module through its pocket.
5. Fit the 8 M2.5 countersunk screws from below. Tighten them gently: they clamp the PCB between the
   tray posts and the shell bosses.

## 7. Switches, stabilisers and keycaps

1. **Stabilisers first.** Clip the two 2u plate-mount stabilisers into the plate cut-outs at the
   thumb keys T4 and T5, before any switch is fitted there.
2. **Switches.** Press each switch through the plate until it clicks, supporting the hot-swap
   socket from behind if you can. Check the pins are straight first: a bent pin does not enter the
   socket and can push it off its pads.
3. Re-test every key in a key tester.
4. **Keycaps.** The outer column takes 1.5u caps, the inner column (`TG(1)`, `HYPER`/`MEH`) takes
   vertical 1.5u caps, and the two large thumb keys take 2u caps. The top inner key is gone: the
   display sits there.

## 8. Tent legs

Each half has three leg mounts: the outer wall, the inner wall and the thumb-cluster end, at the
stock ErgoDox EZ positions. Put a leg's hub on its boss, push the stock spring thumbscrew through,
and tighten it at the angle you want. See [legs.md](legs.md).

## 9. Connect and use

1. With both halves unpowered, plug in the TRRS cable.
2. Plug the host into the **left** half.
3. In linked-power mode the right half starts too. In split-powered mode plug its own USB-C in.

The keymap ([firmware.md](firmware.md#keymap)) has three layers: base, symbols / F-keys, and
media / mouse. ZMK Studio works over the left half's USB connection; unlock it with `&studio_unlock`
on layer 2.

## Troubleshooting

| Symptom | Check |
|---|---|
| No `RPI-RP2` drive | Use a data cable (not charge-only). Hold BOOT and tap RESET. Measure 3.3 V on the 3V3 net. |
| Left half types, right half does nothing | Was the cable plugged in while powered? Unplug everything and reconnect TRRS first. Is the cable straight 4-pole? Is the right half flashed with the **peripheral** firmware? |
| Right half dark in split-powered mode | JP1 is cut, so the right half needs its own USB-C. |
| One key dead | Re-seat the switch; check the socket's two pads and the diode next to it. |
| A whole row or column dead | See [matrix.md](matrix.md) for the GPIO of that row or column and check that pin on the RP2040. |
| Display blank | Re-seat the module in J3 and check the pin order against [pinout.md](pinout.md#display-header-j3). |
| Wrong characters on the right half | The left half needs the **central** firmware, the right half the **peripheral** firmware. |
