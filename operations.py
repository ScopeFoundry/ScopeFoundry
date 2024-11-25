from collections import OrderedDict
from typing import Callable

from qtpy import QtCore, QtWidgets, QtGui

from ScopeFoundry.dynamical_widgets.tools import Tools
from ScopeFoundry.helper_funcs import filter_with_patterns


class OperationsQObject(QtCore.QObject):

    added = QtCore.Signal(str)
    removed = QtCore.Signal(str)


class Operations(OrderedDict):

    def __init__(self, other=(), /, **kwds):
        super().__init__(other, **kwds)
        self.q_object = OperationsQObject()
        self._widgets_managers_ = []
        self.descriptions = {}
        self.icon_paths = {}

    def add(self, name: str, func: Callable, description="", icon_path=""):
        if name in self.__dict__:
            return
        self[name] = func
        self.descriptions[name] = description
        self.icon_paths[name] = icon_path
        self.q_object.added.emit(name)

    def remove(self, name):
        if name not in self:
            return
        del self[name]
        del self.descriptions[name]
        del self.icon_paths[name]
        self.q_object.removed.emit(name)

    def new_button(self, name):
        op_button = QtWidgets.QPushButton(name)
        op_button.setObjectName(name)
        op_button.clicked.connect(lambda checked, f=self[name]: f())
        tt = self.descriptions[name]
        if tt:
            op_button.setToolTip(tt)
        icon_path = self.icon_paths[name]
        if icon_path:
            op_button.setIcon(QtGui.QIcon(str(icon_path)))
        return op_button


class OperationWidgetsManager:

    def __init__(self, operations: Operations, tools: Tools) -> None:
        self.operations = operations
        self.tools = tools

        operations.q_object.added.connect(self.add)
        operations.q_object.removed.connect(self.remove)

        self.widgets = {}
        self.update()

    def add(self, name: str):
        self.update()

    def remove(self, name: str):
        widget = self.widgets.pop(name, None)
        if widget is None:
            return
        self.tools.remove_from_layout(name, widget)

    def update(self):
        for op_name in filter_with_patterns(
            self.operations.keys(), self.tools.include, self.tools.exclude
        ):
            if op_name in self.widgets.keys():
                continue
            op_button = self.operations.new_button(op_name)
            self.widgets[op_name] = op_button
            self.tools.add_to_layout(None, op_button)
