"""
Created on Jul 23, 2014

Modified by Ed Barnard
UI enhancements by Ed Barnard, Alan Buckley
"""

import asyncio
import enum
import logging
import sys
import traceback
from pathlib import Path
from typing import Callable
from warnings import warn

from qtpy import QtCore, QtWidgets

from ScopeFoundry import ini_io
from ScopeFoundry.base_app.console_widget import new_console_widget
from ScopeFoundry.base_app.logging_handlers import HtmlHandler
from ScopeFoundry.base_app.logging_widget import LoggingWidget
from ScopeFoundry.helper_funcs import get_logger_from_class
from ScopeFoundry.logged_quantity import LQCollection, LoggedQuantity
from ScopeFoundry.dynamical_widgets.tree_widget import SubtreeManager
from ScopeFoundry.operations import Operations


# See https://riverbankcomputing.com/pipermail/pyqt/2016-March/037136.html
# makes sure that unhandled exceptions in slots don't crash the whole app with PyQt 5.5 and higher
# old version:
## sys.excepthook = traceback.print_exception
# new version to send to logger
def log_unhandled_exception(*exc_info):
    text = "".join(traceback.format_exception(*exc_info))
    logging.critical("Unhandled exception:" + text)
    # print("Unhandled exception:" + text)


sys.excepthook = log_unhandled_exception


# To fix a bug with jupyter qtconsole for python 3.8
# https://github.com/jupyter/notebook/issues/4613#issuecomment-548992047
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class WRITE_RES(enum.Enum):
    SUCCESS = enum.auto()
    MISSING = enum.auto()
    PROTECTED = enum.auto()


class BaseApp(QtCore.QObject):

    name = "ScopeFoundry"

    def __init__(self, argv=[], **kwargs):
        super().__init__()

        self.qtapp = QtWidgets.QApplication.instance()
        if not self.qtapp:
            self.qtapp = QtWidgets.QApplication(argv)
        self.qtapp.setApplicationName(self.name)

        self.q_object = BaseAppQObject()

        self.setup_logging()
        self.setup_console_widget()

        path = Path(__file__)
        self.this_path = path.parent
        self.this_filename = path.name

        self._setting_paths = {}
        self.settings = LQCollection(path="app")
        self.add_lq_collection_to_settings_path(self.settings)

        self.operations = Operations()
        self._subtree_managers_ = []
        self._widgets_managers_ = []

        # self.setup_dark_mode_option(dark_mode=kwargs.get("dark_mode", None))

    def setup_dark_mode_option(self, dark_mode: bool = None):
        if hasattr(self.qtapp.styleHints(), "setColorScheme"):
            choices = ("dark", "light", "system")
            if dark_mode is None:
                initial = "system"
            elif dark_mode:
                initial = "dark"
            else:
                initial = "light"
            self.settings.New(
                name="dark_mode",
                dtype=str,
                choices=choices,
                initial=initial,
                description="<i>system</i> let the operating system decide",
            ).add_listener(self.set_color_scheme)
        elif dark_mode:
            warn(
                "dark mode selection only available with Qt6.8+: pip install PyQt6 or pip install --upgrade PyQt6. trying to use qdarkmode",
                RuntimeWarning,
            )
            try:
                import qdarktheme  # pip install pyqtdarktheme

                qdarktheme.setup()
            except Exception as err:
                warn(
                    "trying to use qdarkmode failed. pip install pyqtdarktheme",
                    RuntimeWarning,
                )
            print(f"pyqdarktheme unavailable: {err}")

        else:
            warn(
                "dark mode selection only available with Qt6.8+: pip install PyQt6 or pip install --upgrade PyQt6",
                RuntimeWarning,
            )

    def set_color_scheme(self, choice):
        if choice == "dark":
            choice = QtCore.Qt.ColorScheme.Dark
        elif choice == "light":
            choice = QtCore.Qt.ColorScheme.Light
        elif choice == "system":
            choice = QtCore.Qt.ColorScheme.Unknown
        self.qtapp.styleHints().setColorScheme(choice)

    def exec_(self):
        return self.qtapp.exec_()

    def setup(self):
        pass

    def setup_console_widget(self, kernel=None):
        try:
            self.console_widget = new_console_widget(self, kernel)
        except Exception as err:
            print("failed to setup console widget " + str(err))
            self.console_widget = QtWidgets.QWidget()
        return self.console_widget

    def setup_logging(self):
        self.log = get_logger_from_class(self)

        logging.basicConfig(level=logging.WARN)
        logging.getLogger("traitlets").setLevel(logging.WARN)
        logging.getLogger("ipykernel.inprocess").setLevel(logging.WARN)
        logging.getLogger("LoggedQuantity").setLevel(logging.WARN)
        logging.getLogger("PyQt5").setLevel(logging.WARN)

        self.logging_widget = LoggingWidget()
        handler = HtmlHandler(level=logging.DEBUG)
        handler.new_log_signal.connect(self.logging_widget.on_new_log)
        logging.getLogger().addHandler(handler)

    def settings_save_ini_ask(self, dir=None, save_ro=True):
        """Opens a Save dialogue asking the user to select a save destination and give the save file a filename. Saves settings to an .ini file."""
        # TODO add default directory, etc
        fname, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.ui, caption="Save Settings", dir="", filter="Settings (*.ini)"
        )
        if fname:
            self.settings_save_ini(fname, save_ro=save_ro)
        return fname

    def settings_load_ini_ask(self, dir=None):
        """Opens a Load dialogue asking the user which .ini file to load into our app settings. Loads settings from an .ini file."""
        # TODO add default directory, etc
        fname, _ = QtWidgets.QFileDialog.getOpenFileName(None, "Settings (*.ini)")
        if fname:
            self.settings_load_ini(fname)
        return fname

    def on_new_subtree(self, subtree: SubtreeManager): ...

    def on_right_click(self): ...

    def add_setting_path(self, lq: LoggedQuantity):
        self._setting_paths[lq.path] = lq

    def remove_setting_path(self, lq: LoggedQuantity):
        self._setting_paths.pop(lq.path, None)

    def add_lq_collection_to_settings_path(self, settings: LQCollection):
        settings.q_object.lq_added.connect(self.add_setting_path)
        settings.q_object.lq_removed.connect(self.remove_setting_path)
        for lq in settings.as_dict().values():
            self.add_setting_path(lq)

    def write_setting(self, path: str, value):
        lq = self.get_lq(path)
        if lq is None:
            return WRITE_RES.MISSING
        lq.update_value(value)
        return WRITE_RES.SUCCESS

    def write_setting_safe(self, path: str, value):
        lq = self.get_lq(path)
        if lq is None:
            return WRITE_RES.MISSING
        elif lq.protected:
            return WRITE_RES.PROTECTED
        lq.update_value(value)
        return WRITE_RES.SUCCESS

    def get_lq(self, path: str) -> LoggedQuantity:
        """
        returns the LoggedQuantity defined by a path string.
        """
        return self._setting_paths.get(path, None)

    def write_settings_safe(self, settings):
        """
        updates settings based on a dictionary.

        ==============  =========  ====================================================================================
        **Arguments:**  **Type:**  **Description:**
        settings        dict       (path, value) map
        ==============  =========  ====================================================================================
        """
        report = {}
        for path, value in settings.items():
            success = self.write_setting_safe(path, value)
            report[path] = success
        return report

    def settings_save_ini(self, fname, save_ro=True):
        """
        ==============  =========  ==============================================
        **Arguments:**  **Type:**  **Description:**
        fname           str        relative path to the filename of the ini file.
        ==============  =========  ==============================================
        """
        settings = self.read_settings(None, True)
        ini_io.save_settings(fname, settings)

        if not save_ro:
            settings = {k: v for k, v in settings.items() if not self.get_lq(k).ro}

        self.propose_settings_values(Path(fname).name, settings)

        self.log.info(f"ini settings saved to {fname} str")

    def settings_load_ini(self, fname):
        """
        ==============  =========  ==============================================
        **Arguments:**  **Type:**  **Description:**
        fname           str        relative path to the filename of the ini file.
        ==============  =========  ==============================================
        """
        settings = ini_io.load_settings(fname)
        self.write_settings_safe(settings)
        self.propose_settings_values(Path(fname).name, settings)
        return settings

    def propose_settings_values(self, name: str, settings):
        """
        Adds to proposed_values of LQs.
        proposed_values can be inspected with right click on connected widgets

        ==============  =========  ====================================================================================
        **Arguments:**  **Type:**  **Description:**
        name            str        label of the proposed value
        settings        dict       (path, value) map
        ==============  =========  ====================================================================================
        """
        for path, val in settings.items():
            lq = self.get_lq(path)
            if lq is None:
                continue
            lq.propose_value(name, val)

    def read_settings(self, paths=None, ini_string_value=False):
        """
        returns a dictionary (path, value):
        ================== =========  =============================================================================
        **Arguments:**     **Type:**  **Description:**
        paths              list[str]  paths to setting, if None(default) all paths are used
        ================== =========  =============================================================================
        """
        paths = self._setting_paths if paths is None else paths
        return {p: self.read_setting(p, ini_string_value) for p in paths}

    def read_setting(self, path: str, ini_string_value=False):
        lq = self.get_lq(path)
        if ini_string_value:
            return lq.ini_string_value()
        return lq.val

    def add_operation(self, name: str, op_func: Callable[[], None], description=""):
        """
        Create an operation for the App.

        *op_func* is a function that will be called upon operation activation

        operations are typically exposed in the default ScopeFoundry gui via a pushButton

        :type name: str
        :type op_func: QtCore.Slot or Callable without Argument
        :type description: str
        """
        self.operations.add(name, op_func, description)

    def remove_operation(self, name: str):
        self.operations.remove(name)


class BaseAppQObject(QtCore.QObject):
    pass


class TestBaseApp(BaseApp):

    name = "test base app"

    def __init__(self, argv=[], **kwargs):
        super().__init__(argv, **kwargs)

        self.ui = QtWidgets.QWidget()
        self.ui.show()
        self.console_widget.show()
        self.logging_widget.show()
        self.setup_dark_mode_option(kwargs.get("dark_mode", False))


if __name__ == "__main__":
    # app = BaseApp(sys.argv)
    app = TestBaseApp(sys.argv, dark_mode=False)
    sys.exit(app.exec_())
