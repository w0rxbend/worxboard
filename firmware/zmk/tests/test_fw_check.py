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


# The RGB part of a generated zephyr.dts, in the format edtlib writes it (core rows, rev B)
GOOD_DTS = """/dts-v1/;

/ {
	chosen {
		zephyr,display = &nice_view;
		zmk,underglow = &led_strip;
	};
	vled: vled {
		compatible = "zmk,ext-power-generic";
		control-gpios = < &gpio0 0x17 0x0 >;
	};
	soc {
		pio0: pio@50200000 {
			compatible = "raspberrypi,pico-pio";
			status = "okay";
			pio0_ws2812: pio0_ws2812 {
				compatible = "worldsemi,ws2812-rpi_pico-pio";
				status = "okay";
				bit-waveform = < 0x3 >, < 0x3 >, < 0x4 >;
				led_strip: ws2812 {
					status = "okay";
					gpios = < &gpio0 0x16 0x0 >;
					chain-length = < 0x25 >;
					color-mapping = < 0x2 0x1 0x3 >;
					reset-delay = < 0x118 >;
					frequency = < 0xc3500 >;
				};
			};
		};
	};
};
"""
GOOD_CONFIG = "".join(f"{key}=y\n" for key in fw_check.RGB_KCONFIG) + "CONFIG_ZMK_RGB_UNDERGLOW_BRT_MAX=8\n"
GOOD_MAP = "".join(f" .text.{s}\n" for s in fw_check.RGB_SYMBOLS)


class RgbCheckTest(unittest.TestCase):
    """Core rows must carry the 37-LED strip on PIO0/GP22, ext-power on GP23 and the brightness cap."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.build = Path(temp.name)
        self.write(GOOD_CONFIG, GOOD_DTS, GOOD_MAP)

    def write(self, config, dts, link_map):
        (self.build / ".config").write_text(config)
        (self.build / "zephyr.dts").write_text(dts)
        (self.build / "zmk.map").write_text(link_map)

    def errors(self):
        return fw_check.check_rgb("core", self.build)

    def test_rev_b_build_passes(self):
        self.assertEqual(self.errors(), [])

    def test_brightness_cap(self):
        for line, ok in (("=8", True), ("=5", True), ("=9", False), ("=12", False), ("=100", False), (None, False)):
            with self.subTest(brt_max=line):
                config = GOOD_CONFIG.replace("CONFIG_ZMK_RGB_UNDERGLOW_BRT_MAX=8\n",
                                             f"CONFIG_ZMK_RGB_UNDERGLOW_BRT_MAX{line}\n" if line else "")
                self.write(config, GOOD_DTS, GOOD_MAP)
                self.assertEqual(self.errors() == [], ok, self.errors())

    def test_rgb_kconfig_is_required(self):
        for key in fw_check.RGB_KCONFIG:
            with self.subTest(key=key):
                self.write(GOOD_CONFIG.replace(f"{key}=y\n", ""), GOOD_DTS, GOOD_MAP)
                self.assertEqual(self.errors(), [f"core: {key} is not set"])

    def test_led_strip_is_required(self):
        broken = {
            "no chosen strip": GOOD_DTS.replace("\t\tzmk,underglow = &led_strip;\n", ""),
            "strip on pio1": GOOD_DTS.replace("pio0: pio@50200000", "pio1: pio@50300000"),
            "strip disabled": GOOD_DTS.replace('"worldsemi,ws2812-rpi_pico-pio";\n\t\t\t\tstatus = "okay"',
                                               '"worldsemi,ws2812-rpi_pico-pio";\n\t\t\t\tstatus = "disabled"'),
            "short chain": GOOD_DTS.replace("< 0x25 >", "< 0x24 >"),
            "wrong data pin": GOOD_DTS.replace("< &gpio0 0x16 0x0 >", "< &gpio0 0x18 0x0 >"),
            "RGB order": GOOD_DTS.replace("< 0x2 0x1 0x3 >", "< 0x1 0x2 0x3 >"),
        }
        for case, dts in broken.items():
            with self.subTest(case=case):
                self.write(GOOD_CONFIG, dts, GOOD_MAP)
                self.assertEqual(len(self.errors()), 1, self.errors())

    def test_ext_power_is_required(self):
        broken = {
            "missing": GOOD_DTS.replace('"zmk,ext-power-generic"', '"vnd,other"'),
            "wrong pin": GOOD_DTS.replace("< &gpio0 0x17 0x0 >", "< &gpio0 0x18 0x0 >"),
            "active low": GOOD_DTS.replace("< &gpio0 0x17 0x0 >", "< &gpio0 0x17 0x1 >"),
        }
        for case, dts in broken.items():
            with self.subTest(case=case):
                self.write(GOOD_CONFIG, dts, GOOD_MAP)
                errors = self.errors()
                self.assertEqual(len(errors), 1, errors)
                self.assertIn("ext-power", errors[0])

    def test_rgb_must_be_linked(self):
        for symbol in fw_check.RGB_SYMBOLS:
            with self.subTest(symbol=symbol):
                self.write(GOOD_CONFIG, GOOD_DTS, GOOD_MAP.replace(f" .text.{symbol}\n", ""))
                errors = self.errors()
                self.assertEqual(len(errors), 1, errors)
                self.assertIn(f"{symbol} missing", errors[0])
