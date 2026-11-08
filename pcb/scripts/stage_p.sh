#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Stage P: the JLCPCB turnkey order package of one half, and the PCBWay files next to it (pcbway/),
# from the committed board.
#   bash pcb/scripts/stage_p.sh <side>      (inside kicad/kicad:10.0.7, cwd = repo root)
# -> build/<side>/production/ (what pcb/production/<side>/ must equal), work files in
#    build/<side>/production-work/. The output is reproducible byte for byte (PYTHONHASHSEED=0, KiKit's
#    seeded panel, date-free Gerbers, fixed zip entries), so CI rebuilds it and compares.
set -euo pipefail

SIDE="${1:?usage: stage_p.sh left|right}"
PCB="pcb/$SIDE/worxboard-$SIDE.kicad_pcb"
SCH="pcb/$SIDE/worxboard-$SIDE.kicad_sch"
WORK="build/$SIDE/production-work"
OUT="build/$SIDE/production"
PANEL="$WORK/panel/worxboard-$SIDE-panel.kicad_pcb"
# KiCad -> JLC centroid and rotation per footprint, checked part by part by cpl_check.py below
ROTATIONS="pcb/scripts/jlc_rotations.csv"

bash tools/kicad_env.sh
rm -rf "$WORK" "$OUT"
mkdir -p "$WORK/panel"

# P1. Panel: the board in a tight frame (6 mm rails, 2 mm milled slot), mouse-bite tabs away from parts
# and the J1/J2 mouths (panel_tabs.py), 3 fiducials per side, 4 NPTH tooling holes (panel.json)
python3 -m kikit.ui panelize -p pcb/scripts/panel.json --text "text: worxboard $SIDE rev B, JLC SMT panel" \
    "$PCB" "$PANEL"

# P2. DRC of the panel: no error, nothing unconnected (the board's own DRC gate is stage C / pcb-drc)
kicad-cli pcb drc --severity-error --exit-code-violations --format json -o "$WORK/panel-drc.json" "$PANEL"
python3 - "$WORK/panel-drc.json" <<'EOF'
import json, sys
d = json.load(open(sys.argv[1]))
bad = [v for v in d["violations"] if v["severity"] == "error"] + d.get("unconnected_items", [])
for v in bad:
    print(f"panel DRC: {v.get('type')} {v.get('description')}", file=sys.stderr)
sys.exit(1 if bad else 0)
EOF

# P3. Gerbers, BOM and CPL of the panel and of the bare board (KiKit), corrections applied
for what in panel bare; do
    board="$PCB"
    [[ $what == panel ]] && board="$PANEL"
    python3 -m kikit.ui fab jlcpcb --assembly --missingError --no-drc --schematic "$SCH" --field LCSC \
        --correctionpatterns "$ROTATIONS" "$board" "$WORK/$what-jlc"
done

# P4. The package: normalised Gerbers, JLC headers, README, order zip, bare-board/
python3 pcb/scripts/jlc_check.py facts "$PANEL" "$PCB" "$WORK/panel-jlc" "$WORK/panel-drc.json" "$WORK/facts.json"
python3 pcb/scripts/package.py "$SIDE" "$WORK/panel-jlc" "$WORK/bare-jlc" "$WORK/facts.json" "$OUT"

# P5. Checks on the package itself: JLC's footprint of every part placed from cpl.csv lands on the
# KiCad pads (panel and bare board), and the files are what JLC takes
python3 pcb/scripts/cpl_check.py "$PANEL" "$OUT/bom.csv" "$OUT/cpl.csv" \
    "$PCB" "$OUT/bare-board/bom.csv" "$OUT/bare-board/cpl.csv"
python3 pcb/scripts/jlc_check.py check "$SIDE" "$OUT" --panel "$PANEL"

# P6. The PCBWay files -> $OUT/pcbway/: KiCad's own position files of the panel and of the board (no
# JLC correction, the frames of the two Gerber sets), a BOM with manufacturer part numbers (mpn.json),
# README; pcbway.py re-derives the JLC CPL from them and fails on any other difference
for what in panel bare; do
    board="$PCB"
    [[ $what == panel ]] && board="$PANEL"
    kicad-cli pcb export pos --format csv --units mm --side both --use-drill-file-origin --exclude-dnp \
        -o "$WORK/$what-pos.csv" "$board"
done
python3 pcb/scripts/mpn.py check
python3 pcb/scripts/pcbway.py "$SIDE" "$PCB" "$WORK/panel-pos.csv" "$WORK/bare-pos.csv" "$WORK/facts.json" "$OUT"
