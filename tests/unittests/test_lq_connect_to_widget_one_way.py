import unittest

from pyqtgraph.widgets.SpinBox import SpinBox
from qtpy import QtWidgets

from ScopeFoundry.base_app.base_app import BaseApp
from ScopeFoundry.tests.unittests.unittest_helpers import close_app_widgets
from ScopeFoundry.widgets import MinMaxQSlider


class LQConnectToWidgetOneWayTest(unittest.TestCase):

    def setUp(self):
        self.app = app = BaseApp([])
        self.addCleanup(close_app_widgets, self.app)
        self.settings = app.settings
        self.str = self.settings.New("str", str, initial="0")
        self.float = self.settings.New("float", float, vmin=-100, vmax=100)
        self.int = self.settings.New("int", int)
        self.bool = self.settings.New("bool", bool)
        self.choices = self.settings.New(
            "choices", int, choices=(("one", 1), ("two", 2), ("three", 3))
        )

    def test_qdouble_spinbox(self):
        wf = QtWidgets.QDoubleSpinBox()
        wi = QtWidgets.QDoubleSpinBox()
        wf.setValue(3)
        wi.setValue(3)

        self.float.connect_to_widget_one_way(wf)
        self.int.connect_to_widget_one_way(wi)
        self.assertEqual(wf.value(), 0)
        self.assertEqual(wi.value(), 0)
        self.assertEqual(len(self.float.prev_vals), 0)

        self.float.update_value(1)
        self.int.update_value(1)
        self.assertEqual(wf.value(), 1)
        self.assertEqual(wi.value(), 1)

        wf.setValue(2)
        wi.setValue(2)
        self.assertEqual(self.float.value, 1)
        self.assertEqual(self.int.value, 1)

    def test_pyqtgraph_spinbox(self):
        wf = SpinBox()
        wi = SpinBox()
        wf.setValue(3)
        wi.setValue(3)

        self.float.connect_to_widget_one_way(wf)
        self.int.connect_to_widget_one_way(wi)
        self.assertEqual(wf.value(), 0)
        self.assertEqual(wi.value(), 0)

        self.float.update_value(1)
        self.int.update_value(1)
        self.assertEqual(wf.value(), 1)
        self.assertEqual(wi.value(), 1)

        wf.setValue(2)
        wi.setValue(2)
        self.assertEqual(self.float.value, 1)
        self.assertEqual(self.int.value, 1)

    def test_qlabel(self):
        ws = QtWidgets.QLabel()
        wf = QtWidgets.QLabel()
        wi = QtWidgets.QLabel()
        ws.setText("3")
        wf.setText("3")
        wi.setText("3")

        self.str.connect_to_widget_one_way(ws)
        self.float.connect_to_widget_one_way(wf)
        self.int.connect_to_widget_one_way(wi)
        self.assertEqual(ws.text(), "0")
        self.assertEqual(wf.text(), "0")
        self.assertEqual(wi.text(), "0")

        self.str.update_value("1")
        self.float.update_value(1.1)
        self.int.update_value(1)
        self.assertEqual(ws.text(), "1")
        self.assertEqual(wf.text(), "1.1")
        self.assertEqual(wi.text(), "1")

    def test_qline_edit(self):
        widget = QtWidgets.QLineEdit()
        widget.setText("3")

        self.str.connect_to_widget_one_way(widget)
        self.assertEqual(widget.text(), "0")

        self.str.update_value("1")
        self.assertEqual(widget.text(), "1")

        widget.setText("2")
        widget.editingFinished.emit()
        self.assertEqual(self.str.value, "1")

    def test_qtext_edit(self):
        widget = QtWidgets.QTextEdit()
        widget.setText("3")

        self.str.connect_to_widget_one_way(widget)
        self.assertEqual(widget.toPlainText(), "0")

        self.str.update_value("1")
        self.assertEqual(widget.toPlainText(), "1")

        widget.setText("2")
        self.assertEqual(self.str.value, "1")

    def test_q_plain_text_edit(self):
        widget = QtWidgets.QPlainTextEdit()
        widget.setPlainText("3")

        self.str.connect_to_widget_one_way(widget)
        self.assertEqual(widget.toPlainText(), "0")

        self.str.update_value("1")
        self.assertEqual(widget.toPlainText(), "1")

        widget.setPlainText("2")
        self.assertEqual(self.str.value, "1")

    def test_check_box(self):
        widget = QtWidgets.QCheckBox()
        widget.setChecked(True)

        self.bool.connect_to_widget_one_way(widget)
        self.assertFalse(widget.isChecked())

        self.bool.update_value(True)
        self.assertTrue(widget.isChecked())

        widget.click()
        self.assertTrue(self.bool.value)

    def test_qcombo_box(self):
        widget = QtWidgets.QComboBox()
        widget.addItem("old", -1)
        widget.setCurrentIndex(0)

        self.choices.connect_to_widget_one_way(widget)
        self.assertEqual(widget.currentData(), 1)
        self.assertEqual(widget.currentIndex(), 0)

        self.choices.update_value(2)
        self.assertEqual(widget.currentData(), 2)

        widget.setCurrentIndex(2)
        self.assertEqual(self.choices.value, 2)

    def test_qslider_int(self):
        lq = self.settings.New("slider", int, initial=5, vmin=-100, vmax=100)
        widget = QtWidgets.QSlider()
        widget.setValue(3)

        lq.connect_to_widget_one_way(widget)
        self.assertEqual(widget.value(), 5)
        self.assertEqual(len(lq.prev_vals), 0)

        lq.update_value(7)
        self.assertEqual(widget.value(), 7)

        widget.setValue(8)
        self.assertEqual(lq.value, 7)

    def test_qslider_float(self):
        widget = QtWidgets.QSlider()
        widget.setValue(3)

        self.float.connect_to_widget_one_way(widget)
        self.assertAlmostEqual(self.float._transform_from_slider(widget.value()), 0)

        self.float.update_value(1)
        self.assertAlmostEqual(self.float._transform_from_slider(widget.value()), 1)

        widget.setValue(self.float._transform_to_slider(2))
        self.assertEqual(self.float.value, 1)

    def test_qslider_int_overflow(self):
        max_4byte_int = (1 << 31) - 1
        lq = self.int
        widget = QtWidgets.QSlider()
        widget.setValue(1000)

        lq.connect_to_widget_one_way(widget)
        self.assertAlmostEqual(lq._transform_from_slider(widget.value()), 0)

        lq.update_value(max_4byte_int)
        self.assertAlmostEqual(
            lq._transform_from_slider(widget.value()) / 1e12, max_4byte_int / 1e12
        )

        widget.setValue(lq._transform_to_slider(max_4byte_int // 2))
        self.assertEqual(lq.value, max_4byte_int)

    def test_min_max_slider(self):
        wf = MinMaxQSlider()
        wi = MinMaxQSlider()
        wf.update_value(3)
        wi.update_value(3)

        self.float.connect_to_widget_one_way(wf)
        self.int.connect_to_widget_one_way(wi)
        self.assertEqual(wf.val, 0)
        self.assertEqual(wi.val, 0)

        self.float.update_value(1)
        self.int.update_value(1)
        self.assertEqual(wf.val, 1)
        self.assertEqual(wi.val, 1)

        wf.update_value(2)
        wi.update_value(2)
        self.assertEqual(self.float.value, 1)
        self.assertEqual(self.int.value, 1)

    def test_qprogress_bar(self):
        lq = self.settings.New("progress", int, initial=5, vmin=0, vmax=100)
        widget = QtWidgets.QProgressBar()
        widget.setRange(0, 100)
        widget.setValue(3)

        lq.connect_to_widget_one_way(widget)
        self.assertEqual(widget.value(), 5)

        lq.update_value(10)
        self.assertEqual(widget.value(), 10)

    def test_qlcd_number(self):
        lq = self.settings.New("lcd", int, initial=5)
        widget = QtWidgets.QLCDNumber()
        widget.display(3)

        lq.connect_to_widget_one_way(widget)
        self.assertEqual(widget.value(), 5)

        lq.update_value(10)
        self.assertEqual(widget.value(), 10)


if __name__ == "__main__":
    unittest.main()
