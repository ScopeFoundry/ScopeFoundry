from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

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
    path: str = field(default="")
    keyboard_shortcut: Optional[str] = field(default=None)

    def new_button(self) -> QtWidgets.QPushButton:
        op_button = QtWidgets.QPushButton(self.name)
        op_button.setObjectName(self.name)
        op_button.clicked.connect(lambda checked, f=self.func: f())
        tooltip = f"<b>{self.path}</b><p><p>{self.description}"
        if self.keyboard_shortcut:
            tooltip += f"<p>Shortcut: {self.keyboard_shortcut}"
        op_button.setToolTip(tooltip)
        if isinstance(self.icon_path, QtGui.QIcon):
            op_button.setIcon(self.icon_path)
        elif self.icon_path:
            op_button.setIcon(QtGui.QIcon(str(self.icon_path)))
        return op_button


class Operations:

    def __init__(self, path="") -> None:
        self.q_object = OperationsQObject()
        self._widgets_managers_: List[OperationWidgetsManager] = []
        self._operations: Dict[str, Operation] = {}
        self._shortcuts: Dict[str, QtWidgets.QShortcut] = {}
        self._shortcut_parent: Optional[QtWidgets.QWidget] = None
        self.path = path

    def set_shortcut_parent(self, parent: QtWidgets.QWidget) -> None:
        """Registers keyboard shortcuts (now and for future operations) on *parent*.
        QShortcut needs a widget parent, which only exists once the gui is created."""
        self._shortcut_parent = parent
        for op in self._operations.values():
            self._register_shortcut(op)

    def _register_shortcut(self, operation: Operation) -> None:
        if (
            not operation.keyboard_shortcut
            or self._shortcut_parent is None
            or operation.name in self._shortcuts
        ):
            return
        shortcut = QtWidgets.QShortcut(
            QtGui.QKeySequence(operation.keyboard_shortcut), self._shortcut_parent
        )
        shortcut.setContext(QtCore.Qt.ApplicationShortcut)
        shortcut.activated.connect(lambda f=operation.func: f())
        self._shortcuts[operation.name] = shortcut

    def new(
        self,
        name: str,
        func: Callable,
        description: str = "",
        icon_path: str = "",
        keyboard_shortcut: Optional[str] = None,
    ) -> Operation:
        return self.add(
            Operation(
                name,
                func,
                description,
                icon_path,
                f"{self.path}/{name}",
                keyboard_shortcut,
            )
        )

    def add(self, operation: Operation) -> Operation:
        assert operation.name not in self._operations
        self._operations[operation.name] = operation
        self._register_shortcut(operation)
        self.q_object.added.emit(operation.name)
        return operation

    def remove(self, name: str) -> None:
        operation = self._operations.pop(name, None)
        if operation is None:
            return
        shortcut = self._shortcuts.pop(name, None)
        if shortcut is not None:
            shortcut.setEnabled(False)
            shortcut.deleteLater()
        self.q_object.removed.emit(name)

    def get(self, name: str) -> Operation:
        return self._operations[name]

    def new_button(self, name: str) -> QtWidgets.QPushButton:
        return self._operations[name].new_button()

    def keys(self) -> List[str]:
        return self._operations.keys()

    def __contains__(self, k: str) -> bool:
        return self._operations.__contains__(k)

    def __iter__(self) -> iter:
        return self._operations.__iter__()

    # For backwards compatbility, returning op_func rather the Operation objects.
    def items(self) -> List[Tuple[str, Callable]]:
        return ((k, v.func) for k, v in self._operations.items())

    def __getitem__(self, key: str) -> Callable:
        return self._operations[key].func


class OperationWidgetsManager:

    def __init__(self, operations: Operations, tools: Tools) -> None:
        self.operations = operations
        self.tools = tools

        operations.q_object.added.connect(self.add)
        operations.q_object.removed.connect(self.remove)

        self.widgets = {}
        self.update()

    def add(self, name: str) -> None:
        self.update()

    def remove(self, name: str) -> None:
        widget = self.widgets.pop(name, None)
        if widget is None:
            return
        self.tools.remove_from_layout(name, widget)

    def update(self) -> None:
        for op_name in filter_with_patterns(
            self.operations.keys(), self.tools.include, self.tools.exclude
        ):
            if op_name in self.widgets.keys():
                continue
            op_button = self.operations.new_button(op_name)
            self.widgets[op_name] = op_button
            self.tools.add_to_layout(None, op_button)
