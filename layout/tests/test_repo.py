# SPDX-License-Identifier: GPL-3.0-or-later
"""Repo hygiene from spec §12 (WS0)."""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
GIT = shutil.which("git")


def ignored(path: str) -> bool:
    r = subprocess.run([GIT, "check-ignore", "-q", "--no-index", path], cwd=ROOT)
    return r.returncode == 0


@pytest.mark.skipif(GIT is None or not (ROOT / ".git").exists(), reason="needs a git checkout")
def test_gitignore_rules():
    assert not ignored("zephyr/module.yml")
    assert not ignored("layout/build/layout.json")
    for p in ("build/x", "zmk/x", "modules/x", ".west/x", "pcb/.tools/x", "case/exports/x",
              "pcb/left/worxboard-left-backups/x", "pcb/left/fp-info-cache",
              "pcb/left/worxboard-left.kicad_prl", "pcb/production/left/gerbers.zip"):
        assert ignored(p), p


def test_stream_justfiles_exist():
    for p in ("layout/layout.just", "firmware/firmware.just", "pcb/pcb.just", "case/case.just",
              "site/site.just"):
        assert (ROOT / p).exists(), p
        assert f"import '{p}'" in (ROOT / "justfile").read_text()
