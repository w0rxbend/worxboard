#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Container D (spec §9.2 stages 13-14): JLCPCB fab outputs, renders, Edge DXF and STEP.
#   bash pcb/scripts/stage_d.sh <side>      (inside kicad/kicad:10.0.7-full, cwd = repo root)
# The -full image carries the stock 3D models, used by both the STEP and the renders.
set -euo pipefail

SIDE="${1:?usage: stage_d.sh left|right}"
PCB="pcb/$SIDE/worxboard-$SIDE.kicad_pcb"
SCH="pcb/$SIDE/worxboard-$SIDE.kicad_sch"
OUT="build/$SIDE"
IMAGES="docs/images"

# Not assembled: excluded by their footprint attributes (exclude_from_bom/pos, J3 dnp), not by
# kikit --ignore, which deletes footprints and corrupts the board under KiCad 10 (deviations WS2c-1)
NOT_ASSEMBLED='^"?(JP1|J3|TP[0-9]+|H[0-9]+|STAB_[A-Z0-9]+)"?$'
RENDER_W=1600
RENDER_H=1000

bash tools/kicad_env.sh
mkdir -p "$OUT" "$IMAGES"

# 13. gerbers.zip, bom.csv, pos.csv; any assembled part without an LCSC field fails
rm -rf "$OUT/jlc"
python3 -m kikit.ui fab jlcpcb --assembly --missingError --no-drc --schematic "$SCH" --field LCSC \
    "$PCB" "$OUT/jlc"
for f in gerbers.zip bom.csv pos.csv; do
    [[ -s "$OUT/jlc/$f" ]] || { echo "missing $OUT/jlc/$f" >&2; exit 1; }
done
if cut -d, -f2- "$OUT/jlc/bom.csv" | tr ',' '\n' | cat - <(cut -d, -f1 "$OUT/jlc/pos.csv") | grep -Eq "${NOT_ASSEMBLED}" ; then
    echo "a not-assembled part is in bom.csv / pos.csv" >&2; exit 1
fi

# 14. renders (committed), Edge.Cuts DXF in mm, STEP with substituted models
for view in top bottom; do
    kicad-cli pcb render --side "$view" --width "$RENDER_W" --height "$RENDER_H" --quality basic \
        -o "$IMAGES/pcb-$SIDE-$view.png" "$PCB"
done
kicad-cli pcb export dxf --mode-single --output-units mm --layers Edge.Cuts -o "$OUT/edge.dxf" "$PCB"
kicad-cli pcb export step --subst-models -f -o "$OUT/worxboard-$SIDE.step" "$PCB"
