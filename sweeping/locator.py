import pyqtgraph as pg
from qtpy import QtCore, QtWidgets

from typing import Tuple, Union, List, Any
import numpy as np


class RemovableItemList(QtWidgets.QGroupBox):
    """A widget that displays a list of items with remove buttons and provides an easy append API."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.items = []
        self.item_widgets = []

        self.setTitle("Marked Positions")

        # Main layout
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setSpacing(2)
        self.layout.setContentsMargins(4, 4, 4, 4)

        # Scroll area for the list
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMaximumHeight(150)

        # Container widget for items
        self.container_widget = QtWidgets.QWidget()
        self.container_layout = QtWidgets.QVBoxLayout(self.container_widget)
        self.container_layout.setSpacing(1)
        self.container_layout.setContentsMargins(2, 2, 2, 2)

        self.scroll_area.setWidget(self.container_widget)

        # Button layout for add and clear buttons
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setSpacing(4)

        # Add button
        self.add_button = QtWidgets.QPushButton("Add Current Position")
        self.add_button.setStyleSheet(
            """
            QPushButton {
                background-color: #4caf50;
                color: white;
                border: none;
                padding: 4px 8px;
                border-radius: 3px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """
        )

        # Clear button
        self.clear_button = QtWidgets.QPushButton("Clear All")
        self.clear_button.clicked.connect(self.clear)
        self.clear_button.setStyleSheet(
            """
            QPushButton {
                background-color: #ff0000;
                color: clear;
                border: none;
                padding: 4px 8px;
                border-radius: 3px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #f57c00;
            }
        """
        )

        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.clear_button)

        self.layout.addLayout(button_layout)
        self.layout.addWidget(self.scroll_area)

        # Stretch to push everything to top
        self.container_layout.addStretch()

    def append(self, item: Any, display_text: str = None) -> None:
        """Add an item to the list with optional custom display text."""
        if display_text is None:
            if isinstance(item, (tuple, list)):
                display_text = ", ".join([f"{x:.2f}" for x in item])
            else:
                display_text = str(item)

        self.items.append(item)

        # Create item widget
        item_widget = QtWidgets.QWidget()
        item_layout = QtWidgets.QHBoxLayout(item_widget)
        item_layout.setContentsMargins(4, 2, 4, 2)
        item_layout.setSpacing(4)

        # Item label
        label = QtWidgets.QLabel(display_text)
        label.setStyleSheet(
            """
            QLabel {
                background-color: palette(base);
                color: palette(text);
                padding: 2px 6px;
                border-radius: 2px;
                border: 1px solid palette(mid);
            }
        """
        )

        # Remove button
        remove_btn = QtWidgets.QPushButton("×")
        remove_btn.setFixedSize(20, 20)
        remove_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 10px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """
        )

        # Connect remove button
        index = len(self.items) - 1
        remove_btn.clicked.connect(lambda: self.remove_item(index))

        item_layout.addWidget(label)
        item_layout.addStretch()
        item_layout.addWidget(remove_btn)

        # Insert before the stretch
        self.container_layout.insertWidget(len(self.item_widgets), item_widget)
        self.item_widgets.append(item_widget)

    def remove_item(self, index: int) -> None:
        """Remove item at the specified index."""
        if 0 <= index < len(self.items):
            # Remove from data
            self.items.pop(index)

            # Remove widget
            widget = self.item_widgets.pop(index)
            self.container_layout.removeWidget(widget)
            widget.deleteLater()

            # Update button connections for remaining items
            self._update_button_connections()

    def _update_button_connections(self) -> None:
        """Update remove button connections after item removal."""
        for i, widget in enumerate(self.item_widgets):
            # Find the remove button and reconnect it
            layout = widget.layout()
            remove_btn = layout.itemAt(layout.count() - 1).widget()
            if isinstance(remove_btn, QtWidgets.QPushButton):
                remove_btn.disconnect()
                remove_btn.clicked.connect(lambda checked, idx=i: self.remove_item(idx))

    def clear(self) -> None:
        """Remove all items from the list."""
        while self.items:
            self.remove_item(0)

    def get_items(self) -> List[Any]:
        """Return a copy of all items in the list."""
        return self.items.copy()

    def count(self) -> int:
        """Return the number of items in the list."""
        return len(self.items)


class Locator:

    def __init__(self, sweep_measurement):
        self.sweep = sweep_measurement
        self._positions_on_x_axis = False
        self.locator_btn = None
        self.as_center_btn = None
        self.infinite_line = None
        self.position_list = None
        self.plot_axes = (
            sweep_measurement.axes if hasattr(sweep_measurement, "axes") else None
        )

    def set_plot_axes(self, plot_axes):
        """Set the plot axes for the locator."""
        self.plot_axes = plot_axes

    # def setup_ui(self, parent_widget) -> QtWidgets.QGroupBox:
    #     """Setup and return the locator UI group box."""

    # locator_gb = QtWidgets.QGroupBox("Locator")
    # locator_layout = QtWidgets.QVBoxLayout(locator_gb)
    # locator_layout.setContentsMargins(6, 6, 6, 6)
    # locator_layout.setSpacing(4)
    #
    # self.locator_btn = QtWidgets.QPushButton("")
    # self.locator_btn.clicked.connect(self.on_push_locator_btn)
    # self.locator_btn.setVisible(self.sweep.settings["locator"])
    #
    # self.as_center_btn = QtWidgets.QPushButton("")
    # self.as_center_btn.clicked.connect(self.on_push_as_center_btn)
    # self.as_center_btn.setVisible(self.sweep.settings["locator"])
    #
    # cb = self.sweep.settings.New_UI(["locator"])

    def setup_ui(self, parent_widget):
        self.position_list = RemovableItemList()
        
        self.position_list.setMaximumWidth(450)
        self.position_list.setMaximumHeight(200)
        return self.position_list
        # return 
        # # Create position list widget
        #
        # self.position_list = RemovableItemList()
        # self.position_list.add_button.setText("Add Current Position")
        # self.position_list.add_button.clicked.connect(self.on_add_current_position)
        #
        # locator_gb = QtWidgets.QGroupBox("Marked positions")
        # locator_layout = QtWidgets.QVBoxLayout(locator_gb)
        #
        # # locator_layout.addWidget(self.locator_btn)
        # # locator_layout.addWidget(self.as_center_btn)
        # locator_layout.addWidget(self.position_list)
        # locator_gb.setMaximumWidth(450)
        # locator_gb.setMaximumHeight(200)
        # return locator_gb

    def setup_infinite_line(self, plot_axes):
        """Setup the infinite line on the plot."""
        self.plot_axes = plot_axes  # Store reference to plot axes

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

        # Connect mouse events for Ctrl+Click functionality
        plot_axes.scene().sigMouseClicked.connect(self.on_plot_mouse_clicked)

    def resolve_actuators_positions(
        self, line=None, x_plot_position=None
    ) -> Union[Tuple[float, ...], None]:
        """Get the current locator position."""
        if not hasattr(self.sweep, "scan_data") or not self.sweep.scan_data.data:
            return None

        if x_plot_position is None:
            if line is None:
                line = self.infinite_line
            x_plot_position = line.value()

        if self._positions_on_x_axis:
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
        positions = self.resolve_actuators_positions(line)

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

    def _update_valid_position_ui(
        self, positions: Tuple[float, ...], info_text=None
    ) -> None:
        """Update UI for valid locator position."""
        actuator_names = [i[0] for i in self.sweep.get_current_actuators_defs()]
        ext_pretty_pos = "<br>".join(
            [
                f"<span style='font-weight: 600;'>{name}:</span> {p:.2f}"
                for name, p in zip(actuator_names, positions)
            ]
        )

        if self.infinite_line:
            html = f"""<div style='padding: 3px;'>
                <span style='font-weight: 700; font-size: 13px;'>Actuator Positions</span><br>
                <span style='font-size: 10px;'>{ext_pretty_pos}</span></div>
                <div style='padding: 3px; font-size: 10px; font-style: italic; color: #FFD700;'>Crtl-click to add to Marked List <br>Alt-click to move to position</div>
                """
            self.infinite_line.label.setHtml(html)
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
        if self.position_list:
            self.position_list.setVisible(visible)

    def on_infinite_line_moved(self, line=None):
        """Handle infinite line movement."""
        self.update_display(line)

    def on_push_locator_btn(self):
        """Handle locator button click."""
        positions = self.resolve_actuators_positions()
        if positions:
            self.set_actuator_positions(positions)
            if self.locator_btn:
                self.locator_btn.setStyleSheet("color: blue; font-weight: normal;")

    def on_push_as_center_btn(self):
        """Handle as center button click."""
        positions = self.resolve_actuators_positions()
        if positions:
            self.set_as_center(positions)
            if self.as_center_btn:
                self.as_center_btn.setStyleSheet("color: blue; font-weight: normal;")

    def on_plot_mouse_clicked(self, event):
        """Handle mouse clicks on the plot axes."""

        if event.button() == QtCore.Qt.LeftButton:
            # Get the position in plot coordinates
            pos = event.pos()
            mouse_point = self.plot_axes.vb.mapSceneToView(pos)

            # Convert click position to actual position based on current display mode
            positions = self.resolve_actuators_positions(
                x_plot_position=mouse_point.x()
            )
            if positions is None:
                self.sweep.set_status("clicked outside data range", "w", True)
                return

            self.set_line_position(positions, mouse_point.x())
            pretty_pos = ", ".join([f"{float(p):1.2f}" for p in positions])

        if event.modifiers() == QtCore.Qt.ControlModifier:
            # Ctrl+Click detected
            if positions is not None:
                self._add_position_to_list(positions)

            self.sweep.set_status(f"({pretty_pos}), added to list", "y", True)
        elif event.modifiers() == QtCore.Qt.AltModifier:
            self.sweep.go_to_positions(positions)
            self.sweep.set_status(f"moved Actuators to ({pretty_pos})", "b", True)

    def _add_position_to_list(self, positions):
        """Add a position to the saved positions list."""
        if positions is not None and self.position_list is not None:
            display_text = ", ".join([f"{pos:.2f}" for pos in positions])

            self.position_list.append(positions, display_text)

    def on_add_current_position(self):
        """Add the current locator position to the saved positions list."""
        positions = self.resolve_actuators_positions()
        self._add_position_to_list(positions)

    def get_positions_list(self) -> List[Tuple[float, ...]]:
        """Return the list of saved positions."""
        if self.position_list:
            return self.position_list.get_items()
        return []

    def on_locator_changed(self):
        """Handle locator visibility change."""
        if hasattr(self, "infinite_line") and self.infinite_line:
            enabled = self.sweep.settings["locator"]
            self.set_visibility(enabled)
            # Also update position list visibility
            if self.position_list:
                self.position_list.setVisible(enabled)

    def set_line_position(self, positions, x_plot_position: float) -> None:
        """Set the infinite line position."""
        if self.infinite_line:
            self.infinite_line.setValue(x_plot_position)
            self._update_valid_position_ui(positions)
