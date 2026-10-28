# Changelog

This project uses [Semantic Versioning](https://semver.org/). Hardware releases are tagged
`v<version>-revA` and publish gerbers, BOM/CPL, UF2 firmware and case files.

## [Unreleased]

### Added

- `layout/`, the single source of truth for both halves:
  - 37 keys per half from the original ErgoDox PCB, with the 25° thumb cluster
  - the nice!view display in the old C6R0 slot
  - USB-C and TRRS anchors, the mounting holes (#7 moved), the PCB outline and the top-side zones
  - the frozen RP2040 GPIO map (`pins.py`)
- `python -m layout.export` writes `layout/build/layout.json`, `docs/images/layout.svg` and
  `build/kle.json`. `just layout-check` runs the WS0 acceptance tests and the no-diff check.
- Root `justfile` that imports each stream's `*.just`. `pyproject.toml` and `uv.lock`
  (Python 3.12; groups `layout`, `case`, `dev`).
- `tools/kicad_env.sh`, `tools/fetch_freerouting.sh` and `tools/images.lock`.
- CI: `.github/workflows/layout.yml`.
- `LICENSE-HARDWARE` (CERN-OHL-S-2.0), `THIRD_PARTY.md` and `docs/deviations.md`.

### Changed

- `.gitignore` no longer ignores `/zephyr/` (the ZMK module lives at `zephyr/module.yml`). It now
  ignores `/build/`, `pcb/.tools/`, `case/exports/`, and `pcb/production/` outside hardware tags.
