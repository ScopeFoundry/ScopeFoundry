from collections import deque
import json

import numpy as np
from qtpy import QtCore, QtWidgets

from ScopeFoundry.helper_funcs import QLock, get_logger_from_class
from ScopeFoundry.ndarray_interactive import ArrayLQ_QTableModel

from . import LoggedQuantity


class ArrayLQ(LoggedQuantity):
    updated_shape = QtCore.Signal(str)

    def __init__(
        self,
        name,
        dtype=float,
        initial=[],
        fmt="%g",
        si=True,
        ro=False,
        unit=None,
        vmin=-1e12,
        vmax=+1e12,
        choices=None,
        description=None,
        protected=False,
    ):
        QtCore.QObject.__init__(self)

        self.name = name
        self.dtype = dtype
        if self.dtype == str:
            self.val = np.array(initial, dtype=object)
        else:
            self.val = np.array(initial, dtype=dtype)
        self.hardware_read_func = None
        self.hardware_set_func = None
        self.fmt = fmt  # % string formatting string. This is ignored if dtype==str
        if self.dtype == str:
            self.fmt = "%s"
        self.unit = unit
        self.vmin = vmin
        self.vmax = vmax
        self.ro = ro  # Read-Only
        self.choices = choices
        self.description = description
        self.protected = protected

        self.log = get_logger_from_class(self)

        if self.dtype == int:
            self.spinbox_decimals = 0
        else:
            self.spinbox_decimals = 2
        self.reread_from_hardware_after_write = False

        self.oldval = None

        self._in_reread_loop = False  # flag to prevent reread from hardware loops

        self.widget_list = []
        self.listeners = []

        # threading lock
        self.lock = QLock(mode=0)  # mode 0 is non-reentrant lock

        self.is_array = True

        self._tableView = None

        self.prev_vals = deque([], 3)
        self.proposed_values = deque([], 7)

    def same_values(self, v1, v2):
        if v1.shape == v2.shape:
            return np.all(v1 == v2)
            self.log.debug("same_values %s %s" % (v2 - v1, np.all(v1 == v2)))
        else:
            return False

    def change_shape(self, newshape):
        # TODO
        pass

    def string_value(self):
        return json.dumps(self.val.tolist())

    def ini_string_value(self):
        return json.dumps(self.val.tolist())

    def coerce_to_type(self, x):
        if isinstance(x, str):
            x = json.loads(x)
        return np.array(x, dtype=self.dtype)

    def send_display_updates(self, force=False):
        with self.lock:
            self.log.debug(self.name + " send_display_updates")
            # print "send_display_updates: {} force={}".format(self.name, force)
            if force or np.any(self.oldval != self.val):

                # print "send display updates", self.name, self.val, self.oldval
                str_val = self.string_value()
                self.updated_value[str].emit(str_val)
                self.updated_text_value.emit(str_val)

                # self.updated_value[float].emit(self.val)
                # if self.dtype != float:
                #    self.updated_value[int].emit(self.val)
                # self.updated_value[bool].emit(self.val)
                self.updated_value[()].emit()

                self.oldval = self.val
            else:
                self.log.debug(
                    self.name
                    + " send_display_updates skipped (olval!=self.val)={} force={} oldval={} val={}".format(
                        (self.oldval != self.val), (force), self.oldval, self.val
                    )
                )
                # print "\t no updates sent", (self.oldval != self.val) , (force), self.oldval, self.val

    @property
    def array_tableView(self):
        if self._tableView == None:
            self._tableView = self.create_tableView()
            self._tableView.setWindowTitle(self.name)
        return self._tableView

    def create_tableView(self, **kwargs):
        widget = QtWidgets.QTableView()
        # widget.horizontalHeader().hide()
        # widget.verticalHeader().hide()
        model = ArrayLQ_QTableModel(
            self, transpose=(len(self.val.shape) == 1), **kwargs
        )
        widget.setModel(model)
        return widget

    def connect_element_follower_lq(self, lq, index, bidir=True):
        """
        connects an LQ to follow the changes of the array and display a specific element
        """
        # when self (array_lq) is update, update follower lq
        lq.connect_lq_math((self,), func=lambda arr, index=index: arr[index])

        if bidir:
            # when LQ is updated, update element in self
            def on_element_follower_lq():
                old_val = self.value[index]
                new_val = lq.value
                if new_val == old_val:
                    return
                new_arr = self.value.copy()
                new_arr[index] = new_val
                self.update_value(new_arr)

            lq.add_listener(on_element_follower_lq)

    def new_default_widget(self):
        widget = self.create_tableView()
        widget.horizontalHeader().hide()
        widget.verticalHeader().hide()
        return widget
