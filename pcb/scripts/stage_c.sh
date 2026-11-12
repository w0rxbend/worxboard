#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Container C (spec §9.2 stages 10-12): maze routing + stitching + fill, DRC gate, U1 GND ties,
# dangling-copper clean-up, pin-in-paste, DRC gate again, checks.
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
python3 pcb/scripts/route.py "$SIDE"
for _ in $(seq "$CONTINUE_ROUNDS"); do             # more completion while items stay unconnected
    drc && break
    python3 pcb/scripts/route.py "$SIDE" --continue
done
drc || { python3 pcb/scripts/checks.py "$SIDE" || true; exit 1; }
python3 pcb/scripts/gnd_ties.py "$SIDE"            # U1 GND ties where routing left a neck (deviations ORDER-4)
python3 pcb/scripts/prune.py "$SIDE"               # dangling rip-up stubs (deviations BOARD-4)
python3 pcb/scripts/pin_in_paste.py "$SIDE"        # paste on J1's shell legs, after routing (ORDER-1)
drc || { python3 pcb/scripts/checks.py "$SIDE" || true; exit 1; }
python3 pcb/scripts/checks.py "$SIDE"
# the LCSC fields parity ignores (ELEC-6), and J3 pad n under nice!view pin n (G1, ELEC-8)
python3 pcb/scripts/netcmp.py --board "$PCB" "$SIDE"
