import time
from copy import copy
from typing import Sequence, Tuple, Union, List

import numpy as np
import pyqtgraph as pg
from qtpy import QtWidgets, QtCore

from ScopeFoundry import BaseMicroscopeApp, Measurement
from ScopeFoundry.scanning.actuators import (
    ActuatorDefinitions,
    ActuatorInfos,
    get_actuator_funcs,
    add_all_possible_actuators_and_parse_definitions,
)

from .sweep_4D_modes import (
    SCAN_MODES,
    SCAN_MODES_DESCRIPTION,
    mk_ranges_consistent,
    mk_positions_gen,
    mk_data_shape,
    mk_indices_gen,
)
from .any_measurement_collector import AnyMeasurementCollector
from .any_setting_collector import AnySettingCollector
from .collector import Collector
from .collector_ui_list import InteractiveCollectorList
from .nd_scan_data import NDScanData
from .utils import mk_new_dir, filtered_lq_paths

MAX_N_DPOINTS_SHOWN = 1_000_000


class Sweep4D(Measurement):

    name = "sweep_4d"

    def run(self):
        s = self.settings

        self.display_ready = False

        mk_ranges_consistent(s, self.actuator_names)

        collectors = self.collector_list_widget.get_collectors()
        if not collectors:
            self.set_status("set a collector repetitions to non-zero", "r")
            print("set a collector repetitions to non-zero")
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

        arrays = tuple([r.sweep_array for r in self.scan_ranges])

        self.scan_data = scan_data = NDScanData(
            base_shape=mk_data_shape(*arrays, s["scan_mode"]),
            measurement=self,
        )
        self.data = self.scan_data.data

        for array, name in zip(arrays, self.actuator_names):
            self.scan_data.create_dataset(f"range_{name}", data=array)

        N = np.prod(scan_data.base_shape)
        self.index = 0

        scan_iteration_indices = mk_indices_gen(*arrays, s["scan_mode"])

        data_set_names = []
        for positions in mk_positions_gen(*arrays, s["scan_mode"]):

            # set positions and wait
            pretty_pos = ", ".join([f"{p:.1f}" for p in positions])
            self.set_status(f"setting {pretty_pos} and wait ", "g")
            for (_, write), position in zip(actuators, positions):
                write(position)
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
                s.get_lq("data_set").change_choice_list(data_set_names)

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
        actuator_names: Sequence[str] = "1234",
        range_n_intervals: Sequence[int] = (1, 1, 1, 1),
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
        super().__init__(app, name)

    def setup(self):
        self.display_ready = False

        s = self.settings
        s.New(
            name="scan_mode",
            dtype=str,
            initial="co-move",
            choices=SCAN_MODES,
            description=SCAN_MODES_DESCRIPTION,
        )
        s.New(
            name="collection_delay",
            initial=0.01,
            unit="s",
            description="after setting the wheel position, data collection is delayed allowing system to reach steady state",
        )

        s.New(
            name="res_in_new_dir",
            dtype=bool,
            initial=False,
            description="dumps data in a new sub folder. Intended for <i>any_measurement</i> where a file is stored per acquisition",
        )
        s.New(
            name="data_set",
            dtype=str,
            initial="powers",
            choices=("",),
            description="plot option",
        ).add_listener(self.update_display)
        s.New("average_over_repetitions", dtype=bool, initial=True).add_listener(
            self.update_display
        )
        s.New(
            name="locator",
            dtype=bool,
            initial=False,
            description="show locator line",
        ).add_listener(self.on_locator_changed)

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
            description="click after connecting to a hardware to extend actuator options",
            icon_path=self.app.qtapp.style().standardIcon(
                QtWidgets.QStyle.SP_BrowserReload
            ),
        )

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
        h_widget = QtWidgets.QWidget()
        h_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed
        )
        h_layout = QtWidgets.QHBoxLayout(h_widget)
        h_layout.setSpacing(4)
        h_layout.setContentsMargins(2, 0, 2, 0)
        h_layout.addWidget(self.mk_run_widget())
        h_layout.addWidget(self.mk_scan_settings_widget())
        h_layout.addWidget(self.mk_collect_widget())

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
        layout.addWidget(h_widget)
        layout.addWidget(self.mk_plot_options_widget())
        layout.addWidget(self.mk_graph_widget())

        self.display_ready = False
        self.set_status("starting power scan", "y")
        s.get_lq("data_set").add_listener(self.update_display)
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

        if not self.display_ready or not self.settings["data_set"]:
            return

        option = self.settings["data_set"]
        if self.settings["average_over_repetitions"]:
            dset = np.array(self.scan_data.data[option]).mean(axis=self.ndim)
            size = self.scan_data.get_dset_size_per_position_and_repeats(option)
            ddim = self.scan_data.get_dset_dims_per_position_and_repeats(option)
        else:
            dset = self.scan_data.data[option]
            size = self.scan_data.get_dset_size_per_position(option)
            ddim = self.scan_data.get_dset_dims_per_position(option)

        if size == 1 and self.settings["scan_mode"] == "co-move":
            # special case where we can put position as x-axis
            self._positions_on_x_axis = True
            x = np.squeeze([p[0] for p in self.scan_data.positions[: self.index]])
            y = np.squeeze(dset[: self.index])
            self.line.setData(x, y)
        else:
            self._positions_on_x_axis = False
            f = max(1, MAX_N_DPOINTS_SHOWN // size)
            curr = self.index * size

            # flatten the scan dimensions
            dset = dset[tuple(zip(*self.scan_data.indices))]

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
        mode_selector_mode = self.settings.New_UI(("scan_mode",))
        h_layout = QtWidgets.QHBoxLayout()
        h_layout.setSpacing(0)
        h_layout.setContentsMargins(0, 0, 0, 0)
        for i in self.actuator_names:
            l = QtWidgets.QVBoxLayout()
            l.setSpacing(0)
            l.setContentsMargins(0, 0, 0, 0)
            l.addWidget(self.settings.get_lq(f"actuator_{i}").new_default_widget())
            r = self.settings.ranges[f"range_{i}"]
            w = r.New_UI()
            l.addWidget(w)
            h_layout.addLayout(l)

        widget = QtWidgets.QGroupBox("Actuators")
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(mode_selector_mode)
        layout.addLayout(h_layout)
        widget.setMaximumWidth(500)
        widget.setFlat(False)
        return widget

    def mk_collect_widget(self):
        self.collector_list_widget = InteractiveCollectorList()
        for collector in self.collectors:
            self.collector_list_widget.add_item(collector)

        widget = QtWidgets.QGroupBox("Data Collectors: set repetitions and order")
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
            self.settings.New_UI(["data_set", "average_over_repetitions"])
        )

        # Locator group
        locator_gb = QtWidgets.QGroupBox("Locator")
        locator_layout = QtWidgets.QVBoxLayout(locator_gb)
        locator_layout.setContentsMargins(6, 6, 6, 6)
        locator_layout.setSpacing(4)

        self.locator_btn = QtWidgets.QPushButton("")
        self.locator_btn.clicked.connect(self.on_push_locator_btn)
        self.locator_btn.setVisible(self.settings["locator"])

        cb = self.settings.New_UI(["locator"])

        locator_layout.addWidget(cb)
        locator_layout.addWidget(self.locator_btn)
        locator_gb.setMaximumWidth(400)

        # Container with horizontal layout holding both group boxes
        container = QtWidgets.QWidget()
        h_layout = QtWidgets.QHBoxLayout(container)
        h_layout.setContentsMargins(3, 3, 3, 3)
        h_layout.setSpacing(4)
        h_layout.addWidget(plot_gb)
        h_layout.addWidget(locator_gb)

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

        # Enhanced infinite line
        self.infinite_line = pg.InfiniteLine(
            angle=90,
            label="locator",
            movable=True,
            pen=pg.mkPen(color="#FF5722", width=2, style=QtCore.Qt.DashLine),
            labelOpts={
                "color": "#FFFFFF",
                "movable": True,
                "fill": "#FF56221E",  # faint semi-transparent background
            },
        )
        self.infinite_line.sigPositionChanged.connect(self.on_infinite_line_moved)
        self.infinite_line.setVisible(self.settings["locator"])
        self.axes.addItem(self.infinite_line)

        return graph_widget

    def get_locator_position(self, line=None):
        if not hasattr(self, "scan_data"):
            return
        if not self.scan_data.data:
            return
        if line is None:
            line = self.infinite_line

        if self._positions_on_x_axis:
            positions = np.array(self.scan_data.positions)[:, 0]
            index = np.argmin(np.abs(positions - line.value()))
            return self.scan_data.positions[index]

        if self.settings["average_over_repetitions"]:
            size = self.scan_data.get_dset_size_per_position_and_repeats(
                self.settings["data_set"]
            )
        else:
            size = self.scan_data.get_dset_size_per_position(self.settings["data_set"])

        index = int(line.value() // size)

        if self.index * size >= MAX_N_DPOINTS_SHOWN:
            smallest_index_shown = self.index - (MAX_N_DPOINTS_SHOWN // size)
            index += smallest_index_shown

        if index < 0 or index >= len(self.scan_data.positions):
            return
        return self.scan_data.positions[index]

    def on_infinite_line_moved(self, line=None):
        positions = self.get_locator_position(line)

        if positions is None:
            self.locator_btn.setEnabled(False)
            self.locator_btn.setText("Invalid Position: Drag locator within data range")
            self.locator_btn.setStyleSheet(
                """
                QPushButton {
                    color: #f44336;
                    font-weight: 600;
                }
            """
            )
            return

        actuator_names = [i[0] for i in self.get_current_actuators_defs()]
        ext_pretty_pos = "<br>".join(
            [
                f"<span style='font-weight: 600;'>{name}:</span> {p:.2f}"
                for name, p in zip(actuator_names, positions)
            ]
        )
        self.infinite_line.label.setHtml(
            f"<div style='padding: 3px;'>"
            f"<span style='font-weight: 700; font-size: 13px;'>Actuator Positions</span><br>"
            f"<span style='font-size: 10px;'>{ext_pretty_pos}</span></div>"
        )
        self.infinite_line.label.setMovable(True)
        self.locator_btn.setEnabled(True)

        pretty_pos = ", ".join([f"{p:.2f}" for p in positions])
        self.locator_btn.setText(f"Set Actuator Position ({pretty_pos})")
        self.locator_btn.setStyleSheet(
            """
            QPushButton {
                color: #4caf50;
                font-weight: 600;
            }
            QPushButton:hover {
                color: #388e3c;
            }
        """
        )

    def on_push_locator_btn(self):
        positions = self.get_locator_position()
        funcs = self.get_current_target_position_funcs()
        for p, f in zip(positions, funcs):
            f(p)
        self.locator_btn.setStyleSheet("color: blue; font-weight: normal;")

    def on_locator_changed(self):
        if not hasattr(self, "infinite_line"):
            return
        enabled = self.settings["locator"]
        self.locator_btn.setVisible(enabled)
        self.infinite_line.setVisible(enabled)

    def get_current_actuators_defs(self) -> List[ActuatorInfos]:
        """Returns a list of currently selected actuator definitions."""
        s = self.settings
        return [self.actuator_defs[s[f"actuator_{i}"]] for i in self.actuator_names]

    def get_current_actuator_funcs(self):
        s = self.settings
        return [self.actuators_funcs[s[f"actuator_{i}"]] for i in self.actuator_names]

    def get_current_target_position_funcs(self):
        return (a[-1] for a in self.get_current_actuator_funcs())
