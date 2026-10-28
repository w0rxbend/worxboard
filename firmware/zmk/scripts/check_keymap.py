# SPDX-License-Identifier: GPL-3.0-or-later
"""Check worxboard.keymap: 74 bindings per layer and base layer == layout.json legends (§5).

    python3 firmware/zmk/scripts/check_keymap.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
KEYMAP = ROOT / "firmware/zmk/config/worxboard.keymap"
LAYOUT_JSON = ROOT / "layout/build/layout.json"
KEYS = 74
LAYERS = 3

# §5 legend (QMK spelling) -> ZMK binding after #define expansion
LEGEND = {
    "=": "&kp EQUAL", "-": "&kp MINUS", "\\": "&kp BSLH", "'": "&kp SQT", "[": "&kp LBKT",
    "]": "&kp RBKT", ",": "&kp COMMA", ".": "&kp DOT",
    "DEL": "&kp DEL", "BSPC": "&kp BSPC", "LSFT": "&kp LSHFT", "RSFT": "&kp RSHFT",
    "LEFT": "&kp LEFT", "RGHT": "&kp RIGHT", "UP": "&kp UP", "DOWN": "&kp DOWN",
    "HOME": "&kp HOME", "END": "&kp END", "PGUP": "&kp PG_UP", "PGDN": "&kp PG_DN",
    "SPC": "&kp SPACE", "TAB": "&kp TAB", "ENT": "&kp RET", "LGUI": "&kp LGUI", "LALT": "&kp LALT",
    "TG(1)": "&tog 1", "TT(1)": "&tt 1 1", "LT(1,`)": "&lt 1 GRAVE", "LT(2,;)": "&lt 2 SEMI",
    "GUI_T(')": "&mt LGUI SQT", "CTL_T(Z)": "&mt LCTRL Z", "CTL_T(/)": "&mt LCTRL FSLH",
    "CTL_T(ESC)": "&mt LCTRL ESC", "ALT_T(APP)": "&mt LALT K_APP", "LA(LSFT)": "&kp LA(LSHFT)",
    "HYPER": "&kp LC(LS(LA(LGUI)))", "MEH": "&kp LC(LS(LALT))",
}


def expected(legend: str) -> str:
    if legend in LEGEND:
        return LEGEND[legend]
    if legend.isdigit():
        return f"&kp N{legend}"
    assert len(legend) == 1 and legend.isalpha(), legend
    return f"&kp {legend}"


def layers(text: str) -> dict[str, list[str]]:
    text = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)
    defines = dict(re.findall(r"^#define\s+(\w+)\s+(.+?)\s*$", text, flags=re.M))
    keymap = text[text.index("compatible = \"zmk,keymap\""):]
    out = {}
    for name, body in re.findall(r"(\w+)\s*\{[^{}]*?bindings\s*=\s*<(.*?)>;", keymap, flags=re.S):
        joined = " ".join(defines.get(t, t) for t in body.split())
        out[name] = ["&" + b.strip() for b in joined.split("&") if b.strip()]
    return out


def main() -> int:
    found = layers(KEYMAP.read_text())
    errors = []
    if len(found) != LAYERS:
        errors.append(f"{len(found)} layers, want {LAYERS}")
    for name, binds in found.items():
        if len(binds) != KEYS:
            errors.append(f"layer {name}: {len(binds)} bindings, want {KEYS}")
    data = json.loads(LAYOUT_JSON.read_text())
    legends = {s: {k["id"]: k["legend"] for k in v["keys"]} for s, v in data["sides"].items()}
    base = next(iter(found.values()))
    for i, (t, got) in enumerate(zip(data["transform_order"], base)):
        want = expected(legends[t["side"]][t["id"]])
        if got != want:
            errors.append(f"base[{i}] {t['side']} {t['id']}: {got!r}, want {want!r}")
    for e in errors:
        print(e, file=sys.stderr)
    if not errors:
        print(f"keymap ok: {len(found)} layers x {KEYS} bindings, base matches layout.json")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
