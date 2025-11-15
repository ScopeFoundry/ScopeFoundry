import numpy as np
from qtpy import QtWidgets


from typing import Any, List


class PositionList:
    """A widget that displays a list of items with remove buttons and provides an easy append API."""

    def __init__(self, ndims: int = 1):
        self.ndims = ndims
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
        for i in range(self.ndims):
            btn = QtWidgets.QPushButton(f"Copy Col {i+1}")
            btn.clicked.connect(
                lambda checked, col=i: self.copy_column_to_clipboard(col)
            )
            copy_buttons_layout.addWidget(btn)

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

    def copy_column_to_clipboard(self, col_index: int) -> None:
        """Copy a specific column of positions to the clipboard."""

        column_values = np.array(self.items)[:, col_index].astype(str)
        clipboard_text = "\n".join(column_values)
        print(f"Copying to clipboard:\n{clipboard_text}")
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(clipboard_text)
