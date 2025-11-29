from typing import List
import matplotlib.pyplot as plt
import numpy as np

from qtpy.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from qtpy import QtCore

from .monitor import MonitorBase, SettingMonitor, DESCRIPTION
from qtpy.QtWidgets import QSizePolicy


class MonitorListItem(QWidget):
    def __init__(self, monitor: MonitorBase, description="", parent=None):
        super().__init__(parent)
        self.monitor = monitor
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(1)

        # Monitor name label
        # self.name_widget = QLabel(self.monitor.name)
        # self.name_widget.setMinimumWidth(180)
        # self.name_widget.setSizePolicy(
        #     QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred
        # )
        # layout.addWidget(self.name_widget)

        # Add widgets for monitor settings
        for name in reversed(self.monitor.settings.keys()):
            lq = self.monitor.settings.get_lq(name)
            widget = lq.new_default_widget()
            if name == "update_period":
                widget.setMaximumWidth(80)
                widget.setSizePolicy(
                    QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred
                )

            # Make bool widgets (checkboxes) as small as possible
            if lq.dtype == bool:
                widget.setMaximumWidth(20)
                widget.setMaximumHeight(20)

            # if name != "enabled":  # Skip label for enabled setting
            #     label = QLabel(f"{name}:")
            #     label.setSizePolicy(
            #         QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred
            #     )
            #     label.setStyleSheet("QLabel { font-size: 8pt; }")
            #     layout.addWidget(label)
            layout.addWidget(widget)

        # Start/Stop button
        self.control_btn = QLabel("●")  # Circle to indicate status
        self.control_btn.setFixedSize(20, 20)
        self.control_btn.setStyleSheet(
            "QLabel { background-color: red; border-radius: 10px; color: white; text-align: center; }"
        )
        self.control_btn.setToolTip("Monitor stopped - click to start")
        layout.addWidget(self.control_btn)

        # Status indicator
        self.status_label = QLabel("Stopped")
        self.status_label.setMaximumWidth(50)
        layout.addWidget(self.status_label)

        # Plot button
        self.plot_btn = QPushButton("📊")
        self.plot_btn.setFixedSize(25, 25)
        self.plot_btn.setToolTip("Show data plot")
        self.plot_btn.clicked.connect(self.show_plot)
        layout.addWidget(self.plot_btn)

        # Remove button
        self.remove_btn = QPushButton("❌")
        self.remove_btn.setFixedSize(25, 25)
        self.remove_btn.setToolTip("Remove this monitor")
        self.remove_btn.clicked.connect(self.remove_monitor)
        layout.addWidget(self.remove_btn)

        self.setLayout(layout)

        # Update status periodically
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_status)
        self.timer.start(500)  # Update every 500ms

    def update_status(self):
        if not self.monitor.is_enabled():
            self.control_btn.setStyleSheet(
                "QLabel { background-color: gray; border-radius: 10px; color: white; text-align: center; }"
            )
            self.status_label.setText("Disabled")
        elif self.monitor._running:
            self.control_btn.setStyleSheet(
                "QLabel { background-color: green; border-radius: 10px; color: white; text-align: center; }"
            )
            self.status_label.setText(f"{self.monitor._current_index}")
        else:
            self.control_btn.setStyleSheet(
                "QLabel { background-color: red; border-radius: 10px; color: white; text-align: center; }"
            )
            self.status_label.setText("Stopped")

    def show_plot(self):
        """Show a plot of the monitor data with event pairs indicated."""
        if not self.monitor.values:
            print(f"No data available for monitor '{self.monitor.name}'")
            return

        # Create the plot
        fig, ax = plt.subplots(figsize=(10, 6))

        # Plot the data
        data_array = np.array(self.monitor.values)
        indices = np.arange(len(data_array))
        ax.plot(indices, data_array, "b-", linewidth=2, label="Monitor Data")

        # Add event pairs as colored regions
        events = self.monitor.get_events()
        colors = ["red", "green", "yellow", "cyan", "magenta", "orange"]
        color_idx = 0

        for event_name, pairs in events.items():
            color = colors[color_idx % len(colors)]
            for start_idx, stop_idx in pairs:
                if start_idx < len(data_array) and stop_idx < len(data_array):
                    ax.axvspan(
                        start_idx,
                        stop_idx,
                        alpha=0.5,
                        color=color,
                        label=(
                            f"{event_name}"
                            if pairs.index((start_idx, stop_idx)) == 0
                            else ""
                        ),
                    )
                    l = stop_idx - start_idx
                    ax.text(start_idx, max(data_array), l)
            color_idx += 1

        # Add pending starts as vertical lines
        pending = self.monitor.get_pending_starts()
        for event_name, start_idx in pending.items():
            if start_idx < len(data_array):
                ax.axvline(
                    start_idx,
                    color="red",
                    linestyle="--",
                    alpha=0.7,
                    label=f"{event_name} (pending)",
                )

        # Customize plot
        ax.set_xlabel("")
        ax.set_ylabel("Value")
        ax.set_title(f"Monitor Data: {self.monitor.settings['setting']}")
        ax.grid(True, alpha=0.3)

        # Add legend if there are events
        if events or pending:
            ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left")
            plt.tight_layout()

        plt.show()

    def remove_monitor(self):
        """Remove this monitor from the parent list."""
        # Find the parent InteractiveMonitorList widget
        parent_widget = self.parent()
        while parent_widget and not isinstance(parent_widget, InteractiveMonitorList):
            parent_widget = parent_widget.parent()

        if parent_widget:
            # Stop the monitor if it's running
            if self.monitor._running:
                self.monitor.stop()

            # Remove from the list widget
            parent_widget.remove_monitor_item(self.monitor)


class InteractiveMonitorList(QWidget):
    def __init__(self, measurement=None, parent=None):
        super().__init__(parent)
        self.measurement = measurement
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # Add button
        self.add_button = QPushButton("+ Add Setting Monitor")
        self.add_button.setMaximumHeight(30)
        self.add_button.clicked.connect(self.add_new_monitor)
        self.add_button.setToolTip(DESCRIPTION)
        layout.addWidget(self.add_button)

        # List widget
        self.list_widget = QListWidget()
        self.list_widget.setDragDropMode(QListWidget.InternalMove)
        self.list_widget.setSizeAdjustPolicy(QListWidget.AdjustToContents)
        self.list_widget.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.list_widget.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        layout.addWidget(self.list_widget)

        self.setLayout(layout)
        self.update_visibility()

    def add_new_monitor(self):
        """Create and add a new MonitorBase to the list."""
        monitor_count = self.list_widget.count() + 1
        monitor = SettingMonitor(f"monitor_{monitor_count}", app=self.measurement.app)
        self.add_monitor(monitor)

    def add_monitor(self, monitor: MonitorBase):
        self.measurement.settings.claim_settings(monitor.settings)
        monitor_item = MonitorListItem(monitor)
        list_item = QListWidgetItem(self.list_widget)
        list_item.setSizeHint(monitor_item.sizeHint())
        list_item.setToolTip(monitor.description)
        self.list_widget.addItem(list_item)
        self.list_widget.setItemWidget(list_item, monitor_item)
        self.update_visibility()
        self.measurement.update_widgets()

    def remove_monitor_item(self, monitor: MonitorBase):
        """Remove a monitor from the list."""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if self.list_widget.itemWidget(item).monitor == monitor:
                self.list_widget.takeItem(i)
                break
        self.update_visibility()
        if hasattr(self, "measurement") and self.measurement:
            self.measurement.update_widgets()

    def update_visibility(self):
        """Hide the list widget when empty and adjust size."""
        has_items = self.list_widget.count() > 0
        self.list_widget.setVisible(has_items)

        if has_items:
            # Calculate minimum height needed for all items
            total_height = 0
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                total_height += item.sizeHint().height()

            # Add some padding and scrollbar space
            min_height = min(total_height + 10, 200)  # Cap at 200px max
            self.list_widget.setMinimumHeight(min_height)
            self.list_widget.setMaximumHeight(min_height + 20)
        else:
            self.list_widget.setMinimumHeight(0)
            self.list_widget.setMaximumHeight(0)

    def get_monitors(self) -> List[MonitorBase]:
        monitors = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            monitor: MonitorBase = self.list_widget.itemWidget(item).monitor
            monitors.append(monitor)
        return monitors

    def start_all_monitors(self):
        """Start all enabled monitors in the list."""
        for monitor in self.get_monitors():
            print(monitor)
            if not monitor.is_enabled():
                continue
            if monitor._running:
                monitor.stop()

            print("stopped", monitor.name)

            monitor.start()
            print("started ", monitor.name)

    def stop_all_monitors(self):
        """Stop all enabled monitors in the list."""
        for monitor in self.get_monitors():
            if monitor.is_enabled() and monitor._running:
                monitor.stop()

    def inform_enabled_monitors(self, event_message: str):
        """Inform all enabled monitors of an event."""
        for monitor in self.get_monitors():
            if monitor.is_enabled():
                monitor.inform(event_message)

    def get_enabled_monitors(self):
        """Return list of enabled monitors."""
        return [monitor for monitor in self.get_monitors() if monitor.is_enabled()]

    def get_all_data(self):
        """Get data from all monitors."""
        all_data = {}
        for monitor in self.get_monitors():
            if not monitor.is_enabled():
                continue
            all_data[f"{monitor.prefix}_raw"] = monitor.values

            for event_name, indices in monitor.get_events().items():
                all_data[f"{monitor.prefix}_{event_name}_start_stop_indices"] = indices
                all_data[f"{monitor.prefix}_{event_name}"] = average_data(
                    indices, monitor.values
                )
        return all_data

    def get_monitors_settings(self):
        return (monitor.settings for monitor in self.get_monitors())


def average_data(start_stop_indices, d):
    avgs = np.zeros(len(start_stop_indices))
    for i, indices in enumerate(start_stop_indices):
        avgs[i] = np.mean(d[indices[0] : indices[1]])
    return avgs
