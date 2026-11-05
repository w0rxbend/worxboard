# SPDX-License-Identifier: GPL-3.0-or-later
"""Assemble the GitHub Pages microsite.

Copies the static viewer (site/web/), layout/build/layout.json, the doc images and the case renders
and, when they exist, the case STLs from case/exports/. Writes manifest.json with the case part
stats, leg placements, the gallery list and the PCB components: every assembled part of the
committed boards (pcb/<side>/*.kicad_pcb) as a box at its footprint position, sized from the
footprint's Fab outline. The case STLs are optional (`just model`).

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
import pcbdata as PCB  # noqa: E402

WEB = ROOT / "site/web"
LAYOUT_JSON = ROOT / "layout/build/layout.json"
CASE_DIR = ROOT / "case"
CASE_EXPORTS = CASE_DIR / "exports"
IMAGE_DIRS = (ROOT / "docs/images", CASE_DIR / "renders")
REPO = "https://github.com/w0rxbend/worxboard"

AL_DENSITY = 2.70e-3      # g/mm3, 6061
CAD_ORIGIN = (130.0, 100.0)   # KiCad -> CAD frame: (x - OX, -(y - OY)), as in the reference case
LAYOUT_BODIES = ("J3",)       # drawn from `layout` (the header up to the display module)
SKIP_REFS = ("SK", "H", "STAB_", "J", "TP", "JP")   # sockets/jacks drawn from layout; holes; copper only
# footprint library -> (body height mm, viewer material)
PART_BODY = {
    "Package_DFN_QFN": (0.9, "chip"), "Package_SO": (1.75, "chip"), "Crystal": (0.8, "metal"),
    "Package_TO_SOT_SMD": (1.1, "chip"), "Diode_SMD": (1.1, "chip"), "Fuse": (0.85, "passive"),
    "Resistor_SMD": (0.35, "chip"), "Capacitor_SMD": (0.5, "passive"), "Button_Switch_SMD": (2.0, "metal"),
}
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
GALLERY = {  # image stem -> (caption, group), in gallery order; unknown images follow with their file name
    "layout": ("Layout of both halves, generated from layout/: ErgoDox stagger, 25° thumbs, the display in the C6R0 slot", "layout"),
    "pcb-left-top": ("Left PCB, top: RP2040, flash, USB-C J1, BOOT/RESET, JP1, display socket J3, TRRS jack J2 on the inner bump", "pcb"),
    "pcb-right-top": ("Right PCB, top: mirrored, same netlist; both boards print DO NOT HOT-PLUG TRRS by J2", "pcb"),
    "pcb-left-bottom": ("Left PCB, bottom: 37 hot-swap socket footprints and 37 diodes", "pcb"),
    "pcb-right-bottom": ("Right PCB, bottom: 37 socket footprints and 37 diodes, all fitted by JLC", "pcb"),
    "pair_top_iso": ("Both CNC top shells: the plate is milled into the key well, with 2u stabiliser cut-outs and a display window", "case"),
    "right_with_legs": ("Closed right-half case with its three custom tent legs", "case"),
    "right_top_underside": ("Right top shell, underside: plate webbing, screw bosses, display pocket", "case"),
    "right_bottom_tray": ("Right bottom tray: the socket cavity and the eight M2.5 screw posts", "case"),
    "right_back_usb": ("Back wall of the right half: USB-C notch, BOOT/RESET pin holes, display bezel", "case"),
    "spacer": ("3D-printed plate spacer, right half (this render predates the stabiliser-wire channels)", "case"),
    "leg": ("Custom 6061 tent leg with its TPU foot cap", "case"),
    "leg_cap_tree": ("The TPU print: 8 foot caps on one tree (6 + 2 spares)", "case"),
    "leg_section": ("Outer leg mount section: M3 tapped pad and Ø10 boss", "case"),
    "section": ("Six sections through the right half: key column, display column, across the display, back-edge screws, USB-C, TRRS", "case"),
    "overlay": ("The right-half case over the PCB layout: case outline, PCB, key well, display pocket, window, zones, bosses", "case"),
    "cpl-sk-hotswap-socket": ("Placement proof, hot-swap sockets (bottom): 74 placed, 74 pass", "proof"),
    "cpl-d101-diode-sod123f": ("Placement proof, matrix diodes (bottom): 74 placed, 74 pass", "proof"),
    "cpl-u1-rp2040-qfn56": ("Placement proof, U1 RP2040 QFN-56: both halves pass", "proof"),
    "cpl-u2-flash-soic8": ("Placement proof, U2 QSPI flash SOIC-8: both halves pass", "proof"),
    "cpl-u3-ldo-sot23-5": ("Placement proof, U3 3.3 V LDO SOT-23-5: both halves pass", "proof"),
    "cpl-u4-u5-esd-sot23-6": ("Placement proof, U4 and U5 ESD arrays: 4 placed, 4 pass", "proof"),
    "cpl-y1-crystal-3225": ("Placement proof, Y1 12 MHz crystal: both halves pass", "proof"),
    "cpl-d1-schottky-sod123": ("Placement proof, D1 Schottky on the USB power path: both halves pass", "proof"),
    "cpl-c-0402": ("Placement proof, 0402 capacitors: 38 placed, 38 pass", "proof"),
    "cpl-r-0402": ("Placement proof, 0402 resistors: 26 placed, 26 pass", "proof"),
    "cpl-f1-ptc-1206": ("Placement proof, F1 polyfuse on the TRRS power line: both halves pass", "proof"),
    "cpl-j1-usb-c": ("Placement proof, J1 USB-C, mouth over the back edge: both halves pass", "proof"),
    "cpl-j2-trrs-pj320d": ("Placement proof, J2 TRRS jack on the inner bump: both halves pass", "proof"),
    "cpl-j3-display-socket": ("Placement proof, J3 display socket: five contacts in five holes", "proof"),
    "cpl-sw-tact-ts1088": ("Placement proof, SW1 and SW2 BOOT and RESET switches: 4 placed, 4 pass", "proof"),
}
WIDE = ("pair_top_iso", "section")   # layout.svg is shown full width in its own section
GALLERY_SKIP = ("site-viewer",)   # screenshots of this page: copied (for the link preview), not listed
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
            if p.suffix not in IMAGE_EXT:
                continue
            shutil.copyfile(p, out / "images" / p.name)
            if p.stem.startswith(GALLERY_SKIP):
                continue
            caption, group = GALLERY.get(p.stem, (p.stem, "other"))
            shots.append(dict(file=f"images/{p.name}", caption=caption, group=group, wide=p.stem in WIDE))
    order = list(GALLERY)
    return sorted(shots, key=lambda s: order.index(Path(s["file"]).stem) if Path(s["file"]).stem in order else len(order))


def bodies() -> dict:
    """Layout part rectangles per side (KiCad frame) the viewer draws itself."""
    return {s: {ref: list(L.part_rect(s, ref)) for ref in LAYOUT_BODIES} for s in L.SIDES}


def components(side: str) -> list[dict]:
    """Assembled parts of the committed board: footprint pose and Fab-outline box (KiCad frame)."""
    out = []
    for f in sorted(PCB.footprints(side).values(), key=lambda f: PCB.ref_key(f.ref)):
        lib = f.lib.split(":")[0]
        if f.ref.startswith(SKIP_REFS) or f.body is None or lib not in PART_BODY:
            continue
        h, mat = PART_BODY[lib]
        x0, y0, x1, y1 = f.body
        out.append(dict(ref=f.ref, value=f.value, part=f.lib.split(":")[1], side=f.side,
                        at=[f.x, f.y, f.rot], box=[round((x0 + x1) / 2, 3), round((y0 + y1) / 2, 3),
                                                   round(x1 - x0, 3), round(y1 - y0, 3), h], mat=mat))
    return out


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
        bodies=bodies(), components={s: components(s) for s in L.SIDES},
        parts=parts, legs=leg_placements(ec) if parts else [], gallery=gallery(out),
    )
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    (out / ".nojekyll").touch()
    total = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    print(f"site: {out} ({total / 1e6:.1f} MB), version {version}")
    print(f"  {len(parts)} case parts, {len(manifest['legs'])} leg mounts, {len(manifest['gallery'])} images, "
          f"{sum(len(c) for c in manifest['components'].values())} PCB components")
    for name, p in parts.items():
        print(f"  {name:13s} {p['triangles']:6d} tris  {p['size']}  {p['mass_g']} g")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else "dev"))
