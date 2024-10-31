from functools import partial
from typing import Protocol, List, Union

from qtpy import QtCore, QtGui, QtWidgets

from ScopeFoundry.helper_funcs import filter_with_patterns
from ScopeFoundry.logged_quantity import ArrayLQ, FileLQ, LoggedQuantity, LQCollection
from ScopeFoundry.operations import Operations


class SubtreeAbleObj(Protocol):

    name: str
    settings: LQCollection
    operations: Operations
    _subtree_managers_: List

    def on_new_subtree(self, subtree): ...  # optional

    def on_right_click(self): ...  # optional


def new_tree_widget(
    objs: List[SubtreeAbleObj], header=["col0", ""], include=None, exclude=None
) -> QtWidgets.QTreeWidget:
    """returns a tree widget that represents objects with their settings and operations"""
    tree_widget = QtWidgets.QTreeWidget()
    tree_widget.setColumnCount(len(header))
    tree_widget.setHeaderLabels(header)
    tree_widget.setColumnWidth(0, 180)
    tree_widget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
    tree_widget.customContextMenuRequested.connect(
        partial(on_right_click, tree=tree_widget)
    )

    for obj in objs:
        SubtreeManager(tree_widget, obj, include, exclude)

    return tree_widget


class SFQTreeWidgetItem(QtWidgets.QTreeWidgetItem):

    obj: Union[SubtreeAbleObj, LoggedQuantity, Operations]


class SubtreeManager:
    """
    adds tree items to the *tree_widget* forming.

     *tree_widget*
        *header_item* (obj dependent)
            - child_0 (LoggedQuantity or OperationBtn)
            - child_1 (LoggedQuantity or OperationBtn)
           ...
        ...

    the
    """

    def __init__(
        self,
        tree_widget: QtWidgets.QTreeWidget,
        obj: SubtreeAbleObj,
        include=None,
        exclude=None,
    ) -> None:
        self.name = obj.name
        self.settings = obj.settings
        self.operations = obj.operations
        self.include = include
        self.exclude = exclude
        self.settings.q_object.lq_added.connect(self.add_lq_child_item)
        self.settings.q_object.lq_removed.connect(self.remove_lq_child_item)
        self.operations.q_object.added.connect(self.add_operation_child_item)
        self.operations.q_object.removed.connect(self.remove_operation_child_item)

        self.settings_items = {}
        self.operation_items = {}

        self.header_item = SFQTreeWidgetItem(tree_widget, [obj.name, ""])
        self.tree_widget = tree_widget  # the widget where instance lives

        if hasattr(obj, "on_new_subtree"):
            obj.on_new_subtree(self)
        obj._subtree_managers_.append(self)

        tree_widget.insertTopLevelItem(0, self.header_item)
        update_settings(
            self.settings,
            self.header_item,
            self.settings_items,
            self.include,
            self.exclude,
        )
        update_operations(
            self.operations,
            self.header_item,
            self.operation_items,
            self.include,
            self.exclude,
        )
        self.header_item.obj = obj

    def add_lq_child_item(self, lq: LoggedQuantity):
        update_settings(
            self.settings,
            self.header_item,
            self.settings_items,
            self.include,
            self.exclude,
        )

    def remove_lq_child_item(self, lq: LoggedQuantity):
        remove_from_tree(lq.name, self.header_item, self.settings_items)

    def add_operation_child_item(self, name: str):
        update_operations(
            self.operations,
            self.header_item,
            self.operation_items,
            self.include,
            self.exclude,
        )

    def remove_operation_child_item(self, name: str):
        remove_from_tree(name, self.header_item, self.operation_items)

    def set_header_text(self, col=1, text="", color=None):
        self.header_item.setText(col, text)
        if color is not None:
            self.header_item.setForeground(col, QtGui.QColor(color))


def remove_from_tree(
    name: str,
    root_item: SFQTreeWidgetItem,
    children,  # dict[str, SFQTreeWidgetItem],
) -> None:
    item = children.pop(name, None)
    if item is None:
        return
    root_item.removeChild(item)


def update_operations(
    operations: Operations,
    root_item: QtWidgets.QTreeWidgetItem,
    children,  #: dict[str, QtWidgets.QTreeWidgetItem],
    include,
    exclude,
) -> None:
    for op_name in filter_with_patterns(operations.keys(), include, exclude):
        if op_name in children.keys():
            continue
        op_func = operations[op_name]
        op_button = QtWidgets.QPushButton(op_name)
        op_button.clicked.connect(lambda checked, f=op_func: f())
        new_item = QtWidgets.QTreeWidgetItem(root_item, [op_name, ""])
        children[op_name] = new_item
        root_item.addChild(new_item)
        root_item.treeWidget().setItemWidget(new_item, 1, op_button)


def update_settings(
    settings: LQCollection,
    root_item: SFQTreeWidgetItem,
    children,  #: dict[str, SFQTreeWidgetItem],
    include=None,
    exclude=None,
) -> None:
    for lqname, lq in tuple(settings.iter(include, exclude)):
        if lqname in children.keys():
            continue
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
    if hasattr(selected_item.obj, "on_right_click"):
        selected_item.obj.on_right_click()
