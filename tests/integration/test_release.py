# SPDX-License-Identifier: GPL-3.0-or-later
"""Release assembly (tests/integration/release.py) and the release workflow (spec §14 WS5).

The assembly runs on a synthetic build tree, so it is tested without `just all`; when the real
outputs exist (after `just all`), it also runs on them and the assets are opened and checked.
"""
from __future__ import annotations

import csv
import io
import re
import shutil
import zipfile
from pathlib import Path

import pytest

import release

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/release.yml"
VERSION = "v9.9.9-revA"
UF2_MAGIC = b"UF2\n"                    # first word of every UF2 block (0x0A324655)
STEP_MAGIC = b"ISO-10303-21;"
JLC_POS_HEADER = ["Designator", "Mid X", "Mid Y", "Layer", "Rotation"]
COPIED = ("build.yaml", "CHANGELOG.md", "LICENSE-HARDWARE")


def fake_tree(root: Path) -> None:
    """The output layout of `just all`, with placeholder contents."""
    for name in COPIED:
        shutil.copyfile(ROOT / name, root / name)
    for side in release.SIDES:
        jlc = root / "build" / side / "jlc"
        jlc.mkdir(parents=True)
        board = (jlc.parent / f"worxboard-{side}.step", jlc.parent / "edge.dxf")
        for f in (*(jlc / n for n in release.JLC_FILES), *board):
            f.write_text(f"{side} {f.name}\n")
    uf2 = root / "build/fw/artifacts"
    uf2.mkdir(parents=True)
    for name in release.artifacts(root):
        (uf2 / f"{name}.uf2").write_bytes(UF2_MAGIC + name.encode())
    exports, plates = root / "case/exports", root / "plates"
    exports.mkdir(parents=True)
    plates.mkdir()
    for f in ("worxboard_left_top.step", "worxboard_left_top.stl", "worxboard_left_fitcheck.dxf",
              "worxboard_leg.step", "worxboard_leg.stl"):
        (exports / f).write_text(f)
    (plates / "worxboard-plate-left.dxf").write_text("plate")


def members(path: Path) -> set[str]:
    with zipfile.ZipFile(path) as z:
        return set(z.namelist())


def test_assets_from_a_fake_tree(tmp_path):
    fake_tree(tmp_path)
    out = tmp_path / "dist"
    written = {p.name for p in release.assemble(tmp_path, out, VERSION)}
    uf2s = {f"{a}.uf2" for a in release.artifacts(tmp_path)}
    assert len(uf2s) == 6 and {"worxboard_left_central.uf2", "worxboard_right_peripheral.uf2"} <= uf2s
    assert written == {f"worxboard-{VERSION}-pcb-left.zip", f"worxboard-{VERSION}-pcb-right.zip",
                       f"worxboard-{VERSION}-case-step.zip", f"worxboard-{VERSION}-case-stl.zip",
                       release.SUMS, *uf2s}
    top = f"worxboard-{VERSION}-pcb-left/"
    assert members(out / f"worxboard-{VERSION}-pcb-left.zip") == {
        top + f for f in (*release.JLC_FILES, "worxboard-left.step", "edge.dxf", "LICENSE-HARDWARE")}
    top = f"worxboard-{VERSION}-case-step/"
    assert members(out / f"worxboard-{VERSION}-case-step.zip") == {
        top + f for f in ("worxboard_left_top.step", "worxboard_leg.step", "worxboard_left_fitcheck.dxf",
                          "worxboard-plate-left.dxf", "LICENSE-HARDWARE")}
    lines = (out / release.SUMS).read_text().splitlines()
    sums = {name: digest for digest, name in (line.split("  ") for line in lines)}
    assert set(sums) == written - {release.SUMS}
    notes = (out / release.NOTES).read_text()
    assert "pre-release" in notes and all(f"`{a}`" in notes for a in written)


def test_assembly_is_reproducible(tmp_path):
    fake_tree(tmp_path)
    a, b = tmp_path / "a", tmp_path / "b"
    release.assemble(tmp_path, a, VERSION)
    release.assemble(tmp_path, b, VERSION)
    assert (a / release.SUMS).read_text() == (b / release.SUMS).read_text()


@pytest.mark.parametrize("gone", ["build/fw/artifacts/worxboard_right_peripheral.uf2",
                                  "build/left/jlc/pos.csv", "build/right/worxboard-right.step"])
def test_missing_input_fails(tmp_path, gone):
    fake_tree(tmp_path)
    (tmp_path / gone).unlink()
    with pytest.raises(SystemExit, match=re.escape(gone)):
        release.assemble(tmp_path, tmp_path / "dist", VERSION)


def test_no_case_exports_fails(tmp_path):
    fake_tree(tmp_path)
    shutil.rmtree(tmp_path / "case/exports")
    with pytest.raises(SystemExit, match="case-stl.zip: no inputs"):
        release.assemble(tmp_path, tmp_path / "dist", VERSION)


def test_notes_take_the_changelog_section(tmp_path):
    fake_tree(tmp_path)
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [Unreleased]\n\nnext\n\n## [9.9.9-revA] - 2030-01-01\n\nthis one\n")
    assert release.changelog_section(tmp_path, VERSION) == "this one"
    assert release.changelog_section(tmp_path, "v1.0.0") == "next"


REAL = release.plan(ROOT, VERSION)


@pytest.mark.skipif(bool(release.missing(REAL)), reason="build outputs missing (just all)")
def test_assets_from_the_real_build(tmp_path):
    out = tmp_path / "dist"
    release.assemble(ROOT, out, VERSION)
    for side in release.SIDES:
        with zipfile.ZipFile(out / f"worxboard-{VERSION}-pcb-{side}.zip") as z:
            top = f"worxboard-{VERSION}-pcb-{side}/"
            gerbers = zipfile.ZipFile(io.BytesIO(z.read(top + "gerbers.zip"))).namelist()
            assert any(n.endswith(".gtl") for n in gerbers) and any(n.endswith(".drl") for n in gerbers)
            assert any(n.endswith("EdgeCuts.gm1") for n in gerbers)
            pos = list(csv.reader(io.StringIO(z.read(top + "pos.csv").decode())))
            assert pos[0] == JLC_POS_HEADER and len(pos) > 1
            bom = list(csv.DictReader(io.StringIO(z.read(top + "bom.csv").decode())))
            assert bom and all(r["LCSC"].startswith("C") for r in bom)
            assert z.read(top + f"worxboard-{side}.step").startswith(STEP_MAGIC)
    for a in release.artifacts(ROOT):
        assert (out / f"{a}.uf2").read_bytes()[:4] == UF2_MAGIC
    with zipfile.ZipFile(out / f"worxboard-{VERSION}-case-step.zip") as z:
        steps = [n for n in z.namelist() if n.endswith(".step")]
        assert {"worxboard_left_top.step", "worxboard_right_bottom.step", "worxboard_leg.step"} <= \
            {Path(n).name for n in steps}
        assert all(z.read(n).startswith(STEP_MAGIC) for n in steps)
    with zipfile.ZipFile(out / f"worxboard-{VERSION}-case-stl.zip") as z:
        assert {"worxboard_left_top.stl", "worxboard_right_top.stl"} <= {Path(n).name for n in z.namelist()}


# ---- .github/workflows/release.yml ---------------------------------------------------------------

def test_release_workflow_runs_only_on_version_tags():
    text = WORKFLOW.read_text()
    on = re.search(r"^on:\n((?:[ \t]+.*\n)+)", text, re.M).group(1)
    assert re.fullmatch(r"\s*push:\n\s*tags:\s*\[\s*\"v\*\"\s*\]\s*", on), \
        f"release.yml must trigger on v* tags only:\n{on}"


def test_release_workflow_publishes_the_assembled_assets_as_a_prerelease():
    text = WORKFLOW.read_text()
    assert "tests/integration/release.py" in text and "pytest tests/integration" in text
    assert "gh release create" in text and "--prerelease" in text and "--verify-tag" in text
