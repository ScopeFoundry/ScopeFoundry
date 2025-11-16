import time
from abc import ABC
from copy import copy
from typing import Sequence, Tuple, Union, List

import numpy as np
import pyqtgraph as pg
from qtpy import QtWidgets, QtCore

from ScopeFoundry import BaseMicroscopeApp, Measurement
from ScopeFoundry.scanning.actuators import (
    ActuatorDefinitions,
    ActuatorInfos,
    add_all_possible_actuators_and_parse_definitions,
    get_actuator_funcs,
)

from .any_measurement_collector import AnyMeasurementCollector
from .any_setting_collector import AnySettingCollector
from .collector import Collector
from .collector_ui_list import InteractiveCollectorList
from .nd_scan_data import NDScanData
from .utils import filtered_lq_paths, mk_new_dir
from .locator import LocatorX
from .position_list import PositionList
from functools import partial


class SweepNDBase(Measurement, ABC):
    """Base class for N-dimensional sweep measurements.

    This class provides common functionality for Sweep1D, Sweep2D, Sweep3D, and Sweep4D.
    Child classes should override specific methods as needed to customize behavior.
    """

    name = "sweep_nd_base"

    def run(self):
        s = self.settings

        self.display_ready = False

        self.mk_ranges_consistent(s, self.actuator_names)

        collectors = self.collector_list_widget.get_collectors()
        if not collectors:
            self.set_status("set collector repetitions to non-zero", "r")
            print("set collector repetitions to non-zero")
            return

        actuators = self.get_current_actuator_funcs()

        if not actuators:
            self.set_status("no actuators selected", "r")
            print("no actuators selected")
            return

        if "any_measurement" in (col.name for col in collectors):
            self.pre_res_in_new_dir = s["res_in_new_dir"]
            s["res_in_new_dir"] = True

        if s["res_in_new_dir"]:
            self.root = self.app.settings["save_dir"]
            self.app.settings["save_dir"] = mk_new_dir(self.root, self.name)

        if s["scan_mode"] == "Position List":
            arrays = tuple(np.array(self.locator.get_positions_list()).T)
        else:
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
            arrays = tuple(arrays)

        self.scan_data = scan_data = NDScanData(
            base_shape=self.mk_data_shape(*arrays, s["scan_mode"]),
            measurement=self,
        )
        self.data = self.scan_data.data

        for array, name in zip(arrays, self.actuator_names):
            self.scan_data.create_dataset(f"range_{name}", data=array)

        N = np.prod(scan_data.base_shape)
        self.index = 0

        scan_iteration_indices = self.mk_indices_gen(*arrays, s["scan_mode"])

        data_set_names = []
        for positions in self.mk_positions_gen(*arrays, s["scan_mode"]):

            # set positions and wait
            pretty_pos = ", ".join([f"{p:.1f}" for p in positions])
            self.set_status(f"setting {pretty_pos} and waiting", "g")
            self.go_to_positions(positions, actuators)
            time.sleep(s["collection_delay"])
            read_positions = tuple([read() for read, _ in actuators])

            base_indices = next(scan_iteration_indices)

            self.prepare_at_position(positions, base_indices)

            for collector in collectors:
                self.set_status(f"collecting {collector.name} on {pretty_pos}", "g")
                self.prepare_collector_at_position(collector, positions, base_indices)
                for r in range(collector.reps):
                    collector.run(self.index, self)

                    # collect data
                    if self.index == 0 and r == 0:
                        scan_data.init_dsets(collector)
                        data_set_names.extend([q[-1] for q in collector.repeats])
                        self.display_ready = True

                    scan_data.incorporate(collector, *base_indices, r)
                self.release_collector(collector, positions, base_indices)
            if self.index == 0:
                self.settings.get_lq("dataset").change_choice_list(data_set_names)

            scan_data.add_position(positions)
            scan_data.add_read_positions(read_positions)
            scan_data.add_indices(base_indices)
            # manager.flush_h5()

            self.index += 1
            self.set_progress(100 * (self.index + 1) / N)

            if self.interrupt_measurement_called:
                break

        self.post_scan()

        for collector in collectors:
            scan_data.average_repeats(collector)
        scan_data.close_h5()

        if s["res_in_new_dir"]:
            s["res_in_new_dir"] = self.pre_res_in_new_dir
            self.app.settings["save_dir"] = self.root

        self.set_status(f"{self.name} finished", "g")
        print("finished - data collected:")
        for k, v in scan_data.data.items():
            print(k, np.array(v).shape)

    def go_to_positions(self, positions, actuators=None):
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

    def post_scan(self):
        """Optional override.
        Gets called after data collection is finished - before file is closed.
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
        super().__init__(app, name)

    def setup(self):
        self.display_ready = False

        s = self.settings
        s.New(
            name="scan_mode",
            dtype=str,
            choices=self.get_scan_modes(),
            description=self.get_scan_modes_description(),
        )
        s.New(
            name="collection_delay",
            initial=0.01,
            unit="s",
            description="after setting the wheel position, data collection is delayed, allowing the system to reach steady state",
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
        s.New("average_over_repetitions", dtype=bool, initial=True).add_listener(
            self.update_display
        )

        s.New(
            "data representation",
            dtype=str,
            initial="full",
            choices=["full", "averaged_to_1D"],
            description="data representation mode: <p>full: data is raveled to 1D for plotting<p>averaged_to_1D: data is averaged over all but the first dimension, ie. x-axis is first actuator, y-axis is data averaged over all other actuators",
        ).add_listener(self.update_display)

        for i in range(self.n_any_measurements):
            self.collectors.append(
                AnyMeasurementCollector(self, name=f"any_measurement_{i}")
            )

        for i in range(self.n_read_any_settings):
            self.collectors.append(AnySettingCollector(self, name=f"any_setting_{i}"))

        for collector in self.collectors:
            collector.setup_reps_lq(s)

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
        )
        self.data = self.scan_data.data

    def update_widgets(self):

        s = self.settings

        for i in range(self.n_read_any_settings):
            s.get_lq(f"any_setting_{i}").change_choice_list(filtered_lq_paths(self.app))

        self.actuator_defs = add_all_possible_actuators_and_parse_definitions(
            actuator_definitions=self.user_defined_actuators, app=self.app
        )
        self.actuators_funcs = get_actuator_funcs(self.app, self.actuator_defs)

        for i in self.actuator_names:
            s.get_lq(f"actuator_{i}").change_choice_list(self.actuators_funcs.keys())

    def setup_figure(self):
        s = self.settings

        # Top horizontal section
        top_widget = QtWidgets.QWidget()
        top_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed
        )
        top_layout = QtWidgets.QHBoxLayout(top_widget)
        top_layout.setSpacing(4)
        top_layout.setContentsMargins(2, 0, 2, 0)
        self.run_widget = self.mk_run_widget()
        self.run_layout = self.run_widget.layout()
        top_layout.addWidget(self.run_widget)
        top_layout.addWidget(self.mk_scan_settings_widget())
        top_layout.addWidget(self.mk_collect_widget())

        # creation order matters here
        graph_widget = self.mk_graph_widget()
        plot_options_widget = self.mk_plot_options_widget()

        self.ui = QtWidgets.QWidget()
        self.ui.setStyleSheet(
            """
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
        """
        )
        layout = QtWidgets.QVBoxLayout(self.ui)
        layout.setSpacing(4)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(top_widget)

        layout.addWidget(plot_options_widget)
        layout.addWidget(graph_widget)

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

    def update_display(self):

        self.update_status_display()

        if not self.display_ready or not self.settings["dataset"]:
            return

        option = self.settings["dataset"]

        # Set left label if applicable (1D case)
        if hasattr(self, "set_left_label_in_update") and self.set_left_label_in_update:
            self.axes.setLabel("left", option)

        if self.settings["average_over_repetitions"]:
            dset = np.array(self.scan_data.data[option]).mean(axis=self.ndim)
            size = self.scan_data.get_dset_size_per_position_and_repeats(option)
            ddim = self.scan_data.get_dset_dims_per_position_and_repeats(option)
        else:
            dset = self.scan_data.data[option]
            size = self.scan_data.get_dset_size_per_position(option)
            ddim = self.scan_data.get_dset_dims_per_position(option)

        if size == 1 and self.should_show_positions_on_x_axis():
            # special case where we can put position as x-axis
            self.locator.real_position_on_x = True
            self.axes.setLabel("bottom", self.settings["actuator_1"])
            x = np.squeeze(self.scan_data.positions[: self.index])
            if x.ndim > 1:
                x = x[:, 0]
            y = np.squeeze(dset[: self.index])
            self.line.setData(x, y)
        else:
            self.locator.real_position_on_x = False
            self.axes.setLabel("bottom", "arbitrary")
            f = max(1, self.max_npoints_shown // size)
            curr = self.index * size

            if self.index > f:
                self.line.setData(
                    dset.ravel()[curr - f * size : curr],
                )
            else:
                self.line.setData(dset.ravel()[:curr])

    def set_status(self, msg, color="w", force_report=False):
        self.status = {
            "title": msg,
            "color": color,
        }
        if force_report:
            self.update_status_display()

    def update_status_display(self):
        if not self.display_ready:
            return
        self.axes.setTitle(**self.status)

    def mk_run_widget(self):
        run_widget = QtWidgets.QGroupBox("Run Control")
        run_widget.setStyleSheet(
            """
            QPushButton {
                padding: 4px 8px;
                font-weight: 500;
            }
        """
        )

        vlayout = QtWidgets.QVBoxLayout(run_widget)
        vlayout.setSpacing(4)
        vlayout.setContentsMargins(8, 12, 8, 8)

        vlayout.addWidget(self.new_start_stop_button())

        include = ("collection_delay", "res_in_new_dir")
        vlayout.addWidget(self.settings.New_UI(include))

        update_btn = self.operations.new_button("update widgets")
        update_btn.setStyleSheet(
            """
            QPushButton {
                color: #1976d2;
                font-weight: 500;
            }
        """
        )
        vlayout.addWidget(update_btn)

        run_widget.setFlat(False)
        run_widget.setMaximumWidth(220)
        return run_widget

    def mk_scan_settings_widget(self):
        """Create the scan settings widget. Override in child classes for custom layout."""
        mode_selector_mode = self.settings.New_UI(("scan_mode",))

        h_widget = QtWidgets.QWidget()
        h_layout = QtWidgets.QHBoxLayout(h_widget)
        self.list_uis = {}
        for ii, name in enumerate(self.actuator_names):

            r = self.settings.ranges[f"range_{name}"]

            range_ui = r.New_UI()
            list_ui = QtWidgets.QTextEdit()

            range_ui.setMaximumWidth(self.range_n_intervals[ii] * 180)
            list_ui.setMaximumWidth(180)
            list_ui.setText("# Enter one position per line.\n")
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
            layout.addWidget(
                self.settings.get_lq(f"actuator_{name}").new_default_widget()
            )
            layout.addWidget(self.settings.New_UI((f"from_list_{name}",)))
            layout.addWidget(list_ui)
            layout.addWidget(range_ui)
            layout.setSpacing(3)
            h_layout.addLayout(layout)

        place_holder = QtWidgets.QLabel("placeholder")
        place_holder.setVisible(False)
        place_holder.setMaximumHeight(50)

        def toggle_mode_selector(mode):
            enable = mode != "Position List"
            h_widget.setVisible(enable)
            place_holder.setVisible(not enable)
            place_holder.setText(f"Will sweep over position list of this measurement")

        self.settings.get_lq("scan_mode").updated_value[str].connect(
            toggle_mode_selector
        )

        widget = QtWidgets.QGroupBox("Actuators: Define scan positions")
        v_layout = QtWidgets.QVBoxLayout(widget)
        v_layout.setSpacing(4)
        v_layout.setContentsMargins(3, 5, 3, 3)
        v_layout.addWidget(mode_selector_mode)
        v_layout.addWidget(h_widget)
        v_layout.addWidget(place_holder)
        widget.setFlat(False)

        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(widget)
        scroll_area.setMaximumWidth(sum(self.range_n_intervals) * 182 + 20)
        return scroll_area

    def mk_collect_widget(self):
        self.collector_list_widget = InteractiveCollectorList()
        for collector in self.collectors:
            self.collector_list_widget.add_item(collector)

        widget = QtWidgets.QGroupBox("Data Collectors: Set repetitions and order")
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setSpacing(4)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.addWidget(self.collector_list_widget)
        return widget

    def mk_plot_options_widget(self):
        # Plot options group
        plot_gb = QtWidgets.QGroupBox("Plot Options")
        plot_layout = QtWidgets.QHBoxLayout(plot_gb)
        plot_layout.setContentsMargins(6, 6, 6, 6)
        plot_layout.setSpacing(4)
        plot_layout.addWidget(
            self.settings.New_UI(["dataset", "average_over_repetitions"])
        )

        # Container with horizontal layout holding both group boxes
        container = QtWidgets.QWidget()
        h_layout = QtWidgets.QHBoxLayout(container)
        h_layout.setContentsMargins(3, 3, 3, 3)
        h_layout.setSpacing(4)
        h_layout.addWidget(plot_gb)

        self.locator = LocatorX(self, axes=self.axes, position_list=self.position_list)
        h_layout.addWidget(self.locator.mk_widget())

        container.setMaximumHeight(150)
        container.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Minimum,
        )

        return container

    def mk_graph_widget(self):
        graph_widget = pg.GraphicsLayoutWidget()
        graph_widget.setStyleSheet(
            """
            QGraphicsView {
                border: 1px solid #888888;
                border-radius: 3px;
            }
        """
        )

        self.axes = graph_widget.addPlot(title=self.name)
        self.axes.setLogMode(False, False)
        self.axes.showGrid(True, True, alpha=0.4)

        # Improved line with better color
        self.line = self.axes.plot()

        graph_widget.setMinimumHeight(400)
        graph_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
        )

        graph_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred
        )

        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(widget)
        layout.setSpacing(0)

        # Create PositionList and inject it into LocatorX
        self.position_list = PositionList(self)
        self.locator = LocatorX(self, axes=self.axes, position_list=self.position_list)
        layout.addWidget(graph_widget)
        layout.addWidget(self.position_list.mk_widget())
        return widget

    def get_current_actuators_defs(self) -> List[ActuatorInfos]:
        """Returns a list of currently selected actuator definitions."""
        s = self.settings
        return [self.actuator_defs[s[f"actuator_{i}"]] for i in self.actuator_names]

    def get_current_actuator_funcs(self):
        s = self.settings
        return [self.actuators_funcs[s[f"actuator_{i}"]] for i in self.actuator_names]

    def get_current_target_position_funcs(self):
        return (a[-1] for a in self.get_current_actuator_funcs())

    def load_data(self, raw_data):
        self.scan_data.data = {n: v for n, v in raw_data.items() if n.endswith("_raw")}
        self.data = self.scan_data.data
        self.settings.get_lq("dataset").change_choice_list(list(self.data.keys()))
        self.scan_data.positions = raw_data["positions"]
        self.index = len(raw_data["positions"] - 1)
        self.display_ready = True

    # Abstract methods that child classes should implement
    def get_scan_modes(self):
        """Return the SCAN_MODES tuple for this sweep type."""
        raise NotImplementedError("Child class must implement get_scan_modes()")

    def get_scan_modes_description(self):
        """Return the SCAN_MODES_DESCRIPTION for this sweep type."""
        raise NotImplementedError(
            "Child class must implement get_scan_modes_description()"
        )

    def mk_data_shape(self, *args):
        """Return the data shape for this sweep type."""
        raise NotImplementedError("Child class must implement mk_data_shape()")

    def mk_indices_gen(self, *args):
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
