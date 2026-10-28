<div align="center">

# worxboard

**An ErgoDox EZ-style split keyboard with an on-board RP2040, ZMK wired split, a nice!view-class LCD
on each half and USB-C on both halves.**

[![layout](https://github.com/w0rxbend/worxboard/actions/workflows/layout.yml/badge.svg)](https://github.com/w0rxbend/worxboard/actions/workflows/layout.yml)
[![License: GPL v3](https://img.shields.io/badge/code-GPLv3-blue.svg)](LICENSE)
[![License: CERN-OHL-S-2.0](https://img.shields.io/badge/hardware-CERN--OHL--S--2.0-blue.svg)](LICENSE-HARDWARE)

![Layout of both halves](docs/images/layout.svg)

</div>

worxboard keeps the exact ErgoDox key positions and the 25° six-key thumb cluster. The top key of
the inner column on each half is replaced by a vertical memory LCD. The two halves link over TRRS
with ZMK's wired split. Everything is generated from one layout package ([`layout/`](layout/)): the
KiCad PCB, the build123d case, the ZMK physical layout and the docs.

> **Status:** rev A, in development. The frozen design is [`docs/design.md`](docs/design.md), and
> agreed deviations are in [`docs/deviations.md`](docs/deviations.md).

The original concept sketch:

![Concept sketch](docs/images/concept-annotated.png)

## Features

<!-- WS4 -->
_To be written (WS4)._

## Build Guide

<!-- WS4: docs/buildguide_en.md -->
_To be written (WS4)._

## Firmware

<!-- WS1 / WS4: docs/firmware.md -->
_To be written (WS1, WS4)._

## PCB

<!-- WS2 / WS4 -->
_To be written (WS2, WS4)._

## Case and plates

<!-- WS3 / WS4: docs/case.md, docs/legs.md -->
_To be written (WS3, WS4)._

## Ordering

<!-- WS4: docs/ordering-jlcpcb.md, docs/bom.md -->
_To be written (WS4)._

## Repository layout

| Path | Contents |
|---|---|
| [`layout/`](layout/) | Single source of truth: keys, thumbs, display, jacks, holes, outline, zones, GPIO map; `layout/build/layout.json` |
| `pcb/` | KiCad 10 project per half, libraries, generator scripts |
| `case/`, `plates/` | build123d case and plate DXFs |
| `firmware/`, `zephyr/`, `build.yaml` | ZMK board module (RP2040) |
| [`docs/`](docs/) | Design spec, build guide, BOM, electrical notes |
| [`tools/`](tools/) | Container helpers and pinned image digests |
| `site/` | Microsite generator |

## Development

You need [uv](https://docs.astral.sh/uv/), [just](https://just.systems/) and Docker (for KiCad and ZMK).

```sh
just setup          # .venv with every Python group
just layout         # regenerate layout.json, layout.svg, build/kle.json
just layout-check   # WS0 acceptance tests + no-diff check
just --list         # every recipe, including the pcb/, case/, firmware/ and site/ ones
```

## License

- Code (`layout/`, `pcb/scripts/`, `case/*.py`, `firmware/`, `tools/`, `site/`): [GPL-3.0](LICENSE).
- Hardware (`pcb/` KiCad files and libraries, case geometry outputs, `plates/`, `docs/`):
  [CERN-OHL-S-2.0](LICENSE-HARDWARE). **Maintainer to confirm** this split before the first hardware tag.
- Third-party material: [`THIRD_PARTY.md`](THIRD_PARTY.md).
