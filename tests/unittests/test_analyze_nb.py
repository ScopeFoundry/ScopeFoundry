import json
import unittest

from ScopeFoundry.measurement import Measurement
from ScopeFoundry import BaseMicroscopeApp, h5_io


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
        self.app = BaseMicroscopeApp([])
        self.m = self.app.add_measurement(DummyMeasure(self.app))

    def test_non_empty_file(self):
        self.m.run()
        self.ipynb_file_name = self.app.on_analyze_with_ipynb()
        with open(self.ipynb_file_name, "r") as file:
            content = json.load(file)

        self.assertGreater(len(content["cells"]), 1)


if __name__ == "__main__":
    unittest.main()
