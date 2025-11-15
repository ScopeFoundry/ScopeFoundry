import pyqtgraph as pg
from qtpy import QtCore, QtWidgets

from typing import Tuple, Union, List
import numpy as np


class LocatorBase:

    def __init__(self, sweep_measurement, axes, position_list):
        self.sweep = sweep_measurement
        self.position_list = position_list
        self.axes = axes
        self.setup_indicator()

        # Connect mouse events for Ctrl+Click functionality
        self.axes.scene().sigMouseClicked.connect(self.on_plot_mouse_clicked)

    def setup_indicator(self):
        """Setup the infinite line on the plot."""
        pass

    def set_indicator_position(self, positions, plot_position: Tuple[float]) -> None:
        """Set the infinite line position."""
        pass

    def update_indicator_label(self, actuator_names, positions):
        """Gets called to update the indicator label."""
        pass

    def resolve_actuators_positions(
        self, plot_position=None
    ) -> Union[Tuple[float, ...], None]:
        """Get the current locator position."""
        pass

    def mk_widget(self):
        self.widget = QtWidgets.QGroupBox("Locator")
        self.widget.setMaximumWidth(450)

        self.go_to_btn = QtWidgets.QPushButton("Go To")
        self.as_center_btn = QtWidgets.QPushButton("Set as Center")
        self.add_btn = QtWidgets.QPushButton("Add to Position List")

        self.widget = QtWidgets.QGroupBox("Locator Controls")
        layout = QtWidgets.QVBoxLayout(self.widget)
        layout.addWidget(self.as_center_btn)
        layout.addWidget(self.go_to_btn)
        layout.addWidget(self.add_btn)
        layout.addStretch()

        self.go_to_btn.clicked.connect(self.on_go_to_btn_clicked)
        self.as_center_btn.clicked.connect(self.on_as_center_clicked)
        self.add_btn.clicked.connect(self.on_add_current_position)

        return self.widget

    def mk_list_widget(self):
        """Create and return the position list widget."""
        return self.position_list.mk_list_widget()

    def set_actuator_positions(self, positions: Tuple[float, ...]) -> None:
        """Set actuator positions based on locator position."""
        funcs = self.sweep.get_current_target_position_funcs()
        for p, f in zip(positions, funcs):
            f(p)

    def set_as_center(self, positions: Tuple[float, ...]) -> None:
        """Set positions as center of scan ranges."""
        for p, r in zip(positions, self.sweep.scan_ranges):
            r.set_center(p)

    def update_display(self) -> None:
        """Update locator display and button states."""
        positions = self.resolve_actuators_positions()

        if positions is None:
            self._update_invalid_position_ui()
            return

        self._update_valid_position_ui(positions)

    def _update_invalid_position_ui(self):
        """Update UI for invalid locator position."""
        if self.go_to_btn:
            self.go_to_btn.setEnabled(False)
            self.go_to_btn.setText("Invalid Position: Drag locator within data range")
            self.go_to_btn.setStyleSheet(
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
        if self.add_btn:
            self.add_btn.setEnabled(False)
            self.add_btn.setText("Invalid Position: Drag locator within data range")
            self.add_btn.setStyleSheet(
                """
                QPushButton {
                    color: #f44336;
                    font-weight: 600;
                }
            """
            )

    def _update_valid_position_ui(
        self, positions: Tuple[float, ...], info_text=None
    ) -> None:
        """Update UI for valid locator position."""
        actuator_names = [i[0] for i in self.sweep.get_current_actuators_defs()]

        self.update_indicator_label(actuator_names, positions)

        pretty_pos = ", ".join([f"{p:.2f}" for p in positions])

        if self.go_to_btn:
            self.go_to_btn.setEnabled(True)
            self.go_to_btn.setText(f"Set Actuator Position ({pretty_pos})")
            self.go_to_btn.setStyleSheet(
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
            self.as_center_btn.setText(f"Set as Center ({pretty_pos})")
            self.as_center_btn.setStyleSheet(
                """
                QPushButton {
                    font-weight: 600;
                }
                QPushButton:hover {
                    color: #388e3c;
                }
            """
            )

        if self.add_btn:
            self.add_btn.setEnabled(True)
            self.add_btn.setText(f"Add to Position List ({pretty_pos})")
            self.add_btn.setStyleSheet(
                """
                QPushButton {
                    color: #2196f3;
                    font-weight: 600;
                }
                QPushButton:hover {
                    color: #1976d2;
                }
            """
            )

    def on_indicator_moved(self):
        """Handle infinite line movement."""
        self.update_display()

    def on_go_to_btn_clicked(self):
        """Handle locator button click."""
        positions = self.resolve_actuators_positions()
        if positions is not None:
            self.set_actuator_positions(positions)
            if self.go_to_btn:
                self.go_to_btn.setStyleSheet("color: blue; font-weight: normal;")

    def on_as_center_clicked(self):
        """Handle as center button click."""
        positions = self.resolve_actuators_positions()
        if positions is not None:
            self.set_as_center(positions)
            if self.as_center_btn:
                self.as_center_btn.setStyleSheet("color: blue; font-weight: normal;")

    def on_plot_mouse_clicked(self, event):
        """Handle mouse clicks on the plot axes."""

        if event.button() != QtCore.Qt.LeftButton:
            return

        # Get the position in plot coordinates
        mouse_point = self.axes.vb.mapSceneToView(event.scenePos())

        positions = self.resolve_actuators_positions(
            plot_position=(mouse_point.x(), mouse_point.y())
        )
        if positions is None:
            self.sweep.set_status("clicked outside data range", "w", True)
            return

        self.set_indicator_position(
            positions, plot_position=(mouse_point.x(), mouse_point.y())
        )
        pretty_pos = ", ".join([f"{float(p):1.2f}" for p in positions])
        self._update_valid_position_ui(positions)

        if event.modifiers() == QtCore.Qt.ControlModifier:
            if positions is not None:
                self.add_position_to_list(positions)

            self.sweep.set_status(f"({pretty_pos}), added to list", "y", True)
        elif event.modifiers() == QtCore.Qt.AltModifier:
            self.sweep.go_to_positions(positions)
            self.sweep.set_status(f"moved Actuators to ({pretty_pos})", "b", True)

    def add_position_to_list(self, positions):
        """Add a position to the saved positions list."""
        if positions is not None:
            display_text = ", ".join([f"{pos:.2f}" for pos in positions])
            self.position_list.append(positions, display_text)

    def on_add_current_position(self):
        """Add the current locator position to the saved positions list."""
        positions = self.resolve_actuators_positions()
        self.add_position_to_list(positions)


class LocatorRoi(LocatorBase):
    """Locator for ROI positioning. Assumes that the axes are image with the extents matching the actuators positions."""

    def __init__(
        self,
        sweep_measurement,
        axes,
        position_list,
    ):
        super().__init__(sweep_measurement, axes, position_list)

    def setup_indicator(self):
        self.circ_roi_size = 0.1

        pen = pg.mkPen(color="#FF5722", width=5, style=QtCore.Qt.DashLine)

        self.pt_roi = pg.CircleROI(
            (0, 0), (self.circ_roi_size, self.circ_roi_size), movable=True, pen=pen
        )

        self.pt_roi.removeHandle(0)
        self.pt_roi.sigRegionChangeFinished.connect(self.on_indicator_moved)
        self.axes.addItem(self.pt_roi)

    def resolve_actuators_positions(self, plot_position=None):
        if plot_position is None:
            roi_state = self.pt_roi.saveState()
            x0, y0 = roi_state["pos"]
        else:
            x0, y0 = plot_position
        return (x0, y0)
        xc = x0 + self.circ_roi_size / 2.0
        yc = y0 + self.circ_roi_size / 2.0
        return (xc, yc)

    def set_indicator_position(self, positions, plot_position: Tuple[float]) -> None:
        """Set the infinite line position."""
        xc, yc = positions
        x0 = xc - self.circ_roi_size / 2.0
        y0 = yc - self.circ_roi_size / 2.0
        self.pt_roi.setPos((x0, y0))
        self._update_valid_position_ui(positions)


class LocatorX(LocatorBase):

    def __init__(self, sweep_measurement, axes, position_list):
        super().__init__(sweep_measurement, axes, position_list)
        self.real_position_on_x = False

    def setup_indicator(
        self,
    ):

        self.infinite_line_x = pg.InfiniteLine(
            angle=90,
            label="locator",
            movable=True,
            pen=pg.mkPen(color="#FF5722", width=2, style=QtCore.Qt.DashLine),
            labelOpts={
                "color": "#FFFFFF",
                "movable": True,
                "fill": "#FF5722",  # faint semi-transparent background
            },
        )
        self.infinite_line_x.sigPositionChanged.connect(self.on_indicator_moved)
        self.axes.addItem(self.infinite_line_x)

    def set_indicator_position(self, positions, plot_position: Tuple[float]) -> None:
        """Set the infinite line position."""
        self.infinite_line_x.setValue(plot_position[0])
        self._update_valid_position_ui(positions)

    def resolve_actuators_positions(
        self, plot_position=None
    ) -> Union[Tuple[float, ...], None]:
        """Get the current locator position."""
        if not hasattr(self.sweep, "scan_data") or not self.sweep.scan_data.data:
            return None

        if plot_position is None:
            x_plot_position = self.infinite_line_x.value()
        else:
            x_plot_position = plot_position[0]

        if self.real_position_on_x:
            if hasattr(self.sweep, "ndim") and self.sweep.ndim > 1:
                positions = np.array(self.sweep.scan_data.positions)[:, 0]
                index = np.argmin(np.abs(positions - x_plot_position))
                return self.sweep.scan_data.positions[index]
            else:
                return (x_plot_position,)

        settings = self.sweep.settings
        if settings["average_over_repetitions"]:
            size = self.sweep.scan_data.get_dset_size_per_position_and_repeats(
                settings["data_set"]
            )
        else:
            size = self.sweep.scan_data.get_dset_size_per_position(settings["data_set"])

        index = int(x_plot_position // size)

        if self.sweep.index * size >= self.sweep.max_npoints_shown:
            smallest_index_shown = self.sweep.index - (
                self.sweep.max_npoints_shown // size
            )
            index += smallest_index_shown

        if index < 0 or index >= len(self.sweep.scan_data.positions):
            return None

        return self.sweep.scan_data.positions[index]

    def update_indicator_label(self, actuator_names, positions):
        ext_pretty_pos = "<br>".join(
            [
                f"<span style='font-weight: 600;'>{name}:</span> {p:.2f}"
                for name, p in zip(actuator_names, positions)
            ]
        )
        if self.infinite_line_x:
            html = f"""<div style='padding: 3px;'>
                <span style='font-weight: 700; font-size: 13px;'>Actuator Positions</span><br>
                <span style='font-size: 10px;'>{ext_pretty_pos}</span></div>
                <div style='padding: 3px; font-size: 10px; font-style: italic; color: #FFD700;'>Crtl-click to add to Position List <br>Alt-click to move to position</div>
                """
            self.infinite_line_x.label.setHtml(html)
            self.infinite_line_x.label.setMovable(True)
