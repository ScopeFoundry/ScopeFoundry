import itertools
from pathlib import Path
import time
from copy import copy
from typing import Dict, Sequence, Tuple, Union, List, TypedDict, Generator, Callable
from functools import partial

import matplotlib.pyplot as plt
import numpy as np
import pyqtgraph as pg
from qtpy import QtWidgets

from ScopeFoundry import BaseMicroscopeApp, Measurement
from ScopeFoundry.scanning.actuators import (
    ActuatorDefinitions,
    ActuatorInfos,
    add_all_possible_actuators_and_parse_definitions,
    get_actuator_funcs,
)
from .monitor_ui_list import InteractiveMonitorList
from .any_measurement_collector import AnyMeasurementCollector
from .any_setting_collector import AnySettingCollector
from .collector import Collector
from .collector_ui_list import InteractiveCollectorList
from .nd_scan_data import NDScanData
from .utils import filtered_lq_paths, mk_new_dir
from .locator import LocatorX
from .position_list import PositionList


class SweepConfig(TypedDict):
    positions_gen_func: Callable[[], Generator[float]]
    base_indices_gen_func: Callable[[], Generator[int]]
    progress_index_gen_func: Callable[[], Generator[int]]
    N: int


class SweepNDBase(Measurement):
    """Base class for N-dimensional sweep measurements.

    This class provides common functionality for Sweep1D, Sweep2D, Sweep3D, and Sweep4D.
    Child classes should override specific methods as needed to customize behavior.
    """

    name = "sweep_nd_base"

    def run(self):
        """Main run method - orchestrates the entire scan process."""
        if not self._validate_seep_setup():
            return

        self._setup_sweep_environment()
        sweep_config = self._prepare_sweep_configuration()

        self._execute_sweep(sweep_config)
        self._finalize_sweep()

    def _validate_seep_setup(self) -> bool:
        """Validate that scan can proceed with current settings."""
        self.display_ready = False
        s = self.settings

        self.mk_ranges_consistent(s, self.actuator_names)

        collectors = self.collector_list_widget.get_collectors()
        if not collectors:
            self.set_status("set collector repetitions to non-zero", "r", True)
            return False

        actuators = self.get_current_actuator_funcs()
        if not actuators:
            self.set_status("no actuators selected", "r")
            return False

        return True

    def _setup_sweep_environment(self):
        """Setup environment for scan execution."""
        s = self.settings
        collectors = self.collector_list_widget.get_collectors()

        # Handle any_measurement collector
        if "any_measurement" in (col.name for col in collectors):
            self.pre_res_in_new_dir = s["res_in_new_dir"]
            s["res_in_new_dir"] = True

        # Setup new directory if needed
        if s["res_in_new_dir"]:
            self.root = self.app.settings["save_dir"]
            self.app.settings["save_dir"] = mk_new_dir(self.root, self.name)

    def _prepare_sweep_configuration(self) -> SweepConfig:
        """Prepare scan configuration based on scan mode."""
        s = self.settings

        if s["scan_mode"] == "RETAKE_POSITIONS":
            return self._prepare_retake_config()
        elif s["scan_mode"] == "RETAKE_SLICE":
            return self._prepare_retake_slice_config()
        elif s["scan_mode"] == "ADD_REPS":
            return self._prepare_add_averages_config()
        else:
            return self._prepare_new_sweep_config()

    def _prepare_retake_config(self) -> SweepConfig:
        """Prepare configuration for RETAKE_POSITIONS scan mode."""
        target_positions = self.position_list.get_items()
        indices = []
        base_indices = []
        positions = []

        for target_position in target_positions:
            index = find_nearest_position_index(
                self.scan_data.positions, target_position
            )
            indices.append(index)
            base_indices.append(self.scan_data.indices[index])
            positions.append(self.scan_data.positions[index])

        # Setup scan data
        scan_data = self.scan_data
        scan_data.open_new_h5_file()
        scan_data.init_dsets_from_memory()

        indices.append(len(scan_data.positions) - 1)

        self.set_status(f"Retaking data at index {self.progress_index}", "y")
        self.display_ready = True

        for k, v in scan_data.rep_idx.items():
            for idx in base_indices:
                scan_data.rep_idx[k][idx] *= 0
        scan_data.current_sweep = 0

        return {
            "positions_gen_func": lambda: (pos for pos in positions),
            "base_indices_gen_func": lambda: (idx for idx in base_indices),
            "progress_index_gen_func": lambda: (i + 1 for i in indices),
            "N": len(indices),
        }

    def _prepare_retake_slice_config(self) -> SweepConfig:
        """Prepare configuration for RETAKE_SLICE scan mode."""
        ii_min = self.settings["retake_slice_start"]
        ii_max = self.settings["retake_slice_stop"]

        scan_data = self.scan_data
        scan_data.open_new_h5_file()
        scan_data.init_dsets_from_memory()

        self.set_status(f"Retaking a slice of data", "y")
        self.display_ready = True

        for k, v in scan_data.rep_idx.items():
            for idx in scan_data.indices[ii_min:ii_max]:
                scan_data.rep_idx[k][idx] *= 0
        scan_data.current_sweep = 0

        return {
            "positions_gen_func": lambda: (
                pos for pos in scan_data.positions[ii_min:ii_max]
            ),
            "base_indices_gen_func": lambda: (
                idx for idx in scan_data.indices[ii_min:ii_max]
            ),
            "progress_index_gen_func": lambda: itertools.count(ii_min, 1),
            "N": ii_max - ii_min,
        }

    def _prepare_add_averages_config(self) -> SweepConfig:
        """Prepare configuration for ADD_AVERAGES scan mode."""
        # Reuse existing scan data and extend it with more repetitions
        # Use existing positions and indices

        scan_data = self.scan_data
        scan_data.open_new_h5_file()
        scan_data.init_dsets_from_memory()

        self.set_status("Adding more averages to existing data", "y")
        self.display_ready = True

        return {
            "positions_gen_func": lambda: (pos for pos in scan_data.positions),
            "base_indices_gen_func": lambda: (idx for idx in scan_data.indices),
            "progress_index_gen_func": lambda: itertools.count(0, 1),
            "N": len(scan_data.positions),
        }

    def _prepare_new_sweep_config(self) -> SweepConfig:
        """Prepare configuration for new scan."""
        s = self.settings
        arrays = self._mk_sweep_arrays()

        self.scan_data = scan_data = NDScanData(
            base_shape=self.mk_data_shape(*arrays, s["scan_mode"]),
            measurement=self,
        )
        self.data = self.scan_data.data
        self.dataset_names = []
        self.extent_control_names = []

        for array, name in zip(arrays, self.actuator_names):
            self.scan_data.create_dataset(f"range_{name}", data=array)
            self.scan_data.data[f"range_{name}"] = array

        self.display_ready = False

        N = 1
        for arr in arrays:
            N *= arr.size

        return {
            "positions_gen_func": lambda: self.mk_positions_gen(
                *arrays, s["scan_mode"]
            ),
            "base_indices_gen_func": lambda: self.mk_indices_gen(
                *arrays, s["scan_mode"]
            ),
            "progress_index_gen_func": lambda: itertools.count(0, 1),
            "N": N,
        }

    def _mk_sweep_arrays(self) -> tuple:
        """Get arrays for sweep based on settings."""
        s = self.settings

        if s["scan_mode"] == "position_list":
            return tuple(np.array(self.position_list.get_items()).T)

        arrays = []
        for name in self.actuator_names:
            if self.settings[f"from_list_{name}"]:
                pos_list = self.list_uis[name].toPlainText().splitlines()
                pos_list = [s.split("#")[0] for s in pos_list]  # remove comments
                pos_list = [float(p) for p in pos_list if p.strip() != ""]
                arrays.append(np.array(pos_list))
            else:
                arrays.append(
                    np.array(self.settings.ranges[f"range_{name}"].sweep_array)
                )

        return tuple(arrays)

    def _execute_sweep(self, sweep_config: dict):
        """Execute the main sweep loop."""
        s = self.settings
        collectors = self.collector_list_widget.get_collectors()
        actuators = self.get_current_actuator_funcs()

        scan_data = self.scan_data
        positions_gen_func = sweep_config["positions_gen_func"]
        base_indices_gen_func = sweep_config["base_indices_gen_func"]
        progress_index_gen_func = sweep_config["progress_index_gen_func"]
        N = sweep_config["N"]

        self.monitor_list_widget.start_all_monitors()

        self.first_loop = True

        while True:
            # print("current sweep", self.scan_data.current_sweep)

            if not self._should_continue_sweep():
                break

            if self.scan_data.current_sweep > 0:
                scan_data.extend_for_reps(collectors)

            # not sure why this can not be packed in the zip() directly.
            pos_list = list(positions_gen_func())
            base_list = list(base_indices_gen_func())

            progress_index_gen = progress_index_gen_func()
            self.progress_index = next(progress_index_gen)

            for ii, (positions, base_indices) in enumerate(zip(pos_list, base_list)):
                if self.interrupt_measurement_called:
                    break
                self._execute_position(
                    positions,
                    base_indices,
                    actuators,
                    collectors,
                    s,
                    ii,
                )

                # Update UI choices on first position
                if not self.scan_data.dsets_initialized:
                    self.settings.get_lq("dataset").change_choice_list(
                        self.dataset_names
                    )
                    self.settings.get_lq("extent_control").change_choice_list(
                        self.extent_control_names + ["None"]
                    )
                    self.scan_data.dsets_initialized = True
                    # self.post_dset_initialized()

                self.progress_index = next(progress_index_gen)
                self.set_progress(100 * (self.progress_index + 1) / N)

            self.scan_data.current_sweep += 1

    def _should_continue_sweep(self) -> bool:
        """Check if sweep should continue."""

        if self.interrupt_measurement_called:
            return False

        if self.first_loop:
            self.first_loop = False
            return True

        if self.scan_data.current_sweep > 0 and self.settings["scan_mode"].startswith(
            "RETAKE"
        ):
            self.set_status("RETAKE modes - only one sweep allowed", "r")
            return False

        return self.settings["re-sweep"]

    def _execute_position(
        self,
        positions,
        base_indices,
        actuators,
        collectors,
        settings,
        ii,
    ) -> None:
        """Execute a single sweep position. Returns True if sweep should be interrupted."""
        # Set positions and wait
        pretty_pos = ", ".join([f"{p:.1f}" for p in positions])
        self.set_status(f"setting {pretty_pos} and waiting", "g")
        self.go_to_positions(positions, actuators)
        delay = settings["collection_delay"]
        if ii == 0:
            delay += settings["initial_delay"]
        time.sleep(delay)
        read_positions = tuple([read() for read, _ in actuators])

        self.prepare_at_position(positions, base_indices)

        # Process each collector
        for collector in collectors:
            self._execute_collector_at_position(
                collector,
                positions,
                base_indices,
                pretty_pos,
            )

        if (
            not settings["scan_mode"].startswith("RETAKE")
            and self.scan_data.current_sweep == 0
        ):
            self.scan_data.add_position(positions)
            self.scan_data.add_read_positions(read_positions)
            self.scan_data.add_indices(base_indices)

    def _execute_collector_at_position(
        self,
        collector,
        positions,
        base_indices,
        pretty_pos,
    ):
        """Execute a single collector at current position."""
        self.set_status(f"collecting {collector.name} on {pretty_pos}", "g")
        self.prepare_collector_at_position(collector, positions, base_indices)

        self.monitor_list_widget.inform_enabled_monitors(f"start_{collector.name}")

        for r in range(collector.reps):
            if self.interrupt_measurement_called:
                break

            collector.run(self.progress_index, self)

            # Initialize datasets after first run when shapes are known
            if not self.scan_data.dsets_initialized and r == 0:
                self.scan_data.init_dsets(collector)
                self.dataset_names.extend([q[-1] for q in collector.repeats])
                self.extent_control_names = list(self.scan_data.data.keys())
                self.display_ready = True

            time.sleep(0.1)
            self.scan_data.incorporate(collector, *base_indices)

        self.monitor_list_widget.inform_enabled_monitors(f"stop_{collector.name}")
        self.release_collector(collector, positions, base_indices)

    def _finalize_sweep(self):
        """Finalize sweep - cleanup and save data."""
        s = self.settings
        collectors = self.collector_list_widget.get_collectors()
        scan_data = self.scan_data

        self.post_scan()
        self.monitor_list_widget.stop_all_monitors()
        self.progress_index = len(self.scan_data.positions)

        # Save monitor data
        for k, v in self.monitor_list_widget.get_all_data().items():
            print(k, v)
            self.scan_data.h5_meas_group.create_dataset(k, data=v)

        # Average repeats and close file
        for collector in collectors:
            scan_data.average_repeats(collector)
        scan_data.close_h5()

        # Restore directory settings
        if s["res_in_new_dir"]:
            s["res_in_new_dir"] = self.pre_res_in_new_dir
            self.app.settings["save_dir"] = self.root

        self.set_status(f"{self.name} finished", "g")
        print("finished - data collected:")
        for k, v in scan_data.data.items():
            print(k, np.array(v).shape)

    def post_run(self) -> None:
        self.save_png()

    def go_to_positions(self, positions, actuators=None) -> None:
        if actuators is None:
            actuators = self.get_current_actuator_funcs()
        for (_, write), position in zip(actuators, positions):
            write(position)

    def prepare_at_position(
        self, positions: Tuple[float], base_indices: Tuple[int]
    ) -> None:
        """Optional override.

        Intended for setting up collectors.
        Gets called after position is set, But before data collection.

        - positions: tuple of positions
        - base_indices: tuple of indices of the current position in the scan data

        Note, that data handling is defined in respective collectors and not here.
        """
        pass

    def prepare_collector_at_position(
        self, collector: Collector, positions: Tuple[float], base_indices: Tuple[int]
    ) -> None:
        """Optional override.

        Intended for setting up a specific collector.
        This method is called for each collector before data collection.

        Note that the default behavior is to call the collector's prepare method.

        Arguments:
        - positions: tuple of positions
        - base_indices: tuple of indices of the current position in the scan data

        Note, that data handling is defined in respective collectors and not here.
        """
        collector.prepare(self, positions)

    def release_collector(
        self, collector: Collector, positions: Tuple[float], base_indices: Tuple[int]
    ) -> None:
        """Optional override.
        Intended to 'undo' the prepare_collector_at_position method if needed.
        """
        collector.release(self, positions)

    def post_scan(self) -> None:
        """Optional override.
        Gets called after data collection is finished - before file is closed.
        """
        pass

    def post_dset_initialized(self) -> None:
        """Optional override.
        Gets called after datasets are initialized (usually after first position is executed and all datasets names are known).
        """
        pass

    def __init__(
        self,
        app: BaseMicroscopeApp,
        name: Union[str, None] = None,
        collectors: Sequence[Collector] = (),
        actuators: Sequence[ActuatorDefinitions] = (),
        actuator_names: Sequence[str] = "1",
        range_n_intervals: Sequence[int] = (1,),
        n_read_any_settings: int = 2,
        n_any_measurements: int = 2,
    ):
        self.collectors = [copy(x) for x in collectors]
        self.user_defined_actuators = list(actuators)
        self.actuator_names = actuator_names
        self.range_n_intervals = range_n_intervals
        self.ndim = len(actuator_names)
        self.n_read_any_settings = n_read_any_settings
        self.n_any_measurements = n_any_measurements
        self.max_npoints_shown = 1_000_000
        self.data = {}
        self.dataset_names = []
        self.extent_control_names = []
        super().__init__(app, name)

    def setup(self) -> None:
        self.display_ready = False

        s = self.settings
        s.New(
            name="scan_mode",
            dtype=str,
            initial="nested",
            choices=list(self.get_scan_modes())
            + [
                "position_list",
                "RETAKE_POSITIONS",
                "RETAKE_SLICE",
                "ADD_REPS",
            ],
            description="<h3>Create new sweep:</h3>"
            + "<i>specify the values each actuator takes during the sweep (either by ranges or a list of positions). Use one of the following modes to define how the values are combined. </i>"
            + self.get_scan_modes_description()
            + "<p><i>position_list:</i> positions are defined by this Measurement's Position List.</p>"
            + "<br>"
            + "<h3>MODIFY or EXTEND previous sweep:</h3>"
            + "<i>never alters/deletes saved data files, always makes new files, reuses data in memory</i>"
            + "<p><i>RETAKE_POSITIONS:</i> Allows to retake (fix) inidiviual data points specified in Position List. To add positions ctrl click on data. Makes a new datafile with data in memory with retaken data points updated.</p>"
            + "<p><i>RETAKE_SLICE:</i> Retake a slice of data specified by start and stop indices. Makes a new datafile with data in memory with retaken data points updated.</p>"
            + "<p><i>ADD_REPS:</i> Adds more repetitions to existing scan data to improve signal-to-noise ratio through additional averaging. You can change the number of repetitions for collectors that are already active (i.e. have non-zero repetitions) and activate <i>re-sweep</i>. Makes a new datafile with data with more repetitions.</p>",
        )
        s.New(
            name="collection_delay",
            initial=0.01,
            unit="s",
            description="after setting first actuator(s) position(s), data collection is delayed, allowing the system to reach steady state",
        )
        s.New(
            name="initial_delay",
            initial=0.0,
            unit="s",
            description="additional delay added to collection_delay for the first point sweep. Useful when reaching first sweep point takes somwhat longer than the rest of the points.",
        )
        s.New(
            name="res_in_new_dir",
            dtype=bool,
            initial=False,
            description="dumps data in a new subfolder. Intended for <i>any_measurement</i> where a file is stored per acquisition",
        )
        s.New(
            name="dataset",
            dtype=str,
            initial="",
            choices=("",),
            description="set dataset to plot",
        ).add_listener(self.update_display)
        s.New(
            name="extent_control",
            dtype=str,
            initial="",
            choices=("",),
            description="dataset to use for extent control",
        ).add_listener(self.update_display)
        s.New("average_over_repetitions", dtype=bool, initial=True).add_listener(
            self.update_display
        )

        s.New(
            name="position_representation",
            dtype=str,
            initial="flat",
            choices=["flat", "map_vertical"],
            description="<p>flat: flattened data per sweep point flattend and aranged in order measured<p>map_vertical: data at positions is along vertical direction of a map",
        ).add_listener(self.update_display)
        s.New(
            name="dset_reducer",
            dtype=str,
            initial="None",
            choices=["None", "max", "min", "center_index"],
            description="<p>Reduce the data to a number at each sweep point:<p>None: no reduction<p>max: maximum<p>min: minimum<p>center_index: middle data point when data per point is flattened",
        ).add_listener(self.update_display)

        s.New(
            "retake_slice_start",
            int,
            initial=0,
            description="start index of slice to retake (inclusive)",
        )
        s.New(
            "retake_slice_stop",
            int,
            initial=0,
            description="stop index of slice to retake (EXCLUSIVE!)",
        )
        s.New(
            "re-sweep",
            bool,
            initial=False,
            description="after current sweep is completed the measurement restarts (indefinitely) to add more repetitions. Uncheck to stop the measurement after current sweep is completed.",
        )
        for i in range(self.n_any_measurements):
            self.collectors.append(
                AnyMeasurementCollector(self, name=f"any_measurement_{i}")
            )

        for i in range(self.n_read_any_settings):
            self.collectors.append(AnySettingCollector(self, name=f"any_setting_{i}"))

        for collector in self.collectors:
            collector.setup_reps_lq(s)
            collector.setup()
            self.settings.claim_settings(collector.settings, collector.name)

        self.scan_ranges = []
        for name, n in zip(self.actuator_names, self.range_n_intervals):
            s.New(f"actuator_{name}", dtype=str, choices=["none"])
            s.New(
                f"from_list_{name}",
                dtype=bool,
                initial=False,
                description="use a manual list instead of a parametric range. Put one number per line. Comments can be added after #",
            )
            if n == 1:
                self.scan_ranges.append(
                    s.New_Range(f"range_{name}", True, False, initials=(1, 2, 11))
                )
            else:
                self.scan_ranges.append(
                    s.new_intervaled_range(f"range_{name}", n, False, True)
                )

        self.add_operation(
            "update widgets",
            self.update_widgets,
            description="click after connecting to hardware to extend actuator options",
            icon_path=self.app.qtapp.style().standardIcon(
                QtWidgets.QStyle.SP_BrowserReload
            ),
        )

        self.scan_data = NDScanData(
            base_shape=(2,),
            measurement=self,
            open_new_h5=False,  # dummy initialization, avoid opening file here
        )
        self.data = self.scan_data.data

        self.position_list = PositionList(self)

    def update_widgets(self) -> None:

        s = self.settings

        paths = filtered_lq_paths(self.app, False)
        for i in range(self.n_read_any_settings):
            s.get_lq(f"any_setting_{i}").change_choice_list(paths)

        for monitor in self.monitor_list_widget.get_monitors():
            monitor.settings.get_lq("setting").change_choice_list(paths)

        self.actuator_defs = add_all_possible_actuators_and_parse_definitions(
            actuator_definitions=self.user_defined_actuators, app=self.app
        )
        self.actuators_funcs = get_actuator_funcs(self.app, self.actuator_defs)

        for i in self.actuator_names:
            s.get_lq(f"actuator_{i}").change_choice_list(self.actuators_funcs.keys())

    def setup_figure(self) -> None:
        s = self.settings

        # Top horizontal section
        top_widget = QtWidgets.QWidget()
        top_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        top_widget.setMaximumHeight(340)
        top_layout = QtWidgets.QHBoxLayout(top_widget)
        top_layout.setSpacing(4)
        top_layout.setContentsMargins(2, 0, 2, 0)
        self.run_widget = self.mk_run_widget()
        self.run_layout = self.run_widget.layout()
        top_layout.addWidget(self.run_widget)
        top_layout.addWidget(self.mk_scan_settings_widget())
        top_layout.addWidget(self.mk_collect_widget())

        self.ui = QtWidgets.QWidget()
        self.ui.setStyleSheet("""
            QGroupBox {
                font-weight: 600;
                border: 1px solid #888888;
                border-radius: 3px;
                margin-top: 8px;
                padding-top: 6px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
            }
        """)
        layout = QtWidgets.QVBoxLayout(self.ui)
        layout.setSpacing(4)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(top_widget)

        # order matters here
        graph_widget = self.mk_graph_widget()

        layout.addWidget(self.mk_plot_options_widget())
        layout.addWidget(self.wrap_with_position_list_widget(graph_widget))

        self.display_ready = False
        self.set_status(f"starting {self.name}", "y")
        s.get_lq("dataset").add_listener(self.update_display)
        for i in range(self.n_any_measurements):
            s.get_lq(f"any_measurement_{i}").change_choice_list(
                self.app.measurements.keys()
            )
        for i in range(self.n_read_any_settings):
            s.get_lq(f"any_setting_{i}").change_choice_list(
                self.app.get_setting_paths(True)
            )

        self.set_status("welc\u1e4fme", (253, 188, 24), True)

        self.update_widgets()

    def update_display(self) -> None:
        self.update_status_display()

        if not self.display_ready:
            return

        img, size, i_min, i_max = self._get_plot_data()
        if img is None:
            return

        if size == 1:
            self.settings["position_representation"] = "flat"

        # Update locator properties
        self.locator.size = size
        self.locator.i_min = i_min
        self.locator.real_position_on_x = self._should_use_real_positions(size)

        x = self._get_x_data(i_min, i_max, size)

        # Plot based on representation mode
        if self.settings["position_representation"] == "flat":
            x_label, y_label = self.flat_configs()
            if x is not None:
                y = np.squeeze(img)
                self.line.setData(x, y)
            else:
                y = np.squeeze(img).ravel()
                self.line.setData(y)

        elif self.settings["position_representation"] == "map_vertical":
            (x0, x1, y0, y1), x_label, y_label = self.imshow_configs(
                i_min, i_max, x, size
            )
            rect = pg.QtCore.QRectF(x0, y0, x1 - x0, y1 - y0)
            self.img_item.setImage(img, rect=rect, autoLevels=True)

        self.axes.setLabel("bottom", x_label)
        self.axes.setLabel("left", y_label)

        # Show appropriate plot type
        show_image = self.settings["position_representation"] == "map_vertical"
        self.img_item.setVisible(show_image)
        self.line.setVisible(not show_image)

    def set_status(
        self,
        msg: str,
        color: Union[str, Tuple[int, int, int]] = "w",
        force_report: bool = False,
    ) -> None:
        self.status = {"title": msg, "color": color}
        if force_report:
            self.update_status_display()

    def update_status_display(self) -> None:
        if not self.display_ready:
            return
        self.axes.setTitle(**self.status)

    def mk_run_widget(self) -> QtWidgets.QWidget:
        run_widget = QtWidgets.QGroupBox("Run Control")
        run_widget.setStyleSheet("""
            QPushButton {
                padding: 4px 8px;
                font-weight: 500;
            }
        """)

        vlayout = QtWidgets.QVBoxLayout(run_widget)
        vlayout.setSpacing(4)
        vlayout.setContentsMargins(8, 12, 8, 8)

        vlayout.addWidget(self.new_start_stop_button())

        include = ("collection_delay", "initial_delay", "res_in_new_dir", "re-sweep")
        vlayout.addWidget(self.settings.New_UI(include))

        update_btn = self.operations.new_button("update widgets")
        update_btn.setStyleSheet("""
            QPushButton {
                color: #1976d2;
                font-weight: 500;
            }
        """)
        vlayout.addWidget(update_btn)

        run_widget.setFlat(False)
        run_widget.setMaximumWidth(220)
        return run_widget

    def mk_scan_settings_widget(self) -> QtWidgets.QWidget:
        """Create the scan settings widget. Override in child classes for custom layout."""
        mode_selector_mode = self.settings.New_UI(("scan_mode",))

        params_widget = QtWidgets.QWidget()
        params_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Maximum,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )

        h_layout = QtWidgets.QHBoxLayout(params_widget)
        self.list_uis = {}
        for ii, name in enumerate(self.actuator_names):
            r = self.settings.ranges[f"range_{name}"]

            range_ui = r.New_UI(include_clipboard_btns=True)
            list_ui = QtWidgets.QTextEdit()

            if self.range_n_intervals[ii] > 1:
                width = 540
            else:
                width = 190
            range_ui.setMaximumWidth(width)
            list_ui.setMaximumWidth(width)
            list_ui.setText("# Enter one number per line.\n")
            self.list_uis[name] = list_ui
            list_ui.setVisible(False)

            from_list_lq = self.settings.get_lq(f"from_list_{name}")

            def toggle_list_ui(range_ui, list_ui, checked):
                list_ui.setVisible(checked)
                range_ui.setVisible(not checked)

            from_list_lq.updated_value[bool].connect(
                partial(toggle_list_ui, range_ui, list_ui)
            )

            layout = QtWidgets.QVBoxLayout()
            w1 = self.settings.get_lq(f"actuator_{name}").new_default_widget()
            w2 = self.settings.New_UI((f"from_list_{name}",))
            w1.setMaximumWidth(width)
            w2.setMaximumWidth(width)

            layout.addWidget(w1)
            layout.addWidget(w2)
            layout.addWidget(list_ui)
            layout.addWidget(range_ui)
            layout.setSpacing(3)
            h_layout.addLayout(layout)

        self.retake_widget = QtWidgets.QTextEdit(
            f"<p>Retakes data at positions defined in Position List. To add positions ctrl click on data.</p><p>Uses existing data in memory and creates a new file with updated data at specified points.</p><p><b>Note:</b> Position List should contain positions from the current scan that need to be re-measured.</p>"
        )
        self.retake_widget.setReadOnly(True)
        self.retake_widget.setVisible(False)
        # self.retake_widget.setMaximumWidth(350)

        self.position_list_widget = QtWidgets.QTextEdit(
            f"<p>Sweeps over positions defined in the Position List. To add positions ctrl click on data.</p><p>Each position should specify coordinates for all actuators in order.</p>"
        )
        self.position_list_widget.setReadOnly(True)
        self.position_list_widget.setVisible(False)
        # self.position_list_widget.setMaximumWidth(350)

        self.retake_slice_widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(self.retake_slice_widget)
        w = QtWidgets.QTextEdit(
            f"<p>Retakes data at positions defined by indices of the sweep. Index i corresponds to i-th data point taken. Designed for re-measurement of adjacent points.</p><p>Uses existing scan data in memory and creates a new file with updated measurements at specified positions.</p>"
        )
        w.setReadOnly(True)
        layout.addWidget(w)
        layout.addWidget(
            self.settings.New_UI(("retake_slice_start", "retake_slice_stop"))
        )
        self.retake_slice_widget.setVisible(False)
        # self.retake_slice_widget.setMaximumWidth(350)

        self.add_reps_widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(self.add_reps_widget)
        w = QtWidgets.QTextEdit(
            f"<p>Extends data by re running the last sweep. <p> You can change the number of repetitions for collectors that are already active (i.e. have non-zero repetitions) and activate re-sweep.</p>"
        )
        w.setReadOnly(True)
        layout.addWidget(w)
        self.add_reps_widget.setVisible(False)

        lu: Dict[str, QtWidgets.QWidget] = {
            "position_list": self.position_list_widget,
            "RETAKE_POSITIONS": self.retake_widget,
            "RETAKE_SLICE": self.retake_slice_widget,
            "ADD_REPS": self.add_reps_widget,
        }

        def toggle_mode_selector(mode):
            params_widget.setHidden(mode in lu.keys())
            for m, w in lu.items():
                show = m == mode
                w.setHidden(not show)

        self.settings.get_lq("scan_mode").updated_value[str].connect(
            toggle_mode_selector
        )

        widget = QtWidgets.QGroupBox("Actuators: Define scan positions")
        v_layout = QtWidgets.QVBoxLayout(widget)
        v_layout.setSpacing(0)
        v_layout.setContentsMargins(2, 2, 2, 2)
        v_layout.addWidget(mode_selector_mode)
        v_layout.addWidget(params_widget)
        v_layout.addWidget(self.retake_widget)
        v_layout.addWidget(self.position_list_widget)
        v_layout.addWidget(self.retake_slice_widget)
        v_layout.addWidget(self.add_reps_widget)
        widget.setFlat(False)
        return widget

    def mk_collect_widget(self) -> QtWidgets.QWidget:
        self.collector_list_widget = InteractiveCollectorList()
        for collector in self.collectors:
            self.collector_list_widget.add_item(collector)

        self.monitor_list_widget = InteractiveMonitorList(self)

        widget = QtWidgets.QGroupBox("Data Collectors: Set repetitions and order")
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setSpacing(4)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.addWidget(self.collector_list_widget)
        layout.addWidget(self.monitor_list_widget)
        return widget

    def mk_plot_options_widget(self) -> QtWidgets.QWidget:
        # Plot options group
        plot_gb = QtWidgets.QGroupBox("Plot Options")
        plot_layout = QtWidgets.QHBoxLayout(plot_gb)
        plot_layout.setContentsMargins(6, 6, 6, 6)
        plot_layout.setSpacing(4)

        glayout = QtWidgets.QGridLayout()

        w1 = self.settings.get_lq("dataset").new_default_widget()
        w10 = QtWidgets.QLabel("Dataset:")
        # w1.setMaximumWidth(400)
        # w10.setMaximumWidth(400)
        glayout.addWidget(w10, 0, 0)
        glayout.addWidget(w1, 1, 0)

        w3 = self.settings.get_lq("average_over_repetitions").new_default_widget()
        w3.setMaximumWidth(120)
        l3 = QtWidgets.QLabel("Average reps:")
        l3.setMaximumWidth(90)

        glayout.addWidget(l3, 0, 1)
        glayout.addWidget(w3, 0, 2)
        w5 = self.settings.get_lq("dset_reducer").new_default_widget()
        l5 = QtWidgets.QLabel("reduce")
        glayout.addWidget(l5, 1, 1)
        glayout.addWidget(w5, 1, 2)

        w2 = self.settings.get_lq("position_representation").new_default_widget()
        w2.setMaximumWidth(150)
        l2 = QtWidgets.QLabel("Position Representation:")
        glayout.addWidget(l2, 0, 3)
        glayout.addWidget(w2, 1, 3)

        w4 = self.settings.get_lq("extent_control").new_default_widget()
        w40 = QtWidgets.QLabel("y-extent")
        # w4.setMaximumWidth(120)
        # w40.setMaximumWidth(120)
        glayout.addWidget(w40, 0, 4)
        glayout.addWidget(w4, 1, 4)

        w40.setVisible(False)
        w4.setVisible(False)

        self.settings.get_lq("position_representation").updated_value[str].connect(
            lambda mode: w40.setVisible(mode == "map_vertical")
        )
        self.settings.get_lq("position_representation").updated_value[str].connect(
            lambda mode: w4.setVisible(mode == "map_vertical")
        )
        plot_layout.addLayout(glayout)

        # Container with horizontal layout holding both group boxes
        container = QtWidgets.QWidget()
        h_layout = QtWidgets.QHBoxLayout(container)
        h_layout.setContentsMargins(3, 3, 3, 3)
        h_layout.setSpacing(4)
        h_layout.addWidget(plot_gb)

        if hasattr(self, "locator"):
            h_layout.addWidget(self.locator.mk_widget())
        else:
            self.log.warning(
                f"Does not have a locator! Recommend to add one at self.mk_graph_widget method or self.setup_figure\n self.locator = LocatorX(self, self.position_list) or (self.locator = LocatorRoi for 2D sweeps)\n self.locator.set_axes(self.axes) \n Trying to add LocatorX..."
            )
            try:
                self.locator = LocatorX(self, self.position_list)
                self.locator.set_axes(self.axes)
                h_layout.addWidget(self.locator.mk_widget())
                self.log.warning(
                    f"added LocatorX successfully. Recommend to add it properly in the child class code."
                )
            except Exception as e:
                self.log.warning(f"Failed to make locator: {e}")

        # container.setMaximumHeight(150)
        # container.setMaximumWidth(800)
        container.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
            QtWidgets.QSizePolicy.Policy.Maximum,
        )

        return container

    def mk_graph_widget(self) -> QtWidgets.QWidget:
        graph_widget = pg.GraphicsLayoutWidget()
        graph_widget.setStyleSheet("""
            QGraphicsView {
                border: 1px solid #888888;
                border-radius: 3px;
            }
        """)

        self.axes = graph_widget.addPlot(title=self.name)
        self.axes.setLogMode(False, False)
        self.axes.showGrid(True, True, alpha=0.4)

        # Improved line with better color
        self.line = self.axes.plot()
        self.img_item = pg.ImageItem()
        self.axes.addItem(self.img_item)
        self.img_item.setVisible(False)

        graph_widget.setMinimumHeight(400)
        graph_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
        )

        graph_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred
        )

        self.locator = LocatorX(self, self.position_list)
        self.locator.set_axes(self.axes)
        return graph_widget

    def wrap_with_position_list_widget(
        self, graph_widget: QtWidgets.QWidget
    ) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(widget)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(graph_widget)
        layout.addWidget(self.position_list.mk_widget())
        return widget

    def get_current_actuators_defs(self) -> List[ActuatorInfos]:
        """Returns a list of currently selected actuator definitions."""
        s = self.settings
        return [self.actuator_defs[s[f"actuator_{i}"]] for i in self.actuator_names]

    def get_current_actuator_funcs(self) -> List:
        s = self.settings
        return [self.actuators_funcs[s[f"actuator_{i}"]] for i in self.actuator_names]

    def get_current_target_position_funcs(self) -> List:
        return (a[-1] for a in self.get_current_actuator_funcs())

    def load_data(self, raw_data) -> None:
        self.scan_data.data = {n: v for n, v in raw_data.items() if n.endswith("_raw")}
        self.data = self.scan_data.data
        self.settings.get_lq("dataset").change_choice_list(list(self.data.keys()))
        self.scan_data.positions = raw_data["positions"]
        self.progress_index = len(raw_data["positions"] - 1)
        self.display_ready = True

    # Abstract methods that child classes should implement
    def get_scan_modes(self) -> Tuple:
        """Return the SCAN_MODES tuple for this sweep type."""
        raise NotImplementedError("Child class must implement get_scan_modes()")

    def get_scan_modes_description(self) -> Tuple[str, ...]:
        """Return the SCAN_MODES_DESCRIPTION for this sweep type."""
        raise NotImplementedError(
            "Child class must implement get_scan_modes_description()"
        )

    def mk_data_shape(self, *args) -> Tuple[int, ...]:
        """Return the data shape for this sweep type."""
        raise NotImplementedError("Child class must implement mk_data_shape()")

    def mk_indices_gen(self, *args) -> Generator[Tuple[int, ...]]:
        """Return the indices generator for this sweep type."""
        raise NotImplementedError("Child class must implement mk_indices_gen()")

    def mk_positions_gen(self, *args):
        """Return the positions generator for this sweep type."""
        raise NotImplementedError("Child class must implement mk_positions_gen()")

    def mk_ranges_consistent(self, settings, actuator_names):
        """Make ranges consistent for this sweep type."""
        raise NotImplementedError("Child class must implement mk_ranges_consistent()")

    def should_show_positions_on_x_axis(self):
        """Return whether positions should be shown on x-axis in update_display."""
        return self.settings["scan_mode"] == "co-move"

    def _get_plot_data(self):
        """Get processed data for plotting.

        Returns:
            tuple: (img, size, i_min, i_max) where:
                - img: processed image data
                - size: size per position
                - i_min, i_max: data range indices
        """
        if not self.display_ready or not self.settings["dataset"]:
            return None, None, None, None

        dataset_name = self.settings["dataset"]

        if self.settings["average_over_repetitions"]:
            import warnings

            warnings.filterwarnings("ignore", category=RuntimeWarning)
            dset = np.nanmean(self.scan_data.data[dataset_name], axis=self.ndim)
            size = self.scan_data.get_dset_size_per_position_and_repeats(dataset_name)
        else:
            dset = self.scan_data.data[dataset_name]
            size = self.scan_data.get_dset_size_per_position(dataset_name)

        # Flatten data to positions x size
        img = dset[tuple(zip(*self.scan_data.indices))].reshape((-1, size))

        if self.settings["dset_reducer"] == "None":
            pass
        elif self.settings["dset_reducer"] == "max":
            img = np.nanmax(img, axis=1).reshape((-1, 1))
            size = 1
        elif self.settings["dset_reducer"] == "min":
            img = np.nanmin(img, axis=1).reshape((-1, 1))
            size = 1
        elif self.settings["dset_reducer"] == "center_index":
            img = img[:, img.size // 2].reshape((-1, 1))
            size = 1

        # Apply data range limits
        i_span_max = self.max_npoints_shown // size
        i_max = len(self.scan_data.positions)
        i_min = max(i_max - i_span_max, 0)
        img = img[i_min:i_max, :]

        return img, size, i_min, i_max

    def _should_use_real_positions(self, size):
        """Determine if real positions should be used on x-axis.

        Args:
            size: size per position

        Returns:
            bool: True if real positions should be used
        """
        return (size == 1 and self.should_show_positions_on_x_axis()) or (
            self.settings["position_representation"] == "map_vertical"
            and self.should_show_positions_on_x_axis()
        )

    def flat_configs(self):
        if self.locator.real_position_on_x:
            x_label = self.settings[f"actuator_{self.actuator_names[0]}"].split("/")[0]
        else:
            x_label = "sweep position"
        y_label = self.settings["dataset"]
        return x_label, y_label

    def imshow_configs(self, i_min, i_max, x, size):

        if self.locator.real_position_on_x:
            x_label = self.settings[f"actuator_{self.actuator_names[0]}"].split("/")[0]
        else:
            x_label = "sweep position"

        if (
            self.settings["extent_control"] != "None"
            and self.settings["average_over_repetitions"]
        ):
            y_label = self.settings["extent_control"]
        else:
            y_label = ""

        if (
            self.settings["extent_control"] != "None"
            and self.settings["average_over_repetitions"]
        ):
            ys = self.scan_data.data[self.settings["extent_control"]].flatten()
            dy = ys[1] - ys[0] if len(ys) > 1 else 0.5
            y0 = ys.min() - dy / 2
            y1 = ys.max() + dy / 2
        else:
            y0 = 0
            y1 = size

        if x is not None:
            dx = x[1] - x[0]
            x0 = min(x) - dx / 2
            x1 = max(x) + dx / 2
        else:
            x0 = i_min - 0.5
            x1 = i_max + 0.5

        return (x0, x1, y0, y1), x_label, y_label

    def _get_y_label(self):
        if (
            self.settings["extent_control"] != "None"
            and self.settings["average_over_repetitions"]
        ):
            return self.settings["extent_control"]
        else:
            return ""

    def _get_x_label(self):
        if self.locator.real_position_on_x:
            return self.settings[f"actuator_{self.actuator_names[0]}"].split("/")[0]
        return "sweep position"

    def _get_x_data(self, i_min, i_max, size):
        """Get x-axis data for plotting.

        Args:
            i_min, i_max: data range indices
            size: size per position

        Returns:
            tuple: x_data
        """
        real_position_on_x = self._should_use_real_positions(size)

        if real_position_on_x:
            x = np.squeeze(self.scan_data.positions[i_min:i_max])
            if x.ndim > 1:
                x = x[:, 0]
        else:
            x = None

        return x

    def save_png(self, filename=None):
        """Save the current plot as a PNG file using matplotlib.

        Args:
            filename (str, dataset_nameal): Path to save the PNG file.
        """

        img, size, i_min, i_max = self._get_plot_data()
        if img is None:
            print(self.name, "save_png: No data ready to plot")
            return

        dataset_name = self.settings["dataset"]

        if self.settings["average_over_repetitions"]:
            dataset_name = dataset_name.rstrip("_raw")
        x = self._get_x_data(i_min, i_max, size)

        # Create matplotlib figure
        plt.figure(figsize=(10, 6))

        if self.settings["position_representation"] == "flat":
            x_label, y_label = self.flat_configs()
            if x is not None:
                y = np.squeeze(img)
                plt.plot(x, y, "o-", markersize=2, linewidth=1)
            else:
                y = np.squeeze(img).ravel()
                plt.plot(y, "o-", markersize=2, linewidth=1)
            plt.xlabel(x_label)
            plt.ylabel(y_label)
            plt.grid(True, alpha=0.3)

        elif self.settings["position_representation"] == "map_vertical":
            # Image plot
            extent, x_label, y_label = self.imshow_configs(i_min, i_max, x, size)
            plt.imshow(img.T, aspect="auto", origin="lower", extent=extent)
            plt.xlabel(x_label)
            plt.ylabel(y_label)
            plt.colorbar(label=dataset_name)

        plt.title(f"{self.name} - {dataset_name}")
        plt.tight_layout()

        if filename is None:
            path = self.dataset_metadata.get_file_path(".png")
        else:
            path = Path(self.app.settings["save_dir"]) / filename

        plt.savefig(path, dpi=150, bbox_inches="tight")
        plt.close()

        print(f"Plot saved as: {path}")


def find_nearest_position_index(positions, target_positions) -> int:
    positions_array = np.array(positions)
    target_positions = np.array(target_positions)
    distances = np.linalg.norm(positions_array - target_positions, ord=2, axis=1)
    return int(np.argmin(distances))
