from functools import partial
import json
from typing import Dict

from qtpy import QtWidgets


def new_favorites_widget(app):
    """Create a new FavoritesWidget instance."""
    return FavoritesWidget(app)


class FavoritesWidget:
    """A widget to display and manage favorite objects with their settings and operations."""

    def __init__(self, app):
        self.app = app
        self._lq_paths = []
        self._operations = []
        self._lq_paths_list = []

        self.main_widget = QtWidgets.QWidget()
        self.main_widget.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred
        )
        self._widgets: Dict[str, QtWidgets.QWidget] = {}
        self.layout = QtWidgets.QVBoxLayout(self.main_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(2)

        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.main_widget)

    def refresh_widgets(self):
        while self.layout.count():
            child = self.layout.takeAt(0)

        for name in sorted(self._widgets.keys()):
            widget = self._widgets[name]
            self.layout.addWidget(widget)

        self.main_widget.setVisible(bool(self._widgets))

    def add_lq_paths(self, lq_paths: list):
        for lq_path in lq_paths:
            self.add_lq_path(lq_path, False)
        self.refresh_widgets()

    def add_operation_paths(self, operation_paths: list):
        for path in operation_paths:
            if path in self._operations:
                continue
            self._widgets[path] = self.app.get_operation(path).new_button()
            self._operations.append(path)
        self.refresh_widgets()

    def add_lq_paths_lists(self, lq_paths_lists: list):
        for paths in lq_paths_lists:
            if paths[1] in self._lq_paths_list:
                continue
            self._widgets[paths[1]] = self.new_lq_paths_list(paths)
            self._lq_paths_list.append(paths)
        self.refresh_widgets()

    def add_lq_path(self, lq_path: str, refresh: bool = True):
        if lq_path in self._widgets:
            self._widgets[lq_path].setVisible(True)
        else:
            self._lq_paths.append(lq_path)
            self._widgets[lq_path] = self.new_lq_widget(lq_path)

        if refresh:
            self.refresh_widgets()

    def new_lq_widget(self, lq_path: str):
        btn = QtWidgets.QPushButton()
        btn.setMaximumWidth(24)
        btn.setToolTip("Remove from favorites")
        btn.setIcon(
            self.app.qtapp.style().standardIcon(QtWidgets.QStyle.SP_TabCloseButton)
        )
        btn.clicked.connect(partial(self.remove_lq_path, lq_path))

        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(btn)
        label = QtWidgets.QLabel(
            " ".join(lq_path.lstrip("mm/").lstrip("hw/").split("/"))
        )
        label.setStyleSheet("font-weight: bold;")
        layout.addWidget(label)
        layout.addWidget(self.app.get_lq(lq_path).new_default_widget())
        return widget

    def remove_lq_path(self, lq_path: str):
        if lq_path in self._lq_paths:
            self._lq_paths.remove(lq_path)
            widget = self._widgets.pop(lq_path, None)
            widget.setVisible(False)
        self.refresh_widgets()

    def new_lq_paths_list(self, paths_list: list):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(QtWidgets.QLabel(paths_list[0]))
        for element in paths_list[1:]:
            layout.addWidget(self.app.get_lq(element).new_default_widget())
        return widget

    def load(self, fname: str):
        # UNTESTED METHOD
        with open(fname, "r") as fp:
            content = json.load(fp)
            self.add_lq_paths_lists(content.get("lq_paths_lists", []))
            self.add_operation_paths(content.get("operations", []))
            self.add_lq_paths(content.get("lq_paths", []))

    def save(self, fname: str):
        # UNTESTED METHOD
        with open(fname, "w") as fp:
            json.dump(
                {
                    "lq_paths_list": self._lq_paths_list,
                    "lq_paths": self._lq_paths,
                    "operations": self._operations,
                },
                fp,
            )
