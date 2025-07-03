import json
import sys
import threading
import time
import warnings
from functools import partial
from pathlib import Path
from typing import Callable

from qtpy import QtCore, QtGui, QtWidgets

from .base_app import BaseMicroscopeApp
from .dynamical_widgets import add_to_layout, new_widget
from .dynamical_widgets.tree_widget import SubtreeManager
from .helper_funcs import (
    QLock,
    get_child_path,
    get_logger_from_class,
    init_docs_path,
    itemize_launchers,
)
from .logged_quantity import LQCollection
from .operations import Operations


class HardwareComponent:
    """
    :class:`HardwareComponent`

    Base class for ScopeFoundry Hardware objects

    to subclass, implement :meth:`setup`, :meth:`connect` and :meth:`disconnect`

    """

    def __init__(self, app: BaseMicroscopeApp, debug: bool = False, name: str = None):
        """
        create new HardwareComponent attached to *app*
        """
        if not hasattr(self, "name"):
            self.name = self.__class__.__name__

        if name is not None:
            self.name = name

        self.settings = LQCollection(path=f"hw/{self.name}")
        self.operations = Operations(path=f"hw/{self.name}")
        self._subtree_managers_ = []
        self._widgets_managers_ = []

        self.log = get_logger_from_class(self)
        self.docs_path = get_child_path(self) / "docs"

        # threading lock
        # self.lock = threading.Lock()
        # self.lock = DummyLock()
        self.lock = QLock(mode=1)  # mode 0 is non-reentrant lock

        self.app = app

        self.toggle_to_connected_count = 0

        self.connected = self.settings.New(
            "connected",
            dtype=bool,
            colors=["none", "rgba( 0, 255, 0, 80)"],
            description=f"to <i>{self.name}</i> hardware if checked.",
        )

        self.debug_mode = self.settings.New(
            "debug_mode", dtype=bool, initial=debug, colors=["none", "yellow"]
        )

        # self.connect_success = False # ever used?
        self.auto_thread_lock = True

        self.setup()

        if self.auto_thread_lock:
            self.thread_lock_all_lq()

        # self.has_been_connected_once = False # ever used?
        # self.is_connected = False # ever used?

        self.q_object = HardwareQObject()
        self.connection_succeeded = self.q_object.connection_succeeded
        self.connection_failed = self.q_object.connection_failed

        self.add_operation("Reload Code", self.reload_code)
        self.add_operation("Read from\nHardware", self.read_from_hardware)

        self.q_object.connection_failed.connect(self.on_connection_failed)
        self.q_object.connection_succeeded.connect(self.on_connection_succeeded)
        self.connected.updated_value[bool].connect(self.enable_connection)

    def enable_connection(self, enable=True):
        if enable:
            try:
                self.connect()
                # start thread if needed
                if hasattr(self, "run"):
                    self.update_thread_interrupted = False
                    self._update_thread = threading.Thread(target=self.run)
                    self._update_thread.start()

                self.connection_succeeded.emit()
                self.toggle_to_connected_count += 1
                print(f"{self.name} connected {self.toggle_to_connected_count} times")
            except Exception as err:
                self.connection_failed.emit()
                raise err
        else:
            if not self.has_been_connected_once:
                return
            try:
                try:
                    if hasattr(self, "run") and hasattr(self, "_update_thread"):
                        self.update_thread_interrupted = True
                        self._update_thread.join(timeout=5.0)
                        del self._update_thread
                finally:
                    self.disconnect()
                    self.set_connection_status("", "orange")
            except Exception as err:
                self.set_connection_status("⚠", "red")
                raise err

    def run(self):
        if hasattr(self, "threaded_update"):
            while not self.update_thread_interrupted:
                try:
                    self.threaded_update()
                except Exception as err:
                    print("threaded update failed", err)
                    time.sleep(1.0)

    def read_from_hardware(self):
        """
        Read all settings (:class:`LoggedQuantity`) connected to hardware states
        """
        for name, lq in self.settings.as_dict().items():
            if lq.has_hardware_read():
                lq.read_from_hardware()
                if self.debug_mode.val:
                    self.log.debug(f"read_from_hardware {name}: {lq.val}")

    def add_logged_quantity(self, name, **kwargs):
        return self.settings.New(name, **kwargs)

    def on_connection_succeeded(self):
        print(self.name, "connection succeeded!")
        self.connected.update_value(True)
        self.set_connection_status("✓", "green")

    def on_connection_failed(self):
        print(self.name, "connection failed!")
        self.connected.update_value(False)
        self.set_connection_status("⚠", "red")

    @property
    def gui(self):
        warnings.warn(
            "Hardware.gui is deprecated, use Hardware.app", DeprecationWarning
        )
        return self.app

    def web_ui(self):
        return f"Hardware {self.name}"

    def thread_lock_lq(self, lq):
        lq.old_lock = lq.lock
        lq.lock = self.lock

    def thread_lock_all_lq(self):
        for lq in self.settings.as_list():
            lq.old_lock = lq.lock
            lq.lock = self.lock

    def reload_code(self):
        import inspect

        if sys.version_info[1] <= 11:
            import xreload
        else:
            from ScopeFoundry import xreload

        mod = inspect.getmodule(self)

        x = xreload.xreload(mod)
        print("Reloaded code", x)

    def New_UI(self):
        scroll_area = self.settings.New_UI(style="scroll_form")
        for name in self.operations:
            btn = self.operations.new_button(name)
            scroll_area.widget().layout().addRow(btn)
        return scroll_area

    def new_control_widgets(
        self, title: str = None, include=None, exclude=None, style="scroll_form"
    ):
        """creates scroll area group box that updates on dynamical add/remove of settings/operations"""
        if title is None:
            title = self.name
        return new_widget(self, title, include, exclude, style)

    def add_to_layout(self, layout, include=None, exclude=None):
        add_to_layout(self, layout, include, exclude)

    def add_operation(
        self, name: str, op_func: Callable[[], None], description="", icon_path=""
    ):
        """
        Create an operation for the HardwareComponent.

        *op_func* is a function that will be called upon operation activation

        operations are typically exposed in the default ScopeFoundry gui via a pushButton

        :type name: str
        :type op_func: QtCore.Slot or Callable without Argument
        :type description: str
        """
        self.operations.new(name, op_func, description, icon_path)

    def remove_operation(self, name):
        self.operations.remove(name)

    def on_new_subtree(self, subtree: SubtreeManager):
        status_text = QtWidgets.QLabel()

        connect_cb = QtWidgets.QCheckBox()
        s0 = connect_cb.styleSheet()
        self.settings.get_lq("connected").connect_to_widget(connect_cb)
        connect_cb.setStyleSheet(s0)
        connect_cb.setFixedWidth(22)
        connect_cb.setFixedHeight(22)
        connect_cb.setToolTip(f"connect/disconnect {self.name}")

        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(widget)
        layout.addWidget(status_text)
        layout.addWidget(connect_cb)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        subtree.tree_widget.setItemWidget(subtree.header_item, 1, widget)
        subtree.status_text = status_text

    def set_connection_status(self, text, color):
        for manager in self._subtree_managers_:
            manager.status_text.setText(text)
            manager.status_text.setStyleSheet(f"QLabel {{color : {color}; }}")

    def on_right_click(self):
        cmenu = QtWidgets.QMenu()
        a = cmenu.addAction(self.name)
        a.setEnabled(False)

        connect = partial(self.settings.get_lq("connected").update_value, True)
        disconnect = partial(self.settings.get_lq("connected").update_value, False)

        cmenu.addAction("Connect", connect)
        cmenu.addAction("Disconnect", disconnect)
        cmenu.addAction("Read from Hardware", self.read_from_hardware)

        init_docs_path(self.docs_path, self.settings)
        pairs = itemize_launchers(self.docs_path, self.app.launch_browser)
        if pairs:
            cmenu.addSeparator()
            for name, func in pairs:
                cmenu.addAction(name, func)

        cmenu.exec_(QtGui.QCursor.pos())

    @property
    def has_been_connected_once(self) -> bool:
        """
        Returns True if the hardware has been connected at least once
        """
        return self.toggle_to_connected_count > 0

    @property
    def is_connected(self) -> bool:
        """
        Returns True if the hardware is currently connected
        """
        return self.settings["connected"]

    def setup(self):
        """
        Runs during __init__, before the hardware connection is established
        Should generate desired LoggedQuantities, operations
        """
        raise NotImplementedError()

    def connect(self):
        """
        Opens a connection to hardware
        and connects :class:`LoggedQuantity` settings to related hardware
        functions and parameters
        """
        raise NotImplementedError()

    def disconnect(self):
        """
        Disconnects the hardware and severs hardware--:class:`LoggedQuantity` links
        """

        raise NotImplementedError()


class HardwareQObject(QtCore.QObject):

    connection_succeeded = QtCore.Signal()
    connection_failed = QtCore.Signal()
