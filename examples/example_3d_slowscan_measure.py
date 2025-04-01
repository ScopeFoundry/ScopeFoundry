from ScopeFoundry import HardwareComponent
from ScopeFoundry.scanning import BaseRaster3DSlowScanV2


class Example3DSlowScanMeasure(BaseRaster3DSlowScanV2):

    name = "example_3d_scan"

    def scan_specific_setup(self):
        self.detector: HardwareComponent = self.app.hardware["noiser_200"]

    def pre_scan_setup(self):
        if self.settings["save_h5"]:
            self.signal_map = self.h5_meas_group.create_dataset(
                name="signal_map", shape=self.scan_shape, dtype=float
            )

    def collect_pixel(self, pixel_num, k, j, i):
        signal = self.detector.settings.get_lq("signal").read_from_hardware()
        self.display_image_map[k, j, i] = signal
        if self.settings["save_h5"]:
            self.signal_map[k, j, i] = signal
