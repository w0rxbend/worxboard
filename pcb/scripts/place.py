# SPDX-License-Identifier: GPL-3.0-or-later
"""Build the board of one half from its netlist and layout.json (spec §8, §9 stage 7).

    python3 pcb/scripts/place.py <side>   build/<side>/<side>.net -> pcb/<side>/worxboard-<side>.kicad_pcb

Every footprint gets the reference, value, FPID, nets and KIID path of its symbol, so DRC
schematic parity passes. Positions come from layout/build/layout.json (left = mirrored right
frame, rot_L = -rot_R, B-side parts flipped); the MCU cluster is placed in the U1 frame. The
script also draws Edge.Cuts, sets the netclasses and rules (in the .kicad_pro), and adds the
GND pours and silkscreen. It asserts that every top-side courtyard lies in Z_BACK u Z_TRRS.

Runs in kicad/kicad:10.0.7 (pcbnew) with shapely on PYTHONPATH (spec §9.1).
"""
from __future__ import annotations

import json
import math
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT))

import pcbnew  # noqa: E402
from shapely.geometry import Polygon, box  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

from design import POWER_NETS  # noqa: E402
from netcmp import load as load_netlist  # noqa: E402

LAYOUT_JSON = ROOT / "layout/build/layout.json"
STOCK_FP = Path("/usr/share/kicad/footprints")
LOCAL_FP = ROOT / "pcb/lib/worxboard.pretty"
MIRROR_X = 260.0

# Rules (spec §8.4); netclass (track, clearance)
NETCLASSES = {"Default": (0.25, 0.2), "Power": (0.5, 0.2), "USB": (0.25, 0.2)}
USB_NETS = ("USB_DP", "USB_DM", "USB_C_DP", "USB_C_DM")
VIA = (0.6, 0.3)                 # pad, drill
BOARD_MIN = 0.127                # JLC 2-layer minimum track / clearance
EDGE_CLEARANCE = 0.5
HOLE_CLEARANCE = 0.25
BOARD_T = 1.6
OUTLINE_W = 0.1
ZONE_CLEARANCE = 0.25
ZONE_MIN_W = 0.25
ZONE_THERMAL = (0.3, 0.4)        # gap, spoke
ARC_STEPS = 16                   # outline fillets in zone polygons
HOLE_KEEPOUT = 6.5               # copper keepout diameter around each mounting hole
ZONE_TOL = 0.02                  # courtyard vs zone check slack (mm)
SILK_TEXT = (1.0, 0.15)          # size, thickness
SKIP_FIELDS = ("Footprint", "Datasheet", "Description", "Reference", "Value")
DIODE_OFFSET = (0.0, 5.0)        # B.Cu diode centre in the key frame (below the switch centre)

# U1 (x, y, rot) per half. The RP2040 cannot be mirrored: the left one is turned 180 deg so its
# USB pins face J1, and sits 1.5 mm further back (docs/deviations.md WS2b)
# KiCad saves items sorted by KIID, so random KIIDs reorder the board, the DSN and with them the
# Freerouting result. Every board-writing stage seeds the generator from its inputs instead, so
# the same inputs give a byte-identical board (with PYTHONHASHSEED=0, set by pcb.just). The
# per-side base seeds are ones whose rebuild routes to 0 unconnected (docs/deviations.md WS2c-4).
KIID_SEED = {"left": 0x2, "right": 0x1}


def seed_kiids(side: str, *inputs: bytes) -> None:
    """Seed KiCad's UUID generator from the stage inputs (distinct inputs -> distinct streams)."""
    crc = KIID_SEED[side]
    for b in inputs:
        crc = zlib.crc32(b, crc)
    pcbnew.KIID.SeedGenerator(crc)


U1_POSE = {"right": (166.0, 44.0, 0.0), "left": (93.4, 42.0, 180.0)}
U1_ROT = {s: p[2] for s, p in U1_POSE.items()}

# MCU cluster in the U1 frame (x, y, rot), mm from the U1 centre; the same on both halves
CLUSTER = {
    "Y1": (-0.37, 8.9, -90), "R7": (2.6, 10.42, 0),
    "R3": (6.5, -5.125, 180), "R4": (6.5, -4.075, 180),              # USB 27R, in the pair
    "C14": (2.2, -6.4, 0), "C15": (2.2, -7.6, 0), "C17": (4.3, -6.4, 0), "C16": (4.3, -7.6, 0),
    "C19": (6.0, -7.4, 90),                                          # beside the pins 48-50 escapes
}
CLUSTER_SIDE = {
    "right": {"C6": (-1.0, 12.2, 0), "C7": (1.2, 12.2, 0)},
    "left": {"C6": (-2.8, 9.0, 90), "C7": (4.2, 9.4, 90)},           # the board edge is near
}

# Everything else, right frame (x, y, rot); the left half mirrors x with mirror_rot()
PLACE_R = {
    "U2": (154.6, 35.0, 0), "C5": (160.6, 33.2, 90),                 # flash beside its escapes
    "R8": (147.0, 33.4, 90), "R9": (145.8, 33.4, 90), "R13": (145.0, 46.0, 0),
    "U4": (177.5, 39.4, 0),
    "C11": (175.0, 43.2, 0), "C12": (175.0, 44.4, 0), "C13": (177.2, 43.2, 0), "C18": (177.2, 44.4, 0),
    "C8": (179.4, 43.2, 0), "C9": (179.4, 44.4, 0), "C10": (179.4, 45.6, 0),   # IOVDD, on the 3V3 moat
    "SW1": (176.0, 50.0, 90), "SW2": (180.0, 50.0, 90),
    "J1": (186.0, 34.25, 180),
    "R1": (189.4, 42.4, 90), "R2": (183.4, 43.2, 0), "R10": (182.6, 47.6, 90),
    "D1": (193.6, 44.2, 90), "C1": (196.1, 44.2, 90), "C2": (196.1, 48.6, 90),
    "U3": (199.6, 46.4, 0), "C3": (202.8, 45.2, 90), "C4": (202.8, 48.0, 90),
    "R5": (190.6, 47.6, 90), "R6": (190.6, 50.4, 90),
    "JP1": (186.6, 51.6, 0), "F1": (192.8, 52.8, 0),
    "TP11": (171.0, 55.5, 0), "TP4": (173.2, 55.5, 0), "TP5": (175.4, 55.5, 0), "TP6": (177.6, 55.5, 0),
    "TP7": (179.8, 55.5, 0), "TP8": (182.0, 55.5, 0), "TP9": (184.2, 55.5, 0), "TP10": (186.4, 55.5, 0),
    "TP1": (81.6, 44.4, 0), "TP2": (83.8, 44.4, 0), "TP3": (86.0, 44.4, 0),
    "J2": (57.375, 103.0, 0), "U5": (55.4, 94.6, 0), "R11": (61.4, 94.8, 90), "R12": (59.8, 94.8, 90),
}
# Left-half overrides (left frame): the turned U1 puts the flash and the pair elsewhere
PLACE_L = {
    "J1": (74.0, 34.25, 180),
    "U2": (96.0, 53.7, 180), "C5": (90.0, 55.4, 90), "R8": (89.0, 52.6, 90), "R9": (87.8, 52.6, 90),
    "C11": (99.8, 34.4, 0), "C12": (99.8, 33.2, 0), "C13": (101.8, 34.4, 0), "C18": (101.8, 33.2, 0),
    "C8": (102.0, 36.4, 0), "C9": (102.0, 37.6, 0), "C10": (104.0, 37.0, 0),
    "R1": (80.5, 39.6, 0), "R2": (70.2, 43.4, 0),
    "TP11": (81.0, 33.8, 0), "TP4": (83.2, 33.8, 0), "TP5": (85.4, 33.8, 0), "TP6": (81.0, 36.0, 0),
    "TP7": (83.2, 36.0, 0), "TP8": (87.6, 34.0, 0), "TP9": (87.6, 36.2, 0), "TP10": (85.4, 36.2, 0),
}

# Left USB pair: a straight run from past R3/R4 to the J1 columns, U4 on it (route_critical.py)
USB_L_START = (7.8, -4.6)        # U1 frame
USB_L_END_DY = 1.0               # end of the diagonal below the J1 pad rear ends
U4_L_S = 8.6                     # U4 centre along the diagonal

# Silkscreen, right frame (text, x, y, rot)
SILK = [("worxboard {S} rev A", 130.0, 45.0, 0),
        ("DO NOT HOT-PLUG TRRS", 51.6, 116.0, 90), ("HOST → LEFT", 53.4, 116.0, 90),
        ("JP1: cut = split power", 186.6, 54.2, 0)]

# Courtyards allowed past the zones (mm): J2's sleeve pad and snout, J1's snout
ZONE_ALLOW = {"J2": 1.4, "J1": 0.0}


def mm(v: float) -> int:
    return pcbnew.FromMM(v)


def pt(x: float, y: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I(mm(x), mm(y))


def rotate(x: float, y: float, deg: float) -> tuple[float, float]:
    """KiCad screen rotation (y down, positive CCW on screen)."""
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return x * c + y * s, -x * s + y * c


def mirror_rot(rot: float) -> float:
    """Rotation of a part mirrored to the left half (pin geometry of 2-pin parts is mirrored)."""
    return (180.0 - rot) % 360.0


def layout_side(side: str) -> dict:
    return json.loads(LAYOUT_JSON.read_text())["sides"][side]


def u1_frame(side: str, lx: float, ly: float) -> tuple[float, float]:
    ux, uy, rot = U1_POSE[side]
    dx, dy = rotate(lx, ly, rot)
    return ux + dx, uy + dy


def usb_diagonal(side: str, j1: tuple[float, float]) -> tuple[tuple[float, float], tuple[float, float]]:
    """Left half: start and end of the straight pair run (end below the J1 pair columns)."""
    a = u1_frame(side, *USB_L_START)
    b = (j1[0] - 0.5, j1[1] + JACK_REAR + USB_L_END_DY)
    return a, b


JACK_REAR = 4.77                 # J1 origin -> pad row rear end (rotated 180: 4.045 + 1.45 / 2)


def top_positions(side: str) -> dict[str, tuple[float, float, float]]:
    """Every top-side part: (x, y, rot) in the side's own frame."""
    out = {}
    for ref, (x, y, r) in PLACE_R.items():
        out[ref] = (x, y, r) if side == "right" else (MIRROR_X - x, y, mirror_rot(r))
    if side == "left":
        out.update(PLACE_L)
    out["U1"] = U1_POSE[side]
    rot = U1_ROT[side]
    for ref, (lx, ly, lr) in {**CLUSTER, **CLUSTER_SIDE[side]}.items():
        out[ref] = (*u1_frame(side, lx, ly), (rot + lr) % 360.0)
    if side == "left":
        (x0, y0), (x1, y1) = usb_diagonal(side, out["J1"][:2])
        n = math.hypot(x1 - x0, y1 - y0)
        ux, uy = (x1 - x0) / n, (y1 - y0) / n
        out["U4"] = (x0 + U4_L_S * ux, y0 + U4_L_S * uy, math.degrees(math.atan2(-uy, ux)))
    lay = layout_side(side)
    p1 = lay["display"]["header_pins"][0]             # J3 pin 1 at low x, pins along +x
    out["J3"] = (p1[0], p1[1], 90.0)
    return out


def load_fp(fpid: str) -> pcbnew.FOOTPRINT:
    lib, name = fpid.split(":")
    path = LOCAL_FP if lib == "worxboard" else STOCK_FP / f"{lib}.pretty"
    fp = pcbnew.FootprintLoad(str(path), name)
    if fp is None:
        raise SystemExit(f"footprint {fpid} not found")
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp


def place(fp: pcbnew.FOOTPRINT, x: float, y: float, rot: float, back: bool = False) -> None:
    fp.SetPosition(pt(x, y))
    if back:
        fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    fp.Rotate(fp.GetPosition(), pcbnew.EDA_ANGLE(rot, pcbnew.DEGREES_T))


def add_footprints(board: pcbnew.BOARD, side: str, net_path: Path) -> None:
    nl = load_netlist(net_path)
    nets = {}
    for name in sorted(nl.nets):
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        nets[name] = ni
    lay = layout_side(side)
    keys = {k["id"]: k for k in lay["keys"]}
    holes = lay["holes"]
    top = top_positions(side)
    tstamps = _tstamps(net_path)
    for ref in sorted(nl.comps, key=_ref_key):
        c = nl.comps[ref]
        fp = load_fp(c.footprint)
        fp.SetReference(ref)
        fp.SetValue(c.value)
        fp.SetPath(pcbnew.KIID_PATH(f"/{tstamps[ref]}"))
        for name, value in c.fields.items():           # symbol fields (parity checks them)
            if name not in SKIP_FIELDS:
                fp.SetField(name, value)
                fp.GetField(name).SetVisible(False)
        fp.SetExcludedFromBOM("exclude_from_bom" in c.props)
        fp.SetDNP("dnp" in c.props)
        board.Add(fp)
        for pad in fp.Pads():
            hit = c.pins.get(pad.GetNumber())
            if hit:
                pad.SetNet(nets[hit[1]])
        key = c.fields.get("Key")
        if key and ref.startswith("SK"):
            k = keys[key]
            place(fp, k["x"], k["y"], k["rot"], back=True)
        elif key:
            k = keys[key]
            dx, dy = rotate(*DIODE_OFFSET, k["rot"])
            place(fp, k["x"] + dx, k["y"] + dy, k["rot"] + 180.0, back=True)
        elif "Hole" in c.fields:
            place(fp, *holes[int(c.fields["Hole"])], 0.0)
        else:
            place(fp, *top[ref])
        fp.Reference().SetVisible(ref.startswith(("J", "SW", "JP", "U")))
    for k in lay["keys"]:
        if "stabs" in k:
            (x0, y0), (x1, y1) = k["stabs"]
            stab = load_fp("worxboard:Stab_MX_2u")
            stab.SetReference(f"STAB_{k['id']}")
            stab.Reference().SetVisible(False)
            board.Add(stab)
            place(stab, k["x"], k["y"], math.degrees(math.atan2(-(y1 - y0), x1 - x0)))


def _ref_key(ref: str) -> tuple[str, int]:
    head = ref.rstrip("0123456789")
    return head, int(ref[len(head):] or 0)


def _tstamps(net_path: Path) -> dict[str, str]:
    """ref -> symbol uuid (netlist comp tstamps)."""
    from netcmp import find, find_all, parse, val
    root = parse(net_path.read_text())
    return {val(c, "ref"): val(c, "tstamps") for c in find_all(find(root, "components"), "comp")}


def outline_points(side: str) -> list[tuple[float, float]]:
    """Closed outline with the fillets sampled (zones, checks)."""
    pts = []
    for s in layout_side(side)["outline"]["segments"]:
        if s["type"] == "line":
            pts.append(tuple(s["start"]))
            continue
        (cx, cy), (sx, sy), (ex, ey), (mx_, my) = s["centre"], s["start"], s["end"], s["mid"]
        a0, a1 = math.atan2(sy - cy, sx - cx), math.atan2(ey - cy, ex - cx)
        am = math.atan2(my - cy, mx_ - cx)
        sweep = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        if abs(((am - a0 + math.pi) % (2 * math.pi) - math.pi)) > abs(sweep):
            sweep -= math.copysign(2 * math.pi, sweep)
        r = math.hypot(sx - cx, sy - cy)
        pts += [(cx + r * math.cos(a0 + sweep * i / ARC_STEPS), cy + r * math.sin(a0 + sweep * i / ARC_STEPS))
                for i in range(ARC_STEPS)]
    return pts


def add_outline(board: pcbnew.BOARD, side: str) -> None:
    for s in layout_side(side)["outline"]["segments"]:
        shape = pcbnew.PCB_SHAPE(board)
        shape.SetLayer(pcbnew.Edge_Cuts)
        shape.SetWidth(mm(OUTLINE_W))
        if s["type"] == "line":
            shape.SetShape(pcbnew.SHAPE_T_SEGMENT)
            shape.SetStart(pt(*s["start"]))
            shape.SetEnd(pt(*s["end"]))
        else:
            shape.SetShape(pcbnew.SHAPE_T_ARC)
            shape.SetArcGeometry(pt(*s["start"]), pt(*s["mid"]), pt(*s["end"]))
        board.Add(shape)


def add_gnd_zones(board: pcbnew.BOARD, side: str) -> None:
    gnd = board.FindNet("GND")
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(gnd)
        z.SetZoneName(f"GND_{board.GetLayerName(layer)}")
        z.SetLocalClearance(mm(ZONE_CLEARANCE))
        z.SetMinThickness(mm(ZONE_MIN_W))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(mm(ZONE_THERMAL[0]))
        z.SetThermalReliefSpokeWidth(mm(ZONE_THERMAL[1]))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        outline = z.Outline()
        outline.NewOutline()
        for x, y in outline_points(side):
            outline.Append(mm(x), mm(y))
        board.Add(z)


def add_hole_keepouts(board: pcbnew.BOARD, side: str) -> None:
    """Copper keepout around each M2.5 hole (spec §8.2: case boss / screw head)."""
    from shapely.geometry import Point
    for i, (x, y) in enumerate(layout_side(side)["holes"]):
        z = pcbnew.ZONE(board)
        z.SetIsRuleArea(True)
        z.SetLayerSet(pcbnew.LSET.AllCuMask(2))
        for attr in ("Tracks", "Vias", "ZoneFills"):
            getattr(z, f"SetDoNotAllow{attr}")(True)
        z.SetDoNotAllowPads(False)
        z.SetDoNotAllowFootprints(False)
        z.SetZoneName(f"HOLE_{i}")
        o = z.Outline()
        o.NewOutline()
        for px, py in list(Point(x, y).buffer(HOLE_KEEPOUT / 2, quad_segs=8).exterior.coords)[:-1]:
            o.Append(mm(px), mm(py))
        board.Add(z)


def add_silk(board: pcbnew.BOARD, side: str) -> None:
    for text, x, y, rot in SILK:
        t = pcbnew.PCB_TEXT(board)
        t.SetText(text.format(S=side[0].upper()))
        t.SetLayer(pcbnew.F_SilkS)
        t.SetPosition(pt(x if side == "right" else MIRROR_X - x, y))
        t.SetTextAngle(pcbnew.EDA_ANGLE(rot, pcbnew.DEGREES_T))
        t.SetTextSize(pcbnew.VECTOR2I(mm(SILK_TEXT[0]), mm(SILK_TEXT[0])))
        t.SetTextThickness(mm(SILK_TEXT[1]))
        board.Add(t)


def setup_board(board: pcbnew.BOARD) -> None:
    ds = board.GetDesignSettings()
    ds.SetBoardThickness(mm(BOARD_T))
    board.SetCopperLayerCount(2)
    ds.m_TrackMinWidth = mm(BOARD_MIN)
    ds.m_MinClearance = mm(BOARD_MIN)
    ds.m_CopperEdgeClearance = mm(EDGE_CLEARANCE)
    ds.m_HoleClearance = mm(HOLE_CLEARANCE)


def write_rules(pro: Path) -> None:
    """Netclasses and DRC rules live in the project file (kept: what gen_sch.py wrote)."""
    data = json.loads(pro.read_text()) if pro.exists() else {"meta": {"filename": pro.name, "version": 3}}
    classes = []
    for name, (track, clear) in NETCLASSES.items():
        classes.append({"name": name, "track_width": track, "clearance": clear, "via_diameter": VIA[0],
                        "via_drill": VIA[1], "microvia_diameter": 0.3, "microvia_drill": 0.1,
                        "diff_pair_width": 0.25, "diff_pair_gap": 0.2, "diff_pair_via_gap": 0.25,
                        "bus_width": 12, "wire_width": 6, "line_style": 0,
                        "priority": 2147483647 if name == "Default" else len(classes),
                        "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)",
                        "tuning_profile": ""})
    patterns = [{"netclass": "Power", "pattern": n} for n in POWER_NETS]
    patterns += [{"netclass": "USB", "pattern": n} for n in USB_NETS]
    data["net_settings"] = {"classes": classes, "meta": {"version": 5}, "net_colors": None,
                            "netclass_assignments": None, "netclass_patterns": patterns}
    severities = {k: "error" for k in ("missing_footprint", "extra_footprint", "net_conflict",
                                       "footprint_symbol_mismatch", "duplicate_footprints")}
    severities.update({k: "warning" for k in ("lib_footprint_issues", "lib_footprint_mismatch",
                                              "silk_overlap", "text_height", "text_thickness",
                                              "npth_inside_courtyard")})
    data["board"] = {"design_settings": {
        "rules": {"min_clearance": BOARD_MIN, "min_track_width": BOARD_MIN,
                  "min_copper_edge_clearance": EDGE_CLEARANCE, "min_hole_clearance": HOLE_CLEARANCE,
                  "min_hole_to_hole": 0.25, "min_via_diameter": VIA[0], "min_through_hole_diameter": VIA[1],
                  "min_via_annular_width": 0.13, "min_connection": 0.0, "min_groove_width": 0.0,
                  "min_silk_clearance": 0.0, "min_text_height": 0.8, "min_text_thickness": 0.12,
                  "min_microvia_diameter": 0.2, "min_microvia_drill": 0.1, "min_resolved_spokes": 1,
                  "solder_mask_to_copper_clearance": 0.0, "allow_blind_buried_vias": False,
                  "allow_microvias": False, "max_error": 0.005, "use_height_for_length_calcs": True},
        "rule_severities": severities,
        "track_widths": [0.0, 0.15, 0.25, 0.5], "via_dimensions": [{"diameter": 0.0, "drill": 0.0}],
        "meta": {"version": 2}}}
    pro.write_text(json.dumps(data, indent=2) + "\n")


def courtyard(fp: pcbnew.FOOTPRINT) -> Polygon | None:
    sps = fp.GetCourtyard(pcbnew.F_CrtYd)
    if sps.OutlineCount() == 0:
        return None
    polys = []
    for i in range(sps.OutlineCount()):
        o = sps.Outline(i)
        polys.append(Polygon([(pcbnew.ToMM(o.CPoint(j).x), pcbnew.ToMM(o.CPoint(j).y)) for j in range(o.PointCount())]))
    return unary_union(polys)


def check_zones(board: pcbnew.BOARD, side: str) -> list[str]:
    lay = layout_side(side)
    pcb = Polygon(outline_points(side))
    zones = []
    for name in ("Z_BACK", "Z_TRRS"):
        for p in lay["zones"][name]:
            zones.append(Polygon(p["exterior"], p.get("holes", [])))
    allowed = unary_union(zones)
    errs = []
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if fp.IsFlipped() or ref.startswith(("H", "STAB_")):
            continue
        cy = courtyard(fp)
        if cy is None:
            errs.append(f"{ref}: no courtyard")
            continue
        out = cy.intersection(pcb).difference(allowed.buffer(ZONE_TOL + ZONE_ALLOW.get(ref, 0.0)))
        if out.area > 1e-4:
            b = out.bounds
            errs.append(f"{ref}: courtyard outside Z_BACK/Z_TRRS by {out.area:.3f} mm2 near ({b[0]:.1f},{b[1]:.1f})")
    return errs


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in ("left", "right"):
        print(__doc__)
        return 2
    side = argv[1]
    net_path = ROOT / "build" / side / f"{side}.net"
    pcb_path = ROOT / "pcb" / side / f"worxboard-{side}.kicad_pcb"
    sch = pcb_path.with_suffix(".kicad_sch")    # the netlist carries an export date: seed from its source
    seed_kiids(side, b"place", side.encode(), sch.read_bytes(), LAYOUT_JSON.read_bytes())
    board = pcbnew.BOARD()
    setup_board(board)
    add_footprints(board, side, net_path)
    add_outline(board, side)
    add_gnd_zones(board, side)
    add_hole_keepouts(board, side)
    add_silk(board, side)
    errs = check_zones(board, side)
    write_rules(pcb_path.with_suffix(".kicad_pro"))
    board.Save(str(pcb_path))
    print(f"wrote {pcb_path.relative_to(ROOT)}: {len(board.GetFootprints())} footprints")
    for e in errs:
        print(f"ZONE: {e}")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
