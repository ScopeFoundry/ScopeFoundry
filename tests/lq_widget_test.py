import os

os.environ["QT_API"] = "pyqt6"
import time

import numpy as np
from qtpy import QtCore, QtWidgets


from ScopeFoundry import (
    BaseApp,
    BaseMicroscopeApp,
    HardwareComponent,
    Measurement,
    new_tree_widget,
)


class LQWidgetTestApp(BaseApp):

    name = "LQWidgetTestApp"

    def __init__(self, argv):
        BaseApp.__init__(self, argv)

        self.settings.New(
            "long_string_test",
            dtype=str,
            initial="Lorem ipsum dolor sit amet, consectetur adipiscing elit. Aliquam accumsan, ligula a tristique luctus, felis est blandit libero, nec placerat justo diam at lacus. Fusce volutpat vitae lacus non lobortis. Fusce porttitor varius placerat. Curabitur et varius urna, sit amet gravida leo. Etiam eleifend luctus erat, vel maximus libero lacinia at. Pellentesque mattis pulvinar sem, sit amet porttitor mi maximus in. Sed venenatis orci sit amet nulla luctus, vitae pulvinar neque facilisis. Donec in felis sodales libero fringilla aliquam eu non urna. Praesent ac elit ac lorem cursus aliquam eu venenatis mauris. Proin sed aliquet nunc. Duis venenatis mi dapibus.",
            ro=False,
        )

        self.ui = self.settings.New_UI()

        long_string_test_plainTextEdit = QtWidgets.QPlainTextEdit()
        self.ui.layout().addRow(
            "long_string_test_plainTextEdit", long_string_test_plainTextEdit
        )

        self.settings.long_string_test.connect_to_widget(long_string_test_plainTextEdit)

        self.console_widget.show()
        self.ui.show()


class Hardware(HardwareComponent):

    name = "hardware"

    def setup(self):
        self.settings.New("val1", initial=0.1)
        self.settings.New("val2", str, initial="hello world")
        self.settings.New("val3", str, choices=("Apple", "Bear", "Car"))

    def connect(self):
        self.settings.New("val4", int, 33).connect_to_hardware(lambda: 33, print)
        print("connected to", self.name)

    def disconnect(self):
        self.settings.remove("val4")
        print("disconnected from", self.name)


class Measure(Measurement):

    name = "measure"

    def setup(self):

        self.settings.New(
            "color test",
            str,
            choices=("yellow", "blue", "grey"),
            colors=("yellow", "blue"),
        )
        self.settings.New("run_crash_immediately", dtype=bool, initial=False)
        self.settings.New("run_crash_middle", dtype=bool, initial=False)

        self.settings.New("name", dtype=str, initial="cool_op_name")

        self.add_operation("add_setting", self.on_add_setting)
        self.add_operation("remove_setting", self.on_remove_setting)

        self.add_operation("add_operation", self.on_add_operation)
        self.add_operation("remove_operation", self.on_remove_operation)

        self.data_array = np.zeros(100)

    def on_add_setting(self):
        self.settings.New(self.settings["name"], str, "generated")

    def on_remove_setting(self):
        self.settings.remove(self.settings["name"])

    def on_add_operation(self):
        self.add_operation(
            self.settings["name"],
            lambda: print("operation called"),
        )
        print(list(self.operations.keys()))

    def on_remove_operation(self):
        self.remove_operation(self.settings["name"])
        print(list(self.operations.keys()))

    def setup_figure(self):

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        # splitter.addWidget(self.app.hardware["hardware"].New_UI())
        splitter.addWidget(
            self.app.hardware["hardware"].new_control_widgets(
                include=("val*", "relo*"),
                title="incl: val*,relo*  excl: *1",
                exclude=("*1",),
            )
        )

        splitter.addWidget(self.new_control_widgets())
        widget = QtWidgets.QWidget()
        vbox_layout = QtWidgets.QVBoxLayout(widget)
        label = QtWidgets.QLabel(
            "used add_to_layout with a given QVBoxLayout to dyn add/remove widgets. \n include pattern matching: cool_*,add*, remove*, name"
        )
        vbox_layout.addWidget(label)
        splitter.addWidget(widget)
        self.add_to_layout(vbox_layout, include=("cool_*", "add*", "remove*", "name"))

        grid_widget = QtWidgets.QWidget()
        grid_layout = QtWidgets.QGridLayout(grid_widget)
        splitter.addWidget(grid_widget)
        self.add_to_layout(grid_layout, include=("cool_*", "add*", "remove*", "name"))

        self.ui = QtWidgets.QWidget()
        vsplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        layout = QtWidgets.QVBoxLayout(self.ui)
        layout.addWidget(self.activation.new_pushButton())
        layout.addWidget(vsplitter)
        vsplitter.addWidget(
            new_tree_widget(
                (self.app.measurements["measure"], self.app.hardware["hardware"]),
                ("hello", "world"),
            )
        )
        vsplitter.addWidget(splitter)

    def run(self):

        if self.settings["run_crash_immediately"]:
            raise IOError("run_crash_immediately")

        N = 10

        self.data_array = np.zeros(N)

        for i in range(N):
            # print(self.name, i, 'of', N)
            if self.interrupt_measurement_called:
                print(self.name, "interrupted at", i, "of", N)
                break
            self.set_progress(100.0 * i / N)
            if i > N / 2 and self.settings["run_crash_middle"]:
                raise IOError("run_crash_middle")

            self.settings.New(f"cool_{i}")
            self.add_operation(f"cool_{i}", lambda: print("hello"))
            time.sleep(0.1)

        for i in range(N):
            self.settings.remove(f"cool_{i}")
            self.remove_operation(f"cool_{i}")
            time.sleep(0.1)


class MeasureNonUI(Measurement):

    name = "measure_non_ui"


class LQWidgetMicroscopeTestApp(BaseMicroscopeApp):

    name = "lq_widget_test_app"
    mdi = True

    def setup(self):

        self.add_hardware(Hardware(self))
        self.add_measurement(Measure(self))
        self.add_measurement(MeasureNonUI(self))


if __name__ == "__main__":
    import sys

    # app = LQWidgetTestApp(sys.argv)
    app = LQWidgetMicroscopeTestApp(sys.argv)
    app.exec_()
