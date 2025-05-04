import logging
import sys
import time

import numpy as np

from ScopeFoundry import BaseMicroscopeApp
from ScopeFoundry.examples.ScopeFoundryHW.bsinc_noiser200 import Noiser200HW
from ScopeFoundry.examples.ScopeFoundryHW.simulon_xyz_stage import SimulonXYZStageHW
from ScopeFoundry.scanning import (
    BaseRaster2DFrameSlowScan,
    BaseRaster2DSlowScan,
    BaseRaster2DSlowScanV2,
    BaseRaster3DSlowScan,
    BaseRaster3DSlowScanV2,
)

logging.basicConfig(level=logging.INFO)
logging.getLogger("ScopeFoundry").setLevel(logging.DEBUG)


class TestRaster2DSlowScan(BaseRaster2DSlowScan):
    name = "test_cart_2d_slow_scan"

    def scan_specific_setup(self):
        self.stage = self.app.hardware["simulon_xyz_stage"]
        self.detector = self.app.hardware["noiser_200"]

    def move_position_start(self, h, v):
        self.stage.settings["x_target_position"] = h
        self.stage.settings["y_target_position"] = v

    def move_position_fast(self, h, v, dh, dv):
        return self.move_position_start(h, v)

    def move_position_slow(self, h, v, dh, dv):
        return self.move_position_start(h, v)

    def pre_scan_setup(self):
        self.display_update_period = 0.050  # seconds

        if self.settings["save_h5"]:
            self.test_data = self.h5_meas_group.create_dataset(
                "test_data", self.scan_shape, dtype=float
            )

        self.prev_px = time.time()

    def post_scan_cleanup(self):
        print("post_scan_cleanup")

    def collect_pixel(self, pixel_i, k, j, i):
        # print pixel_i, k,j,i
        t0 = time.time()
        # px_data = np.random.rand()
        # px_data = t0 - self.prev_px
        x0, y0 = self.pos
        x_set = self.stage.settings["x_position"]
        y_set = self.stage.settings["y_position"]
        x_hw = self.stage.settings.get_lq("x_position").read_from_hardware()
        y_hw = self.stage.settings.get_lq("y_position").read_from_hardware()
        if np.abs(x_hw - x0) > 1:
            self.log.debug("=" * 60)
            self.log.debug("pos      {} {}".format(x0, y0))
            self.log.debug("settings {} {}".format(x_set, y_set))
            self.log.debug("hw       {} {}".format(x_hw, y_hw))
            self.log.debug("settings value delta {} {}".format(x_set - x0, y_set - y0))
            self.log.debug("read_hw  value delta {} {}".format(x_hw - x0, y_hw - y0))
            self.log.debug("=" * 60)

        x = x_hw
        y = y_hw

        px_data = (
            np.sinc((x - 50) * 0.05) ** 2 * np.sinc(0.05 * (y - 50)) ** 2
        )  # + 0.05*np.random.random()
        # px_data = (x-xhw)**2 + ( y-yhw)**2
        # if px_data > 1:
        #    print('hw', x, xhw, y, yhw)
        self.display_image_map[k, j, i] = px_data
        if self.settings["save_h5"]:
            self.test_data[k, j, i] = px_data
        time.sleep(self.settings["pixel_time"])
        # self.prev_px = t0


class TestRaster2DFrameSlowScan(BaseRaster2DFrameSlowScan):
    name = "test_cart_2d_frame_slow_scan"

    def scan_specific_setup(self):
        self.stage = self.app.hardware["simulon_xyz_stage"]
        self.detector = self.app.hardware["noiser_200"]

    def pre_scan_setup(self):  # called at the begining of run
        self.display_update_period = 0.050  # seconds

        if self.settings["save_h5"]:
            self.test_data = self.create_h5_framed_dataset(
                "test_data", self.display_image_map
            )

        self.prev_px = time.time()

    def post_scan_cleanup(self):  # called at the end of run
        print("post_scan_cleanup")

    def collect_pixel(self, pixel_i, frame_i, k, j, i):
        t0 = time.time()
        x_hw = self.stage.settings.get_lq("x_position").read_from_hardware()
        y_hw = self.stage.settings.get_lq("y_position").read_from_hardware()

        theta = np.pi / 10.0 * frame_i
        x = x_hw * np.cos(theta) - y_hw * np.sin(theta)
        y = x_hw * np.sin(theta) + y_hw * np.cos(theta)

        px_data = (
            np.sinc((x - 50) * 0.05) ** 2 * np.sinc(0.05 * (y - 50)) ** 2
        )  # + 0.05*np.random.random()

        self.display_image_map[k, j, i] = px_data
        if self.settings["save_h5"]:
            self.test_data[frame_i, k, j, i] = px_data
        time.sleep(self.settings["pixel_time"])

    def on_new_frame(self, frame_i):
        print("on_new_frame")
        if self.settings["save_h5"]:
            self.extend_h5_framed_dataset(self.test_data, frame_i)

    def on_end_frame(self, frame_i):
        pass


class TestRaster3DSlowScan(BaseRaster3DSlowScan):
    name = "test_cart_3d_slow_scan"

    def scan_specific_setup(self):
        self.stage = self.app.hardware["simulon_xyz_stage"]
        self.detector = self.app.hardware["noiser_200"]

    def move_position_start(self, h, v, z):
        self.stage.settings["x_target_position"] = h
        self.stage.settings["y_target_position"] = v
        self.stage.settings["z_target_position"] = z

    def move_position_slow(self, h, v, dh, dv):
        self.stage.settings["x_target_position"] = h
        self.stage.settings["y_target_position"] = v

    def pre_scan_setup(self):
        self.display_update_period = 0.050  # seconds

        if self.settings["save_h5"]:
            self.test_data = self.h5_meas_group.create_dataset(
                "test_data", self.scan_shape, dtype=float
            )

        self.prev_px = time.time()

    def post_scan_cleanup(self):
        print("post_scan_cleanup")

    def collect_pixel(self, pixel_i, k, j, i):

        t0 = time.time()

        x0, y0 = self.pos
        x_set = self.stage.settings["x_position"]
        y_set = self.stage.settings["y_position"]

        x_hw = self.stage.settings.get_lq("x_position").read_from_hardware()
        y_hw = self.stage.settings.get_lq("y_position").read_from_hardware()
        z_hw = self.stage.settings.get_lq("z_position").read_from_hardware()

        if np.abs(x_hw - x0) > 1:
            self.log.debug("=" * 60)
            self.log.debug("pos      {} {}".format(x0, y0))
            self.log.debug("settings {} {}".format(x_set, y_set))
            self.log.debug("hw       {} {}".format(x_hw, y_hw))
            self.log.debug("settings value delta {} {}".format(x_set - x0, y_set - y0))
            self.log.debug("read_hw  value delta {} {}".format(x_hw - x0, y_hw - y0))
            self.log.debug("=" * 60)

        x = x_hw
        y = y_hw

        px_data = np.sinc((x - 50) * 0.05) ** 2 * np.sinc(0.05 * (y - 50)) ** 2

        # NOTE: In 3D index k represents z position / while in 2D k represents 'frame'
        self.display_image_map[k, j, i] = px_data
        if self.settings["save_h5"]:
            self.test_data[k, j, i] = px_data
        time.sleep(self.settings["pixel_time"])


class Example2DSlowScanMeasure(BaseRaster2DSlowScanV2):

    name = "example_2d_scan"

    def scan_specific_setup(self):
        self.detector = self.app.hardware["noiser_200"]

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


class Example3DSlowScanMeasure(BaseRaster3DSlowScanV2):

    name = "example_3d_scan"

    def scan_specific_setup(self):
        self.detector = self.app.hardware["noiser_200"]

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


class TestRaster2DSlowScanApp(BaseMicroscopeApp):

    name = "app"

    def setup(self):

        stage = self.add_hardware(SimulonXYZStageHW(self))
        stage.settings["connected"] = True

        detector = self.add_hardware(Noiser200HW(self))
        detector.settings["connected"] = True

        self.add_measurement(
            TestRaster2DSlowScan(self, h_limits=(0, 100), v_limits=(0, 100))
        )
        self.add_measurement(
            TestRaster2DFrameSlowScan(self, h_limits=(0, 100), v_limits=(0, 100))
        )

        self.add_measurement(
            TestRaster3DSlowScan(
                self, h_limits=(0, 100), v_limits=(0, 100), z_limits=(-1, 1)
            )
        )

        for m in self.measurements.values():
            S = m.settings
            # S = self.test_cart_2d_slow_scan.settings
            S["h1"] = 100
            S["v1"] = 100
            S["dh"] = S["dv"] = 1.0

        actuators = (
            (
                "x_position",
                "hw/simulon_xyz_stage/x_position",
                "hw/simulon_xyz_stage/x_target_position",
            ),
            (
                "y_position",
                "hw/simulon_xyz_stage/y_position",
                "hw/simulon_xyz_stage/y_target_position",
            ),
            (
                "z_position",
                "hw/simulon_xyz_stage/z_position",
                "hw/simulon_xyz_stage/z_target_position",
            ),
        )

        self.add_measurement(
            Example2DSlowScanMeasure(
                self, actuators=actuators, h_limits=(0, 100), v_limits=(0, 100)
            )
        )
        self.add_measurement(
            Example3DSlowScanMeasure(
                self,
                actuators=actuators,
                h_limits=(0, 100),
                v_limits=(0, 100),
                z_limits=(-1, 1),
            )
        )


if __name__ == "__main__":
    app = TestRaster2DSlowScanApp([])

    # from ScopeFoundry.flask_web_view.flask_web_view import MicroscopeFlaskWebThread
    # app.flask_thread = MicroscopeFlaskWebThread(app)
    # app.flask_thread.start()

    sys.exit(app.exec_())
