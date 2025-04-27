from typing import List, Tuple
import time

import numpy as np
import pyqtgraph as pg
from qtpy import QtWidgets

from ScopeFoundry import h5_io
from ScopeFoundry.measurement import Measurement
from ScopeFoundry.scanning.actuators import mk_actuator_func

from .collector import Collector
from .nd_scan_data import NDScanData


def mk_positions_gen(ar_1, mode="nested"):
    if mode == "nested":
        for k, v in enumerate(ar_1):
            yield v


def mk_data_shape(ar_1, reps, mode="nested"):
    if mode == "nested":
        return len(ar_1), reps


def mk_indices_gen(ar_1, reps, mode="nested"):
    if mode == "nested":
        for k, v in enumerate(ar_1):
            for rep in range(reps):
                yield k, rep


SCAN_MODES = ("nested",)


class Sweep1D(Measurement):

    name = "sweep_1d"

    def __init__(
        self,
        app,
        name=None,
        collectors: List[Collector] = None,
        actuators: List[Tuple[str, str]] = None,
    ):
        self.collectors = collectors
        self.user_defined = actuators
        super().__init__(app, name)

    def setup(self):
        s = self.settings
        s.New(
            "repetitions",
            int,
            initial=1,
            description="repetitions at each position",
        )
        s.New(
            "collection_delay",
            initial=0.01,
            unit="s",
            description="after setting the wheel position, data collection is delayed allowing system to reach steady state",
        )
        s.New(
            "plot_option",
            dtype=str,
            initial="powers",
            choices=("",),
            description="plot option",
        )
        s.New(
            "res_in_new_dir",
            bool,
            initial=False,
            description="dumps data in a new sub folder. Intended for <i>any_measurement</i> where a file is stored per acquisition",
        )

        for key in self.collectors:
            self.settings.New(f"collect_{key.name}", bool, initial=False)

        self.range_1 = self.settings.New_Range("range_1", initials=(1, 2, 2))

        self.settings.New("actuator_1", dtype=str, choices=["none"])

        self.add_operation("update_actuator_choices", self.update_actuator_choices)

    def update_actuator_choices(self):

        self.actuators_funcs = {}

        if self.user_defined is not None:
            for write_path, read_path in self.user_defined:
                self.actuators_funcs[write_path] = mk_actuator_func(
                    self.app, write_path, read_path
                )

        for write_path in self.app.get_setting_paths(filter_has_hardware_write=True):
            self.actuators_funcs[write_path] = mk_actuator_func(
                self.app, write_path, None
            )

        choices = list(self.actuators_funcs.keys())
        self.settings.get_lq("actuator_1").change_choice_list(choices)

    def pre_run(self):
        self.axes.clear()

    def run(self):
        s = self.settings
        self.display_ready = False

        collectors: List[Collector] = self.collectors
        actuator = self.actuators_funcs[s[f"actuator_1"]]

        ar_1 = self.range_1.array

        h5_file = h5_io.h5_base_file(app=self.app, measurement=self)
        self.data_manager = manager = NDScanData(
            collectors,
            base_shape=mk_data_shape(ar_1, s["repetitions"]),
            h5_file=h5_file,
            h5_group=h5_io.h5_create_measurement_group(self, h5_file),
        )

        N = np.prod(manager.base_shape)
        index = 0

        indices_gen = mk_indices_gen(ar_1, s["repetitions"])

        for positions in mk_positions_gen(ar_1):

            # set positions and wait
            (read, write), pos = (actuator, positions)
            write(pos)
            time.sleep(s["collection_delay"])

            # acquire data for each repetition
            for _ in range(s["repetitions"]):
                for collector in collectors:
                    collector.prepare()
                    collector.run(index, self)

                # collect data
                data_indices = next(indices_gen)
                if index == 0:
                    manager.init_dsets()
                    s.get_lq("plot_option").change_choice_list(manager.data.keys())
                    self.display_ready = True

                manager.incorporate(*data_indices)
                index += 1

            manager.add_position(positions)
            manager.add_indices(data_indices[:-1])  # exclude the repetition index
            self.set_progress(100 * (index + 1) / N)
            manager.flush_h5()

        print("finished - data collected:")
        for k, v in manager.data.items():
            print(k, np.array(v).shape)

        manager.flush_h5()
        manager.close_h5()

    def setup_figure(self):
        self.update_actuator_choices()

        s = self.settings

        h_layout = QtWidgets.QHBoxLayout()
        h_layout.addWidget(self.mk_run_widget(s))
        h_layout.addWidget(self.mk_collect_widget())
        v_layout = QtWidgets.QVBoxLayout()
        v_layout.addLayout(h_layout)
        v_layout.addWidget(self.mk_scan_settings_widget())

        graph_widget = pg.GraphicsLayoutWidget()
        self.axes = graph_widget.addPlot(title=self.name)
        self.axes.setLogMode(False, False)
        self.axes.showGrid(True, True)

        self.ui = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(self.ui)
        layout.addLayout(v_layout)
        layout.addWidget(graph_widget)

        self.display_ready = False
        self.set_status("starting power scan", "y")
        # self.update_choices()
        s.get_lq("plot_option").add_listener(self.update_display)
        self.set_status("welc\u1e4fme", (253, 188, 24), True)

    def update_display(self):

        if not self.display_ready:
            return

        option = self.settings["plot_option"]
        data = np.array(self.data_manager.data[option])

        to_plot = data.sum(
            axis=(
                0,
                1,
            )
        ).T

        self.axes.plot(to_plot)

    def set_status(self, msg, color="w", force_report=False):
        self.status = {
            "title": msg,
            "color": color,
        }
        if force_report:
            self.update_status_display()

    def update_status_display(self):
        self.axes.setTitle(**self.status)

    def mk_run_widget(self, s):
        run_widget = QtWidgets.QGroupBox("run")
        vlayout = QtWidgets.QVBoxLayout(run_widget)
        vlayout.addWidget(s.get_lq("activation").new_pushButton())
        include = (
            "plot_option",
            # "use_shutter",
            # "power_measurement",
            # "powermeter",
            "collection_delay",
            "res_in_new_dir",
        )
        vlayout.addWidget(s.New_UI(include))
        run_widget.setFlat(False)
        return run_widget

    def mk_scan_settings_widget(self):
        h_layout = QtWidgets.QHBoxLayout()
        w3 = self.settings.New_UI(("repetitions",))
        w3.layout().setSpacing(1)
        w3.layout().addWidget(self.operations.new_button("update_actuator_choices"))
        h_layout.addWidget(w3)
        for r, i in zip((self.range_1,), "1"):
            w1 = r.New_UI()
            w1.layout().insertRow(0, QtWidgets.QLabel(f"actuator_{i}"))
            w1.layout().insertRow(
                1, self.settings.get_lq(f"actuator_{i}").new_default_widget()
            )
            w1.layout().setSpacing(1)
            h_layout.addWidget(w1)

        widget = QtWidgets.QGroupBox("scan settings")
        widget.setLayout(h_layout)
        widget.setFlat(False)
        return widget

    def mk_collect_widget(self):
        s = self.settings
        collect_widget = QtWidgets.QGroupBox(title="collect")
        layout = QtWidgets.QGridLayout(collect_widget)
        layout.addWidget(QtWidgets.QLabel("integration_time"), 0, 1)
        for row, collector in enumerate(self.collectors):
            cb = s.get_lq(f"collect_{collector.name}").new_default_widget()
            cb.setText(collector.name)
            cb.setStyleSheet(f"background-color:rgba{collector.color + (0.3,) };")
            if collector.name == "any_measurement":
                w = s.get_lq("available_measures").new_default_widget()
            else:
                print(collector.int_lq)
                w = self.app.get_lq(collector.int_lq).new_default_widget()
            layout.addWidget(cb, row + 1, 0)
            layout.addWidget(w, row + 1, 1)
        collect_widget.setFlat(False)
        return collect_widget
