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

# Not assembled (JP1, TP*, H*, STAB_*): copper or drill only, excluded by their footprint attributes
# (exclude_from_bom/pos), not by kikit --ignore, which deletes footprints and corrupts the board under
# KiCad 10 (deviations WS2c-1). Everything else, J3 included, is fitted by JLC (deviations ELEC-3);
# netcmp.py --board checks both against design.py (deviations ELEC-6)
# J3's STEP body: the 5.0 mm socket model of pcb/lib, never KiCad's 8.5 mm one (deviations ELEC-3)
J3_MODEL="PinSocket_1x04_P2.54mm_Vertical_H5.0mm"
STOCK_SOCKET_MODEL="PinSocket_1x04_P2.54mm_Vertical"
# KiCad -> JLC CPL corrections (kikit pattern file: footprint regex -> X, Y, rotation), one row per
# footprint whose JLC footprint differs in origin or zero angle; cpl_check.py below proves every
# placement against JLC's own footprint. The order package is stage P (stage_p.sh, pcb/production/)
ROTATIONS="pcb/scripts/jlc_rotations.csv"
RENDER_W=1600
RENDER_H=1000

bash tools/kicad_env.sh
mkdir -p "$OUT" "$IMAGES"

# 13. gerbers.zip, bom.csv, pos.csv; any assembled part without an LCSC field fails
rm -rf "$OUT/jlc"
python3 -m kikit.ui fab jlcpcb --assembly --missingError --no-drc --schematic "$SCH" --field LCSC \
    --correctionpatterns "$ROTATIONS" "$PCB" "$OUT/jlc"
for f in gerbers.zip bom.csv pos.csv; do
    [[ -s "$OUT/jlc/$f" ]] || { echo "missing $OUT/jlc/$f" >&2; exit 1; }
done
# kikit takes bom.csv from the schematic but pos.csv, its corrections and the gerbers from the board,
# and KiCad's parity ignores the LCSC field: the board, bom.csv and pos.csv must carry exactly
# design.py's fitted parts and LCSC numbers, and no retired part (deviations ELEC-6); J3 must put pad n
# under pin n of the OLED plugged into it (gate G1, deviations ELEC-8)
python3 pcb/scripts/netcmp.py --board "$PCB" "$SIDE" "$OUT/jlc"
# The CPL places JLC's own footprint of every part (pcb/scripts/jlc_footprints.json) on its KiCad pads:
# within 0.1 mm, pin 1 on pin 1, terminals on their pads, socket bodies clear of the switch holes
python3 pcb/scripts/cpl_check.py --quiet "$PCB" "$OUT/jlc/bom.csv" "$OUT/jlc/pos.csv"

# 14. renders (committed), Edge.Cuts DXF in mm, STEP with substituted models. The case fit check
# reads this STEP, so J3 must carry the 5.0 mm socket it is ordered with (deviations ELEC-3); DNP
# parts (none on rev A) stay out of it
for view in top bottom; do
    kicad-cli pcb render --side "$view" --width "$RENDER_W" --height "$RENDER_H" --quality basic \
        -o "$IMAGES/pcb-$SIDE-$view.png" "$PCB"
done
kicad-cli pcb export dxf --mode-single --output-units mm --layers Edge.Cuts -o "$OUT/edge.dxf" "$PCB"
kicad-cli pcb export step --subst-models --no-dnp -f -o "$OUT/worxboard-$SIDE.step" "$PCB"
if ! grep -q "PRODUCT('$J3_MODEL'" "$OUT/worxboard-$SIDE.step"; then
    echo "$OUT/worxboard-$SIDE.step lacks the J3 body $J3_MODEL" >&2
    exit 1
fi
if grep -q "PRODUCT('$STOCK_SOCKET_MODEL'" "$OUT/worxboard-$SIDE.step"; then
    echo "$OUT/worxboard-$SIDE.step carries KiCad's 8.5 mm $STOCK_SOCKET_MODEL body" >&2
    exit 1
fi
