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

        self._widgets: Dict[str, QtWidgets.QWidget] = {}
        self.layout = QtWidgets.QVBoxLayout(self.main_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(2)

        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.main_widget)
        self.scroll_area.setMinimumWidth(280)
        self.scroll_area.setContentsMargins(0, 0, 0, 0)

    def refresh_widgets(self):
        while self.layout.count():
            child = self.layout.takeAt(0)

        for name in sorted(self._widgets.keys()):
            widget = self._widgets[name]
            self.layout.addWidget(widget)

        self.layout.addSpacerItem(
            QtWidgets.QSpacerItem(
                0, 0, QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum
            )
        )

        self.scroll_area.setVisible(self.has_items())
        self.app.ui.quickaccess_scrollArea.setVisible(
            self.has_items() or self.app.quickbar is not None
        )
        self.layout.addStretch()

    def add_lq_paths(self, lq_paths: list):
        for lq_path in lq_paths:
            self.add_lq_path(lq_path, False)
        self.refresh_widgets()

    def add_operation_paths(self, operation_paths: list):
        for path in operation_paths:
            if path in self._operations:
                continue
            self._widgets[path] = self.new_operation_widget(path)
            self._operations.append(path)
        self.refresh_widgets()

    def add_lq_paths_lists(self, lq_paths_lists: list):
        for paths in lq_paths_lists:
            label_text = paths[0]
            if label_text in self._lq_paths_list:
                continue
            self._widgets[label_text] = self.new_lq_paths_list(paths)
            self._lq_paths_list.append(label_text)
        self.refresh_widgets()

    def add_lq_path(self, lq_path: str, refresh: bool = True):
        if lq_path in self._widgets:
            self._widgets[lq_path].setVisible(True)
        else:
            self._lq_paths.append(lq_path)
            self._widgets[lq_path] = self.new_lq_widget(lq_path)

        if refresh:
            self.refresh_widgets()

    def remove_lq_path(self, lq_path: str):
        if lq_path in self._lq_paths:
            self._lq_paths.remove(lq_path)
            widget = self._widgets.pop(lq_path, None)
            widget.setVisible(False)
        self.refresh_widgets()

    def remove_lq_paths_list(self, label_text: str):
        if not label_text in self._lq_paths_list:
            return
        widget = self._widgets.pop(label_text, None)
        widget.setVisible(False)
        self._lq_paths_list.remove(label_text)
        self.refresh_widgets()

    def remove_operation(self, operation_path: str):
        if not operation_path in self._operations:
            return
        widget = self._widgets.pop(operation_path, None)
        widget.setVisible(False)
        self._operations.remove(operation_path)
        self.refresh_widgets()

    def has_items(self):
        return (
            bool(self._operations) or bool(self._lq_paths) or bool(self._lq_paths_list)
        )

    def new_remove_btn(self, lq_path):
        btn = QtWidgets.QPushButton()
        btn.setMaximumWidth(24)
        btn.setToolTip("Remove from favorites")
        btn.setIcon(
            self.app.qtapp.style().standardIcon(QtWidgets.QStyle.SP_TabCloseButton)
        )
        return btn

    def new_lq_widget(self, lq_path: str):
        btn = self.new_remove_btn(lq_path)
        btn.clicked.connect(partial(self.remove_lq_path, lq_path))

        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(btn)
        text = "<i>{}</i> <b>{}</b>".format(
            *lq_path.lstrip("mm/").lstrip("hw/").split("/")
        )
        label = QtWidgets.QLabel(text)
        # label.setStyleSheet("font-weight: bold;")

        layout.addWidget(label)
        layout.addWidget(self.app.get_lq(lq_path).new_default_widget())
        return widget

    def new_lq_paths_list(self, paths_list: list):
        btn = self.new_remove_btn(paths_list[1])
        label_text = paths_list[0]
        btn.clicked.connect(partial(self.remove_lq_paths_list, label_text))

        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(btn)
        layout.addWidget(QtWidgets.QLabel(label_text))
        for element in paths_list[1:]:
            layout.addWidget(self.app.get_lq(element).new_default_widget())
        return widget

    def new_operation_widget(self, operation_path: str):
        btn = self.new_remove_btn(operation_path)
        btn.clicked.connect(partial(self.remove_operation, operation_path))

        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(btn)
        layout.addWidget(self.app.get_operation(operation_path).new_button())
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
