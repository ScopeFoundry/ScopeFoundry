import time

import numpy as np

from ScopeFoundry import h5_io

from .base_raster_scan import BaseRaster2DScan


class BaseRaster2DFrameSlowScan(BaseRaster2DScan):

    name = "base_raster_2D_frame_slowscan"

    def run(self):
        S = self.settings

        # Hardware
        # self.apd_counter_hc = self.app.hardware_components['apd_counter']
        # self.apd_count_rate = self.apd_counter_hc.apd_count_rate
        # self.stage = self.app.hardware_components['dummy_xy_stage']

        # Data File
        # H5

        # Compute data arrays
        self.compute_scan_arrays()

        self.initial_scan_setup_plotting = True

        self.display_image_map = np.zeros(self.scan_shape, dtype=float)
        self.pixel_times = np.zeros(self.scan_shape, dtype=float)

        # h5 data file setup
        self.t0 = time.time()

        if self.settings["save_h5"]:
            self.h5_file = h5_io.h5_base_file(self.app, measurement=self)

            self.h5_file.attrs["time_id"] = self.t0
            H = self.h5_meas_group = h5_io.h5_create_measurement_group(
                self, self.h5_file
            )

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
            self.pixel_times_h5 = self.create_h5_framed_dataset(
                name="pixel_times", single_frame_map=self.pixel_times, dtype=float
            )

        self.frame_i = 0
        self.pixel_i = 0
        self.current_scan_index = self.scan_index_array[0]

        self.pre_scan_setup()

        try:
            while not self.interrupt_measurement_called:
                # start scan
                for i in range(self.settings["n_frames"]):
                    if self.settings["save_h5"]:
                        self.extend_h5_framed_dataset(self.pixel_times_h5, self.frame_i)
                    if self.interrupt_measurement_called:
                        break
                    # start frame
                    self.pixel_i = 0
                    self.current_scan_index = self.scan_index_array[0]
                    self.move_position_start(
                        self.scan_h_positions[0], self.scan_v_positions[0]
                    )
                    self.on_new_frame(self.frame_i)

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
                        self.pixel_times[kk, jj, ii] = pixel_t0
                        if self.settings["save_h5"]:
                            self.pixel_times_h5[self.frame_i, kk, jj, ii] = pixel_t0
                        self.collect_pixel(self.pixel_i, self.frame_i, kk, jj, ii)
                        S["progress"] = (
                            100.0
                            * (self.frame_i * self.Npixels + self.pixel_i)
                            / (self.Npixels * self.settings["n_frames"])
                        )
                    self.on_end_frame(self.frame_i)
                    self.frame_i += 1
                if not self.settings["continuous_scan"]:
                    break
        finally:
            self.post_scan_cleanup()
            if self.settings["save_h5"] and hasattr(self, "h5_file"):
                self.h5_file.close()

    def move_position_start(self, x, y):
        self.stage.settings["x_position"] = x
        self.stage.settings["y_position"] = y

    def move_position_slow(self, x, y, dx, dy):
        self.stage.settings["x_position"] = x
        self.stage.settings["y_position"] = y

    def move_position_fast(self, x, y, dx, dy):
        self.stage.settings["x_position"] = x
        self.stage.settings["y_position"] = y
        # x = self.stage.settings['x_position']
        # y = self.stage.settings['y_position']
        # x = self.stage.settings.get_lq("x_position").read_from_hardware()
        # y = self.stage.settings.get_lq("y_position").read_from_hardware()
        # print(x,y)

    def pre_scan_setup(self):
        print(self.name, "pre_scan_setup not implemented")
        # hardware
        # create data arrays
        # update figure

    def collect_pixel(self, pixel_num, frame_i, k, j, i):
        # collect data
        # store in arrays
        print(
            self.name, "collect_pixel", pixel_num, frame_i, k, j, i, "not implemented"
        )

    def post_scan_cleanup(self):
        print(self.name, "post_scan_setup not implemented")

    def on_new_frame(self, frame_i):
        pass

    def on_end_frame(self, frame_i):
        pass

    @property
    def frames_scan_shape(self):
        """
        Returns the shape of data arrays for n_frames:
        (n_frames, N_subframes, Nv, Nh)
        """
        return (self.settings["n_frames"],) + self.scan_shape

    def create_h5_framed_dataset(self, name, single_frame_map, **kwargs):
        """
        Create and return an empty HDF5 dataset in self.h5_meas_group that can store
        multiple frames of single_frame_map.

        Must fill the dataset as frames roll in.

        creates reasonable defaults for compression and dtype, can be overriden
        with**kwargs are sent directly to create_dataset
        """
        if self.settings["save_h5"]:
            shape = (self.settings["n_frames"],) + single_frame_map.shape
            if self.settings["continuous_scan"]:
                # allow for array to grow to store additional frames
                maxshape = (None,) + single_frame_map.shape
            else:
                maxshape = shape
            # print('maxshape', maxshape)
            default_kwargs = dict(
                name=name,
                shape=shape,
                dtype=single_frame_map.dtype,
                # chunks=(1,),
                maxshape=maxshape,
                compression="gzip",
                # shuffle=True,
            )
            default_kwargs.update(kwargs)
            map_h5 = self.h5_meas_group.create_dataset(**default_kwargs)
            return map_h5

    def extend_h5_framed_dataset(self, map_h5, frame_num):
        """
        Adds additional frames to dataset map_h5, if frame_num
        is too large. Adds n_frames worth of extra frames
        """
        if self.settings["continuous_scan"]:
            current_num_frames = map_h5.shape[0]
            frame_shape = map_h5.shape[1:]
            if frame_num >= current_num_frames:
                # print ("extend_h5_framed_dataset", map_h5.name, map_h5.shape, frame_num)
                n_frames_extend = self.settings["n_frames"]
                new_num_frames = n_frames_extend * (1 + frame_num // n_frames_extend)
                map_h5.resize((new_num_frames,) + tuple(frame_shape))
                return True
            else:
                # "Dataset is large enough, no expansion"
                return False
        else:
            # "non continuous scan, no expansion"
            return False
