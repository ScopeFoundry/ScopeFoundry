from functools import partial
from pathlib import Path
import re

from qtpy import QtWidgets, QtGui

from .logged_quantity import LoggedQuantity


class FileLQ(LoggedQuantity):
    """
    Specialized str type :class:`LoggedQuantity` that handles
    a filename (or directory) and associated file.
    """

    def __init__(self, name, default_dir=None, is_dir=False, file_filters=(), **kwargs):

        initial = kwargs.pop("initial", None)
        if not initial:
            initial = str(Path.cwd())

        LoggedQuantity.__init__(self, name, dtype=str, initial=initial, **kwargs)

        self.default_dir = default_dir
        self.is_dir = is_dir

        if isinstance(file_filters, str):
            file_filters = [file_filters]
        self.file_filters = file_filters

    def connect_to_browse_widgets(
        self, lineEdit: QtWidgets.QLineEdit, pushButton: QtWidgets.QPushButton
    ):
        self.connect_to_widget(lineEdit)

        lineEdit.setAcceptDrops(True)
        lineEdit.dragEnterEvent = self.on_drag_enter
        lineEdit.dropEvent = partial(self.on_drop, widget=lineEdit)

        pushButton.clicked.connect(self.file_browser)

    def file_browser(self):

        path = Path(self.default_dir) if self.default_dir else Path(self.val)
        if not path.exists():
            path = Path.cwd()

        directory = str(path) if path.is_dir() else str(path.parent)

        if self.is_dir:
            fname = QtWidgets.QFileDialog.getExistingDirectory(directory=directory)
        else:
            fname, _ = QtWidgets.QFileDialog.getOpenFileName(
                parent=None,
                caption=f"Open File for {self.name}",
                dir=directory,
                filter=";;".join([*self.file_filters, "All Files (*)"]),
            )
        self.log.debug(repr(fname))
        if fname:
            self.update_value(fname)

    def new_default_widget(self):
        line_edit = QtWidgets.QLineEdit()
        btn = QtWidgets.QPushButton("...")
        btn.setMaximumWidth(30)
        self.connect_to_browse_widgets(line_edit, btn)
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(widget)
        layout.setSpacing(0)
        layout.addWidget(line_edit)
        layout.addWidget(btn)
        return widget

    def on_drag_enter(self, event: QtGui.QDragEnterEvent):
        if event.mimeData().hasUrls():
            fname = Path([u.toLocalFile() for u in event.mimeData().urls()][0])
            valid_suffixes = re.findall(r"\*\.(\w+)", ";;".join([*self.file_filters]))
            if not self.file_filters or fname.suffix[1:] in valid_suffixes:
                event.accept()
                return

        event.ignore()

    def on_drop(self, event: QtGui.QDropEvent, widget: QtWidgets.QLineEdit):
        fname = Path([u.toLocalFile() for u in event.mimeData().urls()][0])
        widget.setText(str(fname))
        widget.editingFinished.emit()
