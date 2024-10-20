from __future__ import absolute_import, print_function

import threading
import time
import warnings
from collections import OrderedDict

import pyqtgraph as pg
from qtpy import QtCore, QtWidgets, QtGui

from ScopeFoundry.logged_quantity.tree import ObjSubtree
from .base_app import BaseMicroscopeApp
from .helper_funcs import QLock, get_logger_from_class
from .logged_quantity import LQCollection


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
        self.operations = OrderedDict()
        self.sub_trees = []

        self.tree_item = None

        self.log = get_logger_from_class(self)

        # threading lock
        # self.lock = threading.Lock()
        # self.lock = DummyLock()
        self.lock = QLock(mode=1)  # mode 0 is non-reentrant lock

        self.app = app

        self.connected = self.settings.New(
            "connected",
            dtype=bool,
            colors=["none", "rgba( 0, 255, 0, 120)"],
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
            except Exception as err:
                self.connection_failed.emit()
                raise err
        else:
            print("disabling connection")
            try:
                try:
                    if hasattr(self, "run") and hasattr(self, "_update_thread"):
                        self.update_thread_interrupted = True
                        self._update_thread.join(timeout=5.0)
                        del self._update_thread
                finally:
                    self.disconnect()
                    self.update_sub_trees(1, "X", "orange")
            except Exception as err:
                self.update_sub_trees(1, "?", "red")
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
                if self.debug_mode.val:
                    self.log.debug("read_from_hardware {}".format(name))
                lq.read_from_hardware()

    def add_logged_quantity(self, name, **kwargs):
        return self.settings.New(name, **kwargs)

    def add_operation(self, name, op_func):
        """
        Create an operation for the HardwareComponent.

        *op_func* is a function that will be called upon operation activation

        operations are typically exposed in the default ScopeFoundry gui via a pushButton

        :type name: str
        :type op_func: QtCore.Slot
        """

        self.operations[name] = op_func

    def on_connection_succeeded(self):
        print(self.name, "connection succeeded!")
        self.update_sub_trees(1, "O", "green")

    def on_connection_failed(self):
        print(self.name, "connection failed!")
        self.connected.update_value(False)
        self.update_sub_trees(1, "X", "red")

    @property
    def gui(self):
        warnings.warn(
            "Hardware.gui is deprecated, use Hardware.app", DeprecationWarning
        )
        return self.app

    def web_ui(self):
        return "Hardware {}".format(self.name)

    def thread_lock_lq(self, lq):
        lq.old_lock = lq.lock
        lq.lock = self.lock

    def thread_lock_all_lq(self):
        for lq in self.settings.as_list():
            lq.old_lock = lq.lock
            lq.lock = self.lock

    def reload_code(self):
        import inspect

        import xreload

        mod = inspect.getmodule(self)
        x = xreload.xreload(mod)
        print("Reloading from code", mod, x)

    def New_UI(
        self,
        include=None,
        exclude=None,
        style="form",
        include_operations=None,
        title=None,
    ):

        additional_widgets = {}

        if include_operations is None:
            include_operations = self.operations.keys()

        for op_name in include_operations:
            btn = QtWidgets.QPushButton(op_name)
            btn.clicked.connect(self.operations[op_name])
            additional_widgets[op_name] = btn

        return self.settings.New_UI(include, exclude, style, additional_widgets, title)

    def new_control_widgets(self):
        """use Measurement.New_UI for more control"""
        return self.New_UI(None, None, "form", None, self.name)

    def add_sub_tree(self, tree: QtWidgets.QTreeWidget, sub_tree: ObjSubtree):
        self.sub_trees.append(sub_tree)

    def update_sub_trees(self, col, text, color):
        for tree in self.sub_trees:
            tree: ObjSubtree
            tree.set_header(col, text, color)

    def on_right_click(self):
        cmenu = QtWidgets.QMenu()
        a = cmenu.addAction(self.name)
        a.setEnabled(False)
        connect_action = cmenu.addAction("Connect")
        disconnect_action = cmenu.addAction("Disconnect")

        action = cmenu.exec_(QtGui.QCursor.pos())
        if action == connect_action:
            self.settings["connected"] = True
        elif action == disconnect_action:
            self.settings["connected"] = False

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


def new_control_widgets(name, settings: LQCollection, operations: dict):
    controls_groupBox = QtWidgets.QGroupBox(name)
    controls_formLayout = QtWidgets.QFormLayout()
    controls_groupBox.setLayout(controls_formLayout)

    # control_widgets = OrderedDict()
    for lqname, lq in settings.as_dict().items():
        if lq.choices is not None:
            widget = QtWidgets.QComboBox()
        elif lq.dtype in [int, float]:
            if lq.si:
                widget = pg.SpinBox()
            else:
                widget = QtWidgets.QDoubleSpinBox()
        elif lq.dtype in [bool]:
            widget = QtWidgets.QCheckBox()
        elif lq.dtype in [str]:
            widget = QtWidgets.QLineEdit()
        lq.connect_to_widget(widget)

        controls_formLayout.addRow(lqname, widget)
        # control_widgets[lqname] = widget

    for op_name, op_func in operations.items():
        op_button = QtWidgets.QPushButton(op_name)
        op_button.clicked.connect(lambda checked, f=op_func: f())
        controls_formLayout.addRow(op_name, op_button)

    return controls_groupBox
