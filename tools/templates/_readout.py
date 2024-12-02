"""
Created on $DATE_PRETTY

@author: $AUTHORS
"""

import pyqtgraph as pg
from qtpy import QtCore, QtWidgets

from ScopeFoundry import Measurement, h5_io


class $READOUT_CLASS_NAME(Measurement):

    name = "$READOUT_NAME"

    def setup(self):

        s = self.settings
        s.New("save_h5", bool, initial=True)

        # data structure of the measurement
        self.data = {"y": [2, 5, 2], "img": [[2, 4], [1, 3]]}

    def setup_figure(self):
        # measurement controlls
        cb_layout = QtWidgets.QHBoxLayout()
        cb_layout.addWidget(self.new_start_stop_button())
        cb_layout.addWidget(
            self.settings.New_UI(
                exclude=("activation", "run_state", "profile", "progress")
            )
        )
        header_widget = QtWidgets.QWidget()
        header_layout = QtWidgets.QVBoxLayout(header_widget)
        header_layout.addLayout(cb_layout)

        # plot
        self.graphics_widget = pg.GraphicsLayoutWidget(border=(100, 100, 100))
        self.plot = self.graphics_widget.addPlot(title=self.name)
        self.plot_lines = {}
        self.plot_lines["y"] = self.plot.plot(pen="g")
        # adding an image item
        # self.img_widget = self.graphics_widget.addPlot()
        # self.img_item = pg.ImageItem()
        # self.img_widget.addItem(self.img_item)

        # hw controls (also in the tree)
        # hw = self.app.hardware["$HW_NAME"]
        # hw_ctr = hw.new_control_widgets()

        # ScopeFoundry assumes .ui is the main widget:
        self.ui = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        self.ui.addWidget(header_widget)
        self.ui.addWidget(self.graphics_widget)
        # self.ui.addWidget(hw_ctr)

    def update_display(self):
        self.plot_lines["y"].setData(self.data["y"])
        # self.img_item.setImage(self.data["img"])

    def run(self):
        print(self.__class__, "run method not implemented")

        # hw = self.app.hardware["$HW_NAME"]
        # self.data['y'] = hw.dev.read_data()

        if self.settings["save_h5"]:
            self.save_h5_data()

    def save_h5_data(self):
        h5_file = h5_io.h5_base_file(app=self.app, measurement=self)
        h5_meas_group = h5_io.h5_create_measurement_group(self, h5_file)
        for k, v in self.data.items():
            h5_meas_group[k] = v
        h5_file.close()
