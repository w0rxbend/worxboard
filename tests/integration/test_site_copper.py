# SPDX-License-Identifier: GPL-3.0-or-later
"""The copper figures the microsite prints beside its layer view (site/pcbdata.py `copper`): the track
segments of each layer, their length and their nets, and the vias, read from a board file. The page
also says in plain words that In1.Cu is a ground sheet with no track on it (deviations REVB-8), so the
committed boards are held to that."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SIDES = ("left", "right")


def _site_pcbdata():
    """site/pcbdata.py under a name of its own: `pcbdata` in this directory is the tests' own reader."""
    spec = importlib.util.spec_from_file_location("site_pcbdata", ROOT / "site/pcbdata.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module          # dataclasses look their module up while the file runs
    spec.loader.exec_module(module)
    return module


site_pcbdata = _site_pcbdata()

# Three tracks on F.Cu (5 mm and 2 mm on ROW0, 1 mm on COL1), one locked 10 mm track on B.Cu, two vias.
BOARD = """\
(kicad_pcb
\t(segment
\t\t(start 10 10)
\t\t(end 13 14)
\t\t(width 0.15)
\t\t(layer "F.Cu")
\t\t(net "ROW0")
\t\t(uuid "a")
\t)
\t(segment
\t\t(start 13 14)
\t\t(end 13 16)
\t\t(width 0.15)
\t\t(layer "F.Cu")
\t\t(net "ROW0")
\t\t(uuid "b")
\t)
\t(segment
\t\t(start 0 0)
\t\t(end -1 0)
\t\t(width 0.2)
\t\t(layer "F.Cu")
\t\t(net "COL1")
\t\t(uuid "c")
\t)
\t(segment
\t\t(start 20.5 0)
\t\t(end 20.5 10)
\t\t(width 0.25)
\t\t(locked yes)
\t\t(layer "B.Cu")
\t\t(net "VLED")
\t\t(uuid "d")
\t)
\t(via
\t\t(at 13 14)
\t\t(size 0.6)
\t\t(drill 0.3)
\t\t(layers "F.Cu" "B.Cu")
\t\t(net "ROW0")
\t\t(uuid "e")
\t)
\t(via
\t\t(at 20.5 0)
\t\t(size 0.6)
\t\t(drill 0.3)
\t\t(layers "F.Cu" "B.Cu")
\t\t(locked yes)
\t\t(net "VLED")
\t\t(uuid "f")
\t)
)
"""

TRACK_ARC = """\
\t(arc
\t\t(start 0 0)
\t\t(mid 1 1)
\t\t(end 2 0)
\t\t(width 0.2)
\t\t(layer "F.Cu")
\t\t(net "ROW0")
\t\t(uuid "g")
\t)
"""


def test_copper_counts_the_tracks_of_each_layer_with_their_length_and_nets():
    layers = site_pcbdata.copper_of(BOARD).layers

    assert layers["F.Cu"] == site_pcbdata.Tracks(count=3, length=pytest.approx(8.0), nets=2)
    assert layers["B.Cu"] == site_pcbdata.Tracks(count=1, length=pytest.approx(10.0), nets=1)


def test_copper_lists_only_layers_that_carry_a_track():
    assert set(site_pcbdata.copper_of(BOARD).layers) == {"F.Cu", "B.Cu"}


def test_copper_counts_the_vias():
    assert site_pcbdata.copper_of(BOARD).vias == 2


def test_copper_refuses_a_board_with_track_arcs():
    """Nothing measures an arc, so a board with one must not get a length that leaves it out."""
    with pytest.raises(ValueError, match="arc"):
        site_pcbdata.copper_of(BOARD.replace("\t(via\n", TRACK_ARC + "\t(via\n", 1))


@pytest.mark.parametrize("side", SIDES)
def test_the_ground_sheet_carries_no_track(side):
    """The site says In1.Cu is one sheet of ground with no track on it (deviations REVB-8)."""
    assert "In1.Cu" not in site_pcbdata.copper(side).layers
