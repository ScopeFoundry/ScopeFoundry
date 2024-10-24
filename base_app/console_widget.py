import logging

import numpy as np
import pyqtgraph as pg

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


def new_console_widget(self, kernel=None):
    """
    Create and return console QWidget. If Jupyter / IPython is installed
    this widget will be a full-featured IPython console. If Jupyter is unavailable
    it will fallback to a pyqtgraph.console.ConsoleWidget.

    If the app is started in an Jupyter notebook, the console will be
    connected to the notebook's IPython kernel.

    the returned console_widget will also be accessible as console_widget

    In order to see the console widget, remember to insert it into an existing
    window or call console_widget.show() to create a new window
    """
    if CONSOLE_TYPE == "pyqtgraph.console":
        console_widget = pyqtgraph.console.ConsoleWidget(
            namespace={"app": self, "pg": pg, "np": np}, text="ScopeFoundry Console"
        )
    elif CONSOLE_TYPE == "qtconsole":

        if kernel is None:
            try:  # try to find an existing kernel
                # https://github.com/jupyter/notebook/blob/master/docs/source/examples/Notebook/Connecting%20with%20the%20Qt%20Console.ipynb
                import ipykernel as kernel

                conn_file = kernel.get_connection_file()
                import qtconsole.qtconsoleapp

                app = qtconsole.qtconsoleapp.JupyterQtConsoleApp()
                console_widget = app.new_frontend_connection(conn_file)
                console_widget.setWindowTitle("ScopeFoundry IPython Console")
            except:  # make your own new in-process kernel
                # https://github.com/ipython/ipython-in-depth/blob/master/examples/Embedding/inprocess_qtconsole.py
                kernel_manager = QtInProcessKernelManager()
                kernel_manager.start_kernel()
                kernel = kernel_manager.kernel
                kernel.shell.banner1 += """
                ScopeFoundry Console
                
                Variables:
                    * np: numpy package
                    * app: the ScopeFoundry App object
                """
                kernel.gui = "qt4"
                kernel.shell.push({"np": np, "app": self})
                kernel_client = kernel_manager.client()
                kernel_client.start_channels()

                # console_widget = RichIPythonWidget()
                console_widget = RichJupyterWidget()
                console_widget.setWindowTitle("ScopeFoundry IPython Console")
                console_widget.kernel_manager = kernel_manager
                console_widget.kernel_client = kernel_client
        else:
            import qtconsole.qtconsoleapp

            app = qtconsole.qtconsoleapp.JupyterQtConsoleApp()
            console_widget = app.new_frontend_connection(kernel.get_connection_file())
            console_widget.setWindowTitle("ScopeFoundry IPython Console")
    else:
        raise ValueError("CONSOLE_TYPE undefined")

    return console_widget
