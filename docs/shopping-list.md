# Shopping list

Everything one worxboard needs, both halves. Stock and prices are from **2026-11-04**; check them
again on the day you order.

> [!NOTE]
> The PCBs arrive with every part fitted, the display socket J3 included. The only soldering
> left is the display's own five header pins, on the display module, not on the PCB. Everything else
> plugs in or screws on.

## The four orders

| Order | Shop | What | Files and settings |
|---|---|---|---|
| PCBs, assembled | [JLCPCB](https://jlcpcb.com) | 2 designs (left, right): 5 PCBs and 2 assembled each, Standard PCBA, both sides | [`pcb/production/`](../pcb/production/), steps in [ordering-jlcpcb.md](ordering-jlcpcb.md) |
| Machined case | [JLCCNC](https://jlccnc.com) | 2 top shells, 2 bottom trays, 6 tent legs; aluminium 6061-T6, bead blast + anodize | [`case/production/jlccnc/`](../case/production/jlccnc/ORDER_NOTES.md) |
| Printed case parts | [JLC3DP](https://jlc3dp.com) | 2 plate spacers (MJF PA12), 1 tree of 8 leg foot caps (FDM TPU 95A) | [`case/production/jlc3dp/`](../case/production/jlc3dp/ORDER_NOTES.md) |
| Everything below | keyboard and hardware shops | switches, keycaps, stabilisers, displays, cables, screws, feet, thumbscrews | this page |

The case package is case revision **A3**. Its [README](../case/production/README.md) says what it
expects from the parts it holds. Order the aluminium case only after one assembled PCB has been
checked: a 3D-printed test top is cheap ([case.md](case.md#before-machining)).

## Off-board parts for one keyboard

LCSC numbers are given where LCSC stocks a part that fits. Everything else comes from keyboard or
hardware shops.

### Switches, keycaps, stabilisers

| Item | Qty | Spec | Where |
|---|---|---|---|
| MX-style switches | **74** (+ a few spares) | MX-compatible, plate-mount, **3-pin or 5-pin**: the PCB has the two Ø1.75 mm peg holes for 5-pin switches, and the Kailh-type hot-swap sockets take standard MX pins. Not Choc, Alps or other low-profile switches | any keyboard shop (Gateron, Kailh, Cherry, Akko and others). LCSC stocks HanElectricity's 3-pin MX copies: red C49234236 (2 757 in stock), brown C49234237 (3 414), blue C49234235 (9 850), black C49234238 (1 298), at about $0.11 each |
| Keycaps, 1u | **58** | | keyboard shops |
| Keycaps, 1.5u | **12** | 8 for the outer column, mounted horizontally (C0R0–C0R3 on each half), and 4 for the inner column, mounted **vertically** (C6R1, C6R2) | |
| Keycaps, 2u | **4** | the two large thumb keys per half (T4, T5), mounted **vertically** | |
| Plate-mount stabilisers, 2u | **4** | Cherry-style, clip-in, for a 1.5 mm plate. The plate cut-outs are Cherry spec, and the PCB has the Ø3.05 / Ø4.0 mm clearance holes under them. Screw-in (PCB-mount) stabilisers do not fit | keyboard shops |

- **Keycap count by size**, from [`layout.json`](../layout/build/layout.json): per half 29 × 1u,
  4 × 1.5u horizontal, 2 × 1.5u vertical and 2 × 2u vertical, 37 keys. There is no key where the
  display sits, at the top of the inner column (C6R0). On an ErgoDox that key is 1u, so a standard
  76-key ErgoDox keycap set covers the keyboard and leaves **2 × 1u spare**.
- **Profile:** a uniform profile (DSA, XDA, KAM or another row-less one) is the easy choice. The
  vertical 1.5u and 2u caps and the 25° thumb cluster otherwise need an ErgoDox-specific sculpted
  kit.
- **Next to the display:** the back edge of the C6R1 cap ends about 0.25 mm in plan from the display
  module's far end (CASE-1). Standard-size caps fit. Check an oversized cap on the first assembly.

### Displays

| Item | Qty | Spec | Where |
|---|---|---|---|
| nice!view | **2** | Sharp LS011B7DH03 memory LCD module, 36 × 14 × 2.9 mm, 5 pins in the order MOSI, SCK, VCC, GND, CS. An LS011B7DH03 breakout with the same pin order and size works too | [nicekeyboards.com](https://nicekeyboards.com/nice-view), [Typeractive](https://typeractive.xyz/products/nice-view) and other keyboard shops |

- **Header:** the nice!view ships with a 5-pin socket and a male header. J3 on the PCB is the
  socket, fitted by JLC (C27985230, 5.0 mm, the same height as the nice!view's own). You only need
  the **male header**. Solder it to the module, long pins down, and trim the pins **flush on the
  glass side**. Untrimmed, they stand about 2 mm up and hit the display pocket's ceiling. Keep the
  supplied socket as a spare (see [J3 out of stock](ordering-jlcpcb.md#if-a-part-is-out-of-stock)).
- **Stack:** the case allows the glass up to 9.75 mm above the PCB, the full tolerance of a 5.0 mm
  socket with the stock header (8.9 mm nominal; CASE-1). Do not raise the module on an extra spacer.
- A spare header: the "5-pin sockets" that nice!view shops sell are the same parts.

### Cables

| Item | Qty | Spec | Where |
|---|---|---|---|
| TRRS cable | **1** | 3.5 mm, **4-pole** (TRRS, not TRS), **straight** 1:1 wiring (the crossover is on the PCB). The plug head must be **≤ Ø6.3 mm for its first 3.7 mm** behind the metal shaft, because the plug passes a Ø6.5 mm hole in the 3 mm case wall ([case.md](case.md#trrs-cable)). Check it with calipers | keyboard shops ("TRRS cable", often coiled); audio shops (headset extension cables are TRRS) |
| USB-C cable | **1**, optionally 2 | USB 2.0 data cable (not charge-only), C to whatever your host has. The plug's overmould must fit the case's 13 × 8 mm recess round the USB-C notch. Slim plugs fit. The second cable is only needed for split-powered mode (JP1 cut) or to flash the right half without moving the cable | any shop |

### Case hardware

From [`case/production/hardware.csv`](../case/production/hardware.csv) (case revision A3, CASE-3).
No threaded inserts are needed: JLCCNC taps every thread into the aluminium top, and the plate is
milled into it.

| Item | Qty | Spec | Where |
|---|---|---|---|
| M2.5 × 12 countersunk screws | **12** | M2.5 × 0.45, 12 mm including the head, 90° head ≤ Ø5.2 mm (DIN 7991 hex socket, or ISO 7046 cross recess), steel or A2. Six per half, in T2–T4 and T6–T8 | hardware shops. LCSC C5138785 (GB819 cross recess, A2) had only 13 in stock |
| M2.5 × 10 countersunk screws | **4** | the same, 10 mm. Two per half, in T1 and T5, under the key well: **snug only** | hardware shops. LCSC had none in stock |
| Rubber feet | **8** | self-adhesive, Ø10 mm (at most Ø10.3), 2–3 mm tall. Four per half, in the Ø10.5 × 0.6 mm recesses | electronics distributors, hardware shops |
| Leg thumbscrews | **6** | M3 × 12 knurled-head thumbscrew (DIN 464 or DIN 653, head Ø ≥ 7 mm, so it bears on the leg's back face), or the stock ErgoDox EZ M3 spring thumbscrew, measured first | hardware shops. ZSA sells EZ spare parts |
| Friction washers | **6** | Ø10 × Ø3.2 mm, 0.5–1.0 mm thick, fibre, rubber or cork: one between each leg hub and its boss | hardware shops |
| Leg foot caps | 6 (8 printed) | TPU 95A, from the JLC3DP tree. Snip them off at the base and push them onto the leg spigots | JLC3DP, above |

> [!WARNING]
> **Screw lengths matter.** Every tapped hole in the top shell is blind. An M2.5 × 14 in an edge
> boss, or an M2.5 × 12 in T1 or T5, reaches past the end of the thread and stops before its head
> seats. An M3 thumbscrew may reach at most 3.7 mm past the outer and thumb bosses and 5.7 mm past
> the inner one: an M3 × 12 on the 8 mm leg hub needs its washer ([`case/production/README.md`](../case/production/README.md)).

### Tools

- A soldering iron, only for the nice!view headers (and to re-bridge JP1 if you ever cut it).
- Flush cutters, a file or sandpaper for the panel tab nubs, a craft knife if you cut JP1.
- A 1.5 mm hex key or a Phillips driver for the M2.5 screws, depending on the screws you buy.
- A Ø2.5 mm pin (a paper clip) for the BOOT and RESET buttons through the case.
- A multimeter, calipers. Optionally a key tester, a switch puller and a keycap puller.

## Summary for one keyboard

| Item | Qty |
|---|---|
| Assembled PCB, left / right (JLCPCB) | 1 / 1 (2 / 2 ordered) |
| Top shell, bottom tray, left / right (JLCCNC) | 1 each |
| Tent legs (JLCCNC) | 6 |
| Plate spacers, left / right (JLC3DP) | 1 / 1 |
| Leg foot cap tree (JLC3DP) | 1 (8 caps) |
| MX switches, 3- or 5-pin | 74 |
| Keycaps: 1u / 1.5u / 2u | 58 / 12 / 4 |
| 2u plate-mount stabilisers | 4 |
| nice!view with its header | 2 |
| TRRS cable, 4-pole, straight, slim plug | 1 |
| USB-C data cable | 1–2 |
| M2.5 × 12 / M2.5 × 10 countersunk screws | 12 / 4 |
| Rubber feet, Ø10 mm | 8 |
| M3 × 12 knurled thumbscrews and friction washers | 6 + 6 |
