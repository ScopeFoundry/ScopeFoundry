from dataclasses import dataclass, field
from typing import Callable, Dict, List, Tuple

from qtpy import QtCore, QtGui, QtWidgets

from ScopeFoundry.dynamical_widgets.tools import Tools
from ScopeFoundry.helper_funcs import filter_with_patterns


class OperationsQObject(QtCore.QObject):

    added = QtCore.Signal(str)
    removed = QtCore.Signal(str)


@dataclass
class Operation:
    name: str
    func: Callable
    description: str = field(default="")
    icon_path: str = field(default="")

    def new_button(self):
        op_button = QtWidgets.QPushButton(self.name)
        op_button.setObjectName(self.name)
        op_button.clicked.connect(lambda checked, f=self.func: f())
        if self.description:
            op_button.setToolTip(self.description)
        if self.icon_path:
            op_button.setIcon(QtGui.QIcon(str(self.icon_path)))
        return op_button


class Operations:

    def __init__(self):
        self.q_object = OperationsQObject()
        self._widgets_managers_: List[OperationWidgetsManager] = []
        self._operations: Dict[str, Operation] = {}

    def new(self, name: str, func: Callable, description="", icon_path="") -> Operation:
        return self.add(Operation(name, func, description, icon_path))

    def add(self, operation: Operation) -> Operation:
        assert operation.name not in self._operations
        self._operations[operation.name] = operation
        self.q_object.added.emit(operation.name)
        return operation

    def remove(self, name) -> None:
        if name not in self._operations:
            return
        del self._operations[name]
        self.q_object.removed.emit(name)

    def get(self, name) -> Operation:
        return self._operations[name]

    def new_button(self, name) -> QtWidgets.QPushButton:
        return self._operations[name].new_button()

    def keys(self):
        return self._operations.keys()

    def __contains__(self, k):
        return self._operations.__contains__(k)

    def __iter__(self):
        return self._operations.__iter__()

    # For backwards compatbility, returning op_func rather the Operation objects.
    def items(self):
        return ((k, v.func) for k, v in self._operations.items())

    def __getitem__(self, key) -> Callable:
        return self._operations[key].func


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
