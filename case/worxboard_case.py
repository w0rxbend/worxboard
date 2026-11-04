# SPDX-License-Identifier: GPL-3.0-or-later
"""
worxboard case for CNC aluminium milling (build123d, parametric).
Port of ergodox_case.py (w0rxbend/ergodox v0.6.1) to the worxboard layout (spec §10).

Parts per half:
  * TOP    - shell with integrated 1.5 mm switch plate in a recessed key well, perimeter walls,
             display pocket under a raised bezel + viewing window, USB-C and TRRS notches, PCB clamp bosses,
             tent-leg bosses.
  * BOTTOM - tray: floor + low walls + PCB support posts, countersunk M2.5 holes, L / R mark.
  * SPACER - separate plate spacer between the plate and the PCB.
Plus one tent leg and its foot cap (fit all six positions).

Every position comes from the `layout` package (the single source of truth shared with the
PCB): keys, holes, outline, display, jacks and component zones. Layout numbers are in the
KiCad frame of each half (x -> outer on the right half, y -> towards the user, mm); the left
half is built explicitly from its own (mirrored) layout data.
"""
from __future__ import annotations

import importlib
import math
import os
import sys
from functools import lru_cache

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import layout as L  # noqa: E402
from build123d import (  # noqa: E402
    Align, Axis, Box, Circle, Compound, Cylinder, Edge, Face, FontStyle, Kind, Plane, Polyline,
    Pos, Rectangle, RectangleRounded, Rot, Sketch, Solid, Sphere, Text, Torus, Vector, Vertex, Wire,
    chamfer, export_step, export_stl, extrude, fillet, loft, make_face, mirror, offset,
)
from shapely.affinity import affine_transform  # noqa: E402
from shapely.geometry import Point, Polygon, box  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

LO = importlib.import_module("layout.outline")      # the package re-exports outline() over it
LD = importlib.import_module("layout.display")
LH = importlib.import_module("layout.holes")
from layout.keys import HOUSING, local_axes  # noqa: E402
from layout.thumbs import STAB_OFFSET, U as THUMB_U, thumb_pt  # noqa: E402

SIDES = L.SIDES

# --------------------------------------------------------------------------
# Parameters (mm)
# --------------------------------------------------------------------------
# Case design revision, printed on the drawings and in the STEP headers of the order package
# (case/production). Bump it with any change to the ordered geometry.
CASE_REVISION = "A3"
CASE_REVISION_DATE = "2026-11-04"

# Vertical stack, Z = 0 at the bottom face of the case
FLOOR_T = 3.0            # bottom tray floor thickness
Z_SPLIT = 7.0            # top/bottom parting plane == PCB bottom face
PCB_T = 1.6
Z_PCB_TOP = Z_SPLIT + PCB_T                    # 8.6
PLATE_T = 1.5                                  # Cherry MX plate thickness
Z_PLATE_BOT = Z_PCB_TOP + 5.0 - PLATE_T        # 12.1 (MX: plate top 5.0 above PCB top)
Z_PLATE_TOP = Z_PLATE_BOT + PLATE_T            # 13.6
WELL_DEPTH = 4.0                               # key well depth below top surface
Z_TOP = Z_PLATE_TOP + WELL_DEPTH               # 17.6
TOP_SKIN = 3.0                                 # material above the component pocket
Z_POCKET_CEIL = Z_TOP - TOP_SKIN               # 14.6 (6 mm above the PCB for the jacks)
assert abs(Z_PCB_TOP - LD.Z_PCB_TOP) < 1e-9

WALL = 3.0               # perimeter wall thickness
CASE_OFFSET = 3.5        # case outer = PCB outline + 0.5 clearance + WALL (mitre join)
CAVITY_MIN_CLEAR = 0.3   # convex corner radii are reduced until the cavity keeps this to the PCB
CHAMFER_COLLAPSE = 15.0  # PCB corner chamfers shorter than this become one (filleted) case corner
TOP_EDGE_FILLET = 1.5    # rounded top outer edge
SEAM_CHAMFER = 0.5       # small chamfer on both sides of the parting line
TOOL_R = 1.0             # key-well corner radius: corner_r(WELL_DEPTH) (JLCCNC R0.9 at 4.0 deep)
FILLET_MIN_TURN = 20.0   # polygon corners turning less than this (arc chords) stay unfilleted
# JLCCNC CNC Machining Design Guideline (https://jlccnc.com/help/article/CNC-Machining-Design-Guideline,
# read 2026-11-04): an internal corner H deep (from the face the cutter enters by) needs R >= H / 10 + 0.5,
# with a tool of D = H / 5; R0.5 is possible to 3 mm; and its tool table (diameter, maximum length, Min R)
# sets the radius past the Ø2 tool's 10 mm. corner_r() turns a depth into that radius (deviation CASE-8).
JLCCNC_TOOLS = ((2.0, 10.0, 1.5), (3.0, 15.0, 2.0), (4.0, 20.0, 2.5), (6.0, 30.0, 3.5), (8.0, 40.0, 4.5),
                (10.0, 50.0, 5.5))
JLCCNC_SMALL_DEPTH = 3.0  # R0.5 to this depth
JLCCNC_WALL_MIN = 0.8     # recommended minimum wall of a metal part (0.5 absolute)

SWITCH_CUT = 14.0        # MX plate cutout
SWITCH_CUT_R = 0.5       # corner radius (use a 1 mm tool, or switch DOGBONES on)
DOGBONES = False
WELL_CLEAR = 0.6         # well clearance around each key cell
WELL_MIN_WALL = 2.0      # the well is clipped to keep this much wall (T0/T3 overhang, WS0-3)
KEYCAP_INSET = 0.45      # keycap edge inside its 19.05 cell (18.15 cap)
STABILIZERS = True       # plate-mount Cherry stab cutouts on the two 2u thumb keys (spec §5)
# Cherry plate cut-out per stab, across the key (u, + = housing side, layout.stab_dir) and along it
STAB_CUT_U = (-5.53, 6.77)        # main opening, 6.65 wide along the key
STAB_CUT_W = 6.65
STAB_SIDE_NOTCH_U = (-2.3, 0.5)   # notch on the outer side, Cherry 0.875 deep -> 1.0 (1 mm tool)
STAB_SIDE_NOTCH_D = 1.0
STAB_END_NOTCH = (3.3, 1.2)       # notch at the housing end: width along the key, depth
# The Cherry stabiliser wire's long bar runs under the plate, between plate and PCB, from one housing
# to the other, beside the switch: the plate spacer keeps a channel for it on both sides of the key,
# across the key this far from its centre, along it from one stab to the other (deviation ORDER-6)
STAB_WIRE_U = (6.5, 10.0)

# Outline corner radii by vertex class (reference values)
R_BACK = 10.0            # convex corners of the back edge
R_FRONT_OUTER = 12.0     # convex corner at the outer front
R_THUMB = 8.0            # thumb cluster convex corners
R_CONCAVE_TOP = 6.0      # concave corner, back side of the thumb
R_CONCAVE_FRONT = 14.0   # concave corner where main body meets thumb, front side
R_BUMP = 5.0             # TRRS bump corners (spec r6 does not fit the 10.1 mm bump edge, WS3-2)
BACK_Y = 60.0            # convex corners above this y are "back" corners
CONCAVE_FRONT_Y = 130.0  # concave corners below this y use R_CONCAVE_FRONT
BUMP_X, BUMP_Y = 62.2, (80.0, 130.0)           # TRRS bump region (right frame)

# Fasteners: M2.5 countersunk screws from below, through the tray and the PCB into blind tapped holes
# in the top's bosses (deviation CASE-3). JLCCNC threaded-hole guideline: a blind hole keeps at least
# half its diameter unthreaded at the bottom, and the effective thread is at most 3 D. Drill depth is
# the full-diameter depth from the boss face (Z_PCB_TOP); the 118 deg drill point is modelled beyond it.
SCREW_CLEAR_D = 2.9      # M2.5 clearance
SCREW_CSK_D = 5.2        # M2.5 countersunk head (90 deg)
M25_D = 2.5
TAP_D = 2.05             # M2.5 tap drill
DRILL_POINT_DEG = 118.0
TAP_UNTHREADED_MIN = M25_D / 2    # JLCCNC: >= D/2 of a blind hole unthreaded
TAP_THREAD_MAX = 3 * M25_D        # JLCCNC: effective thread <= 3 D
# kind -> (drill depth, min full thread, screw length): bosses in the bezel / edge area, and the two
# under the key well, where the plate leaves 5.0 mm of material above the boss face
TAP_HOLE = {"edge": (6.0, 4.5, 12), "plate": (3.6, 2.3, 10)}
SCREW_HEAD_SINK = 0.2    # the countersunk head sits flush to 0.2 below the underside (bottom drawing)
SCREW_TIP_CLEAR = 0.3    # screw tip (head at its deepest) to the end of the full thread
SCREW_MIN_ENGAGE = 1.4   # shortest thread engagement, head flush (the bosses under the key well)
TAP_SKIN_MIN = 0.75      # drill point to the cosmetic face above it (key-well floor or top face)
BOSS_D = 6.5
POST_D = 6.5
# A boss or post closer to the wall than this is joined to it by a web as wide as the boss, so
# no narrow, deep slot is left between them. Top: the gap is up to 6 mm deep, bottom: 4 mm.
WEB_GAP_TOP = 5.0
WEB_GAP_BOTTOM = 2.0
# Relief pocket above the plate level (outside the key well) is only kept where it is at least
# this wide; the component zones (Z_BACK, Z_TRRS) are always relieved.
RELIEF_MIN_W = 6.0
RELIEF_WELL_SKIN = 1.0   # well wall left between the key well and a relieved component zone
RELIEF_ISLAND_CLEAR = 0.3  # relief pocket edge to the bosses, webs and leg pads standing in it (CASE-8)
RELIEF_QUAD_SEGS = 4     # chords per quarter circle of the relief pockets' arcs: 0.03 mm off a true R1.5,
                         # and the top STEP stays under the 5 MB the repository commits (CASE-8)
# The PJ-320D (J2, gate G2) is 14.1 long: its last 0.9 mm runs past Z_TRRS, through the well skin and
# under the plate between C6R1 and C6R2, and its top is flush with the plate top. Its body + this is
# relieved in the top part (to Z_POCKET_CEIL, through the plate), the spacer and the plate DXF. The
# relief's R1.5 corners (relief_r) leave a body corner r - sqrt(2) (r - c) of it: 0.44 at 0.75 (0.43 with
# the 4-chord arcs, 0.38 in the top after relief_poly's second opening); at 0.5 it was 0.08 / 0.02 (CASE-9).
J2_RELIEF_CLEAR = 0.75
# Least plan clearance from a jack body (J1, J2: layout envelope, on the PCB) to the top part, the
# spacer and the plate DXF: the case is ISO 2768-m, the jack is placed by JLC SMT, the PCB floats in
# the cavity (0.3-0.5 mm clear) as far as its screw holes let it, and a plate edge bearing on the jack
# loads its SMD joints (CASE-9).
JACK_MIN_CLEAR = 0.3

# Tent / tilt legs: reuses the stock EZ spring thumbscrews (M3), see docs/legs.md.
DETENT_TEETH = False
LEG_Z = 12.0             # thread axis; the Ø10 boss then spans Z 7.0-17.0 on the top part
LEG_TAP_D = 2.5          # M3 tap drill
LEG_DEPTH = 7.5          # max drill depth from the boss face
LEG_MIN_DRILL = 5.0      # min drill depth from the boss face
LEG_UNTHREADED = 1.5     # JLCCNC: >= D/2 of the blind M3 hole unthreaded (CASE-3)
LEG_MIN_THREAD = 3.5     # min full thread (> 1 D)
LEG_REACH_CLEAR = 0.3    # the thumbscrew must stop this far short of the end of the full thread
LEG_PAD = (10.0, 6.0)    # pad (along wall, into case) behind the wall
LEG_PAD_MAX = {"inner": 5.0}   # inner pad clamped clear of the display pocket (spec §10.4)
LEG_BOSS_D = 10.0        # boss on the outer wall face
LEG_BOSS_H = 2.7         # boss height above the wall face (bearing face / tooth tips)
LEG_BOSS_ROOT_R = 0.5    # fillet where the boss meets the wall: a floor fillet (the end mill's corner on
                         # the wall face), not a vertical internal corner, so corner_r() does not apply
LEG_BOSS_EDGE = 0.3      # round on the rim of the flat bearing face
LEG_TEETH = 36           # radial detent teeth if DETENT_TEETH (stock: 10 deg steps)
LEG_TOOTH_R0 = 2.2       # teeth run from this radius to the boss edge
LEG_TOOTH_ANGLE = 90.0   # included angle of the V teeth
LEG_HUB_D = 10.4         # stock: 10.4-10.5
LEG_HUB_L = 8.0          # hub length along the screw, bearing face to spring face
LEG_HOLE_D = 3.4         # M3 clearance
LEG_CBORE = (6.5, 4.0)   # spring counterbore in the outer face (diameter, depth)
LEG_ARM_W = 7.5          # arm width in the swing plane at the hub (stock ~7.5)
LEG_ARM_T = 6.0          # arm thickness along the screw, flush with the spring face
LEG_NECK_D = 6.0         # round neck behind the foot cap (= arm width there)
LEG_LEN = 47.0           # pivot to foot tip, cap fitted
LEG_FOOT_D = 9.0         # foot cap outside diameter
LEG_CAP_L = 8.5          # foot cap length (Ø9 cylinder + dome)
LEG_SPIGOT = (4.5, 5.0)  # spigot for the cap (diameter, length)
LEG_EDGE = 0.3           # edge chamfer on the hub
# Foot caps for JLC3DP (deviation CASE-4): its only flexible material, TPU 95A, is FDM with a minimum part
# of 30 x 30 x 10 mm (design guideline; its TPU page says 30 x 30 x 15), and one cap is 9 x 9 x 8.5. So the
# caps are ordered as one tree: CAP_TREE_N caps standing on their open end, joined at the base by runner
# bars, round a tag post that makes the height.
CAP_TREE_N = 8           # 6 per keyboard + 2 spares
CAP_TREE_PITCH = 12.5    # caps on the 8 outer places of a 3 x 3 grid, the tag post in the middle
CAP_RUNNER = 1.6         # runner bar width and height (JLC3DP FDM TPU wall: 1.6 standard, 1.2 min)
CAP_TAG = (8.0, 16.0)    # tag post diameter, height
CAP_TREE_MIN = (30.0, 30.0, 15.0)   # JLC3DP FDM TPU minimum part size, the larger of its two figures
# Stock EZ leg positions (right frame): (name, PCB edge (vertex indices of layout VERTICES),
# anchor point and direction of the line that meets the wall). Outer / inner main walls at
# y 64, thumb leg 0.56 key units along the thumb-cluster end wall.
LEG_MAIN_Y = 64.0
LEG_THUMB_V = 0.56
LEGS = (("outer", (2, 3), (130.0, LEG_MAIN_Y), (1.0, 0.0)),
        ("inner", (12, 13), (130.0, LEG_MAIN_Y), (-1.0, 0.0)),
        ("thumb", (7, 8), thumb_pt(0, LEG_THUMB_V), (-THUMB_U[0], -THUMB_U[1])))

# Display (spec §4, §10.4; gate G1; deviations ELEC-3, CASE-1). J3 is a 5.0 mm socket (C27985230) and a
# stock nice!view sits on its own male header, so the glass top is 8.9 mm above the PCB top nominally and
# 9.75 mm at full tolerance: above Z_TOP. The pocket over the module + 0.5 rises over that stack, under
# a raised bezel around the viewing window.
DISPLAY_STACK_MAX = 9.75     # glass top above the PCB top, full tolerance (ELEC-3)
DISPLAY_GLASS_CLEAR = 0.25   # pocket ceiling above the highest glass top
Z_DISPLAY_TOP = round(Z_PCB_TOP + DISPLAY_STACK_MAX + DISPLAY_GLASS_CLEAR, 3)   # 18.6
BEZEL_SKIN = 1.0             # skin over the pocket, through which the window opens
Z_BEZEL_TOP = round(Z_DISPLAY_TOP + BEZEL_SKIN, 3)                             # 19.6: 2.0 proud of Z_TOP
BEZEL_WALL = 2.0             # bezel wall around the pocket where the key well leaves room
BEZEL_R = 2.0                # plan radius of the bezel's free corners
BEZEL_CHAMFER = 0.5          # 45 deg chamfer on the bezel's top edges
BEZEL_OVERLAP = 0.05         # the bezel runs this far into the key well, which then trims it flush
DISPLAY_LEG_CLEAR = 1.2  # leg pads stay this far from the pocket
DISPLAY_BOSS_CLEAR = 1.0  # bosses / webs stay this far from the pocket

# USB-C on both halves (spec §10.5): back-wall notch + outside recess for the plug overmould
USB_NOTCH = (9.4, 3.6)   # w x h
USB_NOTCH_R = 1.6
USB_RECESS = (13.0, 8.0)
USB_RECESS_DEPTH = 1.8   # leaves 1.2 mm of wall locally
USB_RECESS_R = 1.5
# TRRS (spec §10.6): round hole through the inner bump wall
TRRS_NOTCH_D = 6.5
NOTCH_TOL = 0.2          # notch centres must equal the layout anchors within this
# Reset / boot pin-holes through the top skin (spec §10.7)
PIN_HOLE_D = 3.0
PIN_HOLES = ("SW_BOOT", "SW_RST")

# Rubber feet recesses (right frame)
FOOT_D = 10.5
FOOT_DEPTH = 0.6
FOOT_EDGE_MIN = 1.5      # recess edge to the outline
FEET = [(68.0, 45.0), (198.0, 45.0), (196.0, 148.0), (45.0, 178.0)]

# Plate spacer: separate part between the plate and the PCB, under the plate island, with an
# opening around every switch and stabiliser, clear of the component zones and the display.
SPACER_T = 3.0
SPACER_HOLE = 15.0       # opening per switch: the 14.0 lower housing + 2 x 0.5
SPACER_CLEAR = 0.5       # to the case walls, screw bosses, leg pads, zones and display
SPACER_MIN_WEB = 1.0     # narrowest web left in the spacer (JLC3DP MJF PA12 wall, CASE-5)

# Left == mirror(right) before the side mark: relative volume / area, and centroid / bbox in mm
# (shapely chord approximations differ by a few µm between the two orientations)
MIRROR_TOL = 5e-5
MIRROR_TOL_MM = 0.005    # centroid / bbox; the stab cut-outs once differed by 0.01-0.07 here

# Side mark engraved on the underside
ENGRAVE_AT = (165.0, 100.0)    # right frame
ENGRAVE_SIZE = 10.0
ENGRAVE_DEPTH = 0.4
ENGRAVE_FONT = "DejaVu Sans"

# --------------------------------------------------------------------------
# Frames: KiCad frame of each half -> CAD frame (X right, Y up). OX is the mirror line, so the
# two halves are exact mirror images about X = 0.
# --------------------------------------------------------------------------
OX, OY = L.MIRROR_X / 2, 100.0


def P(x: float, y: float) -> tuple[float, float]:
    return (x - OX, -(y - OY))


def K(cx: float, cy: float) -> tuple[float, float]:
    """CAD frame -> KiCad frame."""
    return (cx + OX, OY - cy)


def to_cad(geom):
    return affine_transform(geom, [1, 0, 0, -1, -OX, OY])


def cad_rot(deg_screen: float) -> float:
    # KiCad rotation (screen CCW with y down) == CAD CCW with y up
    return deg_screen


def mx(side: str, x: float) -> float:
    return x if side == "right" else L.MIRROR_X - x


@lru_cache
def KEYS(side: str) -> tuple:
    """(x, y, cap_w_u, cap_h_u, rot) of the 37 switches."""
    keys = tuple((k.x, k.y, k.w, k.h, k.rot) for k in L.keys(side))
    assert len(keys) == 37
    return keys


@lru_cache
def SCREWS(side: str) -> tuple:
    return tuple(L.holes(side))


@lru_cache
def DISPLAY(side: str) -> dict:
    return L.display(side)


@lru_cache
def JACK(side: str, ref: str):
    return next(j for j in L.jacks(side) if j.ref == ref)


def _rect_poly(r) -> Polygon:
    return box(*r)


# --------------------------------------------------------------------------
# Outline: PCB polygon + CASE_OFFSET (mitre), reference radii by vertex class
# --------------------------------------------------------------------------
def _signed_area(pts) -> float:
    n = len(pts)
    return sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n)) / 2


def _line_x(p, d, q, e):
    """Intersection of lines p + t d and q + s e."""
    den = d[0] * e[1] - d[1] * e[0]
    t = ((q[0] - p[0]) * e[1] - (q[1] - p[1]) * e[0]) / den
    return (p[0] + t * d[0], p[1] + t * d[1])


def _convex(pts, i, orient) -> bool:
    a, b, c = pts[i - 1], pts[i], pts[(i + 1) % len(pts)]
    return ((b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])) * orient > 0


def _collapse_chamfers(pts):
    """Replace short PCB corner chamfers (both ends convex) by their sharp corner."""
    orient = math.copysign(1, _signed_area(pts))
    n = len(pts)
    short = {i for i in range(n) if math.dist(pts[i], pts[(i + 1) % n]) < CHAMFER_COLLAPSE
             and _convex(pts, i, orient) and _convex(pts, (i + 1) % n, orient)}
    consumed = {(i + 1) % n for i in short}
    assert not short & consumed, "adjacent chamfers"
    out = []
    for i in range(n):
        if i in consumed:
            continue
        if i in short:
            a, b = pts[i - 1], pts[i]
            c, d = pts[(i + 1) % n], pts[(i + 2) % n]
            out.append(_line_x(a, (b[0] - a[0], b[1] - a[1]), c, (d[0] - c[0], d[1] - c[1])))
        else:
            out.append(pts[i])
    return out


def _offset_pts(pts, d):
    """Mitre offset of a simple polygon by d (outward)."""
    orient = math.copysign(1, _signed_area(pts))
    n = len(pts)
    lines = []
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        e = (b[0] - a[0], b[1] - a[1])
        ln = math.hypot(*e)
        nrm = (orient * e[1] / ln, -orient * e[0] / ln)
        lines.append(((a[0] + nrm[0] * d, a[1] + nrm[1] * d), e))
    return [_line_x(*lines[i - 1], *lines[i]) for i in range(n)]


def _vertex_radius(p, convex: bool, xmax: float) -> float:
    x, y = p
    bump = x < BUMP_X and BUMP_Y[0] < y < BUMP_Y[1]
    if bump:
        return R_BUMP
    if not convex:
        return R_CONCAVE_TOP if y < CONCAVE_FRONT_Y else R_CONCAVE_FRONT
    if y < BACK_Y:
        return R_BACK
    if abs(x - xmax) < 1.0:
        return R_FRONT_OUTER
    return R_THUMB


def _fillet_poly(verts) -> Polygon:
    return LO.polygon(LO.segments(list(verts)))


@lru_cache
def case_vertices(side: str) -> tuple:
    """(x, y, r) of the case outer outline in drawing order (left half: mirrored + reversed)."""
    if side == "left":
        return tuple((L.MIRROR_X - x, y, r) for x, y, r in reversed(case_vertices("right")))
    pcb_pts = _collapse_chamfers([(x, y) for x, y, _ in LO.VERTICES])
    orient = math.copysign(1, _signed_area(pcb_pts))
    pts = _offset_pts(pcb_pts, CASE_OFFSET)
    xmax = max(x for x, _ in pcb_pts)
    pcb = L.outline("right").buffer(CAVITY_MIN_CLEAR)
    convex = [_convex(pts, i, orient) for i in range(len(pts))]
    radii = [_vertex_radius(pcb_pts[i], convex[i], xmax) for i in range(len(pts))]
    base = [0.0 if c else r for c, r in zip(convex, radii)]   # concave fillets only grow the cavity
    for i in range(len(pts)):
        while convex[i] and radii[i] > 0:   # convex fillets shrink the cavity corner: keep the PCB in
            trial = [(x, y, radii[i] if k == i else base[k]) for k, (x, y) in enumerate(pts)]
            if _fillet_poly(trial).buffer(-WALL).buffer(1e-6).contains(pcb):
                break
            radii[i] -= 0.5
    n = len(pts)
    for i in range(n):                   # neighbouring fillets must fit on their shared edge
        j = (i + 1) % n
        if _tangent_len(pts, i, radii[i]) + _tangent_len(pts, j, radii[j]) > math.dist(pts[i], pts[j]) - 0.1:
            sys.exit(f"case outline: fillets r{radii[i]} / r{radii[j]} do not fit the edge at {pts[i]}")
    return tuple((x, y, r) for (x, y), r in zip(pts, radii))


def _tangent_len(pts, i, r: float) -> float:
    """Corner -> tangent point distance of a radius-r fillet at vertex i."""
    a, b, c = pts[i - 1], pts[i], pts[(i + 1) % len(pts)]
    u = (a[0] - b[0], a[1] - b[1])
    v = (c[0] - b[0], c[1] - b[1])
    cosang = (u[0] * v[0] + u[1] * v[1]) / (math.hypot(*u) * math.hypot(*v))
    return r / math.tan(math.acos(max(-1.0, min(1.0, cosang))) / 2)


@lru_cache
def outline_poly(side: str) -> Polygon:
    """Case outer outline, KiCad frame (arcs as chords)."""
    return _fillet_poly(case_vertices(side))


@lru_cache
def outline_face(side: str) -> Face:
    """Case outer outline (CAD frame) with true arcs."""
    edges = []
    for s in LO.segments(list(case_vertices(side))):
        if s["type"] == "line":
            if math.dist(s["start"], s["end"]) > 1e-6:
                edges.append(Edge.make_line(P(*s["start"]), P(*s["end"])))
        else:
            edges.append(Edge.make_three_point_arc(P(*s["start"]), P(*s["mid"]), P(*s["end"])))
    return _up(Face(Wire(edges)))


def _up(face: Face) -> Face:
    """Face with its normal along +Z (extrusions go up)."""
    return face if face.normal_at().Z > 0 else -face


@lru_cache
def inner_face(side: str) -> Face:
    return offset(outline_face(side), -WALL, kind=Kind.ARC).faces()[0]


@lru_cache
def cavity_poly(side: str) -> Polygon:
    return outline_poly(side).buffer(-WALL)


# --------------------------------------------------------------------------
# 2D geometry
# --------------------------------------------------------------------------
def _filleted_polygon_face(coords, radius: float) -> Face:
    """Straight-edged polygon (CAD frame) -> Face with its real convex corners filleted (pocket
    tool radius). Corners turning less than FILLET_MIN_TURN (arc chords) are left alone."""
    face = _up(make_face(Polyline(*coords, close=True)).faces()[0])
    if radius <= 0:
        return face
    n = len(coords)
    area2 = sum(coords[i][0] * coords[(i + 1) % n][1] - coords[(i + 1) % n][0] * coords[i][1]
                for i in range(n))
    convex = []
    for i in range(n):
        a, b, c = coords[i - 1], coords[i], coords[(i + 1) % n]
        u, v = (b[0] - a[0], b[1] - a[1]), (c[0] - b[0], c[1] - b[1])
        cross = u[0] * v[1] - u[1] * v[0]
        turn = math.degrees(math.atan2(abs(cross), u[0] * v[0] + u[1] * v[1]))
        short = min(math.hypot(*u), math.hypot(*v))
        # the fillet takes radius * tan(turn / 2) of each edge; an edge shared with another fillet
        # has room for it if that is under half the edge (CASE-8: a clipped well corner was left sharp)
        if cross * area2 > 0 and turn > FILLET_MIN_TURN and (
                short > radius or radius * math.tan(math.radians(turn) / 2) < short / 2 - 1e-3):
            convex.append(b)
    if not convex:
        return face
    verts = [min(face.vertices(), key=lambda v: (v.X - p[0]) ** 2 + (v.Y - p[1]) ** 2) for p in convex]
    out = fillet(verts, radius)
    return _up(out if isinstance(out, Face) else out.faces()[0])


def sp_faces(geom, radius: float = 0.0, min_area: float = 0.05) -> list[Face]:
    """Shapely (Multi)Polygon in the KiCad frame -> CAD-frame build123d faces (holes kept)."""
    out = []
    for g in getattr(geom, "geoms", [geom]):
        if g.is_empty or g.area < min_area or g.geom_type != "Polygon":
            continue
        g = to_cad(g.simplify(0.01))
        f = _filleted_polygon_face(list(g.exterior.coords)[:-1], radius)
        for ring in g.interiors:
            f = _up((f - make_face(Polyline(*list(ring.coords)[:-1], close=True))).faces()[0])
        out.append(f)
    return out


@lru_cache
def well_poly(side: str, extra: float = 0.0):
    """Key well (KiCad frame): key cells + WELL_CLEAR, slivers closed, clipped to keep
    WELL_MIN_WALL of wall."""
    u = unary_union([L.cell(k, WELL_CLEAR) for k in L.keys(side)])
    # close slivers between staggered columns, keep sharp (mitred) corners
    u = u.buffer(1.5, join_style="mitre").buffer(-1.5, join_style="mitre")
    if extra:
        return u.buffer(extra, join_style="mitre")
    return u.intersection(outline_poly(side).buffer(-WELL_MIN_WALL)).simplify(0.05)


@lru_cache
def well_face(side: str, extra: float = 0.0) -> tuple[Face, ...]:
    return tuple(sp_faces(well_poly(side, extra), TOOL_R if not extra else 0.0))


def switch_cut(x, y, rot) -> Sketch:
    cx, cy = P(x, y)
    if DOGBONES:
        s = Rectangle(SWITCH_CUT, SWITCH_CUT)
        d = SWITCH_CUT / 2 - 0.5 * 0.7071
        for sx in (-1, 1):
            for sy in (-1, 1):
                s += Pos(sx * d, sy * d) * Circle(0.5)
    else:
        s = RectangleRounded(SWITCH_CUT, SWITCH_CUT, SWITCH_CUT_R)
    return Pos(cx, cy) * Rot(0, 0, cad_rot(rot)) * s


def stab_cuts(x, y, rot, housing) -> Sketch:
    """Cherry-spec plate-mount stab cut-outs of a vertical 2u key (stabs along v, wire across u).
    `housing` is layout.stab_dir: the cut-out's long half points there, at the PCB's Ø4.0 holes.
    The 0.875 side notch is widened to the 1 mm end mill; every outside corner is R0.5."""
    cx, cy = P(x, y)
    ux, uy = local_axes(rot)[0]
    su = 1.0 if housing[0] * ux + housing[1] * uy > 0 else -1.0      # housing towards +u or -u
    (u0, u1), w, r = STAB_CUT_U, STAB_CUT_W, SWITCH_CUT_R
    (n0, n1), nd = STAB_SIDE_NOTCH_U, STAB_SIDE_NOTCH_D
    bw, bd = STAB_END_NOTCH
    s = Sketch()
    for sv in (-1, 1):
        v = sv * STAB_OFFSET
        s += Pos(su * (u0 + u1) / 2, v) * RectangleRounded(u1 - u0, w, r)
        s += Pos(su * (n0 + n1) / 2, v + sv * w / 2) * RectangleRounded(n1 - n0, 2 * nd, r)
        s += Pos(su * (u1 + bd / 2 - nd / 2), v) * RectangleRounded(bd + nd, bw, r)
    return Pos(cx, cy) * Rot(0, 0, cad_rot(rot)) * s


def stab_wire_cuts(x, y, rot) -> Sketch:
    """Channels in the plate spacer for the stabiliser wire of a vertical 2u key: STAB_WIRE_U across
    the key on both sides of its centre, along the key between the two stabs (whose spacer cut-outs
    open the channel's ends)."""
    cx, cy = P(x, y)
    u0, u1 = STAB_WIRE_U
    s = Sketch()
    for su in (-1, 1):
        s += Pos(su * (u0 + u1) / 2, 0) * RectangleRounded(u1 - u0, 2 * STAB_OFFSET, TOOL_R)
    return Pos(cx, cy) * Rot(0, 0, cad_rot(rot)) * s


def stab_keys(side: str):
    """(x, y, w, h, rot, layout.stab_dir) of the 2u keys."""
    if not STABILIZERS:
        return []
    return [(k.x, k.y, k.w, k.h, k.rot, L.stab_dir(k, side)) for k in L.keys(side) if k.h == 2]


@lru_cache
def zones_poly(side: str, grow: float = 0.0):
    """Z_BACK and Z_TRRS (component zones from layout), optionally grown."""
    z = L.zones(side)
    u = unary_union([z["Z_BACK"], z["Z_TRRS"]])
    return u.buffer(grow) if grow else u


@lru_cache
def jack_relief_poly(side: str):
    """J2's body + J2_RELIEF_CLEAR (KiCad frame), corners rounded to the relief pocket's cutter radius
    (gate G2, deviations BOARD-13, CASE-8, CASE-9). Cut as is in the spacer and the plate DXF; the top
    cuts it as part of relief_poly, whose second opening pulls the corners 0.05 mm further in."""
    p = box(*JACK(side, "J2").body).buffer(J2_RELIEF_CLEAR, join_style="mitre")
    return p.buffer(-relief_r(), quad_segs=RELIEF_QUAD_SEGS).buffer(relief_r(), quad_segs=RELIEF_QUAD_SEGS)


@lru_cache
def pocket_poly(side: str, grow: float = 0.0) -> Polygon:
    p = _rect_poly(DISPLAY(side)["pocket"])
    return p.buffer(grow, join_style="mitre") if grow else p


def _area(geom) -> float:
    """Area of the polygonal part of a shapely intersection (shared edges count 0)."""
    return sum(g.area for g in getattr(geom, "geoms", [geom]) if g.geom_type == "Polygon")


@lru_cache
def bezel_rect(side: str) -> tuple[float, float, float, float]:
    """Raised display bezel (KiCad frame x0, y0, x1, y1, deviation CASE-1): the pocket + BEZEL_WALL,
    each edge pulled back to the key well where the well is nearer, so the bezel meets it flush: the
    C6R1 well in front (the pocket's front strip lies in it, WS3-5) and the C5 column at the side."""
    px0, py0, px1, py1 = DISPLAY(side)["pocket"]
    x0, y0, x1, y1 = px0 - BEZEL_WALL, py0 - BEZEL_WALL, px1 + BEZEL_WALL, py1 + BEZEL_WALL
    well = well_poly(side)

    def hit(*b):
        g = well.intersection(box(*b))
        return [p for p in getattr(g, "geoms", [g]) if p.geom_type == "Polygon" and p.area > 1e-6]

    front = hit(px0, py0, px1, y1)                      # in front, over the pocket's own width
    if front:
        y1 = min(p.bounds[1] for p in front)
    back = hit(px0, y0, px1, py0)
    if back:
        y0 = max(p.bounds[3] for p in back)
    right = hit(px1, y0, x1, y1 - 1e-3)
    if right:
        x1 = min(p.bounds[0] for p in right)
    left = hit(x0, y0, px0, y1 - 1e-3)
    if left:
        x0 = max(p.bounds[2] for p in left)
    return (x0, y0, x1, y1)


def bezel_face(side: str) -> Face:
    """Bezel outline (part frame): corners away from the key well rounded to BEZEL_R, the ones on the
    well left sharp (they meet the well wall)."""
    x0, y0, x1, y1 = bezel_rect(side)
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    face = _up(make_face(Polyline(*[P(*c) for c in corners], close=True)).faces()[0])
    free = [P(*c) for c in corners if well_poly(side).distance(Point(c)) > BEZEL_R + 0.5]
    if free:
        verts = [min(face.vertices(), key=lambda v: (v.X - c[0]) ** 2 + (v.Y - c[1]) ** 2) for c in free]
        out = fillet(verts, BEZEL_R)
        face = _up(out if isinstance(out, Face) else out.faces()[0])
    return face


def build_bezel(side: str) -> Solid:
    """The raised bezel, standing on the top face, top edges chamfered."""
    b = prism(bezel_face(side), Z_TOP, Z_BEZEL_TOP)
    return chamfer(b.edges().group_by(Axis.Z)[-1], BEZEL_CHAMFER)


def drill_point(d: float) -> float:
    """Length of a drill's conical point beyond its full-diameter depth."""
    return d / 2 / math.tan(math.radians(DRILL_POINT_DEG / 2))


def tap_hole(side: str, sx: float, sy: float) -> dict:
    """M2.5 tapped hole of the boss at (sx, sy): drill and thread depth from the boss face, the screw,
    its engagement and deepest reach, and the skin left between the drill point and the face above."""
    kind = "plate" if screw_under_plate(side, sx, sy) else "edge"
    drill, thread, screw = TAP_HOLE[kind]
    face = Z_PLATE_TOP if kind == "plate" else Z_TOP
    tip = Z_PCB_TOP + drill + drill_point(TAP_D)
    return dict(kind=kind, drill=drill, thread=thread, screw=screw, unthreaded=round(drill - thread, 3),
                engage=round(screw - Z_PCB_TOP, 3), reach=round(screw + SCREW_HEAD_SINK - Z_PCB_TOP, 3),
                tip=tip, face=face, skin=round(face - tip, 3))


def tap_cut(side: str, sx: float, sy: float) -> Solid:
    """Tap-drill hole as drilled: Ø TAP_D to the drill depth, then the 118 deg point."""
    h = tap_hole(side, sx, sy)
    cx, cy = P(sx, sy)
    hole = Pos(cx, cy, Z_PCB_TOP - 0.01) * Cylinder(TAP_D / 2, h["drill"] + 0.01,
                                                     align=(Align.CENTER, Align.CENTER, Align.MIN))
    return hole + Pos(cx, cy, 0) * Solid.make_cone(TAP_D / 2, 0, drill_point(TAP_D),
                                                   Plane.XY.offset(Z_PCB_TOP + h["drill"]))


def leg_thread(depth: float) -> float:
    """Min full M3 thread in a leg hole of this drill depth (JLCCNC: >= D/2 unthreaded)."""
    return math.floor((depth - LEG_UNTHREADED) * 10 + 1e-6) / 10


# --------------------------------------------------------------------------
# 3D parts
# --------------------------------------------------------------------------
def prism(face_or_sketch, z0: float, z1: float) -> Solid:
    return extrude(Plane.XY.offset(z0) * face_or_sketch, amount=z1 - z0)


def _housing_dist(kx, ky, rot, x, y) -> float:
    a = math.radians(rot)
    dx, dy = x - kx, y - ky
    lu = dx * math.cos(a) - dy * math.sin(a)
    lv = dx * math.sin(a) + dy * math.cos(a)
    return math.hypot(max(abs(lu) - HOUSING / 2, 0), max(abs(lv) - HOUSING / 2, 0))


def clearance_report(side: str) -> list:
    """(index, x, y, clearance to the nearest switch housing) per screw."""
    return [(i, sx, sy, min(_housing_dist(kx, ky, rot, sx, sy) for kx, ky, w, h, rot in KEYS(side)))
            for i, (sx, sy) in enumerate(SCREWS(side))]


def boss_radius(side: str, sx, sy) -> float:
    d = [w for i, x, y, w in clearance_report(side) if (x, y) == (sx, sy)][0]
    return max(min(BOSS_D / 2, d - 0.3), TAP_D / 2 + 1.0)


def boss_web(side: str, sx, sy, inner: Face, max_gap: float):
    """Web (part frame face) joining the boss at (sx, sy) to the nearest point of the wall
    when the gap between them is below max_gap, else None. As wide as the boss, 0.5 into
    the wall, clipped to the case outline and kept off the display pocket."""
    c = Vector(*P(sx, sy))
    r = boss_radius(side, sx, sy)
    wall = inner.outer_wire()
    d = wall.distance_to(Vertex(c.X, c.Y, 0))
    if d - r >= max_gap:
        return None
    n = 2000
    pts = [wall.position_at(i / n) for i in range(n)]
    w = min(pts, key=lambda v: (v - c).length)
    u = (w - c).normalized()
    length = (w - c).length + 0.5
    ang = math.degrees(math.atan2(u.Y, u.X))
    web = Pos(c.X, c.Y) * Rot(0, 0, ang) * Pos(length / 2, 0) * Rectangle(length, 2 * r)
    s = (Sketch() + web) & outline_face(side)
    for f in sp_faces(pocket_footprint(side).buffer(DISPLAY_BOSS_CLEAR, join_style="mitre")):
        s -= f
    return max(s.faces(), key=lambda f: f.area)


def corner_r(depth: float) -> float:
    """Smallest radius JLCCNC machines in a vertical internal corner this deep below the face its cutter
    enters by (JLCCNC_TOOLS, deviation CASE-8): R0.5 to 3 mm; to 10 mm R = depth / 10 + 0.5 (tool
    D = depth / 5) rounded up to 0.5 mm, i.e. R1.0 (Ø1 tool) to 5 mm and R1.5 (Ø2, the first row of the
    shop's table) to 10 mm; deeper, the Min R of the smallest tool in the table that reaches the depth
    (11.6 mm: Ø3, R2)."""
    if depth <= JLCCNC_SMALL_DEPTH + 1e-9:
        return 0.5
    if depth <= JLCCNC_TOOLS[0][1] + 1e-9:
        return math.ceil((depth / 10 + 0.5) / 0.5 - 1e-9) * 0.5
    for _d, reach, r in JLCCNC_TOOLS:
        if reach + 1e-9 >= depth:
            return r
    sys.exit(f"corner_r: no tool in JLCCNC's table reaches {depth} mm")


def relief_r() -> float:
    """Corner radius of the relief pockets above the plate level (J2's included): cut from the parting
    face up to Z_POCKET_CEIL, 7.6 deep -> R1.5."""
    return corner_r(Z_POCKET_CEIL - Z_SPLIT)


def wall_fillets(inner: Face, feature, r: float) -> list[Face]:
    """Material that rounds the internal corners where a feature (2D footprint, part frame)
    meets the wall to radius r: the cavity minus its opening by r, kept next to the feature."""
    cavity = (Sketch() + inner) & offset(feature, 4 * r, kind=Kind.ARC)
    cavity -= feature
    opened = Sketch()
    for f in cavity.faces():
        core = None
        for kind in (Kind.ARC, Kind.INTERSECTION):
            try:
                core = offset(f, -r, kind=kind).faces()
                break
            except RuntimeError:
                pass
        if core is None:
            if f.area > 4 * r * r:
                sys.exit(f"wall_fillets: 2D offset failed on a {f.area:.1f} mm2 cavity face")
            continue             # a sliver narrower than 2r: fill it all
        for g in core:
            opened += offset(g, r, kind=Kind.ARC)
    fill = cavity - opened
    fill &= offset(feature, 2 * r, kind=Kind.ARC)
    return [f for f in fill.faces() if f.area > 1e-4]


@lru_cache
def boss_webs(side: str, part: str) -> dict:
    """{(sx, sy): web face} for every screw boss that needs a web (part 'top' or 'bottom')."""
    gap = WEB_GAP_TOP if part == "top" else WEB_GAP_BOTTOM
    inner = inner_face(side)
    out = {}
    for sx, sy in SCREWS(side):
        f = boss_web(side, sx, sy, inner, gap)
        if f is not None:
            out[(sx, sy)] = f
    return out


def screw_under_plate(side: str, sx, sy) -> bool:
    return well_poly(side).contains(Point(sx, sy))


@lru_cache
def _leg_wall_points(side: str) -> tuple:
    """(name, KiCad point on the outer wall face, KiCad outward normal), right frame mirrored."""
    if side == "left":
        return tuple((n, (L.MIRROR_X - p[0], p[1]), (-q[0], q[1])) for n, p, q in _leg_wall_points("right"))
    v = LO.VERTICES
    orient = math.copysign(1, _signed_area([(x, y) for x, y, _ in v]))
    out = []
    for name, (i, j), anchor, d in LEGS:
        a, b = v[i][:2], v[j][:2]
        e = (b[0] - a[0], b[1] - a[1])
        ln = math.hypot(*e)
        nrm = (orient * e[1] / ln, -orient * e[0] / ln)
        p = _line_x((a[0] + nrm[0] * CASE_OFFSET, a[1] + nrm[1] * CASE_OFFSET), e, anchor, d)
        out.append((name, p, nrm))
    return tuple(out)


def leg_mounts(side: str):
    """(cad point on outer surface, outward unit normal) for 3 legs."""
    return [(P(*p), (n[0], -n[1])) for _, p, n in _leg_wall_points(side)]


def leg_names(side: str) -> list[str]:
    return [name for name, _, _ in _leg_wall_points(side)]


def _leg_frame(px, py, nx, ny, shape):
    """Place a shape built in the wall-local frame (X = inward depth from the outer
    face, Y = along the wall, Z = absolute) at a wall position."""
    return Pos(px, py, 0) * Rot(0, 0, math.degrees(math.atan2(-ny, -nx))) * shape


def _in_housing(side: str, x: float, y: float, margin: float, display_margin: float | None = None) -> bool:
    """KiCad-frame point inside any switch housing (15.6 mm incl. clips) or the display pocket?"""
    for kx, ky, w, h, rot in KEYS(side):
        a = math.radians(rot)
        dx, dy = x - kx, y - ky
        lu = dx * math.cos(a) - dy * math.sin(a)
        lv = dx * math.sin(a) + dy * math.cos(a)
        if abs(lu) < HOUSING / 2 + margin and abs(lv) < HOUSING / 2 + margin:
            return True
    x0, y0, x1, y1 = DISPLAY(side)["pocket"]
    m = margin if display_margin is None else display_margin
    return x0 - m < x < x1 + m and y0 - m < y < y1 + m


def leg_pad_depth(side: str, px, py, nx, ny) -> float:
    """Inward pad depth behind the wall that stays clear of switch housings and the display."""
    names = dict(zip([tuple(round(c, 6) for c in m[0]) for m in leg_mounts(side)], leg_names(side)))
    limit = LEG_PAD_MAX.get(names.get((round(px, 6), round(py, 6)), ""), LEG_PAD[1])
    tx, ty = -ny, nx
    depth = 0.0
    while depth < limit:
        d = WALL + depth + 0.25
        hit = False
        for t in (-LEG_PAD[0] / 2, 0.0, LEG_PAD[0] / 2):
            cx, cy = px - nx * d + tx * t, py - ny * d + ty * t
            if _in_housing(side, *K(cx, cy), 0.5, DISPLAY_LEG_CLEAR):
                hit = True
        if hit:
            break
        depth += 0.25
    return depth


def leg_hole_depth(side: str, px, py, nx, ny) -> float:
    """Tap drill depth from the boss face: inside the pad, and stopped short of the key
    well when the thread would pass just under the well floor."""
    depth = LEG_BOSS_H + WALL + leg_pad_depth(side, px, py, nx, ny) - 0.5
    if LEG_Z + 1.5 > Z_PLATE_TOP - 0.5:
        well = well_poly(side)
        d = 0.0
        while d < depth and not well.contains(Point(*K(px - nx * d, py - ny * d))):
            d += 0.1
        depth = min(depth, LEG_BOSS_H + d - 0.3)
    return min(LEG_DEPTH, depth)


def tooth_k() -> float:
    """Tooth height / radius of the radial V teeth (sharp V, full pitch)."""
    return math.tan(math.pi / LEG_TEETH) / math.tan(math.radians(LEG_TOOTH_ANGLE) / 2)


def detent_grooves(r_out: float, z_tip: float) -> list:
    """LEG_TEETH V-groove solids, axis +Z, tip plane at z_tip (boss teeth when cut, hub teeth
    when added: the hub is the exact negative of the boss)."""
    half, k = math.pi / LEG_TEETH, tooth_k()
    grooves = []
    for i in range(LEG_TEETH):
        secs = []
        for r in (LEG_TOOTH_R0, r_out):
            w = r * math.tan(half)
            pts = [(r, -w, z_tip + 0.01), (r, w, z_tip + 0.01), (r, 0, z_tip - r * k)]
            secs.append(make_face(Polyline(*pts, close=True)))
        grooves.append(Rot(0, 0, i * 360 / LEG_TEETH) * loft(secs))
    return grooves


def boss_root_fillet() -> Solid:
    """Concave fillet ring where the leg boss meets the wall (boss frame, wall face at Z = 0)."""
    r1, rf = LEG_BOSS_D / 2, LEG_BOSS_ROOT_R
    ring = Pos(0, 0, -1) * Cylinder(r1 + rf, rf + 1, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return ring - Pos(0, 0, rf) * Torus(r1 + rf, rf)


def detent_boss() -> Solid:
    """Leg boss in a local frame: axis along +Z, wall face at Z = 0, bearing face at LEG_BOSS_H."""
    r1 = LEG_BOSS_D / 2
    boss = Pos(0, 0, -WALL / 2) * Cylinder(r1, WALL / 2 + LEG_BOSS_H,
                                          align=(Align.CENTER, Align.CENTER, Align.MIN))
    if not DETENT_TEETH:
        return fillet(boss.edges().group_by(Axis.Z)[-1], LEG_BOSS_EDGE)
    boss -= detent_grooves(r1 + 0.3, LEG_BOSS_H)
    root = LEG_TOOTH_R0 * tooth_k()
    boss -= Pos(0, 0, LEG_BOSS_H - root) * Cylinder(LEG_TOOTH_R0, 1,
                                                    align=(Align.CENTER, Align.CENTER, Align.MIN))
    return boss


@lru_cache
def relief_poly(side: str):
    """Relief pocket (KiCad frame) above the plate level: inside the wall, WALL / 2 + 0.5 from the
    key well, opened to RELIEF_MIN_W; plus all of Z_BACK and Z_TRRS (spec §10.6-7), which keep
    RELIEF_WELL_SKIN of well wall; plus J2's body, which runs past Z_TRRS through that skin and under the
    plate (jack_relief_poly). The union is opened last by the cutter radius (relief_r), so every corner
    the clipping leaves, against the wall or between the pieces, is one the cutter can make (CASE-8)."""
    cav = cavity_poly(side)
    r = RELIEF_MIN_W / 2
    main = cav.difference(well_poly(side, WALL / 2 + 0.5)).buffer(-r, quad_segs=RELIEF_QUAD_SEGS).buffer(
        r, quad_segs=RELIEF_QUAD_SEGS)
    zone = zones_poly(side).difference(well_poly(side).buffer(RELIEF_WELL_SKIN, join_style="mitre"))
    zone = zone.union(jack_relief_poly(side)).intersection(cav)
    rr = relief_r()
    q = RELIEF_QUAD_SEGS
    keep = relief_islands(side).buffer(RELIEF_ISLAND_CLEAR, quad_segs=q)
    out = unary_union([main, zone]).intersection(cav.buffer(-0.01)).difference(keep)
    return out.buffer(-rr, quad_segs=q).buffer(rr, quad_segs=q)


def _face_poly(face) -> Polygon:
    """Part-frame build123d face -> KiCad-frame shapely polygon (its outer wire, 8 points per edge)."""
    pts = [K(q.X, q.Y) for e in face.outer_wire().edges() for q in (e.position_at(t / 8) for t in range(8))]
    return Polygon(pts).buffer(0)


@lru_cache
def relief_islands(side: str):
    """What the top part adds in the relief band (Z_PLATE_BOT-Z_POCKET_CEIL) after the relief cut, as
    the KiCad-frame plan: the bosses that rise to Z_POCKET_CEIL with their webs and wall fillets, and the
    tent-leg pads with theirs (build_top). The relief keeps RELIEF_ISLAND_CLEAR off them, so none of them
    meets its edge at a sharp angle (CASE-8)."""
    inner = inner_face(side)
    rf = corner_r(Z_POCKET_CEIL - Z_SPLIT)
    webs = boss_webs(side, "top")
    polys = []
    for sx, sy in SCREWS(side):
        if screw_under_plate(side, sx, sy):
            continue
        polys.append(Point(sx, sy).buffer(boss_radius(side, sx, sy), quad_segs=32))
        if (sx, sy) in webs:
            polys += [_face_poly(f) for f in [webs[(sx, sy)], *wall_fillets(inner, webs[(sx, sy)], rf)]]
    for (px, py), (nx, ny) in leg_mounts(side):
        pad_d = leg_pad_depth(side, px, py, nx, ny)
        foot = _leg_frame(px, py, nx, ny, Pos((WALL + pad_d) / 2, 0) * Rectangle(WALL + pad_d, LEG_PAD[0]))
        polys += [_face_poly(f) for f in [*foot.faces(), *wall_fillets(inner, foot, rf)]]
    return unary_union(polys)


def relief_faces(side: str) -> list[Face]:
    return sp_faces(relief_poly(side), min_area=4 * relief_r() ** 2)


def spacer_face(side: str) -> Sketch:
    """Spacer outline (part frame): the plate island inside the wall, minus an opening per switch
    and stabiliser, the stabiliser wire channels, the PCB screw bosses, the tent-leg pads, the component zones and the display
    pocket, each with SPACER_CLEAR."""
    inner = offset(outline_face(side), -WALL - SPACER_CLEAR, kind=Kind.ARC).faces()[0]
    s = Sketch() + list(well_face(side, extra=WALL / 2 + 0.5))
    s &= inner
    for kx, ky, w, h, rot in KEYS(side):
        s -= Pos(*P(kx, ky)) * Rot(0, 0, cad_rot(rot)) * RectangleRounded(SPACER_HOLE, SPACER_HOLE, TOOL_R)
    for kx, ky, w, h, rot, sd in stab_keys(side):
        s -= offset(stab_cuts(kx, ky, rot, sd), SPACER_CLEAR, kind=Kind.ARC)
        s -= stab_wire_cuts(kx, ky, rot)
    for sx, sy in SCREWS(side):
        s -= Pos(*P(sx, sy)) * Circle(boss_radius(side, sx, sy) + SPACER_CLEAR)
    for web in boss_webs(side, "top").values():
        s -= offset(web, SPACER_CLEAR, kind=Kind.ARC)
    for (px, py), (nx, ny) in leg_mounts(side):
        d = WALL + leg_pad_depth(side, px, py, nx, ny) + SPACER_CLEAR
        s -= _leg_frame(px, py, nx, ny, Pos(d / 2, 0) * Rectangle(d, LEG_PAD[0] + 2 * SPACER_CLEAR))
    for f in sp_faces(unary_union([zones_poly(side, SPACER_CLEAR), pocket_poly(side, SPACER_CLEAR),
                                   jack_relief_poly(side)])):
        s -= f
    # keep the main lattice; crumbs cut off by the zones are dropped
    s = Sketch() + [f for f in s.faces() if f.area > 20.0]
    # open it by SPACER_MIN_WEB: slivers narrower than that are dropped, so the printed part has no
    # wall below JLC3DP's MJF minimum (deviation CASE-5); this only removes material
    s = offset(offset(s, -SPACER_MIN_WEB / 2, kind=Kind.ARC), SPACER_MIN_WEB / 2, kind=Kind.ARC)
    return Sketch() + [f for f in s.faces() if f.area > 20.0]


def build_spacer(side: str) -> Solid:
    return prism(spacer_face(side), Z_PLATE_BOT - SPACER_T, Z_PLATE_BOT)


def spacer_check(side: str, spacer: Solid):
    """The spacer must clear the PCB and keep every switch opening and stabiliser wire channel free."""
    gap = Z_PLATE_BOT - SPACER_T - Z_PCB_TOP
    if gap < 0:
        sys.exit(f"plate spacer is {-gap:.2f} mm too thick for the plate-to-PCB gap")
    zmid = Z_PLATE_BOT - SPACER_T / 2
    for kx, ky, w, h, rot in KEYS(side):
        a = math.radians(cad_rot(rot))
        cx, cy = P(kx, ky)
        r = SPACER_HOLE / 2 - 0.05
        c = r - TOOL_R * (1 - 1 / math.sqrt(2)) - 0.05   # inside the rounded corners
        for u, v in ((-c, -c), (-c, c), (c, -c), (c, c), (0, -r), (0, r), (-r, 0), (r, 0)):
            q = Vector(cx + u * math.cos(a) - v * math.sin(a), cy + u * math.sin(a) + v * math.cos(a), zmid)
            if spacer.is_inside(q):
                sys.exit(f"{side} plate spacer covers the switch at ({kx:.1f},{ky:.1f})")
    for kx, ky, w, h, rot, sd in stab_keys(side):
        for f in stab_cuts(kx, ky, rot, sd).faces():
            c = f.center()
            if spacer.is_inside(Vector(c.X, c.Y, zmid)):
                sys.exit(f"{side} plate spacer covers a stabiliser at ({kx:.1f},{ky:.1f})")
        a = math.radians(cad_rot(rot))
        cx, cy = P(kx, ky)
        for su in (-1, 1):                    # the wire channel is open along its whole length
            for u in (su * STAB_WIRE_U[0] + su * 0.3, su * sum(STAB_WIRE_U) / 2, su * STAB_WIRE_U[1] - su * 0.3):
                for i in range(-10, 11):
                    v = i / 10 * (STAB_OFFSET - 0.5)
                    q = Vector(cx + u * math.cos(a) - v * math.sin(a), cy + u * math.sin(a) + v * math.cos(a), zmid)
                    if spacer.is_inside(q):
                        sys.exit(f"{side} plate spacer blocks the stabiliser wire channel of ({kx:.1f},{ky:.1f}) "
                                 f"at u {u:.1f}, v {v:.1f}")
    sec = spacer_face(side)
    for name, geom in (("component zones", zones_poly(side)), ("display pocket", pocket_poly(side)),
                       ("J2 body", box(*JACK(side, "J2").body))):
        for f in sp_faces(geom):
            if (Sketch() + f & sec).area > 1e-3:
                sys.exit(f"{side} plate spacer overlaps the {name}")
    jd = {ref: spacer.distance_to(jack_body(side, ref)) for ref in ("J1", "J2")}
    for ref, d in jd.items():
        if d < JACK_MIN_CLEAR:
            sys.exit(f"{side} plate spacer is {d:.3f} mm from the {ref} body (JACK_MIN_CLEAR {JACK_MIN_CLEAR})")
    print(f"  {side:5s} plate spacer: {SPACER_T} thick, Z {Z_PLATE_BOT - SPACER_T:.1f}-{Z_PLATE_BOT:.1f}, "
          f"{gap:.1f} mm above the PCB, {SPACER_HOLE} openings, {len(spacer.solids())} piece(s); "
          + ", ".join(f"{ref} body {d:.3f} mm clear" for ref, d in jd.items()))


def web_check(side: str):
    """Boss webs must stay clear of the switch housings, the display and the zoned parts."""
    parts = [box(*L.part_rect(side, ref)).buffer(0.5) for ref in ("J1", "J2", "J3", "U1", "U2", *PIN_HOLES)]
    for part in ("top", "bottom"):
        for (sx, sy), web in boss_webs(side, part).items():
            bb = web.bounding_box()
            n = 30
            for i in range(n + 1):
                for j in range(n + 1):
                    q = Vector(bb.min.X + (bb.max.X - bb.min.X) * i / n, bb.min.Y + (bb.max.Y - bb.min.Y) * j / n)
                    if not web.is_inside(q):
                        continue
                    kx, ky = K(q.X, q.Y)
                    if _in_housing(side, kx, ky, 0.3):
                        sys.exit(f"{side} {part} web at screw ({sx:.1f},{sy:.1f}) hits a switch housing or the display")
                    if part == "top" and any(p.contains(Point(kx, ky)) for p in parts):
                        sys.exit(f"{side} top web at screw ({sx:.1f},{sy:.1f}) hits a zoned part")
            print(f"  {side:5s} {part:6s} web: screw ({sx:6.1f},{sy:6.1f}) joined to the wall, {web.area:.0f} mm2")


def tap_check(side: str, top: Solid | None = None):
    """Every M2.5 hole follows the JLCCNC threaded-hole guideline, its screw seats before it reaches
    the end of the full thread, and the drill point leaves skin under the face above (CASE-3). On the
    built part, the hole is open to its drill depth and solid from the drill point to the face."""
    for i, (sx, sy) in enumerate(SCREWS(side)):
        h = tap_hole(side, sx, sy)
        name = f"{side} T{i + 1} ({sx:.1f},{sy:.1f})"
        if h["unthreaded"] < TAP_UNTHREADED_MIN - 1e-9:
            sys.exit(f"{name}: {h['unthreaded']} mm unthreaded at the bottom, JLCCNC needs {TAP_UNTHREADED_MIN}")
        if h["thread"] > TAP_THREAD_MAX + 1e-9:
            sys.exit(f"{name}: {h['thread']} mm of thread is more than 3 D")
        if h["reach"] > h["thread"] - SCREW_TIP_CLEAR + 1e-9:
            sys.exit(f"{name}: an M2.5x{h['screw']} reaches {h['reach']:.2f} mm, past the {h['thread']} mm "
                     f"thread less {SCREW_TIP_CLEAR}: it would bottom before its head seats")
        if h["engage"] < SCREW_MIN_ENGAGE - 1e-9:
            sys.exit(f"{name}: an M2.5x{h['screw']} engages only {h['engage']:.2f} mm of thread")
        if h["skin"] < TAP_SKIN_MIN - 1e-9:
            sys.exit(f"{name}: the drill point leaves {h['skin']:.2f} mm under Z {h['face']}")
        if top is not None:
            cx, cy = P(sx, sy)
            for z in (Z_PCB_TOP + 0.2, Z_PCB_TOP + h["drill"] - 0.1):
                if top.is_inside(Vector(cx, cy, z)):
                    sys.exit(f"{name}: the tap drill is not open at Z {z:.2f}")
            for z in (h["tip"] + 0.05, (h["tip"] + h["face"]) / 2, h["face"] - 0.05):
                if not top.is_inside(Vector(cx, cy, z)):
                    sys.exit(f"{name}: no material above the drill point at Z {z:.2f}")
        print(f"  {side:5s} T{i + 1} ({sx:6.1f},{sy:6.1f}) {h['kind']:5s}: drill {h['drill']} + point, thread "
              f"{h['thread']} ({h['unthreaded']} unthreaded), M2.5x{h['screw']} engages {h['engage']:.1f} "
              f"(reach <= {h['reach']:.1f}), skin {h['skin']:.2f} to Z {h['face']}"
              + ("; probed" if top is not None else ""))


def leg_check(side: str):
    """Each boss and pad must sit on a straight wall, inside the top part."""
    if LEG_Z - LEG_BOSS_D / 2 < Z_SPLIT - 1e-6 or LEG_Z + LEG_BOSS_D / 2 > Z_TOP:
        sys.exit("tent-leg boss does not fit between the parting plane and the top")
    outline = outline_face(side)
    half = max(LEG_PAD[0], LEG_BOSS_D) / 2 + 0.5
    for name, ((px, py), (nx, ny)) in zip(leg_names(side), leg_mounts(side)):
        tx, ty = -ny, nx
        for t in (-half, half):
            qx, qy = px + tx * t, py + ty * t
            on_wall = (outline.is_inside(Vector(qx - nx * 0.05, qy - ny * 0.05)) and
                       not outline.is_inside(Vector(qx + nx * 0.05, qy + ny * 0.05)))
            if not on_wall:
                sys.exit(f"{side} {name} tent leg at {K(px, py)} runs off its straight wall")
        pad = leg_pad_depth(side, px, py, nx, ny)
        depth = leg_hole_depth(side, px, py, nx, ny)
        if depth < LEG_MIN_DRILL:
            sys.exit(f"{side} {name} tent-leg thread is shorter than {LEG_MIN_DRILL} mm")
        if leg_thread(depth) < LEG_MIN_THREAD:
            sys.exit(f"{side} {name} tent-leg full thread {leg_thread(depth)} is below {LEG_MIN_THREAD} mm")
        pad_poly = Polygon([K(px - nx * d + tx * t, py - ny * d + ty * t)
                            for d, t in ((0, -LEG_PAD[0] / 2), (0, LEG_PAD[0] / 2),
                                         (WALL + pad, LEG_PAD[0] / 2), (WALL + pad, -LEG_PAD[0] / 2))])
        dclear = pad_poly.distance(pocket_footprint(side))
        kx, ky = K(px, py)
        print(f"  {side:5s} {name:5s} tent leg at ({kx:6.1f},{ky:6.1f}): pad depth {pad:4.2f}  "
              f"M3 drill depth {depth:4.2f} mm from boss face, full thread {leg_thread(depth):.1f}, "
              f"screw reach <= {leg_thread(depth) - LEG_REACH_CLEAR:.1f}, {dclear:.2f} mm to the display pocket")
        if dclear < DISPLAY_LEG_CLEAR - 1e-6:
            sys.exit(f"{side} {name} tent-leg pad is {dclear:.2f} mm from the display pocket")


def pcb_check(side: str):
    """The cavity holds the PCB with CAVITY_MIN_CLEAR, and the well keeps WELL_MIN_WALL."""
    pcb = L.outline(side)
    cav = cavity_poly(side)
    clear = cav.exterior.distance(pcb) if cav.contains(pcb) else -1.0
    if clear < CAVITY_MIN_CLEAR - 0.02:
        sys.exit(f"{side} cavity clears the PCB by only {clear:.2f} mm")
    wall = outline_poly(side).exterior.distance(well_poly(side))
    caps = unary_union([L.cell(k, -KEYCAP_INSET) for k in L.keys(side)])
    outside = caps.difference(well_poly(side)).area
    if outside > 1e-3:
        sys.exit(f"{side} keycaps reach past the clipped key well ({outside:.3f} mm2)")
    radii = sorted({r for _, _, r in case_vertices(side)})
    print(f"  {side:5s} outline: {len(case_vertices(side))} corners, radii {radii}; cavity to PCB "
          f"{clear:.2f} mm min; key well to outer face {wall:.2f} mm min")


def display_check(side: str, top: Solid | None = None):
    """The window and module lie inside the pocket, the pocket ceiling clears the J3 + nice!view stack
    under BEZEL_SKIN of bezel, the bezel covers the pocket up to the key well without running over it
    or the top-edge fillet, and (on the built part) the window and pocket are open up to the ceiling
    with bezel skin around the window (CASE-1)."""
    d = DISPLAY(side)
    pocket, window, module = _rect_poly(d["pocket"]), _rect_poly(d["window"]), _rect_poly(d["module"])
    bezel, well = _rect_poly(bezel_rect(side)), well_poly(side)
    if not pocket.buffer(1e-6).contains(window):
        sys.exit(f"{side} display window is not inside the pocket")
    if not pocket.buffer(1e-6).contains(module):
        sys.exit(f"{side} display module is not inside the pocket")
    if Z_DISPLAY_TOP - Z_PCB_TOP < DISPLAY_STACK_MAX + DISPLAY_GLASS_CLEAR - 1e-9:
        sys.exit(f"{side} display pocket ceiling is below the J3 + nice!view stack")
    if Z_BEZEL_TOP - Z_DISPLAY_TOP < BEZEL_SKIN - 1e-9 or Z_BEZEL_TOP < Z_TOP:
        sys.exit(f"{side} display bezel leaves less than {BEZEL_SKIN} mm of skin")
    if _area(pocket.difference(bezel).difference(well)) > 1e-3:
        sys.exit(f"{side} display pocket runs out from under the bezel")
    if not bezel.buffer(-1.0).contains(window):
        sys.exit(f"{side} display window is less than 1.0 mm from the bezel edge")
    if _area(bezel.intersection(well)) > 1e-3:
        sys.exit(f"{side} display bezel runs over the key well")
    if not outline_poly(side).buffer(-(TOP_EDGE_FILLET + 1.0)).contains(bezel):
        sys.exit(f"{side} display bezel runs onto the top-edge fillet")
    wclear = window.exterior.distance(Polygon(well.exterior)) if not window.intersects(well) else -1
    if wclear < 0.5:
        sys.exit(f"{side} display window is only {wclear:.2f} mm from the key well")
    footprint = pocket_footprint(side)
    for sx, sy in SCREWS(side):
        if footprint.distance(Point(sx, sy)) < boss_radius(side, sx, sy) + DISPLAY_BOSS_CLEAR:
            sys.exit(f"{side} display pocket hits the boss at ({sx:.1f},{sy:.1f})")
    # corners (CASE-8): the cutter's radius is JLCCNC's for the pocket depth; the header-end corners are
    # relieved and the far ones lie in the key well (open above the plate); the reliefs leave JLCCNC's
    # minimum wall to the key well and, above the top face, to the outside of the bezel
    r = pocket_corner_r()
    if r < corner_r(Z_DISPLAY_TOP - Z_SPLIT) - 1e-9:
        sys.exit(f"{side} display pocket corner R{r} is below JLCCNC's minimum for its depth")
    corners = pocket_corners(side)
    if [c[1] for c in corners if c[4]] != [d["pocket"][3]] * 2:
        sys.exit(f"{side} display pocket: only its two far-end corners may lie in the key well")
    walls = []
    for cx, cy in pocket_reliefs(side):
        disc = Point(cx, cy).buffer(r, quad_segs=64)
        walls += [well.distance(disc), bezel.exterior.distance(disc) if bezel.contains(disc) else -1.0]
    if min(walls) < JLCCNC_WALL_MIN - 1e-6:
        sys.exit(f"{side} display pocket relief leaves a {min(walls):.2f} mm wall "
                 f"(JLCCNC: {JLCCNC_WALL_MIN})")
    for cx, cy, sx, sy, in_well in corners:
        if in_well and not well.contains(Point(cx, cy).buffer(TOOL_R)):
            sys.exit(f"{side} display pocket corner ({cx:.2f},{cy:.2f}) is within the well's corner radius "
                     "of the well edge: it would be an internal corner above the plate")
    if top is not None:
        (wx, wy), (px0, py0, px1, _) = d["window_centre"], d["pocket"]
        x0, y0, x1, y1 = d["window"]
        bx0, by0, bx1, _ = bezel_rect(side)
        probes_open = [(wx, wy, Z_BEZEL_TOP - 0.2), (wx, wy, Z_DISPLAY_TOP - 0.2),
                       ((px0 + px1) / 2, py0 + 1.0, Z_PCB_TOP + 0.5),
                       (px0 + 0.3, py0 + 0.3, Z_DISPLAY_TOP - 0.05), (px1 - 0.3, wy, Z_DISPLAY_TOP - 0.05),
                       (px0 + 0.03, py0 + 0.03, Z_DISPLAY_TOP - 0.5), (px1 - 0.03, py0 + 0.03, Z_DISPLAY_TOP - 0.5),
                       (bx0 - 0.3, wy, Z_TOP + 0.3)]
        probes_solid = [(wx, y0 - 0.8, Z_BEZEL_TOP - 0.3), (x0 - 0.8, wy, Z_BEZEL_TOP - 0.3),
                        (px0 + 0.3, py0 + 0.3, Z_DISPLAY_TOP + 0.1), (bx0 + 0.3, wy, Z_BEZEL_TOP - 0.6),
                        ((bx0 + bx1) / 2, by0 + 0.3, Z_BEZEL_TOP - 0.6)]
        a = r / math.sqrt(2)
        for cx, cy, sx, sy, in_well in corners:
            if in_well:     # open over the plate, the cutter's fillet in the plate
                probes_open.append((cx + sx * 0.05, cy + sy * 0.05, Z_PLATE_TOP + 0.3))
                probes_solid.append((cx + sx * 0.05, cy + sy * 0.05, Z_PLATE_TOP - 0.5))
            else:           # the relief runs into both walls, from the PCB up to the ceiling
                for z in (Z_PLATE_BOT + 0.3, Z_PLATE_TOP + 0.5, Z_DISPLAY_TOP - 0.3):
                    probes_open += [(cx - sx * (r - a - 0.1), cy + sy * a, z),
                                    (cx + sx * a, cy - sy * (r - a - 0.1), z)]
                probes_solid.append((cx - sx * (r - a + 0.1), cy + sy * a, Z_DISPLAY_TOP - 0.3))
        for x, y, z in probes_open:
            if top.is_inside(Vector(*P(x, y), z)):
                sys.exit(f"{side} display window / pocket is not open at ({x:.2f},{y:.2f},{z:.2f})")
        for x, y, z in probes_solid:
            if not top.is_inside(Vector(*P(x, y), z)):
                sys.exit(f"{side} no bezel skin or wall at ({x:.2f},{y:.2f},{z:.2f})")
    b = bezel_rect(side)
    print(f"  {side:5s} display: pocket x {d['pocket'][0]:.2f}-{d['pocket'][2]:.2f} y {d['pocket'][1]:.3f}-"
          f"{d['pocket'][3]:.3f} Z {Z_PCB_TOP}-{Z_DISPLAY_TOP} (glass <= {Z_PCB_TOP + DISPLAY_STACK_MAX:.2f}); "
          f"bezel x {b[0]:.3f}-{b[2]:.3f} y {b[1]:.3f}-{b[3]:.3f} Z {Z_TOP}-{Z_BEZEL_TOP}; window "
          f"{d['window'][2] - d['window'][0]:.0f}x{d['window'][3] - d['window'][1]:.0f} at {d['window_centre']}, "
          f"{wclear:.2f} mm from the well; corners R{r} ({len(pocket_reliefs(side))} dog-bones, thinnest "
          f"wall {min(walls):.2f}; {sum(c[4] for c in corners)} in the key well)"
          + ("; probed open" if top is not None else ""))


def usb_notch(side: str) -> dict:
    """USB-C notch: centre (KiCad x, y on the outer face, Z), outward normal (KiCad)."""
    j = JACK(side, "J1")
    return dict(x=j.x + j.facing[0] * CASE_OFFSET, y=j.y + j.facing[1] * CASE_OFFSET,
                z=Z_PCB_TOP + j.axis_z, n=j.facing)


def trrs_notch(side: str) -> dict:
    j = JACK(side, "J2")
    return dict(x=j.x + j.facing[0] * CASE_OFFSET, y=j.y + j.facing[1] * CASE_OFFSET,
                z=Z_PCB_TOP + j.axis_z, n=j.facing)


def _wall_place(notch: dict, shape):
    px, py = P(notch["x"], notch["y"])
    return _leg_frame(px, py, notch["n"][0], -notch["n"][1], shape)


def usb_cuts(side: str) -> list[Solid]:
    """Notch through the back wall + outside recess for the plug overmould (wall-local frame)."""
    n = usb_notch(side)
    w, h = USB_NOTCH
    notch = Pos(-1, 0, n["z"]) * Box(WALL + 2, w, h, align=(Align.MIN, Align.CENTER, Align.CENTER))
    notch = fillet(notch.edges().filter_by(Axis.X), USB_NOTCH_R)
    rw, rh = USB_RECESS
    recess = Pos(-1, 0, n["z"]) * Box(USB_RECESS_DEPTH + 1, rw, rh, align=(Align.MIN, Align.CENTER, Align.CENTER))
    recess = fillet(recess.edges().filter_by(Axis.X), USB_RECESS_R)
    return [_wall_place(n, notch), _wall_place(n, recess)]


def trrs_cut(side: str) -> Solid:
    """Round hole through the inner bump wall (side_notch of spec §10.6)."""
    n = trrs_notch(side)
    hole = Pos(-1, 0, n["z"]) * Rot(0, 90, 0) * Cylinder(TRRS_NOTCH_D / 2, WALL + 2,
                                                         align=(Align.CENTER, Align.CENTER, Align.MIN))
    return _wall_place(n, hole)


def jack_body(side: str, ref: str) -> Solid:
    """The layout envelope of a jack's body (case frame), standing on the PCB top."""
    j = JACK(side, ref)
    x0, y0, x1, y1 = j.body
    return Pos(*P((x0 + x1) / 2, (y0 + y1) / 2), Z_PCB_TOP) * Box(
        x1 - x0, y1 - y0, j.height, align=(Align.CENTER, Align.CENTER, Align.MIN))


def jack_clearances(side: str, ref: str) -> dict[str, float]:
    """Plan clearance of a jack body (layout envelope) to each outline that cuts round it: the top's
    relief pocket (relief_poly, which also follows the cavity wall at the jack mouth) and, for J2, its
    own relief (jack_relief_poly: the spacer cut-out) and the plate DXF's notch (CASE-9)."""
    body = box(*JACK(side, ref).body)
    relief = relief_poly(side)
    part = next(g for g in getattr(relief, "geoms", [relief]) if g.intersects(body))
    out = {"top relief": part.simplify(0.01).exterior.distance(body)}
    if ref == "J2":
        out["J2 relief"] = jack_relief_poly(side).simplify(0.01).exterior.distance(body)
        bf = sp_faces(body)[0]
        out["plate DXF"] = min(f.distance_to(bf) for f in plate_face(side).faces())
    return out


def jack_check(side: str, top: Solid | None = None, bottom: Solid | None = None):
    """USB / TRRS notch centres equal the layout anchors within NOTCH_TOL, they fit the part they
    cut, the jack bodies sit under the relief pocket at least JACK_MIN_CLEAR from every edge round
    them, and (on the built part) the holes are open and the top stays JACK_MIN_CLEAR off the bodies."""
    relief = relief_poly(side)
    for ref, notch, cut, size in (("J1", usb_notch(side), usb_cuts(side)[0], USB_NOTCH),
                                  ("J2", trrs_notch(side), trrs_cut(side), (TRRS_NOTCH_D, TRRS_NOTCH_D))):
        j = JACK(side, ref)
        bb = cut.bounding_box()
        c = bb.center()
        kx, ky = K(c.X, c.Y)
        # the notch axis must pass through the jack mouth, at the jack axis height
        along = (kx - j.x) * j.facing[1] - (ky - j.y) * j.facing[0]
        dz = c.Z - (Z_PCB_TOP + j.axis_z)
        if abs(along) > NOTCH_TOL or abs(dz) > NOTCH_TOL:
            sys.exit(f"{side} {ref} notch is {along:+.2f} along the wall / {dz:+.2f} in Z from the layout jack")
        if c.Z - size[1] / 2 < Z_SPLIT + 0.3 or c.Z + size[1] / 2 > Z_POCKET_CEIL:
            sys.exit(f"{side} {ref} notch leaves no material at the parting plane or under the top skin")
        body = box(*j.body)
        if not relief.buffer(1e-6).contains(body):
            sys.exit(f"{side} {ref} body is not under the relief pocket")
        if Z_PCB_TOP + j.height > Z_POCKET_CEIL - 0.3:
            sys.exit(f"{side} {ref} is {j.height} mm tall: raise the pocket ceiling (gate G2)")
        clear = jack_clearances(side, ref)
        for what, d in clear.items():
            if d < JACK_MIN_CLEAR:
                sys.exit(f"{side} {ref} body is {d:.3f} mm from the {what} (JACK_MIN_CLEAR {JACK_MIN_CLEAR})")
        clear_txt = ", ".join(f"{what} {d:.3f}" for what, d in clear.items())
        if top is not None:
            # the built part: its least 3D distance to the body (plate edge, relief, wall or ceiling)
            d3 = top.distance_to(jack_body(side, ref))
            if d3 < JACK_MIN_CLEAR:
                sys.exit(f"{side} top part is {d3:.3f} mm from the {ref} body (JACK_MIN_CLEAR {JACK_MIN_CLEAR})")
            clear_txt += f", built top {d3:.3f}"
            px, py = P(notch["x"], notch["y"])
            nx, ny = notch["n"][0], -notch["n"][1]
            deep = WALL - 0.4                 # past the USB plug recess
            mid = Vector(px - nx * deep, py - ny * deep, notch["z"])
            if top.is_inside(mid):
                sys.exit(f"{side} {ref} notch is not open in the top part")
            tx, ty = -ny, nx
            if not top.is_inside(mid + Vector(tx, ty, 0) * (size[0] / 2 + 0.4)):
                sys.exit(f"{side} {ref} notch is wider than modelled")
        print(f"  {side:5s} {ref} notch: centre ({kx:.2f},{ky:.2f}) Z {c.Z:.2f}, {along:+.3f} / {dz:+.3f} mm "
              f"from layout; body {j.height} tall, {Z_POCKET_CEIL - Z_PCB_TOP - j.height:.1f} mm headroom, "
              f"clear (mm): {clear_txt}" + ("; probed open" if top is not None else ""))
    if bottom is not None:
        n = usb_notch(side)
        px, py = P(n["x"], n["y"])
        q = Vector(px - n["n"][0] * 0.9, py + n["n"][1] * 0.9, Z_SPLIT - 0.4)
        if bottom.is_inside(q):
            sys.exit(f"{side} USB recess is not cut in the bottom part")


def feet_check(side: str):
    o = outline_poly(side).buffer(-FOOT_EDGE_MIN - FOOT_D / 2)
    for fx, fy in feet(side):
        if not o.contains(Point(fx, fy)):
            sys.exit(f"{side} rubber foot at ({fx:.1f},{fy:.1f}) runs off the underside")
        for sx, sy in SCREWS(side):
            if math.dist((fx, fy), (sx, sy)) < FOOT_D / 2 + SCREW_CSK_D / 2 + FOOT_EDGE_MIN / 3:
                sys.exit(f"{side} rubber foot at ({fx:.1f},{fy:.1f}) hits the countersink at ({sx:.1f},{sy:.1f})")


def feet(side: str) -> list[tuple[float, float]]:
    return [(mx(side, x), y) for x, y in FEET]


def pin_holes(side: str) -> list[tuple[float, float]]:
    a = L.anchors(side)
    return [a[ref] for ref in PIN_HOLES]


def pocket_corner_r() -> float:
    """Radius of the cutter that reaches the display pocket's ceiling from the parting face: 11.6 deep,
    past the Ø2 tool's 10 mm, so JLCCNC's Ø3 tool and its Min R 2 (corner_r, deviation CASE-8)."""
    return corner_r(Z_DISPLAY_TOP - Z_SPLIT)


def pocket_corners(side: str) -> list[tuple[float, float, int, int, bool]]:
    """Display pocket corners (KiCad frame): x, y, the inward diagonal, and whether the corner lies in
    the key well. The far (front) end lies in the C6R1 well (WS3-5): there the pocket is walled only in
    the plate, below Z_PLATE_TOP, under the module; the header-end corners are walled up to the ceiling."""
    x0, y0, x1, y1 = DISPLAY(side)["pocket"]
    well = well_poly(side)
    return [(cx, cy, sx, sy, well.contains(Point(cx, cy)))
            for cx, cy, sx, sy in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x1, y1, -1, -1), (x0, y1, 1, -1))]


def pocket_reliefs(side: str) -> list[tuple[float, float]]:
    """Centres (KiCad frame) of the dog-bone reliefs, circles of pocket_corner_r() through each corner
    walled up to the ceiling, where the module and J3 stand 0.5 mm from both walls (CASE-1, CASE-8)."""
    a = pocket_corner_r() / math.sqrt(2)
    return [(cx + sx * a, cy + sy * a) for cx, cy, sx, sy, in_well in pocket_corners(side) if not in_well]


def pocket_footprint(side: str) -> Polygon:
    """Plan of the display pocket (KiCad frame): the rectangle plus the dog-bone reliefs."""
    r = pocket_corner_r()
    return unary_union([pocket_poly(side), *[Point(c).buffer(r, quad_segs=64) for c in pocket_reliefs(side)]])


def pocket_cut(side: str) -> Solid:
    """Display pocket: the rectangle up to the ceiling with a dog-bone relief in each corner walled up
    to it (pocket_reliefs), so the cutter leaves no fillet where the module and J3 have only 0.5 mm per
    side; the corners in the key well are walled only in the plate, under the module, and there get the
    cutter's radius as a fillet (deviations CASE-1, CASE-8)."""
    r = pocket_corner_r()
    rect = sp_faces(pocket_poly(side))[0]
    far = [P(cx, cy) for cx, cy, _sx, _sy, in_well in pocket_corners(side) if in_well]
    low = rect
    if far:
        verts = [min(rect.vertices(), key=lambda v: (v.X - c[0]) ** 2 + (v.Y - c[1]) ** 2) for c in far]
        out = fillet(verts, r)
        low = _up(out if isinstance(out, Face) else out.faces()[0])
    cut = prism(low, Z_PCB_TOP - 0.01, Z_PLATE_TOP + 0.01) + prism(rect, Z_PLATE_TOP, Z_DISPLAY_TOP)
    for cx, cy in pocket_reliefs(side):
        px, py = P(cx, cy)
        cut += Pos(px, py, Z_PCB_TOP - 0.01) * Cylinder(r, Z_DISPLAY_TOP - Z_PCB_TOP + 0.01,
                                                      align=(Align.CENTER, Align.CENTER, Align.MIN))
    return cut


def window_cut(side: str) -> Solid:
    """Viewing window: rounded rectangle through the bezel skin with a chamfer on its top edge."""
    d = DISPLAY(side)
    x0, y0, x1, y1 = d["window"]
    cx, cy = P(*d["window_centre"])
    w, h = x1 - x0, y1 - y0
    win = LD.WINDOW_R
    c = LD.WINDOW_CHAMFER
    zt = Z_BEZEL_TOP
    cut = Pos(cx, cy, 0) * prism(RectangleRounded(w, h, win), Z_DISPLAY_TOP - 0.01, zt + 1)
    bevel = loft([Plane.XY.offset(zt - c) * (Pos(cx, cy) * RectangleRounded(w, h, win)).faces()[0],
                  Plane.XY.offset(zt + 0.01) * (Pos(cx, cy) * RectangleRounded(w + 2 * c + 0.02, h + 2 * c + 0.02,
                                                                                win + c + 0.01)).faces()[0]])
    return cut + bevel


def build_top(side: str) -> Solid:
    outline = outline_face(side)
    inner = inner_face(side)
    well = well_face(side)

    body = prism(outline, Z_SPLIT, Z_TOP)
    body = fillet(body.edges().group_by(Axis.Z)[-1], TOP_EDGE_FILLET)
    body = chamfer(body.edges().group_by(Axis.Z)[0], SEAM_CHAMFER)

    # main cavity below the plate
    body -= prism(inner, Z_SPLIT - 1, Z_PLATE_BOT)
    # component / weight-relief pocket above, kept away from the well
    for f in relief_faces(side):
        body -= prism(f, Z_PLATE_BOT - 0.01, Z_POCKET_CEIL)
    # key well
    for wf in well:
        body -= prism(wf, Z_PLATE_TOP, Z_TOP + 1)
    # raised display bezel, flush with the key well where it meets it (cut below with the pocket)
    body += build_bezel(side)
    # switch cutouts through the plate
    for kx, ky, w, h, rot in KEYS(side):
        body -= prism(switch_cut(kx, ky, rot), Z_PLATE_BOT - 1, Z_PLATE_TOP + 0.01)
    for kx, ky, w, h, rot, sd in stab_keys(side):
        body -= prism(stab_cuts(kx, ky, rot, sd), Z_PLATE_BOT - 1, Z_PLATE_TOP + 0.01)

    # PCB clamp bosses + tapped holes; bosses near the wall are joined to it
    webs = boss_webs(side, "top")
    for sx, sy in SCREWS(side):
        cx, cy = P(sx, sy)
        r = boss_radius(side, sx, sy)
        under = screw_under_plate(side, sx, sy)
        ceil = Z_PLATE_BOT if under else Z_POCKET_CEIL
        body += Pos(cx, cy, Z_PCB_TOP) * Cylinder(r, ceil - Z_PCB_TOP + 0.01,
                                                align=(Align.CENTER, Align.CENTER, Align.MIN))
        if (sx, sy) in webs:
            body += prism(webs[(sx, sy)], Z_PCB_TOP, ceil + 0.01)
            for f in wall_fillets(inner, webs[(sx, sy)], corner_r(ceil - Z_SPLIT)):
                body += prism(f, Z_PCB_TOP, ceil + 0.01)
        body -= tap_cut(side, sx, sy)

    # tent legs: pad behind the wall, Ø10 boss outside (flat or toothed), tapped M3 hole
    boss = detent_boss()
    root = boss_root_fillet()
    band = prism(offset(outline, 2.0, kind=Kind.ARC), Z_SPLIT, Z_TOP - TOP_EDGE_FILLET)
    for (px, py), (nx, ny) in leg_mounts(side):
        pad_d = leg_pad_depth(side, px, py, nx, ny)
        pad = Pos(0, 0, Z_PCB_TOP + 0.4) * Box(WALL + pad_d, LEG_PAD[0], Z_POCKET_CEIL - Z_PCB_TOP - 0.4,
                                               align=(Align.MIN, Align.CENTER, Align.MIN))
        pad = _leg_frame(px, py, nx, ny, pad) & prism(outline, Z_SPLIT, Z_TOP)
        foot = _leg_frame(px, py, nx, ny, Pos((WALL + pad_d) / 2, 0) * Rectangle(WALL + pad_d, LEG_PAD[0]))
        for f in wall_fillets(inner, foot, corner_r(Z_POCKET_CEIL - Z_SPLIT)):
            pad += prism(f, Z_PCB_TOP + 0.4, Z_POCKET_CEIL)
        for wf in well:
            pad -= prism(wf, Z_PLATE_TOP, Z_TOP + 1)
        body += pad
        body += _leg_frame(px, py, nx, ny, Pos(0, 0, LEG_Z) * Rot(0, -90, 0) * boss)
        # root fillet, kept on the flat part of the wall
        body += _leg_frame(px, py, nx, ny, Pos(0, 0, LEG_Z) * Rot(0, -90, 0) * root) & band
        depth = leg_hole_depth(side, px, py, nx, ny)
        drill = Pos(-LEG_BOSS_H - 0.01, 0, LEG_Z) * Rot(0, 90, 0) * Cylinder(
            LEG_TAP_D / 2, depth + 0.01, align=(Align.CENTER, Align.CENTER, Align.MIN))
        drill += Pos(-LEG_BOSS_H + depth, 0, LEG_Z) * Rot(0, 90, 0) * Solid.make_cone(
            LEG_TAP_D / 2, 0, drill_point(LEG_TAP_D))
        body -= _leg_frame(px, py, nx, ny, drill)

    # the key well again, up to just over the bosses and pads (and below the bezel, which meets the well
    # flush): boss T2 (right frame (59.7, 121.7)) reached 0.67 mm into the well and stood 1.0 mm above
    # the plate there as a crescent island (CASE-8); the well is one cut from the top, nothing stands in it
    for wf in well:
        body -= prism(wf, Z_PLATE_TOP, Z_POCKET_CEIL + 0.5)

    # display: pocket over the module (cuts the spacer zone and the plate) + viewing window
    body -= pocket_cut(side)
    body -= window_cut(side)

    # USB-C notch + plug recess, TRRS hole
    for cut in usb_cuts(side):
        body -= cut
    body -= trrs_cut(side)

    # reset / boot pin-holes through the top skin
    for x, y in pin_holes(side):
        cx, cy = P(x, y)
        body -= Pos(cx, cy, Z_POCKET_CEIL - 1) * Cylinder(
            PIN_HOLE_D / 2, TOP_SKIN + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return body


def side_mark(side: str) -> Solid:
    """Engraved L / R on the underside, mirrored so it reads correctly from below."""
    cx, cy = P(mx(side, ENGRAVE_AT[0]), ENGRAVE_AT[1])
    txt = Text(side[0].upper(), font_size=ENGRAVE_SIZE, font=ENGRAVE_FONT, font_style=FontStyle.BOLD)
    txt = mirror(txt, about=Plane.YZ)
    return Pos(cx, cy) * prism(txt, -0.01, ENGRAVE_DEPTH)


def build_bottom(side: str, engrave: bool = True) -> Solid:
    outline = outline_face(side)
    inner = inner_face(side)
    body = prism(outline, 0, Z_SPLIT)
    body = fillet(body.edges().group_by(Axis.Z)[0], 1.0)
    body = chamfer(body.edges().group_by(Axis.Z)[-1], SEAM_CHAMFER)
    body -= prism(inner, FLOOR_T, Z_SPLIT + 1)
    webs = boss_webs(side, "bottom")
    for sx, sy in SCREWS(side):
        cx, cy = P(sx, sy)
        r = boss_radius(side, sx, sy)
        body += Pos(cx, cy, FLOOR_T - 0.01) * Cylinder(
            r, Z_SPLIT - FLOOR_T + 0.01, align=(Align.CENTER, Align.CENTER, Align.MIN))
        if (sx, sy) in webs:
            body += prism(webs[(sx, sy)], FLOOR_T - 0.01, Z_SPLIT)
            for f in wall_fillets(inner, webs[(sx, sy)], corner_r(Z_SPLIT - FLOOR_T)):
                body += prism(f, FLOOR_T - 0.01, Z_SPLIT)
        body -= Pos(cx, cy, -1) * Cylinder(SCREW_CLEAR_D / 2, Z_SPLIT + 2,
                                          align=(Align.CENTER, Align.CENTER, Align.MIN))
        # 90 deg countersink
        h = (SCREW_CSK_D - SCREW_CLEAR_D) / 2
        body -= Pos(cx, cy, 0) * Solid.make_cone(SCREW_CSK_D / 2 + 0.01, SCREW_CLEAR_D / 2, h + 0.01,
                                                 Plane.XY.offset(-0.01))
    for fx, fy in feet(side):
        cx, cy = P(fx, fy)
        body -= Pos(cx, cy, -0.01) * Cylinder(FOOT_D / 2, FOOT_DEPTH + 0.01,
                                             align=(Align.CENTER, Align.CENTER, Align.MIN))
    # the USB plug recess reaches below the parting plane
    body -= usb_cuts(side)[1]
    if engrave:
        body -= side_mark(side)
    return body


def build_leg() -> Solid:
    """Custom tent leg, own frame: hub axis +Z, bearing face at Z = 0, spring face at
    Z = LEG_HUB_L, arm along +Y. One part fits all six positions."""
    r = LEG_HUB_D / 2
    hub = Cylinder(r, LEG_HUB_L, align=(Align.CENTER, Align.CENTER, Align.MIN))
    hub = chamfer(hub.edges().group_by(Axis.Z)[-1], LEG_EDGE)
    zc = LEG_HUB_L - LEG_ARM_T / 2                       # arm flush with the spring face
    y_neck = LEG_LEN - LEG_CAP_L                         # shoulder the foot cap sits on
    neck_l = 4.0
    y1 = y_neck - neck_l
    plan = make_face(Polyline((-LEG_ARM_W / 2, 0), (LEG_ARM_W / 2, 0), (LEG_NECK_D / 2, y1),
                              (-LEG_NECK_D / 2, y1), close=True))
    arm = Pos(0, 0, LEG_HUB_L - LEG_ARM_T) * extrude(plan, LEG_ARM_T)
    arm = fillet([e for e in arm.edges() if abs((e.end_point() - e.start_point()).normalized().Y) > 0.9],
                 min(1.5, LEG_ARM_T / 2 - 0.2))
    neck = Pos(0, y_neck - neck_l, zc) * Rot(-90, 0, 0) * Cylinder(
        LEG_NECK_D / 2, neck_l, align=(Align.CENTER, Align.CENTER, Align.MIN))
    spigot = Pos(0, y_neck, zc) * Rot(-90, 0, 0) * Cylinder(
        LEG_SPIGOT[0] / 2, LEG_SPIGOT[1], align=(Align.CENTER, Align.CENTER, Align.MIN))
    spigot = chamfer(spigot.edges().sort_by(Axis.Y)[-1], 0.4)
    leg = hub + arm + neck + spigot
    # round the arm-to-hub joint to the cutter radius (edges on the hub cylinder, arm side)
    joint = [e for e in leg.edges()
             if all(abs(math.hypot(q.X, q.Y) - r) < 0.02 and q.Y > 0.5
                    for q in (e.position_at(s) for s in (0, 0.25, 0.5, 0.75, 1)))]
    leg = fillet(joint, corner_r(LEG_ARM_T))
    leg -= Cylinder(LEG_HOLE_D / 2, 3 * LEG_HUB_L)
    leg -= Pos(0, 0, LEG_HUB_L - LEG_CBORE[1]) * Cylinder(
        LEG_CBORE[0] / 2, LEG_HUB_L, align=(Align.CENTER, Align.CENTER, Align.MIN))
    if DETENT_TEETH:
        teeth = Pos(0, 0, -2) * Cylinder(r, 2.005, align=(Align.CENTER, Align.CENTER, Align.MIN))
        leg += [teeth & g for g in detent_grooves(r + 0.3, 0.0)]
    return leg


def build_leg_cap() -> Solid:
    """Foot cap (print in TPU), in the leg frame: slides onto the spigot."""
    y0, zc = LEG_LEN - LEG_CAP_L, LEG_HUB_L - LEG_ARM_T / 2
    body_l = LEG_CAP_L - LEG_FOOT_D / 2
    cap = Pos(0, y0, zc) * Rot(-90, 0, 0) * Cylinder(
        LEG_FOOT_D / 2, body_l, align=(Align.CENTER, Align.CENTER, Align.MIN))
    cap += Pos(0, y0 + body_l, zc) * Sphere(LEG_FOOT_D / 2)
    cap &= Pos(0, y0, zc) * Box(2 * LEG_FOOT_D, LEG_CAP_L, 2 * LEG_FOOT_D, align=(Align.CENTER, Align.MIN, Align.CENTER))
    cap -= Pos(0, y0 - 0.01, zc) * Rot(-90, 0, 0) * Cylinder(
        LEG_SPIGOT[0] / 2 - 0.1, LEG_SPIGOT[1], align=(Align.CENTER, Align.CENTER, Align.MIN))
    return cap


def leg_cap_upright() -> Solid:
    """The foot cap in its own frame: axis +Z, open end on Z = 0, dome up."""
    y0, zc = LEG_LEN - LEG_CAP_L, LEG_HUB_L - LEG_ARM_T / 2
    return Rot(90, 0, 0) * (Pos(0, -y0, -zc) * build_leg_cap())


def cap_tree_places() -> list[tuple[float, float]]:
    """Cap centres: the 8 outer places of a 3 x 3 grid, in order round the ring."""
    p = CAP_TREE_PITCH
    ring = [(-p, -p), (0, -p), (p, -p), (p, 0), (p, p), (0, p), (-p, p), (-p, 0)]
    return ring[:CAP_TREE_N]


def build_leg_cap_tree() -> Solid:
    """CAP_TREE_N foot caps for one JLC3DP TPU part (deviation CASE-4): caps upright on their open end,
    runner bars at the base between neighbours and spokes to a central tag post. Each cap snips off
    at its base, away from the dome that meets the desk; the bores stay clear."""
    cap = leg_cap_upright()
    places = cap_tree_places()
    r = CAP_RUNNER

    def bar(a, b):
        ln = math.dist(a, b)
        ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
        return Pos((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, 0) * Rot(0, 0, ang) * Box(
            ln, r, r, align=(Align.CENTER, Align.CENTER, Align.MIN))

    tree = Cylinder(CAP_TAG[0] / 2, CAP_TAG[1], align=(Align.CENTER, Align.CENTER, Align.MIN))
    tree = chamfer(tree.edges().group_by(Axis.Z)[-1], 0.5)
    for (x, y) in places:
        tree += Pos(x, y, 0) * cap
    for a, b in zip(places, places[1:] + places[:1] if len(places) == 8 else places[1:]):
        tree += bar(a, b)
    for (x, y) in places:
        if x == 0 or y == 0:
            tree += bar((0.0, 0.0), (x, y))
    bore = Pos(0, 0, -0.01) * Cylinder(LEG_SPIGOT[0] / 2 - 0.1, LEG_SPIGOT[1] + 0.01,
                                        align=(Align.CENTER, Align.CENTER, Align.MIN))
    for (x, y) in places:
        tree -= Pos(x, y, 0) * bore
    return tree


def cap_tree_check(tree: Solid):
    """One solid, at least JLC3DP's minimum part size, every bore open, caps as modelled."""
    bb = tree.bounding_box()
    size = sorted((bb.size.X, bb.size.Y, bb.size.Z), reverse=True)
    if any(s < m for s, m in zip(size, CAP_TREE_MIN)):
        sys.exit(f"leg cap tree {size[0]:.1f} x {size[1]:.1f} x {size[2]:.1f} is below JLC3DP's minimum {CAP_TREE_MIN}")
    if len(tree.solids()) != 1:
        sys.exit("leg cap tree is not one piece")
    for (x, y) in cap_tree_places():
        for z in (0.05, LEG_SPIGOT[1] - 0.1):
            if tree.is_inside(Vector(x, y, z)):
                sys.exit(f"leg cap tree: the bore at ({x},{y}) is not open at Z {z}")
        if not tree.is_inside(Vector(x, y, LEG_CAP_L - 0.3)):
            sys.exit(f"leg cap tree: no dome at ({x},{y})")
    print(f"  leg cap tree: {CAP_TREE_N} caps, {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm "
          f"(JLC3DP FDM minimum {CAP_TREE_MIN[0]:.0f} x {CAP_TREE_MIN[1]:.0f} x {CAP_TREE_MIN[2]:.0f}), "
          f"runners {CAP_RUNNER} x {CAP_RUNNER}, one piece, bores open")


def leg_parts(side: str, swing_deg: float = 90.0) -> list:
    """Legs + caps seated on each boss for the assembly preview (90 = straight down)."""
    leg = build_leg() + build_leg_cap()
    parts = []
    for (px, py), (nx, ny) in leg_mounts(side):
        seat = Pos(0, 0, LEG_Z) * Rot(0, -90, 0) * Pos(0, 0, LEG_BOSS_H) * Rot(0, 0, swing_deg)
        parts.append(_leg_frame(px, py, nx, ny, seat * leg))
    return parts


# --------------------------------------------------------------------------
# 2D exports
# --------------------------------------------------------------------------
def _dxf(layers: dict):
    """ExportDXF with fixed metadata (reproducible files)."""
    import ezdxf
    from build123d import ExportDXF, LineType, Unit
    ezdxf.options.write_fixed_meta_data_for_testing = True
    dxf = ExportDXF(unit=Unit.MM)
    for name, dashed in layers.items():
        dxf.add_layer(name, line_type=LineType.DASHED) if dashed else dxf.add_layer(name)
    return dxf


def _wire_of(sketch_or_face):
    return sketch_or_face.faces()[0].outer_wire() if not isinstance(sketch_or_face, Face) else sketch_or_face.outer_wire()


def export_fitcheck_dxf(side: str, path: str):
    """1:1 top-view drawing of one half: case outline, inner wall, PCB, key well, switch cutouts,
    screw holes, display window + pocket, USB / TRRS notches, pin-holes. Print at 100 % and lay
    the PCB on it."""
    dxf = _dxf({"OUTLINE": False, "WALL_INNER": True, "PCB": True, "KEY_WELL": False, "SWITCH_CUTOUTS": False,
                "SCREWS": False, "DISPLAY": False, "JACKS": False, "FEATURES": False})
    dxf.add_shape(outline_face(side).outer_wire(), layer="OUTLINE")
    dxf.add_shape(inner_face(side).outer_wire(), layer="WALL_INNER")
    for f in sp_faces(L.outline(side)):
        dxf.add_shape(f.outer_wire(), layer="PCB")
    for wf in well_face(side):
        dxf.add_shape(wf.outer_wire(), layer="KEY_WELL")
    for kx, ky, w, h, rot in KEYS(side):
        dxf.add_shape(_wire_of(switch_cut(kx, ky, rot)), layer="SWITCH_CUTOUTS")
    for kx, ky, w, h, rot, sd in stab_keys(side):
        for f in stab_cuts(kx, ky, rot, sd).faces():
            dxf.add_shape(f.outer_wire(), layer="SWITCH_CUTOUTS")
    for sx, sy in SCREWS(side):
        dxf.add_shape(_wire_of(Pos(*P(sx, sy)) * Circle(SCREW_CLEAR_D / 2)), layer="SCREWS")
        dxf.add_shape(_wire_of(Pos(*P(sx, sy)) * Circle(boss_radius(side, sx, sy))), layer="SCREWS")
    d = DISPLAY(side)
    for f in sp_faces(pocket_footprint(side)):
        dxf.add_shape(f.outer_wire(), layer="DISPLAY")
    x0, y0, x1, y1 = d["window"]
    dxf.add_shape(_wire_of(Pos(*P(*d["window_centre"])) * RectangleRounded(x1 - x0, y1 - y0, LD.WINDOW_R)),
                  layer="DISPLAY")
    for notch, w in ((usb_notch(side), USB_NOTCH[0]), (usb_notch(side), USB_RECESS[0]),
                     (trrs_notch(side), TRRS_NOTCH_D)):
        px, py = P(notch["x"], notch["y"])
        nx, ny = notch["n"][0], -notch["n"][1]
        dxf.add_shape(_wire_of(_leg_frame(px, py, nx, ny, Pos(WALL / 2, 0) * Rectangle(WALL, w))), layer="JACKS")
    for ref in ("J1", "J2"):
        dxf.add_shape(_wire_of(sp_faces(box(*JACK(side, ref).body))[0]), layer="JACKS")
    for x, y in pin_holes(side):
        dxf.add_shape(_wire_of(Pos(*P(x, y)) * Circle(PIN_HOLE_D / 2)), layer="FEATURES")
    dxf.write(path)


@lru_cache
def plate_face(side: str) -> Sketch:
    """Switch plate island (part frame): the well + WALL / 2 + 0.5 inside the wall, minus the
    switch and stabiliser cutouts and the J2 relief (its top is flush with the plate top). The
    integrated plate of the top part; also exported as a stand-alone DXF for an FR4 / aluminium plate."""
    s = Sketch() + list(well_face(side, extra=WALL / 2 + 0.5))
    s &= inner_face(side)
    for kx, ky, w, h, rot in KEYS(side):
        s -= switch_cut(kx, ky, rot)
    for kx, ky, w, h, rot, sd in stab_keys(side):
        s -= stab_cuts(kx, ky, rot, sd)
    for f in sp_faces(jack_relief_poly(side)):
        s -= f
    return s


def export_plate_dxf(side: str, path: str):
    dxf = _dxf({"PLATE_OUTLINE": False, "SWITCH_CUTOUTS": False})
    s = plate_face(side)
    for f in s.faces():
        dxf.add_shape(f.outer_wire(), layer="PLATE_OUTLINE")
        for w in f.inner_wires():
            dxf.add_shape(w, layer="SWITCH_CUTOUTS")
    dxf.write(path)


def mirror_x(shape):
    return mirror(shape, about=Plane.YZ)


def mirror_check(name: str, left, right):
    """The left part must be the mirror image of the right part."""
    m = mirror_x(right)
    a, b = left.bounding_box(), m.bounding_box()
    dv = abs(left.volume - m.volume) / m.volume
    da = abs(left.area - m.area) / m.area
    dc = (left.center() - m.center()).length
    dbb = max((a.min - b.min).length, (a.max - b.max).length)
    if dv > MIRROR_TOL or da > MIRROR_TOL or dc > MIRROR_TOL_MM or dbb > MIRROR_TOL_MM:
        sys.exit(f"{name}: left is not the mirror of right (dV {dv:.2e}, dA {da:.2e}, dC {dc:.4f}, dBB {dbb:.4f})")
    print(f"  {name:7s} left == mirror(right): dV {dv:.1e}, dA {da:.1e}, centroid {dc:.1e} mm")


def export_part_step(shape, path: str, name: str):
    """STEP named after the part (the shop sees the name), stamped with the case revision date rather
    than the export time, so the same model gives the same file."""
    shape.label = name
    export_step(shape, path, timestamp=f"{CASE_REVISION_DATE}T00:00:00")


def report(name: str, s):
    bb = s.bounding_box()
    print(f"{name:22s} vol {s.volume / 1000:7.2f} cm3  mass(6061) {s.volume * 2.70e-3:6.1f} g  "
          f"bbox {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f}  valid={s.is_valid}  solids={len(s.solids())}")


def main(outdir: str, platedir: str | None = None):
    os.makedirs(outdir, exist_ok=True)
    platedir = platedir or os.path.join(ROOT, "plates")
    os.makedirs(platedir, exist_ok=True)
    print("Screw clearances to switch housings (mm), right half:")
    for i, sx, sy, w in clearance_report("right"):
        print(f"  #{i} ({sx:7.2f},{sy:7.2f}) clearance {w:5.2f}  boss r {boss_radius('right', sx, sy):.2f}"
              f"{'  under plate' if screw_under_plate('right', sx, sy) else ''}")
    print("Checks:")
    for side in SIDES:
        pcb_check(side)
        leg_check(side)
        web_check(side)
        feet_check(side)
        display_check(side)
        jack_check(side)
        tap_check(side)
    parts = {}
    for side in SIDES:
        export_fitcheck_dxf(side, os.path.join(outdir, f"worxboard_{side}_fitcheck.dxf"))
        export_plate_dxf(side, os.path.join(platedir, f"worxboard-plate-{side}.dxf"))
        parts[f"{side}_top"] = build_top(side)
        parts[f"{side}_bottom"] = build_bottom(side, engrave=False)
        parts[f"{side}_spacer"] = build_spacer(side)
    print("Mirror:")
    for kind in ("top", "bottom", "spacer"):
        mirror_check(kind, parts[f"left_{kind}"], parts[f"right_{kind}"])
    print("Built-part checks:")
    for side in SIDES:
        parts[f"{side}_bottom"] -= side_mark(side)
        display_check(side, parts[f"{side}_top"])
        jack_check(side, parts[f"{side}_top"], parts[f"{side}_bottom"])
        tap_check(side, parts[f"{side}_top"])
        spacer_check(side, parts[f"{side}_spacer"])
    parts["leg"], parts["leg_cap"], parts["leg_cap_tree"] = build_leg(), build_leg_cap(), build_leg_cap_tree()
    cap_tree_check(parts["leg_cap_tree"])
    for name, s in parts.items():
        export_part_step(s, os.path.join(outdir, f"worxboard_{name}.step"), f"worxboard_{name}")
        fine = name.startswith("leg")
        export_stl(s, os.path.join(outdir, f"worxboard_{name}.stl"),
                   tolerance=0.01 if fine else 0.02, angular_tolerance=0.1 if fine else 0.3)
        report(name, s)
    asm = Compound([parts["right_top"], parts["right_bottom"], parts["right_spacer"], *leg_parts("right")])
    export_part_step(asm, os.path.join(outdir, "worxboard_right_assembly_with_legs.step"),
                     "worxboard_right_assembly_with_legs")
    export_stl(asm, os.path.join(outdir, "worxboard_right_assembly_with_legs.stl"), tolerance=0.05)
    bad = [name for name, s in parts.items() if not s.is_valid or len(s.solids()) != 1]
    if bad:
        sys.exit(f"invalid geometry: {', '.join(bad)}")
    print("all case checks passed")
    return parts


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "case", "exports"),
         sys.argv[2] if len(sys.argv) > 2 else None)
