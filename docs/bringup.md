# First-article bring-up

This procedure tests the first assembled rev B boards. It closes the items in
[verification.md, "Not verified until a board is built"](verification.md#not-verified-until-a-board-is-built),
the crystal start-up risk (PLANS.md PR-04) and the power budget (PR-19). Run it on at least two kits
(L1/R1 and L2/R2) before you order the aluminium case or call the design released.

The [build guide](buildguide_en.md) is for builders. This page is for the first boards, so it
measures more and assumes nothing works yet.

## Rules

1. Work through the stages in order. Each stage needs the one before it on the same half.
2. Write each result in the stage's table: the measured value, or `ok` / `FAIL`. Leave a cell empty
   only if you did not run that step.
3. **Stop at the first FAIL in stages 1 and 2** on that half. Power faults get worse with time.
   Record the failure and what you saw, then continue with the other boards.
4. When the run is done, copy the tables into `docs/verification.md` (PLANS.md T-15). Every FAIL
   becomes a new `PR-*` finding in `PLANS.md`.

The expected values come from the datasheets and the estimates in [electrical.md](electrical.md).
Several are estimates: a value outside the range is a finding, not proof of a fault.

## Equipment

- A multimeter.
- A bench supply at 5.0 V with a current limit, or a USB-C power meter between the host and the board.
- An oscilloscope, 50 MHz or more, for step 4.5 only.
- A straight 4-pole TRRS cable, a USB-C cable, two nice!view modules, a loupe and tweezers.
- A few MX switches from the order and a shine-through keycap.
- A host with a key tester page and ZMK Studio.

Measure GND at TP10. The rails are at these parts (positions in [pinout.md](pinout.md#part-positions)):
VSYS at C1, 3V3 at C3, 1V1 at C19, VLED at C20.

## Stage 1. Inspection, unpowered

Closes "JLC assembly" and "LED assembly".

| Step | Check | Pass |
|---|---|---|
| 1.1 | Compare both sides with the renders, as in [build guide step 1](buildguide_en.md#1-check-the-assembled-pcbs) | every part present; U1 pin 1, U6, U7, D1 and the diodes match the render |
| 1.2 | Look at the QFN, the USB-C pins and J1's four shell legs with the loupe | no bridge; solder round all four legs |
| 1.3 | Look at all 37 LEDs from the top through their cutouts, and at their leads from the bottom | each LED flat in its cutout; solder fillet on all four leads |
| 1.4 | Look at all 37 hot-swap sockets (C41430893) | each socket flat; both pads wetted |
| 1.5 | Measure resistance to GND from VSYS, 3V3, 1V1 and VLED. Wait for the reading to settle while the caps charge | none under 100 Ω |

| Step | L1 | R1 | L2 | R2 |
|---|---|---|---|---|
| 1.1 | | | | |
| 1.2 | | | | |
| 1.3 | | | | |
| 1.4 | | | | |
| 1.5 | | | | |

## Stage 2. First power, boot ROM

Closes the crystal start-up (PR-04) and the VLED default state. The flash is empty, so the boot ROM
runs.

| Step | Check | Pass |
|---|---|---|
| 2.1 | Power the half from the bench supply through its USB-C at 5.0 V, with a 200 mA limit. Read the current | under 100 mA, with no current limiting |
| 2.2 | Measure VSYS | 4.5–4.8 V (5.0 V minus D1's drop) |
| 2.3 | Measure 3V3 | 3.23–3.37 V |
| 2.4 | Measure 1V1 | 1.05–1.15 V |
| 2.5 | Measure VLED | under 0.2 V: U6 stays off because R15 holds EN low |
| 2.6 | Plug the half into the host | `RPI-RP2` appears within 5 s |
| 2.7 | Unplug for at least 10 s, then plug in again. Do it **20 times**, starting from a cold board | `RPI-RP2` appears every time. Write the count, for example `20/20` |

| Step | L1 | R1 | L2 | R2 |
|---|---|---|---|---|
| 2.1 mA | | | | |
| 2.2 V | | | | |
| 2.3 V | | | | |
| 2.4 V | | | | |
| 2.5 V | | | | |
| 2.6 | | | | |
| 2.7 | | | | |

If 2.7 fails even once, the crystal does not start reliably for the boot ROM: record it under PR-04.
If the board never enumerates, flash it over SWD (TP8 SWCLK, TP9 SWDIO, TP10 GND) to tell a crystal
fault from a USB fault.

## Stage 3. Firmware, matrix and split

Closes "Firmware on hardware" (the matrix, the wired split and the bootloader entry).

| Step | Check | Pass |
|---|---|---|
| 3.1 | Flash `worxboard_left_central.uf2` on the left and `worxboard_right_peripheral.uf2` on the right ([firmware.md](firmware.md#flash)) | the half restarts, with no `RPI-RP2` left |
| 3.2 | Left alone, on the host: short each socket's two pads with tweezers in a key tester | all 37 positions type the keymap's key |
| 3.3 | Both halves unpowered: connect the TRRS cable, then plug the host into the left half. Test the 37 right positions the same way | all 37 type |
| 3.4 | Double-tap RESET, then try BOOT + RESET, on each half | `RPI-RP2` appears both ways |

| Step | L1 | R1 | L2 | R2 |
|---|---|---|---|---|
| 3.1 | | | | |
| 3.2 / 3.3 | | | | |
| 3.4 | | | | |

## Stage 4. LEDs and the VLED switch

Closes "LED chain", "VLED switch and limit", "U7 waveform", "Brightness and current" and
"RGB over the split". The controls are on layer 1 ([firmware.md](firmware.md#controls)).

| Step | Check | Pass |
|---|---|---|
| 4.1 | After the firmware starts, measure VLED | within 0.1 V of VSYS |
| 4.2 | Press `RGB_BRI` ten times to reach the 8 % cap ([firmware.md](firmware.md#brightness-cap)). Count the lit LEDs | 37 of 37, all the same colour |
| 4.3 | If any LED is dark: note the first dark one in chain order (row 0 inward, row 1 outward, row 2 inward, C6R2, row 3 outward, row 4 inward, then T5, T4, T3, T2, T0, T1) | none dark. If one is, the fault is at that LED or the one before it |
| 4.4 | Colour order: start at red (hue 0). Press `RGB_HUI` 12 times (120°), then 12 more (240°) | red, then green, then blue: GRB is right |
| 4.5 | Scope GP22 (U7 pin 2) and R16's LED side (RGB_D101) | T0H 250–400 ns and T1H 700–1000 ns at both points; a high level within 0.3 V of VLED at R16; clean edges |
| 4.6 | Toggle RGB off (`RGB_TOG`) and measure VLED | under 0.2 V. Toggle on again: back within 0.1 V of VSYS |
| 4.7 | Press the RGB keys on the left half only | the right half follows every change |

| Step | L1 | R1 | L2 | R2 |
|---|---|---|---|---|
| 4.1 V | | | | |
| 4.2 | | | | |
| 4.3 | | | | |
| 4.4 | | | | |
| 4.5 | | | | |
| 4.6 | | | | |
| 4.7 | | | | |

### Current at the cap (PR-19)

Set saturation to 0 (full white) with a ZMK Studio binding: saturation has no key in the keymap.
Then measure with the power meter between the host and the left half, both halves on the cable.

| Step | Check | Pass (estimate) |
|---|---|---|
| 4.8 | Current with the LEDs toggled off | about 60 mA for both halves |
| 4.9 | Current at full white, 8 % cap | under 400 mA for both halves (estimated 360–390 mA) |
| 4.10 | VSYS on the right half (C1) at full white | at least 4.0 V (the LEDs need 3.7 V, U3 needs 3.6 V) |
| 4.11 | Step through the four effects at full brightness | the 4.9 current is never exceeded |
| 4.12 | Optional, one board: U6's limit. Power the half from the bench supply (5.0 V, 1 A limit). Short C20 to GND through the ammeter for under 1 s | 0.34–0.56 A (0.45 A ± 25 %), and the board recovers |

| Step | Kit 1 | Kit 2 |
|---|---|---|
| 4.8 mA | | |
| 4.9 mA | | |
| 4.10 V | | |
| 4.11 | | |
| 4.12 A | | |

## Stage 5. Displays, contacts and long runs

Closes the display items, the forwarded lock indicators, "J2 contacts", "Right-half settings writes" and "Plug-in capacitance".

| Step | Check | Pass |
|---|---|---|
| 5.1 | Unpowered: plug the nice!view modules into J3 as in [build guide step 4](buildguide_en.md#4-plug-in-the-displays), then power up | both screens show their status screen |
| 5.2 | Read both screens with the board the right way up | the text is upright. If both are upside down, set `CONFIG_WORXBOARD_DISPLAY_ROTATION_270=y` ([firmware.md](firmware.md#known-issues)) |
| 5.3 | J2 contacts: plug the TRRS cable into one half only. Beep from the free plug's contacts to the board | Tip to R11's jack side (TRRS_A), Ring1 to R12's jack side (TRRS_B), Ring2 to F1's VLINK side, Sleeve to GND |
| 5.4 | Change an RGB setting. Then type on the right half without stopping for 2 minutes. A settings write happens about 1 minute after the change | no dropped, doubled or stuck keys |
| 5.5 | Power-cycle both halves | both restore the same RGB state |
| 5.6 | Plug the keyboard into each host you will use, both halves on the cable | it enumerates every time, with no over-current warning |
| 5.7 | Leave the keyboard running for 1 hour with the displays on | both screens still update; no reset |
| 5.8 | Press Caps Lock on the host | the lock indicator shows on the right screen: the central forwards it |

| Step | L1 | R1 | L2 | R2 |
|---|---|---|---|---|
| 5.1 | | | | |
| 5.2 | | | | |
| 5.3 | | | | |
| 5.4 | | | | |
| 5.5 | | | | |
| 5.6 | | | | |
| 5.7 | | | | |
| 5.8 | | | | |

## Stage 6. Fit

Closes "Case" and "Display setback fit". Use the 3D-printed test top first
([case.md](case.md#before-machining)). Do not use the machined case for this stage.

| Step | Check | Pass |
|---|---|---|
| 6.1 | Fit one switch over an LED and put a shine-through keycap on it, LEDs at the cap | the light reaches the legend through the switch's south slot (PR-09) |
| 6.2 | Clip a 2u stabiliser into the test top | it seats with its wire on the side the case drawing shows (PR-08) |
| 6.3 | Plug in the USB-C and TRRS cables through the test top's slots | both plugs seat fully |
| 6.4 | Press BOOT and RESET through the case pin holes | both buttons respond |
| 6.5 | With the nice!view in J3, fit the test top and press the C6R1 keycap to the bottom | the module lies in its pocket under the window, and the keycap clears it |

| Step | Kit 1 | Kit 2 |
|---|---|---|
| 6.1 | | |
| 6.2 | | |
| 6.3 | | |
| 6.4 | | |
| 6.5 | | |

## Coverage

Each item in [verification.md, "Not verified until a board is built"](verification.md#not-verified-until-a-board-is-built)
and the steps that close it:

| Item | Steps |
|---|---|
| JLC assembly | 1.1, 1.4 |
| Firmware on hardware | 2.6, 2.7, 3.1–3.4, 5.1, 5.2, 5.7, 5.8 (the role-swap builds are experimental and not tested here) |
| J2 contacts | 5.3 |
| Case | 6.3, 6.4, 6.5 |
| LED assembly | 1.3 |
| LED chain | 4.2, 4.3, 4.4 |
| VLED switch and limit | 2.5, 4.1, 4.6, 4.12 |
| U7 waveform | 4.5 |
| Brightness and current | 4.8–4.11 |
| RGB over the split | 4.7 |
| Right-half settings writes | 5.4, 5.5 |
| Display setback fit | 6.5 |
| Plug-in capacitance | 5.6 |
| Crystal start-up (PLANS.md PR-04) | 2.7 |
| Power budget (PLANS.md PR-19) | 4.8–4.12 |
