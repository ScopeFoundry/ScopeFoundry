import time
from copy import copy
from typing import Sequence, Tuple, Union

import numpy as np
import pyqtgraph as pg
from qtpy import QtWidgets

from ScopeFoundry import BaseMicroscopeApp, Measurement
from ScopeFoundry.scanning.actuators import (
    ActuatorDefinitions,
    get_actuator_funcs,
    add_all_possible_actuators_and_parse_definitions,
)

from .sweep_1D_modes import (
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
from .utils import filtered_lq_paths, mk_new_dir


class Sweep1D(Measurement):

    name = "sweep_1d"

    def run(self):
        s = self.settings

        s.get_lq("plot_option").change_choice_list([])
        self.display_ready = False

        mk_ranges_consistent(s, self.actuator_names)

        collectors = self.collector_list_widget.get_collectors()
        print(collectors)
        if not collectors:
            self.set_status("set a collector repetitions to non-zero", "r")
            print("set a collector repetitions to non-zero")
            return

        actuators = [
            self.actuators_funcs[s[f"actuator_{i}"]] for i in self.actuator_names
        ]

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

        for array, name in zip(arrays, self.actuator_names):
            self.scan_data.create_dataset(f"range_{name}", data=array)

        N = np.prod(scan_data.base_shape)
        self.index = 0

        scan_iteration_indices = mk_indices_gen(*arrays, s["scan_mode"])

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
                        s.get_lq("plot_option").add_choices(list(scan_data.data.keys()))
                        self.display_ready = True

                    scan_data.incorporate(collector, *base_indices, r)
                self.release_collector(collector, positions, base_indices)

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

        Intended for setting up detectors.
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
    ):
        self.collectors = [copy(x) for x in collectors]
        self.user_defined_actuators = list(actuators)
        self.actuator_names = actuator_names
        self.range_n_intervals = range_n_intervals
        self.ndim = len(actuator_names)
        super().__init__(app, name)

    def setup(self):
        s = self.settings
        s.New(
            name="scan_mode",
            dtype=str,
            initial="NA",
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
            name="plot_option",
            dtype=str,
            initial="powers",
            choices=("",),
            description="plot option",
        )

        s.New("any_measurement", str, choices=[""])
        s.New("any_setting", str, choices=[""])

        self.any_measurement_collector = AnyMeasurementCollector(
            app=self.app,
            measure_lq=self.settings.get_lq("any_measurement"),
            acquisition_duration_path=self.settings.get_lq("any_measurement").path,
        )
        self.collectors.append(self.any_measurement_collector)
        self.any_setting_collector = AnySettingCollector(
            app=self.app,
            setting_lq=self.settings.get_lq("any_setting"),
            acquisition_duration_path=self.settings.get_lq("any_setting").path,
        )
        self.collectors.append(self.any_setting_collector)

        for collector in self.collectors:
            s.New(
                name=f"{collector.name}_repetitions",
                dtype=int,
                initial=0,
                vmin=0,
                description="number of times data gets collected at each position",
            )

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

        s.get_lq("any_setting").change_choice_list(filtered_lq_paths(self.app))

        defs = add_all_possible_actuators_and_parse_definitions(
            actuator_definitions=self.user_defined_actuators,
            app=self.app,
        )

        self.actuators_funcs = get_actuator_funcs(self.app, defs)

        for i in self.actuator_names:
            s.get_lq(f"actuator_{i}").change_choice_list(self.actuators_funcs.keys())

    def setup_figure(self):

        s = self.settings

        h_widget = QtWidgets.QWidget()
        h_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed
        )
        h_layout = QtWidgets.QHBoxLayout(h_widget)
        h_layout.addWidget(self.mk_run_widget())
        h_layout.addWidget(self.mk_scan_settings_widget())
        h_layout.addWidget(self.mk_collect_widget())

        self.ui = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(self.ui)
        layout.addWidget(h_widget)
        layout.addWidget(s.get_lq("plot_option").new_default_widget())
        layout.addWidget(self.mk_graph_widget())

        self.display_ready = False
        self.set_status("starting power scan", "y")
        s.get_lq("plot_option").add_listener(self.update_display)
        s.get_lq("any_measurement").change_choice_list(self.app.measurements.keys())
        s.get_lq("any_setting").change_choice_list(self.app.get_setting_paths(True))
        self.set_status("welc\u1e4fme", (253, 188, 24), True)

        self.update_widgets()

    def update_display(self):

        self.update_status_display()

        if not self.display_ready or not self.settings["plot_option"]:
            return

        dset = np.array(self.scan_data.data[self.settings["plot_option"]]).mean(
            axis=self.ndim
        )
        dlen = np.prod(dset.shape[self.ndim :])  # len of data

        ddim = len(dset.shape[self.ndim :])

        curr = self.index * dlen

        if ddim >= 1:
            f = max(1, 100_000 // dlen)

            if self.index > f:
                self.line.setData(
                    # np.arange(curr - f * plen, curr) / plen,
                    dset.ravel()[curr - f * dlen : curr],
                )
            else:
                self.line.setData(
                    # np.arange(curr) / plen,
                    dset.ravel()[:curr]
                )
        else:
            self.line.setData(dset)

        # elif ddim in (2, 3):
        #     self.img_item.setVisible(True)
        #     images = dset.reshape((-1,)+ dset.shape[4:])
        #     self.img_item.setImage(images[curr], autoLevels=True)

    def set_status(self, msg, color="w", force_report=False):
        self.status = {
            "title": msg,
            "color": color,
        }
        if force_report:
            self.update_status_display()

    def update_status_display(self):
        self.axes.setTitle(**self.status)

    def mk_run_widget(self):
        run_widget = QtWidgets.QGroupBox("run")
        vlayout = QtWidgets.QVBoxLayout(run_widget)
        vlayout.addWidget(self.new_start_stop_button())
        include = (
            # "plot_option",
            "collection_delay",
            "res_in_new_dir",
        )
        vlayout.addWidget(self.settings.New_UI(include))
        vlayout.addWidget(self.operations.new_button("update widgets"))
        run_widget.setFlat(False)
        return run_widget

    def mk_scan_settings_widget(self):

        name = self.actuator_names[0]
        r = self.settings.ranges[f"range_{name}"]

        selector_w = self.settings.get_lq(f"actuator_{name}").new_default_widget()
        range_w = r.New_UI()

        w = widget = QtWidgets.QGroupBox("scan settings")
        layout = QtWidgets.QVBoxLayout(w)
        layout.addWidget(selector_w)
        layout.addWidget(range_w)
        layout.setSpacing(1)
        return widget

    def mk_collect_widget(self):

        widget = QtWidgets.QGroupBox(
            title="choose the number of repetion for each detectors - drag and drop to change order"
        )
        layout = QtWidgets.QVBoxLayout(widget)

        self.collector_list_widget = InteractiveCollectorList()
        for collector in self.collectors:
            collector.reps_lq_path = self.settings.get_lq(
                f"{collector.name}_repetitions"
            ).path
            self.collector_list_widget.add_item(collector)

        layout.addWidget(self.collector_list_widget)
        return widget

    def mk_graph_widget(self):
        graph_widget = pg.GraphicsLayoutWidget()
        self.axes = graph_widget.addPlot(title=self.name)
        self.axes.setLogMode(False, False)
        self.axes.showGrid(True, True)
        self.line = self.axes.plot()
        # self.img_axes = graph_widget.addPlot(title=self.name)
        # self.img_item = pg.ImageItem()
        # self.img_item.setVisible(False)
        # self.img_axes.addItem(self.img_item)
        return graph_widget
