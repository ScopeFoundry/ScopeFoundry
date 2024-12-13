from typing import List, Protocol, Union

from qtpy import QtCore, QtWidgets

from ScopeFoundry.dynamical_widgets.tools import Tools
from ScopeFoundry.logged_quantity.collection import (
    LQCollection,
    LQCollectionWidgetsManager,
)
from ScopeFoundry.operations import Operations, OperationWidgetsManager


class Widgetable(Protocol):

    name: str
    settings: LQCollection
    operations: Operations
    _widgets_managers_: List


def new_widget(
    obj: Union[Widgetable, Operations, LQCollection],
    title: str = None,
    include=None,
    exclude=None,
    style="scroll_form",
) -> Union[QtWidgets.QScrollArea, QtWidgets.QWidget]:
    """returns a widget that represents objects with their settings and operations"""
    assert style in ("form", "hbox", "scroll_form")

    if title:
        widget = QtWidgets.QGroupBox()
        widget.setTitle(title)
    else:
        widget = QtWidgets.QWidget()

    if style in ("form", "scroll_form"):
        layout = QtWidgets.QFormLayout()

    elif style == "hbox":
        layout = QtWidgets.QHBoxLayout()

    if hasattr(obj, "settings") and hasattr(obj, "operations"):
        vlayout = QtWidgets.QVBoxLayout(widget)
        vlayout.addLayout(layout)
        add_to_layout(obj.settings, layout, include, exclude)
        add_to_layout(obj.operations, vlayout, include, exclude)
    else:
        widget.setLayout(layout)
        add_to_layout(obj, layout, include, exclude)

    if style == "scroll_form":
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(widget)
        return scroll_area

    return widget


def add_to_layout(
    obj: Union[Widgetable, Operations, LQCollection],
    layout: Union[QtWidgets.QFormLayout, QtWidgets.QHBoxLayout, QtWidgets.QVBoxLayout],
    include=None,
    exclude=None,
) -> None:
    """dynamically adds widgets to a given layout."""

    tools = Tools(layout, include, exclude)

    if isinstance(obj, LQCollection):
        obj._widgets_managers_.append(LQCollectionWidgetsManager(obj, tools))
    elif isinstance(obj, Operations):
        obj._widgets_managers_.append(OperationWidgetsManager(obj, tools))
    else:
        obj._widgets_managers_.append(LQCollectionWidgetsManager(obj.settings, tools))
        obj._widgets_managers_.append(OperationWidgetsManager(obj.operations, tools))
