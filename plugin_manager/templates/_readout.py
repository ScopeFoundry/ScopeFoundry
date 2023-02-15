'''
Created on $DATE_PRETTY

@author: $AUTHORS
'''
import pyqtgraph as pg
from pyqtgraph.dockarea import DockArea
from qtpy.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget

from ScopeFoundry import Measurement, h5_io


class $READOUT_CLASS_NAME(Measurement):

    name = "$READOUT_NAME"

    def setup(self):

        S = self.settings
        S.New("save_h5", bool, initial=True)

        # just making a guess of data structure here to test if display works
        self.data = {
            "y": [2, 5, 2]
        }

    def setup_figure(self):
        self.ui = DockArea()
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.plot_dock = self.ui.addDock(
            name=self.name, widget=widget, position='right')

        # setup measurement controlls
        cb_layout = QHBoxLayout()
        layout.addLayout(cb_layout)
        cb_layout.addWidget(self.settings.New_UI(exclude=('activation', 'run_state', 'profile', )))
        cb_layout.addWidget(self.settings.activation.new_pushButton())

        # setup a plot
        graph_layout = pg.GraphicsLayoutWidget(border=(100, 100, 100))
        layout.addWidget(graph_layout)
        self.plot = graph_layout.addPlot(title=self.name)
        self.plot_lines = {}
        self.plot_lines["y"] = self.plot.plot(pen="g")

        # setup hw controls widget
        hw = self.app.hardware["$HW_NAME"]
        self.ui.addDock(name="$HW_NAME",
                        widget=hw.new_control_widgets(),
                        #position='below'
                        )

        self.update_display()

    def update_display(self):
        self.plot_lines["y"].setData(self.data['y'])

    def run(self):
        print(self.__class__, 'run method not implemented')

        # hw = self.app.hardware["$HW_NAME"]
        # self.data = {"y": []}
        # self.data['y'] = hw.dev.read_data()

        if self.settings['save_h5']:
            self.save_h5_data()

    def save_h5_data(self):
        h5_file = h5_io.h5_base_file(app=self.app, measurement=self)
        h5_meas_group = h5_io.h5_create_measurement_group(self, h5_file)
        for k, v in self.data.items():
            h5_meas_group[k] = v
        h5_file.close()
