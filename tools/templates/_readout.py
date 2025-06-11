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
        """
        Runs once during app initialization.
        This is where you define your settings, 
        and set up data structures.
        """
        s = self.settings
        s.New("save_h5", bool, initial=True)

        # data structure of the measurement
        self.data = {"y": [2, 5, 2], "img": [[2, 4], [1, 3]]}

    def setup_figure(self):
        """
        Runs once during app initialization and is responsible
        for creating a QtWidgets.QWidget self.ui.
        """
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
        """
        Runs when the measurement starts. Executes in a separate thread from the GUI.
        It should not update the graphical interface directly and should focus only
        on data acquisition.
        """

        print(self.__class__, "run method not implemented")

        # hw = self.app.hardware["$HW_NAME"]
        # self.data['y'] = hw.dev.read_data()

        if self.settings["save_h5"]:
            self.save_h5(data=self.data)


    # ---------------------------------------------------------------------------
    ## UNCOMMENT IF YOU HAVE SCOPEFOUNDRY 2.0 OR EARLIER
    # ---------------------------------------------------------------------------
    # def save_h5(self, data):
    #     """
    #     opens new a .h5 file, stores *data*, and closes the file.

    #     If *dataset_metadata* is None, Measurement.new_dataset_metadata() is called which updates
    #     Measurement.dataset_metadata
    #     """
    #     self.open_new_h5_file(data=data)
    #     self.close_h5_file()

    # def open_new_h5_file(self, data = None):
    #     """
    #     sets attributes:
    #       - Measurement.h5_file
    #       - Measurement.h5_meas_group
    #     returns Measurement.h5_meas_group
    #     """

    #     # there might be a file open already
    #     self.close_h5_file()

    #     from ScopeFoundry import h5_io

    #     self.h5_file = h5_io.h5_base_file(self.app, measurement=self)
    #     self.h5_meas_group = h5_io.h5_create_measurement_group(self, self.h5_file)

    #     if data:
    #         for name, value in data.items():
    #             self.h5_meas_group.create_dataset(name=name, data=value)

    #     return self.h5_meas_group 

    # def close_h5_file(self):
    #     if hasattr(self, "h5_file") and self.h5_file.id is not None:
    #         self.h5_file.close()
