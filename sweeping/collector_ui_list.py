from typing import List

from qtpy.QtWidgets import (
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QWidget,
    QFrame,
)
from qtpy.QtCore import Qt

from .collector import Collector
from qtpy.QtWidgets import QSizePolicy


class CustomListItem(QWidget):
    def __init__(self, collector: Collector, parent=None):
        super().__init__(parent)
        self.collector = collector
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout()
        if self.collector.reps_lq:
            self.reps_widget = self.collector.reps_lq.new_default_widget()
            self.reps_widget.setMaximumWidth(85)
            self.reps_widget.setMinimumWidth(72)

            layout.addWidget(self.reps_widget)
        else:
            self.reps_widget = QDoubleSpinBox()

        self.name_widget = QLabel(self.collector.name)
        self.name_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self.name_widget.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(self.name_widget)

        if self.collector.int_lq:
            self.int_widget = self.collector.int_lq.new_default_widget()
            layout.addWidget(self.int_widget)
        for lq_path in self.collector.displayed_lq_paths:
            lq = self.collector.app.get_lq(lq_path)
            if lq is not None:
                widget = lq.new_default_widget()
                widget.setParent(self)
                layout.addWidget(widget)
        for name, lq in self.collector.settings._logged_quantities.items():
            widget = lq.new_default_widget()
            widget.setParent(self)

            # Keep compact checkboxes
            if lq.dtype == bool:
                widget.setMaximumWidth(18)
                widget.setMaximumHeight(18)

            label = QLabel(f"{name}:")
            label.setSizePolicy(
                QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred
            )
            label.setStyleSheet("QLabel { font-size: 10pt; }")
            layout.addWidget(label)
            layout.addWidget(widget)

        else:
            # widget is assumed to exist by remaining code
            self.int_widget = QDoubleSpinBox()

        self.int_widget.setSizePolicy(
            QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Preferred
        )

        if self.collector.target_measure is not None:
            btn = self.collector.target_measure.operations.new_button("show_ui")
            btn.setText("")
            btn.setMaximumWidth(24)
            btn.setMaximumHeight(24)
            layout.addWidget(btn)

        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        self.collector.reps_lq.add_listener(self.on_reps_changed)

        self.on_reps_changed()

    def on_reps_changed(self, value=None):
        if self.collector.reps_lq.val:
            self.name_widget.setStyleSheet("background-color: rgba(0, 255, 0, 0.08);")
            self.setStyleSheet("font-size:10pt;")
        else:
            self.name_widget.setStyleSheet("background-color: None; ")
            self.setStyleSheet("font-size:10pt;")


class InteractiveCollectorList(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QListWidget.InternalMove)

        # Enable smooth scrolling and auto-sizing
        self.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setSizeAdjustPolicy(QListWidget.AdjustToContents)

    def add_item(self, collector: Collector):
        customItem = CustomListItem(collector)
        listItem = QListWidgetItem(self)

        # Ensure proper sizing for modern layout
        size_hint = customItem.sizeHint()
        size_hint.setHeight(
            max(size_hint.height(), 28)
        )  # Minimum height for modern look
        listItem.setSizeHint(size_hint)
        listItem.setToolTip(collector.description)

        self.addItem(listItem)
        self.setItemWidget(listItem, customItem)

        # Auto-adjust list size
        self.updateGeometry()

    def get_collectors(self) -> List[Collector]:
        collectors = []
        for i in range(self.count()):
            item = self.item(i)
            collector: Collector = self.itemWidget(item).collector
            reps = collector.reps_lq.val
            if reps == 0:
                continue
            collectors.append(collector)
        return collectors
