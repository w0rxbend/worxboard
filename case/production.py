# SPDX-License-Identifier: GPL-3.0-or-later
"""Keep case/production (committed) equal to the order package that `just order` builds.

    production.py sync  <order_dir> <production_dir>    copy the generated files in
    production.py check <order_dir> <production_dir>    fail if any generated file differs

Generated files (GENERATED): jlccnc/*.{step,pdf} and hole_table.csv, jlc3dp/*.stl, hardware.csv.
The hand-written README.md and */ORDER_NOTES.md live only in case/production (`just order` copies
them into the package). The package is byte-reproducible on one machine (fixed STEP time stamp, PDFs
without a creation date). When bytes differ, `check` compares STEP solids by subtracting each from
the other, STL triangle coordinates and winding, and PDF page sizes and rendered drawings at 600 dpi.
File metadata and triangle ordering may differ. CSV files must be identical.
"""
from __future__ import annotations

import fnmatch
import hashlib
import math
import os
import shutil
import struct
import sys
from contextlib import closing

GENERATED = ("jlccnc/*.step", "jlccnc/*.pdf", "jlccnc/hole_table.csv", "jlc3dp/*.stl", "jlc3dp/*.step",
             "hardware.csv")   # jlc3dp/*.step: none today, kept so a stale copy is reported
STL_COORD_TOL = 1e-4       # mm, absolute: do not scale tolerance with distance from the origin
STEP_VOLUME_TOL = 1e-4    # mm3, allowance for boolean noise, not a fraction of the part volume
PDF_DPI = 600


def generated(root: str) -> list[str]:
    out = []
    for dirpath, _, files in os.walk(root):
        for f in files:
            rel = os.path.relpath(os.path.join(dirpath, f), root).replace(os.sep, "/")
            if any(fnmatch.fnmatch(rel, g) for g in GENERATED):
                out.append(rel)
    return sorted(out)


def same_step(a: str, b: str) -> tuple[bool, str]:
    """Equal bulk properties do not locate holes: compare the material in both directions."""
    from build123d import import_step
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps

    sa, sb = import_step(a), import_step(b)
    if not sa.solids() or not sb.solids() or not sa.is_valid or not sb.is_valid:
        return False, "STEP must contain valid solids"
    if len(sa.solids()) != len(sb.solids()):
        return False, "STEP solid counts differ"
    difference = 0.0
    for first, second in ((sa, sb), (sb, sa)):
        cut = BRepAlgoAPI_Cut(first.wrapped, second.wrapped)
        if not cut.IsDone() or cut.Shape().IsNull():
            return False, "STEP geometry comparison failed"
        props = GProp_GProps()
        BRepGProp.VolumeProperties_s(cut.Shape(), props)
        volume = abs(props.Mass())
        if not math.isfinite(volume):
            return False, "STEP geometry comparison returned an invalid volume"
        difference += volume
    ok = difference <= STEP_VOLUME_TOL
    return ok, f"STEP symmetric difference {difference:.6g} mm3 (allowed {STEP_VOLUME_TOL:g})"


def stl_triangles(path: str) -> list[tuple[float, ...]]:
    """Canonical oriented triangles of a binary STL; ignore headers and stored normals."""
    with open(path, "rb") as fh:
        data = fh.read()
    if len(data) < 84:
        raise ValueError(f"{path}: truncated binary STL")
    n = struct.unpack("<I", data[80:84])[0]
    if not n or len(data) != 84 + 50 * n:
        raise ValueError(f"{path}: invalid binary STL triangle count")
    triangles = []
    for i in range(n):
        v = struct.unpack("<9f", data[84 + 50 * i + 12:84 + 50 * i + 48])
        if not all(math.isfinite(x) for x in v):
            raise ValueError(f"{path}: non-finite STL coordinate")
        # Only cyclic permutations preserve the face's winding.
        triangles.append(min(v, v[3:] + v[:3], v[6:] + v[:6]))
    return sorted(triangles)


def pdf_pages(path: str) -> list[tuple[tuple[float, float], bytes]]:
    """Compare drawings, fonts and text together, independent of PDF object IDs or compression."""
    import pypdfium2 as pdfium

    pages = []
    with pdfium.PdfDocument(path) as doc:
        for i in range(len(doc)):
            with closing(doc[i]) as page, closing(page.render(scale=PDF_DPI / 72)) as bitmap:
                digest = hashlib.sha256(bitmap.to_numpy().tobytes()).digest()
                pages.append((page.get_size(), digest))
    if not pages:
        raise ValueError(f"{path}: PDF has no pages")
    return pages


def same(a: str, b: str) -> tuple[bool, str]:
    if open(a, "rb").read() == open(b, "rb").read():
        return True, "identical"
    ext = os.path.splitext(a)[1].lower()
    if ext == ".step":
        return same_step(a, b)
    elif ext == ".stl":
        fa, fb = stl_triangles(a), stl_triangles(b)
        ok = len(fa) == len(fb) and all(abs(x - y) <= STL_COORD_TOL
                                      for ta, tb in zip(fa, fb) for x, y in zip(ta, tb))
        return ok, "same STL triangles" if ok else "STL triangle coordinates or winding differ"
    elif ext == ".pdf":
        ok = pdf_pages(a) == pdf_pages(b)
        return ok, "same PDF drawings" if ok else "PDF page sizes or rendered drawings differ"
    else:
        return False, "differs"


def sync(order: str, prod: str):
    for rel in generated(prod):
        if rel not in generated(order):
            os.remove(os.path.join(prod, rel))
            print(f"  removed {rel}")
    for rel in generated(order):
        dst = os.path.join(prod, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(os.path.join(order, rel), dst)
        print(f"  {rel}")


def check(order: str, prod: str):
    want, have = generated(order), generated(prod)
    bad = [f"missing in {prod}: {r}" for r in want if r not in have]
    bad += [f"not built any more: {r}" for r in have if r not in want]
    for rel in want:
        if rel in have:
            ok, how = same(os.path.join(order, rel), os.path.join(prod, rel))
            print(f"  {rel}: {how}")
            if not ok:
                bad.append(f"{rel}: {how}")
    if bad:
        sys.exit("case/production is stale (run `just model order production`):\n  " + "\n  ".join(bad))
    print(f"case/production matches the order package: {len(want)} generated files")


if __name__ == "__main__":
    if len(sys.argv) != 4 or sys.argv[1] not in ("sync", "check"):
        sys.exit(__doc__)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    (sync if sys.argv[1] == "sync" else check)(sys.argv[2], sys.argv[3])
