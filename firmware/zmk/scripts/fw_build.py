# SPDX-License-Identifier: GPL-3.0-or-later
"""Build build.yaml rows like zmkfirmware/zmk build-user-config.yml. Runs inside zmk-build-arm.

    python3 fw_build.py [artifact-name ...]      # default: every row

Expects the repo at $FW_REPO (default /work, as mounted by `just fw`) and an initialised west
workspace in the current directory. Each row builds into $FW_REPO/build/fw/<artifact>/ and its
zmk.uf2 is copied to $FW_REPO/build/fw/artifacts/<artifact>.uf2. Exit 1 if any selected row fails.
"""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import yaml  # PyYAML ships with west in the build image

REPO = Path(os.environ.get("FW_REPO", "/work"))
CONFIG = REPO / "firmware/zmk/config"
OUT = REPO / "build/fw"


def rows() -> list[dict]:
    data = yaml.safe_load((REPO / "build.yaml").read_text())
    return data["include"]


def build(row: dict) -> bool:
    name = row["artifact-name"]
    bdir = OUT / name
    cmd = ["west", "build", "-p", "-s", "zmk/app", "-d", str(bdir), "-b", row["board"]]
    if row.get("snippet"):
        cmd += ["-S", row["snippet"]]
    cmd += ["--", f"-DZMK_CONFIG={CONFIG}", f"-DZMK_EXTRA_MODULES={REPO}"]
    cmd += shlex.split(row.get("cmake-args", ""))
    print("::", " ".join(cmd), flush=True)
    log = OUT / f"{name}.log"
    with log.open("w") as fh:
        ok = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT).returncode == 0
    uf2 = bdir / "zephyr/zmk.uf2"
    if ok and uf2.exists():
        (OUT / "artifacts").mkdir(parents=True, exist_ok=True)
        shutil.copy(uf2, OUT / "artifacts" / f"{name}.uf2")
        return True
    print(log.read_text()[-4000:], file=sys.stderr)
    return False


def main(argv: list[str]) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    selected = [r for r in rows() if not argv or r["artifact-name"] in argv]
    if argv and len(selected) != len(argv):
        print(f"unknown artifact in {argv}", file=sys.stderr)
        return 1
    results = {r["artifact-name"]: build(r) for r in selected}
    for name, ok in results.items():
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
