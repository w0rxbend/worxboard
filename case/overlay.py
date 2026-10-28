# SPDX-License-Identifier: GPL-3.0-or-later
"""Top-view overlay of the case model on the PCB layout of one half: PCB outline and component
zones (from `layout`), case outline, inner wall, key well, switch cutouts, display pocket and
window, USB-C / TRRS notches, screws, tent legs and pin-holes. Replaces the reference overlay on a
photo of the EZ: worxboard has no photo to calibrate against, the layout is the reference.

Usage: overlay.py <out.png> [side]
"""
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import worxboard_case as E  # noqa: E402
import layout as L  # noqa: E402
from shapely.geometry import box  # noqa: E402

out = sys.argv[1]
side = sys.argv[2] if len(sys.argv) > 2 else "right"


def wire_xy(face, n=24):
    """KiCad-frame points along a CAD face's outer wire."""
    pts = []
    for e in face.outer_wire().edges():
        k = 2 if "LINE" in str(e.geom_type) else n
        pts += [E.K(p.X, p.Y) for p in (e.position_at(i / (k - 1)) for i in range(k))]
    return zip(*pts)


def poly_xy(poly):
    for g in getattr(poly, "geoms", [poly]):
        yield g.exterior.xy


fig, ax = plt.subplots(figsize=(12, 10.5), dpi=90)
for g in poly_xy(E.zones_poly(side)):
    ax.fill(*g, color="#ffe08a", alpha=0.7, lw=0, label="component zones")
for g in poly_xy(E.relief_poly(side)):
    ax.plot(*g, color="#c89000", lw=0.6, ls=":")
ax.plot(*L.outline(side).exterior.xy, color="#2a8a2a", lw=1.2, label="PCB")
ax.plot(*wire_xy(E.outline_face(side)), color="#c00000", lw=1.4, label="case outline")
ax.plot(*wire_xy(E.inner_face(side)), color="#c00000", lw=0.6, ls="--", label="inner wall")
for wf in E.well_face(side):
    ax.plot(*wire_xy(wf), color="#0070d0", lw=0.9, label="key well")
for kx, ky, w, h, rot in E.KEYS(side):
    ax.plot(*wire_xy(E.switch_cut(kx, ky, rot).faces()[0]), color="#404040", lw=0.6)
for kx, ky, w, h, rot in E.stab_keys(side):
    for f in E.stab_cuts(kx, ky, rot).faces():
        ax.plot(*wire_xy(f), color="#404040", lw=0.5)
d = E.DISPLAY(side)
for r, col, lab in ((d["pocket"], "#8000c0", "display pocket"), (d["window"], "#d000d0", "window"),
                    (d["module"], "#8000c0", None)):
    ax.plot(*box(*r).exterior.xy, color=col, lw=1.0 if lab else 0.5, ls="-" if lab else ":", label=lab)
for ref in ("J1", "J2"):
    ax.plot(*box(*E.JACK(side, ref).body).exterior.xy, color="#e06000", lw=1.0)
for n in (E.usb_notch(side), E.trrs_notch(side)):
    ax.plot(n["x"], n["y"], "o", color="#e06000", ms=6, label=None)
for sx, sy in E.SCREWS(side):
    ax.add_patch(plt.Circle((sx, sy), E.boss_radius(side, sx, sy), fill=False, color="#a00060", lw=0.8))
for x, y in E.pin_holes(side):
    ax.add_patch(plt.Circle((x, y), E.PIN_HOLE_D / 2, fill=False, color="#000000", lw=0.8))
for name, (x, y), (nx, ny) in E._leg_wall_points(side):
    ax.annotate(f"leg {name}", (x, y), (x + 9 * nx, y + 9 * ny), fontsize=7, ha="center",
                arrowprops=dict(arrowstyle="-", lw=0.5))
handles, labels = ax.get_legend_handles_labels()
uniq = dict(zip(labels, handles))
ax.legend(uniq.values(), uniq.keys(), fontsize=7, loc="lower right")
ax.set_aspect("equal")
ax.invert_yaxis()
ax.grid(alpha=0.25)
ax.set_title(f"worxboard {side} half: case over the PCB layout (KiCad frame, mm)", fontsize=10)
plt.tight_layout()
plt.savefig(out)
