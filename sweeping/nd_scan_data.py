from typing import Iterable, Tuple, Dict

import numpy as np

from ScopeFoundry import Measurement, h5_io
from .collector import Collector


def to_dstname(name: str) -> str:
    return name.replace("/", "__")


class NDScanData:

    def __init__(
        self,
        base_shape: Tuple[int],
        measurement: Measurement,
        open_new_h5: bool = True,
    ):
        self.data: Dict[str, np.ndarray] = {}
        self.base_shape = base_shape
        self.scan_dims = len(base_shape)

        self.measurement = measurement
        self.app = measurement.app

        self.positions = []
        self.read_positions = []
        self.indices = []

        # keep track of repetition indices for each dataset
        self.rep_idx: Dict[str, np.ndarray] = {}

        self.current_sweep = 0
        if open_new_h5:
            self.open_new_h5_file()

    def open_new_h5_file(self):
        self.h5_meas_group = self.measurement.open_new_h5_file()
        self.h5_file = self.measurement.h5_file
        self.metadata = self.measurement.dataset_metadata
        self.dsets_initialized = False

    def add_position(self, positions: Tuple[float]):
        self.positions.append(positions)

    def add_read_positions(self, positions: Tuple[float]):
        self.read_positions.append(positions)

    def add_indices(self, indices: Tuple[int]):
        self.indices.append(indices)

    def init_dsets(self, collector: Collector):
        collector.repeats = []
        if not len(collector.repeated_dset_names):
            # assume all datasets are repeated, user should set to None if explicitly does not want to collect anything.
            collector.repeated_dset_names = list(collector.data.keys())
        for name, d in collector.data.items():
            if not hasattr(d, "dtype"):
                try:
                    d = np.array(d)
                except Exception as err:
                    raise Exception(
                        f"{collector.name} has invalid dataset: {name}. Make sure all datasets can be cast with numpy.array"
                    )
                    print(err)
            if name in collector.repeated_dset_names:
                global_name = to_dstname(f"{collector.name}_{name}_raw")
                shape = self.base_shape + (collector.reps,) + d.shape
                self.data[global_name] = np.ones(shape, dtype=d.dtype) * np.nan
                collector.repeats.append((name, global_name))
                self.create_extendable_h5_dset(
                    global_name, shape, axis=self.scan_dims, dtype=d.dtype
                )
                self.rep_idx[global_name] = np.zeros(self.base_shape, dtype=int)
                print("init", global_name, shape, d.dtype)
            else:
                global_name = to_dstname(f"{collector.name}_{name}")
                self.data[global_name] = d
                self.h5_meas_group.create_dataset(global_name, data=d)

        for lq_path in collector.settings_to_collect:
            self.create_extendable_h5_dset(
                to_dstname(lq_path),
                shape=self.base_shape + (collector.reps,),
                axis=self.scan_dims,
                dtype=self.app.get_lq(lq_path).dtype,
            )
            self.rep_idx[to_dstname(lq_path)] = np.zeros(self.base_shape, dtype=int)

    def extend_for_reps(self, collectors):
        axis = self.scan_dims

        for collector in collectors:
            for name, d in collector.data.items():
                if name not in collector.repeated_dset_names:
                    continue

                global_name = to_dstname(f"{collector.name}_{name}_raw")
                old_d = self.data[global_name]

                # Create new nan-initialized array with additional repetitions
                nans_to_add = (
                    np.ones(
                        old_d.shape[:axis]
                        + (collector.reps,)
                        + old_d.shape[axis + 1 :],
                        dtype=old_d.dtype,
                    )
                    * np.nan
                )

                # Concatenate old data with new nan-initialized entries
                new_d = np.concatenate((old_d, nans_to_add), axis=axis)
                self.data[global_name] = new_d

                h5_io.extend_h5_dataset_along_axis(
                    self.h5_meas_group[global_name],
                    new_len=new_d.shape[axis],
                    axis=axis,
                )
                # print("extended", global_name, old_d.shape, new_d.shape, new_len)

            for lq_path in collector.settings_to_collect:
                ds = self.h5_meas_group[to_dstname(lq_path)]
                new_len = ds.shape[axis] + collector.reps
                h5_io.extend_h5_dataset_along_axis(ds, new_len, axis)

    def init_dsets_from_memory(self, extendable_axes=None):
        if extendable_axes is None:
            axis = [self.scan_dims]
        else:
            axis = extendable_axes + [self.scan_dims]

        for global_name, d in self.data.items():
            can_extend = np.all(
                len(d.shape) >= a and d.shape[:a] == self.base_shape for a in axis
            )
            should_extend = global_name.endswith("_raw")
            if can_extend and should_extend:
                self.create_extendable_h5_dset(global_name, shape=d.shape, axis=axis)
                self.h5_meas_group[global_name][:] = d
            else:
                self.create_dataset(global_name, data=d)

        self.dsets_initialized = True

    def incorporate(self, collector: Collector, *base_indices):
        """collects data from collectors and writes it to the h5 file"""

        for name, global_name in collector.repeats:
            indices = base_indices + (self.rep_idx[global_name][base_indices],)
            self.data[global_name][indices] = collector.data[name]
            self.h5_meas_group[global_name][indices] = collector.data[name]
            self.rep_idx[global_name][base_indices] += 1
        for lq_path in collector.settings_to_collect:
            val = self.app.get_lq(lq_path).read_from_hardware()
            indices = base_indices + (self.rep_idx[to_dstname(lq_path)][base_indices],)
            self.h5_meas_group[to_dstname(lq_path)][indices] = val
            self.rep_idx[to_dstname(lq_path)][base_indices] += 1

    def average_repeats(self, collector: Collector):
        for name, d in collector.data.items():
            if name in collector.repeated_dset_names:
                avg_name = to_dstname(f"{collector.name}_{name}")
                global_name = to_dstname(f"{collector.name}_{name}_raw")
                d = np.nanmean(self.data[global_name], axis=self.scan_dims)
                self.h5_meas_group.create_dataset(avg_name, data=d)
                print("saved", avg_name, d.shape, d.dtype)

    def get_dset_size_per_position(self, name: str) -> int:
        if name in self.data:
            return int(np.prod(self.data[name].shape[self.scan_dims :]))
        return 0

    def get_dset_dims_per_position(self, name: str) -> Tuple[int]:
        if name in self.data:
            return self.data[name].shape[self.scan_dims :]
        return ()

    def get_dset_size_per_position_and_repeats(self, name: str) -> int:
        if name in self.data:
            return int(np.prod(self.data[name].shape[self.scan_dims + 1 :]))
        return 0

    def get_dset_dims_per_position_and_repeats(self, name: str) -> Tuple[int]:
        if name in self.data:
            return self.data[name].shape[self.scan_dims + 1 :]
        return ()

    def flush_h5(self):
        self.h5_file.flush()

    def create_dataset(self, name, shape=None, dtype=None, data=None, **kwds):
        self.h5_meas_group.create_dataset(name, shape, dtype, data, **kwds)

    def create_extendable_h5_dset(
        self, name, shape=None, dtype=None, data=None, axis=None, **kwds
    ):
        print(name, shape, axis, dtype)
        h5_io.create_extendable_h5_dataset(self.h5_meas_group, name, shape, axis, dtype)

    def close_h5(self):
        self.h5_meas_group.create_dataset("positions", data=self.positions)
        self.h5_meas_group.create_dataset("read_positions", data=self.read_positions)
        self.h5_meas_group.create_dataset("indices", data=self.indices)
        self.h5_file.flush()
        self.h5_file.close()
