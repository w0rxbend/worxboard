# Ordering the PCBs from JLCPCB (turnkey)

This page takes you through one turnkey order at [JLCPCB](https://jlcpcb.com) for one keyboard. JLC
makes both PCBs, buys every part, places both sides, hand-solders the display socket J3 and ships the
boards. When they arrive, nothing on the PCB is left to solder. The left and right boards are **two
separate designs**: each is its own item in one cart.

The case is a separate order (JLCCNC and JLC3DP, [`case/production/`](../case/production/README.md)).
Switches, keycaps, displays, cables and screws come from other shops: see
[shopping-list.md](shopping-list.md).

> [!IMPORTANT]
> Gates G1 to G3 pass ([verification.md](verification.md#summary)), and the order package is checked
> in CI on every push. Rev A has still **not been built**. Order 2 assembled boards per side (one
> spare), test them ([build guide](buildguide_en.md)), and only then order the case in aluminium.

## Contents

- [What you upload](#what-you-upload)
- [Before you order](#before-you-order)
- [Step by step](#step-by-step)
- [Placement preview checklist](#placement-preview-checklist)
- [If a part is out of stock](#if-a-part-is-out-of-stock)
- [Cost estimate](#cost-estimate)
- [After the order is placed](#after-the-order-is-placed)
- [When the boards arrive](#when-the-boards-arrive)
- [How the package is made and checked](#how-the-package-is-made-and-checked)

## What you upload

Everything is committed under [`pcb/production/`](../pcb/production/): one folder per side.

| JLC upload field | Left | Right | Contents |
|---|---|---|---|
| Gerber file | [`left/gerbers.zip`](../pcb/production/left/gerbers.zip) | [`right/gerbers.zip`](../pcb/production/right/gerbers.zip) | the **panel**, 198.84 × 174.75 mm: the board in a frame with rails, mouse-bite tabs, 3 fiducials per side and 4 tooling holes |
| BOM file | [`left/bom.csv`](../pcb/production/left/bom.csv) | [`right/bom.csv`](../pcb/production/right/bom.csv) | 22 lines, 21 LCSC part numbers (SW1 and SW2 share one) |
| CPL file | [`left/cpl.csv`](../pcb/production/left/cpl.csv) | [`right/cpl.csv`](../pcb/production/right/cpl.csv) | 119 placements, 74 on the bottom, with JLC's rotation and centre corrections applied |

- `worxboard-<side>-jlc-order.zip` in each folder holds the same three files plus the side's
  [README](../pcb/production/left/README.md). The README repeats the order form in short.
- `bare-board/` holds the board without a frame (182.84 × 158.75 mm), for an order where JLC adds
  the rails itself. Use it only if JLC refuses the panel. Its README gives the form changes and the
  remark to paste.
- The panel is the default. JLC's assembly terms want parts at least 2.5 mm from the board edge, or
  rails. Here J1 (USB-C) and J2 (TRRS) overhang the edge by design, and several thumb sockets sit
  closer than 2.5 mm (deviation BOARD-7). The panel's 2 mm milled slot gives them room, and it has
  no tab in front of J1 or J2.

## Before you order

1. **CI is green on the commit you order from.** The
   [`pcb` workflow](https://github.com/w0rxbend/worxboard/actions/workflows/pcb.yml) rebuilds both
   order packages from the committed boards and fails on any byte of difference ("Order package
   left/right"). It also redraws the placement overlays ("CPL overlay drawings").
2. **Stock, on the day.** Run `just pcb-stock left 5`. It checks the live JLC stock of every BOM line
   for 5 assembled boards per half, both halves together, and it needs the network. On
   2026-11-04 at 05:17 UTC every line passed. The thinnest were C95562 (TRRS jack, 5 513),
   C27985230 (J3, 6 294), C51118 (LDO, 12 075) and C49304726 (crystal, 13 833). If a line fails,
   see [If a part is out of stock](#if-a-part-is-out-of-stock).
3. **The files.** Download each side's `worxboard-<side>-jlc-order.zip` from GitHub (open the file
   in [`pcb/production/`](../pcb/production/), then *Download raw file*) or take them from a clone,
   then unzip them. Do not use `build/<side>/jlc/` or the CI `worxboard-pcb-<side>` artifacts: those
   are KiKit's raw bare-board files, without the panel and in KiKit's own column names.
4. A JLCPCB account with a shipping address. Optionally, run the Gerbers through
   [JLCDFM](https://dfm.jlcpcb.com) first: it shows what JLC's engineers will see.

## Step by step

Do steps 1 to 8 for the **left** side, then again for the **right** side with `pcb/production/right/`.
JLC renames form options now and then, so pick the closest match. The values are what matters.

### 1. Upload the Gerbers

On [jlcpcb.com](https://jlcpcb.com), open *Instant Quote* and upload `gerbers.zip` as the Gerber
file. JLC should read **2 layers** and **198.84 × 174.75 mm**. If it shows about 183 × 159 mm, you
uploaded the bare board.

### 2. PCB options

| Option | Value | Why |
|---|---|---|
| Base material | FR-4 | |
| Layers | **2** | |
| Dimensions | 198.84 × 174.75 mm (read from the Gerbers) | the panel |
| PCB qty | **5** | the minimum; you get 5 panels, of which the PCBA quantity are assembled |
| Product type | Industrial/Consumer electronics | |
| Different design | 1 | one board per panel |
| Delivery format | **Panel by Customer** (if the form asks for the panel format: 1 column × 1 row) | the frame is in the Gerbers |
| PCB thickness | **1.6 mm** | the case stack is built on it |
| PCB colour | any (green is cheapest and fastest) | the mask webs at the QFN (about 0.2 mm) suit every colour |
| Silkscreen | the default for the colour | |
| Material type | FR-4 TG135 (the default) | |
| Surface finish | **ENIG** (1 U" gold) | flat pads for the 0.4 mm QFN and the USB-C |
| Outer copper weight | 1 oz | |
| Via covering | **Tented** | |
| Min via hole size / diameter | 0.3 mm / (0.4/0.45 mm), the default | every via is 0.3 / 0.6 mm |
| Board outline tolerance | ±0.2 mm (regular) | |
| Confirm production file | **Yes** | you approve the panel JLC will make |
| Mark on PCB | none (the default since 2026-05) | the boards carry their own label |
| Electrical test | flying probe, the default | |
| Gold fingers, castellated holes, edge plating, press-fit | No | |
| Build time | standard | JLC adds $15.71 per design for an expedited panel order |

### 3. PCB assembly options

Turn on **PCB Assembly** at the bottom of the form.

| Option | Value | Why |
|---|---|---|
| PCBA type | **Standard** | Economic places one side only; this board has 74 parts on the bottom |
| Assembly side | **Both sides** | top: the RP2040 cluster, USB-C, TRRS and J3; bottom: 37 sockets and 37 diodes |
| PCBA qty | **2** | one for the keyboard and one spare; 5 adds about $27 per design ([costs](#cost-estimate)) |
| Tooling holes | **Added by Customer** | 4 non-plated Ø2.0 mm holes in the rail corners |
| Edge rails / fiducials | **Added by Customer** | rails 6 mm or wider; 3 fiducials per side, Ø1.0 mm copper in a Ø2.0 mm opening, 4.0 mm from the edges (JLC asks for 3.85 mm) |
| Confirm parts placement | **Yes** | an engineer sends you the placement for approval before production |
| Depanel / remove edge rails | No | break the tabs yourself ([below](#when-the-boards-arrive)) |
| Other advanced options | defaults | |

You can paste this as the assembly remark. It is optional, but it saves a question:

```
Panel by customer: 1 board in a frame, 6 mm rails, 3 fiducials per side, 4 tooling holes (2.0 mm).
J1 (USB-C) and J2 (TRRS) overhang the board edge into the milled slot on purpose.
Bottom side: 37 hot-swap sockets SK101-SK137 and 37 diodes D101-D137. J3 is a THT socket (hand solder).
Ship with the frame attached.
```

### 4. Check the board views

JLC shows the top and the bottom of the Gerbers. You should see the board inside its frame, the three
copper fiducials on each side of the rails and the four holes in the rail corners. Continue.

### 5. Upload the BOM and the CPL

Upload `bom.csv` as the BOM file and `cpl.csv` as the CPL file, then *Process BOM & CPL*. The
headers are JLC's own (`Comment,Designator,Footprint,LCSC Part #` and
`Designator,Mid X,Mid Y,Layer,Rotation`), so no column mapping should be needed. If JLC asks,
map them one to one.

### 6. Check the parts list

JLC lists 22 lines (SW1 and SW2 are two lines of the same part). For each line:

- the line is **selected** (ticked) and shows the LCSC number from [bom.md](bom.md#per-half-assembled-by-jlcpcb);
- the quantity matches: 37 for the sockets and for the diodes, 11 for C1525;
- there is no *shortage* and no *No Part Selected*.

J3 (C27985230) is the only through-hole part. JLC hand-solders it, and the quote carries a
hand-soldering fee for it. Every other part is SMT. The library type (basic or extended) does not
change the price in Standard PCBA: every part pays the same loading fee.

### 7. Check the placement preview

JLC draws its own footprint of each part where the CPL puts it. Work through the
[checklist below](#placement-preview-checklist), on the top and then on the bottom side. Do not
move or rotate anything in the viewer unless a part is clearly wrong. If one is, write the
designator and what you saw in the remark: the engineer checks it at *Confirm parts placement*.

### 8. Product description, then add to cart

On the *Quote & Order* page, choose the product description that fits a keyboard PCB assembly,
such as an entry for computer peripherals or keyboards. JLC uses it for the customs declaration. Its
[tariff FAQ](https://jlcpcb.com/help/article/us-tariff-policy-faq) (updated 2026-10-29) lists HS
847330, "computer parts and accessories", for PCBA orders, which it calls intermediate products, and
JLC may change the code to match the goods. Save the item to the cart.

Repeat steps 1 to 8 for the right side.

### 9. Check out

In the cart, check both items: two designs, each 5 PCBs and 2 assembled, Standard, both sides.
Choose a shipping method. Shipments to individuals in the US go DDP: JLC collects the duties up
front. Then pay.

## Placement preview checklist

Every placement in `cpl.csv` was checked against JLC's own footprint of that part: KiKit places it
where the CPL says, and `pcb/scripts/cpl_check.py` compares it with the KiCad pads. All 119 of 119
pass on each half. Each drawing below shows JLC's footprint, placed from the CPL, over the KiCad pads. Bottom-side
parts are drawn as seen through the board from the top. What the preview still has to confirm is
how JLC's own viewer applies the CPL, the bottom side above all. JLC does not document its
bottom-side convention, and the CPL follows the one that KiKit, kicad-jlcpcb-tools and KiBot use.

**Top side**

| Part | Check in the preview | Drawing |
|---|---|---|
| U1, RP2040 (QFN-56) | the chip's pin-1 dot sits at the pin-1 corner of the silkscreen. The left U1 is turned 180° from the right one on purpose (CPL 180° left, 0° right) | [cpl-u1-rp2040-qfn56.svg](images/cpl-u1-rp2040-qfn56.svg) |
| U2, flash (SOIC-8) | the pin-1 dot or bevel at pad 1 | [cpl-u2-flash-soic8.svg](images/cpl-u2-flash-soic8.svg) |
| U3, LDO (SOT-23-5) | three leads on the three-pad side, two on the two-pad side | [cpl-u3-ldo-sot23-5.svg](images/cpl-u3-ldo-sot23-5.svg) |
| U4, U5, ESD (SOT-23-6) | the pin-1 mark at pad 1. The left U4 sits at an angle (61.46°) | [cpl-u4-u5-esd-sot23-6.svg](images/cpl-u4-u5-esd-sot23-6.svg) |
| Y1, crystal (3225) | the pin-1 corner mark at pad 1 | [cpl-y1-crystal-3225.svg](images/cpl-y1-crystal-3225.svg) |
| J1, USB-C | the **mouth faces out over the back edge**, the two plastic pegs sit in the two small holes, and the four shell legs sit in their slots | [cpl-j1-usb-c.svg](images/cpl-j1-usb-c.svg) |
| J2, TRRS jack | the **barrel mouth is at the bump edge**, pointing out of the board, with the two pegs in their holes | [cpl-j2-trrs-pj320d.svg](images/cpl-j2-trrs-pj320d.svg) |
| J3, display socket (THT) | the body lies along the row of five holes, one contact per hole | [cpl-j3-display-socket.svg](images/cpl-j3-display-socket.svg) |
| D1, Schottky (SOD-123) | the cathode band at pad 1 (the VSYS side) | [cpl-d1-schottky-sod123.svg](images/cpl-d1-schottky-sod123.svg) |
| SW1, SW2, F1, 0402 R and C | on their pads | [tact](images/cpl-sw-tact-ts1088.svg), [PTC](images/cpl-f1-ptc-1206.svg), [R](images/cpl-r-0402.svg), [C](images/cpl-c-0402.svg) |

**Bottom side**

| Part | Check in the preview | Drawing |
|---|---|---|
| SK101–SK137, hot-swap sockets | the socket's curved **notch wraps the big round switch-centre hole**, and its two metal terminals sit on the two pads. A socket turned 180° still covers both pads, but its body then sits over the centre hole. The thumb sockets SK132–SK137 sit at 155° or 205° | [cpl-sk-hotswap-socket.svg](images/cpl-sk-hotswap-socket.svg) |
| D101–D137, diodes (SOD-123F) | the **cathode band at pad 1**, the ROW side | [cpl-d101-diode-sod123f.svg](images/cpl-d101-diode-sod123f.svg) |

![SK101 and the thumb sockets: JLC's socket footprint over the KiCad pads](images/cpl-sk-hotswap-socket.svg)

![U1: JLC's QFN-56 footprint over the KiCad pads, left and right](images/cpl-u1-rp2040-qfn56.svg)

> [!WARNING]
> If **every** socket and diode on the bottom shows turned by 180°, JLC's viewer uses another
> bottom-side convention. Do not edit the files: say so in the remark, or answer when JLC sends the
> placement for confirmation. A single part that is off is more likely a slip in JLC's viewer. Note
> it the same way.

## If a part is out of stock

Run `just pcb-stock left 5` again on the day: it names the line that fails. Then, in this order:

1. **Swap on JLC's parts page, only to a pre-checked alternate.** Click the part's search or
   replace button and enter the alternate's LCSC number. JLC places by designator from the same
   CPL, and the alternates marked "yes" below have JLC footprints that take the same correction as
   the original. `cpl_check.py` checked them (`pcb/scripts/jlc_footprints.json`).
2. **Any other alternate** must have the same package, value and pinout. Check it in the placement
   preview with extra care, because its JLC footprint may have another origin or zero angle. For
   the next order, put it in `pcb/scripts/design.py` and rebuild the package, so that
   `cpl_check.py` proves it.
3. **Do not untick a part** to order without it, unless you accept soldering it yourself.

| Ref | Part | Alternate | Stock 2026-11-04 | Placement checked | Notes |
|---|---|---|---|---|---|
| SK101–SK137 | C41430893 | **C49352235** (HanElectricity CPG151101S11-2) | 26 943 | yes, same row | its body clears the switch post by 0.50 mm at 180° |
| Y1 | C49304726 | **C9002** (YXC X322512MSB4SI, basic) | 286 104 | yes, no row | CL 20 pF against the 18 pF the 27 pF caps give: a few tens of ppm, far inside USB's ±2500 ppm (ELEC-1) |
| J3 | C27985230 | **none that fits the case** | | | the 5.7 mm sockets (C46061764, C55218875) take the same row but lift the glass 0.7 mm, to 10.45 mm above the PCB at full tolerance, over the pocket ceiling at 10.0 mm (CASE-1). If J3 is out, wait for stock, or untick J3 and solder the 5 mm socket that ships with the nice!view yourself |
| U3 | C51118 | C82942 (ME6211C33M5G-N) | 370 432 | no | same SOT-23-5 pinout (1 VIN, 2 GND, 3 EN, 4 NC, 5 VOUT; both datasheets), 500 mA |
| U4, U5 | C7519 | C2687116 (UMW USBLC6-2SC6) | 109 130 | no | a second-source copy of the same part |
| F1 | C70069 | C70070 (nSMD025-30V) | 46 671 | no | the same 1206 PTC, 250 mA hold, rated 30 V |
| R3, R4 | C2909343 | C25100 (27 Ω 0402) | 36 392 | no | any 27 Ω 0402 |
| other 0402 R and C | | any part of the same value, package and dielectric (prefer basic parts) | | no | |
| U1, U2, J1, J2, SW1, SW2, D1, D101–D137 | | no alternate checked | | | U1 has one source. U2 has huge stock (74 052) as a basic part. For J1 and J2 any other part needs another footprint, so wait for stock |

The retired parts C2803348 (the Kailh socket), C113767 (the old flash) and C91749 (the old
crystal) must not come back: `stock.py` and `netcmp.py` fail on them.

## Cost estimate

Estimated on **2026-11-04**, for one keyboard: two designs, each with 5 PCBs and 2 assembled. The
assembly rates are from JLC's [PCBA price page](https://jlcpcb.com/help/article/pcb-assembly-price)
(last updated 2026-10-22). Part prices are JLC's live unit prices for the quantity JLC buys, which
is 2 boards plus its attrition, read at 05:15 UTC. JLC publishes no price formula for the bare PCB
or for shipping, so those two lines are ranges, not quotes. Your cart shows the real figures.

| Line | Per design | Both designs | Basis |
|---|---|---|---|
| PCB fabrication, 5 panels, 2 layers, ENIG | $20–50 | $40–100 | not quoted. The panel is 347 cm², under JLC's 650 cm² large-size limit |
| Setup, Standard, double-sided | $51.12 | $102.24 | price page |
| Stencil, double-sided | $16.42 | $32.84 | price page |
| Part loading, 20 SMT part numbers × $1.53 | $30.60 | $61.20 | the same for basic and extended parts in Standard PCBA. JLC does not say whether the THT J3 counts: +$1.53 if it does |
| SMT joints, 330 per board × 2 × $0.0016 | $1.06 | $2.12 | 335 joints per board, less J3's 5 |
| THT hand soldering, J3: $3.58 per order + 10 joints × $0.0164 | $3.74 | $7.48 | price page |
| X-ray for the QFN, 2 × $1.64 | $3.28 | $6.56 | the price page lists X-ray as required for QFN |
| Parts for 2 boards, with attrition | $16.17 | $32.34 | the largest lines: U2 $4.92, sockets $3.42, U1 $2.18 |
| Confirm parts placement | $0.45 | $0.90 | price page |
| Packing | $0.52 | $1.04 | $0.50 + $0.00003 per cm² |
| **PCBA subtotal** | **$123.36** | **$246.72** | |
| Fixtures, if charged: 2 × $8.21 | $0–16.42 | $0–32.84 | listed on the price page without a condition |
| Shipping | | $20–45 | not quoted. It depends on the country and the carrier |
| **Total** | | **about $307–425** | before import duty and VAT |

- **Extended-part fees:** none apply. JLC's separate fee per extended part ($3.07) is for Economic
  PCBA only, which this board cannot use.
- **5 assembled per side** instead of 2 adds about $27 per design: parts $35.90, X-ray $8.20, joints.
- No panel fee: JLC charges it only when one panel holds more than one design.
- The case is quoted by JLCCNC and JLC3DP when you upload the files
  ([`case/production/`](../case/production/README.md)). The off-board parts are in
  [shopping-list.md](shopping-list.md).

## After the order is placed

JLC's engineers review the files after payment. A question puts the order on hold until you answer
it in the order page.

- **Confirm production file.** JLC posts the panel as it will be made. Check that it is the
  198.84 × 174.75 mm panel from the Gerbers: no extra holes inside the board outline, no V-cut, and
  no tab in front of J1 (back edge) or J2 (bump edge). Then approve it.
- **Confirm parts placement.** JLC posts the placement on both sides. Work through the
  [checklist](#placement-preview-checklist) again, then approve.

Likely questions and the answers:

| Question | Answer |
|---|---|
| Parts closer than 2.5 mm to the board edge (J1, J2, thumb sockets) | Intended. J1 and J2 overhang the edge into the 2 mm milled slot of the customer panel. The rails are on the frame. |
| J1 or J2 overhangs the board outline | Intended: the connector mouths are the case openings. |
| Tooling holes are 2.0 mm, not 1.152 mm | They follow JLC's SMT guideline of 2026-09. Add your own on the rails if you need them, but none inside the board. |
| Bottom-side rotation of the sockets or diodes | As the CPL gives it: each socket's notch wraps the round switch-centre hole, and each diode's cathode band is at pad 1. |
| Silkscreen over pads or past the edge | Clip it. |
| J3 is through-hole | Yes: C27985230, hand-soldered from the top, 5 joints. |

## When the boards arrive

1. Break each board out of its frame at the 14 mouse-bite tabs. Bend each tab gently, away from
   J1 and J2: those two overhang the edge.
2. File or sand every tab nub flush with the board edge. The case leaves only about 0.3 mm round
   the PCB.
3. Keep the spare assembled board and the three bare panels per side.
4. Continue with the [build guide](buildguide_en.md): check, flash and test the boards before the
   case goes on.

## How the package is made and checked

| Command | What it does |
|---|---|
| `just pcb-production <side>` | builds `pcb/production/<side>/` from the committed board: KiKit panel (`pcb/scripts/panel.json`, `panel_tabs.py`), Gerbers, BOM and CPL in JLC's formats, README, order zip, bare-board files |
| `just pcb-production-check <side>` | rebuilds and requires the committed package to match byte for byte. CI's "Order package" jobs run this |
| `just pcb-stock <side> [boards]` | `jlc_check.py`: formats, BOM = CPL = the 119 parts `design.py` fits, panel size, rails, fiducials, tooling holes, plus live JLC stock |
| `just pcb-cpl-images` | redraws `docs/images/cpl-*.svg` with `cpl_check.py` (CI's "CPL overlay drawings" job) |
| `just pcb-fab <side>` | stage D: the board's own fab outputs, with `netcmp.py --board` (the parts, LCSC numbers and J3's pin-1 end) and `cpl_check.py` |

The CPL corrections live in `pcb/scripts/jlc_rotations.csv`. KiKit applies them by footprint
name. A bottom-side part gets 180° minus the KiCad angle plus the correction, with the X and Y offset
not mirrored:

| Footprint | Parts | X; Y; rotation |
|---|---|---|
| `QFN-56-1EP_7x7mm_P0.4mm_EP3.2x3.2mm` | U1 | 0; 0; 0 |
| `SOIC-8_5.3x5.3mm_P1.27mm` | U2 | 0; 0; 270 |
| `SOT-23-5`, `SOT-23-6` | U3, U4, U5 | 0; 0; −90 |
| `USB_C_Receptacle_HRO_TYPE-C-31-M-12` | J1 | 0; −1.394; 0 |
| `Jack_3.5mm_PJ320D_Horizontal` | J2 | 0.776; 0; 90 |
| `worxboard:SW_MX_Hotswap_Kailh` | SK101–SK137 | 0.635; 3.81; 180 |
| `worxboard:PinSocket_1x05_P2.54mm_Vertical_H5.0mm` | J3 | 0; 5.08; 270 |
| everything else (0402 R and C, SOD-123, SOD-123F, 3225 crystal, TS-1088, 1206) | | no correction |

Each row was derived from JLC's footprint of that LCSC part, which is fetched by
`pcb/scripts/jlc_footprints.py` from the EasyEDA / JLCEDA library. Each row is proven by
`cpl_check.py`, which also fails the wrong values: U1 at 270° lands 6.1 mm off, and a socket at 0°
puts its body 1.13 mm into the switch's centre-post hole. Deviations PKG-1 to PKG-4 have the details.
