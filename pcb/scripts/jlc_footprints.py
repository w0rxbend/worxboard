# SPDX-License-Identifier: GPL-3.0-or-later
"""JLC's own footprint of every LCSC part on the boards, for the CPL placement check (cpl_check.py).

    python3 pcb/scripts/jlc_footprints.py [--cache DIR] [--out FILE] [C2040 C165948 ...]

JLC places a part by the footprint its parts library links to the LCSC number: the EasyEDA /
JLCEDA official-library footprint (https://easyeda.com, https://lceda.cn). Its origin is the
centroid JLC puts on the CPL's Mid X / Mid Y, and its zero orientation is what the CPL rotation turns.
This script fetches that footprint for each LCSC number (default: every number in design.py, both
halves, plus the fallbacks in FALLBACKS) and writes the geometry the check needs to
pcb/scripts/jlc_footprints.json:

  pads      number, shape, centre, size, rotation, outline polygon, layer (top / multi), hole
  holes     non-plated holes (locating pegs, socket barrels)
  leads     the part's own terminals (EasyEDA lead-shape layer): what must land on the KiCad pads
  body      the part's outline (component-shape layer): the hot-swap socket's notch around the post
  polarity  the pin-1 / cathode mark (component-polarity layer)

Coordinates are mm, relative to the footprint origin, in EasyEDA's frame (x right, y down, top view of
the part). Network only (CI never runs this; it reads the committed JSON). Source records:
  https://lceda.cn/api/products/<LCSC>/components   (easyeda.com's same API answers 403 from here)
  https://wmsc.lcsc.com/ftps/wm/product/detail?productCode=<LCSC>  (edaSvgInfo: the same footprint
  as an SVG, used as a cross-check of every pad centre)
Footprint data: JLCEDA/EasyEDA official library (https://lceda.cn/, https://easyeda.com).
"""
from __future__ import annotations

import json
import math
import re
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

UNIT = 0.254                       # EasyEDA canvas unit: 10 mil
API = "https://lceda.cn/api/products/{}/components?version=6.4.7"
LCSC_API = "https://wmsc.lcsc.com/ftps/wm/product/detail?productCode={}"
UA = {"User-Agent": "Mozilla/5.0 (worxboard jlc_footprints.py)"}
OUT = HERE / "jlc_footprints.json"
# Fallbacks named in design.py / docs (socket, crystal, display socket): checked so a swap stays safe
FALLBACKS = ["C49352235", "C9002", "C55218874"]
LAYER = {"1": "top", "2": "bottom", "11": "multi"}
ARC_STEP = math.radians(10)


def get(url: str, cache: Path | None, name: str) -> bytes:
    path = cache / name if cache else None
    if path and path.is_file():
        return path.read_bytes()
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        data = r.read()
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    time.sleep(0.3)
    return data


def num(s: str) -> float:
    return float(s) if s.strip() else 0.0


def arc_points(x0, y0, rx, ry, phi, large, sweep, x1, y1) -> list[tuple[float, float]]:
    """SVG elliptical arc (endpoint form) -> points after the start (SVG implementation notes F.6)."""
    if rx == 0 or ry == 0 or (x0, y0) == (x1, y1):
        return [(x1, y1)]
    c, s = math.cos(math.radians(phi)), math.sin(math.radians(phi))
    dx, dy = (x0 - x1) / 2, (y0 - y1) / 2
    xp, yp = c * dx + s * dy, -s * dx + c * dy
    rx, ry = abs(rx), abs(ry)
    lam = xp * xp / (rx * rx) + yp * yp / (ry * ry)
    if lam > 1:
        rx, ry = rx * math.sqrt(lam), ry * math.sqrt(lam)
    num_ = rx * rx * ry * ry - rx * rx * yp * yp - ry * ry * xp * xp
    den = rx * rx * yp * yp + ry * ry * xp * xp
    k = math.sqrt(max(0.0, num_ / den)) * (-1 if large == sweep else 1)
    cxp, cyp = k * rx * yp / ry, -k * ry * xp / rx
    cx, cy = c * cxp - s * cyp + (x0 + x1) / 2, s * cxp + c * cyp + (y0 + y1) / 2

    def ang(ux, uy, vx, vy):
        return math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)
    t0 = ang(1, 0, (xp - cxp) / rx, (yp - cyp) / ry)
    dt = ang((xp - cxp) / rx, (yp - cyp) / ry, (-xp - cxp) / rx, (-yp - cyp) / ry)
    if not sweep and dt > 0:
        dt -= 2 * math.pi
    elif sweep and dt < 0:
        dt += 2 * math.pi
    n = max(1, int(abs(dt) / ARC_STEP) + 1)
    pts = []
    for i in range(1, n + 1):
        t = t0 + dt * i / n
        ex, ey = rx * math.cos(t), ry * math.sin(t)
        pts.append((c * ex - s * ey + cx, s * ex + c * ey + cy))
    pts[-1] = (x1, y1)
    return pts


def path_polys(d: str) -> list[list[tuple[float, float]]]:
    """SVG path (M, L, A, Z, absolute; EasyEDA writes nothing else in footprints) -> closed polylines."""
    toks = re.findall(r"[MLAZmlaz]|-?\d*\.?\d+(?:e-?\d+)?", d)
    polys, cur, i, cmd = [], [], 0, None
    while i < len(toks):
        t = toks[i]
        if t.isalpha():
            cmd = t.upper()
            i += 1
            if cmd == "Z":
                if cur:
                    polys.append(cur)
                cur = []
            continue
        if cmd == "M":
            if cur:
                polys.append(cur)
            cur = [(float(toks[i]), float(toks[i + 1]))]
            i += 2
            cmd = "L"
        elif cmd == "L":
            cur.append((float(toks[i]), float(toks[i + 1])))
            i += 2
        elif cmd == "A":
            rx, ry, phi, large, sweep, x1, y1 = (float(v) for v in toks[i:i + 7])
            x0, y0 = cur[-1]
            cur += arc_points(x0, y0, rx, ry, phi, int(large), int(sweep), x1, y1)
            i += 7
        else:
            raise ValueError(f"path command {cmd!r} in {d[:60]!r}")
    if cur:
        polys.append(cur)
    return polys


def parse(record: dict) -> dict:
    pk = record["packageDetail"]
    ds = pk["dataStr"]
    ox, oy = float(ds["head"]["x"]), float(ds["head"]["y"])

    def mm(x: float, y: float) -> list[float]:
        return [round((x - ox) * UNIT, 4), round((y - oy) * UNIT, 4)]

    pads, holes, leads, cutouts, body, polarity = [], [], [], [], [], []
    for s in ds["shape"]:
        p = s.split("~")
        kind = p[0]
        if kind == "PAD":
            shape, cx, cy, w, h, layer, number, hole_r, pts, rot = (
                p[1], num(p[2]), num(p[3]), num(p[4]), num(p[5]), p[6], p[8], num(p[9]), p[10], num(p[11]))
            if layer not in LAYER:
                continue
            xy = [float(v) for v in pts.split()] if pts.strip() else []
            poly = [mm(xy[i], xy[i + 1]) for i in range(0, len(xy) - 1, 2)]
            if shape == "OVAL" and len(poly) == 2:     # OVAL: the points are the stadium's centre line
                poly = stadium(xy[0], xy[1], xy[2], xy[3], min(w, h) / 2, mm)
            elif len(poly) < 3:                         # ELLIPSE: no outline, approximate it
                poly = oval(cx, cy, w, h, rot, mm)
            pads.append({"num": number, "shape": shape, "at": mm(cx, cy), "size": [round(w * UNIT, 4),
                         round(h * UNIT, 4)], "rot": rot, "layer": LAYER[layer],
                         "hole": round(2 * hole_r * UNIT, 4), "poly": poly})
        elif kind == "HOLE":
            holes.append({"at": mm(num(p[1]), num(p[2])), "d": round(2 * num(p[3]) * UNIT, 4)})
        elif kind == "SOLIDREGION" and p[1] in ("99", "100"):
            polys = [[mm(x, y) for x, y in poly] for poly in path_polys(p[3])]
            if p[1] == "99":
                body += polys
            elif p[4].strip() == "cutout":
                cutouts += polys
            else:
                leads += polys
        elif kind == "CIRCLE" and p[5] == "101":
            polarity.append({"at": mm(num(p[1]), num(p[2])), "r": round(num(p[3]) * UNIT, 4)})
    return {"lcsc": record["lcsc"]["number"], "title": record.get("title", ""), "package": pk["title"],
            "updated": time.strftime("%Y-%m-%d", time.gmtime(int(pk.get("updateTime") or 0))),
            "pads": pads, "holes": holes, "leads": leads, "lead_cutouts": cutouts, "body": body,
            "polarity": polarity}


def stadium(x0, y0, x1, y1, r, mm) -> list[list[float]]:
    a = math.atan2(y1 - y0, x1 - x0)
    out = []
    for (x, y), start in (((x1, y1), a - math.pi / 2), ((x0, y0), a + math.pi / 2)):
        for i in range(19):
            t = start + math.pi * i / 18
            out.append(mm(x + r * math.cos(t), y + r * math.sin(t)))
    return out


def oval(cx, cy, w, h, rot, mm) -> list[list[float]]:
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    out = []
    for i in range(36):
        t = 2 * math.pi * i / 36
        u, v = w / 2 * math.cos(t), h / 2 * math.sin(t)
        out.append(mm(cx + c * u - s * v, cy + s * u + c * v))
    return out


def svg_pads(svg: str) -> dict[str, list[float]]:
    """Pad number -> centre (EasyEDA units) from the LCSC footprint SVG."""
    out = {}
    for m in re.finditer(r'<g c_partid="part_pad"[^>]*>', svg):
        tag = m.group(0)
        n = re.search(r'number="([^"]*)"', tag)
        o = re.search(r'c_origin="([^"]*)"', tag)
        if n and o:
            out.setdefault(n.group(1), []).append([float(v) for v in o.group(1).split(",")])
    return out


def cross_check(fp: dict, svg: str, origin: tuple[float, float]) -> float:
    """Worst pad-centre distance (mm) between the API record and the SVG; inf if a pad is missing."""
    worst = 0.0
    sp = svg_pads(svg)
    for pad in fp["pads"]:
        cands = sp.get(pad["num"], [])
        if not cands:
            return math.inf
        worst = max(worst, min(math.dist(pad["at"], [(x - origin[0]) * UNIT, (y - origin[1]) * UNIT])
                               for x, y in cands))
    return worst


def main(argv: list[str]) -> int:
    cache, out, codes = None, OUT, []
    it = iter(argv)
    for a in it:
        if a == "--cache":
            cache = Path(next(it))
        elif a == "--out":
            out = Path(next(it))
        else:
            codes.append(a)
    if not codes:
        from design import design
        codes = sorted({p.lcsc for side in ("left", "right") for p in design(side) if p.lcsc}) + FALLBACKS
    result = {}
    for code in codes:
        rec = json.loads(get(API.format(code), cache, f"lceda_{code}.json"))["result"]
        if rec["lcsc"]["number"] != code:
            raise SystemExit(f"{code}: the record is for {rec['lcsc']['number']}")
        fp = parse(rec)
        info = json.loads(get(LCSC_API.format(code), cache, f"lcsc_{code}.json"))["result"]
        svg_url = "https:" + info["edaSvgInfo"]["pcbSvg"]
        svg = get(svg_url, cache, f"svg_{code}.svg").decode()
        org = re.search(r'<g c_origin="([^"]*)"', svg)
        origin = tuple(float(v) for v in org.group(1).split(",")) if org else (0.0, 0.0)
        worst = cross_check(fp, svg, origin)
        fp["svg_check_mm"] = round(worst, 4)
        fp["source"] = API.format(code)
        result[code] = fp
        print(f"{code:10} {fp['package']:40} pads {len(fp['pads']):3} holes {len(fp['holes'])} "
              f"leads {len(fp['leads']):3} svg cross-check {worst:.4f} mm")
        if worst > 0.005:          # the SVG rounds centres to 0.01 unit (0.0025 mm)
            raise SystemExit(f"{code}: the API record and the LCSC SVG disagree by {worst:.3f} mm")
    out.write_text(json.dumps({"_source": "JLCEDA/EasyEDA official library (https://lceda.cn/, "
                                          "https://easyeda.com), fetched by pcb/scripts/jlc_footprints.py",
                               "_units": "mm, footprint origin, x right, y down, part top view",
                               **{k: result[k] for k in sorted(result)}}, indent=1, sort_keys=False) + "\n")
    print(f"{out}: {len(result)} parts")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
