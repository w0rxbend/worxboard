# SPDX-License-Identifier: GPL-3.0-or-later
"""Overlay drawings for cpl_check.py: JLC's footprint, placed from the CPL, over the KiCad pads.

One SVG per JLC footprint (part type), one tile per distinct board / side / CPL rotation, written as
cpl-<part type>.svg (docs/images). Board frame, seen from the top: bottom-side parts appear mirrored,
as they lie on the board. Called by `cpl_check.py --svg DIR`; output is deterministic.
"""
from __future__ import annotations

import math
import re
from pathlib import Path

from shapely.affinity import affine_transform
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

TILE_W, TILE_H, HEAD = 340, 300, 46
COLS = 3
MAX_TILES = 6
# JLC package -> file name and a caption
NAMES = [
    (r"^LQFN-56", "u1-rp2040-qfn56", "U1 RP2040, QFN-56 (C2040)"),
    (r"^SOIC-8", "u2-flash-soic8", "U2 flash, SOIC-8 208 mil"),
    (r"^SOT-25-5", "u3-ldo-sot23-5", "U3 AP2112K, SOT-23-5"),
    (r"^SOT-23-6", "u4-u5-esd-sot23-6", "U4, U5 USBLC6-2SC6, SOT-23-6"),
    (r"^CRYSTAL", "y1-crystal-3225", "Y1 12 MHz crystal, 3225"),
    (r"^USB-C", "j1-usb-c", "J1 USB-C, HRO TYPE-C-31-M-12 (C165948)"),
    (r"PJ-320D", "j2-trrs-pj320d", "J2 TRRS jack, PJ-320D (C95562)"),
    (r"^HDR-TH_5P", "j3-display-socket", "J3 display socket, 1x5 2.54 mm THT"),
    (r"KEYBOARD-SW|CPG151101S11", "sk-hotswap-socket", "SK101-SK137 MX hot-swap socket (B.Cu)"),
    (r"^SOD-123F", "d101-diode-sod123f", "D101-D137 1N4148W, SOD-123F (B.Cu)"),
    (r"^SOD-123", "d1-schottky-sod123", "D1 B5819W, SOD-123"),
    (r"^SW-SMD", "sw-tact-ts1088", "SW1, SW2 TS-1088"),
    (r"^F1206", "f1-ptc-1206", "F1 PTC fuse, 1206"),
    (r"^R0402", "r-0402", "Resistors, 0402"),
    (r"^C0402", "c-0402", "Capacitors, 0402"),
]
COL = {"edge": "#b8860b", "kcu": "#c8c8c8", "kcu_edge": "#4d4d4d", "hole": "#ffffff", "hole_edge": "#1a1a1a",
       "jpad": "#d62728", "lead": "#1f77b4", "body": "#2ca02c", "text": "#1a1a1a", "bg": "#ffffff"}


def name_of(package: str) -> tuple[str, str]:
    for pat, slug, cap in NAMES:
        if re.search(pat, package):
            return slug, cap
    slug = re.sub(r"[^a-z0-9]+", "-", package.lower()).strip("-")
    return slug, package


def f(v: float) -> str:
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def path(geom, to) -> str:
    """Polygon / MultiPolygon -> SVG path data in tile pixels."""
    polys = [geom] if geom.geom_type == "Polygon" else list(getattr(geom, "geoms", []))
    out = []
    for p in polys:
        if p.is_empty or p.geom_type != "Polygon":
            continue
        for ring in [p.exterior, *p.interiors]:
            pts = [to(x, y) for x, y in ring.coords]
            out.append("M" + " L".join(f"{f(x)} {f(y)}" for x, y in pts) + " Z")
    return " ".join(out)


def tile(res, k, fp, edge, label: str, ox: float, oy: float) -> list[str]:
    A = res.placement.matrix()
    jpads = [affine_transform(Polygon(q["poly"]), A) for q in fp["pads"]]
    leads = [affine_transform(Polygon(lp), A) for lp in fp["leads"]]
    cut = unary_union([Polygon(c) for c in fp["lead_cutouts"]]) if fp["lead_cutouts"] else None
    if cut is not None:
        cut = affine_transform(cut, A)
        leads = [lp.difference(cut) for lp in leads]
    body = affine_transform(unary_union([Polygon(b).buffer(0) for b in fp["body"]]), A) if fp["body"] else None
    jholes = [Point(res.placement.point(h["at"])).buffer(h["d"] / 2, 24) for h in fp["holes"]]
    kcu = [p.copper for p in k.pads if p.copper is not None]
    kho = [p.hole for p in k.pads if p.hole is not None]
    allg = unary_union(kcu + kho + jpads + ([body] if body is not None else []))
    x0, y0, x1, y1 = allg.bounds
    pad_mm = 0.6
    x0, y0, x1, y1 = x0 - pad_mm, y0 - pad_mm, x1 + pad_mm, y1 + pad_mm
    w, h = TILE_W - 16, TILE_H - 16 - 34
    sc = min(w / (x1 - x0), h / (y1 - y0))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2

    def to(x, y):
        return (ox + 8 + w / 2 + (x - cx) * sc, oy + 8 + h / 2 + (y - cy) * sc)
    sw = max(0.6, min(1.5, sc * 0.03))
    g = [f'<rect x="{f(ox + 2)}" y="{f(oy + 2)}" width="{TILE_W - 4}" height="{TILE_H - 4}" fill="none" '
         f'stroke="#dddddd"/>']
    window = box(x0, y0, x1, y1)
    if edge is not None and not edge.is_empty:
        cut = window.difference(edge)            # off-board part of the tile
        if not cut.is_empty:
            g.append(f'<path d="{path(cut, to)}" fill="{COL["edge"]}" fill-opacity="0.18" stroke="none"/>')
        line = edge.boundary.intersection(window)
        segs = [line] if line.geom_type == "LineString" else list(getattr(line, "geoms", []))
        for sg in segs:
            if sg.geom_type == "LineString" and len(sg.coords) > 1:
                pts = [to(x, y) for x, y in sg.coords]
                g.append(f'<path d="M{" L".join(f"{f(x)} {f(y)}" for x, y in pts)}" fill="none" '
                         f'stroke="{COL["edge"]}" stroke-width="2"/>')
    for p in kcu:
        g.append(f'<path d="{path(p, to)}" fill="{COL["kcu"]}" stroke="{COL["kcu_edge"]}" stroke-width="{f(sw)}"/>')
    for p in kho:
        g.append(f'<path d="{path(p, to)}" fill="{COL["hole"]}" stroke="{COL["hole_edge"]}" stroke-width="{f(sw)}"/>')
    if body is not None:
        g.append(f'<path d="{path(body, to)}" fill="{COL["body"]}" fill-opacity="0.12" stroke="{COL["body"]}" '
                 f'stroke-width="{f(sw * 1.4)}"/>')
    for p in leads:
        g.append(f'<path d="{path(p, to)}" fill="{COL["lead"]}" fill-opacity="0.65" stroke="none"/>')
    for p in jpads:
        g.append(f'<path d="{path(p, to)}" fill="none" stroke="{COL["jpad"]}" stroke-width="{f(sw * 1.2)}"/>')
    for p in jholes:
        g.append(f'<path d="{path(p, to)}" fill="none" stroke="{COL["lead"]}" stroke-width="{f(sw * 1.2)}" '
                 f'stroke-dasharray="3 2"/>')
    # pin 1: KiCad pad 1 (black cross) under JLC pin 1 (red ring)
    k1 = next((p for p in k.pads if p.num == "1" and p.copper is not None), None)
    j1 = next((q for q in fp["pads"] if q["num"] == "1"), None)
    r = max(4.0, sc * 0.25)
    if k1 is not None:
        x, y = to(*k1.at)
        g.append(f'<path d="M{f(x - r)} {f(y)} L{f(x + r)} {f(y)} M{f(x)} {f(y - r)} L{f(x)} {f(y + r)}" '
                 f'stroke="{COL["text"]}" stroke-width="1.5"/>')
    if j1 is not None:
        x, y = to(*res.placement.point(j1["at"]))
        g.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r)}" fill="none" stroke="{COL["jpad"]}" stroke-width="2"/>')
    side = "B.Cu, seen from top" if res.bottom else "F.Cu"
    stats = f"place {res.place_err:.3f} mm · terminals {res.lead_min_area:.0%} on pad"
    if res.post_clear is not None:
        stats += f" · post clear {res.post_clear:.2f}"
    ty = oy + TILE_H - 30
    g.append(f'<text x="{f(ox + 8)}" y="{f(ty)}" font-size="12" font-weight="bold">{label} {res.ref} · '
             f'{side} · CPL {res.rot:g}°</text>')
    g.append(f'<text x="{f(ox + 8)}" y="{f(ty + 15)}" font-size="11">{stats}'
             f'{" · FAIL" if res.errors else ""}</text>')
    return g


def write_all(out: Path, tiles, fps) -> list[str]:
    """tiles: [(board label, [Result], {ref: KFoot}, board outline)] -> written file names."""
    out.mkdir(parents=True, exist_ok=True)
    groups: dict[str, list] = {}
    for label, results, board, edge in tiles:
        side = next((s for s in ("left", "right") if s in label), label)
        for res in results:
            groups.setdefault(res.package, []).append((side, res, board[res.ref], edge))
    written = []
    for package, items in sorted(groups.items()):
        slug, cap = name_of(package)
        seen, pick = set(), []
        for side, res, k, edge in sorted(items, key=lambda t: (t[0], t[1].bottom, round(t[1].rot % 360, 2),
                                                                len(t[1].ref), t[1].ref)):
            key = (side, res.bottom, round(res.rot % 360, 2))
            if key not in seen:
                seen.add(key)
                pick.append((side, res, k, edge))
        # keep both sides represented when trimming
        pick = (pick[:MAX_TILES] if len(pick) <= MAX_TILES else
                [p for p in pick if p[0] == "left"][:MAX_TILES // 2] + [p for p in pick if p[0] != "left"][:MAX_TILES // 2])
        rows = math.ceil(len(pick) / COLS)
        W, H = TILE_W * COLS, HEAD + TILE_H * rows
        lcscs = sorted({res.lcsc for _, res, _, _ in items})
        n = len(items)
        body = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
                f'font-family="DejaVu Sans, Arial, sans-serif" fill="{COL["text"]}">',
                f'<rect width="{W}" height="{H}" fill="{COL["bg"]}"/>',
                f'<text x="8" y="18" font-size="14" font-weight="bold">{cap} · JLC footprint {package} '
                f'({", ".join(lcscs)}) · {n} placed, {n - sum(1 for _, r, _, _ in items if r.errors)} pass</text>',
                f'<text x="8" y="36" font-size="11"><tspan fill="{COL["kcu_edge"]}">grey: KiCad copper</tspan>, '
                f'white: KiCad holes, <tspan fill="{COL["jpad"]}">red: JLC pads</tspan>, '
                f'<tspan fill="{COL["lead"]}">blue: part terminals / pegs</tspan>, '
                f'<tspan fill="{COL["body"]}">green: part body</tspan>, '
                f'<tspan fill="{COL["edge"]}">gold: board edge</tspan>; '
                f'red ring = JLC pin 1, cross = KiCad pad 1</text>']
        for i, (side, res, k, edge) in enumerate(pick):
            fp = fps[res.lcsc]
            body += tile(res, k, fp, edge, side.upper(), TILE_W * (i % COLS), HEAD + TILE_H * (i // COLS))
        body.append("</svg>")
        name = f"cpl-{slug}.svg"
        (out / name).write_text("\n".join(body) + "\n")
        written.append(name)
    return written
