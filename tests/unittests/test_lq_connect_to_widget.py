import unittest

from pyqtgraph.widgets.SpinBox import SpinBox
from qtpy import QtWidgets

from ScopeFoundry.base_app.base_app import BaseApp
from ScopeFoundry.widgets import MinMaxQSlider


class LQConnectToWidgetTest(unittest.TestCase):

    def setUp(self):
        self.app = app = BaseApp([])
        self.settings = app.settings
        self.str = self.settings.New("str", str, initial="0")
        self.float = self.settings.New("float", float, vmin=-100, vmax=100)
        self.int = self.settings.New("int", int)
        self.bool = self.settings.New("bool", bool)
        self.choices = self.settings.New(
            "choices", int, choices=(("one", 1), ("two", 2), ("three", 3))
        )
        self._dir = self.settings.New("dir", "file", initial="test_dir", is_dir=True)

    def tearDown(self):
        # self.app.on_close()
        self.app.qtapp.exit()
        del self.app

    def test_qdouble_spinbox(self):
        wf = QtWidgets.QDoubleSpinBox()
        wi = QtWidgets.QDoubleSpinBox()

        wf.setValue(3.0)
        wi.setValue(3)

        # test on connection widget take lq value
        self.float.connect_to_widget(wf)
        self.int.connect_to_widget(wi)
        self.assertEqual(wf.value(), 0.0)
        self.assertEqual(wi.value(), 0)

        # lq to widget
        self.float.update_value(1.0)
        self.int.update_value(1.0)
        self.assertEqual(wf.value(), 1)
        self.assertEqual(wf.value(), 1)

        # widget to lq
        wf.setValue(2)
        wi.setValue(2)
        self.assertEqual(self.float.value, 2)
        self.assertEqual(self.int.value, 2)

    def test_pyqtgraph_spinbox(self):
        wf = SpinBox()
        wi = SpinBox()

        wf.setValue(3.0)
        wi.setValue(3)

        # test on connection widget take lq value
        self.float.connect_to_widget(wf)
        self.int.connect_to_widget(wi)
        self.assertEqual(wf.value(), 0.0)
        self.assertEqual(wi.value(), 0)

        # lq to widget
        self.float.update_value(1.0)
        self.int.update_value(1.0)
        self.assertEqual(wf.value(), 1)
        self.assertEqual(wf.value(), 1)

        # widget to lq
        wf.setValue(2)
        wi.setValue(2)
        self.assertEqual(self.float.value, 2)
        self.assertEqual(self.int.value, 2)

    def test_qlabel(self):
        ws = QtWidgets.QLabel()
        wf = QtWidgets.QLabel()
        wi = QtWidgets.QLabel()

        ws.setText("3")
        wf.setText("3")
        wi.setText("3")

        # test on connection widget take lq value
        self.str.connect_to_widget(ws)
        self.float.connect_to_widget(wf)
        self.int.connect_to_widget(wi)
        self.assertEqual(ws.text(), "0")
        self.assertEqual(wf.text(), "0")
        self.assertEqual(wi.text(), "0")

        # lq to widget
        self.str.update_value("1")
        self.float.update_value(1.1)
        self.int.update_value(1)
        self.assertEqual(ws.text(), "1")
        self.assertEqual(wf.text(), "1.1")
        self.assertEqual(wi.text(), "1")

        # widget to lq
        # NA

    def test_qline_edit(self):
        ws = QtWidgets.QLineEdit()
        wf = QtWidgets.QLineEdit()
        wi = QtWidgets.QLineEdit()

        ws.setText("3")
        wf.setText("3")
        wi.setText("3")

        # test on connection widget take lq value
        self.str.connect_to_widget(ws)
        self.float.connect_to_widget(wf)
        self.int.connect_to_widget(wi)
        self.assertEqual(ws.text(), "0")
        self.assertEqual(wf.text(), "0")
        self.assertEqual(wi.text(), "0")

        # lq to widget
        self.str.update_value("1")
        self.float.update_value(1.1)
        self.int.update_value(1)
        self.assertEqual(ws.text(), "1")
        self.assertEqual(wf.text(), "1.1")
        self.assertEqual(wi.text(), "1")

        # widget to lq
        ws.setText("2")
        wf.setText("2")
        wi.setText("2")
        ws.editingFinished.emit()
        wf.editingFinished.emit()
        wi.editingFinished.emit()
        self.assertEqual(self.str.value, "2")
        self.assertEqual(self.float.value, 2.0)
        self.assertEqual(self.int.value, 2)

    def test_q_plain_text_edit(self):

        ws = QtWidgets.QPlainTextEdit()
        ws.document().setPlainText("3")

        # test on connection widget take lq value
        self.str.connect_to_widget(ws)
        self.assertEqual(ws.document().toPlainText(), "0")

        # lq to widget
        self.str.update_value("1")
        self.assertEqual(ws.document().toPlainText(), "1")

        # widget to lq
        ws.document().setPlainText("2")
        self.assertEqual(self.str.value, "2")

    def test_check_box(self):
        wb = QtWidgets.QCheckBox()

        # print("checkbox1")
        wb.setChecked(True)

        # test on connection widget take lq value
        self.bool.connect_to_widget(wb)
        self.assertEqual(wb.isChecked(), False)

        # lq to widget
        # print("checkbox2")

        self.bool.update_value(True)
        self.assertEqual(wb.isChecked(), True)

        # widget to lq
        # print("checkbox3")

        wb.setChecked(False)

        # TODO The fact that emit is required controversial. Can one also check/uncheck without clicking?
        wb.clicked.emit()
        self.assertEqual(self.bool.value, False)

        # print("checkbox4")
        wb.setChecked(True)
        wb.clicked.emit(True)
        self.assertEqual(self.bool.value, True)

    def test_qcombo_box(self):
        wc = QtWidgets.QComboBox()

        wc.clear()
        wc.addItem("-1", -1)
        wc.addItem("-2", -2)
        wc.setCurrentIndex(1)

        # test on connection widget take lq value
        self.choices.connect_to_widget(wc)
        self.assertEqual(wc.currentData(), 1)

        ## potentially too strong of a test.
        self.assertEqual(wc.currentIndex(), 0)

        # lq to widget
        self.choices.update_value(1)
        self.assertEqual(wc.currentData(), 1)

        # widget to lq
        wc.setCurrentIndex(2)
        self.assertEqual(self.choices.value, 3)

    def test_qslider_int_non_overflow(self):
        lq = self.settings.New("int2", int, vmin=-100, vmax=100)

        wi = QtWidgets.QSlider()
        wi.setValue(3)

        # test on connection widget take lq value
        lq.connect_to_widget(wi)
        self.assertEqual(wi.value(), 0.0)

        # lq to widget
        lq.update_value(1)
        self.assertEqual(wi.value(), 1)

        # widget to lq
        wi.setValue(2)
        self.assertEqual(lq.value, 2)

    def test_qslider_int_overflow(self):
        # falls back to act like a float
        wi = QtWidgets.QSlider()
        wi.setValue(int(1000))

        lq = self.int

        # test on connection widget take lq value
        lq.connect_to_widget(wi)
        self.assertAlmostEqual(lq._transform_from_slider(wi.value()), 0.0)

        # lq to widget
        lq.update_value(int(1e11))
        self.assertAlmostEqual(
            lq._transform_from_slider(wi.value()) / 1e12, int(1e11) / 1e12
        )

        # widget to lq
        wi.setValue(lq._transform_to_slider(2e11))
        self.assertAlmostEqual(lq.value / 1e12, 2e11 / 1e12)

    def test_qslider_float(self):
        wf = QtWidgets.QSlider()
        wf.setValue(3)

        # test on connection widget take lq value
        self.float.connect_to_widget(wf)
        self.assertAlmostEqual(self.float._transform_from_slider(wf.value()), 0.0)

        # lq to widget
        self.float.update_value(1.0)
        self.assertAlmostEqual(self.float._transform_from_slider(wf.value()), 1.0)

        # widget to lq
        wf.setValue(self.float._transform_to_slider(2))
        self.assertAlmostEqual(self.float.value, 2)

    def test_min_max_slider(self):
        wf = MinMaxQSlider()
        wi = MinMaxQSlider()

        wf.update_value(3.0)
        wi.update_value(3)

        # test on connection widget take lq value
        self.float.connect_to_widget(wf)
        self.int.connect_to_widget(wi)
        self.assertEqual(wf.val, 0.0)
        self.assertEqual(wi.val, 0.0)

        # lq to widget
        self.float.update_value(1.0)
        self.int.update_value(1)
        self.assertEqual(wf.val, 1)
        self.assertEqual(wi.val, 1)

        # widget to lq
        wf.update_value(2)
        wi.update_value(2)
        self.assertEqual(self.float.value, 2)
        self.assertEqual(self.int.value, 2)

    def test_connect_to_file_widget(self):
        wdir = QtWidgets.QLineEdit()
        browseButton = QtWidgets.QPushButton("...")

        # test on connection widget take lq value
        wdir.setText("3")
        self._dir.connect_to_browse_widgets(wdir, browseButton)
        self.assertEqual(wdir.text(), "test_dir")

        # lq to widget
        self._dir.update_value("1")
        self.assertEqual(wdir.text(), "1")

        # widget to lq
        wdir.setText("2")
        wdir.editingFinished.emit()
        self.assertEqual(self._dir.value, "2")


class MyBaseApp(BaseApp):

    def __init__(self, argv, **kwargs):
        super().__init__(argv, **kwargs)

        lq = self.settings.New("test_lq", float, 33, "Hz", vmin=10, vmax=133)
        # lq = self.settings.New("test_lq", int, 33, "Hz", vmin=10, vmax=133)

        # w = MinMaxQSlider("test")
        w = QtWidgets.QSlider()
        lq.connect_to_widget(w)
        s = self.settings.New_UI(title="settings")

        self.ui = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(self.ui)
        layout.addWidget(w)
        layout.addWidget(s)
        self.ui.show()


if __name__ == "__main__":
    import sys

    app = MyBaseApp([])
    sys.exit(app.exec_())
    # unittest.main()
