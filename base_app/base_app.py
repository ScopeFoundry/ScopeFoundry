"""
Created on Jul 23, 2014

Modified by Ed Barnard
UI enhancements by Ed Barnard, Alan Buckley
"""
from __future__ import absolute_import, division, print_function

import asyncio
import logging
import sys
import time
import traceback
from logging import Handler
from pathlib import Path

import numpy as np
import pyqtgraph as pg
from qtpy import QtCore, QtGui, QtWidgets

from ScopeFoundry.helper_funcs import get_logger_from_class, str2bool
from ScopeFoundry.logged_quantity import LQCollection

try:
    import configparser
except:  # python 2
    import ConfigParser as configparser

try:
    import IPython

    if (
        IPython.version_info[0] < 4
    ):  # compatibility for IPython < 4.0 (pre Jupyter split)
        from IPython.qt.console.rich_ipython_widget import (
            RichIPythonWidget as RichJupyterWidget,
        )
        from IPython.qt.inprocess import QtInProcessKernelManager
    else:
        from qtconsole.inprocess import QtInProcessKernelManager
        from qtconsole.rich_jupyter_widget import RichJupyterWidget
    CONSOLE_TYPE = "qtconsole"
except Exception as err:
    logging.warning(
        "ScopeFoundry unable to import iPython console, using pyqtgraph.console instead. Error: {}".format(
            err
        )
    )
    import pyqtgraph.console

    CONSOLE_TYPE = "pyqtgraph.console"


# from equipment.image_display import ImageDisplay


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

# Dark mode
try:
    import qdarktheme  # pip install pyqtdarktheme

    darktheme_available = True
except Exception as err:
    darktheme_available = False
    print(f"pyqdarktheme unavailable: {err}")


class BaseApp(QtCore.QObject):

    def __init__(self, argv=[], dark_mode=False):
        QtCore.QObject.__init__(self)
        self.log = get_logger_from_class(self)

        path = Path(__file__)
        self.this_path = path.parent
        self.this_filename = path.name

        self.qtapp = QtWidgets.QApplication.instance()
        if not self.qtapp:
            self.qtapp = QtWidgets.QApplication(argv)

        if dark_mode and darktheme_available:
            qdarktheme.setup_theme()

        self.settings = LQCollection()

        # auto creation of console widget
        try:
            self.setup_console_widget()
        except Exception as err:
            print("failed to setup console widget " + str(err))
            self.console_widget = QtWidgets.QWidget()

        # FIXME Breaks things for microscopes, but necessary for stand alone apps!
        # if hasattr(self, "setup"):
        #    self.setup()

        self.setup_logging()

        if not hasattr(self, "name"):
            self.name = "ScopeFoundry"
        self.qtapp.setApplicationName(self.name)

    def exec_(self):
        return self.qtapp.exec_()

    def setup_console_widget(self, kernel=None):
        """
        Create and return console QWidget. If Jupyter / IPython is installed
        this widget will be a full-featured IPython console. If Jupyter is unavailable
        it will fallback to a pyqtgraph.console.ConsoleWidget.

        If the app is started in an Jupyter notebook, the console will be
        connected to the notebook's IPython kernel.

        the returned console_widget will also be accessible as self.console_widget

        In order to see the console widget, remember to insert it into an existing
        window or call self.console_widget.show() to create a new window
        """
        if CONSOLE_TYPE == "pyqtgraph.console":
            self.console_widget = pyqtgraph.console.ConsoleWidget(
                namespace={"app": self, "pg": pg, "np": np}, text="ScopeFoundry Console"
            )
        elif CONSOLE_TYPE == "qtconsole":

            if kernel == None:
                try:  # try to find an existing kernel
                    # https://github.com/jupyter/notebook/blob/master/docs/source/examples/Notebook/Connecting%20with%20the%20Qt%20Console.ipynb
                    import ipykernel as kernel

                    conn_file = kernel.get_connection_file()
                    import qtconsole.qtconsoleapp

                    self.qtconsole_app = qtconsole.qtconsoleapp.JupyterQtConsoleApp()
                    self.console_widget = self.qtconsole_app.new_frontend_connection(
                        conn_file
                    )
                    self.console_widget.setWindowTitle("ScopeFoundry IPython Console")
                except:  # make your own new in-process kernel
                    # https://github.com/ipython/ipython-in-depth/blob/master/examples/Embedding/inprocess_qtconsole.py
                    self.kernel_manager = QtInProcessKernelManager()
                    self.kernel_manager.start_kernel()
                    self.kernel = self.kernel_manager.kernel
                    self.kernel.shell.banner1 += """
                    ScopeFoundry Console
                    
                    Variables:
                     * np: numpy package
                     * app: the ScopeFoundry App object
                    """
                    self.kernel.gui = "qt4"
                    self.kernel.shell.push({"np": np, "app": self})
                    self.kernel_client = self.kernel_manager.client()
                    self.kernel_client.start_channels()

                    # self.console_widget = RichIPythonWidget()
                    self.console_widget = RichJupyterWidget()
                    self.console_widget.setWindowTitle("ScopeFoundry IPython Console")
                    self.console_widget.kernel_manager = self.kernel_manager
                    self.console_widget.kernel_client = self.kernel_client
            else:
                import qtconsole.qtconsoleapp

                self.qtconsole_app = qtconsole.qtconsoleapp.JupyterQtConsoleApp()
                self.console_widget = self.qtconsole_app.new_frontend_connection(
                    kernel.get_connection_file()
                )
                self.console_widget.setWindowTitle("ScopeFoundry IPython Console")
        else:
            raise ValueError("CONSOLE_TYPE undefined")

        return self.console_widget

    def setup(self):
        pass

    def settings_save_ini(self, fname, save_ro=True):
        """"""
        config = configparser.ConfigParser()
        config.optionxform = str
        config.add_section("app")
        config.set("app", "name", self.name)
        for lqname, lq in self.settings.as_dict().items():
            if not lq.ro or save_ro:
                config.set("app", lqname, lq.ini_string_value())

        with open(fname, "w") as configfile:
            config.write(configfile)

        self.log.info("ini settings saved to {} {}".format(fname, config.optionxform))

    def settings_load_ini(self, fname):
        self.log.info("ini settings loading from " + fname)

        config = configparser.ConfigParser()
        config.optionxform = str
        config.read(fname)

        if "app" in config.sections():
            for lqname, new_val in config.items("app"):
                # print(lqname)
                lq = self.settings.as_dict().get(lqname)
                if lq:
                    if lq.dtype == bool:
                        new_val = str2bool(new_val)
                    lq.update_value(new_val)

    def settings_save_ini_ask(self, dir=None, save_ro=True):
        """Opens a Save dialogue asking the user to select a save destination and give the save file a filename. Saves settings to an .ini file."""
        # TODO add default directory, etc
        fname, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.ui, caption="Save Settings", dir="", filter="Settings (*.ini)"
        )
        # print(repr(fname))
        if fname:
            self.settings_save_ini(fname, save_ro=save_ro)
        return fname

    def settings_load_ini_ask(self, dir=None):
        """Opens a Load dialogue asking the user which .ini file to load into our app settings. Loads settings from an .ini file."""
        # TODO add default directory, etc
        fname, _ = QtWidgets.QFileDialog.getOpenFileName(None, "Settings (*.ini)")
        # print(repr(fname))
        if fname:
            self.settings_load_ini(fname)
        return fname

    def setup_logging(self):

        logging.basicConfig(
            level=logging.WARN
        )  # , filename='example.log', stream=sys.stdout)
        logging.getLogger("traitlets").setLevel(logging.WARN)
        logging.getLogger("ipykernel.inprocess").setLevel(logging.WARN)
        logging.getLogger("LoggedQuantity").setLevel(logging.WARN)
        logging.getLogger("PyQt5").setLevel(logging.WARN)
        logger = logging.getLogger("FoundryDataBrowser")

        self.logging_widget = QtWidgets.QWidget()
        self.logging_widget.setWindowTitle("Log")
        self.logging_widget.setLayout(QtWidgets.QVBoxLayout())
        self.logging_widget.search_lineEdit = QtWidgets.QLineEdit()
        self.logging_widget.log_textEdit = QtWidgets.QTextEdit("")

        self.logging_widget.layout().addWidget(self.logging_widget.search_lineEdit)
        self.logging_widget.layout().addWidget(self.logging_widget.log_textEdit)

        self.logging_widget.log_textEdit.document().setDefaultStyleSheet(
            "body{font-family: Courier;}"
        )

        self.logging_widget_handler = LoggingQTextEditHandler(
            self.logging_widget.log_textEdit, level=logging.DEBUG
        )
        logging.getLogger().addHandler(self.logging_widget_handler)


class LoggingQTextEditHandler(Handler, QtCore.QObject):

    new_log_signal = QtCore.Signal((str,))

    def __init__(self, textEdit, level=logging.NOTSET, buffer_len=500):
        self.textEdit = textEdit
        self.buffer_len = buffer_len
        self.messages = []
        Handler.__init__(self, level=level)
        QtCore.QObject.__init__(self)
        self.new_log_signal.connect(self.on_new_log)

    def emit(self, record):
        log_entry = self.format(record)
        self.new_log_signal.emit(log_entry)

    def on_new_log(self, log_entry):
        # self.textEdit.moveCursor(QtGui.QTextCursor.End)
        # self.textEdit.insertHtml(log_entry)
        # self.textEdit.moveCursor(QtGui.QTextCursor.End)
        self.messages.append(log_entry)
        if len(self.messages) > self.buffer_len:
            self.messages = [
                "...<br>",
            ] + self.messages[-self.buffer_len :]
        self.textEdit.setHtml("\n".join(self.messages))
        self.textEdit.moveCursor(QtGui.QTextCursor.End)

    level_styles = dict(
        CRITICAL="color: red;",
        ERROR="color: red;",
        WARNING="color: orange;",
        INFO="color: green;",
        DEBUG="color: green;",
        NOTSET="",
    )

    def format(self, record):
        # timestamp = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(record.created))
        style = self.level_styles.get(record.levelname, "")
        return """{} - <span style="{}">{}</span>: <i>{}</i> :{}<br>""".format(
            timestamp, style, record.levelname, record.name, record.msg
        )


if __name__ == "__main__":
    app = BaseApp(sys.argv)
    sys.exit(app.exec_())
