"""
Created on Jan 23, 2023

@author: Benedikt Ursprung
"""
import time

import numpy
import pyqtgraph as pg
from qtpy import QtWidgets

from ScopeFoundry import Measurement, h5_io

INDEF = "indefinite"
TIMEOUT = "timeout"
ETOL = "error_tol"
ETOL_W_TIMEOUT = f"{ETOL}_with_{TIMEOUT}"


class PIDFeedbackControl(Measurement):
    name = "pid_feedback_control"

    def setup(self):
        s = self.settings
        s.New("Kp", float, initial=1)
        s.New("Ki", float, initial=0)
        s.New("Kd", float, initial=0)
        s.New("setpoint", float, initial=1.0, si=True)
        s.New(
            "sensor",
            str,
            initial="-",
            choices=("-",),
            description="choose a setting that supports read_from_hardware.",
        )
        s.New(
            "plant_input",
            str,
            initial="-",
            choices=("-",),
            description="choose a setting that has a hardware_set_func",
        )
        s.New(
            "timeout",
            float,
            vmin=0.0,
            initial=10.0,
            unit="s",
            description=f"used to define <b>terminate</b> condition <i>{TIMEOUT}</i> and <i>{ETOL_W_TIMEOUT}</i>, ignored otherwise",
        )
        s.New("error", float, initial=1_000, unit="%", ro=True)
        s.New(
            "error_tol",
            float,
            vmin=0.0,
            initial=1.0,
            unit="%",
            description=f"used to define <b>terminate</b> condition <i>{ETOL}</i> and <i>{ETOL_W_TIMEOUT}</i>, ignored otherwise",
        )
        s.New(
            "terminate",
            str,
            initial=ETOL_W_TIMEOUT,
            choices=(TIMEOUT, INDEF, ETOL_W_TIMEOUT, ETOL),
            description=f"condition for {self.name} to end.",
        )
        s.New(
            "min_plant_input",
            float,
            initial=-1e-99,
            si=True,
            description=f"minimum plant input value.",
        )
        s.New(
            "max_plant_input",
            float,
            initial=1e-99,
            si=True,
            description=f"maximum plant input value.",
        )
        s.New("save_h5", bool, initial=False)
        self.data = mk_data_dict(600, 1.0)

    def setup_figure(self):
        s = self.settings

        ctr_layout = QtWidgets.QHBoxLayout()
        ctr_layout.addWidget(s.New_UI(("setpoint", "plant_input", "sensor")))
        ctr_layout.addWidget(s.New_UI(("min_plant_input", "max_plant_input")))
        ctr_layout.addWidget(s.New_UI(("Kp", "Ki", "Kd")))
        ctr_layout.addWidget(s.New_UI(("terminate", "timeout", "error_tol")))

        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addWidget(self.new_start_stop_button())
        op_button = QtWidgets.QPushButton("unfilter options")
        op_button.clicked.connect(self.update_choices)
        btn_layout.addWidget(op_button)
        op_button = QtWidgets.QPushButton("filter options to available")
        op_button.setToolTip("only settings that are connected to hardware")
        op_button.clicked.connect(self.update_choices_filtered)
        btn_layout.addWidget(op_button)

        graph_widget = pg.GraphicsLayoutWidget(border=(0, 0, 0))
        axes = graph_widget.addPlot(title=self.name)
        t = self.data["lab_times"]
        self.sensor_values_plotline = axes.plot(t, self.data["sensor_values"], pen="w")
        self.setpoints_plotline = axes.plot(t, self.data["setpoints"], pen="y")

        self.ui = QtWidgets.QWidget()
        self.layout = QtWidgets.QVBoxLayout(self.ui)
        self.layout.addLayout(ctr_layout)
        self.layout.addLayout(btn_layout)
        self.layout.addWidget(graph_widget)

        self.update_choices()

    def run(self):
        from simple_pid.pid import PID  # pip install simple-pid (requires v>2)

        s = self.settings

        pid = PID(Kp=s["Kp"],
                  Ki=s["Ki"],
                  Kd=s["Kd"],
                  setpoint=s["setpoint"],
                  starting_output=apply_min_max(self.app.get_lq(s["plant_input"]).val, s["min_plant_input"], s["max_plant_input"]),
                  )

        ii = 0
        wrap_around = 600
        self.data = mk_data_dict(wrap_around, s["setpoint"])
        t0 = time.time()
        lab_time = 0

        while not self.interrupt_measurement_called:
            pid.tunings = s["Kp"], s["Ki"], s["Kd"]
            pid.setpoint = s["setpoint"]
            sensor_value = self.app.get_lq(s["sensor"]).read_from_hardware()
            plant_input = apply_min_max(pid(sensor_value), s["min_plant_input"], s["max_plant_input"])
            self.app.get_lq(s["plant_input"]).update_value(plant_input)
            s["error"] = 100.0 * (1 - sensor_value / s["setpoint"])
            lab_time = time.time() - t0

            self.data["setpoints"][ii] = s["setpoint"]
            self.data["sensor_values"][ii] = sensor_value
            self.data["lab_times"][ii] = lab_time

            if self.should_terminate(lab_time):
                break

            ii = (ii + 1) % wrap_around
            time.sleep(0.01)

        if s["save_h5"]:
            self.save_h5()

    def should_terminate(self, lab_time):
        s = self.settings
        if s["terminate"] == INDEF:
            return False
        if s["terminate"] == TIMEOUT:
            self.set_progress(100.0 * lab_time / s["timeout"])
            return lab_time >= s["timeout"]
        if s["terminate"] == ETOL:
            self.set_progress(100.0 * s["error_tol"] / abs(s["error"]))
            return abs(s["error"]) <= s["error_tol"]
        if s["terminate"] == ETOL_W_TIMEOUT:
            self.set_progress(100.0 * lab_time / s["timeout"])
            return lab_time >= s["timeout"] or abs(s["error"]) <= s["error_tol"]

    def update_display(self):
        t = self.data["lab_times"]
        indices = numpy.argsort(t)
        self.sensor_values_plotline.setData(t[indices], self.data["sensor_values"][indices])
        self.setpoints_plotline.setData(t[indices], self.data["setpoints"][indices])

    def update_choices(self):
        s = self.settings
        s.get_lq("sensor").change_choice_list(self.app.get_setting_paths())
        s.get_lq("plant_input").change_choice_list(self.app.get_setting_paths())

    def update_choices_filtered(self):
        s = self.settings
        s.get_lq("sensor").change_choice_list(self.app.get_setting_paths(True, False))
        s.get_lq("plant_input").change_choice_list(self.app.get_setting_paths(False, True))

    def New_mini_UI(self):
        s = self.settings
        ss_btn = self.new_start_stop_button(texts=("▶", "🛑"))
        # ss_btn.setMaximumWidth(40)

        spw = s.get_lq("setpoint").new_default_widget()
        # spw.setMaximumWidth(80)

        erw = s.get_lq("error").new_default_widget()
        # erw.setMaximumWidth(80)

        show_ui_btn = self.operations.new_button("show_ui")
        show_ui_btn.setText("")
        show_ui_btn.setMaximumWidth(40)

        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(widget)
        layout.addWidget(ss_btn)
        layout.addWidget(spw)
        layout.addWidget(erw)
        layout.addWidget(show_ui_btn)
        return widget

    def save_h5(self):
        h5_file = h5_io.h5_base_file(app=self.app, measurement=self)
        group = h5_io.h5_create_measurement_group(self, h5_file)
        for k, v in self.data.items():
            group[k] = v
        h5_file.close()


def apply_min_max(value, min_value, max_value):
    return min(max(value, min_value), max_value)


def mk_data_dict(N, setpoint):
    return {
        "setpoints": numpy.ones(N) * setpoint,
        "sensor_values": numpy.ones(N) * numpy.nan,
        "lab_times": numpy.arange(N),
    }
