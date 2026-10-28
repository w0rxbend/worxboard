# SPDX-License-Identifier: GPL-3.0-or-later
"""Write the layout contracts: layout/build/layout.json, docs/images/layout.svg, build/kle.json.

    python -m layout.export            # write all three
    python -m layout.export --check    # exit 1 if a committed file is stale
"""
from __future__ import annotations

import json
import sys
from html import escape
from pathlib import Path

from shapely.geometry import MultiPolygon, Polygon

import layout as L
from layout import pins as P
from layout.zones import BACK_Y, CELL_GROW, TRRS_X, TRRS_Y0, TRRS_Y1, Y1_MAX_FROM_U1
from layout.display import (HEADER_PIN_ORDER, MODULE, WINDOW_CHAMFER, WINDOW_R, Z_PCB_TOP,
                            Z_POCKET_TOP)
from layout.holes import HOLE_D, KEEPOUT_D
from layout.keys import HOUSING

ROOT = Path(__file__).resolve().parent.parent
LAYOUT_JSON = ROOT / "layout/build/layout.json"
LAYOUT_SVG = ROOT / "docs/images/layout.svg"
KLE_JSON = ROOT / "build/kle.json"
COMMITTED = (LAYOUT_JSON, LAYOUT_SVG)

SCHEMA = 1
NDIGITS = 4              # mm, enough for the 1e-4 key check
SPLIT_GAP = 30.0         # preview: right half placed this far right of the left half
SVG_MARGIN = 8.0
SVG_SCALE = 4.0          # px per mm


def _r(v):
    """Round floats recursively; -0.0 -> 0.0 so output is stable."""
    if isinstance(v, float):
        return round(v, NDIGITS) + 0.0
    if isinstance(v, dict):
        return {k: _r(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_r(x) for x in v]
    return v


def _polys(g) -> list[Polygon]:
    return list(g.geoms) if isinstance(g, MultiPolygon) else [g]


def _poly_json(g) -> list[dict]:
    return [{"exterior": list(p.exterior.coords)[:-1],
             "holes": [list(i.coords)[:-1] for i in p.interiors]} for p in _polys(g)]


def _key_json(k: L.Key, side: str) -> dict:
    d = {"id": k.id, "x": k.x, "y": k.y, "rot": k.rot, "w": k.w, "h": k.h,
         "row": k.row, "col": k.col, "rc": k.rc(side),
         "legend": k.legend_left if side == "left" else k.legend_right}
    if k.h == 2:
        d["stabs"] = L.stab_holes(k)
    return d


def _jack_json(j: L.Jack) -> dict:
    return {"ref": j.ref, "footprint": j.footprint, "x": j.x, "y": j.y, "facing": j.facing,
            "body": j.body, "axis_z": j.axis_z, "height": j.height}


def _side_json(side: str) -> dict:
    return {
        "keys": [_key_json(k, side) for k in L.keys(side)],
        "display": L.display(side),
        "jacks": [_jack_json(j) for j in L.jacks(side)],
        "anchors": L.anchors(side),
        "holes": L.holes(side),
        "outline": {"vertices": L.outline_vertices(side), "segments": L.outline_segments(side)},
        "zones": {name: _poly_json(g) for name, g in L.zones(side).items()},
    }


def layout_dict() -> dict:
    return _r({
        "schema": SCHEMA,
        "generator": "python -m layout.export",
        "units": "mm",
        "frame": "KiCad; +x outward on the right half, +y towards the user, rot CCW on screen",
        "mirror_x": L.MIRROR_X,
        "pitch": L.PITCH,
        "housing": HOUSING,
        "hole": {"drill": HOLE_D, "keepout": KEEPOUT_D},
        "display_part": {"module": MODULE, "window_r": WINDOW_R, "window_chamfer": WINDOW_CHAMFER,
                         "pocket_z": [Z_PCB_TOP, Z_POCKET_TOP], "header_pin_order": HEADER_PIN_ORDER},
        "zone_rules": {"cell_grow": CELL_GROW, "Z_BACK": {"y_max": BACK_Y},
                       "Z_TRRS": {"x_max_right": TRRS_X, "y": [TRRS_Y0, TRRS_Y1]},
                       "y1_max_from_u1": Y1_MAX_FROM_U1},
        "transform_order": [{"side": s, "id": i, "rc": rc} for s, i, rc in L.transform_order()],
        "pins": {
            "gpio": [{"name": p.name, "qfn": p.qfn, "net": p.net, "note": p.note} for p in P.PINS],
            "rows": P.ROW_GPIOS, "cols": P.COL_GPIOS, "right_cols": P.RIGHT_COL_GPIOS,
            "uart": {"tx": P.UART_TX, "rx": P.UART_RX, "baud": P.UART_BAUD},
            "trrs": P.TRRS,
        },
        "sides": {s: _side_json(s) for s in L.SIDES},
    })


def layout_json() -> str:
    return json.dumps(layout_dict(), indent=1, ensure_ascii=False) + "\n"


# ---------------------------------------------------------------- KLE
def kle_json() -> str:
    """keyboard-layout-editor.com JSON: one row per key, rotated about its own centre."""
    rows: list = [{"name": "worxboard", "author": "w0rxbend"}]
    dx = _split_offset()
    for s, kid, _ in L.transform_order():
        k = next(k for k in L.keys(s) if k.id == kid)
        cx = (k.x + (dx if s == "right" else 0.0)) / L.PITCH
        cy = k.y / L.PITCH
        props = {"r": -k.rot, "rx": cx, "ry": cy, "x": -k.w / 2, "y": -k.h / 2}
        if k.w != 1:
            props["w"] = k.w
        if k.h != 1:
            props["h"] = k.h
        rows.append([_r(props), k.legend_left if s == "left" else k.legend_right])
    return json.dumps(rows, ensure_ascii=False) + "\n"


# ---------------------------------------------------------------- SVG
def _split_offset() -> float:
    lx = L.outline("left").bounds[2]
    rx = L.outline("right").bounds[0]
    return lx - rx + SPLIT_GAP


def _path(poly: Polygon, dx: float) -> str:
    def ring(c):
        return "M" + " L".join(f"{x + dx:.3f},{y:.3f}" for x, y in list(c)[:-1]) + " Z"
    return " ".join([ring(poly.exterior.coords), *(ring(i.coords) for i in poly.interiors)])


def _rect_svg(r, dx: float, cls: str, rx: float = 0.0) -> str:
    x0, y0, x1, y1 = r
    return (f'<rect class="{cls}" x="{x0 + dx:.3f}" y="{y0:.3f}" width="{x1 - x0:.3f}" '
            f'height="{y1 - y0:.3f}" rx="{rx}"/>')


def layout_svg() -> str:
    dx_r = _split_offset()
    x0 = L.outline("left").bounds[0] - SVG_MARGIN
    y0 = min(L.outline(s).bounds[1] for s in L.SIDES) - SVG_MARGIN
    x1 = L.outline("right").bounds[2] + dx_r + SVG_MARGIN
    y1 = max(L.outline(s).bounds[3] for s in L.SIDES) + SVG_MARGIN
    w, h = x1 - x0, y1 - y0
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0:.3f} {y0:.3f} {w:.3f} {h:.3f}" '
        f'width="{w * SVG_SCALE:.0f}" height="{h * SVG_SCALE:.0f}" font-family="sans-serif">',
        "<title>worxboard rev A layout (generated by layout/export.py)</title>",
        "<style>.bg{fill:#fff}.pcb{fill:#1f6f4a;stroke:#0b3d27;stroke-width:.4}"
        ".zone{fill:#f5c542;opacity:.45}.cap{fill:#eef1f4;stroke:#55606b;stroke-width:.3}"
        ".hsg{fill:none;stroke:#9aa5b1;stroke-width:.2;stroke-dasharray:1 .6}"
        ".disp{fill:#2b2f36;stroke:#111;stroke-width:.3}.win{fill:#b9d4c9}"
        ".hole{fill:#fff;stroke:#c0c6cc;stroke-width:.3}.jack{fill:#c0c6cc;stroke:#333;stroke-width:.3}"
        ".part{fill:#3a3f47}</style>",
        f'<rect class="bg" x="{x0:.3f}" y="{y0:.3f}" width="{w:.3f}" height="{h:.3f}"/>',
    ]
    for s in L.SIDES:
        dx = dx_r if s == "right" else 0.0
        o = L.outline(s)
        out.append(f'<g id="{s}">')
        out.append(f'<path class="pcb" d="{_path(o, dx)}"/>')
        for g in L.zones(s).values():
            out += [f'<path class="zone" fill-rule="evenodd" d="{_path(p, dx)}"/>' for p in _polys(g)]
        for k in L.keys(s):
            out.append(f'<path class="cap" d="{_path(L.cell(k, -0.5), dx)}"/>')
            out.append(f'<path class="hsg" d="{_path(L.housing(k), dx)}"/>')
            legend = k.legend_left if s == "left" else k.legend_right
            out.append(f'<text font-size="2.6" fill="#222" text-anchor="middle" x="{k.x + dx:.3f}" y="{k.y + 0.9:.3f}" '
                       f'transform="rotate({-k.rot:g} {k.x + dx:.3f} {k.y:.3f})">{escape(legend)}</text>')
        d = L.display(s)
        out.append(_rect_svg(d["module"], dx, "disp", 1.0))
        out.append(_rect_svg(d["window"], dx, "win", WINDOW_R))
        for ref in ("U1", "U2", "SW_BOOT", "SW_RST", "J3"):
            out.append(_rect_svg(L.part_rect(s, ref), dx, "part", 0.3))
        for j in L.jacks(s):
            out.append(_rect_svg(j.body, dx, "jack", 0.5))
        for x, y in L.holes(s):
            out.append(f'<circle class="hole" cx="{x + dx:.3f}" cy="{y:.3f}" r="{KEEPOUT_D / 2}"/>')
        cx = (o.bounds[0] + o.bounds[2]) / 2 + dx
        out.append(f'<text font-size="6" fill="#222" text-anchor="middle" x="{cx:.3f}" y="{o.bounds[1] - 2:.3f}">{s.upper()}</text>')
        out.append("</g>")
    out.append("</svg>")
    return "\n".join(out) + "\n"


def outputs() -> dict[Path, str]:
    return {LAYOUT_JSON: layout_json(), LAYOUT_SVG: layout_svg(), KLE_JSON: kle_json()}


def main(argv: list[str]) -> int:
    files = outputs()
    if "--check" in argv:
        stale = [p for p in COMMITTED if not p.exists() or p.read_text() != files[p]]
        for p in stale:
            print(f"stale: {p.relative_to(ROOT)} (run `just layout`)", file=sys.stderr)
        return 1 if stale else 0
    for p, text in files.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        print(f"wrote {p.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
