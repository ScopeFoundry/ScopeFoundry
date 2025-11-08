import h5py
import numpy as np
import pyqtgraph as pg
from qtpy import QtCore, QtWidgets

from .sweep_2D import Sweep2D


class Map2D(Sweep2D):

    name = "map_2d"

    def __init__(
        self,
        app,
        name=None,
        collectors=(),
        actuators=(),
        actuator_names="12",
        range_n_intervals=(1, 1),
        n_read_any_settings=2,
        n_any_measurements=2,
        invert_h=False,
        invert_v=False,
    ):
        super().__init__(
            app,
            name,
            collectors,
            actuators,
            actuator_names,
            range_n_intervals,
            n_read_any_settings,
            n_any_measurements,
        )
        self.invert_h = invert_h
        self.invert_v = invert_v

    def setup(self):
        self.img_items = []
        ans = super().setup()
        self.add_operation(
            "clear_previous_scans",
            self.clear_previous_scans,
            icon_path=self.app.qtapp.style().standardIcon(
                QtWidgets.QStyle.SP_DialogDiscardButton
            ),
        )
        self.add_operation(
            "load image from h5",
            self.load_img_from_h5,
            icon_path=self.app.qtapp.style().standardIcon(QtWidgets.QStyle.SP_FileIcon),
        )
        self.settings["scan_mode"] = "nested"
        self._current_arrow_lqs = ()

    def setup_figure(self):
        super().setup_figure()
        self.settings.get_lq("actuator_1").add_listener(self.connect_pos_widgets)
        self.settings.get_lq("actuator_2").add_listener(self.connect_pos_widgets)
        self.axes.getViewBox().invertX(self.invert_h)
        self.axes.getViewBox().invertY(self.invert_v)
        self.run_layout.addWidget(self.operations.new_button("load image from h5"))
        self.run_layout.addWidget(self.operations.new_button("clear_previous_scans"))

    def new_img_item(self):
        """Create a new image item and add it to the plot."""
        self.img_item = img_item = pg.ImageItem()
        self.img_items.append(img_item)
        self.axes.addItem(img_item)
        self.hist_lut.setImageItem(img_item)
        return img_item

    def load_img_from_h5(self, fname=None):

        if fname is None:
            fname, _ = QtWidgets.QFileDialog.getOpenFileName(
                parent=None,
                caption=f"Open File",
                filter=";;".join(
                    [f"{self.name} (*{self.name}*.h5)", "All Files (*.h5)"]
                ),
            )

        self.app.settings_load_h5(fname, True, False)

        with h5py.File(fname, "r") as file:
            m = file[f"measurement/{self.name}"]
            dset_names = []
            for k, v in m.items():
                if k.endswith("_raw"):
                    continue
                if not isinstance(v, h5py.Dataset):
                    continue
                if k in (
                    "positions",
                    "indices",
                    "range_1",
                    "range_2",
                    "imshow_extent",
                    "range_extent",
                    "read_positions",
                ):
                    continue
                if len(v.shape) < 2:
                    continue
                dset_names.append(k)

        dlg = ComboSelectDialog(dset_names)
        if not dlg.exec_():
            return

        selected_dset = dlg.get_value()

        with h5py.File(fname, "r") as file:
            m = file[f"measurement/{self.name}"]
            imshow_extent = m["imshow_extent"][:]
            dset = m[selected_dset][:]

        x0, x1, y0, y1 = imshow_extent
        rect = QtCore.QRectF(x0, y0, x1 - x0, (y1 - y0))

        img_item = self.new_img_item()
        img = dset.mean(axis=tuple(np.arange(len(dset.shape))[2:]))

        img_item.setImage(img, rect=rect)

    def pre_run(self):
        self.new_img_item()
        return super().pre_run()

    def mk_plot_options_widget(self):
        plot_option_widget = QtWidgets.QWidget()
        plot_option_layout = QtWidgets.QHBoxLayout(plot_option_widget)
        plot_option_layout.addWidget(self.settings.New_UI(["data_set"]))
        return plot_option_widget

    def mk_graph_widget(self):
        graph_layout = graph_widget = pg.GraphicsLayoutWidget()

        self.axes: pg.PlotItem = graph_layout.addPlot()
        self.axes.showGrid(x=True, y=True)
        self.axes.setAspectLocked(lock=True, ratio=1)

        self.hist_lut = pg.HistogramLUTItem()
        graph_layout.addItem(self.hist_lut)
        self.new_img_item()

        self.scan_roi = pg.ROI([0, 0], [1, 1], movable=True)
        self.scan_roi.addScaleHandle([1, 1], [0, 0])
        self.scan_roi.addScaleHandle([0, 0], [1, 1])
        self.update_scan_roi()
        self.scan_roi.sigRegionChangeFinished.connect(self.on_mouse_update_scan_roi)
        self.axes.addItem(self.scan_roi)
        for r in self.get_ranges():
            r.add_listener(self.update_scan_roi)
        self.axes.scene().sigMouseMoved.connect(self.on_mouse_moved)

        # Point ROI
        self.circ_roi_size = 0.1
        self.pt_roi = pg.CircleROI(
            (0, 0), (self.circ_roi_size, self.circ_roi_size), movable=True, pen=(0, 9)
        )
        h = self.pt_roi.addTranslateHandle((0.5, 0.5))
        h.pen = pg.mkPen("r")
        h.update()
        self.axes.addItem(self.pt_roi)
        self.pt_roi.removeHandle(0)
        self.pt_roi.sigRegionChangeFinished[object].connect(self.on_update_pt_roi)

        # Current position arrow
        self.current_pos_arrow = pg.ArrowItem()
        self.current_pos_arrow.setZValue(100)
        self.axes.addItem(self.current_pos_arrow)

        return graph_widget

    def update_display(self):
        self.update_status_display()

        if not self.display_ready or not self.settings["data_set"]:
            return

        dset = np.array(self.scan_data.data[self.settings["data_set"]])
        img = dset.reshape(*(*self.scan_data.base_shape, -1)).mean(axis=-1)
        self.img_item.setImage(img, rect=self.calc_rect())

    def get_ranges(self):
        r1 = self.settings.ranges["range_1"]
        r2 = self.settings.ranges["range_2"]
        return r1, r2

    def calc_range_extent(self):
        r1, r2 = self.get_ranges()
        return [r1.min.val, r1.max.val, r2.min.val, r2.max.val]

    def calc_imshow_extent(self):
        r1, r2 = self.get_ranges()
        return [
            r1.min.val - 0.5 * r1.step.val,
            r1.max.val + 0.5 * r1.step.val,
            r2.min.val - 0.5 * r2.step.val,
            r2.max.val + 0.5 * r2.step.val,
        ]

    def calc_rect(self) -> QtCore.QRectF:
        x0, x1, y0, y1 = self.calc_imshow_extent()
        print(x0, y0, x1 - x0, (y1 - y0))
        return QtCore.QRectF(x0, y0, x1 - x0, (y1 - y0))

    def on_mouse_update_scan_roi(self):
        x0, y0 = self.scan_roi.pos()
        w, h = self.scan_roi.size()

        r1, r2 = self.get_ranges()
        r1.center.update_value(x0 + w / 2)
        r2.center.update_value(y0 + h / 2)
        r1.span.update_value(w - r1.step.val)
        r2.span.update_value(h - r2.step.val)

        self.update_scan_roi()

    def update_scan_roi(self):
        self.log.debug("update_scan_roi")
        x0, x1, y0, y1 = self.calc_imshow_extent()
        self.scan_roi.blockSignals(True)
        self.scan_roi.setPos((x0, y0, 0))
        self.scan_roi.setSize((x1 - x0, y1 - y0, 0))
        self.scan_roi.blockSignals(False)

    def disconnect_pos_widgets(self):
        if self._current_arrow_lqs:
            lq1, lq2 = self._current_arrow_lqs
            lq1.updated_value.disconnect(self._con_1)
            lq2.updated_value.disconnect(self._con_2)
            self._current_arrow_lqs = ()

    def connect_pos_widgets(self):
        print("connect_pos_widgets")
        self.disconnect_pos_widgets()

        defs = list(self.get_current_actuators_defs())

        read_def_1 = defs[0][1]
        read_def_2 = defs[1][1]

        print(read_def_1, read_def_2)

        lq_1 = self.app.get_lq(read_def_1) if isinstance(read_def_1, str) else None
        lq_2 = self.app.get_lq(read_def_2) if isinstance(read_def_2, str) else None

        if lq_1 is None or lq_2 is None:
            self._con_1 = None
            self._con_2 = None
            self._current_arrow_lqs = ()
        else:
            self._con_1 = lq_1.updated_value.connect(self.update_arrow_pos)
            self._con_2 = lq_2.updated_value.connect(self.update_arrow_pos)
            self._current_arrow_lqs = (lq_1, lq_2)

    def update_arrow_pos(self):
        if not self._current_arrow_lqs:
            return
        lq1, lq2 = self._current_arrow_lqs
        self.current_pos_arrow.setPos(lq1.val, lq2.val)

    def on_goto_position(self):
        pass

    def on_mouse_moved(self, evt):
        pt = self.axes.vb.mapSceneToView(evt)
        self.axes.setTitle(f"H {pt.x():+02.2f}, V {pt.y():+02.2f}")
        # self.pos_label.setText(f"H {pt.x():+02.2f}, V {pt.y():+02.2f}")

    def post_scan(self):
        H = self.scan_data.h5_meas_group
        H.create_dataset("imshow_extent", data=self.calc_imshow_extent())
        H.create_dataset("range_extent", data=self.calc_range_extent())

    def clear_previous_scans(self):
        for img_item in self.img_items:
            self.axes.removeItem(img_item)
            img_item.deleteLater()
        self.img_items = [self.img_item]

    def clear_qt_attr(self, attr_name):
        if hasattr(self, attr_name):
            attr = getattr(self, attr_name)
            attr.deleteLater()
            del attr

    def on_update_pt_roi(self, roi=None):
        if roi is None:
            roi = self.circ_roi
        roi_state = roi.saveState()
        x0, y0 = roi_state["pos"]
        xc = x0 + self.circ_roi_size / 2.0
        yc = y0 + self.circ_roi_size / 2.0

        f1, f2 = self.get_current_target_position_funcs()
        f1(xc)
        f2(yc)

    def new_pt_pos(self, x, y):
        """override this method to handle new point position"""
        print("new_pt_pos", x, y)


class ComboSelectDialog(QtWidgets.QDialog):
    def __init__(self, items, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Data set to display")
        self.layout = QtWidgets.QVBoxLayout(self)

        self.combo = QtWidgets.QComboBox(self)
        self.combo.addItems(items)
        self.layout.addWidget(self.combo)

        self.select_btn = QtWidgets.QPushButton("Select data set", self)
        self.layout.addWidget(self.select_btn)

        self.select_btn.clicked.connect(self.accept)

    def get_value(self):
        return self.combo.currentText()
