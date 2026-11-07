# SPDX-License-Identifier: GPL-3.0-or-later
"""The post-build display gates: both portrait orientations, the SSD1306 driver, the custom screen."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("fw_check", Path(__file__).parents[1] / "scripts/fw_check.py")
fw_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fw_check)


MAP = "worx_display_rotation_init\nflush_rotated\n.text.ssd1306_init\n"


class DisplayCheckTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.build = Path(temp.name)
        (self.build / "zmk.map").write_text(MAP)

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
                (self.build / "zmk.map").write_text("worx_display_rotation_init\n.text.ssd1306_init\n")
                errors = fw_check.check_display("core", self.build)
                self.assertEqual(len(errors), 1)
                self.assertIn("flush_rotated missing", errors[0])

    def test_ssd1306_must_be_linked_and_ls0xx_not(self):
        self.config(90)
        (self.build / "zmk.map").write_text("worx_display_rotation_init\nflush_rotated\n")
        self.assertIn("SSD1306 driver not linked", fw_check.check_display("core", self.build)[0])
        (self.build / "zmk.map").write_text(MAP + ".text.ls0xx_init\n")
        self.assertIn("retired display driver", fw_check.check_display("core", self.build)[0])


class ScreenCheckTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.build = Path(temp.name)
        (self.build / "zmk.map").write_text(MAP)

    def config(self, screen=True, heap=8192):
        (self.build / ".config").write_text(
            ("CONFIG_WORXBOARD_STATUS_SCREEN=y\n" if screen else "") + f"CONFIG_LV_Z_MEM_POOL_SIZE={heap}\n")

    def test_custom_screen_with_its_heap_passes(self):
        self.config()
        self.assertEqual(fw_check.check_screen("core", self.build), [])

    def test_missing_screen_small_heap_or_ble_symbols_fail(self):
        self.config(screen=False)
        self.assertIn("WORXBOARD_STATUS_SCREEN", fw_check.check_screen("core", self.build)[0])
        self.config(heap=4096)
        self.assertIn("MEM_POOL_SIZE 4096", fw_check.check_screen("core", self.build)[0])
        self.config()
        (self.build / "zmk.map").write_text(MAP + "zmk_ble_active_profile_index\n")
        self.assertIn("forbidden symbols", fw_check.check_screen("core", self.build)[0])
