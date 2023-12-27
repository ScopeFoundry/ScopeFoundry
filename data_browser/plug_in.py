from qtpy import QtCore, QtWidgets

from ScopeFoundry.logged_quantity import LQCollection


class DataBrowserPlugin(QtCore.QObject):

    """Abstract class for DataBrowser Views"""

    name = "base plugin"  # Override me
    button_text = "🔍base"  # (optional) override me
    show_keyboard_key = None  # (optional) override me : e.g QtCore.Qt.Key_F

    def setup(self):
        """Override this method"""
        pass

    def update(self, fname: str = None) -> None:
        """is evoked if loaded evaluates to True, somewhat analogous to on_change_filename for viewers"""
        pass

    def __init__(self, databrowser):
        QtCore.QObject.__init__(self)
        self.databrowser = databrowser
        self.settings = LQCollection()
        self.ui = None

        self.show_button = QtWidgets.QPushButton(self.button_text)
        self.show_button.setCheckable(True)
        self.show_button.toggled[bool].connect(self.on_show_toggle)
        self.show_button.setToolTip(self.name)

        self.is_loaded = False

    def update_if_showing(self, fname: str):
        if self.is_showing:
            self.update(fname)

    @property
    def new_fname(self):
        return self.databrowser.settings["data_filename"]

    def get_hide_show_button(self):
        btn = self.show_button
        s = f"""QPushButton:!checked{{ background::rgba(216, 223, 235,0.3); border: 1px solid grey; }}
                QPushButton:checked{{ background:rgba(216, 223, 235 ,1); border: 1px solid grey; }}"""
        self.show_button.setStyleSheet(btn.styleSheet() + s)
        return self.show_button

    def toggle_show_hide(self):
        self.show_button.setChecked(not self.show_button.isChecked())

    @property
    def is_showing(self):
        return self.show_button.isChecked()

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
        else:
            self.hide()
