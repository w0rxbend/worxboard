# Ordering the PCBs from JLCPCB

This page explains how to order one keyboard's PCBs, assembled, from [JLCPCB](https://jlcpcb.com).
The left and right boards are **two separate designs**: order each one with its own files.

> [!IMPORTANT]
> Do not order until gates **G1–G3** pass ([bom.md](bom.md#gates)); all three are still open.
> Rev A has not been built: the boards pass DRC and the scripted checks, but no board has been made.

## The files

Each side has three files, written by KiKit (`kikit fab jlcpcb --assembly --missingError`) in stage
13 of the PCB pipeline:

| File | Upload as | Contents |
|---|---|---|
| `gerbers.zip` | Gerber file | Copper, mask, silkscreen, Edge.Cuts and drill files |
| `bom.csv` | BOM file | Comment, designators, footprint and **LCSC** part number of every assembled part: 21 lines, the same on both sides ([bom.md](bom.md#per-half-assembled-by-jlcpcb)) |
| `pos.csv` | CPL (placement) file | Position, rotation and side of every assembled part: 118 per side, 74 of them on the bottom |

Where to get them:

- **CI**: every push to `main` runs the [`pcb` workflow](https://github.com/w0rxbend/worxboard/actions/workflows/pcb.yml).
  Its `board` job uploads `worxboard-pcb-left` and `worxboard-pcb-right`, each with `gerbers.zip`,
  `bom.csv`, `pos.csv`, the board STEP, the Edge.Cuts DXF, the DRC report and the renders.
- **Locally**: `just pcb-fab left` and `just pcb-fab right` write them to `build/<side>/jlc/` from
  the committed boards (Docker, `kicad/kicad:10.0.7-full`, a few minutes). `just pcb <side>`
  rebuilds the board itself first (about 20 minutes per side).
- **Release**: on a `v*-revA` hardware tag they are to be committed under `pcb/production/left/` and
  `pcb/production/right/` (crkbd style) and attached to the GitHub release. No tag exists yet: the
  release workflow is part of WS5.

J3 (display socket), JP1, the test pads, the mounting holes and the stabiliser holes are left out of
the BOM and CPL on purpose: their footprints are marked "exclude from BOM / position files" and the
pipeline fails if one of them shows up (deviation WS2c-1). The builder fits J3.

## PCB settings

| Option | Value |
|---|---|
| Base material | FR-4 |
| Layers | **2** |
| Dimensions | taken from the Gerbers (about 183 × 159 mm per half) |
| PCB qty | 5 (the minimum); you need 1 per keyboard of each side |
| Different designs | 1 per order (left and right are separate orders, or separate items in one cart) |
| PCB thickness | **1.6 mm** |
| PCB colour | any; black or white suit the silkscreen best |
| Surface finish | **ENIG** (flat pads for the QFN and the USB-C) |
| Outer copper weight | 1 oz |
| Via covering | tented |
| Min via hole size / diameter | 0.3 / 0.6 mm (the default) |
| Board outline tolerance | ±0.2 mm (regular) |
| Mark on PCB | "Remove mark", or leave it: there is space on the bottom side |

## Assembly settings

| Option | Value |
|---|---|
| PCB assembly | **yes** |
| PCBA type | **Standard** (Economic does not do two-sided assembly) |
| Assembly side | **Both sides**: the RP2040 cluster, USB-C and TRRS jack are on top; the 37 hot-swap sockets and 37 diodes are on the bottom |
| PCBA qty | 2 to 5 |
| Tooling holes | added by JLCPCB |
| Confirm parts placement | **yes**: check the rotation of every part in the preview, see below |

### Steps

1. Upload `gerbers.zip` and set the options above.
2. Turn on assembly and upload `bom.csv` and `pos.csv`.
3. Check every line on the parts page: the LCSC numbers must match [bom.md](bom.md). If a part
   is out of stock, pick a replacement with the same footprint and value and note it on the order.
   **[G3]** parts must be re-checked on the day you order. On 2026-10-29 LCSC showed no stock for
   C113767 (flash), C25744 (10 kΩ) and C2803348 (hot-swap socket).
4. In the placement preview, check in particular:
   - U1 (RP2040): the pin-1 dot matches the silkscreen (the left U1 is turned 180° on purpose);
   - J1 (USB-C): the mouth faces off the back edge;
   - J2 (TRRS): the mouth faces off the inner edge of the bump;
   - the bottom side: every hot-swap socket sits on its two pads, and every diode's cathode bar is
     on the row side.

   J1, J2 and the hot-swap sockets show no 3D body in the preview: KiCad's library has no model
   for them (deviation WS2c-2). Judge them by their pads.
5. Repeat for the other side.

## Costs

JLCPCB charges a one-off loading fee per **extended** part and design. This board uses these extended
parts: C2040 (RP2040), C113767 (flash), C91749 (crystal), C7519 (ESD), C95562 (TRRS jack), C165948
(USB-C), C2803348 (hot-swap socket), C455280 (tact switch) and the PTC C70069. Expect the fees for both
designs, plus the two-sided Standard assembly setup, to dominate the price of a small order. The
hot-swap sockets (74 per keyboard) are the most expensive line.

## After delivery

Follow the [build guide](buildguide_en.md): check the boards, flash them bare, choose the power
mode (JP1), then fit the display socket.

## Case

The case is not ordered here. [case.md](case.md) covers the case files; `just order` builds a
CNC order package with PDF drawings and the form settings (`case/ORDER_NOTES.md`).
