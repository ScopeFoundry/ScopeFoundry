# There is also a unittest in tests/unittest/lq_range_test
from ScopeFoundry import BaseApp
from qtpy import QtWidgets
import pyqtgraph as pg

import logging


logging.basicConfig(level="DEBUG")


class MultiLQRangeTestApp(BaseApp):

    def __init__(self, argv):
        BaseApp.__init__(self, argv)

        ### LQ
        self.x_range = self.settings.new_multi_range(
            "x",
            n=5,
            include_center_span=True,
            include_sweep_type=True,
            unit="s",
            si=False,
            spinbox_decimals=4,
            description="range",
        )  # , preserve_num=True)

        self.x_range.add_listener(lambda: print(self.x_range.array))

        self.ui = QtWidgets.QScrollArea()
        self.ui.setWidgetResizable(True)
        hlayout = QtWidgets.QHBoxLayout()
        self.ui.setLayout(hlayout)

        hlayout.addWidget(self.x_range.New_UI())

        self.ui.layout().addWidget(self.console_widget)
        # self.plot.show()
        self.ui.show()
        self.ui.setWindowTitle("MultiLQRangeTestApp")
        # self.console_widget.show()


if __name__ == "__main__":
    app = MultiLQRangeTestApp([])
    app.exec_()
