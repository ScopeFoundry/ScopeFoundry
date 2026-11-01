from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from ScopeFoundry import BaseMicroscopeApp, HardwareComponent, Measurement
from ScopeFoundry.base_app.base_app import WRITE_RES
from ScopeFoundry.base_app.profile_manager import ProfileManager
from ScopeFoundry.tests.unittests.unittest_helpers import close_app_widgets


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
        self._app_implementation_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._app_implementation_dir.cleanup)
        implementation_dir_patch = patch.object(
            ProfileManager,
            "_app_implementation_dir",
            return_value=Path(self._app_implementation_dir.name),
        )
        implementation_dir_patch.start()
        self.addCleanup(implementation_dir_patch.stop)
        self.app = BaseMicroscopeApp([])
        self.addCleanup(close_app_widgets, self.app)
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

    def test_resolve_and_remove_missing(self):
        src = self.root / "settings_io_test_measure1_false_2.ini"
        wrong = "meeeeeeasurement/measure1/straaaaang"
        target = "measurement/measure1/string"
        fname = Path(self._app_implementation_dir.name) / "copy.ini"
        fname.write_text(src.read_text())
        self.app.microscope_config_path = Path(self._app_implementation_dir.name) / "t.scopefoundry"

        from ScopeFoundry import ini_io
        from ScopeFoundry.base_app.show_io_report_dialog import (
            get_setting_path_mappings,
            remove_missing_from_ini,
            resolve_missing_settings,
        )

        resolve_missing_settings(self.app, str(fname), {wrong: ("replace", target)})
        self.assertEqual(get_setting_path_mappings(self.app), {wrong: target})

        loaded = ini_io.load_settings(fname)
        self.assertIn(target, loaded)
        self.assertNotIn(wrong, loaded)

        fname.write_text(src.read_text())
        remove_missing_from_ini(self.app, str(fname), [wrong])
        self.assertNotIn(wrong, ini_io.load_settings(fname))

        fname.write_text(src.read_text())
        resolve_missing_settings(self.app, str(fname), {wrong: ("remove", None)})
        self.assertNotIn(wrong, ini_io.load_settings(fname))

        from ScopeFoundry.base_app.show_io_report_dialog import (
            apply_known_mappings,
            get_ignored_missing_settings,
        )

        self.assertFalse(apply_known_mappings(self.app, str(fname), ["unmapped/a/b"]))
        fname.write_text(src.read_text())
        self.mms["string"] = "unchanged"
        self.assertTrue(apply_known_mappings(self.app, str(fname), [wrong]))
        self.assertNotEqual(self.mms["string"], "unchanged")

        resolve_missing_settings(self.app, str(fname), {wrong: ("ignore_always", None)})
        self.assertEqual(get_ignored_missing_settings(self.app), [wrong])
        self.assertEqual(get_setting_path_mappings(self.app), {wrong: target})

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

    def test_non_mdi_window_positions_restore_fullscreen(self):
        main_window = Mock()
        app = SimpleNamespace(mdi=False, ui=main_window)
        positions = {
            "main": {
                "geometry": (0, 0, 640, 480),
                "maximized": False,
                "minimized": False,
                "fullscreen": True,
            }
        }

        BaseMicroscopeApp.set_window_positions(app, positions)

        main_window.showNormal.assert_called_once_with()
        main_window.showFullScreen.assert_called_once_with()
        main_window.setGeometry.assert_not_called()

    def test_geometry_only_window_positions_remain_loadable(self):
        main_window = Mock()
        app = SimpleNamespace(mdi=False, ui=main_window)
        positions = {"main": {"geometry": (0, 0, 640, 480)}}

        BaseMicroscopeApp.set_window_positions(app, positions)

        main_window.showNormal.assert_called_once_with()
        main_window.setGeometry.assert_called_once_with(0, 0, 640, 480)

if __name__ == "__main__":
    unittest.main()
