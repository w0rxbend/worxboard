# SPDX-License-Identifier: GPL-3.0-or-later
"""Cross-sections through the right half (top + bottom + spacer): the middle-finger column,
the display column, the back-edge screws / USB-C, and the TRRS jack row.

Usage: section.py <exports_dir> <out.png>
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
d = E.DISPLAY("right")
cuts = [  # (origin, normal, horizontal axis, title)
    ((E.P(129.54, 0)[0], 0, 0), (1, 0, 0), 1, "X = middle-finger column (Y horizontal)"),
    ((E.P(d["window_centre"][0], 0)[0], 0, 0), (1, 0, 0), 1, "X = display column: pocket, window, J3 end"),
    ((0, E.P(0, E.SCREWS("right")[5][1])[1], 0), (0, 1, 0), 0, "Y = back-edge screws (X horizontal)"),
    ((0, E.P(0, E.usb_notch("right")["y"] + E.WALL / 2)[1], 0), (0, 1, 0), 0, "Y = back wall: USB-C notch"),
    ((0, E.P(0, E.trrs_notch("right")["y"])[1], 0), (0, 1, 0), 0, "Y = TRRS jack row: notch in the inner bump"),
]
fig, axs = plt.subplots(len(cuts), 1, figsize=(16, 3.0 * len(cuts)), dpi=90)
for ax, (origin, normal, axis, title) in zip(axs, cuts):
    for name, col in (("right_top", "#7a8aa0"), ("right_bottom", "#b0b8c4"), ("right_spacer", "#d8b060")):
        m = trimesh.load(os.path.join(O, f"worxboard_{name}.stl"))
        sec = m.section(plane_origin=origin, plane_normal=normal)
        if sec is None:
            continue
        for ent in sec.discrete:
            ax.fill(ent[:, axis], ent[:, 2], color=col, alpha=0.9, lw=0.3, ec="k")
    for z, lab in ((E.Z_SPLIT, "PCB bottom"), (E.Z_PCB_TOP, "PCB top"), (E.Z_PLATE_TOP, "plate top"),
                   (E.Z_DISPLAY_TOP, "display pocket")):
        ax.axhline(z, color="r", lw=0.5, ls="--")
        ax.text(0.005, z + 0.2, lab, color="r", fontsize=7, transform=ax.get_yaxis_transform())
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=9)
    ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(sys.argv[2])
