# SPDX-License-Identifier: GPL-3.0-or-later
"""Order-file comparisons must notice geometry changes that preserve bulk properties."""
import struct
import zlib

import pytest
from build123d import Box, Cylinder, Pos, export_step, export_stl

from case.production import same


@pytest.mark.parametrize("ext,export", [("step", export_step), ("stl", export_stl)])
def test_moved_hole_is_not_the_same_part(tmp_path, ext, export):
    a = Box(30, 20, 5) - Pos(-7, 0, 0) * Cylinder(2, 10)
    b = Box(30, 20, 5) - Pos(7, 0, 0) * Cylinder(2, 10)
    assert a.volume == pytest.approx(b.volume)
    assert a.area == pytest.approx(b.area)
    pa, pb = tmp_path / f"a.{ext}", tmp_path / f"b.{ext}"
    export(a, pa)
    export(b, pb)
    assert not same(str(pa), str(pb))[0]


def test_step_metadata_can_differ(tmp_path):
    a, b = tmp_path / "a.step", tmp_path / "b.step"
    export_step(Box(30, 20, 5) - Cylinder(2, 10), a)
    b.write_text(a.read_text().replace("DATA;", "/* another exporter header */\nDATA;", 1))
    assert same(str(a), str(b))[0]


def test_step_checks_added_and_removed_material(tmp_path):
    a, b = tmp_path / "a.step", tmp_path / "b.step"
    export_step(Box(30, 20, 5), a)
    export_step(Box(30, 20, 5) - Cylinder(2, 10), b)
    assert not same(str(a), str(b))[0]
    assert not same(str(b), str(a))[0]


@pytest.mark.parametrize("reverse_winding", [False, True])
def test_stl_facet_order_is_ignored_but_winding_is_not(tmp_path, reverse_winding):
    a, b = tmp_path / "a.stl", tmp_path / "b.stl"
    export_stl(Box(30, 20, 5), a)
    data = a.read_bytes()
    facets = []
    for offset in range(84, len(data), 50):
        record = data[offset:offset + 50]
        v = [record[12:24], record[24:36], record[36:48]]
        vertices = (v[0], v[2], v[1]) if reverse_winding else (v[1], v[2], v[0])
        facets.append(record[:12] + b"".join(vertices) + record[48:])
    b.write_bytes(b"Different STL header".ljust(80, b" ") + data[80:84] + b"".join(reversed(facets)))
    assert same(str(a), str(b))[0] is not reverse_winding


def test_truncated_stl_cannot_pass(tmp_path):
    a, b = tmp_path / "a.stl", tmp_path / "b.stl"
    export_stl(Box(30, 20, 5), a)
    b.write_bytes(a.read_bytes()[:84] + struct.pack("<f", 0.0))
    with pytest.raises(ValueError, match="triangle count"):
        same(str(a), str(b))


def write_pdf(path, x=10, compressed=False, width=100):
    """Small valid drawing with a dimension label and an independently positioned outline."""
    stream = f"BT /F1 10 Tf 10 40 Td (M2.5) Tj ET\n{x} 10 6 6 re S\n".encode()
    if compressed:
        stream = zlib.compress(stream)
    filters = b" /Filter /FlateDecode" if compressed else b""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width} 60] "
         "/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>").encode(),
        b"<< /Length " + str(len(stream)).encode() + filters + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    data = b"%PDF-1.4\n"
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(data)
    data += f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode()
    data += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:])
    data += f"trailer\n<< /Root 1 0 R /Size {len(offsets)} >>\nstartxref\n{xref}\n%%EOF\n".encode()
    path.write_bytes(data)


def test_pdf_drawing_change_with_identical_text_fails(tmp_path):
    a, b = tmp_path / "a.pdf", tmp_path / "b.pdf"
    write_pdf(a, x=10)
    write_pdf(b, x=30)
    assert not same(str(a), str(b))[0]


def test_pdf_compression_can_differ(tmp_path):
    a, b = tmp_path / "a.pdf", tmp_path / "b.pdf"
    write_pdf(a)
    write_pdf(b, compressed=True)
    assert a.read_bytes() != b.read_bytes()
    assert same(str(a), str(b))[0]


def test_pdf_page_size_change_fails(tmp_path):
    a, b = tmp_path / "a.pdf", tmp_path / "b.pdf"
    write_pdf(a)
    write_pdf(b, width=120)
    assert not same(str(a), str(b))[0]
