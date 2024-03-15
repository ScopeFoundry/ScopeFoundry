"""
author: Camille Stavrakas, Edward Barnard, Benedikt Ursprung
"""
import datetime
import time
from typing import Sequence

import numpy as np
import pyqtgraph as pg
from qtpy import QtWidgets
from ScopeFoundry import Measurement, h5_io

DESCRIPTION = """
<p>Sweeps a setting z within a range, measures an optimization quantity f(z)
and calculates z0 such that:</p>
<p>f(z0) >= f(z) for all z</p>
<p>finally sets z = z0 + z_offset</p>
"""


def mk_data_dict(center, span, num, z_original):
    return {
        "z_original": z_original,
        "z0_coarse": center,
        "z0_fine": center,
        "z0": center,
        "z_coarse": mk_z_array(center, span, num),
        "f_coarse": np.zeros(num),
        "z_fine": mk_z_array(center, span, 2 * num),
        "f_fine": np.zeros(2 * num),
    }


SAME_AS_Z = "same_as_z"


class RangedOptimization(Measurement):
    name = "ranged_optimization"

    def __init__(
        self,
        app,
        name=None,
        lq_kwargs={"spinbox_decimals": 6, "unit": ""},
        range_initials=[0, 10, 0.1],
    ):
        self.range_initials = range_initials
        self.lq_kwargs = lq_kwargs
        self.z0_history = []
        self.f_history = []
        self.z_history = []
        self.time_history = []
        self.z_read_path = ""
        Measurement.__init__(self, app, name)

    def setup(self):
        self.settings.New("f", str, choices=("",), description=DESCRIPTION)
        self.settings.New("N_samples", int, initial=10)
        self.settings.New(
            "sampling_period",
            float,
            initial=0.050,
            unit="s",
            si=True,
            description="time waited between sampling",
        )
        self.settings.New(
            "use_current_z_as_center",
            bool,
            initial=True,
            description="instead of <b>z_center</b> the current value of <b>z</b> is used",
        )
        self.settings.New_Range(
            "z",
            include_center_span=True,
            initials=self.range_initials,
            description="defines a range over which <b>z</b> is varied",
            **self.lq_kwargs,
        )
        self.settings.New(
            "z_offset",
            initial=0,
            description="an offset that will be applied when moving to optimal <i>z</i> value after optimization",
            **self.lq_kwargs,
        )
        self.settings.New(
            "use_fine_optimization",
            bool,
            initial=True,
            description="optimization runs again around z0 from first run",
        )
        self.settings.New("coarse_to_fine_span_ratio", initial=4.0)
        self.settings.New("z_span_travel_time", initial=2.0, unit="sec")
        self.settings.New(
            "z",
            str,
            choices=[],
            description="path to a setting that can manipulate the sweep value z",
        )
        self.settings.New(
            "z_read",
            str,
            initial=SAME_AS_Z,
            choices=[SAME_AS_Z],
            description=f"if not <i>{SAME_AS_Z}</i> this setting will be used to get actual value of z",
        )
        cs = list(post_processors.keys())
        self.settings.New(
            "post_processor",
            str,
            initial="gauss_mean",
            choices=cs,
            description="e.g. fit gaussian to data and use the derived mean as optimized value",
        )
        self.settings.New("take_post_process_value", bool, initial=False)
        self.settings.New("save_h5", bool, initial=True)

        s = self.settings
        self.data = mk_data_dict(s["z_center"], s["z_span"], s["z_num"], 0)
        self.add_operation("filter choices", self.filter_choices)
        self.add_operation("unfilter choices", self.unfilter_choices)
        self.add_operation("post process", self.post_process)
        self.add_operation("go to optimal value", self.go_to_optimal_value)
        self.add_operation("go to post process value",
                           self.go_to_post_process_value)

    def setup_figure(self):
        s = self.settings

        settings_layout = QtWidgets.QHBoxLayout()
        settings_layout.addWidget(
            s.New_UI(("z_span", "z_num", "use_current_z_as_center", "z_center")))
        settings_layout.addWidget(s.New_UI(("f", "z", "z_read", "z_offset")))
        settings_layout.addWidget(s.New_UI(
            ("N_samples", "sampling_period", "use_fine_optimization", "post_processor")))

        take_pushButton = QtWidgets.QPushButton("interrupt and take")
        take_pushButton.clicked.connect(self.take_current_optimal)
        pp_btn = QtWidgets.QPushButton("post process")
        pp_btn.clicked.connect(self.post_process)
        go_to_pp_btn = QtWidgets.QPushButton("go to processed value")
        go_to_pp_btn.clicked.connect(self.go_to_post_process_value)
        btns_layout = QtWidgets.QHBoxLayout()
        btns_layout.addWidget(s.get_lq("activation").new_pushButton())
        btns_layout.addWidget(take_pushButton)
        btns_layout.addWidget(pp_btn)
        btns_layout.addWidget(go_to_pp_btn)

        self.ui = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(settings_layout)
        layout.addLayout(btns_layout)
        layout.addWidget(self.mk_graph_widget())
        self.ui.setLayout(layout)

        self.unfilter_choices()

    def run(self):
        s = self.settings

        self._take_current_flag = False
        self.set_post_process_lines_visible(False)
        self.update_z_read()
        self.try_connect_hws()
        self.update_z_center()
        z_ori = self.read_z()
        d = self.data = mk_data_dict(
            s["z_center"], s["z_span"], s["z_num"], z_ori)

        self.ii = 0
        self.total_dpt = (1 + 2 * s["use_fine_optimization"]) * s["z_num"]

        # coarse sweep
        self.sweep("coarse")

        # fine sweep
        if s["use_fine_optimization"] and not self.interrupt_measurement_called:
            r = self.settings["coarse_to_fine_span_ratio"]
            d["z_fine"] = mk_z_array(d["z0_coarse"], s["z_span"] / r, 2 * s["z_num"])
            d["f_fine"] = np.ones_like(d["z_fine"]) * max(d["f_coarse"])
            self.sweep("fine")

        # go to final position
        if self.interrupt_measurement_called:
            if self._take_current_flag:
                val = d["z0"] + s["z_offset"]
                msg = f"{self.name} interrupted with take, moving optimal to {val:0.2f}"
            else:
                val = d['z_original']
                msg = f"{self.name} interrupted, moving to original position to {val:0.2f}"
            timeout = timeout = s["z_span_travel_time"] / 4
            self.write_z_target(val, timeout, msg)
        else:
            if s["take_post_process_value"]:
                self.go_to_post_process_value()
            else:
                self.go_to_optimal_value()
            self.update_history(d["z0"])
            self.save_h5()
            self.print_history()
            
    def sweep(self, name="coarse"):
        s = self.settings
        d = self.data
        
        self.write_z_target(d[f"z_{name}"][0], s["z_span_travel_time"])
        for i, z in enumerate(d[f"z_{name}"]):
            self.set_progress((self.ii + 1) * 100 / self.total_dpt)
            self.write_z_target(
                z, s["z_span_travel_time"] / s["z_num"] / 4)
            d[f"f_{name}"][i] = self.read_f()
            d["z0"] = d[f"z0_{name}"] = d[f"z_{name}"][np.argmax(d[f"f_{name}"])]
            if self.interrupt_measurement_called:
                break
            self.ii += 1
            
    def update_display(self):
        s = self.settings
        d = self.data

        self.plot_line_coarse.setData(d["z_coarse"], d["f_coarse"])
        self.plot_line_fine.setData(d["z_fine"], d["f_fine"])

        self.line_z_original.setPos(d["z_original"])
        self.line_z0_coarse.setPos(d["z0_coarse"])
        self.line_z0_fine.setPos(d["z0_fine"])

        self.line_z0_fine.setVisible(s["use_fine_optimization"])
        self.plot_line_fine.setVisible(s["use_fine_optimization"])

    def save_h5(self):
        h5_file = h5_io.h5_base_file(app=self.app, measurement=self)
        group = h5_io.h5_create_measurement_group(self, h5_file)
        self.data["times_history"] = [
            int(t.timestamp()) for t in self.time_history]
        self.data["z0_history"] = self.z0_history
        for k, v in self.data.items():
            group[k] = np.array(v)
        h5_file.close()

    def update_history(self, z0):
        s = self.settings
        self.z0_history.append(z0)
        self.f_history.append(s["f"])
        self.z_history.append(s["z_read"])
        self.time_history.append(datetime.datetime.now())

    def print_history(self):
        template = "{0:%y%m%d_%H%M%S}: {2:35} {1:8.4}"
        for rec in zip(self.time_history, self.z0_history, self.f_history):
            print(template.format(*rec))

    def read_f(self):
        x = 0.0
        for _ in range(self.settings["N_samples"]):
            x += self.app.read_setting(self.settings["f"])
            time.sleep(self.settings["sampling_period"])

        return x / self.settings["N_samples"]

    def write_z_target(self, value, timeout=0, msg=None):
        self.app.write_setting(self.settings["z"], value)
        if msg:
            print(msg)
        time.sleep(timeout)

    def read_z(self):
        return self.app.read_setting(self.z_read_path)

    def update_z_read(self):
        s = self.settings
        if s["z_read"] == SAME_AS_Z:
            self.z_read_path = s["z"]
        else:
            self.z_read_path = s["z_read"]

    def update_z_center(self):
        s = self.settings
        if s["use_current_z_as_center"]:
            s["z_center"] = self.read_z() - s["z_offset"]
            
    def try_connect_hws(self):
        """in case user forgot to connect to corresponding hardware"""
        self.connect_hw(self.settings["z"])
        self.connect_hw(self.settings["z_read"])
        self.connect_hw(self.settings["f"])

    def connect_hw(self, lq_path):
        if not lq_path.startswith("hw"):
            return
        try:
            sec, hw_name, _ = lq_path.split("/")
            print(self.name, "setting",
                  "/".join([sec, hw_name, "connected"]), "to True")
            self.app.write_setting("/".join([sec, hw_name, "connected"]), True)
        except (ValueError, KeyError) as e:
            print(self.name, "could connect")
            print(e)

    def take_current_optimal(self):
        self._take_current_flag = True
        self.interrupt_measurement_called = True

    def post_process(self):
        """apply an algorithm to find a derived optimized quantity"""
        s = self.settings
        if s["use_fine_optimization"]:
            z, f = self.data["z_fine"], self.data["f_fine"]
        else:
            z, f = self.data["z_coarse"], self.data["f_coarse"]

        z0, fs = post_process(z, f, s["post_processor"])

        self.set_post_process_lines_visible(True)
        self.plot_line_post_process.setData(z, fs)
        self.line_z0_post_process.setPos(z0)
        return z0

    def set_post_process_lines_visible(self, visible: bool):
        self.plot_line_post_process.setVisible(visible)
        self.line_z0_post_process.setVisible(visible)

    def go_to_post_process_value(self):
        s = self.settings
        val = self.post_process() + s["z_offset"]
        msg = f"{self.name} going to post process position {val:0.2f}"
        self.write_z_target(val, msg=msg)

    def go_to_optimal_value(self):
        s = self.settings
        val = self.data["z0"] + s["z_offset"]
        msg = f"{self.name} going to optimal position {val:0.2f}"
        self.write_z_target(val, msg=msg)

    def _set_choices(self, name, choices):
        before = self.settings[name]
        self.settings.get_lq(name).change_choice_list(choices)
        if not before in choices:
            before = choices[0]
        self.settings[name] = before

    def filter_choices(self):
        self._set_choices("f", self.app.get_setting_paths(True, False))
        self._set_choices("z", self.app.get_setting_paths(False, True))
        self._set_choices("z_read", [SAME_AS_Z] + 
                          self.app.get_setting_paths(True, False))

    def unfilter_choices(self):
        choices = self.app.get_setting_paths()
        self._set_choices("f", choices)
        self._set_choices("z", choices)
        self._set_choices("z_read", [SAME_AS_Z] + choices)

    def mk_graph_widget(self):
        widget = pg.GraphicsLayoutWidget(border=(0, 0, 0))
        axes = widget.addPlot()
        axes.showGrid(x=True, y=True, alpha=0.3)

        self.plot_line_coarse = axes.plot()
        self.plot_line_fine = axes.plot(pen="r")
        self.plot_line_post_process = axes.plot(pen="g")

        # indicator lines
        self.line_z_original = pg.InfiniteLine(
            movable=False,
            pen="b",
            label="original position: {value:0.6f}",
            labelOpts={
                "color": "b",
                "movable": True,
                "position": 0.15,
                "fill": (200, 200, 200, 200),
            },
        )
        self.line_z0_coarse = pg.InfiniteLine(
            movable=False,
            pen=(200, 200, 200),
            label="coarse optimized: {value:0.6f}",
            labelOpts={
                "color": (200, 200, 200),
                "movable": True,
                "position": 0.30,
                "fill": (200, 200, 200, 60),
            },
        )
        self.line_z0_fine = pg.InfiniteLine(
            movable=False,
            pen="r",
            label="fine optimized: {value:0.6f}",
            labelOpts={
                "color": "r",
                "movable": True,
                "position": 0.45,
                "fill": (200, 200, 200, 80),
            },
        )
        self.line_z0_post_process = pg.InfiniteLine(
            movable=False,
            pen="g",
            label="post process value: {value:0.6f}",
            labelOpts={
                "color": "g",
                "movable": True,
                "position": 0.50,
                "fill": (200, 200, 200, 80),
            },
        )
        axes.addItem(self.line_z_original, ignoreBounds=True)
        axes.addItem(self.line_z0_coarse, ignoreBounds=True)
        axes.addItem(self.line_z0_fine, ignoreBounds=True)
        axes.addItem(self.line_z0_post_process, ignoreBounds=True)
        axes.setLabels(bottom="z", left="f")
        axes.enableAutoRange()

        return widget


def mk_z_array(center, span, num):
    return np.linspace(center - 0.5 * span, center + 0.5 * span, num)


def gauss(x, a, x0, sigma):
    return a * np.exp(-((x - x0) ** 2) / (2 * sigma ** 2))


def fit_gauss(x, y):
    from scipy.optimize import curve_fit

    p0 = [y.max(), x[y.argmax()], 10]
    popt, _ = curve_fit(gauss, x, y, p0=p0)
    return popt  # a,mean,sigma


def post_process_gauss(z, f):
    a, mean, sigma = fit_gauss(z, f - f.min())
    f0 = gauss(z, a, mean, sigma) + f.min()
    z0 = mean
    return z0, f0


def post_process_min(z, f):
    return z[np.array(f.argmin())], f


def post_process_max(z, f):
    return z[np.array(f.argmax())], f


post_processors = {
    "gauss_mean": post_process_gauss,
    "min": post_process_min,
    "max": post_process_max,
}


def post_process(x: Sequence, y: Sequence, post_processor: str="gauss_mean"):
    func = post_processors[post_processor]
    return func(x, y)
