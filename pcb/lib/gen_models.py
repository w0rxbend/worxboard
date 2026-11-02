# SPDX-License-Identifier: GPL-3.0-or-later
"""Write the vendored 3D models of pcb/lib (run once per model change; the STEP is committed).

    uv run --group case python pcb/lib/gen_models.py

  pcb/lib/worxboard.3dshapes/PinSocket_1x05_P2.54mm_Vertical_H5.0mm.step
      J3, Hong Cheng HC-PM254-5.0H-1x5PZ (LCSC C27985230): 1x5 2.54 mm female socket, 5.0 mm tall.
      KiCad's library only has the 8.5 mm socket, which would put a wrong body into the board STEP
      that the case fit check reads (docs/deviations.md ELEC-3).

Dimensions from the C27985230 drawing (Hong Cheng, rev A), taken at their upper tolerance because
the model feeds a clearance check: body (B + 0.4) +-0.3 = 13.1 +-0.3 long for B = 12.70, 2.4 +-0.15
wide, H = 5.0 +-0.15 tall; contacts 0.64 x 0.4 with a 3.0 +-0.2 mm tail. KiCad model frame: origin at
pin 1 on the PCB top, pins along -y (the footprint's +y), z up. The STEP header carries no date and
the model no colours (OCCT writes colour styles in hash order), so a re-run writes the same file.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from build123d import Align, Box, Compound, Location, Pos, export_step

OUT = Path(__file__).resolve().parent / "worxboard.3dshapes"

PITCH = 2.54
PINS = 5
BODY = (2.4 + 0.15, (PINS - 1) * PITCH + 2.54 + 0.4 + 0.3, 5.0 + 0.15)   # x, y, z (upper tolerance)
CONTACT = (0.64, 0.4)
TAIL = 3.0 + 0.2
ENTRY = (1.0, 1.0, 1.0)            # square contact entry at the top face (looks only)


def pin_socket_h5() -> Compound:
    name = "PinSocket_1x05_P2.54mm_Vertical_H5.0mm"
    yc = -(PINS - 1) * PITCH / 2
    body = Pos(0, yc, 0) * Box(*BODY, align=(Align.CENTER, Align.CENTER, Align.MIN))
    for i in range(PINS):
        body -= Pos(0, -i * PITCH, BODY[2] - ENTRY[2]) * Box(*ENTRY, align=(Align.CENTER, Align.CENTER, Align.MIN))
    body.label = f"{name}_body"
    tails = []
    for i in range(PINS):
        tail = Location((0, -i * PITCH, 0)) * Box(*CONTACT, TAIL, align=(Align.CENTER, Align.CENTER, Align.MAX))
        tail.label = f"pin{i + 1}"
        tails.append(tail)
    pins = Compound(children=tails, label=f"{name}_pins")
    return Compound(children=[body, pins], label=name)


def write_step(shape: Compound, path: Path) -> None:
    export_step(shape, str(path))
    text = path.read_text()
    text = re.sub(r"FILE_NAME\('[^']*','[^']*'", f"FILE_NAME('{path.name}','1970-01-01T00:00:00'", text, count=1)
    path.write_text(text)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "PinSocket_1x05_P2.54mm_Vertical_H5.0mm.step"
    write_step(pin_socket_h5(), path)
    print(f"wrote {path.relative_to(OUT.parent.parent.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
