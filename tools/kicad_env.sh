#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Run first in every KiCad container (spec §9.1): seed the stock library tables in $HOME
# and add the project's `worxboard` libraries, resolved relative to each project dir.
set -euo pipefail

KICAD_VER="${KICAD_VER:-10.0}"
TEMPLATES=/usr/share/kicad/template
CFG="$HOME/.config/kicad/$KICAD_VER"
LIB='${KIPRJMOD}/../lib'

mkdir -p "$CFG"
cp "$TEMPLATES"/*-lib-table "$CFG"/

add_lib() {  # add_lib <table> <entry>
    local table="$CFG/$1" entry="$2"
    grep -q '(name "worxboard")' "$table" && return 0
    sed -i '$ d' "$table"                      # drop the closing paren
    printf '  %s\n)\n' "$entry" >> "$table"
}
add_lib fp-lib-table  "(lib (name \"worxboard\")(type \"KiCad\")(uri \"$LIB/worxboard.pretty\")(options \"\")(descr \"worxboard\"))"
add_lib sym-lib-table "(lib (name \"worxboard\")(type \"KiCad\")(uri \"$LIB/worxboard.kicad_sym\")(options \"\")(descr \"worxboard\"))"
