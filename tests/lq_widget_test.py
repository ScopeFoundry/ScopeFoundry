import time

import numpy as np
import pyqtgraph as pg
from qtpy import QtCore, QtWidgets

from ScopeFoundry import BaseApp, BaseMicroscopeApp, HardwareComponent, Measurement


class LQWidgetTestApp(BaseApp):

    name = 'LQWidgetTestApp'

    def __init__(self,argv):
        BaseApp.__init__(self,argv)

        self.settings.New('long_string_test',  dtype=str, initial="Lorem ipsum dolor sit amet, consectetur adipiscing elit. Aliquam accumsan, ligula a tristique luctus, felis est blandit libero, nec placerat justo diam at lacus. Fusce volutpat vitae lacus non lobortis. Fusce porttitor varius placerat. Curabitur et varius urna, sit amet gravida leo. Etiam eleifend luctus erat, vel maximus libero lacinia at. Pellentesque mattis pulvinar sem, sit amet porttitor mi maximus in. Sed venenatis orci sit amet nulla luctus, vitae pulvinar neque facilisis. Donec in felis sodales libero fringilla aliquam eu non urna. Praesent ac elit ac lorem cursus aliquam eu venenatis mauris. Proin sed aliquet nunc. Duis venenatis mi dapibus.", ro=False)

        self.ui = self.settings.New_UI()

        long_string_test_plainTextEdit = QtWidgets.QPlainTextEdit()
        self.ui.layout().addRow("long_string_test_plainTextEdit", long_string_test_plainTextEdit)

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
        print("connected to", self.name)

    def disconnect(self):
        print("disconnected from", self.name)


class Measure(Measurement):

    name = "measure"

    def setup(self):

        self.settings.New("amplitude", dtype=float, initial=1.0)
        self.settings.New("run_crash_immediately", dtype=bool, initial=False)
        self.settings.New("run_crash_middle", dtype=bool, initial=False)
        self.settings.New("pre_run_crash", dtype=bool, initial=False)
        self.settings.New("post_run_crash", dtype=bool, initial=False)

    def setup_figure(self):

        self.plot = pg.PlotWidget()
        self.plot_line = self.plot.plot()

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        splitter.addWidget(self.new_control_widgets())
        splitter.addWidget(self.New_UI(("amplitude", "post_run_crash")))
        splitter.addWidget(self.app.hardware["hardware"].new_control_widgets())
        splitter.addWidget(
            self.app.hardware["hardware"].New_UI(
                exclude=("connected",), style="scroll_form", title="my_tile"
            )
        )

        self.ui = pg.QtWidgets.QWidget()
        layout = pg.QtWidgets.QVBoxLayout(self.ui)
        # layout.addWidget(
        #     new_tree((self.app.measurements["measure1"], self), ("hello", "world"))
        # )
        layout.addWidget(self.plot)
        layout.addWidget(splitter)

    def run(self):

        if self.settings["run_crash_immediately"]:
            raise IOError("run_crash_immediately")

        N = 100

        self.data_array = np.zeros(N)

        for i in range(N):
            # print(self.name, i, 'of', N)
            if self.interrupt_measurement_called:
                print(self.name, "interrupted at", i, "of", N)
                break
            self.set_progress(100.0 * i / N)
            self.data_array[i] = self.settings["amplitude"] * np.sin(2 * np.pi * i / N)
            time.sleep(0.05)
            if i > 50 and self.settings["run_crash_middle"]:
                raise IOError("run_crash_middle")

    def update_display(self):
        self.plot_line.setData(self.data_array)

    def pre_run(self):
        print(self.name, "pre_run fun!")
        time.sleep(0.5)
        if self.settings["pre_run_crash"]:
            raise IOError("pre_run_crash")
        time.sleep(0.5)
        print(self.name, "pre_run fun done!")

    def post_run(self):
        print(self.name, "post_run fun!")
        time.sleep(0.5)
        if self.settings["post_run_crash"]:
            raise IOError("post_run_crash")
        time.sleep(0.5)
        print(self.name, "post_run fun done!")


class LQWidgetMicroscopeTestApp(BaseMicroscopeApp):

    name = "measurement"

    def setup(self):

        self.add_hardware(Hardware(self))

        self.add_measurement(Measure(self))


if __name__ == '__main__':
    import sys
    app = LQWidgetTestApp(sys.argv)
    app = LQWidgetMicroscopeTestApp(sys.argv)
    app.exec_()
