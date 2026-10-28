# Ordering the worxboard case from a CNC service

This page explains how to order one keyboard (4 case parts + 6 legs) from JLCCNC or any other CNC
service. It is copied into the order package as `ORDER_NOTES.md` by `just order`.

## The order package

Build it with `just model && just order` (output: `case/exports/order/`). It contains:

| File | Upload as | Purpose |
|---|---|---|
| `worxboard_right_top.step` / `.pdf` | 3D model + 2D drawing (part 1) | Sheet 1: threads T1–T8, L1–L3 and the features W1, D1, U1, J1, P1–P2. Sheet 2: leg bosses |
| `worxboard_right_bottom.step` / `.pdf` | part 2 | Countersunk holes, foot recesses, side mark (no threads) |
| `worxboard_left_top.step` / `.pdf` | part 3 | Mirror of part 1. The threads stay right-hand |
| `worxboard_left_bottom.step` / `.pdf` | part 4 | Mirror of part 2, with its own side mark |
| `worxboard_leg.step` / `.pdf` | part 5, **quantity 6** | Tent leg: flat hub, bore, counterbore (no threads) |
| `worxboard_leg_cap.stl` | (print yourself, TPU) | Foot cap for the leg; not for CNC |
| `worxboard_{left,right}_spacer.stl` | (print or laser-cut yourself) | 3 mm plate spacer; not for CNC |
| `worxboard-plate-{left,right}.dxf` | (optional) | Stand-alone 1.5 mm FR4 / aluminium plate outline |
| `hole_table.csv` | (keep for reference) | Every hole, thread and feature, in STEP coordinates |
| `ORDER_NOTES.md` | (this page) | Form settings, remarks text, answers |

The STEP files model every threaded hole at its **tap-drill diameter**: Ø2.05 for M2.5 and Ø2.5 for M3.
They contain no thread geometry, which is why each part needs its PDF drawing.

## Before ordering

Gates G1–G3 of the design spec must be closed (`docs/verification.md`): the display stack (G1) sets the
pocket and window, the TRRS jack height (G2) sets the bump pocket ceiling. Also run `just fitcheck`
against the WS2 PCB STEP: it must report 0 mm3 interference.

## Form settings

| Option | Top parts (right + left) | Bottom parts (right + left) | Leg |
|---|---|---|---|
| Process | CNC milling | CNC milling | CNC milling |
| Material | Aluminium 6061-T6 (7075-T6 gives a stiffer plate) | Aluminium 6061-T6 | Aluminium 6061-T6 |
| Surface finish | Bead blasting + anodizing | Same as the top | Same as the top |
| Threads | **Yes. 11 per part: 8 × M2.5 + 3 × M3, all right-hand** | **No** | **No** |
| Tolerance | Standard (ISO 2768-m); critical values on the drawing | Standard | Standard |
| Quantity | 1 each | 1 each | **6** |

## Remarks (paste for the TOP parts)

```
Threads per 2D drawing: 8x M2.5x0.45-6H (T1-T8) + 3x M3x0.5-6H (L1-L3), ALL RIGHT-HAND.
The STEP models holes at tap-drill size. Left part is a mirror image, but threads stay RIGHT-HAND.
T1 and T5 are BLIND under the key well (1.1 mm skin): do not break through.
L1-L3: plain Ø10 bosses on the outer walls, 2.7 high, FLAT face, M3 thread in each, see sheet 2.
Display window W1 through a 0.8 mm skin over pocket D1. USB-C notch U1 (back wall) and TRRS hole J1
(inner wall) are side operations. Pin-holes P1-P2 Ø3 thru.
Switch cutouts 14.00 +0.05/-0. Cosmetic: top face, key well, outer walls.
Mask threads during anodizing, or re-tap afterwards.
```

## Remarks (paste for the BOTTOM parts)

```
No threads. 8x Ø2.9 through holes with 90° countersink Ø5.2 for M2.5 countersunk screws (C1-C8),
4x Ø10.5 x 0.6 recesses for rubber feet (F1-F4), engraved side mark M1 (0.4 deep).
The USB-C plug recess continues 0.8 mm into the back wall. Left part is a mirror image.
Cosmetic: underside and outer walls.
```

## Remarks (paste for the LEG)

```
Quantity 6, identical (not left/right). No threads.
Hub face: FLAT (no teeth), flatness 0.05, see drawing detail D. It bears on the flat case boss.
Ø3.4 through bore + Ø6.5 x 4 counterbore on the back face. Spigot Ø4.5 -0.05.
Same anodize colour as the case parts.
```

## Prepared answers to engineering questions

| Likely question | Answer |
|---|---|
| Thread direction? | All right-hand, on both the right and the left parts. Mirroring applies to the geometry only. |
| Thread depth? | See the table on sheet 1. M3: drill 5.5–7.5 from the boss face (the outer and thumb legs stop short of the key well floor), at least depth − 0.5 full thread. |
| The skin over the display pocket is thin (0.8 mm). | Intended: the display glass sits right under it. Machine the pocket from the parting side and support the skin. |
| Sharp internal corners? | All pocket corners are R ≥ 1 mm (Ø2 tool), except the switch cutouts (R0.5). Fillets per R = depth/10 are modelled where pads and webs meet the walls. |
| Gaps between bosses and walls? | Every boss near a wall is joined to it by a solid web. |
| Tolerances not given? | ISO 2768-m. The STEP model is the reference geometry. |
| Text or engraving? | Only the side mark M1 on each bottom part. |
