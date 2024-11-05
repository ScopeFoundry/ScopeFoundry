from ScopeFoundry import HardwareComponent
from ScopeFoundry.scanning import BaseRaster2DSlowScan


class Example2DSlowScanMeasure(BaseRaster2DSlowScan):

    name = "example_2d_scan"

    def scan_specific_setup(self):
        self.stage: HardwareComponent = self.app.hardware["simulon_xyz_stage"]
        self.detector: HardwareComponent = self.app.hardware["noiser_200"]

        self.settings.New("h_axis", str, initial="x", choices="xyz")
        self.settings.New("v_axis", str, initial="y", choices="xyz")

    def move_position_slow(self, h, v, dh, dv):
        self.stage.settings[f"{self.settings['h_axis']}_position"] = h
        self.stage.settings[f"{self.settings['v_axis']}_position"] = v

    def move_position_fast(self, h, v, dh, dv):
        self.stage.settings[f"{self.settings['h_axis']}_position"] = h
        self.stage.settings[f"{self.settings['v_axis']}_position"] = v

    def pre_scan_setup(self):
        if self.settings["save_h5"]:
            self.signal_map = self.h5_meas_group.create_dataset(
                name="signal_map", shape=self.scan_shape, dtype=float
            )


    def setup_figure(self):
        super().setup_figure()
        # add_to_layout(
        #     self.detector,
        #     self.ui.device_details_layout,
        #     include=("connected", "signal", "voltage"),
        # )
        self.ui.details_layout.addWidget(
            self.settings.New_UI(include=("h_axis", "v_axis"))
        )

    def collect_pixel(self, pixel_num, k, j, i):
        signal = self.detector.settings.get_lq("signal").read_from_hardware()
        self.display_image_map[k, j, i] = signal
        if self.settings["save_h5"]:
            self.signal_map[k, j, i] = signal
