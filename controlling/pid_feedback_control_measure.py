"""
Created on Jan 23, 2023

@author: Benedikt Ursprung
"""

import time

import numpy
import pyqtgraph as pg
from qtpy import QtCore, QtGui, QtWidgets

from ScopeFoundry import Measurement, h5_io
from ScopeFoundry.widgets import QSearchableComboBox

INDEF = "indefinite"
TIMEOUT = "timeout"
ETOL = "error_tol"
ETOL_W_TIMEOUT = f"{ETOL}_with_{TIMEOUT}"


class PIDFeedbackLoopDiagram(QtWidgets.QWidget):
    CANVAS_WIDTH = 1280
    CANVAS_HEIGHT = 200

    # Layout parameters (canvas units). Everything else is derived from these.
    MARGIN = 5
    TITLE_H = 24  # space for a block's title
    PAD = 8  # inner padding of blocks
    ROW_H = 32  # height of a line-edit style widget
    ROW_GAP = 6
    SETPOINT_X, SETPOINT_W = 20, 170
    SUM_X, SUM_D = 230, 50  # summing junction: left edge, diameter
    PID_X, PID_W = 325, 225
    PID_LABEL_W = 30
    PLANT_X, PLANT_W = 595, 375
    PLANT_INPUT_W = 350
    PLANT_LIMIT_W = 135
    PLANT_LIMIT_LABEL_W = 32
    SENSOR_W = 350
    SENSOR_DY = 32  # sensor top relative to the main signal line
    RETURN_GAP = 16  # feedback line below the sensor
    OUTPUT_END_X = 1260
    TAP_DX = 130  # where the sensor taps the output, right of the plant
    ARROW_HEAD_L, ARROW_HEAD_W = 8, 4

    def _build_layout(self):
        c = self
        rows_h = 3 * c.ROW_H + 2 * c.ROW_GAP
        pid_h = c.TITLE_H + rows_h + c.PAD
        pid_y = c.MARGIN
        mid = pid_y + pid_h / 2  # main signal line
        plant_h = c.TITLE_H + 2 * c.ROW_H + c.ROW_GAP + c.PAD
        plant_y = mid - plant_h / 2
        plant_right = c.PLANT_X + c.PLANT_W
        tap_x = plant_right + c.TAP_DX
        sensor_h = c.TITLE_H + c.ROW_H + c.PAD
        sensor_y = mid + c.SENSOR_DY
        sensor_x = tap_x - c.SENSOR_W / 2
        return_y = sensor_y + sensor_h + c.RETURN_GAP
        c.CANVAS_HEIGHT = int(return_y + c.MARGIN)

        c.mid_y = mid
        c.tap_x = tap_x
        c.return_y = return_y
        c.sum_cx = c.SUM_X + c.SUM_D / 2
        c.sum_rect = (c.SUM_X, mid - c.SUM_D / 2, c.SUM_D, c.SUM_D)
        c.pid_rect = (c.PID_X, pid_y, c.PID_W, pid_h)
        c.plant_rect = (c.PLANT_X, plant_y, c.PLANT_W, plant_h)
        c.sensor_rect = (sensor_x, sensor_y, c.SENSOR_W, sensor_h)

        setpoint_y = mid - c.ROW_H / 2
        c.setpoint_label_rect = (c.SETPOINT_X, setpoint_y - 22, c.SETPOINT_W, 20)
        c.output_label_rect = (c.OUTPUT_END_X - 100, mid - 26, 100, 22)

        pid_widget_x = c.PID_X + c.PID_LABEL_W + 15
        pid_widget_w = c.PID_W - c.PID_LABEL_W - 30
        c.widget_geometry = {
            "setpoint": (c.SETPOINT_X, setpoint_y, c.SETPOINT_W, c.ROW_H),
            "plant_input": (
                c.PLANT_X + (c.PLANT_W - c.PLANT_INPUT_W) / 2,
                plant_y + c.TITLE_H,
                c.PLANT_INPUT_W,
                c.ROW_H,
            ),
            "sensor": (
                sensor_x + c.PAD,
                sensor_y + c.TITLE_H,
                c.SENSOR_W - 2 * c.PAD,
                c.ROW_H,
            ),
        }
        c.labels = []  # (text, x, y, w, h)
        for i, name in enumerate(("Kp", "Ki", "Kd")):
            y = pid_y + c.TITLE_H + i * (c.ROW_H + c.ROW_GAP)
            c.widget_geometry[name] = (pid_widget_x, y, pid_widget_w, c.ROW_H)
            c.labels.append((name, c.PID_X + 10, y, c.PID_LABEL_W, c.ROW_H))
        limits_y = plant_y + c.TITLE_H + c.ROW_H + c.ROW_GAP
        min_label_x = c.PLANT_X + c.PAD
        min_x = min_label_x + c.PLANT_LIMIT_LABEL_W + 3
        max_x = plant_right - c.PAD - c.PLANT_LIMIT_W
        max_label_x = max_x - 3 - c.PLANT_LIMIT_LABEL_W
        c.widget_geometry["min_plant_input"] = (
            min_x,
            limits_y,
            c.PLANT_LIMIT_W,
            c.ROW_H,
        )
        c.widget_geometry["max_plant_input"] = (
            max_x,
            limits_y,
            c.PLANT_LIMIT_W,
            c.ROW_H,
        )
        c.labels.append(("Min", min_label_x, limits_y, c.PLANT_LIMIT_LABEL_W, c.ROW_H))
        c.labels.append(("Max", max_label_x, limits_y, c.PLANT_LIMIT_LABEL_W, c.ROW_H))

    def __init__(self, widgets):
        super().__init__()
        self._build_layout()
        self.setMinimumHeight(self.CANVAS_HEIGHT - 20)
        self.setMaximumHeight(self.CANVAS_HEIGHT + 10)
        self.widgets = widgets
        for widget in self.widgets.values():
            widget.setParent(self)
        self._position_widgets()

    def _transform(self):
        scale = min(
            self.width() / self.CANVAS_WIDTH,
            self.height() / self.CANVAS_HEIGHT,
        )
        x_offset = (self.width() - self.CANVAS_WIDTH * scale) / 2
        y_offset = (self.height() - self.CANVAS_HEIGHT * scale) / 2
        return scale, x_offset, y_offset

    def _position_widgets(self):
        scale, x_offset, y_offset = self._transform()
        for name, widget in self.widgets.items():
            x, y, width, height = self.widget_geometry[name]
            widget.setGeometry(
                round(x_offset + x * scale),
                round(y_offset + y * scale),
                round(width * scale),
                round(height * scale),
            )

    def resizeEvent(self, event):
        self._position_widgets()
        super().resizeEvent(event)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        scale, x_offset, y_offset = self._transform()
        painter.translate(x_offset, y_offset)
        painter.scale(scale, scale)

        palette = self.palette()
        foreground = palette.color(QtGui.QPalette.WindowText)
        background = palette.color(QtGui.QPalette.Window)
        pen = QtGui.QPen(foreground, 2)
        painter.setPen(pen)
        painter.setBrush(background)

        def draw_block(x, y, width, height, label):
            rect = QtCore.QRectF(x, y, width, height)
            painter.drawRoundedRect(rect, 5, 5)
            painter.drawText(
                rect.adjusted(0, 5, 0, 0),
                QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop,
                label,
            )

        def draw_arrow(start, end):
            painter.drawLine(start, end)
            x, y = end.x(), end.y()
            hl, hw = self.ARROW_HEAD_L, self.ARROW_HEAD_W
            if start.x() < x:
                points = [(x, y), (x - hl, y - hw), (x - hl, y + hw)]
            elif start.x() > x:
                points = [(x, y), (x + hl, y - hw), (x + hl, y + hw)]
            elif start.y() < y:
                points = [(x, y), (x - hw, y - hl), (x + hw, y - hl)]
            else:
                points = [(x, y), (x - hw, y + hl), (x + hw, y + hl)]
            painter.setBrush(foreground)
            painter.drawPolygon(
                QtGui.QPolygonF([QtCore.QPointF(px, py) for px, py in points])
            )
            painter.setBrush(background)

        def point(x, y):
            return QtCore.QPointF(x, y)

        def label(text, x, y, w, h):
            painter.drawText(QtCore.QRectF(x, y, w, h), QtCore.Qt.AlignCenter, text)

        mid = self.mid_y
        sum_x, sum_y, sum_w, sum_h = self.sum_rect
        pid_x, _, pid_w, _ = self.pid_rect
        plant_x, _, plant_w, _ = self.plant_rect
        sensor_x, sensor_y, sensor_w, sensor_h = self.sensor_rect
        setpoint_x, _, setpoint_w, _ = self.widget_geometry["setpoint"]

        label("Setpoint", *self.setpoint_label_rect)
        painter.drawEllipse(QtCore.QRectF(*self.sum_rect))
        label("Σ", *self.sum_rect)
        draw_block(*self.pid_rect, "PID Controller")
        draw_block(*self.plant_rect, "Plant")
        draw_block(*self.sensor_rect, "Sensor")
        for text, x, y, w, h in self.labels:
            label(text, x, y, w, h)
        label("Output", *self.output_label_rect)

        # forward path
        draw_arrow(point(setpoint_x + setpoint_w, mid), point(sum_x, mid))
        draw_arrow(point(sum_x + sum_w, mid), point(pid_x, mid))
        draw_arrow(point(pid_x + pid_w, mid), point(plant_x, mid))
        draw_arrow(point(plant_x + plant_w, mid), point(self.OUTPUT_END_X, mid))

        # feedback path: tap on the output -> sensor -> back to the junction
        tap_x, return_y = self.tap_x, self.return_y
        painter.setBrush(foreground)
        painter.drawEllipse(point(tap_x, mid), 3, 3)
        painter.setBrush(background)
        draw_arrow(point(tap_x, mid), point(tap_x, sensor_y))
        sensor_bottom = sensor_y + sensor_h
        painter.drawLine(point(tap_x, sensor_bottom), point(tap_x, return_y))
        painter.drawLine(point(tap_x, return_y), point(self.sum_cx, return_y))
        draw_arrow(point(self.sum_cx, return_y), point(self.sum_cx, sum_y + sum_h))
        label("−", self.sum_cx + 4, sum_y + sum_h + 2, 16, 16)

        painter.end()
        event.accept()


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
            default_widget_factory=QSearchableComboBox,
        )
        s.New(
            "plant_input",
            str,
            initial="-",
            choices=("-",),
            description="choose a setting that has a hardware_set_func",
            default_widget_factory=QSearchableComboBox,
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

        diagram_widget_names = (
            "setpoint",
            "Kp",
            "Ki",
            "Kd",
            "min_plant_input",
            "max_plant_input",
            "plant_input",
            "sensor",
        )
        diagram_widgets = {
            name: s.get_lq(name).new_default_widget() for name in diagram_widget_names
        }
        diagram_widget = PIDFeedbackLoopDiagram(diagram_widgets)

        terminate_widget = self.settings.New_UI(("terminate", "timeout", "error_tol"))

        btn_layout = QtWidgets.QVBoxLayout()
        btn_layout.addWidget(self.new_start_stop_button())
        op_button = QtWidgets.QPushButton("unfilter options")
        op_button.clicked.connect(self.update_choices)
        btn_layout.addWidget(op_button)
        op_button = QtWidgets.QPushButton("filter options to available")
        op_button.setToolTip("only settings that are connected to hardware")
        op_button.clicked.connect(self.update_choices_filtered)
        btn_layout.addWidget(op_button)

        r_layout = QtWidgets.QHBoxLayout()
        r_layout.addLayout(btn_layout)
        r_layout.addWidget(terminate_widget)

        header_layout = QtWidgets.QVBoxLayout()
        header_layout.addWidget(diagram_widget)
        header_layout.addLayout(r_layout)

        graph_widget = pg.GraphicsLayoutWidget(border=(0, 0, 0))
        axes = graph_widget.addPlot(title=self.name)
        t = self.data["lab_times"]
        self.sensor_values_plotline = axes.plot(t, self.data["sensor_values"], pen="w")
        self.setpoints_plotline = axes.plot(t, self.data["setpoints"], pen="y")

        self.ui = QtWidgets.QWidget()
        self.layout = QtWidgets.QVBoxLayout(self.ui)
        self.layout.addLayout(header_layout)
        self.layout.addWidget(graph_widget)
        self.update_choices()

    def run(self):
        from simple_pid.pid import (
            PID,
        )  # pip install simple-pid (requires v>2) or uv add simple-pid

        s = self.settings

        pid = PID(
            Kp=s["Kp"],
            Ki=s["Ki"],
            Kd=s["Kd"],
            setpoint=s["setpoint"],
            starting_output=apply_min_max(
                self.app.get_lq(s["plant_input"]).val,
                s["min_plant_input"],
                s["max_plant_input"],
            ),
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
            plant_input = apply_min_max(
                pid(sensor_value), s["min_plant_input"], s["max_plant_input"]
            )
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
        self.sensor_values_plotline.setData(
            t[indices], self.data["sensor_values"][indices]
        )
        self.setpoints_plotline.setData(t[indices], self.data["setpoints"][indices])

    def update_choices(self):
        s = self.settings
        s.get_lq("sensor").change_choice_list(self.app.get_setting_paths())
        s.get_lq("plant_input").change_choice_list(self.app.get_setting_paths())

    def update_choices_filtered(self):
        s = self.settings
        s.get_lq("sensor").change_choice_list(self.app.get_setting_paths(True, False))
        s.get_lq("plant_input").change_choice_list(
            self.app.get_setting_paths(False, True)
        )

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


if __name__ == "__main__":
    from ScopeFoundry import BaseMicroscopeApp

    class MyApp(BaseMicroscopeApp):

        def setup(self):
            self.add_measurement(PIDFeedbackControl(self))

        pass

    app = MyApp()
    app.exec_()
