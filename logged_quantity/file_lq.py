from functools import partial
from pathlib import Path
import re

from qtpy import QtWidgets, QtGui, QtCore

from .logged_quantity import LoggedQuantity


class FileLQ(LoggedQuantity):
    """
    Specialized str type :class:`LoggedQuantity` that handles
    a filename (or directory) and associated file.
    """

    def __init__(self, name, default_dir=None, is_dir=False, file_filters=(), **kwargs):

        if not kwargs["initial"]:
            kwargs["initial"] = ""

        LoggedQuantity.__init__(self, name, dtype=str, **kwargs)

        self.default_dir = default_dir
        self.is_dir = is_dir

        if isinstance(file_filters, str):
            file_filters = [file_filters]
        self.file_filters = file_filters

    def connect_to_browse_widgets(self, lineEdit, pushButton):
        assert type(lineEdit) == QtWidgets.QLineEdit
        self.connect_to_widget(lineEdit)

        lineEdit.setAcceptDrops(True)
        lineEdit.dragEnterEvent = self.on_drag_enter
        lineEdit.dropEvent = partial(self.on_drop, widget=lineEdit)

        assert type(pushButton) == QtWidgets.QPushButton
        pushButton.clicked.connect(self.file_browser)

    def file_browser(self):

        path = Path(self.default_dir) if self.default_dir else Path(self.val)
        if not path.exists():
            path = Path.cwd()

        if path.is_dir():
            directory = str(path)
        else:
            directory = str(path.parent)

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
        lineEdit = QtWidgets.QLineEdit()
        browseButton = QtWidgets.QPushButton("...")
        self.connect_to_browse_widgets(lineEdit, browseButton)
        widget = QtWidgets.QWidget()
        widget.setLayout(QtWidgets.QHBoxLayout())
        widget.layout().addWidget(lineEdit)
        widget.layout().addWidget(browseButton)
        return widget

    def on_drag_enter(self, event: QtGui.QDragEnterEvent):
        if event.mimeData().hasUrls():
            fname = Path([u.toLocalFile() for u in event.mimeData().urls()][0])
            suffixes = re.findall(r"\*\.(\w+)", ";;".join([*self.file_filters]))
            if not self.file_filters or fname.suffix[1:] in suffixes:
                event.accept()
                return

        event.ignore()

    def on_drop(self, event: QtGui.QDropEvent, widget: QtWidgets.QLineEdit):
        fname = Path([u.toLocalFile() for u in event.mimeData().urls()][0])
        widget.setText(str(fname))
        widget.editingFinished.emit()
