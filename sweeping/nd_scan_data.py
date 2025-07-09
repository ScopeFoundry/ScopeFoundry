from typing import Tuple, Dict

import numpy as np

from ScopeFoundry.measurement import Measurement
from .collector import Collector


def to_dstname(name: str) -> str:
    return name.replace("/", "__")


class NDScanData:

    def __init__(
        self,
        base_shape: Tuple[int],
        measurement: Measurement,
    ):
        self.data: Dict[str, np.ndarray] = {}
        self.base_shape = base_shape

        self.measurement = measurement
        self.app = measurement.app

        self.positions = []
        self.read_positions = []
        self.indices = []

        self.h5_meas_group = measurement.open_new_h5_file()
        self.h5_file = measurement.h5_file
        self.metadata = measurement.dataset_metadata

    def add_position(self, positions: Tuple[float]):
        self.positions.append(positions)

    def add_read_positions(self, positions: Tuple[float]):
        self.read_positions.append(positions)

    def add_indices(self, indices: Tuple[int]):
        self.indices.append(indices)

    def init_dsets(self, collector: Collector):
        collector.repeats = []
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
                self.data[global_name] = np.zeros(shape, dtype=d.dtype)
                collector.repeats.append((name, global_name))
                self.h5_meas_group.create_dataset(global_name, shape, dtype=d.dtype)
                print("init", global_name, shape, d.dtype)
            else:
                global_name = to_dstname(f"{collector.name}_{name}")
                self.data[global_name] = d
                self.h5_meas_group.create_dataset(global_name, data=d)

        for lq_path in collector.settings_to_collect:
            self.h5_meas_group.create_dataset(to_dstname(lq_path), shape)

    def incorporate(self, collector: Collector, *indices):
        """collects data from collectors and writes it to the h5 file"""

        for name, global_name in collector.repeats:
            self.data[global_name][indices] = collector.data[name]
            self.h5_meas_group[global_name][indices] = collector.data[name]
        for lq_path in collector.settings_to_collect:
            val = self.app.get_lq(lq_path).read_from_hardware()
            self.h5_meas_group[to_dstname(lq_path)][indices] = val

    def average_repeats(self, collector: Collector):
        for name, d in collector.data.items():
            if name in collector.repeated_dset_names:
                avg_name = to_dstname(f"{collector.name}_{name}")
                global_name = to_dstname(f"{collector.name}_{name}_raw")
                d = self.data[global_name].mean(axis=len(self.base_shape))
                self.h5_meas_group.create_dataset(avg_name, data=d)
                print("saved", avg_name, d.shape, d.dtype)

    def flush_h5(self):
        self.h5_file.flush()

    def close_h5(self):
        self.h5_meas_group.create_dataset("positions", data=self.positions)
        self.h5_meas_group.create_dataset("read_positions", data=self.read_positions)
        self.h5_meas_group.create_dataset("indices", data=self.indices)
        self.h5_file.flush()
        self.h5_file.close()
