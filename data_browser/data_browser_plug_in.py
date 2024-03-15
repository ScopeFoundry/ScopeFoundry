from qtpy import QtCore, QtWidgets

from ScopeFoundry.logged_quantity import LQCollection


class DataBrowserPlugIn(QtCore.QObject):

    """Abstract class for DataBrowserPlugIn"""

    name = "base plugin"  # Override me
    button_text = "☔base"  # override me
    show_keyboard_key = None  # (optional) override me : e.g QtCore.Qt.Key_Q
    description = ""  # (optional) override me, include '(Ctrl + Q)' if applicable

    def setup(self):
        """Override this method"""
        # set self.ui here
        # has self.settings

    def update(self, fname: str = None) -> None:
        """Override this method. This method is called on show plugin and when data_filename has changed."""
        # guard against unsupported files
        # load file, extract information, update ui ...

    def __init__(self, databrowser):
        QtCore.QObject.__init__(self)

        self.databrowser = databrowser
        self.settings = LQCollection()
        self.ui = None
        self.is_loaded = False

        self.show_button = QtWidgets.QPushButton(self.button_text)
        self.show_button.setCheckable(True)
        self.show_button.setChecked(False)
        self.show_button.toggled[bool].connect(self.on_show_toggle)
        self.show_button.setToolTip(f"<b>{self.name}</b> {self.description}")

    @property
    def is_showing(self):
        return self.show_button.isChecked()

    def update_if_showing(self, fname: str):
        if self.is_showing:
            self.update(fname)

    def get_show_hide_button(self):
        btn = self.show_button
        s = f"""QPushButton:!checked{{ background::rgba(216, 223, 235,0.3); border: 1px solid grey; }}
                QPushButton:checked{{ background:rgba(216, 223, 235 ,1); border: 1px solid grey; }}"""
        self.show_button.setStyleSheet(btn.styleSheet() + s)
        return self.show_button

    def toggle_show_hide(self):
        self.show_button.setChecked(not self.show_button.isChecked())

    def show(self):
        if not self.is_loaded:
            self.setup()
            self.is_loaded = True
            if self.ui is not None:
                self.databrowser.ui.data_view_layout.addWidget(self.ui)

        if self.ui is None:
            return

        self.ui.show()

    def hide(self):
        if self.ui is None:
            return
        self.ui.hide()

    def on_show_toggle(self, show):
        if show:
            self.show()
            self.update(self.new_fname)
        else:
            self.hide()

    @property
    def new_fname(self):
        return self.databrowser.settings["data_filename"]
