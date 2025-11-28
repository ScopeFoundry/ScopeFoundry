from typing import List

from qtpy.QtWidgets import (
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QWidget,
)
from qtpy import QtCore

from .collector import Collector
from qtpy.QtWidgets import QSizePolicy


class CustomListItem(QWidget):
    def __init__(self, collector: Collector, description="", parent=None):
        super().__init__(parent)
        self.collector = collector
        self.int_ui()

    def int_ui(self):

        layout = QHBoxLayout()
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(1)  # Set spacing between widgets to 5

        if self.collector.reps_lq:
            self.reps_widget = self.collector.reps_lq.new_default_widget()
            self.reps_widget.setMaximumWidth(65)
            layout.addWidget(self.reps_widget)
        else:
            self.reps_widget = QDoubleSpinBox()

        self.name_widget = QLabel(self.collector.name)
        self.name_widget.setSizePolicy(
            QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred
        )
        layout.addWidget(self.name_widget)

        if self.collector.int_lq:
            self.int_widget = self.collector.int_lq.new_default_widget()
            layout.addWidget(self.int_widget)
        for lq_path in self.collector.displayed_lq_paths:
            lq = self.collector.app.get_lq(lq_path)
            if lq is not None:
                widget = lq.new_default_widget()
                layout.addWidget(widget)
        for name, lq in self.collector.settings._logged_quantities.items():
            widget = lq.new_default_widget()
            label = QLabel(f"{name}:")
            label.setSizePolicy(
                    QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred
            )
            label.setStyleSheet("QLabel { font-size: 8pt; }")
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
            btn.setMaximumWidth(25)
            layout.addWidget(btn)

        self.setLayout(layout)

        self.reps_widget.valueChanged.connect(self.on_reps_changed)

        self.name_widget.setEnabled(False)
        self.int_widget.setEnabled(False)

    def on_reps_changed(self, value):
        if value == 0:
            self.name_widget.setEnabled(False)
            self.int_widget.setEnabled(False)
            # self.setStyleSheet("background-color: None;")
        else:
            self.name_widget.setEnabled(True)
            self.int_widget.setEnabled(True)
            # self.setStyleSheet("background-color: rgba(255, 0, 0, 0.3);")


class InteractiveCollectorList(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QListWidget.InternalMove)

    def add_item(self, collector: Collector):
        customItem = CustomListItem(collector)
        listItem = QListWidgetItem(self)
        listItem.setSizeHint(customItem.sizeHint())
        listItem.setToolTip(collector.description)
        self.addItem(listItem)
        self.setItemWidget(listItem, customItem)

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
