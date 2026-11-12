# Ordering the PCBs from PCBWay (turnkey)

This is the [PCBWay](https://www.pcbway.com) counterpart of [ordering-jlcpcb.md](ordering-jlcpcb.md):
one turnkey order for one keyboard, PCBWay making both PCBs, buying the parts, placing both sides and
hand-soldering the display socket J3. The left and right boards are **two separate designs**, so each
is its own item.

> [!IMPORTANT]
> Rev B is a **four-layer** board (deviation [REVB-8](deviations.md)) and has **not been built** yet.
> Read the price from PCBWay's quote: this repo has no estimate for it. Order 2 assembled boards per side (one spare), test them
> ([build guide](buildguide_en.md)), and only then order the case in aluminium.

## What you upload

PCBWay gets the same Gerbers as JLC, but its own BOM and centroid file, from
[`pcb/production/<side>/pcbway/`](../pcb/production/). Each side's
[README](../pcb/production/left/pcbway/README.md) repeats everything below with that side's figures.

| PCBWay upload | Left | Right |
|---|---|---|
| Gerber file | [`left/gerbers.zip`](../pcb/production/left/gerbers.zip) | [`right/gerbers.zip`](../pcb/production/right/gerbers.zip) |
| BOM | [`left/pcbway/bom.csv`](../pcb/production/left/pcbway/bom.csv) | [`right/pcbway/bom.csv`](../pcb/production/right/pcbway/bom.csv) |
| Centroid (pick and place) | [`left/pcbway/centroid-panel.csv`](../pcb/production/left/pcbway/centroid-panel.csv) | [`right/pcbway/centroid-panel.csv`](../pcb/production/right/pcbway/centroid-panel.csv) |

- **The Gerbers are the panel**, 198.84 × 174.75 mm: the board in a frame with 6 mm rails, mouse-bite
  tabs, 3 fiducials per side and 4 tooling holes. J1 (USB-C) and J2 (TRRS) overhang the board edge by
  design, into the frame's 2 mm milled slot, so the panel is the default. Only if PCBWay refuses it,
  upload `bare-board/gerbers.zip` with `pcbway/centroid-bare-board.csv` and ask for rails with a routed
  gap and no tab in front of J1 and J2 (the side README has the wording).
- **Do not upload the JLC `bom.csv` or `cpl.csv`.** The JLC CPL carries JLC-only corrections
  (`pcb/scripts/jlc_rotations.csv`: the hot-swap sockets moved by 0.635 / 3.81 mm and turned 180°, J3
  moved 5.08 mm and turned, SOT-23 −90°, SOIC-8 270°, …) and JLC's bottom-side rotation (180° minus
  the KiCad angle). At PCBWay those parts land in the wrong place. The JLC BOM has only LCSC numbers.
- **`bom.csv`** has one line per part number: designators, quantity, manufacturer and manufacturer part
  number, description, package, SMD or THT, side, and the LCSC number as an alternate source. Its
  designators are the JLC BOM's.
- **`centroid-panel.csv`** is KiCad's own position file of the panel (`Designator, Value, Package,
  Mid X (mm), Mid Y (mm), Rotation, Layer`), with no correction at all, in the frame of the panel
  Gerbers.

## Coordinates and rotations

- **Frame:** the drill/place origin, which is also the Gerbers' origin: the panel's top-left corner
  (the bare board's own origin for `centroid-bare-board.csv`). Y points up, as in the Gerbers, so the
  Y values are negative. The panel centroids are the bare-board ones moved by the KiKit panel's offset,
  which stage P reads from the panel it builds: (−46.08, +22.60) mm on the left and (−15.08, +22.60) mm
  on the right for rev A; each side README gives its own.
- **Mid X / Mid Y** is each footprint's KiCad origin. For J3 (pin 1), the hot-swap sockets (the switch
  centre), J1 and J2 that is not the body centre; the side README lists how far off each is.
- **Rotation** is KiCad's angle, counter-clockwise, 0 to 360°, with KiCad's library footprint as 0°.
- **Bottom side:** X and Y are seen from the top (not negated). Seen from the top, a bottom part is its
  library footprint mirrored top to bottom, then turned by the Rotation value. Seen from the bottom, it
  is turned by **180° minus the Rotation value**, which is the number JLC's CPL carries for the parts
  without a correction.

The remark asks PCBWay to send the placement of both sides for confirmation before production. Check
it with the [JLC placement checklist](ordering-jlcpcb.md#placement-preview-checklist): the same parts,
the same polarity marks.

## Step by step

Do this for the left side, then for the right side. PCBWay renames form options now and then: pick
the closest match.

1. **PCB.** On pcbway.com, start a PCB quote and upload `gerbers.zip`. PCBWay should read **4 layers** and
   198.84 × 174.75 mm. Fill the form from the side README's *PCB order form*: **Panel by Customer**
   (tab route, X-out not accepted, 1 design), **4 layers**, FR-4, **1.6 mm**, PCBWay's standard 4-layer
   stack-up with no impedance control (inner 1 is the GND plane, inner 2 the VLED plane), min track/spacing **5/5mil**
   (the board's rule is 0.127 mm), min hole 0.3 mm, any mask colour, **white** silkscreen, UV printing
   (multi-colour) **None**, surface finish **Immersion gold (ENIG)**, **Tenting vias**, **1 oz** outer copper, **0.5 oz** inner copper.
   The *Other special request* field takes 200 characters: paste the short remark from the README.
2. **Assembly.** Turn on the assembly service: **Turnkey**, Board type **Panelized PCBs**, **Both
   sides**, 2 to 5 boards. Accept substitutes **Yes** (the remark limits them). The README gives the
   part counts the form asks for (unique parts, SMD parts, 1 QFN (U1), 1 through-hole (J3)).
   Depanel: **No**, the boards ship in their frames.
3. **Files.** Upload `pcbway/bom.csv` as the BOM and `pcbway/centroid-panel.csv` as the centroid file
   where the assembly order asks for them.
4. **Remark.** Paste the README's *Remark* into the assembly order's notes, or send it to the PCBWay
   engineer who reviews the order. It covers the overhanging connectors, J3 as the only THT part, J1's
   pin-in-paste shell legs, the bottom-side parts, the centroid convention, the substitution rules and
   the close stabiliser holes, and asks for a placement and polarity confirmation.
5. **Review.** PCBWay reviews the files and quotes the parts after you submit. Answer its questions as in
   [ordering-jlcpcb.md](ordering-jlcpcb.md#after-the-order-is-placed): the answers are the same.

## Substitutions

PCBWay buys the parts itself, by manufacturer part number. Where it cannot get one, the README's
*Substitution rules* table says what it may fit instead:

| Parts | Rule |
|---|---|
| R, C, F1 | any equivalent of the same value, size and rating |
| D1, D101–D137 | the same diode type from another maker, same package |
| Y1 | 12 MHz, 3225 four-pad, CL 18 pF; otherwise ask |
| J3 | only a 1×5 2.54 mm female header with a **5.0 mm** body (the display height depends on it) |
| SK101–SK137 | only the second source HanElectricity CPG151101S11-2 (C49352235) |
| LED101–LED137 | only an SK6812MINI-E (3.2 × 2.8 mm reverse-mount, same pinout): the cutout and pads are made for it |
| SW1, SW2 | the same TS-1088 land pattern; otherwise ask |
| U1–U7, J1, J2 | no substitute: ask first |

## Manufacturer part numbers

`pcb/scripts/mpn.json` maps each LCSC number to its manufacturer, part number, description and
package, as LCSC's product API gives them. `just pcb-mpn` rewrites it (network): it reads every LCSC
number `design.py` names (the parts of both halves and the fallbacks in its comments, less the retired
ones), every number already in the file, and any given on the command line (`just pcb-mpn C123 C456`).
Run it after adding a part to `design.py`. `just pcb-mpn-check`, and stage P in CI, fail without the
network if a number has no entry.

## How the files are made and checked

| Command | What it does |
|---|---|
| `just pcb-production <side>` | stage P: the JLC package and, as step P6, `pcbway/` (KiCad position files of the panel and the board, `pcb/scripts/pcbway.py`) |
| `just pcb-pcbway <side>` | stage P, then copies only `pcbway/` into `pcb/production/<side>/` |
| `just pcb-production-check <side>` | rebuilds and requires the committed package, `pcbway/` included, to match byte for byte (CI's "Order package" jobs) |
| `just pcb-mpn` / `just pcb-mpn-check` | refresh `mpn.json` from LCSC / check it covers `design.py` |

`pcbway.py` fails, and writes nothing, unless the designators are the JLC BOM's, every centroid lies
inside its Gerber outline, the panel centroids are the bare-board ones moved by one offset, and
re-applying `jlc_rotations.csv` and JLC's bottom-side rotation to the centroids gives the JLC CPL
within 0.01 mm and 0.01°, for every part. So each part whose footprint has no correction row sits
exactly where JLC's CPL puts it, and the two files differ by JLC's documented corrections only.
