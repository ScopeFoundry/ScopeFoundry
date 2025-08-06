from typing import List

from qtpy import QtWidgets
import numpy as np

from .lq_range import LQRange
from .logged_quantity import LoggedQuantity


class ActivatableRange:
    """
    A class to represent a range of values that can be active or inactive.
    It extends the LQRange class to include an active state.
    """

    def __init__(
        self,
        lq_range: LQRange = None,
        is_active_lq: LoggedQuantity = None,
    ):
        self.lq_range = lq_range
        self.is_active = is_active_lq

    def New_UI(self) -> QtWidgets.QWidget:
        widget = self.lq_range.New_UI()
        layout: QtWidgets.QFormLayout = widget.layout()
        layout.addRow(self.is_active.name, self.is_active.new_default_widget())
        return widget


class IntervaledLQRange:
    """
    A class to represent a range of three values, with a start, stop, and step.
    """

    def __init__(
        self,
        lq_ranges: List[LQRange],
        is_active_lqs: List[LoggedQuantity],
        no_duplicates: LoggedQuantity,
        sweep_type: LoggedQuantity = None,
    ):
        self.n = len(lq_ranges)
        self.ranges = [ActivatableRange(r, a) for r, a in zip(lq_ranges, is_active_lqs)]
        self.sweep_type = sweep_type
        self.no_duplicates = no_duplicates

    @property
    def array(self):
        """
        Returns a list of the current values of the ranges.
        """
        arr = np.array(
            [r.lq_range.array[:] for r in self.ranges if r.is_active.val]
        ).flatten()
        if self.no_duplicates.val:
            return filter_adjancent_duplicates(arr)
        return arr

    @property
    def sweep_array(self):
        if self.sweep_type.val == "up":
            return self.array
        elif self.sweep_type.val == "down":
            return self.array[::-1]
        elif self.sweep_type.val == "up_down":
            return np.append((self.array, self.array[::-1]))
        elif self.sweep_type.val == "down_up":
            return np.append((self.array[::-1], self.array))
        elif self.sweep_type.val == "zig_zag":
            mid = len(self.array) // 2
            return np.append(
                [
                    self.array[mid::],
                    self.array[::-1],
                    self.array[0:mid:],
                ]
            )
        elif self.sweep_type.val == "zag_zip":
            mid = len(self.array) // 2
            return np.append(
                [
                    self.array[mid:0:-1],
                    self.array[0::],
                    self.array[:mid:-1],
                ]
            )

    def New_UI(self):

        header_layout = QtWidgets.QHBoxLayout()
        if self.sweep_type is not None:
            header_layout.addWidget(QtWidgets.QLabel("Sweep type:"))
            header_layout.addWidget(self.sweep_type.new_default_widget())
        header_layout.addWidget(QtWidgets.QLabel("remove adjacent duplicates:"))
        header_layout.addWidget(self.no_duplicates.new_default_widget())

        grid_layout = QtWidgets.QGridLayout()
        # grid_layout.addWidget(QtWidgets.QLabel("active"), 0, 0)
        grid_layout.addWidget(QtWidgets.QLabel("min"), 0, 1)
        grid_layout.addWidget(QtWidgets.QLabel("max"), 0, 2)
        grid_layout.addWidget(QtWidgets.QLabel("step"), 0, 3)
        grid_layout.addWidget(QtWidgets.QLabel("num"), 0, 4)
        # if self.ranges[0].lq_range.span:
        #    grid_layout.addWidget(QtWidgets.QLabel("span"), 0, 5)
        grid_layout.setColumnMinimumWidth(0, 20)
        grid_layout.setColumnMinimumWidth(1, 100)
        grid_layout.setColumnMinimumWidth(2, 100)
        grid_layout.setColumnMinimumWidth(3, 100)
        grid_layout.setColumnMinimumWidth(4, 50)
        grid_layout.setColumnMinimumWidth(5, 100)

        for ii, r in enumerate(self.ranges):
            w0: QtWidgets.QCheckBox = r.is_active.new_default_widget()
            w1 = r.lq_range.min.new_default_widget()
            w2 = r.lq_range.max.new_default_widget()
            w3 = r.lq_range.step.new_default_widget()
            w4 = r.lq_range.num.new_default_widget()
            grid_layout.addWidget(w0, ii + 1, 0)
            grid_layout.addWidget(w1, ii + 1, 1)
            grid_layout.addWidget(w2, ii + 1, 2)
            grid_layout.addWidget(w3, ii + 1, 3)
            grid_layout.addWidget(w4, ii + 1, 4)
            w1.setEnabled(r.is_active.val)
            w2.setEnabled(r.is_active.val)
            w3.setEnabled(r.is_active.val)
            w4.setEnabled(r.is_active.val)
            w0.stateChanged.connect(w1.setEnabled)
            w0.stateChanged.connect(w2.setEnabled)
            w0.stateChanged.connect(w3.setEnabled)
            w0.stateChanged.connect(w4.setEnabled)

            # if r.lq_range.span:
            #    w5 = r.lq_range.span.new_default_widget()
            #    grid_layout.addWidget(w5, ii + 1, 5)
            #   w0.stateChanged.connect(w5.setEnabled)

        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.addLayout(header_layout)
        layout.addLayout(grid_layout)
        return widget

    def add_listener(self, func, argtype=(), **kwargs):
        """
        Adds a listener to all active ranges.
        """
        for r in self.ranges:
            r.lq_range.add_listener(func, argtype, **kwargs)
            r.is_active.add_listener(func, argtype, **kwargs)


def filter_adjancent_duplicates(ar: np.ndarray, tol: float = 0) -> np.ndarray:
    """
    Filters adjacent duplicates in a numpy array based on a tolerance.
    Returns the filtered array.
    """
    if len(ar) == 0:
        return ar
    mask = np.abs(np.diff(ar)) > tol
    mask = np.insert(mask, 0, True)  # Keep the first element
    return ar[mask]
