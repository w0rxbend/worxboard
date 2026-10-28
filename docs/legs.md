# Tent / tilt legs

worxboard keeps the leg design of the reference [ErgoDox CNC case](https://github.com/w0rxbend/ergodox)
unchanged (see its [legs.md](https://github.com/w0rxbend/ergodox/blob/main/docs/legs.md) for the
measurements behind it). Each half has **three** mounts at the stock ErgoDox EZ positions, and every
mount takes the same custom leg, clamped by the stock EZ M3 spring thumbscrew.

> [!NOTE]
> **In progress (WS3).** The values below are the reference design that `case/worxboard_case.py`
> keeps. The build report of `just model` prints the as-built thread depths.

## The mount

Each mount is an M3 tapped hole with a **flat Ø10 boss** on the outside of the top shell's wall. The
spring thumbscrew presses the leg's flat hub onto the boss, so the leg holds any angle by friction.

| Feature | Value | Parameter |
|---|---|---|
| Thread | M3, tap drill Ø2.5, up to 7.5 mm deep from the boss face | `LEG_TAP_D`, `LEG_DEPTH` |
| Thread axis height | Z 12.0 | `LEG_Z` |
| Boss | Ø10, 2.7 mm proud of the wall, flat face; spans Z 7.0–17.0 on the top part | `LEG_BOSS_D`, `LEG_BOSS_H` |
| Pad behind the wall | 10 mm along the wall, up to 6 mm deep, clear of the switch housings and the key well | `LEG_PAD` |
| Detent teeth | off (`DETENT_TEETH = False`): flat faces are easier to mill | `DETENT_TEETH` |

## Positions

In the right-half frame (the left half is the mirror image):

| Mount | Position | Note |
|---|---|---|
| Outer | outer wall, y = 64 | stock EZ position |
| Inner | inner wall, y = 64 | stock EZ position; its pad is **clamped to 5.0 mm** deep (x ≤ 63.6) so it stays at least 1.2 mm clear of the display pocket |
| Thumb | thumb-cluster end wall, v = 0.56 u | stock EZ position |

The inner leg sits right beside the display. Its position is unchanged from the EZ (the spec rejected
moving it); only the pad behind the wall is shallower.

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
- The inner leg cannot fold flat forwards, because its foot meets the thumb cluster. The stock EZ has
  the same limitation.
- The leg and thumbscrew dimensions come from caliper photos of a stock EZ (about ±0.3 mm). A printed
  leg on a printed top confirms the fit.
