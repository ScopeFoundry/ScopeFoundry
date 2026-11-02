import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ScopeFoundry.measurement import Measurement
from ScopeFoundry import BaseMicroscopeApp, h5_io
from ScopeFoundry.base_app.profile_manager import ProfileManager
from ScopeFoundry.tests.unittests.unittest_helpers import close_app_widgets


class DummyMeasure(Measurement):

    name = "analyze_nb_test"

    def run(self):
        data = [1, 2, 4, 5]
        self.save_h5_data(data)

    def save_h5_data(self, data):
        self.h5_file = h5_io.h5_base_file(app=self.app, measurement=self)
        self.h5_meas_group = h5_io.h5_create_measurement_group(self, self.h5_file)
        self.h5_meas_group.create_dataset("count_to_4", data=data)
        self.h5_file.close()


class AnalyzeNBTest(unittest.TestCase):

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
        self.m = self.app.add_measurement(DummyMeasure(self.app))

    def test_non_empty_file(self):
        self.m.run()
        self.ipynb_file_name = self.app.on_analyze_with_ipynb()
        with open(self.ipynb_file_name, "r") as file:
            content = json.load(file)

        self.assertGreater(len(content["cells"]), 1)


if __name__ == "__main__":
    unittest.main()
