#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Container C (spec §9.2 stages 10-12): session import + stitching + fill, DRC gate, checks.
#   bash pcb/scripts/stage_c.sh <side>      (inside kicad/kicad:10.0.7, cwd = repo root)
set -euo pipefail

SIDE="${1:?usage: stage_c.sh left|right}"
PCB="pcb/$SIDE/worxboard-$SIDE.kicad_pcb"
OUT="build/$SIDE"

CONTINUE_ROUNDS=3

drc() {
    kicad-cli pcb drc --schematic-parity --severity-error --exit-code-violations --format json \
        -o "$OUT/drc.json" "$PCB"
}

bash tools/kicad_env.sh
python3 pcb/scripts/import_ses.py "$SIDE"
for _ in $(seq "$CONTINUE_ROUNDS"); do             # more completion while items stay unconnected
    drc && break
    python3 pcb/scripts/import_ses.py "$SIDE" --continue
done
drc || { python3 pcb/scripts/checks.py "$SIDE" || true; exit 1; }
python3 pcb/scripts/checks.py "$SIDE"
