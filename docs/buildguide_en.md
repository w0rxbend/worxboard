# worxboard rev A build guide

This guide follows the [Corne (crkbd) build guides](https://github.com/foostan/crkbd/tree/main/docs):
check the parts, test the bare boards, then build up from the PCB. JLCPCB assembles **every** part
on the PCB: the RP2040 and its support parts, the USB-C and TRRS connectors, the 37 hot-swap sockets
and 37 diodes per half, and the display socket J3. **Nothing on the PCB needs soldering.** You
solder only the displays' own header pins, then plug in the displays, the switches and the keycaps.

> [!IMPORTANT]
> Rev A has **not been built yet**. Gates G1–G3 pass ([verification.md](verification.md#summary)),
> the boards pass DRC and every scripted check, and the firmware and the case build, but nothing has
> run on hardware. Order the boards as [ordering-jlcpcb.md](ordering-jlcpcb.md) describes. Read
> [electrical.md](electrical.md) once before you start.

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
- [4. Plug in the displays](#4-plug-in-the-displays)
- [5. Prepare the case](#5-prepare-the-case)
- [6. Assemble the case](#6-assemble-the-case)
- [7. Switches, stabilisers and keycaps](#7-switches-stabilisers-and-keycaps)
- [8. Tent legs](#8-tent-legs)
- [9. Connect and use](#9-connect-and-use)
- [Troubleshooting](#troubleshooting)

## Parts

For one keyboard (both halves). The full list with specs, quantities and shops is in
[shopping-list.md](shopping-list.md); the parts JLC fits are in [bom.md](bom.md).

| Part | Qty | Notes |
|---|---|---|
| worxboard-left PCB, JLC-assembled | 1 | RP2040, USB-C, TRRS jack, display socket J3, 37 hot-swap sockets and 37 diodes fitted |
| worxboard-right PCB, JLC-assembled | 1 | the same circuit with the TRRS data lines crossed |
| nice!view display (or an LS011B7DH03 breakout with the same pinout) | 2 | one per half, with the male header it ships with |
| MX-compatible switches, 3- or 5-pin | 74 | 37 per half |
| 2u plate-mount stabilisers | 4 | thumb keys T4 and T5 on each half |
| Keycaps | 74 | 58 × 1u, 8 × 1.5u (outer column), 4 × 1.5u mounted vertically (inner column), 4 × 2u (thumbs) |
| Case: top shell, bottom tray, plate spacer per half; 6 tent legs; the TPU foot-cap tree | 1 set | [`case/production/`](../case/production/README.md), [case.md](case.md) |
| M2.5 × 12 countersunk screws | 12 | 6 per half, in the edge bosses T2–T4 and T6–T8 |
| M2.5 × 10 countersunk screws | 4 | 2 per half, in the bosses under the key well, T1 and T5 |
| Rubber feet, Ø10 mm | 8 | 4 per half |
| M3 × 12 knurled thumbscrews and friction washers | 6 + 6 | one per leg ([legs.md](legs.md)) |
| TRRS cable, 4-pole, **straight** (not crossed) | 1 | 3.5 mm, with a **slim plug head: ≤ Ø6.3 mm for the first 3.7 mm** behind the metal shaft ([case.md](case.md#trrs-cable)) |
| USB-C cable | 1–2 | the second is only needed in split-powered mode or for flashing the right half |

## Tools

- Soldering iron and solder: only for the five header pins on each display module (and to
  re-bridge JP1 if you ever cut it). Nothing on the PCB.
- Flush cutters, tweezers, a small file or fine sandpaper (for the panel tab nubs).
- A multimeter, for the power-mode and continuity checks.
- A Ø2.5 mm or smaller pin (paper clip) to reach the BOOT and RESET buttons through the case.
- A 1.5 mm hex key or a Phillips #1, depending on the M2.5 screws you buy.
- Optional: a Raspberry Pi Debug Probe (or any SWD probe) for the SWD test pads.

## 1. Check the assembled PCBs

The boards arrive in their panel frames. Break each board out at its 14 mouse-bite tabs, bending
the frame gently away from the USB-C (J1) and TRRS (J2) connectors, which overhang the board edge.
Then file or sand every tab nub **flush** with the edge: the case leaves only about 0.3 mm round the
PCB.

Lay out both boards and compare them with the KiCad renders of the committed boards:

| | Top | Bottom |
|---|---|---|
| Left | [pcb-left-top.png](images/pcb-left-top.png) | [pcb-left-bottom.png](images/pcb-left-bottom.png) |
| Right | [pcb-right-top.png](images/pcb-right-top.png) | [pcb-right-bottom.png](images/pcb-right-bottom.png) |

- The **top side** carries, all in the strip along the back edge: the USB-C receptacle (J1), the
  RP2040 (U1), flash (U2), crystal (Y1), regulator (U3), USB ESD (U4), the Schottky diode (D1),
  the polyfuse (F1) and solder jumper (JP1), the BOOT (SW1) and RESET (SW2) buttons, the test pads
  and the 1×5 display socket J3. The TRRS jack (J2), its ESD part (U5) and resistors sit in the bump
  on the inner edge.
- The **bottom side** carries the 37 MX hot-swap sockets (SK101–SK137) and their 37 diodes
  (D101–D137). Each socket's curved notch wraps the round switch-centre hole.
- The silkscreen next to the jack reads `DO NOT HOT-PLUG TRRS` and `HOST → LEFT`; next to JP1 it
  reads `JP1: cut = split power`. The board label reads `worxboard L rev A` or `worxboard R rev A`.
- Every part's position is in [pinout.md](pinout.md#part-positions). The left RP2040 is turned
  180° compared with the right one; that is intended (deviation WS2b-1).

Look for solder bridges on the QFN and the USB-C pins with a loupe. Check that every socket sits
flat and that J3's five pins are soldered on the bottom side.

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

   `RPI-RP2` appears again. On the keyboard, `&bootloader` on layer 2 does the same. If the
   board never shows `RPI-RP2`, the SWD pads TP8 (SWCLK), TP9 (SWDIO) and TP10 (GND) take a
   debug probe.
5. Test the left board on its own: open a key tester, plug the board in, and short each socket's two
   pads with tweezers. Each position must type its key. The right board alone types nothing: it is
   the peripheral and sends its keys over TRRS.
6. With both boards **unpowered**, connect them with the TRRS cable. Then plug the host into the
   **left** board and test every right-hand socket the same way.

## 3. Choose the power mode (JP1)

JP1 is a solder jumper on the top side, in the back strip next to F1 and the USB-C receptacle
(silkscreen `JP1: cut = split power`). It joins the half's own supply (VSYS) to the cable's power
wire (VLINK, on Ring2) through a 250 mA polyfuse (F1). It is **bridged by default**. The case top
covers it, so choose the mode **before** you assemble the case.

| Mode | JP1 on both halves | Cables | Behaviour |
|---|---|---|---|
| **Linked power** (default) | bridged | one USB-C, into the left half | The right half runs from the TRRS cable. Either USB-C can also be plugged in at the same time; Schottky diodes stop the two hosts from back-feeding each other. |
| **Split-powered** | cut on **both** | one USB-C per half | The TRRS cable carries only data and ground. Use this if you never want power on the jack. |

To cut JP1, scratch through the thin trace between the two pads with a craft knife, then check with
a multimeter that the pads are no longer connected. To restore it, bridge the pads with solder.
Do not run one half bridged and the other cut.

## 4. Plug in the displays

J3, a 1×5 female socket 5.0 mm tall, is already fitted at the back end of the display area. The
display module (nice!view or compatible) plugs into it on its own male header and can be pulled out
again.

1. **Solder the male header to the module**, if it is not on yet: the short pins go up through the
   module from below, the long pins point down. Do not use the socket that ships with the nice!view
   (J3 is the same height), and do not add an extra spacer.
2. **Trim the pins flush on the glass side.** They must not stand above the module's glass
   (0.9 mm above its PCB): untrimmed pins reach the ceiling of the display pocket in the case
   (CASE-1).
3. **Plug the module into J3 LCD up**, so that it lies flat over the inner column, where the top
   key would be, and reaches toward you. Do this the same way on both halves. J3 pin 1 is MOSI, and
   pin *n* is the module's pin *n* ([pinout.md](pinout.md#display-header-j3)). Pointing the module
   the other way would put it off the board.
4. Plug the board in again. The left display shows ZMK's status screen, upright: USB at the top,
   the layer at the bottom. The right display shows `worx/board`, the Caps / Num / Scroll
   indicators and `wired`. A lit indicator shows in upper case in a frame.

If both screens read upside down, the panel's pixel origin is at the other end from the one the
firmware assumes. Set `CONFIG_WORXBOARD_DISPLAY_ROTATION_270=y` in
`firmware/zmk/config/worxboard.conf` and flash again ([firmware.md](firmware.md#known-issues)).

## 5. Prepare the case

The case order package is [`case/production/`](../case/production/README.md), case revision A3. It
is checked against the PCB STEPs by `just fitcheck`, with 0 mm³ of interference on both halves.
Before you machine aluminium, 3D-print a test top and check it against your assembled PCB:

- The display sits in its pocket under the window, with the glass below the bezel skin.
- The USB-C notch on the back wall lines up with J1 on **both** halves, and the plug seats fully.
- The TRRS hole in the inner bump lines up with the jack mouth, and the plug seats fully.
- The BOOT and RESET pin holes in the top skin sit over the two buttons.
- The C6R1 keycap clears the display module's far end.

## 6. Assemble the case

1. Fit the four rubber feet into the recesses under each bottom tray.
2. Lay the PCB, top side up, with its display plugged in, on the posts of the bottom tray.
3. Lay the plate spacer over the PCB: each switch goes through its own opening.
4. Put the top shell on, so its bosses meet the PCB and the display goes up into its pocket.
5. Fit the 8 M2.5 countersunk screws from below:
   - the **2 × M2.5 × 10** go into the two bosses under the key well, T1 and T5 (holes 0 and 4 in
     [pinout.md](pinout.md#mounting-holes)). Tighten them **snug only**: their blind threads are
     short;
   - the **6 × M2.5 × 12** go into the others.

   Do not use longer screws: every thread in the top shell is blind, and a longer screw stops
   before its head seats. Tighten them gently: they clamp the PCB between the tray posts and the
   shell bosses.

## 7. Switches, stabilisers and keycaps

1. **Stabilisers first.** Clip the two 2u plate-mount stabilisers into the plate cut-outs at the
   thumb keys T4 and T5, before any switch is fitted there.
2. **Switches.** Press each switch through the plate until it clicks, supporting the hot-swap
   socket from behind if you can. Check the pins are straight first: a bent pin does not enter the
   socket and can push it off its pads.
3. Re-test every key in a key tester.
4. **Keycaps.** The outer column takes 1.5u caps, the inner column (`TG(1)`, `HYPER`/`MEH`) takes
   1.5u caps turned vertical, and the two large thumb keys take 2u caps, also vertical. The top
   inner key is gone: the display sits there.

## 8. Tent legs

Each half has three leg mounts: the outer wall, the inner wall and the thumb-cluster end, at the
stock ErgoDox EZ positions. Snip the foot caps off their TPU tree at the base and push one onto each
leg's spigot. Put a friction washer on the boss, the leg's hub on the washer, push the M3 × 12
thumbscrew through, and tighten it at the angle you want. The washer is required with an M3 × 12:
without it, the screw reaches past the end of the outer and thumb threads. See [legs.md](legs.md).

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
| No `RPI-RP2` drive | Use a data cable (not charge-only). Hold BOOT and tap RESET. Measure 3.3 V on the 3V3 net (C3 or C4). Plug the left half in for the host; the right one does not enumerate as a keyboard. |
| Left half types, right half does nothing | Was the cable plugged in while powered? Unplug everything and reconnect TRRS first. Is the cable straight 4-pole? Is the right half flashed with the **peripheral** firmware? |
| Right half dark in split-powered mode | JP1 is cut, so the right half needs its own USB-C. |
| Right half dark with one cable | Check JP1 is bridged on **both** halves and F1 has not tripped (unplug for a minute). |
| One key dead | Re-seat the switch; check the socket's two pads and the diode next to it ([matrix.md](matrix.md#sockets-and-diodes) gives the SK/D references). |
| A whole row or column dead | See [matrix.md](matrix.md) for the GPIO of that row or column and check that pin on the RP2040. |
| Display blank | Re-seat the module in J3, LCD up, reaching toward you. Check the header's five joints on the module, and the pin order against [pinout.md](pinout.md#display-header-j3). |
| Display upside down | Set `CONFIG_WORXBOARD_DISPLAY_ROTATION_270=y`, see [firmware.md](firmware.md#known-issues). |
| Wrong characters on the right half | The left half needs the **central** firmware, the right half the **peripheral** firmware. |
