import itertools
import time
from abc import ABC
from copy import copy
from typing import Sequence, Tuple, Union, List

from matplotlib import image
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
            self.set_status("set collector repetitions to non-zero", "r", True)
            # print("set collector repetitions to non-zero")
            return

        actuators = self.get_current_actuator_funcs()

        if not actuators:
            self.set_status("no actuators selected", "r")
            # print("no actuators selected")
            return

        if "any_measurement" in (col.name for col in collectors):
            self.pre_res_in_new_dir = s["res_in_new_dir"]
            s["res_in_new_dir"] = True

        if s["res_in_new_dir"]:
            self.root = self.app.settings["save_dir"]
            self.app.settings["save_dir"] = mk_new_dir(self.root, self.name)

        if s["scan_mode"] == "RETAKE":
            # Retake data at specified positions
            target_positions = self.position_list.get_items()
            indices = []  # index
            base_indices_gen = []
            positions_gen = []
            for target_position in target_positions:
                index = find_nearest_position_index(
                    self.scan_data.positions, target_position
                )
                indices.append(index)
                base_indices_gen.append(self.scan_data.indices[index])
                positions_gen.append(self.scan_data.positions[index])

            # Will reuse existing scan_data object in memory
            scan_data = self.scan_data
            scan_data.open_new_h5_file()
            scan_data.recycle()

            # add a dummy value - will be only used to show progress and data
            indices.append(np.prod(scan_data.base_shape))
            progress_index_gen = (i + 1 for i in indices)
            N = len(indices)
            self.set_status(f"Retaking data at index {self.progress_index}", "y")
            self.display_ready = True
        else:
            if s["scan_mode"] == "Position List":
                arrays = tuple(np.array(self.position_list.get_items()).T)
            else:
                arrays = []
                for name in self.actuator_names:
                    if self.settings[f"from_list_{name}"]:
                        pos_list = self.list_uis[name].toPlainText().splitlines()
                        pos_list = [
                            s.split("#")[0] for s in pos_list
                        ]  # remove comments
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

            base_indices_gen = self.mk_indices_gen(*arrays, s["scan_mode"])
            positions_gen = self.mk_positions_gen(*arrays, s["scan_mode"])
            progress_index_gen = itertools.count(0, 1)  # just one by one
            N = np.prod(scan_data.base_shape)
            self.display_ready = False

        data_set_names = []
        self.progress_index = next(progress_index_gen)
        for positions, base_indices in zip(positions_gen, base_indices_gen):

            # set positions and wait
            pretty_pos = ", ".join([f"{p:.1f}" for p in positions])
            self.set_status(f"setting {pretty_pos} and waiting", "g")
            self.go_to_positions(positions, actuators)
            time.sleep(s["collection_delay"])
            read_positions = tuple([read() for read, _ in actuators])

            # base_indices = next(scan_iteration_indices)

            self.prepare_at_position(positions, base_indices)

            for collector in collectors:
                self.set_status(f"collecting {collector.name} on {pretty_pos}", "g")
                self.prepare_collector_at_position(collector, positions, base_indices)
                for r in range(collector.reps):
                    collector.run(self.progress_index, self)

                    # collect data
                    if not scan_data.dsets_initialized:
                        scan_data.init_dsets(collector)
                        data_set_names.extend([q[-1] for q in collector.repeats])
                        self.display_ready = True
                    scan_data.incorporate(collector, *base_indices, r)

                self.release_collector(collector, positions, base_indices)
            if self.progress_index == 0:
                self.settings.get_lq("dataset").change_choice_list(data_set_names)

            scan_data.add_position(positions)
            scan_data.add_read_positions(read_positions)
            scan_data.add_indices(base_indices)
            # manager.flush_h5()

            self.progress_index = next(progress_index_gen)
            self.set_progress(100 * (self.progress_index + 1) / N)

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
            initial="nested",
            choices=list(self.get_scan_modes()) + ["RETAKE"],
            description=self.get_scan_modes_description()
            + "<p><i>RETAKE:</i>: Allows to retake (fix) inidiviual data points specified in Position List. Makes a new datafile with data in memory with retaken data points updated.</p>",
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
            name="position_representation",
            dtype=str,
            initial="flat",
            choices=["flat", "map_vertical"],
            description="<p>flat: flattened data per sweep point flattend and aranged in order measured<p>map_vertical: data at positions is along vertical direction of a map",
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

        self.position_list = PositionList(self)

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

    def update_display(self):

        self.update_status_display()

        if not self.display_ready or not self.settings["dataset"]:
            return

        option = self.settings["dataset"]

        if self.settings["average_over_repetitions"]:
            dset = np.array(self.scan_data.data[option]).mean(axis=self.ndim)
            size = self.scan_data.get_dset_size_per_position_and_repeats(option)
        else:
            dset = self.scan_data.data[option]
            size = self.scan_data.get_dset_size_per_position(option)

        if size == 1:
            self.settings["position_representation"] = "flat"

        # inorder of collection and flattened to positions x size
        img = dset[tuple(zip(*self.scan_data.indices))].reshape((-1, size))

        i_span_max = self.max_npoints_shown // size
        i_max = self.progress_index
        i_min = max(i_max - i_span_max, 0)

        img = img[i_min:i_max, :]

        self.locator.size = size
        self.locator.i_min = i_min
        # self.locator.i_max = i_max

        self.locator.real_position_on_x = (
            (size == 1 and self.should_show_positions_on_x_axis())
            or self.settings["position_representation"] == "map_vertical"
            and self.should_show_positions_on_x_axis()
        )

        if self.locator.real_position_on_x:
            self.axes.setLabel("bottom", self.settings["actuator_1"])

            x = np.squeeze(self.scan_data.positions[i_min:i_max])
            if x.ndim > 1:
                x = x[:, 0]

            if self.settings["position_representation"] == "flat":
                y = np.squeeze(img)[i_min:i_max]
                self.line.setData(x, y)
            elif self.settings["position_representation"] == "map_vertical":
                dx = float(np.diff(x, prepend=-0.5)[-1])
                xmin = min(x) - dx / 2
                xmax = max(x) + dx / 2
                rect = pg.QtCore.QRectF(xmin, 0, xmax - xmin, size)
                self.img_item.setImage(img, rect=rect)

        else:
            self.axes.setLabel("bottom", "arbitrary")

            if self.settings["position_representation"] == "flat":
                y = np.squeeze(img).ravel()
                # x = np.arange(len(y))
                self.line.setData(y)
            elif self.settings["position_representation"] == "map_vertical":
                rect = pg.QtCore.QRectF(-0.5, 0, i_max + 0.5, size)
                self.img_item.setImage(img, rect=rect)

        show_image = self.settings["position_representation"] == "map_vertical"
        self.img_item.setVisible(show_image)
        self.line.setVisible(not show_image)

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
            layout.addWidget(
                self.settings.get_lq(f"actuator_{name}").new_default_widget()
            )
            layout.addWidget(self.settings.New_UI((f"from_list_{name}",)))
            layout.addWidget(list_ui)
            layout.addWidget(range_ui)
            layout.setSpacing(3)
            h_layout.addLayout(layout)

        self.actuator_placeholder = QtWidgets.QTextEdit("placeholder")
        self.actuator_placeholder.setReadOnly(True)
        self.actuator_placeholder.setVisible(False)

        def toggle_mode_selector(mode):
            show_place_holder = mode in ("RETAKE", "Position List")
            h_widget.setHidden(show_place_holder)
            self.actuator_placeholder.setHidden(not show_place_holder)
            if mode == "Position List":
                self.actuator_placeholder.setHtml(
                    f"<p>Sweeps over positions defined in the Position List.</p><p>Each position should specify coordinates for all actuators in order.</p><p><b>Note:</b> Add positions using the Position List panel on the right.</p>"
                )
            elif mode == "RETAKE":
                self.actuator_placeholder.setHtml(
                    f"<p>Retakes data at positions defined in Position List.</p><p>Uses existing scan data in memory and creates a new file with updated measurements at specified positions.</p><p><b>Note:</b> Position List should contain positions from the current scan that need to be re-measured.</p>"
                )

        self.settings.get_lq("scan_mode").updated_value[str].connect(
            toggle_mode_selector
        )

        widget = QtWidgets.QGroupBox("Actuators: Define scan positions")
        v_layout = QtWidgets.QVBoxLayout(widget)
        v_layout.setSpacing(4)
        v_layout.setContentsMargins(3, 5, 3, 3)
        v_layout.addWidget(mode_selector_mode)
        v_layout.addWidget(h_widget)
        v_layout.addWidget(self.actuator_placeholder)
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
            self.settings.New_UI(
                ["dataset", "position_representation", "average_over_repetitions"]
            )
        )

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
                f"Does not have a locator! Recommend to add one at self.mk_graph_widget method or self.setup_figure\n self.locator = LocatorX(self, self.position_list) or (self.locator = LocatorRoi for 2D data)\n self.locator.set_axes(self.axes) \n Trying to add LocatorX..."
            )
            try:
                self.locator = LocatorX(self, self.position_list)
                self.locator.set_axes(self.axes)
                h_layout.addWidget(self.locator.mk_widget())
                self.log.warning(
                    f"added LocatorX successfully. Recommend to add it properly in the child class code."
                )
            except Exception as e:
                self.log.warning(f"Could not make locator: {e}")

        # container.setMaximumHeight(150)
        container.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Maximum,
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

    def wrap_with_position_list_widget(self, graph_widget):
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
        self.progress_index = len(raw_data["positions"] - 1)
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


def find_nearest_position_index(positions, target_positions):
    positions_array = np.array(positions)
    target_positions = np.array(target_positions)
    distances = np.linalg.norm(positions_array - target_positions, ord=2, axis=1)
    return int(np.argmin(distances))
