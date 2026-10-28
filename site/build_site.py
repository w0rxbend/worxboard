# SPDX-License-Identifier: GPL-3.0-or-later
"""Assemble the GitHub Pages microsite.

Copies the static viewer (site/web/), layout/build/layout.json, the doc images and, when they exist,
the case STLs from case/exports/ and their renders. Writes manifest.json with part stats, part
bodies from `layout`, leg placements and the gallery list. Everything except `layout` is optional,
so the site builds before the PCB and case streams have produced anything.

usage: build_site.py <out dir> [version]
"""
from __future__ import annotations

import inspect
import json
import math
import shutil
import struct
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import layout as L  # noqa: E402

WEB = ROOT / "site/web"
LAYOUT_JSON = ROOT / "layout/build/layout.json"
CASE_DIR = ROOT / "case"
CASE_EXPORTS = CASE_DIR / "exports"
IMAGE_DIRS = (ROOT / "docs/images", CASE_DIR / "renders")
REPO = "https://github.com/w0rxbend/worxboard"

AL_DENSITY = 2.70e-3      # g/mm3, 6061
CAD_ORIGIN = (130.0, 100.0)   # KiCad -> CAD frame: (x - OX, -(y - OY)), as in the reference case
ZONED_PARTS = ("U1", "U2", "SW_BOOT", "SW_RST", "J1", "J2", "J3")
CASE_PARTS = {  # stl stem (after "worxboard_") -> label, material, role
    "right_top": ("Right top shell", "alu", "top"),
    "right_bottom": ("Right bottom tray", "alu", "bottom"),
    "right_spacer": ("Right plate spacer", "print", "spacer"),
    "left_top": ("Left top shell", "alu", "top"),
    "left_bottom": ("Left bottom tray", "alu", "bottom"),
    "left_spacer": ("Left plate spacer", "print", "spacer"),
    "leg": ("Tent leg", "alu", "leg"),
    "leg_cap": ("Leg foot cap", "tpu", "leg_cap"),
}
CAPTIONS = {  # image stem -> caption; unknown images get their file name
    "layout": "Layout of both halves, generated from layout/",
    "concept-annotated": "The original concept sketch",
    "pcb-left-top": "Left PCB, top", "pcb-left-bottom": "Left PCB, bottom",
    "pcb-right-top": "Right PCB, top", "pcb-right-bottom": "Right PCB, bottom",
}
IMAGE_EXT = (".png", ".svg", ".jpg")


def stl_stats(path: Path):
    """Bounding box, enclosed volume and triangle count of a binary STL."""
    data = path.read_bytes()
    n = struct.unpack("<I", data[80:84])[0]
    rec = np.frombuffer(data[84:84 + 50 * n],
                        dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]))
    v = rec["v"].astype(np.float64)
    vol = np.einsum("ij,ij->i", v[:, 0], np.cross(v[:, 1], v[:, 2])).sum() / 6
    pts = v.reshape(-1, 3)
    return pts.min(0), pts.max(0), abs(vol), n


def case_module():
    """The WS3 case module, or None if it is missing or its CAD deps are not installed."""
    sys.path.insert(0, str(CASE_DIR))
    try:
        import worxboard_case  # noqa: PLC0415
        return worxboard_case
    except Exception as e:  # noqa: BLE001  (optional input: any import failure means "no case")
        print(f"  note: case model not importable ({type(e).__name__}: {e}); no leg placements")
        return None


def leg_placements(ec) -> list[list[float]]:
    """4x4 row-major matrix per right-half mount that seats a leg on its boss at swing 0
    (same construction as the reference ErgoDox site); the viewer adds the swing about local Z."""
    if ec is None or not hasattr(ec, "leg_mounts"):
        return []
    from build123d import Pos, Rot  # noqa: PLC0415
    takes_side = inspect.signature(ec.leg_mounts).parameters  # WS3 port: leg_mounts(side)
    mounts = ec.leg_mounts("right") if takes_side else ec.leg_mounts()
    out = []
    for (px, py), (nx, ny) in mounts:
        loc = (Pos(px, py, 0) * Rot(0, 0, math.degrees(math.atan2(-ny, -nx)))
               * Pos(0, 0, ec.LEG_Z) * Rot(0, -90, 0) * Pos(0, 0, ec.LEG_BOSS_H))
        t = loc.wrapped.Transformation()
        m = [[t.Value(r, c) for c in range(1, 5)] for r in range(1, 4)] + [[0, 0, 0, 1]]
        out.append([round(x, 6) for row in m for x in row])
    return out


def case_parts(out: Path) -> dict:
    parts = {}
    for stem, (label, mat, role) in CASE_PARTS.items():
        src = CASE_EXPORTS / f"worxboard_{stem}.stl"
        if not src.exists():
            continue
        (out / "models").mkdir(exist_ok=True)
        shutil.copyfile(src, out / "models" / f"{stem}.stl")
        lo, hi, vol, tris = stl_stats(src)
        parts[stem] = dict(label=label, material=mat, role=role, file=f"models/{stem}.stl",
                           triangles=int(tris), size=[round(float(x), 1) for x in hi - lo],
                           mass_g=round(vol * AL_DENSITY, 1) if mat == "alu" else None,
                           volume_cm3=round(vol / 1000, 1))
    return parts


def gallery(out: Path) -> list[dict]:
    shots = []
    (out / "images").mkdir()
    for d in IMAGE_DIRS:
        if not d.is_dir():
            continue
        for p in sorted(d.iterdir()):
            if p.suffix in IMAGE_EXT:
                shutil.copyfile(p, out / "images" / p.name)
                shots.append(dict(file=f"images/{p.name}", caption=CAPTIONS.get(p.stem, p.stem),
                                  wide=p.stem in ("layout", "concept-annotated")))
    return shots


def bodies() -> dict:
    """Top-side part bodies per side (KiCad frame rectangles) for the PCB preview."""
    return {s: {ref: list(L.part_rect(s, ref)) for ref in ZONED_PARTS} for s in L.SIDES}


def main(out: Path, version: str) -> int:
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(WEB, out)
    shutil.copyfile(LAYOUT_JSON, out / "layout.json")
    ec = case_module()
    parts = case_parts(out)
    manifest = dict(
        version=version, repo=REPO,
        cad_origin=[getattr(ec, "OX", CAD_ORIGIN[0]), getattr(ec, "OY", CAD_ORIGIN[1])],
        bodies=bodies(), parts=parts, legs=leg_placements(ec) if parts else [], gallery=gallery(out),
    )
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    (out / ".nojekyll").touch()
    total = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    print(f"site: {out} ({total / 1e6:.1f} MB), version {version}")
    print(f"  {len(parts)} case parts, {len(manifest['legs'])} leg mounts, {len(manifest['gallery'])} images")
    for name, p in parts.items():
        print(f"  {name:13s} {p['triangles']:6d} tris  {p['size']}  {p['mass_g']} g")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else "dev"))
