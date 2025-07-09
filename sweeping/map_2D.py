import numpy as np
import pyqtgraph as pg
from qtpy import QtCore

from .sweep_2D import Sweep2D


class Map2D(Sweep2D):

    name = "map_2d"

    def setup(self):
        self.img_items = []
        ans = super().setup()
        self.add_operation("clear_previous_scans", self.clear_previous_scans)
        self.settings["scan_mode"] = "nested"
        return ans

    def setup_figure(self):
        super().setup_figure()
        r1, r2 = self.get_ranges()
        r1.add_listener(self.connect_pos_widgets)
        r2.add_listener(self.connect_pos_widgets)

    def new_img_item(self, set_rect=True):
        """Create a new image item and add it to the plot."""
        self.img_item = img_item = pg.ImageItem()
        if set_rect:
            # Set the rectangle to cover the full range of the scan
            img_item.setRect(*self.calc_rect())
        self.img_items.append(img_item)
        self.axes.addItem(img_item)
        self.hist_lut.setImageItem(img_item)
        return img_item

    def pre_run(self):
        self.new_img_item()
        return super().pre_run()

    def mk_graph_widget(self):
        graph_layout = graph_widget = pg.GraphicsLayoutWidget()

        self.axes: pg.PlotItem = graph_layout.addPlot()
        self.axes.showGrid(x=True, y=True)
        self.axes.setAspectLocked(lock=True, ratio=1)

        self.hist_lut = pg.HistogramLUTItem()
        graph_layout.addItem(self.hist_lut)
        self.new_img_item(False)

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

        if not self.display_ready or not self.settings["plot_option"]:
            return

        dset = np.array(self.scan_data.data[self.settings["plot_option"]])
        img = dset.reshape(*(*self.scan_data.base_shape, -1)).mean(axis=-1)
        self.img_item.setImage(img, autoLevels=False)

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

    def calc_rect(self):
        x0, x1, y0, y1 = self.calc_imshow_extent()
        return (x0, y0, x1 - x0, y1 - y0)

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

    # def disconnect_pos_widgets(self):
    #     lq1, lq2 = self.current_positions_lqs
    #     lq1.disconnect_from_widget(self.ui.x_doubleSpinBox)
    #     lq2.disconnect_from_widget(self.ui.y_doubleSpinBox)

    def connect_pos_widgets(self):
        # self.disconnect_pos_widgets()

        lq1, lq2 = self.current_positions_lqs
        lq1.updated_value.connect(self.update_arrow_pos)
        lq2.updated_value.connect(self.update_arrow_pos)

    def update_arrow_pos(self):
        lq1, lq2 = self.current_positions_lqs
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

        f1, f2 = self.current_target_position_funcs
        f1(xc)
        f2(yc)

        print("on_update_pt_roi", x0, y0, xc, yc)

    def new_pt_pos(self, x, y):
        """override this method to handle new point position"""
        print("new_pt_pos", x, y)
