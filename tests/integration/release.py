# SPDX-License-Identifier: GPL-3.0-or-later
"""Assemble the GitHub release assets from the `just all` outputs (spec §14 WS5).

    uv run python tests/integration/release.py [--version v0.2.0-revB] [--out dist]

Reads, relative to the repo root:
    committed     pcb/production/<side>/ (JLC panel package, bare-board/, pcbway/), case/production/
    just pcb-fab  build/<side>/jlc/{gerbers.zip,bom.csv,pos.csv}, {worxboard-<side>.step,edge.dxf}
    just fw       build/fw/artifacts/<artifact>.uf2 for every build.yaml row
    just model    case/exports/*.{step,stl}, case/exports/*_fitcheck.dxf, plates/*.dxf
Writes into --out (default dist/):
    worxboard-<version>-order-{left,right}.zip  the order package pcb/production/<side>/ as committed: what
                                                docs/ordering-jlcpcb.md and ordering-pcbway.md upload
    worxboard-<version>-case-order.zip          case/production/ as committed (JLCCNC, JLC3DP, PCBWay notes)
    worxboard-<version>-pcb-{left,right}.zip    bare-board gerbers.zip, bom.csv, pos.csv (CPL), STEP, Edge DXF
    <artifact>.uf2                              one per build.yaml row, named as in docs/firmware.md
    worxboard-<version>-case-step.zip           case STEP, fit-check and plate DXFs
    worxboard-<version>-case-stl.zip            case STL
    SHA256SUMS.txt, release-notes.md            checksums of the assets; notes for `gh release create`
Any missing input is an error. Zips are deterministic (sorted, fixed timestamps). The order zips keep
the folders of their package; pcb.yml and case.yml prove those packages on the same tag.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SIDES = ("left", "right")
JLC_FILES = ("gerbers.zip", "bom.csv", "pos.csv")
ZIP_TIME = (1980, 1, 1, 0, 0, 0)
SUMS, NOTES = "SHA256SUMS.txt", "release-notes.md"
LICENSE = "LICENSE-HARDWARE"
PCBWAY = "pcbway/"                      # every order package carries its PCBWay files
REPO_URL = (os.environ.get("GITHUB_SERVER_URL", "https://github.com") + "/"
            + os.environ.get("GITHUB_REPOSITORY", "w0rxbend/worxboard"))      # release-note links


def artifacts(root: Path) -> list[str]:
    """build.yaml artifact names, in matrix order."""
    return re.findall(r"artifact-name:\s*(\w+)", (root / "build.yaml").read_text())


def flat(*files: Path) -> dict[str, Path]:
    """Zip member name -> file, every file in the zip's top folder."""
    return {p.name: p for p in files}


def package(root: Path, folder: Path) -> dict[str, Path]:
    """Zip member name -> file for a committed order package: its folders are kept (bom.csv exists in
    the package root, in bare-board/ and in pcbway/)."""
    files = sorted(p for p in folder.rglob("*") if p.is_file())
    return {p.relative_to(folder).as_posix(): p for p in files} | flat(root / LICENSE)


def plan(root: Path, version: str) -> dict[str, dict[str, Path]]:
    """Asset name -> {zip member name: input file} (a .uf2 asset is its single input, copied as is)."""
    out = {}
    for side in SIDES:
        b = root / "build" / side
        out[f"worxboard-{version}-order-{side}.zip"] = package(root, root / "pcb/production" / side)
        out[f"worxboard-{version}-pcb-{side}.zip"] = flat(
            *(b / "jlc" / f for f in JLC_FILES), b / f"worxboard-{side}.step", b / "edge.dxf", root / LICENSE)
    out[f"worxboard-{version}-case-order.zip"] = package(root, root / "case/production")
    for name in artifacts(root):
        out[f"{name}.uf2"] = flat(root / "build/fw/artifacts" / f"{name}.uf2")
    exports = root / "case/exports"
    out[f"worxboard-{version}-case-step.zip"] = flat(
        *sorted(exports.glob("*.step")), *sorted(exports.glob("*_fitcheck.dxf")),
        *sorted((root / "plates").glob("*.dxf")), root / LICENSE)
    out[f"worxboard-{version}-case-stl.zip"] = flat(*sorted(exports.glob("*.stl")), root / LICENSE)
    return out


def missing(assets: dict[str, dict[str, Path]]) -> list[str]:
    errs = [str(p) for files in assets.values() for p in files.values() if not p.is_file()]
    errs += [f"{name}: no inputs" for name, files in assets.items() if not set(files) - {LICENSE}]
    errs += [f"{name}: no {PCBWAY} files" for name, files in assets.items()
             if "-order" in name and not any(member.startswith(PCBWAY) for member in files)]
    return errs


def write_zip(dest: Path, files: dict[str, Path]) -> None:
    """Deterministic zip with every member under a top folder named after the zip."""
    top = dest.stem
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for member, path in sorted(files.items()):
            info = zipfile.ZipInfo(f"{top}/{member}", ZIP_TIME)
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, path.read_bytes())


def changelog_section(root: Path, version: str) -> str:
    """The CHANGELOG section for this version (v0.2.0-revB -> [0.2.0-revB] or [0.2.0]), else Unreleased."""
    text = (root / "CHANGELOG.md").read_text()
    bare = version.removeprefix("v")
    for title in (bare, bare.split("-")[0], "Unreleased"):
        m = re.search(rf"^## \[{re.escape(title)}\][^\n]*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
        if m:
            return m.group(1).strip()
    return ""


def notes(root: Path, version: str, assets: list[str]) -> str:
    docs = f"{REPO_URL}/blob/{version}/docs"
    listing = "\n".join(f"- `{a}`" for a in [*assets, SUMS])
    revision = re.search(r"rev([A-Z])", version)
    hardware = f"Rev {revision.group(1)}" if revision else "This revision"
    return f"""worxboard {version}: **pre-release**. {hardware} has not been built or tested on hardware.

Order each half from its `order-<side>.zip`, the checked package of `pcb/production/<side>/`, as its
own design: [ordering-jlcpcb.md]({docs}/ordering-jlcpcb.md), or
[ordering-pcbway.md]({docs}/ordering-pcbway.md) with the `pcbway/` folder. The case is
`case-order.zip` ([case/production]({REPO_URL}/blob/{version}/case/production/README.md)). Check the
live stock of every BOM line on the day you order; [verification.md]({docs}/verification.md) lists
the gates that were run.

Flash `worxboard_left_central.uf2` on the left half (the host plugs in there) and
`worxboard_right_peripheral.uf2` on the right ([firmware.md]({docs}/firmware.md)).

Assets:

{listing}

{changelog_section(root, version)}
"""


def assemble(root: Path, out: Path, version: str) -> list[Path]:
    assets = plan(root, version)
    errs = missing(assets)
    if errs:
        raise SystemExit("release inputs missing (run `just all`):\n  " + "\n  ".join(errs))
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    written = []
    for name, files in assets.items():
        dest = out / name
        if name.endswith(".zip"):
            write_zip(dest, files)
        else:
            (source,) = files.values()
            shutil.copyfile(source, dest)
        written.append(dest)
    sums = (f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in written)
    (out / SUMS).write_text("".join(sums))
    (out / NOTES).write_text(notes(root, version, [p.name for p in written]))
    return [*written, out / SUMS]


def git_version(root: Path) -> str:
    r = subprocess.run(["git", "describe", "--tags", "--always", "--dirty"], cwd=root,
                       capture_output=True, text=True)
    return r.stdout.strip() or "dev"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--version", help="release name (default: git describe)")
    ap.add_argument("--out", type=Path, default=ROOT / "dist")
    args = ap.parse_args(argv)
    version = (args.version or git_version(ROOT)).replace("/", "-")
    for p in assemble(ROOT, args.out, version):
        print(f"{p.stat().st_size:>10}  {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
