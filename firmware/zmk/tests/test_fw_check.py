# SPDX-License-Identifier: GPL-3.0-or-later
"""Both documented portrait orientations must pass the post-build display gate."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("fw_check", Path(__file__).parents[1] / "scripts/fw_check.py")
fw_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fw_check)


class DisplayCheckTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.build = Path(temp.name)
        (self.build / "zmk.map").write_text("worx_display_rotation_init\nflush_rotated\n")

    def config(self, *angles):
        (self.build / ".config").write_text("".join(
            f"CONFIG_WORXBOARD_DISPLAY_ROTATION_{angle}=y\n" for angle in angles))

    def test_both_supported_orientations_pass(self):
        for angle in (90, 270):
            with self.subTest(angle=angle):
                self.config(angle)
                self.assertEqual(fw_check.check_display("core", self.build), [])

    def test_missing_or_conflicting_orientation_fails(self):
        for angles in ((), (90, 270)):
            with self.subTest(angles=angles):
                self.config(*angles)
                self.assertTrue(fw_check.check_display("core", self.build))

    def test_rotation_must_still_be_linked(self):
        for angle in (90, 270):
            with self.subTest(angle=angle):
                self.config(angle)
                (self.build / "zmk.map").write_text("worx_display_rotation_init\n")
                errors = fw_check.check_display("core", self.build)
                self.assertEqual(len(errors), 1)
                self.assertIn("flush_rotated missing", errors[0])
