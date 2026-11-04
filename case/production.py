# SPDX-License-Identifier: GPL-3.0-or-later
"""Keep case/production (committed) equal to the order package that `just order` builds.

    production.py sync  <order_dir> <production_dir>    copy the generated files in
    production.py check <order_dir> <production_dir>    fail if any generated file differs

Generated files (GENERATED): jlccnc/*.{step,pdf} and hole_table.csv, jlc3dp/*.stl, hardware.csv.
The hand-written README.md and */ORDER_NOTES.md live only in case/production (`just order` copies
them into the package). The package is byte-reproducible on one machine (fixed STEP time stamp, PDFs
without a creation date). If a STEP, STL or PDF differs in bytes only, `check` compares what it holds:
STEP volume, area, faces and bounding box; STL triangles, volume and bounding box; PDF pages and text.
CSV files must be identical.
"""
from __future__ import annotations

import fnmatch
import os
import re
import shutil
import struct
import sys
import zlib

GENERATED = ("jlccnc/*.step", "jlccnc/*.pdf", "jlccnc/hole_table.csv", "jlc3dp/*.stl", "jlc3dp/*.step",
             "hardware.csv")   # jlc3dp/*.step: none today, kept so a stale copy is reported
REL_TOL = 1e-6
ABS_TOL = 1e-4      # mm


def generated(root: str) -> list[str]:
    out = []
    for dirpath, _, files in os.walk(root):
        for f in files:
            rel = os.path.relpath(os.path.join(dirpath, f), root).replace(os.sep, "/")
            if any(fnmatch.fnmatch(rel, g) for g in GENERATED):
                out.append(rel)
    return sorted(out)


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= max(ABS_TOL, REL_TOL * max(abs(a), abs(b)))


def step_facts(path: str) -> list[float]:
    from build123d import import_step
    s = import_step(path)
    bb = s.bounding_box()
    return [s.volume, s.area, float(len(s.faces())), float(len(s.solids())),
            bb.min.X, bb.min.Y, bb.min.Z, bb.max.X, bb.max.Y, bb.max.Z]


def stl_facts(path: str) -> list[float]:
    data = open(path, "rb").read()
    n = struct.unpack("<I", data[80:84])[0]
    vol, lo, hi = 0.0, [1e9] * 3, [-1e9] * 3
    for i in range(n):
        v = struct.unpack("<9f", data[84 + 50 * i + 12:84 + 50 * i + 48])
        a, b, c = v[0:3], v[3:6], v[6:9]
        vol += (a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0])
                + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6
        for p in (a, b, c):
            for k in range(3):
                lo[k], hi[k] = min(lo[k], p[k]), max(hi[k], p[k])
    return [float(n), abs(vol), *lo, *hi]


def pdf_facts(path: str) -> list[str]:
    """Page count and every text string, in order, from the (deflated) content streams."""
    data = open(path, "rb").read()
    pages = len(re.findall(rb"/Type\s*/Page[^s]", data))
    texts = []
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.S):
        raw = m.group(1)
        try:
            raw = zlib.decompress(raw)
        except zlib.error:
            pass
        for arr in re.findall(rb"\[(.*?)\]\s*TJ|\(((?:[^()\\]|\\.)*)\)\s*Tj", raw, re.S):
            seg = arr[0] or b"(" + arr[1] + b")"
            texts.append("".join(t.decode("latin-1") for t in re.findall(rb"\(((?:[^()\\]|\\.)*)\)", seg)))
    return [str(pages), *texts]


def same(a: str, b: str) -> tuple[bool, str]:
    if open(a, "rb").read() == open(b, "rb").read():
        return True, "identical"
    ext = os.path.splitext(a)[1].lower()
    if ext == ".step":
        fa, fb = step_facts(a), step_facts(b)
        ok = all(_close(x, y) for x, y in zip(fa, fb))
    elif ext == ".stl":
        fa, fb = stl_facts(a), stl_facts(b)
        ok = fa[0] == fb[0] and all(_close(x, y) for x, y in zip(fa[1:], fb[1:]))
    elif ext == ".pdf":
        fa, fb = pdf_facts(a), pdf_facts(b)
        ok = fa == fb
    else:
        return False, "differs"
    return ok, ("bytes differ, same content" if ok else f"differs: {fa[:6]} vs {fb[:6]}")


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
