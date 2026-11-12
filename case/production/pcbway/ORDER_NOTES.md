# PCBWay CNC order: the machined case parts

PCBWay machines the same five parts from the same files as JLCCNC. Nothing is generated into this
folder: upload the STEP and PDF files of [`../jlccnc/`](../jlccnc/ORDER_NOTES.md) (case revision
**A5**) and use that page's remarks and prepared answers. This page lists only what differs.
Order from one shop, not both: the parts must fit each other and share one anodizing batch.

Not checked for this revision: PCBWay's current design rules, form options and prices. The limits
below are the ones the model is built to; ask PCBWay's engineer to confirm them in the quote.

## Files

| Upload | Files (in `../jlccnc/`) | Qty |
|---|---|---|
| Part 1 | `worxboard_right_top.step` + `.pdf` (2 sheets) | 1 |
| Part 2 | `worxboard_left_top.step` + `.pdf` (2 sheets) | 1 |
| Part 3 | `worxboard_right_bottom.step` + `.pdf` | 1 |
| Part 4 | `worxboard_left_bottom.step` + `.pdf` | 1 |
| Part 5 | `worxboard_leg.step` + `.pdf` | **6** |

Attach the PDF as the technical drawing of each part. The STEP governs the geometry, the PDF the
threads, tolerances and finish. `hole_table.csv` answers questions about hole positions.

## Form settings

| Option | Value |
|---|---|
| Service | CNC machining (3-axis milling; the three leg bosses of each top need a side setup each) |
| Material | Aluminium 6061-T6 |
| Surface finish | Bead blast, then anodize Type II, one colour for all 10 pieces |
| Threads and tapped holes | Tops: 11 each (8 × M2.5 + 3 × M3, right-hand; T1 and T5 through, the rest blind). Bottoms and legs: none |
| Tolerance | ISO 2768-m; tighter where the drawing's general notes say "FIT-CRITICAL" |
| Tightest tolerance | ±0.05 (plate thickness, leg boss height); switch cutouts 14.00 +0.05/0 |
| Roughness | as machined; Ra 1.6 on the bearing faces of the leg bosses and leg hubs (drawings) |
| Technical drawing | Yes, the PDF of each part |
| Quantity | 1 of each case part, 6 legs |

## What the model assumes about the shop

The model follows JLCCNC's published design guideline. PCBWay must be able to do the same; put
these in the remarks and wait for the engineer's answer before paying:

```
Please confirm before production:
1. Internal corners are modelled at R = depth/10 + 0.5 (R1.0 at 4 mm, R1.5 to 8.2 mm, R2 at 11.6 mm) and
   must be machined as modelled, not enlarged. Switch cutouts are R0.5 through a 1.5 mm plate (1 mm end mill).
2. Blind M2.5 threads: drill 6.0, full thread 4.5 min. Blind M3: drill 5.5 / thread 4.0 and drill 7.5 / thread 6.0.
   T1 and T5 are M2.5 through holes that exit in a cosmetic face: chamfer dia. 2.9 x 90 deg, no burr.
3. Thinnest walls: 0.84 mm (display bezel, 1 mm tall), 1.0 mm skin over the display pocket,
   1.5 mm plate over about 130 x 100 mm (flatness 0.2 in the restrained state; low blasting pressure there).
4. All threads right-hand on both the right and the left (mirrored) parts.
5. The four case parts and six legs must fit together and be anodized in one batch, one colour.
   Dimensions apply after finishing. Rack marks on inside faces only. Mask or re-tap the threads.
```

Then paste the TOP, BOTTOM and LEG remarks from [`../jlccnc/ORDER_NOTES.md`](../jlccnc/ORDER_NOTES.md).
Where those say "your guideline", they mean JLCCNC's rules quoted above.

## Printed parts and hardware

PCBWay also prints 3D parts, but the foot-cap tree is sized to JLC3DP's minimum TPU part
(30 × 30 × 15 mm). Order it as in [`../jlc3dp/`](../jlc3dp/ORDER_NOTES.md), or print the single cap
yourself. Screws, feet and leg hardware: [`../hardware.csv`](../hardware.csv).
