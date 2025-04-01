import time

from ScopeFoundry import HardwareComponent
from ScopeFoundry.scanning import BaseRaster2DSlowScanV2



class Example2DSlowScanMeasure(BaseRaster2DSlowScanV2):

    name = "example_2d_scan"

    def scan_specific_setup(self):
        self.detector: HardwareComponent = self.app.hardware["noiser_200"]

    def pre_scan_setup(self):
        if self.settings["save_h5"]:
            self.signal_map = self.h5_meas_group.create_dataset(
                name="signal_map", shape=self.scan_shape, dtype=float
            )

    # def setup_figure(self):
    #     super().setup_figure()
    #     add_to_layout(
    #         self.detector,
    #         self.ui.device_details_layout,
    #         include=("connected", "signal", "voltage"),
    #     )

    def collect_pixel(self, pixel_num, k, j, i):
        signal = self.detector.settings.get_lq("signal").read_from_hardware()
        self.display_image_map[k, j, i] = signal
        if self.settings["save_h5"]:
            self.signal_map[k, j, i] = signal
