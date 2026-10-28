# SPDX-License-Identifier: GPL-3.0-or-later
"""Fit check of the case against the PCB (spec §10.10).

For each half it loads the PCB STEP from WS2 (build/<side>/worxboard-<side>.step, board plus
3D models) and requires 0 mm3 of interference with the top, bottom and spacer parts. Until that
file exists it falls back to envelopes from `layout` (board slab, the anchored top-side parts,
the component zones and the bottom-side socket area), prints a warning and still fails on any
interference.

Usage: check_fit.py <exports_dir> [side ...]      (run worxboard_case.py first)
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import worxboard_case as E  # noqa: E402
import layout as L  # noqa: E402
from build123d import Pos, Solid, import_step  # noqa: E402
from shapely.geometry import Point, Polygon, box  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

PCB_STEP = os.path.join(E.ROOT, "build", "{side}", "worxboard-{side}.step")
MAX_INTERFERENCE = 1e-3  # mm3 ("0 mm3" up to boolean noise)
SIZE_TOL = 0.3           # STEP board bbox vs layout outline bbox (mm)
# Envelope heights above the PCB top (fallback), mm
PART_H = {"J1": L.jacks("right")[0].height, "J2": L.jacks("right")[1].height,
          "U1": 1.0, "U2": 2.2, "SW_BOOT": 2.0, "SW_RST": 2.0}
ZONE_H = 1.2             # passives anywhere in Z_BACK / Z_TRRS
DISPLAY_H = E.Z_DISPLAY_TOP - E.Z_PCB_TOP     # J3 socket + module + glass (gate G1)
BOTTOM_H = 1.8           # hot-swap sockets and diodes on B.Cu
BOTTOM_CLEAR = 0.3       # bottom envelope kept off the support posts
KEEPOUT_MARGIN = 0.05    # envelopes kept off the bosses / webs (polygon chords vs true circles)


def case_parts(exports: str, side: str) -> dict[str, Solid]:
    out = {}
    for kind in ("top", "bottom", "spacer"):
        path = os.path.join(exports, f"worxboard_{side}_{kind}.step")
        if not os.path.exists(path):
            sys.exit(f"{path} missing: run `just model` first")
        out[kind] = import_step(path)
    return out


def _slab(geom, z0: float, z1: float) -> list[Solid]:
    return [E.prism(f, z0, z1) for f in E.sp_faces(geom)]


def _web_polys(side: str, part: str):
    """Boss webs of one part as KiCad-frame polygons."""
    polys = []
    for web in E.boss_webs(side, part).values():
        pts = [E.K(p.X, p.Y) for e in web.outer_wire().edges() for p in (e.position_at(t / 8) for t in range(8))]
        polys.append(Polygon(pts).buffer(0))
    return unary_union(polys)


def web_keepouts(side: str):
    """Top-part boss webs plus their wall fillets: they reach down to the PCB, so top-side parts
    must avoid them."""
    return _web_polys(side, "top").buffer(E.corner_r(E.Z_POCKET_CEIL - E.Z_SPLIT) + KEEPOUT_MARGIN)


def layout_envelopes(side: str) -> dict[str, list[Solid]]:
    """Stand-in solids for the PCB and its parts, from the layout contracts."""
    z0, z1 = E.Z_SPLIT, E.Z_PCB_TOP
    holes = unary_union([Point(p).buffer(E.LH.HOLE_D / 2) for p in L.holes(side)])
    pcb = L.outline(side).difference(holes)
    env = {"board": _slab(pcb, z0, z1)}
    for ref, h in PART_H.items():
        env[ref] = _slab(box(*L.part_rect(side, ref)), z1, z1 + h)
    env["J3 + display"] = _slab(box(*E.DISPLAY(side)["module"]), z1, z1 + DISPLAY_H)
    bosses = unary_union([Point(p).buffer(E.boss_radius(side, *p) + KEEPOUT_MARGIN, quad_segs=32)
                          for p in L.holes(side)])
    env["component zones"] = _slab(E.zones_poly(side).difference(bosses.union(web_keepouts(side))), z1, z1 + ZONE_H)
    posts = bosses.union(_web_polys(side, "bottom")).buffer(BOTTOM_CLEAR)
    env["bottom-side parts"] = _slab(pcb.difference(posts), z0 - BOTTOM_H, z0)
    return env


def step_envelopes(side: str, path: str) -> dict[str, list[Solid]]:
    """PCB STEP solids moved into the case frame: KiCad exports Y up (y_step = -y_kicad) with the
    board bottom at Z 0; the XY offset depends on the export origin, so it is found by matching
    the board solid's bbox to the layout outline."""
    shape = import_step(path)
    solids = list(shape.solids())
    board = max(solids, key=lambda s: s.volume)
    bb = board.bounding_box()
    x0, y0, x1, y1 = L.outline(side).bounds
    if abs((bb.max.X - bb.min.X) - (x1 - x0)) > SIZE_TOL or abs((bb.max.Y - bb.min.Y) - (y1 - y0)) > SIZE_TOL:
        sys.exit(f"{path}: board solid {bb.size.X:.2f} x {bb.size.Y:.2f} does not match the layout outline "
                 f"{x1 - x0:.2f} x {y1 - y0:.2f}")
    # KiCad (x0, y0) is the top-left corner = STEP (min.X, max.Y); case frame P(x, y)
    cx, cy = E.P(x0, y0)
    move = Pos(cx - bb.min.X, cy - bb.max.Y, E.Z_SPLIT - bb.min.Z)
    return {f"solid {i}": [move * s] for i, s in enumerate(solids)}


def interference(parts: dict[str, Solid], env: dict[str, list[Solid]]) -> list[tuple[str, str, float]]:
    out = []
    for kind, part in parts.items():
        pb = part.bounding_box()
        for name, solids in env.items():
            vol = 0.0
            for s in solids:
                sb = s.bounding_box()
                if (sb.min.X > pb.max.X or sb.max.X < pb.min.X or sb.min.Y > pb.max.Y or sb.max.Y < pb.min.Y
                        or sb.min.Z > pb.max.Z or sb.max.Z < pb.min.Z):
                    continue
                common = part & s
                vol += sum(c.volume for c in common.solids()) if common is not None else 0.0
            out.append((kind, name, vol))
    return out


def main(exports: str, sides: list[str]):
    bad = []
    for side in sides:
        parts = case_parts(exports, side)
        path = PCB_STEP.format(side=side)
        if os.path.exists(path):
            env = step_envelopes(side, path)
            src = os.path.relpath(path, E.ROOT)
        else:
            print(f"WARNING: {os.path.relpath(path, E.ROOT)} not found (WS2 PCB STEP); checking against the "
                  f"layout zones and part envelopes instead")
            env = layout_envelopes(side)
            src = "layout envelopes"
        rows = interference(parts, env)
        hits = [(k, n, v) for k, n, v in rows if v > MAX_INTERFERENCE]
        total = sum(v for _, _, v in rows)
        print(f"  {side:5s} vs {src}: {len(env)} bodies, interference {total:.4f} mm3")
        for k, n, v in hits:
            print(f"    {side} {k} hits {n}: {v:.3f} mm3")
        bad += [(side, k, n) for k, n, _ in hits]
        keep = web_keepouts(side)
        print(f"  {side:5s} top-side keepouts for the PCB: boss webs at " + ", ".join(
            f"({g.centroid.x:.1f},{g.centroid.y:.1f})" for g in getattr(keep, "geoms", [keep])))
    if bad:
        sys.exit(f"fit check failed: {len(bad)} interference(s)")
    print("fit check passed: 0 mm3 interference")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2:] or list(E.SIDES))
