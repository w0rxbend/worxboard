# SPDX-License-Identifier: GPL-3.0-or-later
"""Section across the outer wall through the tent-leg pivot: tapped M3 hole in the pad,
the Ø10 leg boss, and the custom leg from the assembly preview.

Usage: leg_section.py <exports_dir> <out.png>
"""
import os
import sys

import matplotlib
import trimesh

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import worxboard_case as E  # noqa: E402

O = sys.argv[1]
(px, py), _ = E.leg_mounts("right")[0]          # outer leg
fig, ax = plt.subplots(figsize=(6, 9), dpi=100)
for name, col, fill in (("right_assembly_with_legs", "#d08040", False),
                        ("right_top", "#7a8aa0", True), ("right_bottom", "#b0b8c4", True)):
    m = trimesh.load(os.path.join(O, f"worxboard_{name}.stl"))
    sec = m.section(plane_origin=(0, py, 0), plane_normal=(0, 1, 0))
    for ent in sec.discrete:
        if fill:
            ax.fill(ent[:, 0], ent[:, 2], color=col, alpha=0.9, lw=0.3, ec="k")
        else:
            ax.plot(ent[:, 0], ent[:, 2], color=col, lw=1.2)
for z, lab in ((E.Z_SPLIT, "parting plane"), (E.Z_PCB_TOP, "PCB top"), (E.LEG_Z, "M3 / pivot axis"),
               (E.Z_PLATE_TOP, "plate top")):
    ax.axhline(z, color="r", lw=0.5, ls="--")
    ax.text(0.01, z + 0.2, lab, color="r", fontsize=7, transform=ax.get_yaxis_transform())
ax.set_xlim(px - 14, px + 16)
ax.set_ylim(-42, 19)
ax.set_aspect("equal")
ax.grid(alpha=0.3)
ax.set_title("Outer tent leg: M3 tapped pad + Ø10 boss (orange = leg)", fontsize=8)
plt.tight_layout()
plt.savefig(sys.argv[2])
