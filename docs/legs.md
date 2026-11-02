# Tent / tilt legs

worxboard keeps the leg design of the reference [ErgoDox CNC case](https://github.com/w0rxbend/ergodox)
unchanged (see its [legs.md](https://github.com/w0rxbend/ergodox/blob/main/docs/legs.md) for the
measurements behind it). Each half has **three** mounts at the stock ErgoDox EZ positions, and every
mount takes the same custom leg, clamped by the stock EZ M3 spring thumbscrew.

> [!NOTE]
> The values below are the as-built model (`case/worxboard_case.py`); `just model` prints them in
> its build report and fails if a leg check does not hold. No leg has been made yet.

## The mount

Each mount is an M3 tapped hole with a **flat Ø10 boss** on the outside of the top shell's wall. The
spring thumbscrew presses the leg's flat hub onto the boss, so the leg holds any angle by friction.

| Feature | Value | Parameter |
|---|---|---|
| Thread | M3, tap drill Ø2.5, 5.5–7.5 mm deep from the boss face (at least 5.0 is checked) | `LEG_TAP_D`, `LEG_DEPTH`, `LEG_MIN_DRILL` |
| Thread axis height | Z 12.0 | `LEG_Z` |
| Boss | Ø10, 2.7 mm proud of the wall, flat face; spans Z 7.0–17.0 on the top part | `LEG_BOSS_D`, `LEG_BOSS_H` |
| Pad behind the wall | 10 mm along the wall, up to 6 mm deep, clear of the switch housings and the key well | `LEG_PAD` |
| Detent teeth | off (`DETENT_TEETH = False`): flat faces are easier to mill | `DETENT_TEETH` |

## Positions

In the right-half frame (the left half is the mirror image). The positions are the stock EZ ones,
measured along the walls of the derived outline (deviation WS3-3):

| Mount | On the wall at | Bearing face (boss top, 2.7 mm out) | Pad depth | M3 drill depth | Note |
|---|---|---|---|---|---|
| Outer | (209.4, 64.0), outer wall | (212.1, 64.0) | 6.00 | 5.50 | the drill stops short of the key well floor; the wall is 3.1 mm from the well |
| Inner | (55.6, 64.0), inner wall | (52.9, 64.0) | 5.00 | 7.50 | pad **clamped to 5.0 mm** (x ≤ 63.6), 1.29 mm clear of the display pocket |
| Thumb | (27.2, 158.5), thumb-cluster end wall, v = 0.56 u | (24.8, 159.7) | 1.75 | 5.50 | the pad is limited by the T0 switch housing |

The first column is the boss centre on the outer face of the wall; the flat bearing face the leg's
hub sits on is `LEG_BOSS_H` = 2.7 mm further out along the wall normal. The hub then reaches another
8.0 mm out (`LEG_HUB_L`), so the inner leg's arm swings in the plane x 44.9–50.9.

The inner leg sits right beside the display. Its position is unchanged from the EZ (the spec rejected
moving it); only the pad behind the wall is shallower. The outer and thumb threads are shorter than
the reference's 7.5 mm, because the derived walls sit closer to the key well; 5.5 mm is still more
than 1.5 × the M3 diameter of engagement.

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
- **Foot cap.** `worxboard_leg_cap.stl`, printed in TPU 95A. The stock EZ rubber caps may also fit.
- **Holding the angle.** Tighten the thumbscrew to lock the leg. If it slips, add a thin friction
  washer (rubber, cork or fibre, Ø10 × Ø3.2, up to 1 mm) between the hub and the boss.

## Known limitations

- The legs hold by friction only; there are no click stops.
- The inner leg cannot fold flat forwards. Its arm swings at x 44.9–50.9, across the outer face of
  the TRRS bump (x 45.5, from y ≈ 80), so it hits the bump at about 75° forward, and a plugged TRRS
  cable (y 103) even earlier. Fold it backwards, or keep it below that angle.
- The leg and thumbscrew dimensions come from caliper photos of a stock EZ (about ±0.3 mm). A printed
  leg on a printed top confirms the fit.
