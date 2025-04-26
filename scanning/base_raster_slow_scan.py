import time
import traceback

import numpy as np

from .base_raster_scan import BaseRaster2DScan, BaseRaster3DScan


class BaseRaster2DSlowScan(BaseRaster2DScan):

    name = "base_raster_2Dslowscan"

    def run(self):
        S = self.settings

        # Compute data arrays
        self.compute_scan_arrays()

        self.initial_scan_setup_plotting = True

        # Fill display image with nan
        # this allows for pyqtgraph histogram to ignore unfilled data
        # pyqtgraph ImageItem also keeps unfilled data pixels transparent
        self.display_image_map = np.nan * np.zeros(self.scan_shape, dtype=float)

        while not self.interrupt_measurement_called:
            try:
                # h5 data file setup
                self.t0 = time.time()

                if self.settings["save_h5"]:
                    H = self.open_new_h5_file()
                    self.h5_filename = self.h5_file.filename

                    # create h5 data arrays
                    H["h_array"] = self.h_array
                    H["v_array"] = self.v_array
                    H["range_extent"] = self.range_extent
                    H["corners"] = self.corners
                    H["imshow_extent"] = self.imshow_extent
                    H["scan_h_positions"] = self.scan_h_positions
                    H["scan_v_positions"] = self.scan_v_positions
                    H["scan_slow_move"] = self.scan_slow_move
                    H["scan_index_array"] = self.scan_index_array

                # start scan
                self.pixel_i = 0
                self.current_scan_index = self.scan_index_array[0]

                self.pixel_time = np.zeros(self.scan_shape, dtype=float)
                if self.settings["save_h5"]:
                    self.pixel_time_h5 = H.create_dataset(
                        name="pixel_time", shape=self.scan_shape, dtype=float
                    )

                self.pre_scan_setup()

                self.move_position_start(
                    self.scan_h_positions[0], self.scan_v_positions[0]
                )

                for self.pixel_i in range(self.Npixels):
                    if self.interrupt_measurement_called:
                        break

                    i = self.pixel_i

                    self.current_scan_index = self.scan_index_array[i]
                    kk, jj, ii = self.current_scan_index

                    h, v = self.scan_h_positions[i], self.scan_v_positions[i]

                    if self.pixel_i == 0:
                        dh = 0
                        dv = 0
                    else:
                        dh = self.scan_h_positions[i] - self.scan_h_positions[i - 1]
                        dv = self.scan_v_positions[i] - self.scan_v_positions[i - 1]

                    if self.scan_slow_move[i]:
                        if self.interrupt_measurement_called:
                            break
                        self.move_position_slow(h, v, dh, dv)
                        if self.settings["save_h5"]:
                            self.h5_file.flush()  # flush data to file every slow move
                        # self.app.qtapp.ProcessEvents()
                        time.sleep(0.01)
                    else:
                        self.move_position_fast(h, v, dh, dv)

                    self.pos = (h, v)
                    # each pixel:
                    # acquire signal and save to data array
                    pixel_t0 = time.time()
                    self.pixel_time[kk, jj, ii] = pixel_t0
                    if self.settings["save_h5"]:
                        self.pixel_time_h5[kk, jj, ii] = pixel_t0
                    self.collect_pixel(self.pixel_i, kk, jj, ii)
                    self.set_progress(100.0 * self.pixel_i / (self.Npixels))
            except Exception as err:
                self.last_err = err
                self.log.error("Failed to Scan {}".format(repr(err)))
                traceback.print_exc()
                # raise(err)
            finally:
                self.post_scan_cleanup()
                if hasattr(self, "h5_file"):
                    print("h5_file", self.h5_file)
                    try:
                        self.h5_file.close()
                    except ValueError as err:
                        self.log.warning("failed to close h5_file: {}".format(err))
                if not self.settings["continuous_scan"]:
                    break
        print(self.name, "done")

    def new_pt_pos(self, x, y):
        self.move_position_start(x, y)

    # Override these methods in subclasses to implement hardware specific movement
    def move_position_start(self, h, v):
        if hasattr(self, "stage"):
            self.stage.settings["x_position"] = h
            self.stage.settings["y_position"] = v
        else:
            print(self.name, "move_position_start not implemented")

    def move_position_slow(self, h, v, dh, dv):
        return self.move_position_fast(h, v, dh, dv)

    def move_position_fast(self, h, v, dh, dv):
        return self.move_position_start(h, v)

    def pre_scan_setup(self):
        print(self.name, "pre_scan_setup not implemented")
        # hardware
        # create data arrays
        # update figure

    def collect_pixel(self, pixel_num: int, k: int, j: int, i: int):
        # collect data
        # store in arrays
        print(self.name, "collect_pixel", pixel_num, k, j, i, "not implemented")

    def post_scan_cleanup(self):
        print(self.name, "post_scan_cleanup not implemented")


class BaseRaster3DSlowScan(BaseRaster3DScan):

    name = "base_raster_3Dslowscan"

    def run(self):
        S = self.settings

        # Compute data arrays
        self.compute_scan_arrays()

        self.initial_scan_setup_plotting = True

        self.display_image_map = np.zeros(self.scan_shape, dtype=float)

        while not self.interrupt_measurement_called:
            try:
                # h5 data file setup
                self.t0 = time.time()

                if self.settings["save_h5"]:
                    H = self.open_new_h5_file()
                    self.h5_filename = self.h5_file.filename

                    # create h5 data arrays
                    H["h_array"] = self.h_array
                    H["v_array"] = self.v_array
                    H["z_array"] = self.z_array
                    H["range_extent"] = self.range_extent
                    H["corners"] = self.corners
                    H["imshow_extent"] = self.imshow_extent
                    H["scan_h_positions"] = self.scan_h_positions
                    H["scan_v_positions"] = self.scan_v_positions
                    H["scan_z_positions"] = self.scan_z_positions
                    H["scan_slow_move"] = self.scan_slow_move
                    H["scan_index_array"] = self.scan_index_array

                # start scan
                self.pixel_i = 0
                self.current_scan_index = self.scan_index_array[0]

                self.pixel_time = np.zeros(self.scan_shape, dtype=float)
                if self.settings["save_h5"]:
                    self.pixel_time_h5 = H.create_dataset(
                        name="pixel_time", shape=self.scan_shape, dtype=float
                    )

                self.pre_scan_setup()

                self.move_position_start(
                    self.scan_h_positions[0],
                    self.scan_v_positions[0],
                    self.scan_z_positions[0],
                )

                for self.pixel_i in range(self.Npixels):
                    if self.interrupt_measurement_called:
                        break

                    i = self.pixel_i

                    self.current_scan_index = self.scan_index_array[i]
                    kk, jj, ii = self.current_scan_index

                    h, v, z = (
                        self.scan_h_positions[i],
                        self.scan_v_positions[i],
                        self.scan_z_positions[i],
                    )

                    if self.pixel_i == 0:
                        dh = 0
                        dv = 0
                    else:
                        dh = self.scan_h_positions[i] - self.scan_h_positions[i - 1]
                        dv = self.scan_v_positions[i] - self.scan_v_positions[i - 1]

                    if self.scan_start_move[i]:
                        if self.interrupt_measurement_called:
                            break
                        self.move_position_start(h, v, z)
                        if self.settings["save_h5"]:
                            self.h5_file.flush()  # flush data to file every slow move
                        # self.app.qtapp.ProcessEvents()
                        time.sleep(0.01)
                    elif self.scan_slow_move[i]:
                        if self.interrupt_measurement_called:
                            break
                        self.move_position_slow(h, v, dh, dv)
                        if self.settings["save_h5"]:
                            self.h5_file.flush()  # flush data to file every slow move
                        # self.app.qtapp.ProcessEvents()
                        time.sleep(0.01)
                    else:
                        self.move_position_fast(h, v, dh, dv)

                    self.pos = (h, v)
                    # each pixel:
                    # acquire signal and save to data array
                    pixel_t0 = time.time()
                    self.pixel_time[kk, jj, ii] = pixel_t0
                    if self.settings["save_h5"]:
                        self.pixel_time_h5[kk, jj, ii] = pixel_t0
                    self.collect_pixel(self.pixel_i, kk, jj, ii)
                    self.set_progress(100.0 * self.pixel_i / (self.Npixels))
            except Exception as err:
                self.last_err = err
                self.log.error("Failed to Scan {}".format(repr(err)))
                traceback.print_exc()
                # raise(err)
            finally:
                self.post_scan_cleanup()
                if hasattr(self, "h5_file"):
                    print("h5_file", self.h5_file)
                    try:
                        self.h5_file.close()
                    except ValueError as err:
                        self.log.warning("failed to close h5_file: {}".format(err))
                if not self.settings["continuous_scan"]:
                    break
        print(self.name, "done")

    def new_pt_pos(self, x, y):
        self.move_position_slow(x, y, 0, 0)

    # Override these methods in subclasses to implement hardware specific movement
    def move_position_start(self, h: float, v: float, z: float):
        if hasattr(self, "stage"):
            self.stage.settings["x_position"] = h
            self.stage.settings["y_position"] = v
            self.stage.settings["z_position"] = z

    def move_position_slow(self, h: float, v: float, dh: float, dv: float):
        if hasattr(self, "stage"):
            self.stage.settings["x_position"] = h
            self.stage.settings["y_position"] = v

    def move_position_fast(self, h: float, v: float, dh: float, dv: float):
        return self.move_position_slow(h, v, dh, dv)

    def pre_scan_setup(self):
        print(self.name, "pre_scan_setup not implemented")
        # hardware
        # create data arrays
        # update figure

    def collect_pixel(self, pixel_num: int, k: int, j: int, i: int):
        # collect data
        # store in arrays
        print(self.name, "collect_pixel", pixel_num, k, j, i, "not implemented")

    def post_scan_cleanup(self):
        print(self.name, "post_scan_cleanup not implemented")
