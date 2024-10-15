import os

from qtpy import QtWidgets

from .logged_quantity import LoggedQuantity


class FileLQ(LoggedQuantity):
    """
    Specialized str type :class:`LoggedQuantity` that handles
    a filename (or directory) and associated file.
    """

    def __init__(self, name, default_dir=None, is_dir=False, **kwargs):
        kwargs.pop("dtype", None)

        LoggedQuantity.__init__(self, name, dtype=str, **kwargs)

        self.default_dir = default_dir
        self.is_dir = is_dir

    def connect_to_browse_widgets(self, lineEdit, pushButton):
        assert type(lineEdit) == QtWidgets.QLineEdit
        self.connect_to_widget(lineEdit)

        if self.default_dir is not None:
            lineEdit.setText(self.default_dir)
        else:
            lineEdit.setText(os.getcwd())

        assert type(pushButton) == QtWidgets.QPushButton
        pushButton.clicked.connect(self.file_browser)

    def file_browser(self):
        if self.is_dir:
            fname = QtWidgets.QFileDialog.getExistingDirectory(
                directory=self.default_dir
            )
        else:
            fname, _ = QtWidgets.QFileDialog.getOpenFileName(directory=self.default_dir)
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
