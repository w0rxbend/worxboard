# SPDX-License-Identifier: GPL-3.0-or-later
"""Exported files: committed, current, deterministic and well-formed."""
import json
import xml.etree.ElementTree as ET

from layout import export as E


def test_export_deterministic():
    assert E.outputs() == E.outputs()


def test_committed_files_current():
    for p in E.COMMITTED:
        assert p.exists(), f"{p} missing: run `just layout`"
        assert p.read_text() == E.outputs()[p], f"{p} stale: run `just layout`"


def test_layout_json_schema():
    d = json.loads(E.layout_json())
    assert d["schema"] == E.SCHEMA and d["mirror_x"] == 260.0
    assert len(d["transform_order"]) == 74
    for side in ("left", "right"):
        s = d["sides"][side]
        assert len(s["keys"]) == 37
        assert {"keys", "display", "jacks", "anchors", "holes", "outline", "zones"} <= s.keys()
        assert {"Z_BACK", "Z_TRRS"} == s["zones"].keys()
        assert len(s["holes"]) == 8
        assert {"type"} <= s["outline"]["segments"][0].keys()


def test_kle_has_74_keys():
    rows = json.loads(E.kle_json())
    assert isinstance(rows[0], dict) and len(rows) == 1 + 74


def test_svg_well_formed():
    root = ET.fromstring(E.layout_svg())
    assert root.tag.endswith("svg")
