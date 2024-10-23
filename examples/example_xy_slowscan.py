import sys

from ScopeFoundry import BaseMicroscopeApp
from ScopeFoundry.examples.hardware.dummy_detector import DummyDetector
from ScopeFoundry.examples.hardware.dummy_xy_stage import DummyXYStageHW
from ScopeFoundry.scanning import BaseRaster2DSlowScan


class DummyXYScanMeasure(BaseRaster2DSlowScan):

    name = "dummy_xy_scan"

    def scan_specific_setup(self):
        self.stage = self.app.hardware["dummy_xy_stage"]
        self.detector = self.app.hardware["dummy_detector"]

    def collect_pixel(self, pixel_num, k, j, i):
        self.display_image_map[k, j, i] = self.detector.signal.read_from_hardware()


class ExampleXYSlowscanApp(BaseMicroscopeApp):

    def setup(self):
        self.add_hardware(DummyXYStageHW(self))
        self.add_hardware(DummyDetector(self))

        self.add_measurement(DummyXYScanMeasure(self))


if __name__ == "__main__":
    app = ExampleXYSlowscanApp(sys.argv)
    app.settings_load_ini("default_settings.ini")
    sys.exit(app.exec_())
