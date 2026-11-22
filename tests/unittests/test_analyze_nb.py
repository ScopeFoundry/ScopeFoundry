import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import h5py
from qtpy import QtCore, QtTest, QtWidgets

from ScopeFoundry import BaseMicroscopeApp
from ScopeFoundry import h5_analyze_with_ipynb
import ScopeFoundry.h5_analyze_with_ipynb.ipynb_analysis_measure as ipynb_measurement
from ScopeFoundry.h5_analyze_with_ipynb import ipynb_analysis
from ScopeFoundry.h5_analyze_with_ipynb.generate_loaders_py import injects_code
from ScopeFoundry.h5_analyze_with_ipynb.ipynb_analysis_measure import (
    IpynbAnalysisMeasurement,
)
from ScopeFoundry.base_app.profile_manager import ProfileManager
from ScopeFoundry.measurement import Measurement
from ScopeFoundry.tests.unittests.unittest_helpers import close_app_widgets


class DummyMeasure(Measurement):
    name = "analyze_nb_test"

    def get_py_snippet(self):
        return "print('measurement snippet')\n"

    def get_py_analysis_scripts(self):
        return list(self.scripts_path.glob("*"))


class AnalyzeNBTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        patcher = patch(
            "ScopeFoundry.base_app.base_microscope_app.get_child_path",
            return_value=self.root,
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = patch.object(
            ProfileManager, "_app_implementation_dir", return_value=self.root
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def make_app(self, app_class=BaseMicroscopeApp):
        app = app_class([])
        self.addCleanup(close_app_widgets, app)
        return app

    def make_data(self, directory, name="data.h5"):
        with h5py.File(directory / name, "w") as data:
            data.create_dataset("measurement/analyze_nb_test/count_to_4", data=[1, 2])

    def add_dummy(self, app):
        scripts = self.root / "measurement_scripts"
        scripts.mkdir()
        with patch.object(DummyMeasure, "_init_py_analysis_directory"):
            measure = DummyMeasure(app)
        measure.scripts_path = scripts
        app.add_measurement(measure)
        return measure

    def test_analysis_and_script_copy(self):
        app = self.make_app()
        measure = self.add_dummy(app)
        analysis = app.measurements["ipynb_analysis"]
        folder = self.root / "data"
        self.make_data(folder)
        self.make_data(folder, "second.h5")
        (measure.scripts_path / "measure_helper.py").write_text("measure")
        (analysis.app_scripts_path / "app_helper.py").write_text("app")
        (analysis.app_scripts_path / "existing.py").write_text("new")
        (folder / "existing.py").write_text("original")
        analysis.settings["ipynb_option"] = "all"
        with patch.object(ipynb_measurement, "open_file") as open_file:
            notebook = analysis.analyze()
        open_file.assert_called_once_with(notebook)
        content = json.loads(notebook.read_text())
        self.assertEqual(len(content["cells"]), 3)
        self.assertIn("print('measurement snippet')\n", content["cells"][2]["source"])
        self.assertTrue((folder / "h5_data_loaders.py").is_file())
        self.assertEqual((folder / "measure_helper.py").read_text(), "measure")
        self.assertEqual((folder / "app_helper.py").read_text(), "app")
        self.assertEqual((folder / "existing.py").read_text(), "original")

    def test_flag_set_during_setup_does_not_disable_analysis(self):
        class App(BaseMicroscopeApp):
            mdi = False

            def setup(self):
                self.enable_ipynb_analysis = False

        app = self.make_app(App)
        analysis = app.measurements["ipynb_analysis"]
        self.assertTrue(analysis.settings["hidden"])
        self.assertIn("ipynb_option", analysis.settings)
        self.assertTrue((self.root / "py_analysis_scripts").exists())
        self.assertTrue(
            app.ui.findChildren(QtWidgets.QPushButton, "analyze with ipynb")
        )
        self.assertIn(
            "analyze with ipynb",
            [action.text() for action in app.ui.menuAdvanced.actions()],
        )
        shortcuts = app.ui.findChildren(QtWidgets.QShortcut)
        self.assertTrue(any(s.key().toString() == "Ctrl+I" for s in shortcuts))

    def test_controls_route_to_measurement_in_both_ui_modes(self):
        for mdi in (True, False):
            with self.subTest(mdi=mdi):

                class App(BaseMicroscopeApp):
                    pass

                App.mdi = mdi
                app = self.make_app(App)
                analysis = app.measurements["ipynb_analysis"]
                operation = analysis.operations.get("analyze with ipynb")
                with patch.object(ipynb_measurement, "open_file"):
                    with patch.object(
                        ipynb_measurement, "generate_loaders_py"
                    ) as generate:
                        generate.return_value = (Path("loaders.py"), {})
                        button = app.ui.findChild(QtWidgets.QPushButton, operation.name)
                        action = next(
                            a
                            for a in app.ui.menuAdvanced.actions()
                            if a.text() == operation.name
                        )
                        button.click()
                        action.trigger()
                        analysis.operations._shortcuts[operation.name].activated.emit()
                        self.assertEqual(generate.call_count, 3)

    def test_threaded_measurement_run_opens_after_completion(self):
        app = self.make_app()
        analysis = app.measurements["ipynb_analysis"]
        self.make_data(self.root / "data")
        with patch.object(ipynb_measurement, "open_file") as open_file:
            analysis.start()
            deadline = QtCore.QDeadlineTimer(10000)
            while analysis.is_measuring() and not deadline.hasExpired():
                QtTest.QTest.qWait(20)
            self.assertEqual(analysis.end_state, "stop_success")
            open_file.assert_called_once_with(self.root / "data" / "overview.ipynb")

    def test_standalone_compatibility_and_options(self):
        self.assertIs(h5_analyze_with_ipynb.update_ipynb, ipynb_analysis.update_ipynb)
        self.assertIs(
            h5_analyze_with_ipynb.analyze_with_ipynb, ipynb_analysis.analyze_with_ipynb
        )
        self.assertIs(
            h5_analyze_with_ipynb.generate_loaders_py,
            ipynb_analysis.generate_loaders_py,
        )
        self.assertTrue(issubclass(IpynbAnalysisMeasurement, Measurement))
        self.make_data(self.root, "first.h5")
        self.make_data(self.root, "second.h5")
        with patch.object(ipynb_analysis, "open_file"):
            h5_analyze_with_ipynb.analyze_with_ipynb(str(self.root), option="all")
        content = json.loads((self.root / "overview.ipynb").read_text())
        self.assertEqual(len(content["cells"]), 4)

    def test_valid_dset_names(self):
        valid_inputs = (
            "hyperspectral__scan",
            "hyperspectral/scan",
            "hyperspectral hyperspectral",
            "hyperspectral scan/dset",
            "hyperspectral_scan/dset b",
        )
        for input in valid_inputs:
            resp = injects_code(input)
            print(resp)
            self.assertFalse(resp, resp)

    def test_invalid_dset_names(self):
        invalid_inputs = ("x=22", "x-22", "str(33)", "__import__(")
        for input in invalid_inputs:
            resp = injects_code(input)
            print(resp)
            self.assertIsInstance(resp, str, resp)


if __name__ == "__main__":
    unittest.main()
