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

    def mk_widget(self):
        widget = QtWidgets.QGroupBox("Positions List")

        # Main layout
        self.layout = QtWidgets.QVBoxLayout(widget)
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

        button_layout.addWidget(self.clear_button)

        copy_buttons_layout = QtWidgets.QHBoxLayout()
        for i in range(self.ndim):
            btn = QtWidgets.QPushButton(f"Copy Col {i+1}")
            btn.clicked.connect(
                lambda checked, col=i: self.copy_column_to_clipboard(col)
            )
            copy_buttons_layout.addWidget(btn)

        use_for_sweep_btn = QtWidgets.QPushButton("▲")
        use_for_sweep_btn.setFixedSize(24, 24)
        use_for_sweep_btn.setToolTip("Use positions for sweep (co-move mode) ")
        use_for_sweep_btn.clicked.connect(self.on_use_for_sweep)
        use_for_sweep_btn.setStyleSheet(
            """
            QPushButton {
                border: 1px solid #ccc;
                border-radius: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
        """
        )
        copy_buttons_layout.addWidget(use_for_sweep_btn)

        # Add save button
        save_btn = QtWidgets.QPushButton("💾")
        save_btn.setFixedSize(24, 24)
        save_btn.setToolTip("Save positions to file")
        save_btn.clicked.connect(self.on_save_to_file)
        save_btn.setStyleSheet(
            """
            QPushButton {
                border: 1px solid #ccc;
                border-radius: 12px;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
        """
        )
        copy_buttons_layout.addWidget(use_for_sweep_btn)

        # Add save button
        save_btn = QtWidgets.QPushButton("💾")
        save_btn.setFixedSize(24, 24)
        save_btn.setToolTip("Save positions to file")
        save_btn.clicked.connect(self.on_save_to_file)
        save_btn.setStyleSheet(
            """
            QPushButton {
                border: 1px solid #ccc;
                border-radius: 12px;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
        """
        )
        copy_buttons_layout.addWidget(save_btn)

        # Add buttons for higher dimensional measurements
        self.create_higher_dim_buttons(copy_buttons_layout)

        self.layout.addLayout(copy_buttons_layout)
        self.layout.addLayout(button_layout)
        self.layout.addWidget(self.scroll_area)

        # Stretch to push everything to top
        self.container_layout.addStretch()

        widget.setMaximumWidth(350)
        return widget

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

    def copy_column_to_clipboard(self, col_index: int) -> None:
        """Copy a specific column of positions to the clipboard."""

        column_values = np.array(self.items)[:, col_index].astype(str)
        clipboard_text = "\n".join(column_values)
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(clipboard_text)

    def on_use_for_sweep(self) -> None:
        if not self.items:
            self.sweep.set_status(
                "Position List is empty! Add by control click on your data plot",
                "r",
                True,
            )
            return
        for name, column_values in zip(
            self.sweep.actuator_names, np.array(self.items).T
        ):
            text = "\n".join(column_values.astype(str))
            list_ui = self.sweep.list_uis[name].setText(text)
            self.sweep.settings[f"from_list_{name}"] = True
        self.sweep.settings["scan_mode"] = "co-move"

    def get_higher_dim_measurements(self) -> List[Any]:
        """Return a list of higher-dimensional measurements if applicable."""
        measurements = []
        for m in self.sweep.app.measurements.values():
            if m is self.sweep:
                continue
            if hasattr(m, "list_uis") and len(m.list_uis) >= self.sweep.ndim:
                measurements.append(m)
        return measurements

    def create_higher_dim_buttons(self, layout):
        """Create small buttons for higher dimensional measurements."""
        higher_dim_measurements = self.get_higher_dim_measurements()

        for i, measurement in enumerate(higher_dim_measurements):
            # Use different symbols for different measurements
            symbols = ["⬆", "⬇", "➡", "⬅", "↗", "↘", "↙", "↖"]
            symbol = symbols[i % len(symbols)]

            btn = QtWidgets.QPushButton(symbol)
            btn.setFixedSize(24, 24)
            btn.setToolTip(f"Use positions for {measurement.name}")
            btn.clicked.connect(
                lambda checked, m=measurement: self.on_use_for_measurement(m)
            )
            btn.setStyleSheet(
                """
                QPushButton {
                    border: 1px solid #ccc;
                    border-radius: 12px;
                    font-weight: bold;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #e0e0ff;
                }
            """
            )
            layout.addWidget(btn)

    def on_use_for_measurement(self, measurement):
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
                text = "\n".join(column_values.astype(str))
                if hasattr(measurement, "list_uis") and name in measurement.list_uis:
                    measurement.list_uis[name].setText(text)
                    measurement.settings[f"from_list_{name}"] = True

        # Set to position list mode if available
        if "Position List" in measurement.get_scan_modes():
            measurement.settings["scan_mode"] = "Position List"

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
