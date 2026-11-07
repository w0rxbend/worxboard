# Bill of materials

Rev A (spec §7). JLCPCB buys and fits every part in the first table, on both sides, the display
socket J3 included: nothing is soldered on the PCB by hand. For an order, the files in
[`pcb/production/<side>/`](../pcb/production/) (`bom.csv`, `cpl.csv`) are the authority: see
[ordering-jlcpcb.md](ordering-jlcpcb.md). The tables below are generated from the same source
(`pcb/scripts/design.py`) and checked against both committed boards by `just docs-gen`. What you
buy yourself (switches, keycaps, displays, cables, screws) is in [shopping-list.md](shopping-list.md).

**Status key**

| Flag | Meaning |
|---|---|
| **[C]** | Verified from the Corne v4.1 JLC BOM ([foostan/crkbd](https://github.com/foostan/crkbd)) |
| **[J]** | Verified against JLC's own part record (library type, stock, assembly process) and its footprint (`pcb/scripts/cpl_check.py`) |
| G1, G2 | The part is what the display gate G1 or the TRRS jack gate G2 checks |

The spec's **[G3]** flags are gone: every one of those lines passed gate G3
([verification.md](verification.md#g3-parts-stock-and-track-width)).

## Per half, assembled by JLCPCB

Both halves have the same parts and references. The only difference between the two PCBs is the
TRRS TX/RX crossover in the netlist (R11/R12). Matrix parts are numbered per key: socket `SK<n>`
and diode `D<n>`, n = 101…137 in [matrix.md](matrix.md#sockets-and-diodes) order.

<!-- BEGIN GENERATED: bom_assembled (site/gen_docs.py from pcb/scripts/design.py; run `just docs-gen`) -->
| Designators | Qty | Part | LCSC | Footprint | Side | Status | Extended |
|---|---|---|---|---|---|---|---|
| U1 | 1 | RP2040 microcontroller | [C2040](https://jlcpcb.com/partdetail/C2040) | `QFN-56-1EP_7x7mm_P0.4mm_EP3.2x3.2mm` | top | [C] | yes |
| U2 | 1 | W25Q128JVSIQ, 16 MB QSPI flash | [C97521](https://jlcpcb.com/partdetail/C97521) | `SOIC-8_5.3x5.3mm_P1.27mm` | top | [J] |  |
| C5, C8–C17 | 11 | 100 nF 0402 | [C1525](https://jlcpcb.com/partdetail/C1525) | `C_0402_1005Metric` | top | [C] |  |
| Y1 | 1 | 12 MHz crystal, CL 18 pF, 3225 (YXC XL2EL89CRI-111YLC-12M) | [C49304726](https://jlcpcb.com/partdetail/C49304726) | `Crystal_SMD_3225-4Pin_3.2x2.5mm` | top | [J] | yes |
| R7, R9, R11, R12 | 4 | 1 kΩ 0402 | [C11702](https://jlcpcb.com/partdetail/C11702) | `R_0402_1005Metric` | top | [C] |  |
| C6, C7 | 2 | 27 pF 0402 | [C1557](https://jlcpcb.com/partdetail/C1557) | `C_0402_1005Metric` | top | [C] | yes |
| R5, R6, R8, R10, R13 | 5 | 10 kΩ 0402 | [C25744](https://jlcpcb.com/partdetail/C25744) | `R_0402_1005Metric` | top | [C] |  |
| SW1 | 1 | TS-1088R-02026 tact switch (BOOT) | [C455280](https://jlcpcb.com/partdetail/C455280) | `SW_SPST_TS-1088-xR020` | top | [C] | yes |
| SW2 | 1 | TS-1088R-02026 tact switch (RESET) | [C455280](https://jlcpcb.com/partdetail/C455280) | `SW_SPST_TS-1088-xR020` | top | [C] | yes |
| C4, C18, C19 | 3 | 1 µF 0402 | [C52923](https://jlcpcb.com/partdetail/C52923) | `C_0402_1005Metric` | top | [C] |  |
| J1 | 1 | HRO TYPE-C-31-M-12, USB-C 16P | [C165948](https://jlcpcb.com/partdetail/C165948) | `USB_C_Receptacle_HRO_TYPE-C-31-M-12` | top | [J] | yes |
| R1, R2 | 2 | 5.1 kΩ 0402 | [C25905](https://jlcpcb.com/partdetail/C25905) | `R_0402_1005Metric` | top | [C] |  |
| R3, R4 | 2 | 27 Ω 0402 | [C2909343](https://jlcpcb.com/partdetail/C2909343) | `R_0402_1005Metric` | top | [C] | yes |
| U4, U5 | 2 | USBLC6-2SC6 ESD array (USB, TRRS) | [C7519](https://jlcpcb.com/partdetail/C7519) | `SOT-23-6` | top | [J] | yes |
| D1 | 1 | B5819W, 1 A Schottky | [C8598](https://jlcpcb.com/partdetail/C8598) | `D_SOD-123` | top | [J] |  |
| C1–C3 | 3 | 10 µF 0402 | [C15525](https://jlcpcb.com/partdetail/C15525) | `C_0402_1005Metric` | top | [C] |  |
| U3 | 1 | AP2112K-3.3TRG1, 600 mA LDO | [C51118](https://jlcpcb.com/partdetail/C51118) | `SOT-23-5` | top | [J] | yes |
| F1 | 1 | nSMD025-24V PTC, 250 mA hold, 24 V | [C70069](https://jlcpcb.com/partdetail/C70069) | `Fuse_1206_3216Metric` | top | [J] | yes |
| J2 | 1 | PJ-320D-4A TRRS jack, SMD | [C95562](https://jlcpcb.com/partdetail/C95562) | `Jack_3.5mm_PJ320D_Horizontal` | top | [J], G2 | yes |
| J3 | 1 | 1×4 2.54 mm female socket, 5.0 mm, **THT** (OLED, G1) | [C42163122](https://jlcpcb.com/partdetail/C42163122) | `PinSocket_1x04_P2.54mm_Vertical_H5.0mm` | top | [J], G1 | yes |
| R14, R15 | 2 | 4.7 kΩ 0402 (OLED I2C pull-ups) | [C25900](https://jlcpcb.com/partdetail/C25900) | `R_0402_1005Metric` | top | [C] |  |
| SK101–SK137 | 37 | MX hot-swap socket CPG151101S11-16 (HanElectricity) | [C41430893](https://jlcpcb.com/partdetail/C41430893) | `SW_MX_Hotswap_Kailh` | **bottom** | [J] | yes |
| D101–D137 | 37 | 1N4148W switching diode | [C81598](https://jlcpcb.com/partdetail/C81598) | `D_SOD-123` | **bottom** | [J] |  |

23 BOM lines, 121 parts per half, 74 of them on the bottom side.
<!-- END GENERATED: bom_assembled -->

- **Stock.** Check it on the day you order: `just pcb-stock left 5` (both halves draw on the same
  stock). On 2026-11-04 at 05:17 UTC every line passed for 5 assembled boards per half. The thinnest
  were C95562 (5 513), C27985230 (6 294), C51118 (12 075) and C49304726 (13 833). Alternates are in
  [ordering-jlcpcb.md](ordering-jlcpcb.md#if-a-part-is-out-of-stock).
- **Replaced parts.** The discontinued Kailh socket C2803348, the flash C113767 and the low-stock
  crystal C91749 were replaced by C41430893, C97521 and C49304726 (deviation ELEC-1). `stock.py` and
  `netcmp.py` fail if one of the retired numbers comes back.
- **J3** is the only through-hole part, a 5.0 mm socket that JLC hand-solders (ELEC-3). A stock
  nice!view plugs into it on its own header.
- **F1** is WS2's choice for the spec's "PTC 1206, 250 mA hold" (deviation WS2a-4).
- **Placement.** `cpl.csv` carries a JLC correction for U1, U2, U3–U5, J1, J2, J3 and the
  sockets (`pcb/scripts/jlc_rotations.csv`). `cpl_check.py` proved every placement against JLC's own
  footprint of the part: 119 of 119 per half (PKG-2). The table is in
  [ordering-jlcpcb.md](ordering-jlcpcb.md#how-the-package-is-made-and-checked). JLC's preview draws its
  own footprint of each part. Check it as
  [ordering-jlcpcb.md](ordering-jlcpcb.md#placement-preview-checklist) describes, because JLC does not
  document its bottom-side convention.

## Not in the JLC BOM or placement file

These footprints are copper or holes only. They are marked "exclude from BOM / position files" on
the boards, and stage D fails if one of them reaches `bom.csv` or `cpl.csv` (`netcmp.py --board`,
deviation ELEC-6).

<!-- BEGIN GENERATED: bom_excluded (site/gen_docs.py from the committed boards; run `just docs-gen`) -->
| Designators | Qty | What | Why |
|---|---|---|---|
| JP1 | 1 | solder jumper VSYS → F1 → VLINK, bridged | copper only; cut it for split-powered mode |
| JP2 | 1 | 3-pad solder jumper: J3 pin 1 = GND (pads 1-2, bridged) or 3V3 (2-3) | copper only; swap with JP3 for a VCC-GND OLED (DISP-1) |
| JP3 | 1 | 3-pad solder jumper: J3 pin 2 = 3V3 (pads 1-2, bridged) or GND (2-3) | copper only; swap with JP2 for a VCC-GND OLED (DISP-1) |
| TP1–TP11 | 11 | Ø1.0 mm test pads: TP1 `DISP_DC`, TP2 `DISP_RST`, TP3 `DISP_BL`, TP4 GP22, TP5 GP23, TP6 GP24, TP7 GP25, TP8 `SWCLK`, TP9 `SWDIO`, TP10 `GND`, TP11 `TRRS_DET` | copper only |
| H1–H8 | 8 | M2.5 mounting holes, NPTH Ø2.7 | drilled |
| STAB_T4, STAB_T5 | 2 | 2u stabiliser holes (board-only footprint, no symbol) | drilled |
<!-- END GENERATED: bom_excluded -->

## JLC fees

In Standard PCBA, the only kind that places both sides, JLC charges the same $1.53 loading fee for
every unique part, **basic or extended** (price page, updated 2026-10-22). The "Extended" column
above therefore does not change the price of this board. JLC's $3.07 extended-part fee applies to
Economic PCBA only. The left and right boards are two designs, so each pays its own setup, stencil
and loading fees. The full estimate is in [ordering-jlcpcb.md](ordering-jlcpcb.md#cost-estimate).

## Gates

The gates of spec §7 blocked **ordering**. All three pass now. The evidence is in
[verification.md](verification.md); this table is its summary.

| Gate | What is checked | Result |
|---|---|---|
| **G1** | nice!view size and pin order, which end pin 1 is, the module and viewing area against the pocket and window, and the stack height | **PASS**: J3 pin 1 (MOSI) at the module's pin 1 on both halves, a gate in stages C and D; the header row at y 39.925; the glass ≤ 9.75 mm above the PCB under a pocket ceiling at 10.0 mm; fit check 0 mm³ |
| **G2** | PJ-320D height, the pad map against the drawing, and the body against the case | **PASS**: 5.0 mm tall, pad map as drawn, the 14.1 × 6.1 mm body relieved in the case with ≥ 0.38 mm at its corners, a gate in `just model`; fit check 0 mm³ |
| **G3** | Every LCSC number and its stock, the PTC choice, JLC's 2-layer rules, and the placement file | **PASS**: 21 of 21 lines in stock on 2026-11-04 with none retired; 0.127 mm track rule against JLC's 0.10; 119 of 119 placements proven against JLC's footprints |

What only a built board can confirm is listed under
[not verified on hardware](verification.md#not-verified-until-a-board-is-built). On the order day,
re-run the stock check (`just pcb-stock left 5`).
