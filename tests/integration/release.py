# SPDX-License-Identifier: GPL-3.0-or-later
"""Assemble the GitHub release assets from the `just all` outputs (spec §14 WS5).

    uv run python tests/integration/release.py [--version v0.1.0-revA] [--out dist] [--production]

Reads, relative to the repo root:
    just pcb-fab  build/<side>/jlc/{gerbers.zip,bom.csv,pos.csv}, {worxboard-<side>.step,edge.dxf}
    just fw       build/fw/artifacts/<artifact>.uf2 for every build.yaml row
    just model    case/exports/*.{step,stl}, case/exports/*_fitcheck.dxf, plates/*.dxf
Writes into --out (default dist/):
    worxboard-<version>-pcb-{left,right}.zip   JLCPCB gerbers.zip, bom.csv, pos.csv (CPL), STEP, Edge DXF
    <artifact>.uf2                              one per build.yaml row, named as in docs/firmware.md
    worxboard-<version>-case-step.zip           case STEP, fit-check and plate DXFs
    worxboard-<version>-case-stl.zip            case STL
    SHA256SUMS.txt, release-notes.md            checksums of the assets; notes for `gh release create`
Any missing input is an error. Zips are deterministic (sorted, fixed timestamps).
--production also copies the JLC files to pcb/production/<side>/ for a v*-revA hardware tag (§9).
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
REPO_URL = (os.environ.get("GITHUB_SERVER_URL", "https://github.com") + "/"
            + os.environ.get("GITHUB_REPOSITORY", "w0rxbend/worxboard"))      # release-note links


def artifacts(root: Path) -> list[str]:
    """build.yaml artifact names, in matrix order."""
    return re.findall(r"artifact-name:\s*(\w+)", (root / "build.yaml").read_text())


def plan(root: Path, version: str) -> dict[str, list[Path]]:
    """Asset name -> input files (a .uf2 asset is its single input, copied as is)."""
    out = {}
    for side in SIDES:
        b = root / "build" / side
        out[f"worxboard-{version}-pcb-{side}.zip"] = [
            *(b / "jlc" / f for f in JLC_FILES), b / f"worxboard-{side}.step", b / "edge.dxf",
            root / "LICENSE-HARDWARE"]
    for name in artifacts(root):
        out[f"{name}.uf2"] = [root / "build/fw/artifacts" / f"{name}.uf2"]
    exports = root / "case/exports"
    out[f"worxboard-{version}-case-step.zip"] = [
        *sorted(exports.glob("*.step")), *sorted(exports.glob("*_fitcheck.dxf")),
        *sorted((root / "plates").glob("*.dxf")), root / "LICENSE-HARDWARE"]
    out[f"worxboard-{version}-case-stl.zip"] = [*sorted(exports.glob("*.stl")), root / "LICENSE-HARDWARE"]
    return out


def missing(assets: dict[str, list[Path]]) -> list[str]:
    errs = [str(p) for files in assets.values() for p in files if not p.is_file()]
    errs += [f"{name}: no inputs" for name, files in assets.items()
             if not [p for p in files if p.name != "LICENSE-HARDWARE"]]
    return errs


def write_zip(dest: Path, files: list[Path]) -> None:
    """Deterministic zip with every file under a top folder named after the zip."""
    top = dest.stem
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(files, key=lambda p: p.name):
            info = zipfile.ZipInfo(f"{top}/{p.name}", ZIP_TIME)
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, p.read_bytes())


def changelog_section(root: Path, version: str) -> str:
    """The CHANGELOG section for this version (v0.1.0-revA -> [0.1.0-revA] or [0.1.0]), else Unreleased."""
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
    return f"""worxboard {version}: **pre-release**. Rev A has not been built or tested on hardware.

> [!WARNING]
> The open gates in [verification.md]({docs}/verification.md) block ordering: check the display
> stack, the TRRS jack and the LCSC stock of every line before ordering boards.

Flash `worxboard_left_central.uf2` on the left half (the host plugs in there) and
`worxboard_right_peripheral.uf2` on the right ([firmware.md]({docs}/firmware.md)). Order each PCB
zip as its own JLCPCB design ([ordering-jlcpcb.md]({docs}/ordering-jlcpcb.md)).

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
            shutil.copyfile(files[0], dest)
        written.append(dest)
    sums = (f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in written)
    (out / SUMS).write_text("".join(sums))
    (out / NOTES).write_text(notes(root, version, [p.name for p in written]))
    return [*written, out / SUMS]


def production(root: Path) -> None:
    """Copy the JLC files to pcb/production/<side>/ (force-added on hardware tags only)."""
    for side in SIDES:
        dest = root / "pcb/production" / side
        dest.mkdir(parents=True, exist_ok=True)
        for f in JLC_FILES:
            shutil.copyfile(root / "build" / side / "jlc" / f, dest / f)


def git_version(root: Path) -> str:
    r = subprocess.run(["git", "describe", "--tags", "--always", "--dirty"], cwd=root,
                       capture_output=True, text=True)
    return r.stdout.strip() or "dev"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--version", help="release name (default: git describe)")
    ap.add_argument("--out", type=Path, default=ROOT / "dist")
    ap.add_argument("--production", action="store_true", help="also fill pcb/production/<side>/")
    args = ap.parse_args(argv)
    version = (args.version or git_version(ROOT)).replace("/", "-")
    for p in assemble(ROOT, args.out, version):
        print(f"{p.stat().st_size:>10}  {p}")
    if args.production:
        production(ROOT)
        print("pcb/production/{left,right}/ filled: git add -f pcb/production before tagging")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
