# Ordering the PCBs from JLCPCB

This page explains how to order one keyboard's PCBs, assembled, from [JLCPCB](https://jlcpcb.com).
The left and right boards are **two separate designs**: order each one with its own files.

> [!IMPORTANT]
> Do not order until gates **G1–G3** pass ([bom.md](bom.md#gates)). Rev A has not been built.

## The files

Each side has three files, written by KiKit (`kikit fab jlcpcb --assembly`) in the PCB pipeline:

| File | Upload as | Contents |
|---|---|---|
| `gerbers.zip` | Gerber file | Copper, mask, silkscreen, Edge.Cuts and drill files |
| `bom.csv` | BOM file | Comment, designators, footprint and **LCSC** part number of every assembled part |
| `pos.csv` | CPL (placement) file | Position, rotation and side of every assembled part, both sides |

Where to get them:

- **Release**: on a `v*-revA` hardware tag they are committed under `pcb/production/left/` and
  `pcb/production/right/` (crkbd style) and attached to the GitHub release.
- **CI**: every run of the `pcb` workflow uploads them as the `jlc` artifact.
- **Locally**: `just pcb left` and `just pcb right` write them to `build/<side>/jlc/`. You need
  Docker; the pipeline runs KiCad 10, Freerouting and KiKit in pinned containers.

J3 (display socket), JP1, the test pads and the mounting holes are left out of the BOM and CPL on
purpose. The builder fits J3.

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
   **[G3]** parts must be re-checked on the day you order.
4. In the placement preview, check in particular:
   - U1 (RP2040): the pin-1 dot matches the silkscreen;
   - J1 (USB-C): the mouth faces off the back edge;
   - J2 (TRRS): the mouth faces off the inner edge of the bump;
   - the bottom side: every hot-swap socket sits on its two pads, and every diode's cathode bar is
     on the row side.
5. Repeat for the other side.

## Costs

JLCPCB charges a one-off loading fee per **extended** part and design. This board uses these extended
parts: C2040 (RP2040), C113767 (flash), C91749 (crystal), C7519 (ESD), C95562 (TRRS jack), C165948
(USB-C), C2803348 (hot-swap socket), C455280 (tact switch) and the PTC. Expect the fees for both
designs, plus the two-sided Standard assembly setup, to dominate the price of a small order. The
hot-swap sockets (74 per keyboard) are the most expensive line.

## After delivery

Follow the [build guide](buildguide_en.md): check the boards, flash them bare, then fit the
display socket.

## Case

The case is not ordered here. [case.md](case.md) covers the case files and how the reference
project orders its CNC aluminium case.
