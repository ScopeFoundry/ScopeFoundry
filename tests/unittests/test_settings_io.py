from pathlib import Path
import unittest

import numpy as np

from ScopeFoundry import BaseMicroscopeApp, HardwareComponent, Measurement
from ScopeFoundry.base_app.base_app import WRITE_RES


class Measure1(Measurement):
    name = "measure1"

    def setup(self):
        self.settings.New("string", str, ro=True, initial="0")
        self.settings.New("float", float, ro=True, initial=0.0)
        self.settings.New("choices", int, choices=INITIAL_CHOICES)
        self.settings.New("array", bool, is_array=True, initial=[False, False, False])


class Hardware1(HardwareComponent):
    name = "hardware1"

    def setup(self):
        self.settings.New("string", str, ro=True, initial="0")
        self.settings.New("float", float, ro=True, initial=0.0)
        self.settings.New("choices", int, choices=INITIAL_CHOICES)
        self.settings.New("protected_int", int, initial=0, protected=True)


INITIAL_CHOICES = [("choice 0", 0), ("choice 1", 1), ("choice 2", 2), ("choice 3", 3)]


class SettingsIOTest(unittest.TestCase):

    def setUp(self):
        self.app = BaseMicroscopeApp([])
        self.ms = self.app.add_measurement(Measure1(self.app))
        self.hw = self.app.add_hardware(Hardware1(self.app))
        self.root = Path(__file__).parent

        self.mms = self.ms.settings
        self.hws = self.hw.settings

    def test_initial_value_set(self):
        self.assertEqual(self.mms["string"], "0")
        self.assertEqual(self.mms["float"], 0.0)
        self.assertEqual(self.mms["choices"], 0)
        self.assertTrue(np.all(self.mms["array"] == np.array([False, False, False])))
        self.assertEqual(self.hws["string"], "0")
        self.assertEqual(self.hws["float"], 0.0)
        self.assertEqual(self.hws["choices"], 0)

    def test_all_correct(self):
        self.app.settings_load_ini(
            self.root / "settings_io_test_correct.ini",
            show_report=False,
        )
        self.assertEqual(self.mms["string"], "1")
        self.assertEqual(self.mms["float"], 1.0)
        self.assertEqual(self.mms["choices"], 1)
        self.assertEqual(self.hws["string"], "1")
        self.assertEqual(self.hws["float"], 1.0)
        self.assertEqual(self.hws["choices"], 1)
        self.assertEqual(self.hws["protected_int"], 0)

    def test_first_section_wrong_and_continue(self):
        self.app.settings_load_ini(
            self.root / "settings_io_test_measure1_false.ini", show_report=False
        )
        self.assertEqual(self.hws["string"], "2")
        self.assertEqual(self.hws["float"], 2.0)
        self.assertEqual(self.hws["choices"], 2)

    def test_reporting(self):
        self.app.settings_load_ini(
            self.root / "settings_io_test_measure1_false_2.ini", show_report=False
        )
        self.assertTrue("meeeeeeasurement/measure1/straaaaang" in self.app._report)
        self.assertTrue(
            self.app._report["meeeeeeasurement/measure1/straaaaang"]
            is WRITE_RES.MISSING
        )
        self.assertTrue(
            self.app._report["hardware/hardware1/protected_int"], "PROTECTED"
        )

    def test_first_section_wrong_and_continue(self):
        fname = self.root / "settings_io_test_measure1_false_2.ini"
        self.app.settings_load_ini(fname, show_report=False)
        self.assertTrue("meeeeeeasurement/measure1/straaaaang" in self.app._report)
        self.assertTrue(
            self.app._report["meeeeeeasurement/measure1/straaaaang"]
            is WRITE_RES.MISSING
        )

        self.assertEqual(self.hws["string"], "2")
        self.assertEqual(self.hws["float"], 2.0)
        self.assertEqual(self.hws["choices"], 2)

    def test_first_setting_misspelled_and_continue(self):
        self.app.settings_load_ini(
            self.root / "settings_io_test_measure1_string_false.ini",
            show_report=False,
        )
        # self.assertEqual(self.hw1["string"], "2")
        self.assertEqual(self.hws["float"], 2.0)
        self.assertEqual(self.hws["choices"], 2)

    def test_roundtrip(self):

        # all values are initial values
        self.app.settings_save_ini(self.root / "settings_io_test_roundtrip.ini")

        # change them up
        self.mms["string"] = "1"
        self.mms["float"] = 1.0
        self.mms["choices"] = 1
        self.mms["array"] = np.array([False, False, True])
        self.hws["string"] = "1"
        self.hws["float"] = 1.0
        self.hws["choices"] = 1

        # make sure they are changed
        self.assertFalse(np.all(self.mms["array"] == np.array([False, False, False])))

        # load values
        self.app.settings_load_ini(
            self.root / "settings_io_test_roundtrip.ini", show_report=False
        )
        self.assertEqual(self.mms["string"], "0")
        self.assertEqual(self.mms["float"], 0.0)
        self.assertEqual(self.mms["choices"], 0)
        self.assertTrue(np.all(self.mms["array"] == np.array([False, False, False])))
        self.assertEqual(self.hws["string"], "0")
        self.assertEqual(self.hws["float"], 0.0)
        self.assertEqual(self.hws["choices"], 0)


if __name__ == "__main__":
    unittest.main()
