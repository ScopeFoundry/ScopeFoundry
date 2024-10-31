from qtpy import QtWidgets


from functools import partial


class Tools:
    """a grouping that provides tools for *WidgetManagers"""

    # to support more layout types bind add/remove functions here:
    def __init__(self, layout, include, exclude) -> None:
        if isinstance(layout, QtWidgets.QFormLayout):
            self.add_to_layout = partial(_add_to_form_lay, layout=layout)
            self.remove_from_layout = partial(_rm_from_form_lay, layout=layout)
        elif isinstance(layout, QtWidgets.QBoxLayout):
            self.add_to_layout = partial(_add_to_box_lay, layout=layout)
            self.remove_from_layout = partial(_rm_from_box_lay, layout=layout)
        elif isinstance(layout, QtWidgets.QGridLayout):
            self.add_to_layout = partial(_add_to_grid_lay, layout=layout)
            self.remove_from_layout = partial(_rm_from_grid_lay, layout=layout)
        else:
            raise TypeError(f"{type(layout)} not support for dynamical widgets")

        self.include = include
        self.exclude = exclude


def _add_to_form_lay(
    name: str,
    widget: QtWidgets.QWidget,
    layout: QtWidgets.QFormLayout,
) -> None:
    if name is None:
        layout.addRow(widget)
    else:
        layout.addRow(name, widget)


def _rm_from_form_lay(
    name: str,
    widget: QtWidgets.QWidget,
    layout: QtWidgets.QFormLayout,
) -> None:
    row = layout.labelForField(widget)
    row.deleteLater()
    widget.deleteLater()


def _add_to_box_lay(
    name: str, widget: QtWidgets.QWidget, layout: QtWidgets.QBoxLayout
) -> None:
    layout.addWidget(widget)


def _rm_from_box_lay(
    name: str, widget: QtWidgets.QWidget, layout: QtWidgets.QBoxLayout
) -> None:
    layout.takeAt(layout.indexOf(widget))
    widget.deleteLater()


def _add_to_grid_lay(
    name: str, widget: QtWidgets.QWidget, layout: QtWidgets.QGridLayout
) -> None:
    row = layout.rowCount()

    if name is not None:
        label = QtWidgets.QLabel(name)
        layout.addWidget(label, row, 0)
        layout.addWidget(widget, row, 1)
        widget.setMinimumWidth(100)
    else:
        layout.addWidget(widget, row, 0, 1, 2)


def _rm_from_grid_lay(
    name: str, widget: QtWidgets.QWidget, layout: QtWidgets.QGridLayout
) -> None:

    for row in range(layout.rowCount()):
        item = layout.itemAtPosition(row, 0)
        if item is None:
            continue
        label = item.widget()
        if isinstance(label, QtWidgets.QLabel) and label.text() == name:
            layout.removeWidget(label)
            label.deleteLater()
            break

    layout.removeWidget(widget)
    widget.deleteLater()
