# Bill of materials

Rev A (spec §7). JLCPCB assembles every part in the first table; the builder supplies the rest.
For an order, the JLC files written by the PCB pipeline (`bom.csv` and `pos.csv`, from KiKit) are
the authority: see [ordering-jlcpcb.md](ordering-jlcpcb.md). The tables below are generated from
the same source (`pcb/scripts/design.py`) and checked against both committed boards by
`just docs-gen`.

**Status key**

| Flag | Meaning |
|---|---|
| **[C]** | Verified from the Corne v4.1 JLC BOM ([foostan/crkbd](https://github.com/foostan/crkbd)) |
| **[J]** | Verified on the JLCPCB part page |
| **[G3]** | **Must be verified before ordering**: LCSC number, stock and footprint (gate G3) |
| G1, G2 | Depends on the display gate G1 or the TRRS jack gate G2 |

## Per half, assembled by JLCPCB

Both halves have the same parts and references. The only difference between the two PCBs is the
TRRS TX/RX crossover in the netlist (R11/R12). Matrix parts are numbered per key: socket `SK<n>`
and diode `D<n>`, n = 101…137 in [matrix.md](matrix.md#sockets-and-diodes) order.

<!-- BEGIN GENERATED: bom_assembled (site/gen_docs.py from pcb/scripts/design.py; run `just docs-gen`) -->
| Designators | Qty | Part | LCSC | Footprint | Side | Status | Extended |
|---|---|---|---|---|---|---|---|
| U1 | 1 | RP2040 microcontroller | [C2040](https://jlcpcb.com/partdetail/C2040) | `QFN-56-1EP_7x7mm_P0.4mm_EP3.2x3.2mm` | top | [C] | yes |
| U2 | 1 | W25Q128JVSIQ, 16 MB QSPI flash | [C113767](https://jlcpcb.com/partdetail/C113767) | `SOIC-8_5.3x5.3mm_P1.27mm` | top | [C] | yes |
| C5, C8–C17 | 11 | 100 nF 0402 | [C1525](https://jlcpcb.com/partdetail/C1525) | `C_0402_1005Metric` | top | [C] |  |
| Y1 | 1 | 12 MHz crystal, 18 pF, 3225 | [C91749](https://jlcpcb.com/partdetail/C91749) | `Crystal_SMD_3225-4Pin_3.2x2.5mm` | top | [C] | yes |
| R7, R9, R11, R12 | 4 | 1 kΩ 0402 | [C11702](https://jlcpcb.com/partdetail/C11702) | `R_0402_1005Metric` | top | [C] |  |
| C6, C7 | 2 | 27 pF 0402 | [C1557](https://jlcpcb.com/partdetail/C1557) | `C_0402_1005Metric` | top | [C] |  |
| R5, R6, R8, R10, R13 | 5 | 10 kΩ 0402 | [C25744](https://jlcpcb.com/partdetail/C25744) | `R_0402_1005Metric` | top | [C] |  |
| SW1 | 1 | TS-1088R-02026 tact switch (BOOT) | [C455280](https://jlcpcb.com/partdetail/C455280) | `SW_SPST_TS-1088-xR020` | top | [C] | yes |
| SW2 | 1 | TS-1088R-02026 tact switch (RESET) | [C455280](https://jlcpcb.com/partdetail/C455280) | `SW_SPST_TS-1088-xR020` | top | [C] | yes |
| C4, C18, C19 | 3 | 1 µF 0402 | [C52923](https://jlcpcb.com/partdetail/C52923) | `C_0402_1005Metric` | top | [C] |  |
| J1 | 1 | HRO TYPE-C-31-M-12, USB-C 16P | [C165948](https://jlcpcb.com/partdetail/C165948) | `USB_C_Receptacle_HRO_TYPE-C-31-M-12` | top | **[G3]** | yes |
| R1, R2 | 2 | 5.1 kΩ 0402 | [C25905](https://jlcpcb.com/partdetail/C25905) | `R_0402_1005Metric` | top | [C] |  |
| R3, R4 | 2 | 27 Ω 0402 | [C2909343](https://jlcpcb.com/partdetail/C2909343) | `R_0402_1005Metric` | top | [C] |  |
| U4, U5 | 2 | USBLC6-2SC6 ESD array (USB, TRRS) | [C7519](https://jlcpcb.com/partdetail/C7519) | `SOT-23-6` | top | [J] | yes |
| D1 | 1 | B5819W, 1 A Schottky | [C8598](https://jlcpcb.com/partdetail/C8598) | `D_SOD-123` | top | **[G3]** |  |
| C1–C3 | 3 | 10 µF 0402 | [C15525](https://jlcpcb.com/partdetail/C15525) | `C_0402_1005Metric` | top | [C] |  |
| U3 | 1 | AP2112K-3.3TRG1, 600 mA LDO | [C51118](https://jlcpcb.com/partdetail/C51118) | `SOT-23-5` | top | **[G3]** |  |
| F1 | 1 | nSMD025-24V PTC, 250 mA hold, 24 V | [C70069](https://jlcpcb.com/partdetail/C70069) | `Fuse_1206_3216Metric` | top | **[G3]** | yes |
| J2 | 1 | PJ-320D-4A TRRS jack, SMD | [C95562](https://jlcpcb.com/partdetail/C95562) | `Jack_3.5mm_PJ320D_Horizontal` | top | [J], G2 | yes |
| SK101–SK137 | 37 | Kailh MX hot-swap socket CPG151101S11 | [C2803348](https://jlcpcb.com/partdetail/C2803348) | `SW_MX_Hotswap_Kailh` | **bottom** | **[G3]** | yes |
| D101–D137 | 37 | 1N4148W switching diode | [C81598](https://jlcpcb.com/partdetail/C81598) | `D_SOD-123` | **bottom** | **[G3]** |  |

21 BOM lines, 118 parts per half, 74 of them on the bottom side.
<!-- END GENERATED: bom_assembled -->

> [!WARNING]
> **Stock.** On 2026-11-02 the hot-swap socket C2803348 was discontinued, and JLC had only 163 of
> C113767 (W25Q128JVSIQ) and 34 of C91749 (crystal); see [verification.md](verification.md#g3-parts-stock-and-track-width)
> for the replacements. Check every line on the day you order (`tests/integration/stock.py`); pick a
> same-footprint replacement if one is out (gate G3).

F1 is WS2's choice for the spec's "PTC 1206, 250 mA hold" (deviation WS2a-4). JLCPCB's preview
shows no 3D body for J1, J2 or the hot-swap sockets, because KiCad's library has no model for them
(deviation WS2c-2). The CPL carries rotation corrections for the RP2040 (QFN-56, +270°), the flash
(SOIC-8, +270°), the SOT-23-5/6 parts U3–U5 (−90°) and the USB-C J1 (+180°) from a public KiCad→JLC
table (deviation REVIEW-FIX-5); the community tables have changed over the years, so check every
IC, diode and connector in JLC's placement preview before you confirm the order
([ordering-jlcpcb.md](ordering-jlcpcb.md#placement-preview)).

## Not in the JLC BOM or placement file

The footprints below are marked "exclude from BOM / position files" (J3 also DNP) on the boards,
and the pipeline fails if any of them reaches `bom.csv` or `pos.csv` (deviation WS2c-1).

<!-- BEGIN GENERATED: bom_excluded (site/gen_docs.py from the committed boards; run `just docs-gen`) -->
| Designators | Qty | What | Why |
|---|---|---|---|
| J3 | 1 | 1×5 2.54 mm female socket for the display | hand-soldered by the builder (DNP); gate G1 |
| JP1 | 1 | solder jumper VSYS → F1 → VLINK, bridged | copper only; cut it for split-powered mode |
| TP1–TP11 | 11 | Ø1.0 mm test pads: TP1 `DISP_DC`, TP2 `DISP_RST`, TP3 `DISP_BL`, TP4 GP22, TP5 GP23, TP6 GP24, TP7 GP25, TP8 `SWCLK`, TP9 `SWDIO`, TP10 `GND`, TP11 `TRRS_DET` | copper only |
| H1–H8 | 8 | M2.5 mounting holes, NPTH Ø2.7 | drilled |
| STAB_T4, STAB_T5 | 2 | 2u stabiliser holes (board-only footprint, no symbol) | drilled |
<!-- END GENERATED: bom_excluded -->

## Builder parts

| Qty (pair) | Part | Notes |
|---|---|---|
| 2 | nice!view display, or an LS011B7DH03 breakout with the same pinout | G1: 36 × 14 × 2.9 mm assumed, pin order MOSI, SCK, VCC, GND, CS |
| 2 | 1×5 2.54 mm female socket and a 1×5 male header spacer | J3; the stack must lift the module 6.0–6.3 mm above the PCB (for example a 3.5 mm low-profile socket on a 2.5 mm spacer), so its underside clears the plate and the glass stays ≤ 8.2 mm (G1, [buildguide](buildguide_en.md#4-fit-the-display-socket)) |
| 74 | MX-compatible switches, 3- or 5-pin | 37 per half |
| 4 | 2u plate-mount stabilisers | T4 and T5 on each half |
| 74 | Keycaps | 8 × 1.5u (outer column), 4 × vertical 1.5u (inner column), 4 × 2u (T4, T5), 58 × 1u |
| 1 | TRRS cable, 3.5 mm, 4-pole, **straight** | plug head ≤ Ø6.3 mm for its first 3.7 mm, to pass the case hole and seat fully ([case.md](case.md#trrs-cable)) |
| 1–2 | USB-C cable | the second only for split-powered mode or flashing the right half |
| 12 | M2.5 × 14 countersunk screws, ISO 10642 | 6 per half, bezel and edge bosses ([case.md](case.md#fasteners)) |
| 4 | M2.5 × 12 countersunk screws, ISO 10642 | 2 per half, the bosses under the key well |
| 8 | Rubber feet, Ø10 mm | 4 per half |
| 6 | Tent legs and foot caps | `worxboard_leg` (CNC) and `worxboard_leg_cap` (TPU), [legs.md](legs.md) |
| 6 | Stock ErgoDox EZ M3 spring thumbscrews | one per leg |
| 1 set | Case: top shell, bottom tray and plate spacer per half | [case.md](case.md) |

## Extended-part fees

JLCPCB charges a one-off loading fee for each **extended** part per order (the "Extended" column):
C2040, C113767, C91749, C7519, C95562, C165948, C2803348, C455280 and the PTC C70069. The left and
right boards are two separate designs, so each one pays the fees once. See
[ordering-jlcpcb.md](ordering-jlcpcb.md#costs).

## Gates

These gates block **ordering**, not the repository. WS5 recorded the results in
[verification.md](verification.md); the table below is their summary.

| Gate | What is checked | Result |
|---|---|---|
| **G1** | nice!view dimensions (36 × 14 × 2.9 mm), pin order, which end pin 1 is, the viewing area under the window, and the socket stack ≤ 8.2 mm | **FAIL**: size, pin order and window PASS; J3 pin 1 is at the wrong end on both boards (the display cannot work as routed), and the module runs 0.7 mm past the case pocket unless the socket stack lifts it above the plate |
| **G2** | PJ-320D height (≤ 5.5 mm), the footprint pad map against the datasheet, and the body length | **FAIL**: height 5.0 mm and pad map PASS; the body is 14.1 mm long, 2.1 mm longer than the case relief |
| **G3** | Every **[G3]** LCSC number above and its stock, the PTC choice, and the JLC 2-layer minimum track (0.127 mm) | **FAIL**: the hot-swap socket C2803348 is discontinued (replacement candidates in verification.md); track width PASS |

The fixes and their owners are listed under
[open items](verification.md#open-items-that-block-ordering). `tests/integration/test_gates.py`
checks G1 and G2 against the drawings, and `tests/integration/stock.py` re-checks G3 stock on the
day of ordering.
