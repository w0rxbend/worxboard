# Tent / tilt legs

worxboard keeps the leg design of the reference [ErgoDox CNC case](https://github.com/w0rxbend/ergodox)
unchanged (see its [legs.md](https://github.com/w0rxbend/ergodox/blob/main/docs/legs.md) for the
measurements behind it). Each half has **three** mounts at the stock ErgoDox EZ positions, and every
mount takes the same custom leg, clamped by an M3 thumbscrew: an M3 × 12 knurled thumbscrew without a
collar (DIN 653) with a friction washer, or the stock EZ spring thumbscrew once it is measured.

> [!NOTE]
> The values below are the as-built model (`case/worxboard_case.py`); `just model` prints them in
> its build report and fails if a leg check does not hold. The legs are ordered from JLCCNC with the
> case ([`case/production/jlccnc/`](../case/production/jlccnc/ORDER_NOTES.md)). No leg has been made yet.

## The mount

Each mount is an M3 tapped hole with a **flat Ø10 boss** on the outside of the top shell's wall. The
spring thumbscrew presses the leg's flat hub onto the boss, so the leg holds any angle by friction.

| Feature | Value | Parameter |
|---|---|---|
| Thread | M3, tap drill Ø2.5, blind: drill 5.5 mm (outer, thumb) or 7.5 mm (inner) from the boss face, with 4.0 / 6.0 mm of full thread (at least D/2 unthreaded at the bottom, JLCCNC's guideline; CASE-3) | `LEG_TAP_D`, `LEG_DEPTH`, `LEG_MIN_DRILL` |
| Thread axis height | Z 12.0 | `LEG_Z` |
| Boss | Ø10, 2.7 mm proud of the wall, flat face; spans Z 7.0–17.0 on the top part | `LEG_BOSS_D`, `LEG_BOSS_H` |
| Pad behind the wall | 10 mm along the wall, up to 6 mm deep, clear of the switch housings and the key well | `LEG_PAD` |
| Detent teeth | off (`DETENT_TEETH = False`): flat faces are easier to mill | `DETENT_TEETH` |

## Positions

In the right-half frame (the left half is the mirror image). The positions are the stock EZ ones,
measured along the walls of the derived outline (deviation WS3-3):

| Mount | On the wall at | Bearing face (boss top, 2.7 mm out) | Pad depth | M3 drill / full thread | Max screw reach past the boss face | Note |
|---|---|---|---|---|---|---|
| Outer | (209.4, 64.0), outer wall | (212.1, 64.0) | 6.00 | 5.5 / 4.0 | 3.7 | the drill stops short of the key well floor; the wall is 3.1 mm from the well |
| Inner | (55.6, 64.0), inner wall | (52.9, 64.0) | 5.00 | 7.5 / 6.0 | 5.7 | pad **clamped to 5.0 mm** (x ≤ 63.6), 1.29 mm clear of the display pocket |
| Thumb | (27.2, 158.5), thumb-cluster end wall, v = 0.56 u | (24.8, 159.7) | 1.75 | 5.5 / 4.0 | 3.7 | the pad is limited by the T0 switch housing |

The first column is the boss centre on the outer face of the wall; the flat bearing face the leg's
hub sits on is `LEG_BOSS_H` = 2.7 mm further out along the wall normal. The hub then reaches another
8.0 mm out (`LEG_HUB_L`), so the inner leg's arm swings in the plane x 44.9–50.9.

The inner leg sits right beside the display. Its position is unchanged from the EZ (the spec rejected
moving it); only the pad behind the wall is shallower. The outer and thumb threads are shorter than
the reference's 7.5 mm, because the derived walls sit closer to the key well.

**The thumbscrew.** An M3 × 12 knurled thumbscrew **without a collar** (DIN 653, the low type: its
flat Ø12 head bears on the leg's back face) reaches 4.0 mm past the boss face through the 8.0 mm hub,
0.3 mm more than the outer and thumb threads allow. **Do not use DIN 464** or any other shouldered
thumbscrew: the length of a DIN 464 M3 is measured under its Ø6 × 5 mm collar, which drops into the
leg's Ø6.5 × 4.0 counterbore and bears on its floor, so an M3 × 12 reaches 8.0 mm past the boss face
and bottoms in the blind thread before it clamps the leg (deviation ORDER-5). A 0.5–1.0 mm friction washer between the hub and the boss brings it to
3.0–3.5 mm, so the washer is **required** with that screw. The stock ErgoDox EZ spring thumbscrew's
length is not known: measure it before using it (`case/production/hardware.csv`).

## The leg

| Feature | Value | Parameter |
|---|---|---|
| Hub | Ø10.4 × 8.0, flat bearing face towards the case | `LEG_HUB_D`, `LEG_HUB_L` |
| Bore | Ø3.4 through (M3 clearance) | `LEG_HOLE_D` |
| Spring counterbore | Ø6.5 × 4.0 in the outer face, for the thumbscrew spring | `LEG_CBORE` |
| Arm | 7.5 wide at the hub, 6.0 thick | `LEG_ARM_W`, `LEG_ARM_T` |
| Foot | Ø4.5 × 5 spigot for a TPU cap, Ø9 with a domed end | `LEG_SPIGOT`, `LEG_FOOT_D` |
| Length | 47 mm from the pivot to the foot tip | `LEG_LEN` |

- **One part for all six positions.** The leg is symmetric. Order 6 per keyboard.
- **Foot cap.** TPU 95A. JLC3DP prints TPU only above 30 × 30 × 15 mm, so the caps are ordered as
  one tree of 8 (`worxboard_leg_cap_tree.stl`, CASE-4). Snip them off at the base. The single cap
  `worxboard_leg_cap.stl` is there to print yourself, and the stock EZ rubber caps may also fit.
- **Holding the angle.** Tighten the thumbscrew to lock the leg. The friction washer (rubber, cork
  or fibre, Ø10 × Ø3.2, 0.5–1.0 mm) between the hub and the boss holds the angle and keeps an
  M3 × 12 within its thread.

## Known limitations

- The legs hold by friction only; there are no click stops.
- The inner leg cannot fold flat forwards. Its arm swings at x 44.9–50.9, across the outer face of
  the TRRS bump (x 45.5, from y ≈ 80), so it hits the bump at about 75° forward, and a plugged TRRS
  cable (y 103) even earlier. Fold it backwards, or keep it below that angle.
- The leg and thumbscrew dimensions come from caliper photos of a stock EZ (about ±0.3 mm). A printed
  leg on a printed top confirms the fit.
