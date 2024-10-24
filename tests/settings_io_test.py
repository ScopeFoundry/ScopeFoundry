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


class ChoiceListTest(unittest.TestCase):

    def setUp(self):
        print("setUp called")
        self.app = BaseMicroscopeApp([])
        self.app.add_measurement(Measure1(self))
        self.app.add_hardware(Hardware1(self))

    def test_initial_value_set(self):
        self.assertEqual(self.app.measurements.measure1.settings["string"], "0")
        self.assertEqual(self.app.measurements.measure1.settings["float"], 0.0)
        self.assertEqual(self.app.measurements.measure1.settings["choices"], 0)
        self.assertTrue(
            np.all(
                self.app.measurements.measure1.settings["array"]
                == np.array([False, False, False])
            )
        )
        self.assertEqual(self.app.hardware.hardware1.settings["string"], "0")
        self.assertEqual(self.app.hardware.hardware1.settings["float"], 0.0)
        self.assertEqual(self.app.hardware.hardware1.settings["choices"], 0)

    def test_all_correct(self):
        self.app.settings_load_ini("settings_io_test_correct.ini", show_report=False)
        self.assertEqual(self.app.measurements.measure1.settings["string"], "1")
        self.assertEqual(self.app.measurements.measure1.settings["float"], 1.0)
        self.assertEqual(self.app.measurements.measure1.settings["choices"], 1)
        self.assertEqual(self.app.hardware.hardware1.settings["string"], "1")
        self.assertEqual(self.app.hardware.hardware1.settings["float"], 1.0)
        self.assertEqual(self.app.hardware.hardware1.settings["choices"], 1)
        self.assertEqual(self.app.hardware.hardware1.settings["protected_int"], 0)

    def test_first_section_wrong_and_continue(self):
        self.app.settings_load_ini(
            "settings_io_test_measure1_false.ini", show_report=False
        )
        self.assertEqual(self.app.hardware.hardware1.settings["string"], "2")
        self.assertEqual(self.app.hardware.hardware1.settings["float"], 2.0)
        self.assertEqual(self.app.hardware.hardware1.settings["choices"], 2)

    def test_reporting(self):
        self.app.settings_load_ini(
            "settings_io_test_measure1_false_2.ini", show_report=False
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
        self.app.settings_load_ini(
            "settings_io_test_measure1_false_2.ini", show_report=False
        )
        self.assertTrue("meeeeeeasurement/measure1/straaaaang" in self.app._report)
        self.assertTrue(
            self.app._report["meeeeeeasurement/measure1/straaaaang"]
            is WRITE_RES.MISSING
        )

        self.assertEqual(self.app.hardware.hardware1.settings["string"], "2")
        self.assertEqual(self.app.hardware.hardware1.settings["float"], 2.0)
        self.assertEqual(self.app.hardware.hardware1.settings["choices"], 2)

    def test_first_setting_misspelled_and_continue(self):
        self.app.settings_load_ini(
            "settings_io_test_measure1_string_false.ini", show_report=False
        )
        # self.assertEqual(self.app.hardware.hardware1.settings["string"], "2")
        self.assertEqual(self.app.hardware.hardware1.settings["float"], 2.0)
        self.assertEqual(self.app.hardware.hardware1.settings["choices"], 2)

    def test_roundtrip(self):

        # all values are initial values
        self.app.settings_save_ini("settings_io_test_roundtrip.ini")

        # change them up
        self.app.measurements.measure1.settings["string"] = "1"
        self.app.measurements.measure1.settings["float"] = 1.0
        self.app.measurements.measure1.settings["choices"] = 1
        self.app.measurements.measure1.settings["array"] = np.array(
            [False, False, True]
        )
        self.app.hardware.hardware1.settings["string"] = "1"
        self.app.hardware.hardware1.settings["float"] = 1.0
        self.app.hardware.hardware1.settings["choices"] = 1

        # make sure they are changed
        self.assertFalse(
            np.all(
                self.app.measurements.measure1.settings["array"]
                == np.array([False, False, False])
            )
        )

        # load values
        self.app.settings_load_ini("settings_io_test_roundtrip.ini", show_report=False)
        self.assertEqual(self.app.measurements.measure1.settings["string"], "0")
        self.assertEqual(self.app.measurements.measure1.settings["float"], 0.0)
        self.assertEqual(self.app.measurements.measure1.settings["choices"], 0)
        self.assertTrue(
            np.all(
                self.app.measurements.measure1.settings["array"]
                == np.array([False, False, False])
            )
        )
        self.assertEqual(self.app.hardware.hardware1.settings["string"], "0")
        self.assertEqual(self.app.hardware.hardware1.settings["float"], 0.0)
        self.assertEqual(self.app.hardware.hardware1.settings["choices"], 0)


if __name__ == "__main__":
    unittest.main()
