import pyqtgraph as pg
from qtpy import QtCore, QtWidgets

from typing import Tuple, Union
import numpy as np


class Locator:
    """Handles locator functionality for 1D sweeps."""

    def __init__(self, sweep_measurement):
        self.sweep = sweep_measurement
        self._positions_on_x_axis = False
        self.locator_btn = None
        self.as_center_btn = None
        self.infinite_line = None

    def setup_ui(self, parent_widget) -> QtWidgets.QGroupBox:
        """Setup and return the locator UI group box."""

        locator_gb = QtWidgets.QGroupBox("Locator")
        locator_layout = QtWidgets.QVBoxLayout(locator_gb)
        locator_layout.setContentsMargins(6, 6, 6, 6)
        locator_layout.setSpacing(4)

        self.locator_btn = QtWidgets.QPushButton("")
        self.locator_btn.clicked.connect(self.on_push_locator_btn)
        self.locator_btn.setVisible(self.sweep.settings["locator"])

        self.as_center_btn = QtWidgets.QPushButton("")
        self.as_center_btn.clicked.connect(self.on_push_as_center_btn)
        self.as_center_btn.setVisible(self.sweep.settings["locator"])

        cb = self.sweep.settings.New_UI(["locator"])

        locator_layout.addWidget(cb)
        locator_layout.addWidget(self.locator_btn)
        locator_layout.addWidget(self.as_center_btn)
        locator_gb.setMaximumWidth(400)

        return locator_gb

    def setup_infinite_line(self, plot_axes):
        """Setup the infinite line on the plot."""
        self.infinite_line = pg.InfiniteLine(
            angle=90,
            label="locator",
            movable=True,
            pen=pg.mkPen(color="#FF5722", width=2, style=QtCore.Qt.DashLine),
            labelOpts={
                "color": "#FFFFFF",
                "movable": True,
                "fill": "#FF56221E",  # faint semi-transparent background
            },
        )
        self.infinite_line.setVisible(self.sweep.settings["locator"])
        self.infinite_line.sigPositionChanged.connect(self.on_infinite_line_moved)
        plot_axes.addItem(self.infinite_line)

    def get_position(self, line=None) -> Union[Tuple[float, ...], None]:
        """Get the current locator position."""
        if not hasattr(self.sweep, "scan_data") or not self.sweep.scan_data.data:
            return None

        if line is None:
            line = self.infinite_line

        if self._positions_on_x_axis:
            # For 2D sweeps in co-move mode, we need to find the closest position
            if hasattr(self.sweep, "ndim") and self.sweep.ndim > 1:
                positions = np.array(self.sweep.scan_data.positions)[:, 0]
                index = np.argmin(np.abs(positions - line.value()))
                return self.sweep.scan_data.positions[index]
            else:
                # For 1D sweeps
                return (line.value(),)

        settings = self.sweep.settings
        if settings["average_over_repetitions"]:
            size = self.sweep.scan_data.get_dset_size_per_position_and_repeats(
                settings["data_set"]
            )
        else:
            size = self.sweep.scan_data.get_dset_size_per_position(settings["data_set"])

        index = int(line.value() // size)

        if self.sweep.index * size >= self.sweep.max_npoints_shown:
            smallest_index_shown = self.sweep.index - (
                self.sweep.max_npoints_shown // size
            )
            index += smallest_index_shown

        if index < 0 or index >= len(self.sweep.scan_data.positions):
            return None

        return self.sweep.scan_data.positions[index]

    def set_actuator_positions(self, positions: Tuple[float, ...]) -> None:
        """Set actuator positions based on locator position."""
        funcs = self.sweep.get_current_target_position_funcs()
        for p, f in zip(positions, funcs):
            f(p)

    def set_as_center(self, positions: Tuple[float, ...]) -> None:
        """Set positions as center of scan ranges."""
        for p, r in zip(positions, self.sweep.scan_ranges):
            r.set_center(p)

    def update_display(self, line=None) -> None:
        """Update locator display and button states."""
        positions = self.get_position(line)

        if positions is None:
            self._update_invalid_position_ui()
            return

        self._update_valid_position_ui(positions)

    def _update_invalid_position_ui(self):
        """Update UI for invalid locator position."""
        if self.locator_btn:
            self.locator_btn.setEnabled(False)
            self.locator_btn.setText("Invalid Position: Drag locator within data range")
            self.locator_btn.setStyleSheet(
                """
                QPushButton {
                    color: #f44336;
                    font-weight: 600;
                }
            """
            )

        if self.as_center_btn:
            self.as_center_btn.setEnabled(False)
            self.as_center_btn.setText(
                "Invalid Position: Drag locator within data range"
            )
            self.as_center_btn.setStyleSheet(
                """
                QPushButton {
                    color: #f44336;
                    font-weight: 600;
                }
            """
            )

    def _update_valid_position_ui(self, positions: Tuple[float, ...]):
        """Update UI for valid locator position."""
        actuator_names = [i[0] for i in self.sweep.get_current_actuators_defs()]
        ext_pretty_pos = "<br>".join(
            [
                f"<span style='font-weight: 600;'>{name}:</span> {p:.2f}"
                for name, p in zip(actuator_names, positions)
            ]
        )

        if self.infinite_line:
            self.infinite_line.label.setHtml(
                f"<div style='padding: 3px;'>"
                f"<span style='font-weight: 700; font-size: 13px;'>Actuator Positions</span><br>"
                f"<span style='font-size: 10px;'>{ext_pretty_pos}</span></div>"
            )
            self.infinite_line.label.setMovable(True)

        if self.locator_btn:
            self.locator_btn.setEnabled(True)
            pretty_pos = ", ".join([f"{p:.2f}" for p in positions])
            self.locator_btn.setText(f"Set Actuator Position ({pretty_pos})")
            self.locator_btn.setStyleSheet(
                """
                QPushButton {
                    color: #4caf50;
                    font-weight: 600;
                }
                QPushButton:hover {
                    color: #388e3c;
                }
            """
            )

        if self.as_center_btn:
            self.as_center_btn.setEnabled(True)
            pretty_pos = ", ".join([f"{p:.2f}" for p in positions])
            self.as_center_btn.setText(f"Set as Center ({pretty_pos})")
            self.as_center_btn.setStyleSheet(
                """
                QPushButton {
                    color: "#FF5622FF";
                    font-weight: 600;
                }
                QPushButton:hover {
                    color: #388e3c;
                }
            """
            )

    def set_visibility(self, visible: bool) -> None:
        """Set visibility of locator components."""
        if self.locator_btn:
            self.locator_btn.setVisible(visible)
        if self.as_center_btn:
            self.as_center_btn.setVisible(visible)
        if self.infinite_line:
            self.infinite_line.setVisible(visible)

    def on_infinite_line_moved(self, line=None):
        """Handle infinite line movement."""
        self.update_display(line)

    def on_push_locator_btn(self):
        """Handle locator button click."""
        positions = self.get_position()
        if positions:
            self.set_actuator_positions(positions)
            if self.locator_btn:
                self.locator_btn.setStyleSheet("color: blue; font-weight: normal;")

    def on_push_as_center_btn(self):
        """Handle as center button click."""
        positions = self.get_position()
        if positions:
            self.set_as_center(positions)
            if self.as_center_btn:
                self.as_center_btn.setStyleSheet("color: blue; font-weight: normal;")

    def on_locator_changed(self):
        """Handle locator visibility change."""
        if hasattr(self, "infinite_line") and self.infinite_line:
            enabled = self.sweep.settings["locator"]
            self.set_visibility(enabled)
