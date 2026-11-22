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

    def make_app(self, app_class=BaseMicroscopeApp):
        app = app_class([])
        app.add_measurement(IpynbAnalysisMeasurement(app))
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
