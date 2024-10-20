from functools import partial
from typing import OrderedDict, Protocol

from qtpy import QtCore, QtGui, QtWidgets

from ScopeFoundry.logged_quantity import ArrayLQ, FileLQ, LoggedQuantity, LQCollection


class SubtreeAbleObj(Protocol):

    name: str
    settings: LQCollection
    operations: OrderedDict

    def add_sub_tree(self, tree: QtWidgets.QTreeWidget, sub_tree): ...

    def on_right_click(self): ...


def new_tree(objs: list[SubtreeAbleObj], header=["col0", ""]) -> QtWidgets.QTreeWidget:
    tree = QtWidgets.QTreeWidget()
    tree.setColumnCount(len(header))
    tree.setHeaderLabels(header)
    tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
    tree.customContextMenuRequested.connect(partial(on_right_click, tree=tree))

    for obj in objs:
        ObjSubtree(tree, obj)

    return tree


class SFQTreeWidgetItem(QtWidgets.QTreeWidgetItem):

    obj: SubtreeAbleObj | LoggedQuantity


class ObjSubtree:
    """
    Generates and holds a sutree item.
    """

    def __init__(
        self,
        tree: QtWidgets.QTreeWidget,
        obj: SubtreeAbleObj,
    ) -> None:
        self.name = obj.name
        self.settings = obj.settings
        self.operations = obj.operations
        self.settings.q_object.new_lq_added.connect(self.add_lq_child_item)
        self.settings.q_object.lq_removed.connect(self.remove_lq_child_item)

        self.settings_items = {}
        self.operation_items = {}

        self.top_item = SFQTreeWidgetItem(tree, [obj.name, ""])
        obj.add_sub_tree(tree, self)

        tree.insertTopLevelItem(0, self.top_item)
        update_settings(self.settings, self.top_item, self.settings_items)
        update_operations(self.operations, self.top_item, self.operation_items)
        self.top_item.obj = obj

    def add_lq_child_item(self, lq: LoggedQuantity):
        update_settings(self.settings, self.top_item, self.settings_items)

    def remove_lq_child_item(self, lq: LoggedQuantity):
        remove_from_tree(lq.name, self.top_item, self.settings_items)

    def set_header(self, col=1, text="", color=None):
        self.top_item.setText(col, text)
        if color is not None:
            self.top_item.setForeground(col, QtGui.QColor(color))


def remove_from_tree(
    name: str,
    root_item: SFQTreeWidgetItem,
    children: dict[str, SFQTreeWidgetItem],
) -> None:
    item = children.pop(name, None)
    if item is None:
        return
    root_item.removeChild(item)


def update_operations(
    operations: dict[str, None],
    root_item: QtWidgets.QTreeWidgetItem,
    children: dict[str, QtWidgets.QTreeWidgetItem],
) -> None:
    for op_name, op_func in operations.items():
        op_button = QtWidgets.QPushButton(op_name)
        op_button.clicked.connect(lambda checked, f=op_func: f())
        new_item = QtWidgets.QTreeWidgetItem(root_item, [op_name, ""])
        children[op_name] = new_item
        root_item.addChild(new_item)
        root_item.treeWidget().setItemWidget(new_item, 1, op_button)


def update_settings(
    settings: LQCollection,
    root_item: SFQTreeWidgetItem,
    children: dict[str, SFQTreeWidgetItem],
) -> None:
    for lqname, lq in tuple(settings.iter(exclude=children.keys())):
        if isinstance(lq, ArrayLQ):
            lineedit = QtWidgets.QLineEdit()
            button = QtWidgets.QPushButton("...")
            widget = QtWidgets.QWidget()
            layout = QtWidgets.QHBoxLayout()
            widget.setLayout(layout)
            layout.addWidget(lineedit)
            layout.addWidget(button)
            layout.setSpacing(0)
            layout.setContentsMargins(0, 0, 0, 0)
            lq.connect_to_widget(lineedit)
            button.clicked.connect(lq.array_tableView.show)
            button.clicked.connect(lq.array_tableView.raise_)
        elif isinstance(lq, FileLQ):
            widget = lq.new_default_widget()
            widget.layout().setSpacing(0)
            widget.layout().setContentsMargins(0, 0, 0, 0)
        elif isinstance(lq, LoggedQuantity):
            widget = lq.new_default_widget()
        else:
            continue

        new_item = SFQTreeWidgetItem(root_item, [lqname, ""])
        new_item.obj = lq

        children[lqname] = new_item
        root_item.addChild(new_item)
        root_item.treeWidget().setItemWidget(new_item, 1, widget)


def on_right_click(position, tree: QtWidgets.QTreeWidget) -> None:
    selected_items = tree.selectedItems()
    if len(selected_items) < 1:
        return
    selected_item: SFQTreeWidgetItem = selected_items[0]
    selected_item.obj.on_right_click()
