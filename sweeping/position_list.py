import datetime
from pathlib import Path
import numpy as np
from qtpy import QtWidgets


from typing import Any, List


class PositionList:
    """A widget that displays a list of items with remove buttons and provides an easy append API."""

    def __init__(
        self,
        sweep,
    ):
        self.sweep = sweep
        self.ndim = sweep.ndim
        self.items = []
        self.item_widgets = []
        self.fully_initialized = False

    def mk_widget(self):
        widget = QtWidgets.QWidget()

        widget.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred
        )

        # Main layout - horizontal to accommodate vertical button
        self.main_layout = QtWidgets.QHBoxLayout(widget)
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # Vertical toggle button (always visible)
        self.toggle_button = QtWidgets.QPushButton("\u25b6")
        self.toggle_button.setFixedSize(12, 180)
        self.toggle_button.setSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
        )
        self.toggle_button.clicked.connect(self.on_toggle_button_clicked)
        self.toggle_button.setToolTip("📍 Position List (0 items) - Click to expand")

        self.main_layout.addWidget(self.toggle_button)

        # Content widget that can be hidden/shown
        self.content_widget = QtWidgets.QWidget()
        self.content_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred
        )
        self.content_layout = QtWidgets.QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(2)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.content_widget)

        # Track expanded state
        self.is_expanded = False  # Scroll area for the list
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        # self.scroll_area.setMaximumHeight(150)

        # Container widget for items
        self.container_widget = QtWidgets.QWidget()
        self.container_layout = QtWidgets.QVBoxLayout(self.container_widget)
        self.container_layout.setSpacing(1)
        self.container_layout.setContentsMargins(2, 2, 2, 2)

        self.scroll_area.setWidget(self.container_widget)

        # Button layout for add and clear buttons
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setSpacing(4)

        # Clear button
        self.clear_button = QtWidgets.QPushButton("Clear All")
        self.clear_button.clicked.connect(self.clear)
        self.clear_button.setStyleSheet(
            """
            QPushButton {
                background-color: #F44336;
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

        button_layout.addWidget(self.clear_button)

        copy_buttons_layout = QtWidgets.QHBoxLayout()
        for i in range(self.ndim):
            btn = QtWidgets.QPushButton(f"📋{i+1}")
            btn.setStyleSheet(
                """
                QPushButton {
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #f57c00;
                }
            """
            )
            btn.setFixedSize(30, 24)
            btn.setToolTip(f"Copy column {i+1} to clipboard")
            btn.clicked.connect(
                lambda checked, col=i: self.copy_column_to_clipboard(col)
            )
            copy_buttons_layout.addWidget(btn)

        # Add save button
        save_btn = QtWidgets.QPushButton("💾")
        save_btn.setFixedSize(24, 24)
        save_btn.setToolTip("Save positions to file")
        save_btn.clicked.connect(self.on_save_to_file)
        save_btn.setStyleSheet(
            """
                QPushButton {
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #f57c00;
                }
            """
        )
        copy_buttons_layout.addWidget(save_btn)

        # need for higher dim buttons
        self.copy_buttons_layout = copy_buttons_layout

        self.content_layout.addLayout(copy_buttons_layout)
        self.content_layout.addWidget(self.scroll_area)
        self.content_layout.addLayout(button_layout)

        # Stretch to push everything to top
        self.container_layout.addStretch()

        widget.setMaximumWidth(250)
        # Allow the widget to shrink horizontally when collapsed
        widget.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred
        )

        # Store reference to widget for visibility control
        self.widget = widget
        self.update_expanded_collapsed()

        return widget

    def append(self, item: Any, display_text: str = None) -> None:
        if not self.fully_initialized:
            self.create_use_in_sweeps_buttons()
            self.fully_initialized = True

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
                background-color: #F44336;
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

        # Update expanded state
        self.is_expanded = True
        self.update_expanded_collapsed()

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

            # Update visibility when item is removed
            self.update_expanded_collapsed()

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

        # Update visibility after clearing all items
        self.is_expanded = False
        self.update_expanded_collapsed()

    def update_expanded_collapsed(self) -> None:
        """Update widget visibility and button state based on content."""
        if not hasattr(self, "toggle_button"):
            return

        item_count = len(self.items)

        # Update tooltip with current item count
        self.toggle_button.setToolTip(
            f"📍 Position List ({item_count} items) - Click to {'collapse' if self.is_expanded else 'expand'}"
        )

        if self.is_expanded:
            self.content_widget.setVisible(True)
            self.toggle_button.setText("▶")
            self.toggle_button.setStyleSheet(
                """
                QPushButton {
                    background-color: #333333;
                    color: #ffffff;
                    border: 1px solid #ccc;
                    border-radius: 3px;
                    font-weight: bold;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #f57c00;
                }
            """
            )
        else:
            # color = "#0A0603"
            self.content_widget.setVisible(False)
            self.toggle_button.setText("◀")
            self.toggle_button.setStyleSheet(
                """
                QPushButton {
                    background-color: #f0f0f0;
                    color: #000000;
                    border: 1px solid #ccc;
                    border-radius: 3px;
                    font-weight: bold;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #f57c00;
                }

            """
            )

    def on_toggle_button_clicked(self) -> None:
        """Handle click on toggle button to expand/collapse content."""
        self.is_expanded = not self.is_expanded
        self.update_expanded_collapsed()

    def get_items(self) -> List[Any]:
        """Return a copy of all items in the list."""
        return self.items.copy()

    def count(self) -> int:
        """Return the number of items in the list."""
        return len(self.items)

    def copy_column_to_clipboard(self, col_index: int) -> None:
        """Copy a specific column of positions to the clipboard."""

        column_values = np.array(self.items)[:, col_index].astype(str)
        clipboard_text = "\n".join(column_values)
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(clipboard_text)

    def get_copyable_measurements(self) -> List[Any]:
        """Return a list of higher-dimensional measurements if applicable."""
        measurements = []
        for m in self.sweep.app.measurements.values():
            if hasattr(m, "list_uis") and len(m.list_uis) >= self.sweep.ndim:
                measurements.append(m)
                print(self.sweep.name, m.name)

        return measurements

    def create_use_in_sweeps_buttons(self):
        """Create small buttons for higher dimensional measurements."""
        for i, measurement in enumerate(self.get_copyable_measurements()):

            if measurement.name == self.sweep.name:
                symbol = f"⇧"
                font_size = 20
            else:
                symbol = f"➡\n{measurement.name[-2:]}"
                font_size = 10

            btn = QtWidgets.QPushButton(symbol)
            btn.setFixedSize(24, 24)
            btn.setToolTip(f"Use positions for {measurement.name}")
            btn.clicked.connect(lambda checked, m=measurement: self.on_use_for_sweep(m))

            # color = "#FFFFFF"
            btn.setStyleSheet(
                f"""
                QPushButton {{
                    border-radius: 1px;
                    font-weight: normal;
                    font-size: {font_size}px;
                }}
                QPushButton:hover {{
                    background-color: #f57c00;
                }}
            """
            )

            self.copy_buttons_layout.addWidget(btn)

    def on_use_for_sweep(self, measurement):
        """Set position list for a specific higher dimensional measurement."""
        if not self.items:
            measurement.set_status(
                "Position List is empty! Add by control click on your data plot",
                "r",
                True,
            )
            return

        # Set positions for the measurement's actuators
        positions_array = np.array(self.items)

        for i, name in enumerate(measurement.actuator_names):
            if (
                i < positions_array.shape[1]
            ):  # Make sure we have data for this dimension
                column_values = positions_array[:, i]
                text = f"# from {self.sweep.name}\n" + "\n".join(
                    column_values.astype(str)
                )
                if hasattr(measurement, "list_uis") and name in measurement.list_uis:
                    measurement.list_uis[name].setText(text)
                    measurement.settings[f"from_list_{name}"] = True

        target_mode = (
            f"{','.join((np.arange(positions_array.shape[1])+1).astype(str))}_co-move"
        )
        for mode in (target_mode, "co-move"):
            if mode in measurement.get_scan_modes():
                measurement.settings["scan_mode"] = mode
                break

        self.sweep.app.bring_measure_ui_to_front(measurement)
        measurement.update_widgets()
        if measurement.name != self.sweep.name:
            for theirs, ours in zip(
                measurement.actuator_names, self.sweep.actuator_names
            ):
                measurement.settings[f"actuator_{theirs}"] = self.sweep.settings[
                    f"actuator_{ours}"
                ]

        measurement.set_status(
            f"Loaded {len(self.items)} positions for {measurement.name}", "g", True
        )

    def on_save_to_file(self) -> None:
        """Save positions to a file."""
        if not self.items:
            print("No positions to save")
            return

        from qtpy.QtWidgets import QFileDialog

        save_dir = Path(self.sweep.app.settings["save_dir"])
        fname = (
            self.sweep.app.settings["data_fname_format"]
            .format(
                app=self.sweep.app,
                measurement=self.sweep,
                timestamp=datetime.datetime.now(),
                ext="csv",
            )
            .replace(".csv", "_position_list.csv")
        )

        filename, _ = QFileDialog.getSaveFileName(
            None,
            "Save Positions",
            dir=str(save_dir / fname),
            filter="CSV Files (*.csv);;Text Files (*.txt);;All Files (*)",
        )

        if filename:
            try:
                import numpy as np

                positions_array = np.array(self.items)

                if filename.endswith(".csv"):
                    np.savetxt(filename, positions_array, delimiter=",", fmt="%.6f")
                else:
                    np.savetxt(filename, positions_array, fmt="%.8f")

                print(f"Saved {len(self.items)} positions to {filename}")
            except Exception as e:
                print(f"Error saving file: {e}")
