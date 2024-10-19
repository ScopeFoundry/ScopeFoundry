from functools import partial
import logging

from qtpy import QtWidgets

from ScopeFoundry import BaseApp, new_tree
from ScopeFoundry.ndarray_interactive import ArrayLQ_QTableModel

logging.basicConfig(level='DEBUG')


class LQArrayTestApp(BaseApp):

    name = 'LQArrayTestApp'

    def __init__(self, argv=[], dark_mode=False):
        super().__init__(argv, dark_mode)

        self.settings.New(
            "test_array",
            dtype=float,
            is_array=True,
            ro=False,
            fmt="%1.2f",
            initial=[[147, 111, 100]],
        )  # ,[208, 8 , 100],[218, 45 , 100],[345, 1500 , 100,],[517, 8 , 100],[772, 300, 100]])

        self.ui = QtWidgets.QScrollArea()
        self.ui.setWidgetResizable(True)
        hlayout = QtWidgets.QHBoxLayout()
        vlayout = QtWidgets.QVBoxLayout()

        self.ui.setLayout(hlayout)

        self.test_array_model = ArrayLQ_QTableModel(
            self.settings.test_array, col_names=["Center", "FWHM", "Amplitude"]
        )
        self.tableView1 = QtWidgets.QTableView()
        self.tableView1.setModel(self.test_array_model)
        vlayout.addWidget(self.tableView1)

        # repeat above
        self.tableView2 = QtWidgets.QTableView()
        self.tableView2.setModel(self.test_array_model)
        vlayout.addWidget(self.tableView2)

        # no header
        self.test_array_model3 = ArrayLQ_QTableModel(self.settings.test_array)
        self.tableView3 = QtWidgets.QTableView()
        # self.tableView3.horizontalHeader().hide()
        self.tableView3.setModel(self.test_array_model3)
        vlayout.addWidget(self.tableView3)

        self.settings.New(
            "test_array4",
            dtype=float,
            is_array=True,
            ro=False,
            fmt="%1.2f",
            initial=[1, 2, 3],
        )
        self.test_array_model4 = ArrayLQ_QTableModel(self.settings.test_array4 )
        self.tableView4 = QtWidgets.QTableView()
        self.tableView4.setModel(self.test_array_model4)
        vlayout.addWidget(self.tableView4)

        self.test_array_model5 = ArrayLQ_QTableModel(self.settings.test_array4 , transpose=True)
        self.tableView5 = QtWidgets.QTableView()
        self.tableView5.setModel(self.test_array_model5)
        vlayout.addWidget(self.tableView5)

        for dtype in [str, bool, int]:
            lq_name = 'test_array_{}'.format(dtype.__name__)
            lq = self.settings.New(
                lq_name, dtype=dtype, is_array=True, ro=False, initial=[0, 1, "20", 0]
            )

            tableModel = ArrayLQ_QTableModel(lq, row_names= [dtype.__name__,], fmt=lq.fmt, transpose=True) 
            tableView = QtWidgets.QTableView()
            tableView.setModel(tableModel)
            vlayout.addWidget(tableView)

        #  int does not round
        self.settings.New("test_int", dtype=int, initial=124)

        hlayout.addWidget(new_tree((self,), ["app", ""]))
        hlayout.addLayout(vlayout)
        self.settings_ui = self.settings.New_UI()
        hlayout.addWidget(self.settings_ui)

        self.ui.show()
        # self.console_widget.show()

        self.load_ini_button = QtWidgets.QPushButton("Load INI file")
        vlayout.addWidget(self.load_ini_button)
        self.save_ini_button = QtWidgets.QPushButton("Save INI file")
        vlayout.addWidget(self.save_ini_button)
        self.load_ini_button = QtWidgets.QPushButton("Load saved INI file")
        vlayout.addWidget(self.load_ini_button)

        self.load_ini_button.clicked.connect(
            partial(self.settings_load_ini, fname="lq_array_test.ini")
        )
        self.save_ini_button.clicked.connect(
            partial(self.settings_save_ini, fname="lq_array_test_saved.ini")
        )
        self.load_ini_button.clicked.connect(
            partial(self.settings_load_ini, fname="lq_array_test_saved.ini")
        )


if __name__ == '__main__':
    import sys

    app = LQArrayTestApp(sys.argv)
    app.exec_()
