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

# Not assembled: copper or drill only, excluded by their footprint attributes (exclude_from_bom/pos),
# not by kikit --ignore, which deletes footprints and corrupts the board under KiCad 10 (deviations
# WS2c-1). Everything else, J3 included, is fitted by JLC (deviations ELEC-3)
NOT_ASSEMBLED='^"?(JP1|TP[0-9]+|H[0-9]+|STAB_[A-Z0-9]+)"?$'
# Fitted by hand at JLC (THT): must be in both bom.csv and pos.csv
ASSEMBLED_THT=(J3)
# J3's STEP body: the 5.0 mm socket model of pcb/lib, never KiCad's 8.5 mm one (deviations ELEC-3)
J3_MODEL="PinSocket_1x05_P2.54mm_Vertical_H5.0mm"
STOCK_SOCKET_MODEL="PinSocket_1x05_P2.54mm_Vertical"
# KiCad -> JLC CPL corrections (kikit pattern file: footprint regex -> X, Y, rotation); JLC's
# placement preview is still the final check (docs/ordering-jlcpcb.md)
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
# Every token after bom.csv's Comment column (designator lists are comma-joined) and pos.csv's
# designators, CRs stripped. Collected first: `... | grep -q` exits on the first match, SIGPIPEs
# the writer, and under pipefail the `if` then reads the 141 as "no match".
designators="$(cut -d, -f2- "$OUT/jlc/bom.csv" | tr ',\r' '\n\n'; cut -d, -f1 "$OUT/jlc/pos.csv" | tr -d '\r')"
if grep -Eq "${NOT_ASSEMBLED}" <<<"$designators"; then
    echo "a not-assembled part is in bom.csv / pos.csv:" >&2
    grep -E "${NOT_ASSEMBLED}" <<<"$designators" >&2
    exit 1
fi
bom_refs="$(cut -d, -f2- "$OUT/jlc/bom.csv" | tr ',\r"' '\n\n\n')"
pos_refs="$(cut -d, -f1 "$OUT/jlc/pos.csv" | tr -d '\r"')"
for ref in "${ASSEMBLED_THT[@]}"; do
    grep -qx "$ref" <<<"$bom_refs" || { echo "$ref is missing from $OUT/jlc/bom.csv" >&2; exit 1; }
    grep -qx "$ref" <<<"$pos_refs" || { echo "$ref is missing from $OUT/jlc/pos.csv" >&2; exit 1; }
done

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
