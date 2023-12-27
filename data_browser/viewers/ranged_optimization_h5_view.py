"""
Created on Jul 25, 2021

@author: Benedikt Ursprung
"""
import pyqtgraph as pg
import h5py
from ScopeFoundry.data_browser import DataBrowserView

MEASURE_NAMES = ("auto_focus", "ranged_optimization")


class RangedOptimizationH5View(DataBrowserView):
    name = "ranged_optimization_h5"

    def is_file_supported(self, fname):
        # ADD other ranged optimization here
        for measure_name in MEASURE_NAMES:
            if measure_name + ".h5" in fname:
                self.measure_name = measure_name
                return True
        return False

    def setup(self):
        self.ui = plot_widget = pg.GraphicsLayoutWidget()

        self.axes = plot_widget.addPlot()
        self.axes.setLabel("left", "f(z)")
        self.axes.setLabel("bottom", "z")
        self.line_coarse = self.axes.plot(y=[0, 2, 1, 3, 2])
        self.line_fine = self.axes.plot(y=[0, 2, 1, 3, 2], pen="r")

        # indicator lines
        self.line_z_original = pg.InfiniteLine(
            movable=False,
            pen="b",
            label="original position: {value:0.6f}",
            labelOpts={
                "color": "b",
                "movable": True,
                "position": 0.15,
                "fill": (200, 200, 200, 200),
            },
        )
        self.line_z0_coarse = pg.InfiniteLine(
            movable=False,
            pen=(200, 200, 200),
            label="coarse optimized: {value:0.6f}",
            labelOpts={
                "color": (200, 200, 200),
                "movable": True,
                "position": 0.30,
                "fill": (200, 200, 200, 60),
            },
        )
        self.line_z0_fine = pg.InfiniteLine(
            movable=False,
            pen="r",
            label="fine optimized: {value:0.6f}",
            labelOpts={
                "color": "r",
                "movable": True,
                "position": 0.45,
                "fill": (200, 200, 200, 80),
            },
        )
        self.axes.addItem(self.line_z_original, ignoreBounds=True)
        self.axes.addItem(self.line_z0_coarse, ignoreBounds=True)
        self.axes.addItem(self.line_z0_fine, ignoreBounds=True)

    def on_change_data_filename(self, fname=None):
        with h5py.File(fname, "r") as file:
            group = file[f"measurement/{self.measure_name}"]

            self.axes.setTitle(self.measure_name)
            self.line_coarse.setData(group["z_coarse"][:], group["f_coarse"][:])
            self.line_z0_fine.setPos(group["z0_coarse"][()])
            self.line_z_original.setPos(group["z_original"][()])

            has_fine = bool(group["settings"].attrs["use_fine_optimization"])
            self.line_z0_fine.setVisible(has_fine)
            self.line_fine.setVisible(has_fine)
            if has_fine:
                self.line_fine.setData(group["z_fine"][:], group["f_fine"][:])
                self.line_z0_fine.setPos(group["z0_fine"][()])

            try:
                S = group["settings"].attrs
                self.axes.setLabel("left", S["f"])
                self.axes.setLabel("bottom", S["z_read"])
            except KeyError as e:
                print(e)
