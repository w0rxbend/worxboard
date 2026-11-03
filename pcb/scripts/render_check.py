# SPDX-License-Identifier: GPL-3.0-or-later
"""The committed renders are current (spec §9 stage 14; deviations BOARD-12).

    python3 pcb/scripts/render_check.py <side>
        compares docs/images/pcb-<side>-{top,bottom}.png (just rendered by stage D) with the committed
        copies in build/<side>/committed/ (pcb.just pcb-render-check extracts them from HEAD)

KiCad's 3D raytracer is not bit-exact from run to run: the same board gives a few pixels that differ
by one or two levels (0 to 4 of the 1.6 million pixels of the left top view). A byte comparison then fails
at random, so the images are compared pixel by pixel: they must have the same size, and at most
TOL_PIXELS pixels may differ, by at most TOL_LEVEL in any channel. Any real change to the board (a moved
part, a track, a via, silk) changes far more pixels than that.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import png

ROOT = Path(__file__).resolve().parents[2]
VIEWS = ("top", "bottom")
TOL_LEVEL = 8                # max per-channel difference of a pixel that may differ (0-255)
TOL_PIXELS = 64              # max number of differing pixels per view


def load(path: Path) -> np.ndarray:
    w, h, rows, info = png.Reader(filename=str(path)).asRGBA8()
    return np.vstack([np.frombuffer(bytes(r), np.uint8) for r in rows]).reshape(h, w, 4).astype(np.int16)


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in ("left", "right"):
        print(__doc__)
        return 2
    side, failed = argv[1], 0
    for view in VIEWS:
        name = f"pcb-{side}-{view}.png"
        new, old = ROOT / "docs/images" / name, ROOT / "build" / side / "committed" / name
        a, b = load(new), load(old)
        if a.shape != b.shape:
            print(f"FAIL {name}: rendered {a.shape[1]}x{a.shape[0]}, committed {b.shape[1]}x{b.shape[0]}")
            failed += 1
            continue
        d = np.abs(a - b).max(axis=2)
        n, worst = int((d > 0).sum()), int(d.max())
        ok = n <= TOL_PIXELS and worst <= TOL_LEVEL
        print(f"{'ok  ' if ok else 'FAIL'} {name}: {n} pixels differ, by at most {worst} "
              f"(allowed {TOL_PIXELS} by {TOL_LEVEL})")
        failed += not ok
    if failed:
        print(f"renders {side}: commit the renders of `just pcb-fab {side}`")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
