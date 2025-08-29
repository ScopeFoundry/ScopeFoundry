import subprocess
from collections import deque
from enum import Enum
from functools import partial
from inspect import signature
from typing import Any, Iterable, List, Tuple, Union

import pyqtgraph as pg
from qtpy import QtCore, QtGui, QtWidgets

from ScopeFoundry.helper_funcs import QLock, bool2str, get_logger_from_class, str2bool
from ScopeFoundry.widgets import MinMaxQSlider


class LoggedQuantity(QtCore.QObject):
    """
    **LoggedQuantity** objects are containers that wrap settings. These settings
    may be a number (integer or float) or a string and occasionally small arrays
    of them.

    These objects emit signals when changed and can be connected bidirectionally
    to Qt Widgets.

    In ScopeFoundry we represent the values in an object called a
    `LoggedQuantity`. A :class:`LoggedQuantity` is a class that contains a
    value, a `bool`, `float`, `int`, `str` etc that is part of an application's
    state. In the case of microscope and equipment control, these also can
    represent the state of a piece of hardware. These are very useful objects
    because the are the central location of the value contained within. All
    graphical interface views will be guaranteed to be consistent with the `LQ`
    state. The data of these quantities will also be saved in datafiles created
    by ScopeFoundry.

    """

    # signal sent when value has been updated
    updated_value = QtCore.Signal((float,), (int,), (bool,), (), (str,))
    # signal sent when value has been updated, sends text representation
    updated_text_value = QtCore.Signal(str)
    # emits the index of the value in self.choices
    updated_choice_index_value = QtCore.Signal(int)

    # signal sent when min max range updated
    updated_min_max = QtCore.Signal((float, float), (int, int), ())
    # signal sent when read only (ro) status has changed
    updated_readonly = QtCore.Signal((bool,), ())

    def __init__(
        self,
        name,
        dtype=float,
        initial=0,
        fmt: str = "%g",
        si: bool = False,
        ro: bool = False,  # read only flag
        unit: str = None,
        spinbox_decimals: int = 2,
        spinbox_step: float = 0.1,
        vmin: float = -1e12,
        vmax: float = +1e12,
        choices: Iterable = None,
        reread_from_hardware_after_write: bool = False,
        description: str = None,
        colors=None,
        protected: bool = False,  # a guard that prevents from being updated, i.e. file loading
        is_cmd: bool = False,
        is_clipboardable: bool = False,
        default_widget_factory=None,
    ):
        QtCore.QObject.__init__(self)

        self.name = name

        if dtype in [int, str, float]:
            pass
        elif dtype in ["int", "uint"]:
            dtype = int
        elif dtype in ["float", "float32"]:
            dtype = float

        self.dtype = dtype

        # choices should be tuple [ ('name', val) ... ] or simple list [val, val, ...]
        self.choices = self._expand_choices(choices)
        if self.choices and not initial in (x[1] for x in self.choices):
            initial = self.choices[0][1]

        self.val = dtype(initial)
        self.hardware_read_func = None
        self.hardware_set_func = None
        self.fmt = fmt  # string formatting string. This is ignored if dtype==str
        if self.dtype == str:
            self.fmt = "%s"
        self.si = si  # will use pyqtgraph SI Spinbox if True
        self.unit = unit
        self.vmin = vmin
        self.vmax = vmax

        # self.change_choice_list(choices)
        self.ro = ro  # Read-Only
        self.is_array = False
        self.description = description

        self.colors = colors
        if colors:
            self.qcolors = [to_q_color(color) for color in colors]
        else:
            self.qcolors = []

        self.log = get_logger_from_class(self)

        if self.dtype == int:
            self.spinbox_decimals = 0
        else:
            self.spinbox_decimals = spinbox_decimals
        self.reread_from_hardware_after_write = reread_from_hardware_after_write

        if self.dtype == int:
            self.spinbox_step = 1
        else:
            self.spinbox_step = spinbox_step

        self.default_widget_factory = default_widget_factory

        self.oldval = None

        self._in_reread_loop = False  # flag to prevent reread from hardware loops

        self.widget_list = []
        self.listeners = []

        # threading lock
        self.lock = QLock(mode=1)  # mode 0 is non-reentrant lock

        self.path = ""

        self.protected = protected

        self.is_clipboardable = is_clipboardable
        self.is_cmd = is_cmd

        self.prev_vals = deque([], 3)
        self.proposed_values = deque([], 7)
        self.actions = []
        self.event_filter: QtCore.QObject = None

    def coerce_to_type(self, x):
        """
        Force x to dtype of the LQ

        =============  ==================================
        **Arguments**  **Description**
        *x*            value of type str, bool, int, etc.
        =============  ==================================

        :returns: Same value, *x* of the same type as its respective logged
        quantity

        """
        if self.dtype == bool and isinstance(x, str):
            return str2bool(x)
        return self.dtype(x)

    def coerce_to_str(self, x):
        if self.dtype == bool:
            return bool2str(x)
        else:
            return str(x)

    @property
    def val_str(self):
        self.coerce_to_str(self.val)

    def _expand_choices(self, choices: Iterable) -> Union[Tuple[str, Any], None]:
        """returns [(name, val)...] or None"""
        if choices is None:
            return None
        return [_expand_choice(c, self.dtype) for c in choices]

    def __str__(self):
        return f"{self.name} = {self.val}"

    def __repr__(self):
        return f"LQ: {self.name} = {self.val}"

    def read_from_hardware(self, send_signal: bool = True):
        self.log.debug(f"{self.name}: read_from_hardware send_signal={send_signal}")
        if self.hardware_read_func is not None:
            with self.lock:
                self.oldval = self.val
                val = self.hardware_read_func()
            self.update_value(
                new_val=val, update_hardware=False, send_signal=send_signal
            )
        else:
            self.log.warning(
                f"{self.name} read_from_hardware called when not connected to hardware"
            )
        return self.val

    def write_to_hardware(self, reread_hardware=None):
        if reread_hardware is None:
            # if undefined, default to stored reread_from_hardware_after_write bool
            reread_hardware = self.reread_from_hardware_after_write
        # Read from Hardware
        if self.has_hardware_write():
            with self.lock:
                self.hardware_set_func(self.val)
            if reread_hardware:
                self.read_from_hardware(send_signal=False)

    @property
    def value(self):
        "return stored value"
        return self.val

    @QtCore.Slot(str)
    @QtCore.Slot(float)
    @QtCore.Slot(int)
    @QtCore.Slot(bool)
    @QtCore.Slot()
    def update_value(
        self, new_val=None, update_hardware=True, send_signal=True, reread_hardware=None
    ):
        """
        Update stored value with new_val

        Change value of LQ and emit signals to inform listeners of change

        if *update_hardware* is true: call connected hardware write function

        =============== =================================================================================================================
        **Arguments:**  **Description:**
        new_val         New value for the LoggedQuantity to store
        update_hardware calls hardware_set_func if defined (default True)
        send_signal     sends out QT signals on upon change (default True)
        reread_hardware read from hardware after writing to hardware to ensure change (defaults to self.reread_from_hardware_after_write)
        =============== =================================================================================================================

        :returns: None

        """
        # use a thread lock during update_value to avoid another thread
        # calling update_value during the update_value

        if reread_hardware is None:
            # if undefined, default to stored reread_from_hardware_after_write bool
            reread_hardware = self.reread_from_hardware_after_write

        with self.lock:

            # sometimes a the sender is a textbox that does not send its new value,
            # grab the text() from it instead
            if new_val is None:
                if hasattr(self.sender(), "text"):
                    new_val = self.sender().text()

            self.oldval = self.coerce_to_type(self.val)
            new_val = self.coerce_to_type(new_val)

            self.log.debug(
                f"{self.path}: update_value {repr(self.oldval)} --> {repr(new_val)}  from sender:{repr(self.sender())}"
            )

            # check for equality of new vs old, do not proceed if they are same
            if self.same_values(self.oldval, new_val):
                self.log.debug(f"{self.path}: same_value so returning")
                return
            # else:
            #     self.log.debug(f"{self.path}: different values {self.oldval} {new_val}")

            # actually change internal state value and store prev. values
            self.prev_vals.appendleft(self.val)
            self.val = new_val

        # Read from Hardware
        if update_hardware and self.hardware_set_func:
            self.hardware_set_func(self.val)
            if reread_hardware:
                self.read_from_hardware(send_signal=False)
        # Send Qt Signals
        if send_signal:
            self.send_display_updates()

    def send_display_updates(self, force=False):
        """
        Emit updated_value signals if value has changed.

        =============  =============================================
        **Arguments**  **Description**
        *force*        will emit signals regardless of value change.
        =============  =============================================

        :returns: None

        """
        # self.log.debug("{self.name}:send_display_updates: {force=}. From {self.oldval} to {self.val}")
        if (not self.same_values(self.oldval, self.val)) or (force):
            self.updated_value[()].emit()

            str_val = self.string_value()
            self.updated_value[str].emit(str_val)
            self.updated_text_value.emit(str_val)

            if self.dtype in [float, int]:
                self.updated_value[float].emit(self.val)
                self.updated_value[int].emit(int(self.val))
            self.updated_value[bool].emit(bool(self.val))

            if self.choices is not None:
                choice_vals = [c[1] for c in self.choices]
                if self.val in choice_vals:
                    self.updated_choice_index_value.emit(choice_vals.index(self.val))
            self.oldval = self.val
        else:
            # no updates sent
            pass

    def same_values(self, v1, v2):
        """
        Compares two values of the LQ type, used in update_value

        =============  ====================
        **Arguments**  **Description**
        v1             value 1
        v2             value 2
        =============  ====================

        :returns: Boolean value (True or False)

        """
        return v1 == v2

    def string_value(self):
        if self.dtype == str:
            return self.val
        else:
            return self.fmt % self.val

    def ini_string_value(self):
        """
        :returns: A string showing the logged quantity value.
        """
        return str(self.val)

    def update_choice_index_value(self, new_choice_index, **kwargs):
        self.update_value(self.choices[new_choice_index][1], **kwargs)

    def add_listener(self, func, argtype=(), **kwargs):
        """
        Connect 'func' as a listener (Qt Slot) for the
        updated_value signal.
        By default 'func' should take no arguments,
        but argtype can define the data type that it should accept.
        but should be limited to those supported by LoggedQuantity
        (i.e. int, float, str)
        **kwargs are passed to the connect function
        appends the 'func' to the 'listeners' list
        """

        #    --> This is now handled by redefining sys.excepthook handle in ScopeFoundry.base_app
        # Wraps func in a try block to absorb the Exception to avoid crashing PyQt5 >5.5
        # see https://riverbankcomputing.com/pipermail/pyqt/2016-March/037134.html
        #         def wrapped_func(func):
        #             def f(*args):
        #                 try:
        #                     func(*args)
        #                 except Exception as err:
        #                     print "Exception on listener:"

        self.updated_value[argtype].connect(func, **kwargs)
        self.listeners.append(func)

    def change_readonly_on(self, other_lq, func=bool):
        """
        When the other_lq updates, this LQ will be change its readonly status to func(other_lq.val).
        """
        other_lq.add_listener(lambda: self.change_readonly(func(other_lq.val)))

    def connect_bidir_to_widget(self, widget):
        # DEPRECATED
        return self.connect_to_widget(widget)

    def set_widget_toolTip(self, widget: QtWidgets.QWidget, text=None):
        if not hasattr(widget, "setToolTip"):
            return []
        tips = [f"<b>{self.path}</b>"]
        if self.unit:
            tips.append(f"<i>({self.unit})</i>")
        for s in [self.description, widget.toolTip(), text]:
            if s is not None:
                tips.append(str(s))
        if self.protected:
            tips.append("\n<b>🔒 protected</b>")

        tips_str = "\n".join(tips)
        widget.setToolTip(f"<div style='white-space: pre-line;'>{tips_str}</div>")
        return tips

    def connect_to_widget(self, widget: QtWidgets.QWidget):
        """
        Creates Qt signal-slot connections between LQ and the QtWidget *widget*

        connects updated_value signal to the appropriate slot depending on
        the type of widget

        Makes a bidirectional connection to a QT widget, ie when LQ is updated,
        widget gets a signal and when widget is updated, the LQ receives a
        signal and update_value() slot is called.

        Handles many types of widgets:
         * QDoubleSpinBox
         * QCheckBox
         * QLineEdit
         * QComboBox
         * pyqtgraph.widgets.SpinBox.SpinBox

        =============  ====================================================================
        **Arguments**  **Description**
        widget         The name of the Qt GUI Object, examples of which are listed above.
                       For example, if you have a QDoubleSpinBox in the gui which you
                       renamed int_value_doubleSpinBox in the Qt Designer Object Inspector,
                       use self.ui.int_value_doubleSpinBox
        =============  ====================================================================

        :returns: None

        """

        self.set_widget_toolTip(widget)
        widget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        widget.customContextMenuRequested.connect(self.on_right_click)

        if isinstance(widget, QtWidgets.QDoubleSpinBox):

            widget.setKeyboardTracking(False)
            if self.vmin is not None:
                widget.setMinimum(self.vmin)
            if self.vmax is not None:
                widget.setMaximum(self.vmax)
            if self.unit is not None:
                widget.setSuffix(f" {self.unit}")
            widget.setDecimals(self.spinbox_decimals)
            widget.setSingleStep(self.spinbox_step)
            widget.setValue(self.val)

            @QtCore.Slot(float)
            def update_widget_value(x=None):
                """
                block signals from widget when value is set via lq.update_value.
                This prevents signal-slot loops between widget and lq
                """
                try:
                    widget.blockSignals(True)
                    widget.setValue(self.val)
                finally:
                    widget.blockSignals(False)

            # self.updated_value[float].connect(widget.setValue)
            widget.to_connection = self.updated_value[float].connect(
                update_widget_value
            )
            # if not self.ro:
            widget.valueChanged[float].connect(self.update_value)

        elif isinstance(widget, MinMaxQSlider):
            self.updated_value[float].connect(widget.update_value)
            widget.updated_value.connect(self.update_value)
            if self.unit is not None:
                widget.unit = self.unit
            widget.set_range(self.vmin, self.vmax)
            widget.set_name(self.name)

        elif isinstance(widget, QtWidgets.QSlider):
            SLIDER_MIN = -2147483648
            SLIDER_MAX = 2147483647
            vmin = min(max(self.vmin, SLIDER_MIN), SLIDER_MAX)
            vmax = max(min(self.vmax, SLIDER_MAX), SLIDER_MIN)
            int_overflow = vmin != self.vmin or vmax != self.vmax

            if int_overflow:
                self.log.info(
                    f"WARNING in using QSlider with {self.path}: Consider narrowing the range with vmin, vmax"
                )

            if self.dtype == int and not int_overflow:
                widget.setRange(int(vmin), int(vmax))
                self.updated_value[int].connect(widget.setValue)
                widget.valueChanged[int].connect(self.update_value)
                widget.setValue(self.value)

            elif self.dtype == float or (self.dtype == int and int_overflow):
                # the sliders values are scaled version of the actual value
                # making slider values symmetric around 0
                SLIDER_MIN = -2147483647
                self.vrange = self.vmax - self.vmin
                widget.setRange(SLIDER_MIN, SLIDER_MAX)
                slider_range = SLIDER_MAX - SLIDER_MIN

                def transform_to_slider(x):
                    lq_avg = 0.5 * (self.vmax + self.vmin)
                    self.vrange = self.vmax - self.vmin
                    return int(slider_range / self.vrange * (x - lq_avg))

                def transform_from_slider(x):
                    lq_avg = 0.5 * (self.vmax + self.vmin)
                    self.vrange = self.vmax - self.vmin
                    return self.vrange / slider_range * x + lq_avg

                # for float testing in tests/unittest/lq_connect_to_widget_test
                self._transform_to_slider = transform_to_slider
                self._transform_from_slider = transform_from_slider

                @QtCore.Slot(float)
                def update_widget_value(x):
                    """
                    block signals from widget when value is set via lq.update_value.
                    This prevents signal-slot loops between widget and lq
                    """
                    try:
                        widget.blockSignals(True)
                        widget.setValue(transform_to_slider(self.val))
                    finally:
                        widget.blockSignals(False)

                @QtCore.Slot(int)
                def update_lq(x):
                    self.update_value(transform_from_slider(x))

                widget.setSingleStep(1)
                self.updated_value[float].connect(update_widget_value)
                widget.valueChanged[int].connect(update_lq)
                widget.setValue(transform_to_slider(self.val))

            else:
                self.log.warning(
                    f"QSlider not supported with setting {self.path} of dtype={self.dtype}"
                )

        elif isinstance(widget, QtWidgets.QCheckBox):

            @QtCore.Slot(bool)
            def update_widget_value(x=None):
                try:
                    widget.blockSignals(True)
                    widget.setChecked(self.val)
                finally:
                    widget.blockSignals(False)

            self.updated_value[bool].connect(update_widget_value)

            if self.ro:
                widget.setEnabled(False)
            else:
                widget.clicked[bool].connect(self.update_value)
                # only works if widget was clicked or
                # widget value changed and widget.clicked.emit() was called
                # Maybe more rigourous would be
                # widget.stateChanged.connect(self.update_value)
                # but then for widgets in tristate can send states 0, 1, 2.
                # Do not know when state occurs

            if self.colors is not None:
                s = f"""QCheckBox:!checked {{ background: {self.colors[0]} }}
                        QCheckBox:checked  {{ background: {self.colors[-1]} }}"""
                widget.setStyleSheet(widget.styleSheet() + s)

        elif isinstance(widget, QtWidgets.QLineEdit):
            self.updated_text_value[str].connect(widget.setText)
            self.updated_value[str].connect(widget.setText)

            if self.ro:
                widget.setReadOnly(True)  # FIXME

            def on_edit_finished():
                self.log.debug(f"{self.path} qLineEdit on_edit_finished")
                try:
                    widget.blockSignals(True)
                    self.update_value(widget.text())
                finally:
                    widget.blockSignals(False)

            widget.editingFinished.connect(on_edit_finished)

        elif isinstance(widget, QtWidgets.QPlainTextEdit):
            # TODO Read only

            def on_lq_changed(new_text):
                current_cursor = widget.textCursor()
                current_cursor_pos = current_cursor.position()
                # print('current_cursor', current_cursor, current_cursor.position())
                widget.document().setPlainText(new_text)
                current_cursor.setPosition(current_cursor_pos)
                widget.setTextCursor(current_cursor)
                # print('current_cursor', current_cursor, current_cursor.position())

            def on_widget_textChanged():
                try:
                    widget.blockSignals(True)
                    self.update_value(widget.toPlainText())
                finally:
                    widget.blockSignals(False)

            # self.updated_text_value[str].connect(widget.document().setPlainText)
            self.updated_text_value[str].connect(on_lq_changed)
            widget.textChanged.connect(on_widget_textChanged)

        elif isinstance(widget, QtWidgets.QTextEdit):

            def on_updated(x=None):
                widget.setText(self.val)

            self.updated_value[str].connect(on_updated)

            def on_text_changed(x=None):
                try:
                    widget.blockSignals(True)
                    self.update_value(widget.toPlainText())
                finally:
                    widget.blockSignals(False)

            widget.textChanged.connect(on_text_changed)

        elif isinstance(widget, QtWidgets.QComboBox):
            assert self.choices is not None
            widget.clear()  # removes all old choices

            for choice_name, choice_value in self.choices:
                widget.addItem(choice_name, choice_value)
            self.updated_choice_index_value[int].connect(widget.setCurrentIndex)
            widget.currentIndexChanged.connect(self.update_choice_index_value)

            if self.colors is not None:
                for i, qcolor in enumerate(self.qcolors):
                    widget.setItemData(i, qcolor, QtCore.Qt.BackgroundRole)

                def update_background_color(idx):
                    if idx < len(self.qcolors):
                        qc = self.qcolors[idx]
                    else:
                        qc = QtGui.QColor("lightgrey")

                    s = f"""QComboBox{{
                                selection-background-color: {qc.name()};
                                selection-color: black;
                                background: {qc.name()};
                            }}"""
                    widget.setStyleSheet(widget.styleSheet() + s)

                widget.currentIndexChanged.connect(update_background_color)

        elif isinstance(widget, pg.widgets.SpinBox.SpinBox):
            # widget.setFocusPolicy(QtCore.Qt.StrongFocus)
            suffix = self.unit
            if self.unit is None:
                suffix = ""
            if self.dtype == int:
                integer = True
                minStep = 1
                step = 1
            else:
                integer = False
                minStep = 0.1
                step = 0.1
            opts = dict(
                suffix=suffix,
                siPrefix=True,
                dec=True,
                step=step,
                minStep=minStep,
                bounds=[self.vmin, self.vmax],
                int=integer,
            )
            if self.si:
                del opts["step"]
                del opts["minStep"]

            widget.setOpts(**opts)

            if self.ro:
                widget.setEnabled(False)
                widget.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
                widget.setReadOnly(True)
            # widget.setDecimals(self.spinbox_decimals)
            if not self.si:
                widget.setSingleStep(self.spinbox_step)

            # self.updated_value[float].connect(widget.setValue)
            # if not self.ro:
            # widget.valueChanged[float].connect(self.update_value)

            @QtCore.Slot(float)
            def update_widget_value(x):
                """
                block signals from widget when value is set via lq.update_value.
                This prevents signal loops
                """
                try:
                    widget.blockSignals(True)
                    widget.setValue(x)
                finally:
                    widget.blockSignals(False)

            self.updated_value[float].connect(update_widget_value)

            def on_widget_update(_widget):
                self.update_value(_widget.value())

            widget.sigValueChanged.connect(on_widget_update)

        elif isinstance(widget, QtWidgets.QLabel):
            self.updated_text_value.connect(widget.setText)
        elif isinstance(widget, QtWidgets.QProgressBar):

            def set_progressbar(x, widget=widget):
                self.log.debug(f"set_progressbar {x}")
                widget.setValue(int(x))

            self.updated_value.connect(set_progressbar)
        elif isinstance(widget, QtWidgets.QLCDNumber):
            self.updated_value[(self.dtype)].connect(widget.display)
        else:
            raise ValueError("Unknown widget type")

        self.send_display_updates(force=True)
        # self.widget = widget
        self.widget_list.append(widget)
        self.change_readonly(self.ro)
        if self.event_filter:
            widget.installEventFilter(self.event_filter)

    def disconnect_from_widget(self, widget: QtWidgets.QWidget):
        """
        Disconnects the Qt signal-slot connections between LQ and the QtWidget *widget*

        :returns: None

        """
        if widget not in self.widget_list:
            # print(f"Widget {widget} not connected to {self.name}")
            return

        self.widget_list.remove(widget)

        widget.disconnect()

        if hasattr(widget, "to_connection"):
            if isinstance(widget, QtWidgets.QDoubleSpinBox):
                self.updated_value[float].disconnect(widget.to_connection)
            # TODO: other widgets!

            # elif isinstance(widget, QtWidgets.QCheckBox):
            #     self.updated_value[bool].disconnect(widget.setChecked)
            # elif isinstance(widget, QtWidgets.QLineEdit):
            #     self.updated_value[str].disconnect(widget.setText)
            #     self.updated_text_value[str].disconnect(widget.setText)
            # elif isinstance(widget, QtWidgets.QPlainTextEdit):
            #     self.updated_text_value[str].disconnect(widget.document().setPlainText)
            #     self.updated_value[str].disconnect(widget.document().setPlainText)
            # elif isinstance(widget, QtWidgets.QSlider):
            #     self.updated_value[float].disconnect(widget.setValue)
            # elif isinstance(widget, MinMaxQSlider):
            #     self.updated_value[float].disconnect(widget.update_value)
            # elif isinstance(widget, QtWidgets.QLCDNumber):
            #     self.update_value[float].disconnect(widget.display)
            # elif isinstance(widget, QtWidgets.QProgressBar):
            #     self.updated_value.disconnect(widget.setValue)
            # elif isinstance(widget, QtWidgets.QComboBox):
            #     self.updated_choice_index_value[int].disconnect(widget.setCurrentIndex)
            #     widget.currentIndexChanged.disconnect(self.update_choice_index_value)

    def connect_to_widget_one_way(self, widget):
        """
        Creates Qt signal-slot connections between LQ and the QtWidget *widget* ONLY IN ONE WAY. CHANGES IN WIDGET WILL NOT TRANSFER TO LQ!!!
        rest is the same as connect_to_widget

        """

        self.set_widget_toolTip(widget)

        if isinstance(widget, QtWidgets.QDoubleSpinBox):

            widget.setKeyboardTracking(False)
            if self.vmin is not None:
                widget.setMinimum(self.vmin)
            if self.vmax is not None:
                widget.setMaximum(self.vmax)
            if self.unit is not None:
                widget.setSuffix(f" {self.unit}")
            widget.setDecimals(self.spinbox_decimals)
            widget.setSingleStep(self.spinbox_step)
            widget.setValue(self.val)

            # events
            @QtCore.Slot(float)
            def update_widget_value(x):
                """
                block signals from widget when value is set via lq.update_value.
                This prevents signal-slot loops between widget and lq
                """
                try:
                    widget.blockSignals(True)
                    widget.setValue(self.val)
                finally:
                    widget.blockSignals(False)

            # self.updated_value[float].connect(widget.setValue)
            self.updated_value[float].connect(update_widget_value)

        elif isinstance(widget, MinMaxQSlider):
            self.updated_value[float].connect(widget.update_value)
            if self.unit is not None:
                widget.unit = self.unit
            widget.set_range(self.vmin, self.vmax)
            widget.set_name(self.name)

        elif isinstance(widget, QtWidgets.QSlider):

            SLIDER_MIN = -2147483648
            SLIDER_MAX = 2147483647
            vmin = min(max(self.vmin, SLIDER_MIN), SLIDER_MAX)
            vmax = max(min(self.vmax, SLIDER_MAX), SLIDER_MIN)
            int_overflow = vmin != self.vmin or vmax != self.vmax

            if int_overflow:
                self.log.info(
                    f"WARNING in using QSlider with {self.path}: Consider narrowing the range with vmin, vmax"
                )

            if self.dtype == int and not int_overflow:
                widget.setRange(int(vmin), int(vmax))
                self.updated_value[int].connect(widget.setValue)
                widget.setValue(self.value)

            elif self.dtype == float or (self.dtype == int and int_overflow):
                # the sliders values are scaled version of the actual value
                # making slider values symmetric around 0
                SLIDER_MIN = -2147483647
                self.vrange = self.vmax - self.vmin
                widget.setRange(SLIDER_MIN, SLIDER_MAX)
                slider_range = SLIDER_MAX - SLIDER_MIN

                def transform_to_slider(x):
                    lq_avg = 0.5 * (self.vmax + self.vmin)
                    self.vrange = self.vmax - self.vmin
                    return int(slider_range / self.vrange * (x - lq_avg))

                def transform_from_slider(x):
                    lq_avg = 0.5 * (self.vmax + self.vmin)
                    self.vrange = self.vmax - self.vmin
                    return self.vrange / slider_range * x + lq_avg

                # for float testing in tests/unittest/lq_connect_to_widget_test
                self._transform_to_slider = transform_to_slider
                self._transform_from_slider = transform_from_slider

                @QtCore.Slot(float)
                def update_widget_value(x):
                    """
                    block signals from widget when value is set via lq.update_value.
                    This prevents signal-slot loops between widget and lq
                    """
                    try:
                        widget.blockSignals(True)
                        widget.setValue(transform_to_slider(self.val))
                    finally:
                        widget.blockSignals(False)

                widget.setSingleStep(1)
                self.updated_value[float].connect(update_widget_value)
                widget.setValue(transform_to_slider(self.val))

            else:
                self.log.warning(
                    f"QSlider not supported with setting {self.path} of dtype={self.dtype}"
                )

        elif isinstance(widget, QtWidgets.QCheckBox):

            @QtCore.Slot(bool)
            def update_widget_value(x=None):
                try:
                    widget.blockSignals(True)
                    widget.setChecked(self.val)
                finally:
                    widget.blockSignals(False)

            self.updated_value[bool].connect(update_widget_value)

            if self.ro:
                widget.setEnabled(False)

            if self.colors is not None:
                s = f"""QCheckBox:!checked {{ background: {self.colors[0]} }}
                        QCheckBox:checked  {{ background: {self.colors[-1]} }}"""
                widget.setStyleSheet(widget.styleSheet() + s)

        elif isinstance(widget, QtWidgets.QLineEdit):
            self.updated_text_value[str].connect(widget.setText)
            self.updated_value[str].connect(widget.setText)
            if self.ro:
                widget.setReadOnly(True)  # FIXME

        elif isinstance(widget, QtWidgets.QPlainTextEdit):
            # TODO Read only

            def on_lq_changed(new_text):
                current_cursor = widget.textCursor()
                current_cursor_pos = current_cursor.position()
                # print('current_cursor', current_cursor, current_cursor.position())
                widget.document().setPlainText(new_text)
                current_cursor.setPosition(current_cursor_pos)
                widget.setTextCursor(current_cursor)
                # print('current_cursor', current_cursor, current_cursor.position())

            # self.updated_text_value[str].connect(widget.document().setPlainText)
            self.updated_text_value[str].connect(on_lq_changed)

        elif isinstance(widget, QtWidgets.QComboBox):
            # need to have a choice list to connect to a QComboBox
            assert self.choices is not None
            widget.clear()  # removes all old choices
            for choice_name, choice_value in self.choices:
                widget.addItem(choice_name, choice_value)
            self.updated_choice_index_value[int].connect(widget.setCurrentIndex)

            if self.colors is not None:
                for i, qcolor in enumerate(self.qcolors):
                    widget.setItemData(i, qcolor, QtCore.Qt.BackgroundRole)

                def update_background_color(idx):
                    if idx < len(self.qcolors):
                        qc = self.qcolors[idx]
                    else:
                        qc = QtGui.QColor("white")

                    s = f"""QComboBox{{
                                selection-background-color: {qc.name()};
                                selection-color: black;
                                background: {qc.name()};
                                }}"""
                    widget.setStyleSheet(widget.styleSheet() + s)

                widget.currentIndexChanged.connect(update_background_color)

        elif isinstance(widget, pg.widgets.SpinBox.SpinBox):
            # widget.setFocusPolicy(QtCore.Qt.StrongFocus)
            suffix = self.unit
            if self.unit is None:
                suffix = ""
            if self.dtype == int:
                integer = True
                minStep = 1
                step = 1
            else:
                integer = False
                minStep = 0.1
                step = 0.1
            opts = dict(
                suffix=suffix,
                siPrefix=True,
                dec=True,
                step=step,
                minStep=minStep,
                bounds=[self.vmin, self.vmax],
                int=integer,
            )
            if self.si:
                del opts["step"]
                del opts["minStep"]

            widget.setOpts(**opts)

            if self.ro:
                widget.setEnabled(False)
                widget.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
                widget.setReadOnly(True)
            # widget.setDecimals(self.spinbox_decimals)
            if not self.si:
                widget.setSingleStep(self.spinbox_step)

            # self.updated_value[float].connect(widget.setValue)
            # if not self.ro:
            # widget.valueChanged[float].connect(self.update_value)

            @QtCore.Slot(float)
            def update_widget_value(x):
                """
                block signals from widget when value is set via lq.update_value.
                This prevents signal loops
                """
                try:
                    widget.blockSignals(True)
                    widget.setValue(x)
                finally:
                    widget.blockSignals(False)

            self.updated_value[float].connect(update_widget_value)

        elif isinstance(widget, QtWidgets.QLabel):
            self.updated_text_value.connect(widget.setText)

        elif isinstance(widget, QtWidgets.QProgressBar):

            @QtCore.Slot(int)
            @QtCore.Slot(float)
            def set_progressbar(x, widget=widget):
                self.log.debug(f"set_progressbar {x}")
                widget.setValue(int(x))

            self.updated_value.connect(set_progressbar)

        elif isinstance(widget, QtWidgets.QLCDNumber):
            self.updated_value[(self.dtype)].connect(widget.display)
        else:
            raise ValueError("Unknown widget type")

        self.send_display_updates(force=True)
        # self.widget = widget
        self.widget_list.append(widget)
        self.change_readonly(self.ro)
        if self.event_filter:
            widget.installEventFilter(self.event_filter)

    def connect_to_pushButton(
        self,
        pushButton: QtWidgets.QPushButton,
        colors=("rgba(105, 240, 104, 220)", "rgba(255, 49, 47, 220)"),
        texts=("▶ START", "🛑 STOP"),
        styleSheet_amendment="""
        QPushButton{ padding:3px }
        QPushButton:hover:!pressed{ border: 1px solid black; }
        """,
    ):
        assert isinstance(pushButton, QtWidgets.QPushButton)
        assert self.dtype == bool

        pushButton.setCheckable(True)

        @QtCore.Slot(bool)
        def update_widget_value(x=None):
            try:
                pushButton.blockSignals(True)
                pushButton.setChecked(self.val)
                pushButton.setText(texts[int(x)])
            finally:
                pushButton.blockSignals(False)

        self.updated_value[bool].connect(update_widget_value)
        pushButton.toggled[bool].connect(self.update_value)

        if self.colors and not colors:
            colors = self.colors
        if colors:
            s = f"""QPushButton:!checked{{ background:{colors[0]}; border: 1px solid grey; }}
                    QPushButton:checked{{ background:{colors[1]}; border: 1px solid grey; }}"""
            pushButton.setStyleSheet(pushButton.styleSheet() + s + styleSheet_amendment)

        if self.ro:
            pushButton.setEnabled(False)

        self.set_widget_toolTip(pushButton)
        self.send_display_updates(force=True)
        self.widget_list.append(pushButton)

    def connect_to_lq(self, lq):
        # FIXME, does not seem to work for dtype=int
        self.updated_value[(self.dtype)].connect(lq.update_value)
        lq.updated_value[(lq.dtype)].connect(self.update_value)

    def change_choice_list(self, choices, new_val=None):
        """
        =============  =================================================
        **Arguments**  **Description**
        *choices*      list of new choices
                       Either of the form [val_1, val_2, ...]
                       or [(name_1, val_1), ...]
        *new_val*      the value that is set after choices have been
                       changed. If None, the previous value is retained,
                       otherwise the last element of *choices*.
        =============  =================================================
        """

        with self.lock:
            self.choices = self._expand_choices(choices)
            for widget in self.widget_list:
                if not isinstance(widget, QtWidgets.QComboBox):
                    continue
                widget.blockSignals(True)
                widget.clear()
                if self.choices is not None:
                    for choice_name, choice_value in self.choices:
                        widget.addItem(choice_name, choice_value)
                widget.blockSignals(False)

        if not self.choices:
            return

        # set a value
        if new_val is None:
            new_val = self.val
        values = [x[1] for x in self.choices]
        if not new_val in values:
            new_val = values[0]
        self.update_value(new_val)

        self.send_display_updates(force=True)

    def add_choices(self, choices, allow_duplicates=False, new_val=None):
        if not isinstance(choices, (list, tuple)):
            choices = [choices]

        if not choices:
            return False

        new_choices = self.choices + self._expand_choices(choices)
        if not allow_duplicates:
            new_choices = remove_duplicates(new_choices)

        if new_val is None:
            new_val = self.val

        self.change_choice_list(new_choices, new_val)
        return True

    def remove_choices(self, choices, new_val=None):
        """
        =============  =================================================
        **Arguments**  **Description**
        *choices*      list of choices to be removed.
                       Either of the form [val_1, val_2, ...]
                       or [(name_1, val_1), ...]

        *new_val*      the value that is set after choices have been
                       changed. If None, the previous value is retained,
                       otherwise the last element of *choices*.
        =============  =================================================
        """
        if not isinstance(choices, (list, tuple)):
            choices = [choices]
        choices = [c for c in self.choices if c not in self._expand_choices(choices)]
        self.change_choice_list(choices, new_val)
        return True

    def change_min_max(self, vmin=-1e12, vmax=+1e12):
        # TODO  setRange should be a slot for the updated_min_max signal
        with self.lock:
            self.vmin = vmin
            self.vmax = vmax
            for widget in self.widget_list:  # may not work for certain widget types
                widget.setRange(vmin, vmax)
            self.updated_min_max.emit(vmin, vmax)

    def change_readonly(self, ro=True):
        with self.lock:
            self.ro = ro
            for widget in self.widget_list:
                if hasattr(widget, "setReadOnly"):
                    widget.setReadOnly(self.ro)
                else:
                    widget.setEnabled(not self.ro)
                # TODO other widget types
            self.updated_readonly.emit(self.ro)

    def change_unit(self, unit):
        with self.lock:
            self.unit = unit
            for widget in self.widget_list:
                if isinstance(widget, QtWidgets.QDoubleSpinBox):
                    if self.unit is not None:
                        widget.setSuffix(f" {self.unit}")

                elif isinstance(widget, pg.widgets.SpinBox.SpinBox):
                    # widget.setFocusPolicy(QtCore.Qt.StrongFocus)
                    suffix = self.unit
                    if self.unit is None:
                        suffix = ""
                    opts = dict(suffix=suffix)

                    widget.setOpts(**opts)

    def is_connected_to_hardware(self):
        """
        :returns: True if either self.hardware_read_func or
        self.hardware_set_func are defined. False if None.
        """
        return (self.hardware_read_func is not None) or (
            self.hardware_set_func is not None
        )

    def has_hardware_read(self):
        return self.hardware_read_func is not None

    def has_hardware_write(self):
        return self.hardware_set_func is not None

    def connect_to_hardware(self, read_func=None, write_func=None):
        if read_func is not None:
            assert callable(read_func)
            self.hardware_read_func = read_func
        if write_func is not None:
            assert callable(write_func)
            self.hardware_set_func = write_func

    def disconnect_from_hardware(self, dis_read=True, dis_write=True):
        if dis_read:
            self.hardware_read_func = None
        if dis_write:
            self.hardware_set_func = None

    def connect_lq_math(self, lqs, func, reverse_func=None):
        """
        Links LQ to other LQs using math functions

        takes a func that takes a set of logged quantities
        new_val = f(lq1, lq2, ...)

        when any of the lqs change, the value of this derived LQ
        will be updated based on func

        reverse_func allows changes to this LQ to update lqs via reverse func

        new_lq1_val, new_lq2_val, ... = g(new_val, old_lqs_values)
        or
        new_lq1_val, new_lq2_val, ... = g(new_val)

        """

        try:
            self.math_lqs = tuple(lqs)
        except TypeError:  # if not iterable, assume its a single LQ
            self.math_lqs = (lqs,)
        self.math_func = func

        self.reverse_math_func = reverse_func
        if reverse_func is not None:
            rev_sig = signature(reverse_func)
            self.reverse_func_num_params = len(rev_sig.parameters)

        def update_math():
            lq_vals = [lq.value for lq in self.math_lqs]
            new_val = self.math_func(*lq_vals)
            # print(self.name, "update_math", lq_vals, "-->", new_val, )
            self.update_value(new_val)

        if reverse_func:

            def update_math_reverse():
                lq_vals = [lq.value for lq in self.math_lqs]
                if self.reverse_func_num_params > 1:
                    new_vals = self.reverse_math_func(self.val, lq_vals)
                else:
                    new_vals = self.reverse_math_func(self.val)

                try:
                    new_vals = tuple(new_vals)
                except TypeError:  # if not iterable, assume its a single value
                    new_vals = (new_vals,)

                for lq, new_val in zip(self.math_lqs, new_vals):
                    lq.update_value(new_val)

        for lq in self.math_lqs:
            lq.updated_value[()].connect(update_math)
            if reverse_func:
                self.add_listener(update_math_reverse)

        update_math()

    def read_from_lq_math(self):
        lq_vals = [lq.value for lq in self.math_lqs]
        new_val = self.math_func(*lq_vals)
        # print("read_from_lq_math", lq_vals, "-->", new_val, )
        self.update_value(new_val)

    def connect_lq_scale(self, lq, scale):
        self.lq_scale = scale
        self.connect_lq_math(
            (lq,),
            func=lambda x: scale * x,
            reverse_func=lambda y, old_vals: [
                y * 1.0 / scale,
            ],
        )

    def new_default_widget(self):
        """returns the appropriate QWidget for the datatype of the
        LQ. automatically connects widget
        """
        if self.default_widget_factory is not None:
            widget = self.default_widget_factory()
        elif self.choices is not None:
            widget = QtWidgets.QComboBox()
        elif self.dtype in [int, float]:
            if self.si:
                widget = pg.SpinBox()
            else:
                widget = QtWidgets.QDoubleSpinBox()
        elif self.dtype in [bool]:
            widget = QtWidgets.QCheckBox()
        elif self.dtype in [str]:
            widget = QtWidgets.QLineEdit()
        self.connect_to_widget(widget)

        if not any((self.is_clipboardable, self.is_cmd)):
            return widget

        wrap_widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(wrap_widget)
        layout.addWidget(widget)
        layout.setSpacing(0)

        if self.is_clipboardable:
            copy_button = QtWidgets.QPushButton("⎘")
            copy_button.setMaximumWidth(25)
            copy_button.setToolTip("copy to clipboard")
            copy_button.clicked.connect(self.copy_to_clipboard)
            layout.addWidget(copy_button)

        if self.is_cmd:
            run_button = QtWidgets.QPushButton("➲")
            run_button.setMaximumWidth(33)
            run_button.setToolTip("run detached")
            run_button.clicked.connect(self.run_subprocess_detached)
            layout.addWidget(run_button)

        return wrap_widget

    def new_pushButton(
        self,
        texts=("▶ START", "🛑 STOP"),
        colors=("rgba(105, 240, 104, 220)", "rgba(255, 49, 47, 220)"),
        **kwargs,
    ):
        """kwargs is past to self.connect_to_pushButton():"""
        assert self.dtype == bool
        pushButton = QtWidgets.QPushButton()
        self.connect_to_pushButton(pushButton, colors, texts, **kwargs)
        return pushButton

    def new_pg_parameter(self):
        from pyqtgraph.parametertree import Parameter

        dtype_map = {str: "str", float: "float", int: "int", bool: "bool"}

        if self.choices:
            print(self.name, "have choices")
            print(self.choices)
            # choices should be tuple [ ('name', val) ... ] or simple list [val, val, ...]

            p = Parameter.create(
                name=self.name, type="list", values=dict(self.choices), value=self.value
            )

            def update_param(v):
                print("updating parameter", self.name, p, v)
                p.setValue(v)

            self.updated_value[self.dtype].connect(
                update_param
            )  # (lambda v, p=p: p.setValue(v))
            p.sigValueChanged.connect(lambda p, v: self.update_value(v))

            return p
        if self.is_array:
            # DOES NOT WORK CORRECTLY
            p = Parameter.create(name=self.name, type="str", value=str(self.value))

            return p
        else:
            p = Parameter.create(
                name=self.name, type=dtype_map[self.dtype], value=self.value
            )

            def update_param(v):
                print("updating parameter", self.name, p, v)
                p.setValue(v)

            self.updated_value[self.dtype].connect(
                update_param
            )  # (lambda v, p=p: p.setValue(v))
            p.sigValueChanged.connect(lambda p, v: self.update_value(v))

            return p

    def set_path(self, path: str):
        self.path = path

    def propose_value(self, name: str, value):
        self.proposed_values.appendleft((name, value))

    def on_right_click(self, position=None):
        cmenu = QtWidgets.QMenu()
        cmenu.addAction(f"{self.path}").setEnabled(False)
        if self.has_hardware_read():
            cmenu.addAction("Read from Hardware", self.read_from_hardware)

        cmenu.addSeparator()
        for action in self.actions:
            cmenu.addAction(*action)
        cmenu.addSeparator()

        # prev. values
        cmenu.addAction("prev. values").setEnabled(False)
        for val in self.prev_vals:
            if self.ro:
                cmenu.addAction(f"{val}")
            else:
                cmenu.addAction(f"{val}", partial(self.update_value, new_val=val))

        # proposed values
        for proposed_name, val in self.proposed_values:
            cmenu.addSeparator()
            cmenu.addAction(proposed_name).setEnabled(False)
            if self.ro:
                cmenu.addAction(f"{val}")
            else:
                cmenu.addAction(f"{val}", partial(self.update_value, new_val=val))

        cmenu.exec_(QtGui.QCursor.pos())

    def connect_to_clipboardable(self, io_widget, copy_button: QtWidgets.QPushButton):
        """type of io_widget"""
        self.connect_to_widget(io_widget)
        copy_button.clicked.connect(self.copy_to_clipboard)

    def copy_to_clipboard(self):
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(self.val)

    def connect_to_run_subprocess_detached(
        self, line_edit: QtWidgets.QWidget, run_button: QtWidgets.QPushButton
    ):
        self.connect_to_widget(line_edit)
        run_button.clicked.connect(self.run_subprocess_detached)

    def run_subprocess_detached(self):
        subprocess.Popen(
            self.val.split(),
            shell=True,
            # stdin=subprocess.PIPE,
            # stdout=subprocess.PIPE,
            # stderr=subprocess.PIPE,
        )


def to_q_color(color, default="lightgrey"):
    try:
        qcolor = QtGui.QColor(color)
    except TypeError:
        qcolor = QtGui.QColor(default)
    finally:
        if qcolor.isValid():
            return qcolor
        return QtGui.QColor(default)


def _expand_choice(c, dtype):
    if isinstance(c, tuple):
        name, val = c
        return (str(name), dtype(val))
    elif isinstance(c, Enum):
        return (c.name, dtype(c.value))
    return (str(c), dtype(c))


# https://stackoverflow.com/questions/480214/how-do-i-remove-duplicates-from-a-list-while-preserving-order
def remove_duplicates(l: List) -> List:
    seen = set()
    seen_add = seen.add
    return [x for x in l if not (x in seen or seen_add(x))]
