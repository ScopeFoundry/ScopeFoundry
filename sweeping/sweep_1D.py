from typing import Sequence, Union

import numpy as np
import pyqtgraph as pg
from qtpy import QtWidgets

from ScopeFoundry import BaseMicroscopeApp
from ScopeFoundry.scanning.actuators import (
    ActuatorDefinitions,
)

from .collector import Collector
from .sweep_nd_base import SweepNDBase
from .sweep_1D_modes import (
    SCAN_MODES,
    SCAN_MODES_DESCRIPTION,
    mk_ranges_consistent,
    mk_positions_gen,
    mk_data_shape,
    mk_indices_gen,
)

SLICE_COLORS = ["red", "blue", "green", "orange", "purple", "cyan", "magenta", "yellow"]


class Sweep1DSlicer:

    def __init__(self, measurement: SweepNDBase):
        self.slice_functions = {"identity": (self.identity, "(CURRENT)")}
        self.measurement = measurement
        self.settings = self.measurement.settings
        self.settings.New("h_slice_width", int, initial=3, vmin=0, unit="data points")
        self.settings.New(
            "h_slice_function",
            str,
            initial="identity",
            choices=tuple(self.slice_functions.keys()),
            description="Function applied to the selected image before horizontal slicing.",
        )
        self.h_slice_lines = []
        self.h_slice_curves = []
        self.v_slice_lines = []
        self.v_slice_curves = []
        self._view_ranges = {}
        self._last_position_representation = None
        self.settings.get_lq("h_slice_width").add_listener(self.update_h_slices)
        self.settings.get_lq("h_slice_function").add_listener(self.update_h_slices)

    def register_slice_function(self, name, function, label="(CURRENT)"):
        """Register a function returning y-values for an h-slice."""
        if not callable(function):
            raise TypeError("slice function must be callable")

        self.slice_functions[name] = (function, label)
        self.settings.get_lq("h_slice_function").add_choices([name])

    def do_slice(self, dset_name, row_count, lower_index, upper_index):
        size, image_data = self.measurement.map_vertical_img(dset_name)
        return np.nanmean(image_data[:row_count, lower_index:upper_index], axis=1)

    def identity(self, row_count, lower_index, upper_index):
        return self.do_slice(
            self.settings["dataset"],
            row_count,
            lower_index,
            upper_index,
        )

    def mk_slice_widget(self):
        # Create a new container to add our slice controls
        container = QtWidgets.QWidget()
        container.setMinimumSize(1, 1)
        layout = QtWidgets.QVBoxLayout(container)

        # Add both slice plot widgets
        layout.addWidget(self.mk_h_slice_plot_widget())
        layout.addWidget(self.mk_v_slice_plot_widget())
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Create horizontal slice controls group
        h_slice_gb = QtWidgets.QGroupBox("Horizontal Slice Controls")
        h_slice_layout = QtWidgets.QHBoxLayout(h_slice_gb)
        h_slice_layout.setContentsMargins(6, 6, 6, 6)
        h_slice_layout.setSpacing(4)

        # Add horizontal slice button
        self.add_h_slice_btn = QtWidgets.QPushButton("Add H-Slice")
        self.add_h_slice_btn.setToolTip(
            "Add a horizontal slice line that appears in the horizontal slice plot"
        )
        self.add_h_slice_btn.clicked.connect(self.add_h_slice)
        h_slice_layout.addWidget(self.add_h_slice_btn)

        # Add show/hide horizontal slice plot button
        self.toggle_h_slice_plot_btn = QtWidgets.QPushButton("Show H-Plot")
        self.toggle_h_slice_plot_btn.setToolTip(
            "Show or hide the horizontal slice plot window"
        )
        self.toggle_h_slice_plot_btn.clicked.connect(self.toggle_h_slice_plot)
        h_slice_layout.addWidget(self.toggle_h_slice_plot_btn)

        # Add clear horizontal slices button
        self.clear_h_slices_btn = QtWidgets.QPushButton("Clear H-Slices")
        self.clear_h_slices_btn.setToolTip("Remove all horizontal slice lines")
        self.clear_h_slices_btn.clicked.connect(self.clear_h_slices)
        h_slice_layout.addWidget(self.clear_h_slices_btn)

        h_slice_layout.addWidget(QtWidgets.QLabel("Average:"))

        h_slice_layout.addWidget(
            self.settings.get_lq("h_slice_width").new_default_widget()
        )
        h_slice_layout.addWidget(QtWidgets.QLabel("Transform:"))
        h_slice_layout.addWidget(
            self.settings.get_lq("h_slice_function").new_default_widget()
        )
        layout.addWidget(h_slice_gb)

        # Create vertical slice controls group
        v_slice_gb = QtWidgets.QGroupBox("Vertical Slice Controls")
        v_slice_layout = QtWidgets.QHBoxLayout(v_slice_gb)
        v_slice_layout.setContentsMargins(6, 6, 6, 6)
        v_slice_layout.setSpacing(4)

        # Add vertical slice button
        self.add_v_slice_btn = QtWidgets.QPushButton("Add V-Slice")
        self.add_v_slice_btn.setToolTip(
            "Add a vertical slice line that appears in the vertical slice plot"
        )
        self.add_v_slice_btn.clicked.connect(self.add_v_slice)
        v_slice_layout.addWidget(self.add_v_slice_btn)

        # Add show/hide vertical slice plot button
        self.toggle_v_slice_plot_btn = QtWidgets.QPushButton("Show V-Plot")
        self.toggle_v_slice_plot_btn.setToolTip(
            "Show or hide the vertical slice plot window"
        )
        self.toggle_v_slice_plot_btn.clicked.connect(self.toggle_v_slice_plot)
        v_slice_layout.addWidget(self.toggle_v_slice_plot_btn)

        # Add clear vertical slices button
        self.clear_v_slices_btn = QtWidgets.QPushButton("Clear V-Slices")
        self.clear_v_slices_btn.setToolTip("Remove all vertical slice lines")
        self.clear_v_slices_btn.clicked.connect(self.clear_v_slices)
        v_slice_layout.addWidget(self.clear_v_slices_btn)

        layout.addWidget(v_slice_gb)
        return container

    def mk_h_slice_plot_widget(self):
        # Create the persistent slice plot window
        self.h_slice_plot_widget = pg.PlotWidget(title="Horizontal Slices")
        self.h_slice_plot_widget.showGrid(True, True)
        self.h_slice_plot_widget.resize(600, 300)

        # Initially hide the plot window
        self.h_slice_plot_widget.hide()

        return self.h_slice_plot_widget

    def mk_v_slice_plot_widget(self):
        # Create the persistent vertical slice plot window
        self.v_slice_plot_widget = pg.PlotWidget(title="Vertical Slices")
        self.v_slice_plot_widget.showGrid(True, True)
        self.v_slice_plot_widget.resize(600, 300)

        # Initially hide the plot window
        self.v_slice_plot_widget.hide()

        return self.v_slice_plot_widget

    def wrap_graph_widget(self, graph_widget):
        return self.wrap_with_slice_widget(graph_widget)

    def wrap_with_slice_widget(self, graph_widget):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(widget)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(graph_widget)
        self._slice_widget = self.mk_slice_widget()
        self._slice_widget.setVisible(
            self.settings["position_representation"] == "map_vertical"
        )

        layout.addWidget(self._slice_widget)
        self._slice_wrap_layout = layout
        self.update_position_representation()
        return widget

    def update_position_representation(self, representation=None):
        if not self.measurement.display_ready:
            return
        if representation is None:
            representation = self.settings["position_representation"]

        if representation != self._last_position_representation:
            view_box = self.measurement.axes.getViewBox()
            previous_representation = self._last_position_representation
            if previous_representation is not None:
                self._view_ranges[previous_representation] = view_box.viewRange()
            if representation in self._view_ranges:
                x_range, y_range = self._view_ranges[representation]
                view_box.setRange(xRange=x_range, yRange=y_range, padding=0)
            self._last_position_representation = representation

        show_slices = representation == "map_vertical"
        if hasattr(self, "_slice_widget"):
            self._slice_widget.setVisible(show_slices)
        for slice_line in self.h_slice_lines + self.v_slice_lines:
            slice_line.setVisible(show_slices)

    def set_compact(self, compact: bool) -> None:
        layout = self._slice_wrap_layout
        direction = (
            QtWidgets.QBoxLayout.Direction.TopToBottom
            if compact
            else QtWidgets.QBoxLayout.Direction.LeftToRight
        )
        layout.setDirection(direction)
        layout.setStretch(0, 2 if compact else 1)
        layout.setStretch(1, 1 if compact else 0)

    def add_h_slice(self):
        """Add a new horizontal slice line to the main plot"""

        self.settings["average_over_repetitions"] = True
        self.settings["position_representation"] = "map_vertical"

        if (
            not hasattr(self.measurement, "img_item")
            or not self.measurement.img_item.isVisible()
        ):
            return

        slice_number = len(self.h_slice_lines) + 1

        # Create colors for different slices
        color = SLICE_COLORS[(slice_number - 1) % len(SLICE_COLORS)]

        # Create a movable horizontal line
        slice_line = pg.InfiniteLine(
            angle=0,  # horizontal line
            movable=True,
            pen=pg.mkPen(color=color, width=2),
            label=f"H-Slice {slice_number}: {{value:0.3f}}",
            labelOpts={"color": "white", "movable": True, "fill": color},
        )

        # Position the line in the center of the current view range
        view_range = self.measurement.axes.getViewBox().viewRange()
        y_center = (view_range[1][0] + view_range[1][1]) / 2
        slice_line.setValue(y_center)

        # Add the line to the main plot
        self.measurement.axes.addItem(slice_line)
        self.h_slice_lines.append(slice_line)

        # Create a plot curve in the persistent plot window
        slice_curve = self.h_slice_plot_widget.plot(
            pen=pg.mkPen(color=color, width=2), name=f"H-Slice {slice_number}"
        )

        # Store curve info
        curve_info = {
            "line": slice_line,
            "curve": slice_curve,
            "slice_number": slice_number,
            "color": color,
        }
        self.h_slice_curves.append(curve_info)

        # Connect the line position change to update function
        slice_line.sigPositionChanged.connect(
            lambda _line: self.update_h_slice(curve_info)
        )

        # Show the slice plot window if it's hidden and we have slices
        self.update_h_slice_plot_visibility()

        # Initial update of the slice
        self.update_h_slice(curve_info)

    def add_v_slice(self):
        """Add a new vertical slice line to the main plot"""
        self.settings["average_over_repetitions"] = True
        self.settings["position_representation"] = "map_vertical"

        if (
            not hasattr(self.measurement, "img_item")
            or not self.measurement.img_item.isVisible()
        ):
            QtWidgets.QMessageBox.warning(
                None,
                "No Image",
                "Cannot add vertical slice: No image is currently displayed. "
                "Make sure an image is visible in the plot.",
            )
            return

        slice_number = len(self.v_slice_lines) + 1

        # Create colors for different slices
        color = SLICE_COLORS[(slice_number - 1) % len(SLICE_COLORS)]

        # Create a movable vertical line
        slice_line = pg.InfiniteLine(
            angle=90,  # vertical line
            movable=True,
            pen=pg.mkPen(color=color, width=2),
            label=f"V-Slice {slice_number}",
            labelOpts={"color": "white", "movable": True, "fill": color},
        )

        # Position the line in the center of the current view range
        view_range = self.measurement.axes.getViewBox().viewRange()
        x_center = (view_range[0][0] + view_range[0][1]) / 2
        slice_line.setValue(x_center)

        # Add the line to the main plot
        self.measurement.axes.addItem(slice_line)
        self.v_slice_lines.append(slice_line)

        # Create a plot curve in the persistent vertical plot window
        slice_curve = self.v_slice_plot_widget.plot(
            pen=pg.mkPen(color=color, width=2), name=f"V-Slice {slice_number}"
        )

        # Store curve info
        curve_info = {
            "line": slice_line,
            "curve": slice_curve,
            "slice_number": slice_number,
            "color": color,
        }
        self.v_slice_curves.append(curve_info)

        # Connect the line position change to update function
        slice_line.sigPositionChanged.connect(
            lambda _line: self.update_v_slice(curve_info)
        )

        # Show the vertical slice plot window if it's hidden and we have slices
        self.update_v_slice_plot_visibility()

        # Initial update of the slice
        self.update_v_slice(curve_info)

    def update_h_slice(self, curve_info):
        """Update the horizontal slice plot when the line is moved"""
        image_data = self.measurement.img_item.image
        if image_data is None:
            print("No image data available")
            return

        # get data index
        y_pos = curve_info["line"].value()
        c = self.settings["extent_control"]
        if c == "None":
            ys = np.arange(image_data.shape[1])
        elif c in self.measurement.scan_data.data:
            ys = self.measurement.scan_data.data[c].flatten()
        else:
            return

        jj = np.argmin(np.abs(ys - y_pos))
        half_width = int(self.settings["h_slice_width"] // 2)
        lower_index = max(0, jj - half_width)
        upper_index = min(len(ys), jj + half_width + 1)

        row_count = min(len(self.measurement.scan_data.positions), image_data.shape[0])
        x = np.asarray(self.measurement.scan_data.positions)[:row_count, 0]
        func, label = self.slice_functions[self.settings["h_slice_function"]]
        y = func(row_count, lower_index, upper_index)

        # point_count = min(len(x), len(y))
        # x = x[-point_count:]
        # y = y[-point_count:]

        curve_info["curve"].setData(x, y)

        self.h_slice_plot_widget.setLabel("bottom", self.settings["actuator_1"])
        if label == "(CURRENT)":
            label = self.settings["dataset"] or "Signal"
        self.h_slice_plot_widget.setLabel("left", label)

    def update_h_slices(self):
        for curve_info in self.h_slice_curves:
            self.update_h_slice(curve_info)

    def update_v_slice(self, curve_info):
        """Update the vertical slice plot when the line is moved"""
        image_data = self.measurement.img_item.image
        if image_data is None:
            print("No image data available")
            return

        # get data index
        x_pos = curve_info["line"].value()
        xs = np.array(self.measurement.scan_data.positions)[:, 0]
        ii = np.argmin(np.abs(xs - x_pos))

        # plot
        y = image_data[ii, :]
        extent_name = self.settings["extent_control"]
        if extent_name == "None" or extent_name not in self.measurement.scan_data.data:
            x = np.arange(image_data.shape[1])
        else:
            x = np.asarray(self.measurement.scan_data.data[extent_name]).flatten()
        point_count = min(len(x), len(y))
        x = x[:point_count]
        y = y[:point_count]
        curve_info["curve"].setData(x, y)
        self.v_slice_plot_widget.setLabel("bottom", extent_name)

    def clear_h_slices(self):
        """Remove all horizontal slice lines and curves"""
        # Remove all lines from the main plot
        for slice_line in self.h_slice_lines:
            self.measurement.axes.removeItem(slice_line)

        # Clear all curves from the slice plot
        self.h_slice_plot_widget.clear()

        # Clear the tracking lists
        self.h_slice_lines.clear()
        self.h_slice_curves.clear()

        # Update visibility
        self.update_h_slice_plot_visibility()

    def clear_v_slices(self):
        """Remove all vertical slice lines and curves"""
        # Remove all lines from the main plot
        for slice_line in self.v_slice_lines:
            self.measurement.axes.removeItem(slice_line)

        # Clear all curves from the vertical slice plot
        self.v_slice_plot_widget.clear()

        # Clear the tracking lists
        self.v_slice_lines.clear()
        self.v_slice_curves.clear()

        # Update visibility
        self.update_v_slice_plot_visibility()

    def toggle_h_slice_plot(self):
        """Show or hide the horizontal slice plot window"""
        if self.h_slice_plot_widget.isVisible():
            self.h_slice_plot_widget.hide()
            self.toggle_h_slice_plot_btn.setText("Show H-Plot")
        else:
            self.h_slice_plot_widget.show()
            self.toggle_h_slice_plot_btn.setText("Hide H-Plot")

    def toggle_v_slice_plot(self):
        """Show or hide the vertical slice plot window"""
        if self.v_slice_plot_widget.isVisible():
            self.v_slice_plot_widget.hide()
            self.toggle_v_slice_plot_btn.setText("Show V-Plot")
        else:
            self.v_slice_plot_widget.show()
            self.toggle_v_slice_plot_btn.setText("Hide V-Plot")

    def update_h_slice_plot_visibility(self):
        """Update horizontal slice plot visibility based on whether there are slices"""
        if len(self.h_slice_curves) > 0:
            if not self.h_slice_plot_widget.isVisible():
                self.h_slice_plot_widget.show()
                self.toggle_h_slice_plot_btn.setText("Hide H-Plot")
        else:
            if self.h_slice_plot_widget.isVisible():
                self.h_slice_plot_widget.hide()
                self.toggle_h_slice_plot_btn.setText("Show H-Plot")

    def update_v_slice_plot_visibility(self):
        """Update vertical slice plot visibility based on whether there are slices"""
        if len(self.v_slice_curves) > 0:
            if not self.v_slice_plot_widget.isVisible():
                self.v_slice_plot_widget.show()
                self.toggle_v_slice_plot_btn.setText("Hide V-Plot")
        else:
            if self.v_slice_plot_widget.isVisible():
                self.v_slice_plot_widget.hide()
                self.toggle_v_slice_plot_btn.setText("Show V-Plot")

    def update_display(self):
        """Update slices when the main image changes."""

        if not hasattr(self.measurement, "scan_data"):
            return
        if len(self.measurement.scan_data.positions) <= 2:
            return

        # Update all horizontal slices when the main image changes
        for curve_info in self.h_slice_curves:
            self.update_h_slice(curve_info)

        # Update all vertical slices when the main image changes
        for curve_info in self.v_slice_curves:
            self.update_v_slice(curve_info)


class Sweep1D(SweepNDBase):

    name = "sweep_1d"

    def __init__(
        self,
        app: BaseMicroscopeApp,
        name: Union[str, None] = None,
        collectors: Sequence[Collector] = (),
        actuators: Sequence[ActuatorDefinitions] = (),
        actuator_names: Sequence[str] = "1",
        range_n_intervals: Sequence[int] = (1,),
        n_read_any_settings: int = 2,
        n_any_measurements: int = 2,
        include_sweep_type: bool = True,
        include_center_span: bool = False,
        spinbox_decimals: int = 3,
    ):
        # Add flag for average_to_scan_shape setting
        self.add_average_to_scan_shape = True
        # Add flag for left label in update_display
        self.set_left_label_in_update = True
        super().__init__(
            app=app,
            name=name,
            collectors=collectors,
            actuators=actuators,
            actuator_names=actuator_names,
            range_n_intervals=range_n_intervals,
            n_read_any_settings=n_read_any_settings,
            n_any_measurements=n_any_measurements,
            include_sweep_type=include_sweep_type,
            include_center_span=include_center_span,
            spinbox_decimals=spinbox_decimals,
        )

    def setup(self) -> None:
        self.slice_manager = Sweep1DSlicer(self)
        super().setup()
        self.settings.get_lq("position_representation").add_listener(
            self.slice_manager.update_position_representation
        )

    def mk_graph_widget(self) -> QtWidgets.QWidget:
        graph_widget = super().mk_graph_widget()
        graph_widget = self.slice_manager.wrap_graph_widget(graph_widget)
        return graph_widget

    def _set_compact(self, compact: bool) -> None:
        super()._set_compact(compact)
        self.slice_manager.set_compact(compact)

    def update_display(self) -> None:
        super().update_display()
        if not self.display_ready:
            return
        if self.settings["position_representation"] == "map_vertical":
            self.slice_manager.update_display()

    # Implement abstract methods from base class
    def get_scan_modes(self):
        return SCAN_MODES

    def get_scan_modes_description(self):
        return SCAN_MODES_DESCRIPTION

    def mk_data_shape(self, *args):
        return mk_data_shape(*args)

    def mk_indices_gen(self, *args):
        return mk_indices_gen(*args)

    def mk_positions_gen(self, *args):
        return mk_positions_gen(*args)

    def mk_ranges_consistent(self, settings, actuator_names):
        return mk_ranges_consistent(settings, actuator_names)

    def should_show_positions_on_x_axis(self):
        """For 1D, don't check scan_mode, just return True if size == 1."""
        return True

    def get_py_snippet(self) -> str:
        dset = self.settings["dataset"].rstrip("_raw")
        if dset:
            return f"for pos, {dset.split('_')[-1]} in zip(data.range_1, data.{dset}):\n    continue"
        return ""
