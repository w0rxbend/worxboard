# Bill of materials

Rev A, from spec §7. JLCPCB assembles every part marked **JLC**; the builder supplies the rest.
The generated JLC files (`bom.csv`, `pos.csv`) come from KiKit and are the authority for an order:
see [ordering-jlcpcb.md](ordering-jlcpcb.md).

**Status key**

| Flag | Meaning |
|---|---|
| **[C]** | Verified from the Corne v4.1 JLC BOM ([foostan/crkbd](https://github.com/foostan/crkbd)) |
| **[J]** | Verified on the JLCPCB part page |
| **[G3]** | **Must be verified before ordering**: LCSC number, stock and footprint (gate G3) |
| G1 | Depends on the display gate G1 (nice!view size, pin order, stack height) |

## Per half, assembled by JLCPCB

Both halves have the same parts list. The only difference between the two PCBs is the TRRS
TX/RX crossover in the netlist.

| Ref | Qty | Part | LCSC | Footprint | Status | Side | Extended |
|---|---|---|---|---|---|---|---|
| U1 | 1 | RP2040 | [C2040](https://jlcpcb.com/partdetail/C2040) | QFN-56 7×7 P0.4 | [C] | top | yes |
| U2 | 1 | W25Q128JVSIQ, 16 MB QSPI flash | [C113767](https://jlcpcb.com/partdetail/C113767) | SOIC-8 5.3×5.3 | [C] | top | yes |
| Y1 | 1 | 12 MHz crystal, 18 pF, 3225 | [C91749](https://jlcpcb.com/partdetail/C91749) | 3225-4Pin | [C] | top | yes |
| U3 | 1 | AP2112K-3.3TRG1, 600 mA LDO | [C51118](https://jlcpcb.com/partdetail/C51118) | SOT-23-5 | **[G3]** | top | |
| U4, U5 | 2 | USBLC6-2SC6, ESD (USB and TRRS) | [C7519](https://jlcpcb.com/partdetail/C7519) | SOT-23-6 | [J] | top | yes |
| D1 | 1 | B5819W, 1 A Schottky | [C8598](https://jlcpcb.com/partdetail/C8598) | SOD-123 | **[G3]** | top | |
| F1 | 1 | PTC 1206, 250 mA hold, ≥ 6 V | chosen by WS2, recorded in `bom.csv` | 1206 | **[G3]** | top | yes |
| J1 | 1 | HRO TYPE-C-31-M-12, USB-C 16P | [C165948](https://jlcpcb.com/partdetail/C165948) | HRO TYPE-C-31-M-12 | **[G3]** | top | yes |
| J2 | 1 | PJ-320D-4A, TRRS jack, SMD | [C95562](https://jlcpcb.com/partdetail/C95562) | PJ320D horizontal | [J], G2 | top | yes |
| SW_BOOT, SW_RST | 2 | TS-1088R-02026 tact switch | [C455280](https://jlcpcb.com/partdetail/C455280) | SW_SPST_TS-1088 | [C] | top | yes |
| R | 2 | 5.1 kΩ 0402 (USB CC1/CC2) | [C25905](https://jlcpcb.com/partdetail/C25905) | 0402 | [C] | top | |
| R | 2 | 27 Ω 0402 (USB D+/D−) | [C2909343](https://jlcpcb.com/partdetail/C2909343) | 0402 | [C] | top | |
| R | 4 | 1 kΩ 0402 (XOUT, BOOT, UART × 2) | [C11702](https://jlcpcb.com/partdetail/C11702) | 0402 | [C] | top | |
| R | 5 | 10 kΩ 0402 (QSPI_SS, RUN, RX pull-up, VBUS divider × 2) | [C25744](https://jlcpcb.com/partdetail/C25744) | 0402 | [C] | top | |
| C | 11 | 100 nF 0402 (decoupling) | [C1525](https://jlcpcb.com/partdetail/C1525) | 0402 | [C] | top | |
| C | 3 | 1 µF 0402 | [C52923](https://jlcpcb.com/partdetail/C52923) | 0402 | [C] | top | |
| C | 3 | 10 µF 0402 | [C15525](https://jlcpcb.com/partdetail/C15525) | 0402 | [C] | top | |
| C | 2 | 27 pF 0402 (crystal load) | [C1557](https://jlcpcb.com/partdetail/C1557) | 0402 | [C] | top | |
| D_xx | 37 | 1N4148W switching diode | [C81598](https://jlcpcb.com/partdetail/C81598) | SOD-123 | **[G3]** | **bottom** | |
| SK_xx | 37 | Kailh MX hot-swap socket CPG151101S11 | [C2803348](https://jlcpcb.com/partdetail/C2803348) | `worxboard:SW_MX_Hotswap_Kailh` | **[G3]** | **bottom** | yes |

**Not in the JLC BOM or placement file** (KiKit `--ignore`):

| Ref | Qty | Part | Notes |
|---|---|---|---|
| J3 | 1 | 1×5 2.54 mm female socket, low profile | hand-soldered by the builder (DNP), G1 |
| JP1 | 1 | solder jumper, bridged | copper only; cut it for split-powered mode |
| TP1–TP7, SWD × 3 | 10 | Ø1.0 mm test pads | copper only |
| H1–H8 | 8 | M2.5 NPTH Ø2.7 | drilled holes |

## Builder parts

| Qty (pair) | Part | Notes |
|---|---|---|
| 2 | nice!view display, or an LS011B7DH03 breakout with the same pinout | G1: 36 × 14 × 2.9 mm, pin order MOSI, SCK, VCC, GND, CS |
| 2 | 1×5 2.54 mm female socket, low profile | J3; socket + module + glass ≤ 8.2 mm above the PCB |
| 74 | MX-compatible switches, 3- or 5-pin | 37 per half |
| 4 | 2u plate-mount stabilisers | T4 and T5 on each half |
| 74 | Keycaps | 8 × 1.5u, 4 × vertical 1.5u, 4 × 2u, 58 × 1u |
| 1 | TRRS cable, 3.5 mm, 4-pole, straight | |
| 1–2 | USB-C cable | |
| 16 | M2.5 countersunk screws, ISO 10642 | per the case; see [case.md](case.md#fasteners) |
| 8 | Rubber feet, Ø10 mm | |
| 6 | Tent legs, foot caps and stock ErgoDox EZ M3 spring thumbscrews | [legs.md](legs.md) |
| 1 set | Case: top shell, bottom tray and plate spacer per half | [case.md](case.md) |

## Extended-part fees

JLCPCB charges a one-off loading fee for each **extended** part per order (the "Extended" column
above): C2040, C113767, C91749, C7519, C95562, C165948, C2803348, C455280 and the PTC. The left and
right boards are two separate designs, so each one pays the fees once. See
[ordering-jlcpcb.md](ordering-jlcpcb.md#costs).

## Gates

These gates block **ordering**, not the repository. WS5 records the results in
`docs/verification.md` (in progress).

| Gate | What must be checked |
|---|---|
| **G1** | nice!view dimensions (36 × 14 × 2.9 mm assumed), header pin order, display active-area position under the window, and the socket stack ≤ 8.2 mm |
| **G2** | PJ-320D height (≤ 5.5 mm) and the footprint pad map against the datasheet |
| **G3** | Every **[G3]** LCSC number above, and its stock; the PTC choice; the JLC 2-layer minimum track (0.127 mm) |
