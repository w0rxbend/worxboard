#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Pull the named container images by the digest in tools/images.lock and tag them, so that a later
# `docker run <tag>` runs the locked image and not whatever the tag points to today (spec §9.1).
#   bash tools/pull_images.sh kicad/kicad:10.0.7 [kicad/kicad:10.0.7-full ...]
set -euo pipefail

LOCK="$(dirname "$0")/images.lock"

for tag in "$@"; do
    digest="$(awk -v tag="$tag" '$1 == tag { print $2 }' "$LOCK")"
    [[ -n "$digest" ]] || { echo "$tag is not in $LOCK" >&2; exit 1; }
    docker pull --quiet "$digest"
    docker tag "$digest" "$tag"
done
