#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Fetch the pinned Freerouting jar into pcb/.tools/ and verify it (spec §9.1).
set -euo pipefail

VERSION=2.5.0
JAR="freerouting-$VERSION.jar"
SHA256=f6f51bb02245e8e717f9359bd260cc9c5c0b1bc0acc8b7cb2cd5b8ffeb5de3c7
DEST="${1:-pcb/.tools}"

mkdir -p "$DEST"
if [[ ! -f "$DEST/$JAR" ]]; then
    gh release download "v$VERSION" -R freerouting/freerouting -p "$JAR" -D "$DEST"
fi
echo "$SHA256  $DEST/$JAR" | sha256sum -c -
