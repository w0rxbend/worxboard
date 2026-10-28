#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Container A, schematic half (spec §9.2 stages 1-6): footprints, schematic, ERC, netlist, netcmp.
#   bash pcb/scripts/stage_a.sh <side>      (inside kicad/kicad:10.0.7, cwd = repo root)
set -euo pipefail

SIDE="${1:?usage: stage_a.sh left|right}"
SCH="pcb/$SIDE/worxboard-$SIDE.kicad_sch"
OUT="build/$SIDE"

bash tools/kicad_env.sh
mkdir -p "$OUT"

python3 pcb/scripts/gen_footprints.py
python3 pcb/scripts/gen_sch.py "$SIDE"
kicad-cli sch erc --format json --severity-error --exit-code-violations -o "$OUT/erc.json" "$SCH"
kicad-cli sch export netlist --format kicadsexpr -o "$OUT/$SIDE.net" "$SCH"
python3 pcb/scripts/netcmp.py "$OUT/$SIDE.net" "$SIDE"
