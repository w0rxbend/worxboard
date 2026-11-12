# Soldering the boards at home

The tested way to get the two boards is factory assembly: [JLCPCB](ordering-jlcpcb.md) or
[PCBWay](ordering-pcbway.md) fits every part. This page is for the other way: you order bare boards
and the parts, and you solder them yourself.

> [!IMPORTANT]
> Nobody has built a board this way. The checks in this repository cover the factory files only, and
> rev B has not been built at all ([verification.md](verification.md)). Treat this page as a plan,
> not as a tested procedure.

## Is it for you

One half carries 201 parts, so the keyboard carries 402. Most of them are easy with a soldering
iron. Three are not: they need solder paste and hot air or a hotplate, because their contacts sit
under the part.

| Parts, per half | Package | Side | Tool |
|---|---|---|---|
| U1, RP2040 | QFN-56, 0.4 mm pitch, with a centre pad | top | paste, then hot air or a hotplate |
| J1, USB-C socket | 16 contacts under a metal shell | top | paste, then hot air or a hotplate |
| Y1, 12 MHz crystal | 3225, pads under the body | top | paste, then hot air or a hotplate |
| 33 resistors and capacitors | 0402 | top | paste, or a fine iron tip and tweezers |
| 5 capacitors, the fuse F1, the diode D1 | 0603, 1206, SOD-123 | top | iron |
| U2 to U7 | SOIC-8, SOT-23-5, SOT-23-6 | top | iron |
| SW1, SW2, the TRRS jack J2 | surface-mount, large pads | top | iron |
| J3, display socket | 5 through-hole pins | top | iron |
| 37 hot-swap sockets | two large pads each | bottom | iron |
| 37 diodes | SOD-123 | bottom | iron |
| 37 RGB LEDs | SK6812MINI-E, four leads, mounted through a cutout | bottom | iron |
| 37 capacitors | 0402 | bottom | fine iron tip and tweezers |

The full list, with a part number for every line, is in [bom.md](bom.md#per-half-assembled-by-jlcpcb).

If the three reflow parts are more than you want to take on, order the boards assembled. On the
JLCPCB parts list you can still leave a part out and fit it yourself, for example when it is out of
stock on the day ([If a part is out of stock](ordering-jlcpcb.md#if-a-part-is-out-of-stock)).

## What to order

1. **The boards.** Upload `gerbers.zip` from each side's
   [`bare-board/`](../pcb/production/left/bare-board/README.md) folder: the board without the
   assembly frame, 182.84 × 158.75 mm. Use the PCB options of the
   [JLCPCB guide](ordering-jlcpcb.md#2-pcb-options), with the single-board changes that folder's
   README lists, and do not add assembly. The left and right boards are two designs.
2. **A stencil.** The Gerbers carry the paste layer of both sides. Order at least the top-side
   stencil: it is what makes U1 and J1 workable.
3. **The parts.** `bom.csv` in the same folder has one LCSC part number per line. The quantities
   are for one board, so order each half's list once and add spares of the 0402 parts and the LEDs.
4. The rest of the keyboard is the same as for factory boards: [shopping-list.md](shopping-list.md).

## Where each part goes

- Open `pcb/<side>/worxboard-<side>.kicad_pcb` in KiCad 10 and keep it beside you: it shows every
  reference, its side and which way it turns.
- Do not take angles from `cpl.csv`. That file carries corrections for JLCPCB's placement machines,
  so some of its angles differ from the board.
- For every part that can go in the wrong way round, the
  [placement preview checklist](ordering-jlcpcb.md#placement-preview-checklist) says where pin 1 or
  the cathode band belongs, with a drawing.

## Order of work

1. **Top side, with paste.** Stencil the paste, place U1, J1, Y1 and the small parts, then reflow.
   Inspect U1 and J1 under magnification for bridges before you go on.
2. **J1's shell legs.** The four legs of the USB-C shell go through slots in the board. Solder them
   with the iron if the paste did not fill them: they hold the socket against the cable.
3. **Bottom side, with the iron.** No part there has hidden contacts. Go from low to tall: the 37
   capacitors, the 37 diodes, the 37 LEDs, then the 37 sockets.
4. **The LEDs.** Each LED sits over its small cutout and shines up through the board. They turn
   along the chain, so they face opposite ways from row to row: check each one against the KiCad
   board. Solder each lead quickly, because the body is plastic.
5. **J3 last.** Push the display socket in from the top and solder its five pins.

## Test before you go on

Follow the build guide from [Check the assembled PCBs](buildguide_en.md#1-check-the-assembled-pcbs)
and [Flash and test the bare boards](buildguide_en.md#2-flash-and-test-the-bare-boards): the board
must show up as a USB drive, every socket must register, and every LED must light. The LEDs are one
chain, so a bad joint on one LED also darkens every LED after it.

## What this page cannot tell you

- Whether the footprints are forgiving by hand. They are the ones the factory files use, and no
  report of a hand-built board exists.
- What it costs. Nobody has priced the bare boards, the stencil and the loose parts against the
  assembled order.
