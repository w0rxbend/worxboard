# SPDX-License-Identifier: GPL-3.0-or-later
"""
Manufacturing drawings (A3 PDF) and the CNC order package for the worxboard case
(port of the reference cad/drawings.py).

For every part it writes <part>.pdf next to <part>.step: views generated from the
STEP file, the thread / hole table, general notes and, for the top parts, the leg boss
sheet (flat face, or tooth count and profile with DETENT_TEETH, plus a section). The tent
leg gets its own sheet (hub bearing face or teeth). Also writes hole_table.csv.

Usage: drawings.py <exports_dir> <order_dir> [version]
The STEP files must already exist in <exports_dir> (run worxboard_case.py first).
"""
from __future__ import annotations

import csv
import datetime
import math
import os
import shutil
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.patches import Circle as MCircle, Polygon as MPoly, Rectangle as MRect  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import worxboard_case as E  # noqa: E402
from build123d import import_step  # noqa: E402

REPO_URL = "https://github.com/w0rxbend/worxboard"
DWG = "WXB"          # drawing number prefix
A3 = (420.0, 297.0)
LW = 0.45            # visible edge line width (pt)
FS = 6.0             # base font size (pt)

# view name -> (camera position, up vector, 3D point -> 2D viewport mapping)
VIEWS = {
    "under": ((0, 0, -500), (0, 1, 0), lambda x, y, z: (-x, y)),
    "+X": ((500, 0, 0), (0, 0, 1), lambda x, y, z: (y, z)),
    "-X": ((-500, 0, 0), (0, 0, 1), lambda x, y, z: (-y, z)),
}
LEG_QTY = 6          # 3 per half; one part fits every position

TOP_MATERIAL = "Aluminium 6061-T6 (7075-T6 acceptable)"
FINISH = "Fine bead blast + anodize Type II, colour per order"


# --------------------------------------------------------------------------
# hole / feature data (STEP coordinates, mm)
# --------------------------------------------------------------------------
def _side(right: bool) -> str:
    return "right" if right else "left"


def top_threads(right: bool) -> list[dict]:
    side = _side(right)
    rows = []
    for i, (sx, sy) in enumerate(E.SCREWS(side)):
        x, y = E.P(sx, sy)
        under = E.screw_under_plate(side, sx, sy)
        depth = E.TAP_DEPTH_PLATE if under else E.TAP_DEPTH
        rows.append(dict(
            id=f"T{i + 1}", thread="M2.5x0.45", hand="RH", cls="6H", drill=E.TAP_D, depth=depth,
            full=round(depth - 0.4, 1), x=x, y=y, z=E.Z_PCB_TOP,
            direction="+Z (from PCB face)",
            note=("BLIND under key well: 1.1 mm skin, must not break through" if under else "blind")))
    for j, ((px, py), (nx, ny)) in enumerate(E.leg_mounts(side)):
        depth = E.leg_hole_depth(side, px, py, nx, ny)
        fx, fy = px + nx * E.LEG_BOSS_H, py + ny * E.LEG_BOSS_H
        rows.append(dict(
            id=f"L{j + 1}", thread="M3x0.5", hand="RH", cls="6H", drill=E.LEG_TAP_D, depth=round(depth, 1),
            full=round(depth - 0.5, 1), x=fx, y=fy, z=E.LEG_Z,
            direction=f"normal to wall, into part ({-nx:+.3f}, {-ny:+.3f}, 0)",
            note=f"in {'toothed detent' if E.DETENT_TEETH else 'flat'} leg boss, see sheet 2"))
    return rows


def top_features(right: bool) -> list[list[str]]:
    """Non-threaded features of the top part that the shop must not miss (STEP coordinates)."""
    side = _side(right)
    d = E.DISPLAY(side)
    (wx, wy), (x0, y0, x1, y1) = d["window_centre"], d["window"]
    (px0, py0, px1, py1) = d["pocket"]
    usb, trrs = E.usb_notch(side), E.trrs_notch(side)
    rows = [
        ["W1", f"display window {x1 - x0:.0f} x {y1 - y0:.0f} R{E.LD.WINDOW_R} THRU top skin, "
               f"{E.LD.WINDOW_CHAMFER} x 45° chamfer on the top edge", *map("{:.2f}".format, E.P(wx, wy))],
        ["D1", f"display pocket {px1 - px0:.1f} x {py1 - py0:.1f}, Z {E.Z_PCB_TOP}-{E.Z_DISPLAY_TOP} "
               f"(top skin {E.Z_TOP - E.Z_DISPLAY_TOP:.1f})", *map("{:.2f}".format, E.P((px0 + px1) / 2, (py0 + py1) / 2))],
        ["U1", f"USB-C notch {E.USB_NOTCH[0]} x {E.USB_NOTCH[1]} R{E.USB_NOTCH_R} thru back wall at Z {usb['z']:.1f}; "
               f"outside recess {E.USB_RECESS[0]:.0f} x {E.USB_RECESS[1]:.0f} x {E.USB_RECESS_DEPTH} deep",
         *map("{:.2f}".format, E.P(usb["x"], usb["y"]))],
        ["J1", f"TRRS hole Ø{E.TRRS_NOTCH_D} thru inner bump wall, axis Z {trrs['z']:.1f}",
         *map("{:.2f}".format, E.P(trrs["x"], trrs["y"]))],
    ]
    for ref, (x, y) in zip(E.PIN_HOLES, E.pin_holes(side)):
        rows.append([f"P{len(rows) - 3}", f"Ø{E.PIN_HOLE_D} THRU top skin ({ref} pin-hole)",
                     *map("{:.2f}".format, E.P(x, y))])
    return rows


def bottom_holes(right: bool) -> list[dict]:
    side = _side(right)
    rows = []
    for i, (sx, sy) in enumerate(E.SCREWS(side)):
        x, y = E.P(sx, sy)
        rows.append(dict(id=f"C{i + 1}", feature=f"Ø{E.SCREW_CLEAR_D} THRU, 90° CSK Ø{E.SCREW_CSK_D}",
                         x=x, y=y, note="for M2.5 ISO 10642 countersunk screw"))
    for i, (fx, fy) in enumerate(E.feet(side)):
        x, y = E.P(fx, fy)
        rows.append(dict(id=f"F{i + 1}", feature=f"Ø{E.FOOT_D} x {E.FOOT_DEPTH} deep recess",
                         x=x, y=y, note="rubber foot"))
    x, y = E.P(E.mx(side, E.ENGRAVE_AT[0]), E.ENGRAVE_AT[1])
    rows.append(dict(id="M1", feature=f"engraved '{side[0].upper()}', {E.ENGRAVE_SIZE:.0f} high x "
                                      f"{E.ENGRAVE_DEPTH} deep", x=x, y=y, note="side mark, reads from below"))
    return rows


# --------------------------------------------------------------------------
# drawing helpers (sheet coordinates in mm, origin bottom-left)
# --------------------------------------------------------------------------
def new_sheet():
    fig = plt.figure(figsize=(A3[0] / 25.4, A3[1] / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, A3[0])
    ax.set_ylim(0, A3[1])
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(MRect((10, 10), A3[0] - 20, A3[1] - 20, fill=False, lw=1.0))
    return fig, ax


def text(ax, x, y, s, size=FS, **kw):
    ax.text(x, y, s, fontsize=size, family="DejaVu Sans", va=kw.pop("va", "top"), **kw)


def title_block(ax, part: str, dwg_no: str, sheet: str, scale: str, version: str, material: str):
    x0, y0, w, h = A3[0] - 190, 10, 180, 42
    ax.add_patch(MRect((x0, y0), w, h, fill=False, lw=0.8))
    for yy in (y0 + 14, y0 + 28):
        ax.plot([x0, x0 + w], [yy, yy], color="k", lw=0.5)
    ax.plot([x0 + 110, x0 + 110], [y0, y0 + 28], color="k", lw=0.5)
    text(ax, x0 + 2, y0 + h - 1.5, "worxboard CNC aluminium case", size=10, weight="bold")
    text(ax, x0 + 2, y0 + h - 8, f"{part}   —   {REPO_URL}", size=6.5)
    text(ax, x0 + 2, y0 + 26.5, f"Drawing no.: {dwg_no}", size=7)
    text(ax, x0 + 2, y0 + 21.5, f"Material: {material}", size=6)
    text(ax, x0 + 2, y0 + 17.5, f"Finish: {FINISH}", size=6)
    text(ax, x0 + 112, y0 + 26.5, f"Sheet {sheet}", size=7)
    text(ax, x0 + 112, y0 + 21.5, f"Scale {scale}", size=6)
    text(ax, x0 + 112, y0 + 17.5, "Units: mm", size=6)
    text(ax, x0 + 2, y0 + 12.5, f"Revision {version}   Date {datetime.date.today().isoformat()}", size=6)
    text(ax, x0 + 2, y0 + 8, "General tolerance ISO 2768-mK. Threads ISO metric, RIGHT-HAND, 6H.", size=6)
    text(ax, x0 + 2, y0 + 4, "The STEP file governs geometry; this drawing governs threads, tolerances, finish.",
         size=5.5)
    text(ax, x0 + 112, y0 + 12.5, "Do not scale drawing", size=6)


def place_view(ax, shape, view: str, cx: float, cy: float, scale: float = 1.0, hidden=False):
    """Draw a hidden-line projection centred at (cx, cy); return a 3D->sheet mapper."""
    cam, up, fn = VIEWS[view]
    vis, hid = shape.project_to_viewport(cam, up, (0, 0, 0))
    bb = shape.bounding_box()
    corners = [fn(x, y, z) for x in (bb.min.X, bb.max.X) for y in (bb.min.Y, bb.max.Y)
               for z in (bb.min.Z, bb.max.Z)]
    u0 = (min(c[0] for c in corners) + max(c[0] for c in corners)) / 2
    v0 = (min(c[1] for c in corners) + max(c[1] for c in corners)) / 2

    def to_sheet(u, v):
        return cx + (u - u0) * scale, cy + (v - v0) * scale

    for edges, style in ((vis, dict(color="k", lw=LW)),
                         (hid if hidden else [], dict(color="0.55", lw=0.25, ls=(0, (2, 1.5))))):
        for e in edges:
            n = 2 if "LINE" in str(e.geom_type) else max(8, min(80, int(e.length / 0.4)))
            pts = [e.position_at(i / (n - 1)) for i in range(n)]
            xs, ys = zip(*(to_sheet(p.X, p.Y) for p in pts))
            ax.plot(xs, ys, **style, solid_capstyle="round")
    return lambda x, y, z: to_sheet(*fn(x, y, z))


def label(ax, p, s, dx=5.0, dy=5.0, color="#c00000"):
    x, y = p
    ax.plot([x, x + dx * 0.8], [y, y + dy * 0.8], color=color, lw=0.4)
    ax.add_patch(MCircle((x, y), 0.6, color=color, lw=0))
    text(ax, x + dx, y + dy, s, size=6.5, color=color, weight="bold", va="center",
         ha="left" if dx >= 0 else "right")


def table(ax, x, y, cols, rows, size=5.4, row_h=3.6):
    """cols: [(header, width_mm)], rows: list of lists of str. (x, y) = top-left."""
    w = sum(c[1] for c in cols)
    ax.add_patch(MRect((x, y - row_h * (len(rows) + 1)), w, row_h * (len(rows) + 1), fill=False, lw=0.6))
    cx = x
    for hdr, cw in cols:
        text(ax, cx + 0.8, y - 0.6, hdr, size=size, weight="bold")
        cx += cw
        ax.plot([cx, cx], [y, y - row_h * (len(rows) + 1)], color="k", lw=0.3)
    for r, row in enumerate(rows):
        yy = y - row_h * (r + 1)
        ax.plot([x, x + w], [yy, yy], color="k", lw=0.3 if r else 0.6)
        cx = x
        for (hdr, cw), cell in zip(cols, row):
            text(ax, cx + 0.8, yy - 0.6, str(cell), size=size)
            cx += cw
    return y - row_h * (len(rows) + 1)


def notes(ax, x, y, title, lines, size=6.0, width=95):
    import textwrap
    text(ax, x, y, title, size=7, weight="bold")
    yy = y - 4.5
    for i, line in enumerate(lines, 1):
        wrapped = textwrap.wrap(line, width)
        for k, w in enumerate(wrapped):
            text(ax, x + (0 if k == 0 else 4), yy, (f"{i}. " if k == 0 else "") + w, size=size)
            yy -= size * 0.5
        yy -= 0.8
    return yy


def dim(ax, p1, p2, s, off=(0, 0), size=5.5):
    ax.annotate("", xy=p1, xytext=p2, arrowprops=dict(arrowstyle="<|-|>", lw=0.4, mutation_scale=4,
                                                      shrinkA=0, shrinkB=0, color="k"))
    mx, my = (p1[0] + p2[0]) / 2 + off[0], (p1[1] + p2[1]) / 2 + off[1]
    text(ax, mx, my, s, size=size, ha="center", va="center",
         bbox=dict(facecolor="white", edgecolor="none", pad=0.3))


# --------------------------------------------------------------------------
# sheets
# --------------------------------------------------------------------------
def top_sheet1(pdf, shape, right, part, dwg, version):
    fig, ax = new_sheet()
    to = place_view(ax, shape, "under", 115, 175, 1.0)
    text(ax, 20, 282, "VIEW FROM BELOW (−Z), parting face up — scale 1:1", size=8, weight="bold")
    rows = top_threads(right)
    for r in rows:
        if r["id"].startswith("T"):
            label(ax, to(r["x"], r["y"], r["z"]), r["id"])
        else:
            label(ax, to(r["x"], r["y"], r["z"]), r["id"], dx=-6 if (r["x"] > 0) == right else 6)
    for f in top_features(right):
        label(ax, to(float(f[2]), float(f[3]), E.Z_TOP), f[0], dx=6, dy=-6, color="#0050a0")
    y = table(ax, 222, 283, [("ID", 9), ("Thread", 17), ("Hand", 9), ("Cls", 8), ("Tap drill", 13),
                             ("Drill depth", 15), ("Min full thr.", 16), ("X", 14), ("Y", 14), ("Z", 10),
                             ("Note", 63)],
              [[r["id"], r["thread"], r["hand"], r["cls"], f"Ø{r['drill']}", f"{r['depth']}",
                f"{r['full']}", f"{r['x']:.2f}", f"{r['y']:.2f}", f"{r['z']:.1f}", r["note"]] for r in rows])
    text(ax, 222, y - 1.5, "X/Y/Z = hole start point in STEP coordinates. T holes: drilled +Z from the PCB "
         "face of the boss. L holes: drilled into the part, normal to the wall, from the boss face.", size=5.2)
    y = table(ax, 222, y - 5, [("ID", 9), ("Feature (no thread)", 140), ("X", 14), ("Y", 14)], top_features(right))
    tq = sum(1 for r in rows if r["id"].startswith("T"))
    lq = len(rows) - tq
    notes(ax, 222, y - 8, "GENERAL NOTES", [
        f"Geometry per {part}.step. Dimensions not shown are taken from the STEP model.",
        f"Material: {TOP_MATERIAL}.",
        f"THREADS: {tq}x M2.5x0.45-6H and {lq}x M3x0.5-6H, ISO metric coarse, ALL RIGHT-HAND (clockwise to "
        "tighten). Holes are modelled at tap-drill diameter in the STEP; tap them per the table. Use bottoming "
        "taps or thread-forming taps to reach the minimum full-thread depth.",
        ("This is a LEFT-hand part: a mirror image of the right-hand part. Threads stay RIGHT-HAND; do not "
         "mirror the thread direction." if not right else
         "The left-hand part is a mirror image of this part. Its threads are also RIGHT-HAND."),
        "Holes marked BLIND under key well: 1.1 mm of material remains to the cosmetic key-well floor. "
        "Must not break through or leave witness marks on the top surface.",
        f"Switch cutouts ({len(E.KEYS(_side(right)))}x): 14.00 +0.05/-0 square, corner R0.5 max, plus "
        f"{2 * len(E.stab_keys(_side(right)))} stabiliser cutouts. Plate thickness 1.50 ±0.05. "
        "Plate flatness 0.2 over the part.",
        "Display window W1 and pocket D1: the pocket runs from the parting side up to 0.8 mm under the top face; "
        "the window opens it. USB-C notch U1 and TRRS hole J1 are side operations (see table).",
        (f"Detent bosses L1-L3 carry {E.LEG_TEETH} radial teeth: see sheet 2. Tooth count is critical."
         if E.DETENT_TEETH else
         "Leg bosses L1-L3: plain Ø10 bosses with a FLAT face (no teeth), see sheet 2."),
        "Cosmetic surfaces: top face, key well, outer walls, leg bosses: no tool marks, scratches or "
        "clamp marks. Inside (cavity) surfaces are non-cosmetic.",
        ("Break sharp edges 0.1-0.2 mm, except detent tooth crests and switch-cutout edges (0.1 max)."
         if E.DETENT_TEETH else
         "Break sharp edges 0.1-0.2 mm, except switch-cutout edges (0.1 max)."),
        f"Finish: {FINISH}. Mask threads during anodizing, or re-tap after anodizing.",
    ], width=118)
    title_block(ax, part, dwg, "1 of 2", "1:1", version, TOP_MATERIAL)
    pdf.savefig(fig)
    plt.close(fig)


def _boss_teeth_spec(ax, rows, r0):
    """Detail C (tooth profile) and the detent teeth table; returns the table bottom."""
    r1 = E.LEG_BOSS_D / 2
    # tooth profile, 20:1, at the boss rim
    k = math.tan(math.pi / E.LEG_TEETH) / math.tan(math.radians(E.LEG_TOOTH_ANGLE) / 2)
    pitch = 2 * math.pi * r1 / E.LEG_TEETH
    hgt = r1 * k
    S2 = 20.0
    px0, py0 = 285, 215
    pts = []
    for i in range(4):
        pts += [(px0 + i * pitch * S2, py0), (px0 + (i + 0.5) * pitch * S2, py0 - hgt * S2)]
    pts.append((px0 + 4 * pitch * S2, py0))
    ax.plot(*zip(*pts), color="k", lw=0.7)
    ax.plot([px0 - 4, px0 + 4 * pitch * S2 + 2], [py0, py0], color="#0050a0", lw=0.3, ls="--")
    text(ax, px0 - 5, py0, "tip plane", size=5.5, color="#0050a0", ha="right", va="center")
    dim(ax, (px0, py0 + 4), (px0 + pitch * S2, py0 + 4), f"pitch {pitch:.3f} at Ø{E.LEG_BOSS_D:.0f}", off=(0, 3))
    dim(ax, (px0 + 4 * pitch * S2 + 4, py0), (px0 + 4 * pitch * S2 + 4, py0 - hgt * S2),
        f"{hgt:.3f}", off=(6, 0))
    text(ax, px0 + 1.5 * pitch * S2, py0 - hgt * S2 + 1, f"{E.LEG_TOOTH_ANGLE:.0f}°", size=6, ha="center",
         va="bottom")
    text(ax, px0 + 2 * pitch * S2, py0 + 13, "DETAIL C — TOOTH PROFILE at boss rim (Ø10), scale 20:1",
         size=7, weight="bold", ha="center")

    # tooth spec table
    tilt = math.degrees(math.atan(k))
    spec = [
        ["Number of teeth", f"{E.LEG_TEETH}  (CRITICAL — must match the leg hub, drawing {DWG}-LEG)"],
        ["Angular pitch", f"{360 / E.LEG_TEETH:.3f}°, equally spaced, no clocking requirement"],
        ["Tooth form", f"symmetric V, {E.LEG_TOOTH_ANGLE:.0f}° included angle, radial (Hirth / face-serration type)"],
        ["Toothed annulus", f"Ø{2 * r0:.1f} to Ø{E.LEG_BOSS_D:.1f} (to boss rim)"],
        ["Tooth height", f"{hgt:.3f} at Ø{E.LEG_BOSS_D:.0f};  {r0 * k:.3f} at Ø{2 * r0:.1f}  (proportional to radius)"],
        ["Groove bottom", f"straight line inclined {tilt:.2f}° to the tip plane, meeting the boss axis in the tip "
                          "plane"],
        ["Crest / root", "sharp, R0.1 max;  crests are the tip plane (no flat land on teeth)"],
        ["Centre land", f"Ø{2 * r0:.1f} flat, recessed {r0 * k:.3f} below tip plane (= root depth at Ø{2 * r0:.1f})"],
        ["Tip plane", f"{E.LEG_BOSS_H} ±0.05 proud of the wall face, parallel to wall, perpendicular to thread axis"],
        ["Thread", f"M3x0.5-6H RIGHT-HAND, concentric with boss within Ø0.05; tap drill Ø{E.LEG_TAP_D}"],
        ["Quantity", f"{len(rows)} bosses per part (L1-L{len(rows)}), identical"],
        ["Machining hint", f"90° engraving cutter, {E.LEG_TEETH} radial passes indexed {360 / E.LEG_TEETH:.0f}°, "
                           f"each a straight ramp of {tilt:.2f}°; 4th axis or right-angle head"],
        ["Mating part", f"custom leg worxboard_leg (drawing {DWG}-LEG, conjugate teeth) + stock M3 spring thumbscrew"],
    ]
    yb = table(ax, 225, 182, [("Detent teeth specification", 38), ("", 147)], spec, size=5.6, row_h=4.0)
    return yb


def top_sheet2(pdf, shape, right, part, dwg, version):
    fig, ax = new_sheet()
    rows = [r for r in top_threads(right) if r["id"].startswith("L")]
    # elevations
    for view, cy, title in (("+X", 262, "VIEW FROM +X"), ("-X", 222, "VIEW FROM −X")):
        to = place_view(ax, shape, view, 115, cy, 1.0)
        text(ax, 20, cy + 16, f"{title} — scale 1:1", size=7, weight="bold")
        for r in rows:
            nx = -float(r["direction"].split("(")[1].split(",")[0])     # outward normal x
            if (view == "+X" and nx > 0.5) or (view == "-X" and nx < -0.3):
                label(ax, to(r["x"], r["y"], r["z"]), r["id"], dx=7, dy=9)

    # detail: boss face, 5:1
    s = 5.0
    cx, cy = 70, 120
    r1, r0 = E.LEG_BOSS_D / 2, E.LEG_TOOTH_R0
    ax.add_patch(MCircle((cx, cy), r1 * s, fill=False, lw=0.8))
    if E.DETENT_TEETH:
        ax.add_patch(MCircle((cx, cy), r0 * s, fill=False, lw=0.6))
    ax.add_patch(MCircle((cx, cy), E.LEG_TAP_D / 2 * s, fill=False, lw=0.6))
    th = [math.radians(a) for a in range(0, 271, 6)]                     # 3/4 thread arc
    ax.plot([cx + 1.5 * s * math.cos(t) for t in th], [cy + 1.5 * s * math.sin(t) for t in th], color="k", lw=0.3)
    for i in range(E.LEG_TEETH if E.DETENT_TEETH else 0):
        a = 2 * math.pi * i / E.LEG_TEETH
        ax.plot([cx + r0 * s * math.cos(a), cx + r1 * s * math.cos(a)],
                [cy + r0 * s * math.sin(a), cy + r1 * s * math.sin(a)], color="k", lw=0.35)        # crest
        b = a + math.pi / E.LEG_TEETH
        ax.plot([cx + r0 * s * math.cos(b), cx + r1 * s * math.cos(b)],
                [cy + r0 * s * math.sin(b), cy + r1 * s * math.sin(b)], color="0.5", lw=0.25)      # root
    if E.DETENT_TEETH:
        a10 = 2 * math.pi / E.LEG_TEETH
        for a in (0, a10):
            ax.plot([cx, cx + (r1 + 3) * s * math.cos(a)], [cy, cy + (r1 + 3) * s * math.sin(a)],
                    color="#0050a0", lw=0.3, ls="--")
        text(ax, cx + (r1 + 3.2) * s, cy + 2, f"{360 / E.LEG_TEETH:.0f}° pitch", size=6, color="#0050a0",
             va="center")
        dim(ax, (cx - r0 * s, cy - 4), (cx + r0 * s, cy - 4), f"Ø{2 * r0:.1f}", size=5)
    dim(ax, (cx - r1 * s, cy - r1 * s - 5), (cx + r1 * s, cy - r1 * s - 5), f"Ø{E.LEG_BOSS_D:.1f} ±0.1")
    text(ax, cx, cy + r1 * s + 9, f"DETAIL A — DETENT BOSS L1-L3, face view, scale 5:1  ({E.LEG_TEETH} TEETH)"
         if E.DETENT_TEETH else "DETAIL A — LEG BOSS L1-L3, face view, scale 5:1  (FLAT FACE, NO TEETH)",
         size=7, weight="bold", ha="center")
    ax.plot([cx + 1.2 * s * 0.7, cx - 9 * s * 0.7 - 6], [cy + 1.2 * s * 0.7, cy + r1 * s + 2], color="k", lw=0.3)
    text(ax, cx - 9 * s * 0.7 - 7, cy + r1 * s + 2, "M3x0.5-6H RH\ntap drill Ø2.5", size=5.5, va="center",
         ha="right")

    # section B-B through boss axis, 5:1 (wall-local: u = depth into part, v = Z - LEG_Z)
    ox, oy = 165, 110
    pad_d = E.LEG_PAD[1]

    def P2(u, v):
        return ox + u * s, oy + v * s
    zr = lambda z: z - E.LEG_Z  # noqa: E731
    hatch = dict(fc="#e8ecf2", ec="k", lw=0.6, hatch="////")
    ax.add_patch(MPoly([P2(0, zr(E.Z_SPLIT)), P2(E.WALL, zr(E.Z_SPLIT)), P2(E.WALL, zr(E.Z_TOP)),
                        P2(0, zr(E.Z_TOP))], closed=True, **hatch))
    ax.add_patch(MPoly([P2(E.WALL, zr(E.Z_PCB_TOP + 0.4)), P2(E.WALL + pad_d, zr(E.Z_PCB_TOP + 0.4)),
                        P2(E.WALL + pad_d, zr(E.Z_POCKET_CEIL)), P2(E.WALL, zr(E.Z_POCKET_CEIL))],
                       closed=True, **hatch))
    r1 = E.LEG_BOSS_D / 2
    ax.add_patch(MPoly([P2(-E.LEG_BOSS_H, -r1), P2(0, -r1), P2(0, r1), P2(-E.LEG_BOSS_H, r1)], closed=True, **hatch))
    depth = max(r["depth"] for r in rows)
    ax.add_patch(MRect(P2(-E.LEG_BOSS_H, -E.LEG_TAP_D / 2), depth * s, E.LEG_TAP_D * s, fc="white", ec="k", lw=0.5))
    for v in (-1.5, 1.5):
        ax.plot(*zip(P2(-E.LEG_BOSS_H, v), P2(-E.LEG_BOSS_H + depth - 0.5, v)), color="k", lw=0.3)
    ax.plot(*zip(P2(-E.LEG_BOSS_H - 2, 0), P2(E.WALL + pad_d + 1, 0)), color="#0050a0", lw=0.3, ls="-.")
    dim(ax, P2(-E.LEG_BOSS_H, r1 + 1.6), P2(0, r1 + 1.6), f"{E.LEG_BOSS_H} ±0.05", off=(0, 3.5))
    dim(ax, P2(-E.LEG_BOSS_H - 2, -r1), P2(-E.LEG_BOSS_H - 2, r1), f"Ø{E.LEG_BOSS_D:.0f}", off=(-5, 0))
    dim(ax, P2(0, zr(E.Z_SPLIT) - 1.2), P2(E.WALL, zr(E.Z_SPLIT) - 1.2), f"wall {E.WALL:.0f}", off=(0, -3))
    dim(ax, P2(-E.LEG_BOSS_H, zr(E.Z_SPLIT) - 3.4), P2(-E.LEG_BOSS_H + depth, zr(E.Z_SPLIT) - 3.4),
        f"drill depth {min(r['depth'] for r in rows)}-{depth} per table", off=(0, -3))
    text(ax, ox + (E.WALL + pad_d / 2) * s, oy + zr(E.Z_PCB_TOP + 0.4) * s - 2, f"thread axis (dash-dot): "
         f"Z = {E.LEG_Z} in STEP", size=5.5, color="#0050a0", ha="center")
    text(ax, ox + (E.WALL + pad_d / 2) * s, oy + zr(E.Z_POCKET_CEIL) * s + 2,
         "pad behind wall\n(depth 1.75-6, see STEP)", size=5.5, ha="center", va="bottom")
    text(ax, ox - E.LEG_BOSS_H * s, oy + zr(E.Z_TOP) * s + 13, "outer wall face", size=5.5, ha="center")
    ax.plot(*zip(P2(0, zr(E.Z_TOP) + 2.2), P2(0, zr(E.Z_TOP))), color="k", lw=0.3)
    text(ax, ox + 15, oy + (zr(E.Z_TOP) + 7) * s, "SECTION B-B through boss axis, scale 5:1 (schematic)",
         size=7, weight="bold", ha="center")

    if E.DETENT_TEETH:
        yb = _boss_teeth_spec(ax, rows, r0)
    else:
        spec = [
            ["Boss", f"Ø{E.LEG_BOSS_D:.1f} ±0.1, {E.LEG_BOSS_H} ±0.05 proud of the outer wall face"],
            ["Bearing face", "FLAT, no teeth. Flatness 0.05, perpendicular to the thread axis within 0.05. "
                             "Ra 1.6 max"],
            ["Function", "the leg hub is clamped against this face by the M3 spring thumbscrew (friction)"],
            ["Thread", f"M3x0.5-6H RIGHT-HAND, concentric with boss within Ø0.05; tap drill Ø{E.LEG_TAP_D}"],
            ["Quantity", f"{len(rows)} bosses per part (L1-L{len(rows)}), identical"],
            ["Machining hint", "side op (4th axis, right-angle head or a setup per wall): face the boss, "
                               "profile Ø10, drill and tap M3"],
            ["Mating part", f"custom leg worxboard_leg (drawing {DWG}-LEG, flat hub face) + stock M3 spring thumbscrew"],
        ]
        yb = table(ax, 225, 182, [("Leg boss specification", 38), ("", 147)], spec, size=5.6, row_h=4.0)
    loc = [[r["id"], f"{r['x']:.2f}", f"{r['y']:.2f}", f"{r['z']:.1f}", r["direction"].split("wall, ")[-1],
            f"{r['depth']}"] for r in rows]
    table(ax, 225, yb - 4, [("Boss", 12), ("X face", 18), ("Y face", 18), ("Z", 10),
                            ("Thread direction (into part)", 62), ("Drill depth", 18)], loc, size=5.6, row_h=4.0)
    text(ax, 225, yb - 4 - 4.0 * (len(loc) + 1) - 1.5, "X/Y/Z: centre of the boss face (tooth tip plane) in STEP coordinates.",
         size=5.2)
    title_block(ax, part, dwg, "2 of 2", "1:1, 5:1, 20:1" if E.DETENT_TEETH else "1:1, 5:1", version, TOP_MATERIAL)
    pdf.savefig(fig)
    plt.close(fig)


def bottom_sheet(pdf, shape, right, part, dwg, version):
    fig, ax = new_sheet()
    to = place_view(ax, shape, "under", 115, 175, 1.0)
    text(ax, 20, 282, "VIEW FROM BELOW (−Z), outside (cosmetic) face — scale 1:1", size=8, weight="bold")
    rows = bottom_holes(right)
    for r in rows:
        label(ax, to(r["x"], r["y"], 0), r["id"], dx=5 if r["id"].startswith("C") else -6)
    y = table(ax, 222, 283, [("ID", 9), ("Feature", 52), ("X", 15), ("Y", 15), ("Note", 50)],
              [[r["id"], r["feature"], f"{r['x']:.2f}", f"{r['y']:.2f}", r["note"]] for r in rows])
    text(ax, 222, y - 1.5, "X/Y in STEP coordinates; features are on the underside (Z = 0).", size=5.2)
    notes(ax, 222, y - 8, "GENERAL NOTES", [
        f"Geometry per {part}.step. Dimensions not shown are taken from the STEP model.",
        f"Material: {TOP_MATERIAL}.",
        "NO THREADS in this part. C1-C8: clearance holes with 90° countersink for M2.5 ISO 10642 / DIN 7991 "
        "countersunk screws; heads must sit flush or up to 0.2 below the underside.",
        "The USB-C plug recess of the top part continues 0.8 mm into the back wall of this part (see STEP). "
        "M1: engraved side mark, cosmetic.",
        ("This is a LEFT-hand part: a mirror image of the right-hand part." if not right else
         "The left-hand part is a mirror image of this part."),
        "Cosmetic surfaces: underside and outer walls: no tool marks, scratches or clamp marks. Inside "
        "(pocket) surfaces are non-cosmetic.",
        "Break sharp edges 0.1-0.2 mm unless modelled.",
        f"Finish: {FINISH}.",
    ], width=118)
    title_block(ax, part, dwg, "1 of 1", "1:1", version, TOP_MATERIAL)
    pdf.savefig(fig)
    plt.close(fig)


def _hub_teeth_spec(ax, r_hub, r0):
    """Detail E (hub tooth profile) and the hub teeth table; returns the table bottom."""
    k = E.tooth_k()
    # profile at the rim, 20:1 (hub teeth point down, towards the case)
    pitch = 2 * math.pi * r_hub / E.LEG_TEETH
    hgt = r_hub * k
    S2 = 20.0
    px0, py0 = 125, 112
    pts = []
    for i in range(4):
        pts += [(px0 + i * pitch * S2, py0), (px0 + (i + 0.5) * pitch * S2, py0 - hgt * S2)]
    pts.append((px0 + 4 * pitch * S2, py0))
    ax.plot(*zip(*pts), color="k", lw=0.7)
    ax.plot([px0 - 4, px0 + 4 * pitch * S2 + 2], [py0, py0], color="#0050a0", lw=0.3, ls="--")
    text(ax, px0 + 4 * pitch * S2 + 3, py0 + 1.5, "face plane Z = 0 (roots)", size=5.5, color="#0050a0")
    dim(ax, (px0, py0 + 4), (px0 + pitch * S2, py0 + 4), f"pitch {pitch:.3f} at Ø{E.LEG_HUB_D}", off=(0, 3))
    dim(ax, (px0 + 4 * pitch * S2 + 4, py0), (px0 + 4 * pitch * S2 + 4, py0 - hgt * S2), f"{hgt:.3f}",
        off=(6, 0))
    text(ax, px0 + 1.5 * pitch * S2, py0 - hgt * S2 - 1, f"{E.LEG_TOOTH_ANGLE:.0f}°", size=6, ha="center")
    text(ax, px0 + 2 * pitch * S2, py0 + 13, f"DETAIL E — TOOTH PROFILE at hub rim (Ø{E.LEG_HUB_D}), 20:1",
         size=7, weight="bold", ha="center")

    tilt = math.degrees(math.atan(k))
    spec = [
        ["Number of teeth", f"{E.LEG_TEETH}  (CRITICAL — same as case bosses L1-L3, drawing {DWG}-TOP)"],
        ["Angular pitch", f"{360 / E.LEG_TEETH:.3f}°, equally spaced, no clocking requirement"],
        ["Tooth form", f"symmetric V, {E.LEG_TOOTH_ANGLE:.0f}° included, radial; exact negative of the case boss"],
        ["Toothed annulus", f"Ø{2 * r0:.1f} to Ø{E.LEG_HUB_D} (to hub rim)"],
        ["Roots", "straight radial lines IN the face plane Z = 0 (no slope)"],
        ["Ridges", f"straight lines rising {tilt:.2f}° from the axis: {r0 * k:.3f} high at Ø{2 * r0:.1f}, "
                   f"{hgt:.3f} at Ø{E.LEG_HUB_D}"],
        ["Crest / root", "sharp, R0.1 max"],
        ["Centre land", f"Ø{2 * r0:.1f} flat in the face plane Z = 0, around the Ø{E.LEG_HOLE_D} hole"],
        ["Machining hint", f"turn/mill a {tilt:.2f}° cone on the face (Ø{2 * r0:.1f} to rim), then "
                           f"{E.LEG_TEETH} radial passes of a 90° engraver, tip ON the face plane, "
                           f"indexed {360 / E.LEG_TEETH:.0f}°. 3-axis, toothed face up."],
    ]
    y = table(ax, 225, 283, [("Hub teeth specification", 30), ("", 155)], spec, size=5.5, row_h=4.0)
    return y


def leg_sheet(pdf, shape, part, dwg, version):
    fig, ax = new_sheet()
    teeth = E.DETENT_TEETH
    face = "toothed face" if teeth else "bearing face"
    r_hub, r0 = E.LEG_HUB_D / 2, E.LEG_TOOTH_R0
    zc = E.LEG_HUB_L - E.LEG_ARM_T / 2
    y_sh = E.LEG_LEN - E.LEG_CAP_L

    # view A: toothed face (from -Z), 2.5:1
    s = 2.5
    to = place_view(ax, shape, "under", 62, 178, s)
    text(ax, 20, 282, f"VIEW A — {face} (−Z), scale 2.5:1", size=8, weight="bold")
    dim(ax, to(r_hub, -r_hub - 2, 0), to(-r_hub, -r_hub - 2, 0), f"Ø{E.LEG_HUB_D} -0.1")
    dim(ax, to(E.LEG_ARM_W / 2 + 3, 0, 0), to(E.LEG_ARM_W / 2 + 3, y_sh, 0), f"{y_sh:.1f}", off=(5, 0))
    dim(ax, to(E.LEG_ARM_W / 2 + 9, 0, 0), to(E.LEG_ARM_W / 2 + 9, y_sh + E.LEG_SPIGOT[1], 0),
        f"{y_sh + E.LEG_SPIGOT[1]:.1f}", off=(5, 0))
    dim(ax, to(-E.LEG_NECK_D / 2, y_sh + 1.0, 0), to(E.LEG_NECK_D / 2, y_sh + 1.0, 0), f"Ø{E.LEG_NECK_D}",
        off=(-11, 0), size=5)
    dim(ax, to(-E.LEG_SPIGOT[0] / 2, y_sh + 3.5, 0), to(E.LEG_SPIGOT[0] / 2, y_sh + 3.5, 0),
        f"Ø{E.LEG_SPIGOT[0]}", off=(-11, 0), size=5)
    dim(ax, to(-E.LEG_ARM_W / 2, 8, 0), to(E.LEG_ARM_W / 2, 8, 0), f"{E.LEG_ARM_W}", off=(-10, 0), size=5)
    text(ax, 62, 108, f"Pivot axis = origin of the STEP model.\nArm along +Y, {face} at Z = 0.",
         size=5.5, ha="center")

    # side view (+X), 2.5:1, hidden lines show the bore
    to2 = place_view(ax, shape, "+X", 150, 262, s, hidden=True)
    text(ax, 95, 282, "VIEW B — side (+X), scale 2.5:1, hidden lines dashed", size=8, weight="bold")
    dim(ax, to2(0, -r_hub - 2.5, 0), to2(0, -r_hub - 2.5, E.LEG_HUB_L), f"{E.LEG_HUB_L}", off=(-5, 0))
    dim(ax, to2(0, 12, E.LEG_HUB_L - E.LEG_ARM_T), to2(0, 12, E.LEG_HUB_L), f"{E.LEG_ARM_T}", off=(5, 0))
    text(ax, to2(0, 0, -1)[0], to2(0, 0, -1)[1] - 1.5, "teeth" if teeth else "bearing face", size=5.5, ha="center")

    # detail D: toothed face 6:1
    sd = 6.0
    cx, cy = 172, 185
    ax.add_patch(MCircle((cx, cy), r_hub * sd, fill=False, lw=0.8))
    if teeth:
        ax.add_patch(MCircle((cx, cy), r0 * sd, fill=False, lw=0.6))
    ax.add_patch(MCircle((cx, cy), E.LEG_HOLE_D / 2 * sd, fill=False, lw=0.6))
    ax.add_patch(MCircle((cx, cy), E.LEG_CBORE[0] / 2 * sd, fill=False, lw=0.3, ls=(0, (2, 1.5)), ec="0.5"))
    for i in range(E.LEG_TEETH if teeth else 0):
        a = 2 * math.pi * i / E.LEG_TEETH
        b = a + math.pi / E.LEG_TEETH
        ax.plot([cx + r0 * sd * math.cos(b), cx + r_hub * sd * math.cos(b)],
                [cy + r0 * sd * math.sin(b), cy + r_hub * sd * math.sin(b)], color="k", lw=0.35)      # ridge
        ax.plot([cx + r0 * sd * math.cos(a), cx + r_hub * sd * math.cos(a)],
                [cy + r0 * sd * math.sin(a), cy + r_hub * sd * math.sin(a)], color="0.5", lw=0.25)    # root
    dim(ax, (cx - r_hub * sd, cy - r_hub * sd - 4), (cx + r_hub * sd, cy - r_hub * sd - 4), f"Ø{E.LEG_HUB_D}")
    if teeth:
        dim(ax, (cx - r0 * sd, cy + 3), (cx + r0 * sd, cy + 3), f"Ø{2 * r0:.1f}", size=5)
    dim(ax, (cx - E.LEG_HOLE_D / 2 * sd, cy - 3), (cx + E.LEG_HOLE_D / 2 * sd, cy - 3),
        f"Ø{E.LEG_HOLE_D} thru", size=5)
    text(ax, cx, cy + r_hub * sd + 8, f"DETAIL D — toothed face, scale 6:1  ({E.LEG_TEETH} TEETH, "
         f"{360 / E.LEG_TEETH:.0f}° pitch)" if teeth else "DETAIL D — bearing face, scale 6:1  (FLAT, NO TEETH)",
         size=7, weight="bold", ha="center")
    text(ax, cx + r_hub * sd + 2, cy - r_hub * sd + 2, f"counterbore Ø{E.LEG_CBORE[0]} x {E.LEG_CBORE[1]}\n"
         "deep, from the back face\n(dashed, hidden)", size=5.2, color="0.35", va="bottom")

    if teeth:
        y = _hub_teeth_spec(ax, r_hub, r0)
    else:
        spec = [
            ["Bearing face", f"Z = 0, FLAT, no teeth, Ø{E.LEG_HOLE_D} to Ø{E.LEG_HUB_D}. Flatness 0.05, "
                             "perpendicular to the bore within 0.05. Ra 1.6 max"],
            ["Function", f"clamped against the flat case boss (drawing {DWG}-TOP sheet 2) by the M3 spring "
                         "thumbscrew; the leg holds its angle by friction"],
        ]
        y = table(ax, 225, 283, [("Bearing face", 30), ("", 155)], spec, size=5.5, row_h=4.0)
    feats = [
        ["Hub", f"Ø{E.LEG_HUB_D} -0.1 x {E.LEG_HUB_L} long (face to back face), back edge chamfer "
                f"{E.LEG_EDGE}x45°"],
        ["Bore", f"Ø{E.LEG_HOLE_D} +0.1/0 THROUGH (M3 clearance, NO THREAD), on the pivot axis"],
        ["Counterbore", f"Ø{E.LEG_CBORE[0]} +0.1/0 x {E.LEG_CBORE[1]} deep from the back face (spring seat)"],
        ["Arm", f"{E.LEG_ARM_W} wide at hub tapering to {E.LEG_NECK_D}, {E.LEG_ARM_T} thick, flush with the "
                "back face, long edges R1.5"],
        ["Neck / spigot", f"Ø{E.LEG_NECK_D} to {y_sh:.1f} from axis; spigot Ø{E.LEG_SPIGOT[0]} -0.05 x "
                          f"{E.LEG_SPIGOT[1]} for the foot cap, end chamfer 0.4"],
        ["Length", f"{y_sh + E.LEG_SPIGOT[1]:.1f} axis to spigot end; {E.LEG_LEN:.0f} to foot tip with cap"],
    ]
    y = table(ax, 225, y - 4, [("Feature", 30), ("Specification", 155)], feats, size=5.5, row_h=4.0)
    notes(ax, 225, y - 6, "GENERAL NOTES", [
        f"Geometry per {part}.step. Dimensions not shown are taken from the STEP model.",
        f"Material: {TOP_MATERIAL}.  QUANTITY: {LEG_QTY} pcs (3 per keyboard half; identical, not handed).",
        "NO THREADS in this part. The stock ErgoDox EZ M3 spring thumbscrew passes through the Ø3.4 bore "
        "into the M3 thread of the case boss.",
        *(["Toothed face: no burrs; tooth count and 90° form are critical (the leg must click in every 10° step).",
           "Break sharp edges 0.1-0.2 mm, except the tooth crests (0.1 max)."] if teeth else
          ["Bearing face: flat, no burrs, no raised tool marks.", "Break sharp edges 0.1-0.2 mm."]),
        f"Finish: {FINISH}; same colour as the case.",
        "Foot cap worxboard_leg_cap: 3D print in TPU 95A (not machined), push onto the spigot.",
    ], width=118)
    title_block(ax, part, dwg, "1 of 1", "2.5:1, 6:1, 20:1" if teeth else "2.5:1, 6:1", version, TOP_MATERIAL)
    pdf.savefig(fig)
    plt.close(fig)


def main(exports: str, order: str, version: str):
    os.makedirs(order, exist_ok=True)
    csv_rows = []
    for side in E.SIDES[::-1]:
        right = side == "right"
        for kind in ("top", "bottom"):
            part = f"worxboard_{side}_{kind}"
            step = os.path.join(exports, part + ".step")
            shape = import_step(step)
            dwg = f"{DWG}-{kind.upper()}-{side[0].upper()}"
            with PdfPages(os.path.join(order, part + ".pdf")) as pdf:
                if kind == "top":
                    top_sheet1(pdf, shape, right, part, dwg, version)
                    top_sheet2(pdf, shape, right, part, dwg, version)
                    for r in top_threads(right):
                        csv_rows.append([part, r["id"], r["thread"], r["hand"], r["cls"], r["drill"], r["depth"],
                                         r["full"], f"{r['x']:.3f}", f"{r['y']:.3f}", f"{r['z']:.3f}",
                                         r["direction"], r["note"]])
                    for f in top_features(right):
                        csv_rows.append([part, f[0], f[1], "", "", "", "", "", f[2], f[3], "", "", "no thread"])
                else:
                    bottom_sheet(pdf, shape, right, part, dwg, version)
                    for r in bottom_holes(right):
                        csv_rows.append([part, r["id"], r["feature"], "", "", "", "", "", f"{r['x']:.3f}",
                                         f"{r['y']:.3f}", "0.000", "-Z face", r["note"]])
            shutil.copy(step, os.path.join(order, part + ".step"))
            print(f"  {part}: drawing + STEP")
        # the plate spacer is not machined: laser-cut / print it from the STL
        shutil.copy(os.path.join(exports, f"worxboard_{side}_spacer.stl"), order)
    part = "worxboard_leg"
    step = os.path.join(exports, part + ".step")
    with PdfPages(os.path.join(order, part + ".pdf")) as pdf:
        leg_sheet(pdf, import_step(step), part, f"{DWG}-LEG", version)
    shutil.copy(step, os.path.join(order, part + ".step"))
    shutil.copy(os.path.join(exports, "worxboard_leg_cap.stl"), os.path.join(order, "worxboard_leg_cap.stl"))
    csv_rows += [[part, "H1", f"Ø{E.LEG_HOLE_D} thru (M3 clearance)", "", "", "", "thru", "", "0.000", "0.000",
                  "0.000", "+Z", "no thread"],
                 [part, "CB1", f"counterbore Ø{E.LEG_CBORE[0]} x {E.LEG_CBORE[1]}", "", "", "",
                  f"{E.LEG_CBORE[1]}", "", "0.000", "0.000", f"{E.LEG_HUB_L:.3f}", "-Z", "spring seat"]]
    print(f"  {part}: drawing + STEP (qty {LEG_QTY}), worxboard_leg_cap.stl (print), spacer STLs")
    with open(os.path.join(order, "hole_table.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["part", "id", "thread_or_feature", "hand", "class", "tap_drill", "drill_depth",
                    "min_full_thread", "x", "y", "z", "direction", "note"])
        w.writerows(csv_rows)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "dev")
