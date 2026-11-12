# SPDX-License-Identifier: GPL-3.0-or-later
"""Assemble the GitHub Pages microsite.

Copies the static product page (site/web/), layout/build/layout.json, the doc images and the case
renders and, when they exist, the case STLs from case/exports/. Writes manifest.json with the case
part stats, leg placements, the gallery list and the PCB components: every assembled part of the
committed boards (pcb/<side>/*.kicad_pcb) as a box at its footprint position, sized from the
footprint's Fab outline. The case STLs are optional (`just model`).

The manifest also carries the copper figures of one half (track segments, length and nets per layer,
vias) for the page's layer view, and the drawing of each layer when `just pcb-layers` has made them:
those are optional too, and the page says so when they are missing.

Renders the build guide: one page per Markdown file of GUIDE_STEPS, in the page frame of
site/guide.template.html, plus guide.html as their index. The Markdown stays the single source, so
the site and the repository cannot drift apart; the build fails if a link between two guide pages
names an anchor that does not exist.

usage: build_site.py <out dir> [version]
"""
from __future__ import annotations

import html
import inspect
import json
import math
import re
import shutil
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from string import Template

import numpy as np
from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import layout as L  # noqa: E402
import pcbdata as PCB  # noqa: E402

WEB = ROOT / "site/web"
LAYOUT_JSON = ROOT / "layout/build/layout.json"
CASE_DIR = ROOT / "case"
CASE_EXPORTS = CASE_DIR / "exports"
IMAGE_DIRS = (ROOT / "docs/images", CASE_DIR / "renders")
COPPER_SIDE = "left"      # the half the layer view shows
COPPER_DRAWINGS = ROOT / "build" / COPPER_SIDE / "layers"   # <layer>.svg, written by `just pcb-layers`
COPPER = {"F.Cu": "f", "In1.Cu": "in1", "In2.Cu": "in2", "B.Cu": "b"}   # KiCad layer -> its name on the page
REPO = "https://github.com/w0rxbend/worxboard"
GUIDE_TEMPLATE = ROOT / "site/guide.template.html"
GUIDE_INDEX = "guide"   # guide.html, the index of the guide pages


@dataclass(frozen=True)
class Guide:
    slug: str      # the page is <slug>.html
    source: str    # its Markdown file, from the repository root
    title: str     # short name, for the navigation
    summary: str   # one sentence, for the guide index


# The build path in the order a builder walks it: (step, what happens in it, its pages).
GUIDE_STEPS = (
    ("Get the boards",
     "Two circuit boards, one per half. A factory can fit all 201 parts of each for you, or you can solder them yourself.",
     (Guide("order-jlcpcb", "docs/ordering-jlcpcb.md", "Order at JLCPCB",
            "Both boards, fully assembled: the files to upload, every form field, the placement check and the cost."),
      Guide("order-pcbway", "docs/ordering-pcbway.md", "Order at PCBWay",
            "The same boards from PCBWay, with its own parts list and placement files."),
      Guide("solder-at-home", "docs/soldering-at-home.md", "Solder it at home",
            "Bare boards and loose parts instead of factory assembly: what it takes and how to go about it."))),
    ("Buy the rest",
     "What no factory sends: switches, keycaps, stabilisers, displays, cables and screws.",
     (Guide("shopping-list", "docs/shopping-list.md", "Shopping list",
            "Every off-board part for one keyboard, with quantities and what to look for."),)),
    ("Order the case",
     "Machined aluminium for the shells, trays and legs, 3D prints for the spacers and foot caps. Test the boards first.",
     (Guide("case", "docs/case.md", "The case",
            "How the case is built up, its files, and the test print to make before any aluminium is cut."),
      Guide("order-case-cnc", "case/production/jlccnc/ORDER_NOTES.md", "Machined parts at JLCCNC",
            "The CNC order: one upload per part, the form settings and the remarks to paste."),
      Guide("order-case-print", "case/production/jlc3dp/ORDER_NOTES.md", "Printed parts at JLC3DP",
            "The plate spacers and the tree of leg foot caps."),
      Guide("order-case-pcbway", "case/production/pcbway/ORDER_NOTES.md", "The case at PCBWay",
            "The same case files, ordered from PCBWay instead."))),
    ("Assemble",
     "Test the bare boards, fit the displays, close the case, push in the switches and keycaps.",
     (Guide("assemble", "docs/buildguide_en.md", "Assemble it",
            "From a box of parts to a keyboard, step by step, with a troubleshooting list."),)),
    ("Bring it to life",
     "Flash both halves, then make the layout and the lights your own.",
     (Guide("firmware", "docs/firmware.md", "Firmware",
            "Get the ZMK firmware, flash it, change the keymap and control the lights."),)),
)
GUIDES = tuple(g for _, _, pages in GUIDE_STEPS for g in pages)
ALERTS = {"NOTE": "Note", "TIP": "Tip", "IMPORTANT": "Important", "WARNING": "Warning", "CAUTION": "Caution"}

AL_DENSITY = 2.70e-3      # g/mm3, 6061
CAD_ORIGIN = (130.0, 100.0)   # KiCad -> CAD frame: (x - OX, -(y - OY)), as in the reference case
LAYOUT_BODIES = ("J3",)       # drawn from `layout` (the header up to the display module)
SKIP_REFS = ("SK", "H", "STAB_", "J", "TP", "JP")   # sockets/jacks drawn from layout; holes; copper only
# footprint library -> (body height mm, viewer material)
PART_BODY = {
    "Package_DFN_QFN": (0.9, "chip"), "Package_SO": (1.75, "chip"), "Crystal": (0.8, "metal"),
    "Package_TO_SOT_SMD": (1.1, "chip"), "Diode_SMD": (1.1, "chip"), "Fuse": (0.85, "passive"),
    "Resistor_SMD": (0.35, "chip"), "Capacitor_SMD": (0.5, "passive"), "Button_Switch_SMD": (2.0, "metal"),
}
CASE_PARTS = {  # stl stem (after "worxboard_") -> label, material, role
    "right_top": ("Right top shell", "alu", "top"),
    "right_bottom": ("Right bottom tray", "alu", "bottom"),
    "right_spacer": ("Right plate spacer", "print", "spacer"),
    "left_top": ("Left top shell", "alu", "top"),
    "left_bottom": ("Left bottom tray", "alu", "bottom"),
    "left_spacer": ("Left plate spacer", "print", "spacer"),
    "leg": ("Tent leg", "alu", "leg"),
    "leg_cap": ("Leg foot cap", "tpu", "leg_cap"),
}
GALLERY = {  # image stem -> (caption, group), in gallery order; unknown images follow with their file name
    "layout": ("Layout of both halves, generated from layout/: ErgoDox stagger, 25° thumbs, the display in the C6R0 slot", "layout"),
    "pcb-left-top": ("Left PCB, top: RP2040, flash, USB-C J1, BOOT/RESET, JP1, display socket J3, TRRS jack J2 on the inner bump", "pcb"),
    "pcb-right-top": ("Right PCB, top: mirrored, same netlist; both boards print DO NOT HOT-PLUG TRRS by J2", "pcb"),
    "pcb-left-bottom": ("Left PCB, bottom: 37 hot-swap sockets, 37 diodes and 37 LEDs", "pcb"),
    "pcb-right-bottom": ("Right PCB, bottom: 37 sockets, 37 diodes and 37 LEDs, all fitted by the fab", "pcb"),
    "pair_top_iso": ("Both CNC top shells: the plate is milled into the key well, with 2u stabiliser cut-outs and a display window", "case"),
    "right_with_legs": ("Closed right-half case with its three custom tent legs", "case"),
    "right_top_underside": ("Right top shell, underside: plate webbing, screw bosses, display pocket", "case"),
    "right_bottom_tray": ("Right bottom tray: the socket cavity and the eight M2.5 screw posts", "case"),
    "right_back_usb": ("Back wall of the right half: USB-C notch, BOOT/RESET pin holes, display bezel", "case"),
    "spacer": ("3D-printed plate spacer, right half (this render predates the stabiliser-wire channels)", "case"),
    "leg": ("Custom 6061 tent leg with its TPU foot cap", "case"),
    "leg_cap_tree": ("The TPU print: 8 foot caps on one tree (6 + 2 spares)", "case"),
    "leg_section": ("Outer leg mount section: M3 tapped pad and Ø10 boss", "case"),
    "section": ("Six sections through the right half: key column, display column, across the display, back-edge screws, USB-C, TRRS", "case"),
    "overlay": ("The right-half case over the PCB layout: case outline, PCB, key well, display pocket, window, zones, bosses", "case"),
    "cpl-sk-hotswap-socket": ("Placement proof, hot-swap sockets (bottom)", "proof"),
    "cpl-d101-diode-sod123f": ("Placement proof, matrix diodes (bottom)", "proof"),
    "cpl-u1-rp2040-qfn56": ("Placement proof, U1 RP2040 QFN-56", "proof"),
    "cpl-u2-flash-soic8": ("Placement proof, U2 QSPI flash SOIC-8", "proof"),
    "cpl-u3-ldo-sot23-5": ("Placement proof, U3 3.3 V LDO SOT-23-5", "proof"),
    "cpl-u4-u5-esd-sot23-6": ("Placement proof, U4 and U5 ESD arrays", "proof"),
    "cpl-y1-crystal-3225": ("Placement proof, Y1 12 MHz crystal", "proof"),
    "cpl-d1-schottky-sod123": ("Placement proof, D1 Schottky on the USB power path", "proof"),
    "cpl-c-0402": ("Placement proof, 0402 capacitors", "proof"),
    "cpl-r-0402": ("Placement proof, 0402 resistors", "proof"),
    "cpl-f1-ptc-1206": ("Placement proof, F1 polyfuse on the TRRS power line", "proof"),
    "cpl-j1-usb-c": ("Placement proof, J1 USB-C, mouth over the back edge", "proof"),
    "cpl-j2-trrs-pj320d": ("Placement proof, J2 TRRS jack on the inner bump", "proof"),
    "cpl-j3-display-socket": ("Placement proof, J3 display socket", "proof"),
    "cpl-sw-tact-ts1088": ("Placement proof, SW1 and SW2 BOOT and RESET switches", "proof"),
    "cpl-led-smd-4p-l3-2-w2-8-ls5-9-sk6812mini-e": ("Placement proof, SK6812MINI-E LEDs (bottom)", "proof"),
    "cpl-c0603": ("Placement proof, 0603 capacitors", "proof"),
    "cpl-sot-23-5-l2-9-w1-6-p0-95-ls2-8-br": ("Placement proof, SOT-23-5 on JLC's L2.9-W1.6 footprint", "proof"),
    "cpl-sot-23-5-l3-0-w1-7-p0-95-ls2-8-bl": ("Placement proof, SOT-23-5 on JLC's L3.0-W1.7 footprint", "proof"),
}
WIDE = ("pair_top_iso", "section")   # layout.svg is shown full width in its own section
GALLERY_SKIP = ("site-viewer",)   # screenshots of this page: copied (for the link preview), not listed
IMAGE_EXT = (".png", ".svg", ".jpg")


def stl_stats(path: Path):
    """Bounding box, enclosed volume and triangle count of a binary STL."""
    data = path.read_bytes()
    n = struct.unpack("<I", data[80:84])[0]
    rec = np.frombuffer(data[84:84 + 50 * n],
                        dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]))
    v = rec["v"].astype(np.float64)
    vol = np.einsum("ij,ij->i", v[:, 0], np.cross(v[:, 1], v[:, 2])).sum() / 6
    pts = v.reshape(-1, 3)
    return pts.min(0), pts.max(0), abs(vol), n


def case_module():
    """The WS3 case module, or None if it is missing or its CAD deps are not installed."""
    sys.path.insert(0, str(CASE_DIR))
    try:
        import worxboard_case  # noqa: PLC0415
        return worxboard_case
    except Exception as e:  # noqa: BLE001  (optional input: any import failure means "no case")
        print(f"  note: case model not importable ({type(e).__name__}: {e}); no leg placements")
        return None


def leg_placements(ec) -> list[list[float]]:
    """4x4 row-major matrix per right-half mount that seats a leg on its boss at swing 0
    (same construction as the reference ErgoDox site); the viewer adds the swing about local Z."""
    if ec is None or not hasattr(ec, "leg_mounts"):
        return []
    from build123d import Pos, Rot  # noqa: PLC0415
    takes_side = inspect.signature(ec.leg_mounts).parameters  # WS3 port: leg_mounts(side)
    mounts = ec.leg_mounts("right") if takes_side else ec.leg_mounts()
    out = []
    for (px, py), (nx, ny) in mounts:
        loc = (Pos(px, py, 0) * Rot(0, 0, math.degrees(math.atan2(-ny, -nx)))
               * Pos(0, 0, ec.LEG_Z) * Rot(0, -90, 0) * Pos(0, 0, ec.LEG_BOSS_H))
        t = loc.wrapped.Transformation()
        m = [[t.Value(r, c) for c in range(1, 5)] for r in range(1, 4)] + [[0, 0, 0, 1]]
        out.append([round(x, 6) for row in m for x in row])
    return out


def case_parts(out: Path) -> dict:
    parts = {}
    for stem, (label, mat, role) in CASE_PARTS.items():
        src = CASE_EXPORTS / f"worxboard_{stem}.stl"
        if not src.exists():
            continue
        (out / "models").mkdir(exist_ok=True)
        shutil.copyfile(src, out / "models" / f"{stem}.stl")
        lo, hi, vol, tris = stl_stats(src)
        parts[stem] = dict(label=label, material=mat, role=role, file=f"models/{stem}.stl",
                           triangles=int(tris), size=[round(float(x), 1) for x in hi - lo],
                           mass_g=round(vol * AL_DENSITY, 1) if mat == "alu" else None,
                           volume_cm3=round(vol / 1000, 1))
    return parts


def gallery(out: Path) -> list[dict]:
    shots = []
    (out / "images").mkdir()
    for d in IMAGE_DIRS:
        if not d.is_dir():
            continue
        for p in sorted(d.iterdir()):
            if p.suffix not in IMAGE_EXT:
                continue
            shutil.copyfile(p, out / "images" / p.name)
            if p.stem.startswith(GALLERY_SKIP):
                continue
            caption, group = GALLERY.get(p.stem, (p.stem, "other"))
            shots.append(dict(file=f"images/{p.name}", caption=caption, group=group, wide=p.stem in WIDE))
    order = list(GALLERY)
    return sorted(shots, key=lambda s: order.index(Path(s["file"]).stem) if Path(s["file"]).stem in order else len(order))


def copper(out: Path) -> dict:
    """The layer view's data: the track figures of each copper layer of one half and its vias, and the
    layers' drawings, copied to layers/ when `just pcb-layers` has made all four."""
    board = PCB.copper(COPPER_SIDE)
    drawn = all((COPPER_DRAWINGS / f"{name}.svg").exists() for name in COPPER)
    layers = {}
    for name, key in COPPER.items():
        tracks = board.layers.get(name, PCB.Tracks(count=0, length=0.0, nets=0))
        layers[key] = dict(name=name, tracks=tracks.count, length_mm=round(tracks.length), nets=tracks.nets)
        if drawn:
            (out / "layers").mkdir(exist_ok=True)
            shutil.copyfile(COPPER_DRAWINGS / f"{name}.svg", out / "layers" / f"{key}.svg")
            layers[key]["file"] = f"layers/{key}.svg"
    return dict(side=COPPER_SIDE, vias=board.vias, drawn=drawn, layers=layers)


def bodies() -> dict:
    """Layout part rectangles per side (KiCad frame) the viewer draws itself."""
    return {s: {ref: list(L.part_rect(s, ref)) for ref in LAYOUT_BODIES} for s in L.SIDES}


def components(side: str) -> list[dict]:
    """Assembled parts of the committed board: footprint pose and Fab-outline box (KiCad frame)."""
    out = []
    for f in sorted(PCB.footprints(side).values(), key=lambda f: PCB.ref_key(f.ref)):
        lib = f.lib.split(":")[0]
        if f.ref.startswith(SKIP_REFS) or f.body is None or lib not in PART_BODY:
            continue
        h, mat = PART_BODY[lib]
        x0, y0, x1, y1 = f.body
        out.append(dict(ref=f.ref, value=f.value, part=f.lib.split(":")[1], side=f.side,
                        at=[f.x, f.y, f.rot], box=[round((x0 + x1) / 2, 3), round((y0 + y1) / 2, 3),
                                                   round(x1 - x0, 3), round(y1 - y0, 3), h], mat=mat))
    return out


# ---------- guide pages ----------
def heading_slug(text: str, used: dict[str, int]) -> str:
    """The anchor GitHub gives a heading, so the links inside the Markdown files work unchanged."""
    slug = re.sub(r"[^\w\- ]", "", text.strip().lower()).replace(" ", "-")
    seen = used.get(slug, 0)
    used[slug] = seen + 1
    return f"{slug}-{seen}" if seen else slug


def site_url(target: str, source: Path) -> str:
    """Where a link or image of the Markdown file `source` points once that file is a site page."""
    if re.match(r"[a-z][a-z0-9+.-]*:|#", target):
        return target   # another site, or an anchor in the same page
    path, _, fragment = target.partition("#")
    dest = (source.parent / path).resolve()
    anchor = f"#{fragment}" if fragment else ""
    page = next((g.slug for g in GUIDES if ROOT / g.source == dest), None)
    if page:
        return f"{page}.html{anchor}"
    if dest.parent in IMAGE_DIRS and dest.suffix in IMAGE_EXT:
        return f"images/{dest.name}"   # gallery() copies both image folders there
    kind = "tree" if dest.is_dir() else "blob"
    return f"{REPO}/{kind}/main/{dest.relative_to(ROOT).as_posix()}{anchor}"


def without_contents(tokens: list) -> list:
    """Drop a "Contents" section: the page frame lists the headings beside the text."""
    kept, skipping = [], False
    for i, tok in enumerate(tokens):
        if tok.type == "heading_open":
            skipping = tokens[i + 1].content.strip() == "Contents"
        if not skipping:
            kept.append(tok)
    return kept


@dataclass(frozen=True)
class Page:
    slug: str
    title: str
    description: str
    body: str                             # HTML of the article
    sections: tuple[tuple[str, str], ...]  # (anchor, text) of each h2
    anchors: frozenset[str] = frozenset()  # every heading anchor, for the link check
    source: str = ""                      # the Markdown file it was rendered from, if any


def render_guide(md: MarkdownIt, guide: Guide) -> Page:
    """One Markdown file as a guide page: GitHub's heading anchors, links and images moved to the site."""
    source = ROOT / guide.source
    tokens = without_contents(md.parse(source.read_text()))
    used: dict[str, int] = {}
    title, sections, anchors = guide.title, [], set()
    for i, tok in enumerate(tokens):
        if tok.type == "heading_open":
            text = "".join(c.content for c in tokens[i + 1].children if c.type in ("text", "code_inline"))
            anchor = heading_slug(text, used)
            anchors.add(anchor)
            tok.attrSet("id", anchor)
            if tok.tag == "h1":
                title = text
            elif tok.tag == "h2":
                sections.append((anchor, text))
        for child in tok.children or ():
            if child.type == "link_open":
                child.attrSet("href", site_url(child.attrGet("href"), source))
            elif child.type == "image":
                child.attrSet("src", site_url(child.attrGet("src"), source))
                child.attrSet("loading", "lazy")
    body = md.renderer.render(tokens, md.options, {})
    body = re.sub(r"<blockquote>\s*<p>\[!(%s)\]\s*" % "|".join(ALERTS),
                  lambda m: f'<blockquote class="alert {m[1].lower()}"><p><b>{ALERTS[m[1]]}</b> ', body)
    body = body.replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")
    return Page(guide.slug, title, guide.summary, body, tuple(sections), frozenset(anchors), guide.source)


def guide_index() -> Page:
    """guide.html: the build path, one entry per step with its pages."""
    steps = "".join(
        f"<li><h2>{html.escape(step)}</h2><p>{html.escape(blurb)}</p><ul>"
        + "".join(f'<li><a href="{g.slug}.html"><b>{html.escape(g.title)}</b><span>{html.escape(g.summary)}</span></a></li>'
                  for g in pages)
        + "</ul></li>"
        for step, blurb, pages in GUIDE_STEPS)
    body = (
        "<h1>Build your worxboard</h1>"
        '<p class="lede">worxboard is free and open source, so nobody sells it: you order the parts from the factories '
        "yourself and put them together. These pages take you through it in five steps, from the first upload to a "
        "keyboard you type on.</p>"
        '<blockquote class="alert important"><p><b>Important</b> Revision B passes every check on the design files, '
        "but no board has been built yet. Order two assembled boards per half, then flash and test them before you "
        f'pay for the aluminium case. <a href="{REPO}/blob/main/docs/verification.md">What is verified</a></p></blockquote>'
        f'<ol class="path">{steps}</ol>')
    return Page(GUIDE_INDEX, "Build guide", "How to order, assemble and flash a worxboard, step by step.", body, ())


def guide_menu(current: str) -> str:
    """The guide's pages grouped by step; the page being read is marked."""
    def link(slug: str, text: str, cls: str = "") -> str:
        mark = ' aria-current="page"' if slug == current else ""
        return f'<a{cls} href="{slug}.html"{mark}>{html.escape(text)}</a>'

    steps = "".join(
        f"<li><span>{html.escape(step)}</span><ul>"
        + "".join(f"<li>{link(g.slug, g.title)}</li>" for g in pages) + "</ul></li>"
        for step, _, pages in GUIDE_STEPS)
    return link(GUIDE_INDEX, "Build guide", ' class="guide-home"') + f"<ol>{steps}</ol>"


def pager(slug: str) -> str:
    """Links to the pages before and after `slug` on the build path."""
    def link(guide: Guide, rel: str, label: str) -> str:
        return f'<a rel="{rel}" href="{guide.slug}.html"><span>{label}</span>{html.escape(guide.title)}</a>'

    i = next(i for i, g in enumerate(GUIDES) if g.slug == slug)
    before = link(GUIDES[i - 1], "prev", "Before") if i > 0 else "<span></span>"
    after = link(GUIDES[i + 1], "next", "Next") if i + 1 < len(GUIDES) else "<span></span>"
    return f'<nav class="pager" aria-label="Previous and next page">{before}{after}</nav>'


def check_guide_links(pages: list[Page]) -> None:
    """Stop the build if a link between two guide pages names an anchor its target does not have."""
    anchors = {p.slug: p.anchors for p in pages}
    broken = [f"{p.slug}.html -> {target}.html#{fragment}"
              for p in pages
              for target, fragment in re.findall(r'href="([\w-]+)\.html#([^"]+)"', p.body)
              if target in anchors and fragment not in anchors[target]]
    if broken:
        raise SystemExit("guide pages: broken anchors:\n  " + "\n  ".join(broken))


def page_html(frame: Template, page: Page, version: str) -> str:
    toc = "".join(f'<li><a href="#{a}">{html.escape(t)}</a></li>' for a, t in page.sections)
    source = (f'<p class="source">This page is <a href="{REPO}/blob/main/{page.source}">{page.source}</a> '
              "in the repository.</p>" + pager(page.slug)) if page.source else ""
    return frame.substitute(
        title=html.escape(page.title), description=html.escape(page.description, quote=True),
        menu=guide_menu(page.slug), body=page.body + source,
        toc=f"<p>On this page</p><ul>{toc}</ul>" if toc else "", version=html.escape(version))


def guide_pages(out: Path, version: str) -> dict[str, str]:
    """Write guide.html and one page per guide; returns {Markdown source: page slug}."""
    md = MarkdownIt("commonmark", {"html": True}).enable("table")
    pages = [render_guide(md, g) for g in GUIDES]
    check_guide_links(pages)
    frame = Template(GUIDE_TEMPLATE.read_text())
    for page in (guide_index(), *pages):
        (out / f"{page.slug}.html").write_text(page_html(frame, page, version))
    return {p.source: p.slug for p in pages}


def main(out: Path, version: str) -> int:
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(WEB, out)
    shutil.copyfile(LAYOUT_JSON, out / "layout.json")
    ec = case_module()
    parts = case_parts(out)
    manifest = dict(
        version=version, repo=REPO,
        cad_origin=[getattr(ec, "OX", CAD_ORIGIN[0]), getattr(ec, "OY", CAD_ORIGIN[1])],
        bodies=bodies(), components={s: components(s) for s in L.SIDES},
        parts=parts, legs=leg_placements(ec) if parts else [], gallery=gallery(out),
        guides=guide_pages(out, version), copper=copper(out),
    )
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    (out / ".nojekyll").touch()
    total = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    print(f"site: {out} ({total / 1e6:.1f} MB), version {version}")
    print(f"  {len(parts)} case parts, {len(manifest['legs'])} leg mounts, {len(manifest['gallery'])} images, "
          f"{len(manifest['guides'])} guide pages, {sum(len(c) for c in manifest['components'].values())} PCB components")
    if not manifest["copper"]["drawn"]:
        print(f"  no copper layer drawings: run `just pcb-layers {COPPER_SIDE}` first to show them in the layer view")
    for name, p in parts.items():
        print(f"  {name:13s} {p['triangles']:6d} tris  {p['size']}  {p['mass_g']} g")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else "dev"))
