# SPDX-License-Identifier: GPL-3.0-or-later
"""Open the paste layer on the through-hole pads that reflow with the SMT parts (pin-in-paste).

    python3 pcb/scripts/pin_in_paste.py <side>     (edits pcb/<side>/worxboard-<side>.kicad_pcb)

J1's four shell legs (pad "SH") are plated slots, and the stock footprint puts them on copper and
mask only. JLC opens no stencil aperture on a through-hole pad that is not on the paste layer ("the
apertures for through-hole components will not be open in stencil as default", JLC's stencil
standard, section 5), so the legs would stay unsoldered and the receptacle would hang on its 0.3 mm
signal pads (docs/deviations.md ORDER-1). This adds the paste layer of the pad's side to each pad
in PIN_IN_PASTE.

Runs at the end of stage C, after prune.py and before the last DRC gate. Paste is not copper, so the
routing does not need it, and it must not come earlier: the stages seed their KIIDs from the board
bytes (place.seed_kiids), so any earlier change re-routes the board. checks.py gates the result.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parents[2]
PIN_IN_PASTE = {"J1": "SH"}      # ref -> pad number


def paste_layer(fp: pcbnew.FOOTPRINT) -> int:
    return pcbnew.B_Paste if fp.GetLayer() == pcbnew.B_Cu else pcbnew.F_Paste


def pads(board: pcbnew.BOARD):
    """(footprint, pad) of every pad in PIN_IN_PASTE."""
    for ref, num in PIN_IN_PASTE.items():
        fp = board.FindFootprintByReference(ref)
        for pad in fp.Pads():
            if pad.GetNumber() == num:
                yield fp, pad


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in ("left", "right"):
        print(__doc__)
        return 2
    side = argv[1]
    path = ROOT / "pcb" / side / f"worxboard-{side}.kicad_pcb"
    board = pcbnew.LoadBoard(str(path))
    added = 0
    for fp, pad in pads(board):
        layer = paste_layer(fp)
        if not pad.IsOnLayer(layer):
            layers = pad.GetLayerSet()
            layers.AddLayer(layer)
            pad.SetLayerSet(layers)
            added += 1
    if added:
        board.Save(str(path))
    print(f"{side}: pin-in-paste: {added} pad(s) given paste, "
          f"{sum(1 for _ in pads(board))} in {', '.join(f'{r} {n}' for r, n in PIN_IN_PASTE.items())}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
