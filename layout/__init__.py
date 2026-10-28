# SPDX-License-Identifier: GPL-3.0-or-later
"""worxboard layout: the single source of truth for both halves.

Data lives in the right-half KiCad frame (mm, +x outward, +y towards the user,
rotation CCW on screen). The left half is x_L = MIRROR_X - x_R, y_L = y_R,
rot_L = -rot_R, with polygon vertex order reversed.

Consumers (pcb/, case/, firmware/, site/) import this package or read
layout/build/layout.json, which `python -m layout.export` writes.
"""
from __future__ import annotations

from dataclasses import replace

from shapely.geometry import MultiPolygon, Point, Polygon, box
from shapely.ops import unary_union

from . import display as _display
from . import holes as _holes
from . import outline as _outline
from . import zones as _zones
from .jacks import JACKS, Jack
from .keys import MAIN_KEYS, PITCH, Key, cell, housing
from .thumbs import THUMB_KEYS, stab_holes

__all__ = ["MIRROR_X", "PITCH", "SIDES", "Key", "Jack", "keys", "display", "jacks", "holes",
           "anchors", "outline", "outline_vertices", "outline_segments", "zones",
           "transform_order", "cell", "housing", "stab_holes"]

MIRROR_X = 260.0
SIDES = ("left", "right")
KEYS_PER_HALF = 37

Rect = tuple[float, float, float, float]


def _check(side: str) -> None:
    if side not in SIDES:
        raise ValueError(f"side must be one of {SIDES}, got {side!r}")


def mx(side: str, x: float) -> float:
    """x in the given side's frame."""
    return x if side == "right" else MIRROR_X - x


def _pt(side: str, p: tuple[float, float]) -> tuple[float, float]:
    return (mx(side, p[0]), p[1])


def _rect(side: str, r: Rect) -> Rect:
    x0, x1 = sorted((mx(side, r[0]), mx(side, r[2])))
    return (x0, r[1], x1, r[3])


def keys(side: str) -> list[Key]:
    """The 37 switches of one half: main block, then thumbs T0..T5."""
    _check(side)
    return [replace(k, x=mx(side, k.x), rot=k.rot if side == "right" else -k.rot)
            for k in (*MAIN_KEYS, *THUMB_KEYS)]


def display(side: str) -> dict[str, Rect | tuple[float, float] | list]:
    """Module, case pocket and viewing-window rectangles, and the J3 header."""
    _check(side)
    d = _display
    pins = sorted(_pt(side, p) for p in d.header_pins())   # pin 1 at low x on BOTH halves
    return {"module": _rect(side, d.MODULE_RECT), "pocket": _rect(side, d.POCKET_RECT),
            "window": _rect(side, d.WINDOW_RECT), "window_centre": _pt(side, d.WINDOW_CENTRE),
            "header": _pt(side, d.HEADER), "header_pins": pins}


def jacks(side: str) -> list[Jack]:
    _check(side)
    return [replace(j, x=mx(side, j.x), facing=(j.facing[0] if side == "right" else -j.facing[0],
                                                j.facing[1]), body=_rect(side, j.body))
            for j in JACKS]


def holes(side: str) -> list[tuple[float, float]]:
    _check(side)
    return [_pt(side, p) for p in _holes.HOLES]


def anchors(side: str) -> dict[str, tuple[float, float]]:
    """Top-side part centres (connectors at their mouth)."""
    _check(side)
    a = {j.ref: (j.x, j.y) for j in jacks(side)}
    a["J3"] = _pt(side, _display.HEADER)
    a.update({ref: _pt(side, p) for ref, p in _zones.PART_ANCHORS.items()})
    return a


def outline_vertices(side: str) -> list[tuple[float, float, float]]:
    """(x, y, fillet r) in drawing order; the left half runs in reverse."""
    _check(side)
    v = [(mx(side, x), y, r) for x, y, r in _outline.VERTICES]
    return v if side == "right" else v[::-1]


def outline_segments(side: str) -> list[dict]:
    return _outline.segments(outline_vertices(side))


def outline(side: str) -> Polygon:
    return _outline.polygon(outline_segments(side))


def _cells(side: str, grow: float):
    return unary_union([cell(k, grow) for k in keys(side)])


def _keepouts(side: str):
    return unary_union([Point(p).buffer(_holes.KEEPOUT_D / 2) for p in holes(side)])


def zones(side: str) -> dict[str, Polygon | MultiPolygon]:
    """Z_BACK and Z_TRRS: PCB areas free for top-side parts."""
    _check(side)
    z = _zones
    pcb = outline(side)
    lo, hi = -1e3, 1e3
    back = box(lo, lo, hi, z.BACK_Y)
    trrs = _rect(side, (lo, z.TRRS_Y0, z.TRRS_X, z.TRRS_Y1))
    blocked = unary_union([_cells(side, z.CELL_GROW), _keepouts(side)])
    return {"Z_BACK": pcb.intersection(back).difference(blocked),
            "Z_TRRS": pcb.intersection(box(*trrs)).difference(blocked)}


def part_rect(side: str, ref: str) -> Rect:
    """Axis-aligned body of a zoned part (J1/J2 bodies, J3 header, MCU cluster)."""
    for j in jacks(side):
        if j.ref == ref:
            return j.body
    if ref == "J3":
        (x0, y), (x1, _) = display(side)["header_pins"][0], display(side)["header_pins"][-1]
        h = _display.HEADER_COURTYARD
        return (x0 - h / 2, y - h / 2, x1 + h / 2, y + h / 2)
    x, y = anchors(side)[ref]
    w, h = _zones.PART_BODIES[ref]
    return (x - w / 2, y - h / 2, x + w / 2, y + h / 2)


# Global ZMK order (spec §5 order rule): rows 0-4 left then right, then the thumbs
THUMB_ORDER = [(5, 5), (5, 6), (5, 7), (5, 8), (5, 4), (5, 9),
               (5, 1), (5, 2), (5, 3), (5, 10), (5, 11), (5, 12)]


def transform_order() -> list[tuple[str, str, tuple[int, int]]]:
    """(side, key id, global rc) in keymap / transform / physical-layout order."""
    by_rc = {k.rc(s): (s, k.id, k.rc(s)) for s in SIDES for k in keys(s)}
    main = sorted((rc for rc in by_rc if rc[0] < 5))
    order = [by_rc[rc] for rc in main] + [by_rc[rc] for rc in THUMB_ORDER]
    assert len(order) == len(by_rc) == 2 * KEYS_PER_HALF
    return order
