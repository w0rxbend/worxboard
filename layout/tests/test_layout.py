# SPDX-License-Identifier: GPL-3.0-or-later
"""WS0 acceptance (spec §14): geometry contracts of the layout package."""
from __future__ import annotations

import itertools
import math

import pytest
from shapely.affinity import scale
from shapely.geometry import Point, box

import layout as L
from layout.display import HEADER_PIN_ORDER
from layout.holes import KEEPOUT_D

# Spec §5, copied independently: id -> (x_R, y_R, rot_R, w, h, row, col, left rc, right rc)
SPEC_MAIN = {
    "C0R0": (191.4525, 67.0052, 0, 1.5, 1, 0, 0, (0, 0), (0, 13)),
    "C1R0": (167.6400, 67.0052, 0, 1, 1, 0, 1, (0, 1), (0, 12)),
    "C2R0": (148.5900, 63.82766, 0, 1, 1, 0, 2, (0, 2), (0, 11)),
    "C3R0": (129.5400, 62.23, 0, 1, 1, 0, 3, (0, 3), (0, 10)),
    "C4R0": (110.4900, 63.82766, 0, 1, 1, 0, 4, (0, 4), (0, 9)),
    "C5R0": (91.4400, 65.1002, 0, 1, 1, 0, 5, (0, 5), (0, 8)),
    "C0R1": (191.4525, 86.0527, 0, 1.5, 1, 1, 0, (1, 0), (1, 13)),
    "C1R1": (167.6400, 86.05266, 0, 1, 1, 1, 1, (1, 1), (1, 12)),
    "C2R1": (148.5900, 82.87766, 0, 1, 1, 1, 2, (1, 2), (1, 11)),
    "C3R1": (129.5400, 81.28, 0, 1, 1, 1, 3, (1, 3), (1, 10)),
    "C4R1": (110.4900, 82.87766, 0, 1, 1, 1, 4, (1, 4), (1, 9)),
    "C5R1": (91.4400, 84.14766, 0, 1, 1, 1, 5, (1, 5), (1, 8)),
    "C6R1": (72.3900, 88.91016, 0, 1, 1.5, 1, 6, (1, 6), (1, 7)),
    "C0R2": (191.4525, 105.1027, 0, 1.5, 1, 2, 0, (2, 0), (2, 13)),
    "C1R2": (167.6400, 105.10266, 0, 1, 1, 2, 1, (2, 1), (2, 12)),
    "C2R2": (148.5900, 101.92766, 0, 1, 1, 2, 2, (2, 2), (2, 11)),
    "C3R2": (129.5400, 100.33, 0, 1, 1, 2, 3, (2, 3), (2, 10)),
    "C4R2": (110.4900, 101.92766, 0, 1, 1, 2, 4, (2, 4), (2, 9)),
    "C5R2": (91.4400, 103.19766, 0, 1, 1, 2, 5, (2, 5), (2, 8)),
    "C0R3": (191.4525, 124.1527, 0, 1.5, 1, 3, 0, (3, 0), (3, 13)),
    "C1R3": (167.6400, 124.15266, 0, 1, 1, 3, 1, (3, 1), (3, 12)),
    "C2R3": (148.5900, 120.97766, 0, 1, 1, 3, 2, (3, 2), (3, 11)),
    "C3R3": (129.5400, 119.38, 0, 1, 1, 3, 3, (3, 3), (3, 10)),
    "C4R3": (110.4900, 120.97766, 0, 1, 1, 3, 4, (3, 4), (3, 9)),
    "C5R3": (91.4400, 122.24766, 0, 1, 1, 3, 5, (3, 5), (3, 8)),
    "C6R2": (72.3900, 117.48516, 0, 1, 1.5, 3, 6, (3, 6), (3, 7)),
    "C0R4": (186.6900, 143.2027, 0, 1, 1, 4, 0, (4, 0), (4, 13)),
    "C1R4": (167.6400, 143.20266, 0, 1, 1, 4, 1, (4, 1), (4, 12)),
    "C2R4": (148.5900, 140.02766, 0, 1, 1, 4, 2, (4, 2), (4, 11)),
    "C3R4": (129.5400, 138.43, 0, 1, 1, 4, 3, (4, 3), (4, 10)),
    "C4R4": (110.4900, 140.02766, 0, 1, 1, 4, 4, (4, 4), (4, 9)),
}
SPEC_THUMB_RC = {"T0": ((5, 6), (5, 7)), "T1": ((5, 5), (5, 8)), "T2": ((5, 4), (5, 9)),
                 "T3": ((5, 3), (5, 10)), "T4": ((5, 2), (5, 11)), "T5": ((5, 1), (5, 12))}
SPEC_THUMB_SIZE = {"T0": (1, 1), "T1": (1, 1), "T2": (1, 1), "T3": (1, 1), "T4": (1, 2), "T5": (1, 2)}
# Original ErgoDox PCB (bishboria/ErgoDox "ErgoDOX pcb/ErgoDOX.kicad_pcb") thumb switch centres
ORIGINAL_THUMBS = {"T0": (34.69894, 143.2687), "T1": (51.96332, 135.21944),
                   "T2": (42.7482, 160.53308), "T3": (50.8, 177.8),
                   "T4": (64.03848, 161.11728), "T5": (81.30286, 153.06548)}
# Spec §8.2
SPEC_HOLES = [(53.899, 165.837), (59.665, 121.666), (105.435, 157.759), (201.778, 140.056),
              (139.040, 91.592), (201.143, 37.135), (118.212, 37.135), (88.000, 37.135)]
# Spec §8.1
SPEC_OUTLINE = [(62.275, 30.6), (202.7428, 30.6), (205.9178, 33.775), (205.9178, 143.383),
                (196.3928, 152.908), (127.1524, 152.908), (48.9839, 189.35192),
                (44.76496, 187.81776), (23.08098, 141.31544), (24.61768, 137.0965),
                (49.0, 125.7267), (49.0, 88.0), (59.1, 88.0), (59.1, 33.775)]

KEY_TOL = 1e-4
THUMB_TOL = 0.002
MIRROR_TOL = 1e-6
AREA_TOL = 1e-6
HOUSING_EDGE = 0.4       # every switch housing at least this far inside the PCB edge
CHAMFER_KEYS = {"T0", "T3"}   # see docs/deviations.md (WS0)
CAP_OVERHANG = 2.0
WINDOW_WELL_GAP = 1.0


def by_id(side):
    return {k.id: k for k in L.keys(side)}


def mirror(g):
    return scale(g, xfact=-1, yfact=1, origin=(L.MIRROR_X / 2, 0))


# -------------------------------------------------------------- keys
def test_key_counts():
    assert [len(L.keys(s)) for s in L.SIDES] == [37, 37]
    assert len(L.transform_order()) == 74
    rows = [sum(1 for _, _, rc in L.transform_order() if rc[0] == r) for r in range(6)]
    assert rows == [12, 14, 12, 14, 10, 12]
    assert "C6R0" not in by_id("right")


def test_main_keys_equal_spec():
    keys = by_id("right")
    for kid, (x, y, rot, w, h, row, col, lrc, rrc) in SPEC_MAIN.items():
        k = keys[kid]
        assert abs(k.x - x) <= KEY_TOL and abs(k.y - y) <= KEY_TOL and k.rot == rot, kid
        assert (k.w, k.h, k.row, k.col) == (w, h, row, col), kid
        assert k.rc("left") == lrc and k.rc("right") == rrc, kid


def test_thumbs_equal_original_pcb():
    keys = by_id("right")
    for kid, (x, y) in ORIGINAL_THUMBS.items():
        k = keys[kid]
        assert abs(k.x - x) <= THUMB_TOL and abs(k.y - y) <= THUMB_TOL, kid
        assert k.rot == 25 and (k.w, k.h) == SPEC_THUMB_SIZE[kid]
        assert (k.rc("left"), k.rc("right")) == SPEC_THUMB_RC[kid]


def test_rc_unique_and_unused_slots():
    for s in L.SIDES:
        local = {(k.row, k.col) for k in L.keys(s)}
        assert len(local) == 37
        assert not local & {(0, 6), (2, 6), (4, 5), (4, 6), (5, 0)}


def test_no_housing_overlaps():
    for s in L.SIDES:
        hs = [L.housing(k) for k in L.keys(s)]
        for a, b in itertools.combinations(hs, 2):
            assert a.distance(b) > 0


def test_stabilisers_on_2u_thumbs():
    k = by_id("right")["T4"]
    a, b = L.stab_holes(k)
    assert math.dist(a, b) == pytest.approx(2 * 11.938)
    assert math.dist(a, (k.x, k.y)) == pytest.approx(11.938)


# -------------------------------------------------------------- display, holes, jacks
def test_display_clearances():
    for s in L.SIDES:
        d = L.display(s)
        disp = box(*d["module"])
        assert min(disp.distance(L.housing(k)) for k in L.keys(s)) >= 4.0
        assert min(disp.distance(Point(p).buffer(KEEPOUT_D / 2)) for p in L.holes(s)) >= 1.0
        assert box(*d["pocket"]).contains(box(*d["window"]))
        assert disp.contains(box(*d["window"]))
        assert L.outline(s).contains(disp)


def test_window_clear_of_key_well():
    """Window stays WINDOW_WELL_GAP clear of the C6R1 key well (cell + 0.6) in the top skin."""
    for s in L.SIDES:
        well = L.cell(by_id(s)["C6R1"], 0.6)
        assert box(*L.display(s)["window"]).distance(well) >= WINDOW_WELL_GAP - 1e-9


def test_display_geometry_right():
    d = L.display("right")
    assert d["module"] == pytest.approx((65.39, 38.625, 79.39, 74.625), abs=1e-3)
    assert d["pocket"] == pytest.approx((64.89, 38.125, 79.89, 75.125), abs=1e-3)
    assert d["header"] == pytest.approx((72.39, 40.6))
    assert len(d["header_pins"]) == len(HEADER_PIN_ORDER) == 5


def test_header_pin1_not_mirrored():
    """The module is one physical part: pin 1 is at low x on both halves."""
    for s in L.SIDES:
        xs = [p[0] for p in L.display(s)["header_pins"]]
        assert xs == sorted(xs)


def test_holes_equal_spec():
    for got, want in zip(L.holes("right"), SPEC_HOLES, strict=True):
        assert got == pytest.approx(want, abs=6e-4)


def test_usb_clear_of_boss5():
    for s in L.SIDES:
        j1 = next(j for j in L.jacks(s) if j.ref == "J1")
        boss5 = Point(L.holes(s)[5]).buffer(KEEPOUT_D / 2)
        assert box(*j1.body).distance(boss5) >= 2.0
    assert L.anchors("right")["J1"] == pytest.approx((186.0, 30.6))
    assert L.anchors("left")["J1"] == pytest.approx((74.0, 30.6))


def test_j2_inside_z_trrs():
    for s in L.SIDES:
        j2 = next(j for j in L.jacks(s) if j.ref == "J2")
        assert L.zones(s)["Z_TRRS"].contains(box(*j2.body))
        assert j2.y == 103.0
        assert j2.facing == ((-1.0, 0.0) if s == "right" else (1.0, 0.0))


def test_back_parts_inside_z_back():
    for s in L.SIDES:
        zb = L.zones(s)["Z_BACK"]
        for ref in ("J1", "J3", "U1", "U2", "SW_BOOT", "SW_RST"):
            assert zb.contains(box(*L.part_rect(s, ref))), (s, ref)


# -------------------------------------------------------------- outline and zones
def test_outline_valid_simple_contains_cells():
    for s in L.SIDES:
        o = L.outline(s)
        assert o.is_valid and o.exterior.is_simple and not o.interiors
        for k in L.keys(s):
            assert o.buffer(-HOUSING_EDGE).contains(L.housing(k)), (s, k.id)
            if k.id in CHAMFER_KEYS:   # keycap corner overhangs the original thumb chamfer
                assert o.buffer(CAP_OVERHANG).contains(L.cell(k)), (s, k.id)
                assert not o.contains(L.cell(k)), (s, k.id)
            else:
                assert o.contains(L.cell(k)), (s, k.id)


def test_outline_vertices_equal_spec():
    assert [(x, y) for x, y, _ in L.outline_vertices("right")] == SPEC_OUTLINE
    radii = {(x, y): r for x, y, r in L.outline_vertices("right") if r}
    assert radii == {(49.0, 88.0): 4.0, (59.1, 88.0): 4.0}


def test_zones_inside_pcb_and_clear_of_cells():
    for s in L.SIDES:
        o = L.outline(s)
        for z in L.zones(s).values():
            assert not z.is_empty and z.is_valid
            assert z.difference(o).area < AREA_TOL
            for k in L.keys(s):
                assert z.intersection(L.cell(k, 0.6)).area < AREA_TOL


# -------------------------------------------------------------- mirror
def test_left_is_mirror_of_right():
    left, right = by_id("left"), by_id("right")
    for kid, r in right.items():
        lk = left[kid]
        assert lk.x == pytest.approx(L.MIRROR_X - r.x, abs=MIRROR_TOL)
        assert (lk.y, lk.rot, lk.w, lk.h, lk.row, lk.col) == (r.y, -r.rot, r.w, r.h, r.row, r.col)
        assert L.cell(lk).symmetric_difference(mirror(L.cell(r))).area < AREA_TOL
    for a, b in zip(L.holes("left"), L.holes("right")):
        assert a == pytest.approx((L.MIRROR_X - b[0], b[1]))
    assert L.outline("left").symmetric_difference(mirror(L.outline("right"))).area < AREA_TOL
    for name, zr in L.zones("right").items():
        assert L.zones("left")[name].symmetric_difference(mirror(zr)).area < AREA_TOL
    for name in ("module", "pocket", "window"):
        assert box(*L.display("left")[name]).symmetric_difference(
            mirror(box(*L.display("right")[name]))).area < AREA_TOL


def test_left_outline_runs_in_reverse():
    r = [(x, y) for x, y, _ in L.outline_vertices("right")]
    l_ = [(x, y) for x, y, _ in L.outline_vertices("left")]
    assert l_ == [(L.MIRROR_X - x, y) for x, y in r][::-1]
    assert L.outline("left").exterior.is_ccw == L.outline("right").exterior.is_ccw


def test_bad_side_rejected():
    with pytest.raises(ValueError):
        L.keys("middle")
