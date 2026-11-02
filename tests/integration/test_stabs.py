# SPDX-License-Identifier: GPL-3.0-or-later
"""The 2u stabilisers: the PCB's Ø4.0 housing holes sit on the side layout.stab_dir names, which is
also where the case puts the long half of the plate cut-out (case.stab_cuts reads the same field),
and the two halves are mirror images (spec §5, §10.8; deviations REVIEW-FIX-7)."""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

import pcbdata
from netcmp import find, find_all, parse

ROOT = Path(__file__).resolve().parents[2]
LAYOUT = json.loads((ROOT / "layout/build/layout.json").read_text())
SIDES = ("left", "right")
HOUSING_D = 4.0              # Ø4.0 NPTH under the stabiliser housing (Stab_MX_2u)
HOUSING_ACROSS = 8.255       # across the key from its centre


def housing_holes(side: str) -> dict[str, list[tuple[float, float]]]:
    """Key id -> board centres of the Ø4.0 holes of its STAB_<id> footprint."""
    root = parse(pcbdata.board_path(side).read_text())
    out = {}
    for fp in find_all(root, "footprint"):
        ref = next(p[2] for p in find_all(fp, "property") if p[1] == "Reference")
        if not ref.startswith("STAB_"):
            continue
        x, y, *rot = map(float, find(fp, "at")[1:])
        a = math.radians(rot[0] if rot else 0.0)
        holes = []
        for pad in find_all(fp, "pad"):
            u, v = map(float, find(pad, "at")[1:3])
            if float(find(pad, "drill")[1]) == HOUSING_D:
                holes.append((x + u * math.cos(a) + v * math.sin(a), y - u * math.sin(a) + v * math.cos(a)))
        out[ref.removeprefix("STAB_")] = holes
    return out


@pytest.mark.parametrize("side", SIDES)
def test_stab_housing_holes_follow_stab_dir(side):
    keys = {k["id"]: k for k in LAYOUT["sides"][side]["keys"] if "stab_dir" in k}
    holes = housing_holes(side)
    assert set(holes) == set(keys)
    for kid, k in keys.items():
        dx, dy = k["stab_dir"]
        for hx, hy in holes[kid]:
            across = (hx - k["x"]) * dx + (hy - k["y"]) * dy
            assert across == pytest.approx(HOUSING_ACROSS, abs=0.01), f"{side} {kid}: Ø4 hole {across:.3f} across"


def test_stab_dirs_are_mirrored():
    right = {k["id"]: k["stab_dir"] for k in LAYOUT["sides"]["right"]["keys"] if "stab_dir" in k}
    left = {k["id"]: k["stab_dir"] for k in LAYOUT["sides"]["left"]["keys"] if "stab_dir" in k}
    assert right.keys() == left.keys() and right
    for kid, (dx, dy) in right.items():
        assert left[kid] == pytest.approx([-dx, dy])
