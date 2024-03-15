from __future__ import absolute_import, print_function
from qtpy import  QtCore, QtWidgets, QtGui
import pyqtgraph
import numpy as np
from collections import OrderedDict
import json
import sys
from ScopeFoundry.helper_funcs import get_logger_from_class, str2bool, QLock, \
    bool2str
from ScopeFoundry.ndarray_interactive import ArrayLQ_QTableModel
import pyqtgraph as pg
from inspect import signature
from ScopeFoundry.widgets import MinMaxQSlider
import os

#import threading

# python 2/3 compatibility
if sys.version_info[0] == 3:
    unicode = str
    
class DummyLock(object):
    def acquire(self):
        pass
    def release(self):
        pass
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass




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
    updated_value = QtCore.Signal((float,),(int,),(bool,), (), (str,),) 
    # signal sent when value has been updated, sends text representation
    updated_text_value = QtCore.Signal(str) 
    # emits the index of the value in self.choices
    updated_choice_index_value = QtCore.Signal(int)
     
    # signal sent when min max range updated
    updated_min_max = QtCore.Signal((float,float),(int,int), (),)
    # signal sent when read only (ro) status has changed 
    updated_readonly = QtCore.Signal((bool,), (),) 
    
    def __init__(self, name, dtype=float, 
                 #hardware_read_func=None, hardware_set_func=None, 
                 initial=0, fmt="%g", si=False,
                 ro = False, # read only flag
                 unit = None,
                 spinbox_decimals = 2,
                 spinbox_step=0.1,
                 vmin=-1e12, vmax=+1e12, choices=None,
                 reread_from_hardware_after_write = False,
                 description = None,
                 colors = None,
                 protected = False,
                 ):
        QtCore.QObject.__init__(self)
        
        self.name = name
        
        if dtype in [int, str, float]:
            pass
        elif dtype in ['int', 'uint']:
            dtype = int
        elif dtype in ['float', 'float32']:
            dtype = float
        
        self.dtype = dtype
        self.val = dtype(initial)
        self.hardware_read_func = None
        self.hardware_set_func = None
        self.fmt = fmt # string formatting string. This is ignored if dtype==str
        if self.dtype == str:
            self.fmt = "%s"
        self.si   = si # will use pyqtgraph SI Spinbox if True
        self.unit = unit
        self.vmin = vmin
        self.vmax = vmax
        # choices should be tuple [ ('name', val) ... ] or simple list [val, val, ...]
        self.choices = self._expand_choices(choices) 
        self.ro = ro # Read-Only
        self.is_array = False
        self.description = description
        
        self.colors = colors
        self.qcolors = []
        if self.colors:
            default_color = QtGui.QColor('lightgrey')
            for color in colors:
                try:
                    qcolor = QtGui.QColor(color)
                except TypeError:
                    qcolor = default_color
                if qcolor.isValid():
                    self.qcolors.append(qcolor)
                else:
                    self.qcolors.append(default_color)
        
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
        
        self.oldval = None
        
        self._in_reread_loop = False # flag to prevent reread from hardware loops
        
        self.widget_list = []
        self.listeners = []
        
        # threading lock
        #self.lock = threading.Lock()
        #self.lock = DummyLock()
        self.lock = QLock(mode=1) # mode 0 is non-reentrant lock
        
        self.path = ""
        self.protected = protected # a guard that prevents from being updated, i.e. file loading


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
        if self.dtype==bool and isinstance(x, str):
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
        
    def _expand_choices(self, choices):
        if choices is None:
            return None
        expanded_choices = []
        for c in choices:
            if isinstance(c, tuple):
                name, val = c
                expanded_choices.append( ( str(name), self.dtype(val) ) )
            else:
                expanded_choices.append( ( str(c), self.dtype(c) ) )
        return expanded_choices
    
    def __str__(self):
        return "{} = {}".format(self.name, self.val)
    
    def __repr__(self):
        return "LQ: {} = {}".format(self.name, self.val)

    
    def read_from_hardware(self, send_signal=True):
        self.log.debug("{}: read_from_hardware send_signal={}".format(self.name, send_signal))
        if self.hardware_read_func is not None:        
            with self.lock:
                self.oldval = self.val
                val = self.hardware_read_func()
            self.update_value(new_val=val, update_hardware=False, send_signal=send_signal)
        else:
            self.log.warn("{} read_from_hardware called when not connected to hardware".format(self.name))
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
    def update_value(self, new_val=None, update_hardware=True, send_signal=True, reread_hardware=None):
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
                if hasattr(self.sender(), 'text'):
                    new_val = self.sender().text()
    
            self.oldval = self.coerce_to_type(self.val)
            new_val = self.coerce_to_type(new_val)
            
            self.log.debug("{}: update_value {} --> {}    sender={}".format(
                            self.name, repr(self.oldval), repr(new_val), repr(self.sender())))
    
            # check for equality of new vs old, do not proceed if they are same
            if self.same_values(self.oldval, new_val):
                self.log.debug("{}: same_value so returning {} {}".format(self.name, self.oldval, new_val))
                return
            else:
                self.log.debug("{}: different values {} {}".format(self.name, self.oldval, new_val))
                
            # actually change internal state value
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
        #self.log.debug("{}:send_display_updates: force={}. From {} to {}".format(self.name, force, self.oldval, self.val))
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
                    self.updated_choice_index_value.emit(choice_vals.index(self.val) )
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
        \*\*kwargs are passed to the connect function
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

    def connect_bidir_to_widget(self, widget):
        # DEPRECATED
        return self.connect_to_widget(widget)
    
    
    def set_widget_toolTip(self, widget, text=None):
        try:
            tips = [f'<b>{self.path}</b>']
            if self.unit: tips.append(f'<i>({self.unit})</i>')
            for s in [self.description, widget.toolTip(), text]:
                if s != None:
                    tips.append(str(s))
            widget.setToolTip(' '.join(tips))
            return tips
        except:
            pass        


    def connect_to_widget(self, widget):
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
       
        if type(widget) == QtWidgets.QDoubleSpinBox:

            widget.setKeyboardTracking(False)
            if self.vmin is not None:
                widget.setMinimum(self.vmin)
            if self.vmax is not None:
                widget.setMaximum(self.vmax)
            if self.unit is not None:
                widget.setSuffix(" "+self.unit)
            widget.setDecimals(self.spinbox_decimals)
            widget.setSingleStep(self.spinbox_step)
            widget.setValue(self.val)
            #events
            def update_widget_value(x):
                """
                block signals from widget when value is set via lq.update_value.
                This prevents signal-slot loops between widget and lq
                """
                try:
                    widget.blockSignals(True)
                    widget.setValue(x)
                finally:
                    widget.blockSignals(False)                    
            #self.updated_value[float].connect(widget.setValue)
            self.updated_value[float].connect(update_widget_value)
            #if not self.ro:
            widget.valueChanged[float].connect(self.update_value)
        
        elif type(widget) == MinMaxQSlider:
            self.updated_value[float].connect(widget.update_value)
            widget.updated_value[float].connect(self.update_value)
            if self.unit is not None:
                widget.setSuffix(self.unit)
            widget.setSingleStep(self.spinbox_step)
            widget.setDecimals(self.spinbox_decimals)
            widget.setRange(self.vmin, self.vmax)
            widget.set_name(self.name)
        
        elif type(widget) == QtWidgets.QSlider:
            if self.dtype == float:
                self.vrange = self.vmax - self.vmin
                def transform_to_slider(x):
                    pct = 100*(x-self.vmin)/self.vrange
                    return int(pct)
                def transform_from_slider(x):
                    val = self.vmin + (x*self.vrange/100)
                    return val
                def update_widget_value(x):
                    """
                    block signals from widget when value is set via lq.update_value.
                    This prevents signal-slot loops between widget and lq
                    """
                    try:
                        widget.blockSignals(True)
                        widget.setValue(transform_to_slider(x))
                    finally:
                        widget.blockSignals(False)
                        
                def update_spinbox(x):
                    self.update_value(transform_from_slider(x))    
                if self.vmin is not None:
                    widget.setMinimum(transform_to_slider(self.vmin))
                if self.vmax is not None:
                    widget.setMaximum(transform_to_slider(self.vmax))
                widget.setSingleStep(1)
                widget.setValue(transform_to_slider(self.val))
                self.updated_value[float].connect(update_widget_value)
                widget.valueChanged[int].connect(update_spinbox)
            elif self.dtype == int:
                self.updated_value[int].connect(widget.setValue)
                #widget.sliderMoved[int].connect(self.update_value)
                widget.valueChanged[int].connect(self.update_value)
                
                widget.setSingleStep(1)            
                
        elif type(widget) == QtWidgets.QCheckBox:

            def update_widget_value(x):
                lq = widget.sender()
                #self.log.debug("LQ {} update qcheckbox: {} arg{} lq value{}".format(lq.name,   widget, x, lq.value))                
                widget.setChecked(lq.value)                    

            self.updated_value[bool].connect(update_widget_value)
            widget.clicked[bool].connect(self.update_value) # another option is stateChanged signal
            if self.ro:
                #widget.setReadOnly(True)
                widget.setEnabled(False)
                
            if self.colors != None:
                if len(self.colors) in (2,3): # QCheckBoxes can have 3 states! (tristate)
                    if len(self.colors) == 2:
                        colors = [self.colors[0], 'lightgrey', self.colors[1]]
                    elif len(self.qcolors) == 3:
                        colors = self.colors
                    s = f"""QCheckBox:!checked {{ background: {colors[0]} }}
                            QCheckBox:checked  {{ background: {colors[2]} }}"""
                    widget.setStyleSheet(widget.styleSheet() + s)
                
                                
        elif type(widget) == QtWidgets.QLineEdit:
            self.updated_text_value[str].connect(widget.setText)
            self.updated_value[str].connect(widget.setText)
            if self.ro:
                widget.setReadOnly(True)  # FIXME
            def on_edit_finished():
                self.log.debug(self.name + " qLineEdit on_edit_finished")
                try:
                    widget.blockSignals(True)
                    self.update_value(widget.text())
                finally:
                    widget.blockSignals(False)
            widget.editingFinished.connect(on_edit_finished)
            
        elif type(widget) == QtWidgets.QPlainTextEdit:
            # TODO Read only
            
            def on_lq_changed(new_text):
                current_cursor = widget.textCursor()
                current_cursor_pos = current_cursor.position()
                #print('current_cursor', current_cursor, current_cursor.position())
                widget.document().setPlainText(new_text)
                current_cursor.setPosition(current_cursor_pos)
                widget.setTextCursor(current_cursor)
                #print('current_cursor', current_cursor, current_cursor.position())
            
            def on_widget_textChanged():
                try:
                    widget.blockSignals(True)
                    self.update_value(widget.toPlainText())
                finally:
                    widget.blockSignals(False)

            #self.updated_text_value[str].connect(widget.document().setPlainText)
            self.updated_text_value[str].connect(on_lq_changed)
            widget.textChanged.connect(on_widget_textChanged)
            
        elif type(widget) == QtWidgets.QComboBox:
            # need to have a choice list to connect to a QComboBox
            assert self.choices is not None 
            widget.clear() # removes all old choices
            for choice_name, choice_value in self.choices:
                widget.addItem(choice_name, choice_value)
            self.updated_choice_index_value[int].connect(widget.setCurrentIndex)
            widget.currentIndexChanged.connect(self.update_choice_index_value)
            if self.colors != None:
                if len(self.qcolors) == len(self.choices):
                    for i,qcolor in enumerate(self.qcolors):
                        widget.setItemData(i,  qcolor, QtCore.Qt.BackgroundRole )
                        
                    def update_background_color(idx):
                        qcolor = self.qcolors[idx]
                        s = f"""QComboBox{{
                                    selection-background-color: {qcolor.name()};
                                    selection-color: black;
                                    background: {qcolor.name()};
                                    }}"""                      
                        widget.setStyleSheet(widget.styleSheet() + s)
                    widget.currentIndexChanged.connect(update_background_color)
            
        elif type(widget) == pyqtgraph.widgets.SpinBox.SpinBox:
            #widget.setFocusPolicy(QtCore.Qt.StrongFocus)
            suffix = self.unit
            if self.unit is None:
                suffix = ""
            if self.dtype == int:
                integer = True
                minStep=1
                step=1
            else:
                integer = False
                minStep=.1
                step=.1
            opts = dict(
                        suffix=suffix,
                        siPrefix=True,
                        dec=True,
                        step=step,
                        minStep=minStep,
                        bounds=[self.vmin, self.vmax],
                        int=integer)
            if self.si:
                del opts['step']
                del opts['minStep']
            
            widget.setOpts(**opts)
                      
            if self.ro:
                widget.setEnabled(False)
                widget.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
                widget.setReadOnly(True)
            #widget.setDecimals(self.spinbox_decimals)
            if not self.si:
                widget.setSingleStep(self.spinbox_step)
            #self.updated_value[float].connect(widget.setValue)
            #if not self.ro:
                #widget.valueChanged[float].connect(self.update_value)
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
            


        elif type(widget) == QtWidgets.QLabel:
            self.updated_text_value.connect(widget.setText)
        elif type(widget) == QtWidgets.QProgressBar:
            def set_progressbar(x, widget=widget):
                self.log.debug("set_progressbar {}".format(x))
                widget.setValue(int(x))
            self.updated_value.connect(set_progressbar)
        elif type(widget) == QtWidgets.QLCDNumber:
            self.updated_value[(self.dtype)].connect(widget.display)
        else:
            raise ValueError("Unknown widget type")
        
        self.send_display_updates(force=True)
        #self.widget = widget
        self.widget_list.append(widget)
        self.change_readonly(self.ro)

    def connect_to_widget_one_way(self, widget):
        """
        Creates Qt signal-slot connections between LQ and the QtWidget *widget* ONLY IN ONE WAY. CHANGES IN WIDGET WILL NOT TRANSFER TO LQ!!!
        rest is the same as connect_to_widget

        """
        
        self.set_widget_toolTip(widget)
       
        if type(widget) == QtWidgets.QDoubleSpinBox:

            widget.setKeyboardTracking(False)
            if self.vmin is not None:
                widget.setMinimum(self.vmin)
            if self.vmax is not None:
                widget.setMaximum(self.vmax)
            if self.unit is not None:
                widget.setSuffix(" "+self.unit)
            widget.setDecimals(self.spinbox_decimals)
            widget.setSingleStep(self.spinbox_step)
            widget.setValue(self.val)
            #events
            def update_widget_value(x):
                """
                block signals from widget when value is set via lq.update_value.
                This prevents signal-slot loops between widget and lq
                """
                try:
                    widget.blockSignals(True)
                    widget.setValue(x)
                finally:
                    widget.blockSignals(False)                    
            #self.updated_value[float].connect(widget.setValue)
            self.updated_value[float].connect(update_widget_value)
        
        elif type(widget) == MinMaxQSlider:
            self.updated_value[float].connect(widget.update_value)
            if self.unit is not None:
                widget.setSuffix(self.unit)
            widget.setSingleStep(self.spinbox_step)
            widget.setDecimals(self.spinbox_decimals)
            widget.setRange(self.vmin, self.vmax)
            widget.set_name(self.name)
        
        elif type(widget) == QtWidgets.QSlider:
            if self.dtype == float:
                self.vrange = self.vmax - self.vmin
                def transform_to_slider(x):
                    pct = 100*(x-self.vmin)/self.vrange
                    return int(pct)
                def transform_from_slider(x):
                    val = self.vmin + (x*self.vrange/100)
                    return val
                def update_widget_value(x):
                    """
                    block signals from widget when value is set via lq.update_value.
                    This prevents signal-slot loops between widget and lq
                    """
                    try:
                        widget.blockSignals(True)
                        widget.setValue(transform_to_slider(x))
                    finally:
                        widget.blockSignals(False)
                         
                if self.vmin is not None:
                    widget.setMinimum(transform_to_slider(self.vmin))
                if self.vmax is not None:
                    widget.setMaximum(transform_to_slider(self.vmax))
                widget.setSingleStep(1)
                widget.setValue(transform_to_slider(self.val))
                self.updated_value[float].connect(update_widget_value)
            elif self.dtype == int:
                self.updated_value[int].connect(widget.setValue)
                widget.setSingleStep(1)            
                
        elif type(widget) == QtWidgets.QCheckBox:

            def update_widget_value(x):
                lq = widget.sender()
                #self.log.debug("LQ {} update qcheckbox: {} arg{} lq value{}".format(lq.name,   widget, x, lq.value))                
                widget.setChecked(lq.value)                    

            self.updated_value[bool].connect(update_widget_value)
            if self.ro:
                #widget.setReadOnly(True)
                widget.setEnabled(False)
                
            if self.colors != None:
                if len(self.colors) in (2,3): # QCheckBoxes can have 3 states! (tristate)
                    if len(self.colors) == 2:
                        colors = [self.colors[0], 'lightgrey', self.colors[1]]
                    elif len(self.qcolors) == 3:
                        colors = self.colors
                    s = f"""QCheckBox:!checked {{ background: {colors[0]} }}
                            QCheckBox:checked  {{ background: {colors[2]} }}"""
                    widget.setStyleSheet(widget.styleSheet() + s)
                
                                
        elif type(widget) == QtWidgets.QLineEdit:
            self.updated_text_value[str].connect(widget.setText)
            self.updated_value[str].connect(widget.setText)
            if self.ro:
                widget.setReadOnly(True)  # FIXME
            
        elif type(widget) == QtWidgets.QPlainTextEdit:
            # TODO Read only
            
            def on_lq_changed(new_text):
                current_cursor = widget.textCursor()
                current_cursor_pos = current_cursor.position()
                #print('current_cursor', current_cursor, current_cursor.position())
                widget.document().setPlainText(new_text)
                current_cursor.setPosition(current_cursor_pos)
                widget.setTextCursor(current_cursor)
                #print('current_cursor', current_cursor, current_cursor.position())

            #self.updated_text_value[str].connect(widget.document().setPlainText)
            self.updated_text_value[str].connect(on_lq_changed)
            
        elif type(widget) == QtWidgets.QComboBox:
            # need to have a choice list to connect to a QComboBox
            assert self.choices is not None 
            widget.clear() # removes all old choices
            for choice_name, choice_value in self.choices:
                widget.addItem(choice_name, choice_value)
            self.updated_choice_index_value[int].connect(widget.setCurrentIndex)
            if self.colors != None:
                if len(self.qcolors) == len(self.choices):
                    for i,qcolor in enumerate(self.qcolors):
                        widget.setItemData(i,  qcolor, QtCore.Qt.BackgroundRole )
                        
                    def update_background_color(idx):
                        qcolor = self.qcolors[idx]
                        s = f"""QComboBox{{
                                    selection-background-color: {qcolor.name()};
                                    selection-color: black;
                                    background: {qcolor.name()};
                                    }}"""                      
                        widget.setStyleSheet(widget.styleSheet() + s)
                    widget.currentIndexChanged.connect(update_background_color)
            
        elif type(widget) == pyqtgraph.widgets.SpinBox.SpinBox:
            #widget.setFocusPolicy(QtCore.Qt.StrongFocus)
            suffix = self.unit
            if self.unit is None:
                suffix = ""
            if self.dtype == int:
                integer = True
                minStep=1
                step=1
            else:
                integer = False
                minStep=.1
                step=.1
            opts = dict(
                        suffix=suffix,
                        siPrefix=True,
                        dec=True,
                        step=step,
                        minStep=minStep,
                        bounds=[self.vmin, self.vmax],
                        int=integer)
            if self.si:
                del opts['step']
                del opts['minStep']
            
            widget.setOpts(**opts)
                      
            if self.ro:
                widget.setEnabled(False)
                widget.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
                widget.setReadOnly(True)
            #widget.setDecimals(self.spinbox_decimals)
            if not self.si:
                widget.setSingleStep(self.spinbox_step)
            #self.updated_value[float].connect(widget.setValue)
            #if not self.ro:
                #widget.valueChanged[float].connect(self.update_value)
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
            

        elif type(widget) == QtWidgets.QLabel:
            self.updated_text_value.connect(widget.setText)
        elif type(widget) == QtWidgets.QProgressBar:
            def set_progressbar(x, widget=widget):
                self.log.debug("set_progressbar {}".format(x))
                widget.setValue(int(x))
            self.updated_value.connect(set_progressbar)
        elif type(widget) == QtWidgets.QLCDNumber:
            self.updated_value[(self.dtype)].connect(widget.display)
        else:
            raise ValueError("Unknown widget type")
        
        self.send_display_updates(force=True)
        #self.widget = widget
        self.widget_list.append(widget)
        self.change_readonly(self.ro)
        
    def connect_to_pushButton(self, pushButton, colors=['rgba( 0, 255, 0, 180)','rgba(255, 69, 0, 180)'], 
                              texts=['START', 'INTERRUPT'],
                              styleSheet_amendment = '''QPushButton{ padding:3px }
                                                        QPushButton:hover:!pressed{ border: 1px solid black; }
                                                         '''):
        assert type(pushButton) == QtWidgets.QPushButton
        assert self.dtype == bool
        if colors==None and self.colors!=None:
            colors = self.colors
        pushButton.setCheckable(True)
        def update_pushButton_value(x):
            lq = pushButton.sender()
            pushButton.setChecked(lq.value)
            pushButton.setText(texts[int(x)])              
        self.updated_value[bool].connect(update_pushButton_value)
        pushButton.toggled[bool].connect(self.update_value)
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
        
    
    def change_choice_list(self, choices):
        #widget = self.widget
        with self.lock:
            self.choices = self._expand_choices(choices)
            
            for widget in self.widget_list:
                if type(widget) == QtWidgets.QComboBox:
                    # need to have a choice list to connect to a QComboBox
                    assert self.choices is not None 
                    try:
                        widget.blockSignals(True)
                        widget.clear() # removes all old choices
                        for choice_name, choice_value in self.choices:
                            widget.addItem(choice_name, choice_value)
                    finally:
                        widget.blockSignals(False)
                else:
                    raise RuntimeError("Invalid widget type.")
        
        self.send_display_updates(force=True)
        
    
    def add_choices(self, choices, allow_duplicates=False, new_val=None):
        if not isinstance(choices, (list, tuple)):
            choices = [choices]
        choices = self._expand_choices(choices)
        if not allow_duplicates:
            choices = list( set(choices) - set(self.choices) )
        if len(choices) > 0:
            new_choices_list = self.choices + choices
            self.change_choice_list(new_choices_list)
            if new_val is None:
                new_val = new_choices_list[-1][1]
            self.update_value(new_val)
            return True
        else:
            return False
        
    def remove_choices(self, choices, new_val=None):
        '''
        *choices*   list of choices to be removed.
        *new_val*   the value the function tries to update to (if still exists)
                    if None (default), *new_val* is replaced by current value.
        '''
        v0 = self.val
        if not isinstance(choices, (list, tuple)):
            choices = [choices]
        choices = self._expand_choices(choices)
        new_choices_list = list( set(self.choices) - set(choices) )
        if len(new_choices_list) < len(self.choices):
            self.change_choice_list(new_choices_list)
            if new_val == None:
                new_val = v0
            for c,v in new_choices_list:
                if v==self.dtype(new_val):
                    self.update_value(self.dtype(new_val))
                    break
                else:
                    self.update_value(new_choices_list[-1][1])
            return True
        else:
            return False
    
    def change_min_max(self, vmin=-1e12, vmax=+1e12):
        # TODO  setRange should be a slot for the updated_min_max signal
        with self.lock:
            self.vmin = vmin
            self.vmax = vmax
            for widget in self.widget_list: # may not work for certain widget types
                widget.setRange(vmin, vmax)
            self.updated_min_max.emit(vmin,vmax)
        
    def change_readonly(self, ro=True):
        with self.lock:
            self.ro = ro
            for widget in self.widget_list:
                if type(widget) in [QtWidgets.QDoubleSpinBox, pyqtgraph.widgets.SpinBox.SpinBox]:
                    widget.setReadOnly(self.ro)
                else:
                    widget.setEnabled(not self.ro)
                #TODO other widget types
            self.updated_readonly.emit(self.ro)
            
    def change_unit(self, unit):
        with self.lock:
            self.unit = unit
            for widget in self.widget_list:
                if type(widget) == QtWidgets.QDoubleSpinBox:
                    if self.unit is not None:
                        widget.setSuffix(" "+self.unit)
                         
                elif type(widget) == pyqtgraph.widgets.SpinBox.SpinBox:
                    #widget.setFocusPolicy(QtCore.Qt.StrongFocus)
                    suffix = self.unit
                    if self.unit is None:
                        suffix = ""
                    opts = dict(
                                suffix=suffix)
                     
                    widget.setOpts(**opts)
    
    def is_connected_to_hardware(self):
        """
        :returns: True if either self.hardware_read_func or 
        self.hardware_set_func are defined. False if None.
        """
        return (self.hardware_read_func is not None) or (self.hardware_set_func is not None)
    
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
        except TypeError: # if not iterable, assume its a single LQ
            self.math_lqs = (lqs,)
        self.math_func = func
        
        self.reverse_math_func = reverse_func
        if reverse_func is not None:
            rev_sig = signature(reverse_func)
            self.reverse_func_num_params = len(rev_sig.parameters)
        
        def update_math():
            lq_vals = [lq.value for lq in self.math_lqs]
            new_val = self.math_func(*lq_vals)
            #print(self.name, "update_math", lq_vals, "-->", new_val, )
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
                except TypeError: # if not iterable, assume its a single value
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
        #print("read_from_lq_math", lq_vals, "-->", new_val, )
        self.update_value(new_val)
        

    def connect_lq_scale(self, lq, scale):
        self.lq_scale = scale
        self.connect_lq_math((lq,), func=lambda x: scale*x,
                          reverse_func=lambda y, old_vals: [y * 1.0/scale,])

    def new_default_widget(self):
        """ returns the appropriate QWidget for the datatype of the
        LQ. automatically connects widget
        """
        if self.choices is not None:
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
        
        return widget
    
    def new_pushButton(self, **kwargs):
        '''kwargs is past to self.connect_to_pushButton(): '''        
        assert self.dtype == bool
        pushButton = QtWidgets.QPushButton()
        self.connect_to_pushButton(pushButton, **kwargs)
        return pushButton
    
    def new_pg_parameter(self):
        from pyqtgraph.parametertree import Parameter
        dtype_map = {str: 'str', float:'float', int:'int', bool:'bool'}
        
        if self.choices:
            print(self.name, "have choices")
            print(self.choices)
            # choices should be tuple [ ('name', val) ... ] or simple list [val, val, ...]

            p = Parameter.create(name=self.name, type='list', values=dict(self.choices), value=self.value)
            
            def update_param(v):
                print("updating parameter", self.name, p, v)
                p.setValue(v)

            
            self.updated_value[self.dtype].connect(update_param)#(lambda v, p=p: p.setValue(v))
            p.sigValueChanged.connect(lambda p,v: self.update_value(v))

            return p
        if self.is_array:
            # DOES NOT WORK CORRECTLY
            p = Parameter.create(name=self.name, type='str', value=str(self.value))
            
            return p
        else: 
            p = Parameter.create(name=self.name, type=dtype_map[self.dtype], value=self.value)
            
            def update_param(v):
                print("updating parameter", self.name, p, v)
                p.setValue(v)
                
            self.updated_value[self.dtype].connect(update_param)#(lambda v, p=p: p.setValue(v))
            p.sigValueChanged.connect(lambda p,v: self.update_value(v))
            
            return p
        
    def set_path(self, path:str):
        self.path = path
        

class FileLQ(LoggedQuantity):
    """
    Specialized str type :class:`LoggedQuantity` that handles 
    a filename (or directory) and associated file.
    """
     
    def __init__(self, name, default_dir=None, is_dir=False, **kwargs):
        kwargs.pop('dtype', None)
        
        LoggedQuantity.__init__(self, name, dtype=str, **kwargs)
        
        self.default_dir = default_dir
        self.is_dir = is_dir
        
    def connect_to_browse_widgets(self, lineEdit, pushButton):
        assert type(lineEdit) == QtWidgets.QLineEdit
        self.connect_to_widget(lineEdit)

        if self.default_dir is not None:
            lineEdit.setText(self.default_dir)
        else:
            lineEdit.setText(os.getcwd())
    
        assert type(pushButton) == QtWidgets.QPushButton
        pushButton.clicked.connect(self.file_browser)
    
    def file_browser(self):
        if self.is_dir:
            fname = QtWidgets.QFileDialog.getExistingDirectory(directory=self.default_dir)
        else:
            fname, _ = QtWidgets.QFileDialog.getOpenFileName(directory=self.default_dir)
        self.log.debug(repr(fname))
        if fname:
            self.update_value(fname)
            
    def new_default_widget(self):
        lineEdit = QtWidgets.QLineEdit()
        browseButton = QtWidgets.QPushButton('...')
        self.connect_to_browse_widgets(lineEdit, browseButton)
        widget = QtWidgets.QWidget()
        widget.setLayout(QtWidgets.QHBoxLayout())
        widget.layout().addWidget(lineEdit)
        widget.layout().addWidget(browseButton)
        return widget

class ArrayLQ(LoggedQuantity):
    updated_shape = QtCore.Signal(str)
    
    def __init__(self, name, dtype=float, 
                 #hardware_read_func=None, hardware_set_func=None, 
                 initial=[], fmt="%g", si=True,
                 ro = False,
                 unit = None,
                 vmin=-1e12, vmax=+1e12, choices=None,
                 description=None,
                 protected=False):
        QtCore.QObject.__init__(self)
        
        self.name = name
        self.dtype = dtype
        if self.dtype == str:
            self.val = np.array(initial, dtype=object)
        else:
            self.val = np.array(initial, dtype=dtype)
        self.hardware_read_func = None
        self.hardware_set_func = None
        self.fmt = fmt # % string formatting string. This is ignored if dtype==str
        if self.dtype == str:
            self.fmt = "%s"
        self.unit = unit
        self.vmin = vmin
        self.vmax = vmax
        self.ro = ro # Read-Only
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
        
        self._in_reread_loop = False # flag to prevent reread from hardware loops
        
        self.widget_list = []
        self.listeners = []

        # threading lock
        self.lock = QLock(mode=0) # mode 0 is non-reentrant lock
        
        self.is_array = True
        
        self._tableView = None
        

    def same_values(self, v1, v2):
        if v1.shape == v2.shape:
            return np.all(v1 == v2)
            self.log.debug("same_values %s %s" % (v2-v1, np.all(v1 == v2)))        
        else:
            return False

    def change_shape(self, newshape):
        #TODO
        pass
 
    def string_value (self):
        return json.dumps(self.val.tolist())
    
    def ini_string_value(self):
        return json.dumps(self.val.tolist())
    
    def coerce_to_type(self, x):
        #print type(x)
        if type(x) in (unicode, str):
            x = json.loads(x)
            #print repr(x)
        return np.array(x, dtype=self.dtype)
    
    def send_display_updates(self, force=False):
        with self.lock:            
            self.log.debug(self.name + ' send_display_updates')
            #print "send_display_updates: {} force={}".format(self.name, force)
            if force or np.any(self.oldval != self.val):
                
                #print "send display updates", self.name, self.val, self.oldval
                str_val = self.string_value()
                self.updated_value[str].emit(str_val)
                self.updated_text_value.emit(str_val)
                    
                #self.updated_value[float].emit(self.val)
                #if self.dtype != float:
                #    self.updated_value[int].emit(self.val)
                #self.updated_value[bool].emit(self.val)
                self.updated_value[()].emit()
                
                self.oldval = self.val
            else:
                self.log.debug(self.name + ' send_display_updates skipped (olval!=self.val)={} force={} oldval={} val={}'.format(
                    (self.oldval != self.val) , (force), self.oldval, self.val))
                #print "\t no updates sent", (self.oldval != self.val) , (force), self.oldval, self.val
    
    @property
    def array_tableView(self):
        if self._tableView == None:
            self._tableView  = self.create_tableView()
            self._tableView.setWindowTitle(self.name)
        return self._tableView
    
    def create_tableView(self, **kwargs):
        widget = QtWidgets.QTableView()
        #widget.horizontalHeader().hide()
        #widget.verticalHeader().hide()
        model = ArrayLQ_QTableModel(self, transpose=(len(self.val.shape) == 1), **kwargs)
        widget.setModel(model)
        return widget


    def connect_element_follower_lq(self, lq, index, bidir=True):
        """
        connects an LQ to follow the changes of the array and display a specific element
        """            
        # when self (array_lq) is update, update follower lq
        lq.connect_lq_math((self,),
                           func=lambda arr, index=index: arr[index])
        
        if bidir:
            # when LQ is updated, update element in self
            def on_element_follower_lq(lq=lq, arr_lq=self, index=index):
                #print("on_element_follower_lq", arr_lq.value, lq.value, index)
                old_val = arr_lq.value[index]
                new_val = lq.value
                if new_val == old_val:
                    return
                new_arr = arr_lq.value.copy()
                new_arr[index] = new_val 
                arr_lq.update_value(new_arr)

            lq.add_listener(on_element_follower_lq)

    def new_default_widget(self):
        widget = self.create_tableView()
        widget.horizontalHeader().hide()
        widget.verticalHeader().hide()
        return widget


class LQCircularNetwork(QtCore.QObject):
    '''
    LQCircularNetwork is collection of logged quantities
    Helper class if a network of lqs with circular structures are present
    Use update_values_synchronously method if the specified lqs should 
    be updated at once. The internal lock-flag prevents infinite loops. 
    '''
    updated_values = QtCore.Signal((),)
    
    def __init__(self, lq_dict=None, lq_list=None):
        if lq_dict is None:
            lq_dict = dict()
        if lq_list is not None:
            for lq in lq_list:
                lq_dict[lq.name] = lq
        self.lq_dict = lq_dict  # {lq_key:lq}
        self.locked = False     # some lock that does NOT allow blocked routines to be executed after release()
                                # a flag (as it is now) works well.

    
    def update_values_synchronously(self,**kwargs):
        '''
        kwargs is dict containing lq_key and new_vals 
        Note: lq_key is not necessarily the name of the lq but key of lq_dict
              as specified at initialization
        '''
        if self.locked == False:
            self.locked = True
            for kev,val in kwargs.items():
                self.lq_dict[kev].update_value(val)
                self.updated_values.emit()
                self.locked = False
                
    def add_lq(self, lq, name=None):
        if name is None:
            name = lq.name
        self.lq_dict[name] = lq



class LQRange(LQCircularNetwork):
    """
    LQRange is a collection of logged quantities that describe a
    numpy.linspace array inputs.
    Four (or six) LQ's are defined, min, max, num, step (center, span)
    and are connected by signals/slots that keep the quantities
    in sync.
    LQRange.array is the linspace array and is kept upto date
    with changes to the 4 (or 6) LQ's
    """       

    def __init__(self, min_lq:LoggedQuantity, max_lq:LoggedQuantity, step_lq:LoggedQuantity, num_lq:LoggedQuantity, center_lq:LoggedQuantity=None, span_lq:LoggedQuantity=None, sweep_type_lq:LoggedQuantity=None):
        QtCore.QObject.__init__(self)
        self.log = get_logger_from_class(self)
        self.min = min_lq
        self.max = max_lq
        self.num = num_lq
        self.step = step_lq
        self.center = center_lq
        self.span = span_lq
        
        lq_dict = {'min':self.min, 'max':self.max, 'num':self.num, 'step':self.step}        
        
        if self.center == None: 
            assert self.span == None, 'Invalid initialization of LQRange'
        else:
            lq_dict.update({'center':self.center})
        if self.span == None: 
            assert self.center == None, 'Invalid initialization of LQRange'
        else:
            lq_dict.update({'span':self.span})
        
        LQCircularNetwork.__init__(self, lq_dict)
      
        '''
        Note: {step, num} and {min,max,span,center} form each 2 circular subnetworks
        The listener functions update the subnetworks, a connect_lq_math connects 
         {min,max,span,center} to {step, num} unidirectional
        '''        
        self.num.add_listener(self.on_change_num)
        self.step.add_listener(self.on_change_step)              
        if self.center and self.span:
            self.center.add_listener(self.on_change_center_span)
            self.span.add_listener(self.on_change_center_span)
            self.min.add_listener(self.on_change_min_max)
            self.max.add_listener(self.on_change_min_max)

        self.step.connect_lq_math((self.min,self.max,self.num), self.calc_step)
        
        if sweep_type_lq is not None:
            self.sweep_type_map = {'up':self.up_sweep_array,           'down':self.down_sweep_array, 
                                   'up_down':self.up_down_sweep_array, 'down_up':self.down_up_sweep_array,
                                   'zig_zag':self.zig_zag_sweep_array, 'zag_zig':self.zag_zig_sweep_array}
            self.sweep_type = sweep_type_lq
            self.sweep_type.change_choice_list(self.sweep_type_map.keys())
            lq_dict["sweep_type"] = sweep_type_lq

    def calc_num(self, min_, max_, step):
        '''
        enforces num to be a positive integer and adjust step accordingly
        returns num,step 
        '''
        span = max_-min_
        if step==0:
            n = 10 
        else: 
            n = span/step #num = n+1 
            if n < 0:
                n = -n
            n = np.ceil(n)
        step = span/n
        num = n+1
        return int(num),step
    
    def calc_step(self, min_, max_, num):
        """
        excludes num=1 to prevent division by zero,
        returns step
        """
        if num==1: #prevent division by zero
            num = 2
        step=(max_-min_)/(num-1)
        return step
    
    def calc_span(self, min_, max_):
        return (max_-min_)
    
    
    def calc_center(self, min_, max_):
        return (max_-min_)/2+min_

    def calc_min(self, center, span):
        return center-span/2.0
    
    def calc_max(self, center, span):
        return center+span/2.0  
    
    def on_change_step(self):
        step = self.step.val
        num,step = self.calc_num(self.min.val, self.max.val, step)
        self.update_values_synchronously(num=num, step=step)
        
    def on_change_num(self):
        num = self.num.val
        if num ==1:
            num = 2
        step = self.calc_step(self.min.val, self.max.val, self.num.val)
        self.update_values_synchronously(num=num,step=step)
               
    def on_change_min_max(self):
        min_ = self.min.val
        max_ = self.max.val
        span = self.calc_span(min_, max_)
        center = self.calc_center(min_, max_)
        self.update_values_synchronously(span=span, center=center)
        
    def on_change_center_span(self):
        span = self.span.val
        center = self.center.val
        min_ = self.calc_min(center, span)
        max_ = self.calc_max(center, span)
        self.update_values_synchronously(min=min_, max=max_)
    
    @property
    def array(self):
        return np.linspace(self.min.val, self.max.val, self.num.val)
    
    def zig_zag_sweep_array(self):
        mid_arg = int(self.num.val/2)
        ar = self.array
        return np.concatenate([ar[mid_arg:],ar[::-1],ar[0:mid_arg]])
    def zag_zig_sweep_array(self):
        return self.zig_zag_sweep_array()[::-1]
    def up_down_sweep_array(self):
        ar = self.array
        return np.concatenate([ar,ar[::-1]])
    def down_up_sweep_array(self):
        return self.up_down_sweep_array()[::-1]
    def down_sweep_array(self):
        return self.array[::-1]
    def up_sweep_array(self):
        return self.array
        
    @property
    def sweep_array(self):
        if hasattr(self, 'sweep_type'):
            return self.sweep_type_map[self.sweep_type.val]()
        else:
            return self.array

    def add_listener(self, func, argtype=(), **kwargs):
        self.min.add_listener(func, argtype, **kwargs)
        self.max.add_listener(func, argtype, **kwargs)
        self.num.add_listener(func, argtype, **kwargs)
        
    def New_UI(self):
        ui_widget =  QtWidgets.QWidget()
        formLayout = QtWidgets.QFormLayout()
        ui_widget.setLayout(formLayout)
        for lqname,lq in self.lq_dict.items():
            formLayout.addRow(lqname, lq.new_default_widget())
        return ui_widget

    
class LQ3Vector(object):
    
    def __init__(self, x_lq, y_lq, z_lq):
        self.x_lq = x_lq
        self.y_lq = y_lq
        self.z_lq = z_lq
    
    @property
    def values(self):
        return np.array([self.x_lq.val, self.y_lq.val, self.z_lq.val])
    
    @property
    def length(self):
        vec = self.values
        return np.sqrt(np.dot(vec,vec))
    
    @property
    def normed_values(self):
        return self.values/self.length
    
    def dot(self, _lq_vector):
        '''
        returns the scalar product with _lq_vector
        '''
        return np.dot(_lq_vector.values,self.values)
    
    def project_on(self, _lq_vector):
        return np.dot(_lq_vector.normed_values, self.values)
    
    def angle_to(self, _lq_vector):
        return np.arccos(np.dot(_lq_vector.normed_values,self.normed_values))
    
    def add_listener(self, func, argtype=(), **kwargs):
        self.x_lq.add_listener(func, argtype, **kwargs)
        self.y_lq.add_listener(func, argtype, **kwargs)
        self.z_lq.add_listener(func, argtype, **kwargs)        



class LQCollection(object):
    """
    LQCollection is a smart dictionary of LoggedQuantity objects.
    
    attribute access such as lqcoll.x1 will return full LoggedQuantity object
    
    dictionary-style access lqcoll['x1'] allows direct reading and writing of 
    the LQ's value, handling the signals automatically
    
    New LQ's can be created with :meth:`New`
    
    LQRange objects can be created with :meth:`New_Range` and will be stored
    in :attr:ranges
    
    """

    def __init__(self):
        self._logged_quantities = OrderedDict()
        self.ranges = OrderedDict()
        self.vectors = OrderedDict()
        
        self.log = get_logger_from_class(self)
        
    def New(self, name, dtype=float, **kwargs):
        """
        Create a new LoggedQuantity with name and dtype
        """
        
        is_array = kwargs.pop('array', False)
        #self.log.debug("{} is_array? {}".format(name, is_array))
        if is_array:
            lq = ArrayLQ(name=name, dtype=dtype, **kwargs)
        else:
            if dtype == 'file':
                lq = FileLQ(name=name, **kwargs)
            else:
                lq = LoggedQuantity(name=name, dtype=dtype, **kwargs)

        return self.Add(lq)
    
    def Add(self, lq):
        """Add an existing LoggedQuantity to the Collection
        Examples of usefulness: add hardware lq to measurement settings
        """
        name = lq.name
        assert not (name in self._logged_quantities)
        assert not (name in self.__dict__)
        self._logged_quantities[name] = lq
        self.__dict__[name] = lq # allow attribute access
        return lq

    def get_lq(self, key) -> LoggedQuantity:
        return self._logged_quantities[key]
    
    def get_val(self, key):
        return self._logged_quantities[key].val
    
    def as_list(self):
        return self._logged_quantities.values()
    
    def as_dict(self):
        return self._logged_quantities
    
    def as_value_dict(self):
        val_dict = dict()
        for k, lq in self.as_dict().items():
            val_dict[k] = lq.value
        return val_dict
    
#    def items(self):
#        return self._logged_quantities.items()
    
    def keys(self):
        return self._logged_quantities.keys()
    
    def remove(self, name):
        del self._logged_quantities[name]
        del self.__dict__[name]

    def __delitem__(self, key): 
        self.remove(key)
    
    def __getitem__(self, key):
        "Dictionary-like access reads and sets value of LQ's"
        return self._logged_quantities[key].val
    
    
    def __setitem__(self, key, item):
        "Dictionary-like access reads and sets value of LQ's"
        self._logged_quantities[key].update_value(item)

    def __contains__(self, key):
        return self._logged_quantities.__contains__(key)
    """
    def __getattribute__(self,name):
        if name in self.logged_quantities.keys():
            return self.logged_quantities[name]
        else:
            return object.__getattribute__(self, name)
    """
    
    def New_Range(self, name, include_center_span=False, include_sweep_type = False, initials = [0, 1., 0.1], **kwargs):
                        
        mn,mx,d = initials
        min_lq  = self.New( name + "_min" , initial=mn, **kwargs ) 
        max_lq  = self.New( name + "_max" , initial=mx, **kwargs ) 
        step_lq = self.New( name + "_step", initial=d, **kwargs)
        num_lq  = self.New( name + "_num", dtype=int, vmin=1, initial=11)
        
        LQRange_kwargs = {'min_lq':min_lq, 'max_lq':max_lq, 'step_lq':step_lq, 'num_lq':num_lq}
        if include_center_span:
            center_lq = self.New(name + "_center", **kwargs, initial=0.5)
            span_lq = self.New( name + "_span", **kwargs, initial=1.0)
            LQRange_kwargs.update({'center_lq':center_lq,'span_lq':span_lq})
        if include_sweep_type:
            sweep_type_lq  = self.New( name + "_sweep_type", dtype=str, choices=('up','down'), initial='up')
            LQRange_kwargs.update({'sweep_type_lq':sweep_type_lq})
        
        lqrange = LQRange(**LQRange_kwargs)

        self.ranges[name] = lqrange
        return lqrange
    
    
    def New_Vector(self, name, components = 'xyz', initial = [1,0,0], **kwargs):

        assert len(components) == len(initial)
        
        if len(components) == 3:

            lq_x = self.New(name+'_'+components[0], initial = initial[0], **kwargs)
            lq_y = self.New(name+'_'+components[1], initial = initial[1], **kwargs)
            lq_z = self.New(name+'_'+components[2], initial = initial[2], **kwargs)
                
            lq_vector = LQ3Vector(lq_x,lq_y,lq_z)
            self.vectors[name] = lq_vector
            return lq_vector
    
    
    def New_UI(self, include = None, exclude = [], style='form'):
        """create a default Qt Widget that contains 
        widgets for all settings in the LQCollection
        """

        if include is None:
            lqnames = self.as_dict().keys()
        else:
            lqnames = include

        ui_widget =  QtWidgets.QWidget()

        if style == 'form':
            formLayout = QtWidgets.QFormLayout()
            ui_widget.setLayout(formLayout)
            
            
            for lqname in lqnames:
                if lqname in exclude:
                    continue
                lq = self.get_lq(lqname)
                #: :type lq: LoggedQuantity
                widget = lq.new_default_widget()
                # Add to formlayout
                formLayout.addRow(lqname, widget)
                #lq_tree_item = QtWidgets.QTreeWidgetItem(self.tree_item, [lqname, ""])
                #self.tree_item.addChild(lq_tree_item)
                #lq.hardware_tree_widget = widget
                #tree.setItemWidget(lq_tree_item, 1, lq.hardware_tree_widget)
                #self.control_widgets[lqname] = widget  
        
        elif style == 'hbox':
            hboxLayout = QtWidgets.QHBoxLayout()
            ui_widget.setLayout(hboxLayout)
            
            for lqname in lqnames:
                if lqname in exclude:
                    continue
                lq = self.get_lq(lqname)                
                widget = lq.new_default_widget()

                hboxLayout.addWidget(QtWidgets.QLabel(lqname))
                hboxLayout.addWidget(widget)
        
        elif style == 'scroll_form':
            scroll_area = QtWidgets.QScrollArea()
            formLayout = QtWidgets.QFormLayout()
            ui_widget.setLayout(formLayout)
            scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
            scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
            scroll_area.setWidgetResizable(True)
            scroll_area.setWidget(ui_widget)
            
            for lqname in lqnames:
                if lqname in exclude:
                    continue
                lq = self.get_lq(lqname)
                #: :type lq: LoggedQuantity
                widget = lq.new_default_widget()
                # Add to formlayout
                formLayout.addRow(lqname, widget)

            return scroll_area
        
        return ui_widget
    
    def add_widgets_to_subtree(self, tree_item):
        lq_tree_items = []
        for lqname, lq in self.as_dict().items():
            #: :type lq: LoggedQuantity
            if isinstance(lq, ArrayLQ):
                lineedit = QtWidgets.QLineEdit()
                button = QtWidgets.QPushButton('...')
                widget = QtWidgets.QWidget()
                layout = QtWidgets.QHBoxLayout()
                widget.setLayout(layout)
                layout.addWidget(lineedit)
                layout.addWidget(button)
                layout.setSpacing(0)
                layout.setContentsMargins(0,0,0,0)
                
                lq.connect_to_widget(lineedit)
                button.clicked.connect(lq.array_tableView.show)
                button.clicked.connect(lq.array_tableView.raise_)
            elif isinstance(lq,FileLQ):
                lineedit = QtWidgets.QLineEdit()
                button = QtWidgets.QPushButton('...')
                widget = QtWidgets.QWidget()
                layout = QtWidgets.QHBoxLayout()
                widget.setLayout(layout)
                layout.addWidget(lineedit)
                layout.addWidget(button)
                layout.setSpacing(0)
                layout.setContentsMargins(0,0,0,0)
                
                lq.connect_to_browse_widgets(lineedit,button)
            else:
                if lq.choices is not None:
                    widget = QtWidgets.QComboBox()
                elif lq.dtype in [int, float]:
                    if lq.si:
                        widget = pg.SpinBox()
                    else:
                        widget = QtWidgets.QDoubleSpinBox()
                elif lq.dtype in [bool]:
                    widget = QtWidgets.QCheckBox()  
                elif lq.dtype in [str]:
                    widget = QtWidgets.QLineEdit()
                lq.connect_to_widget(widget)
    
            lq_tree_item = QtWidgets.QTreeWidgetItem(tree_item, [lqname, ""])
            lq_tree_items.append(lq_tree_item)
            tree_item.addChild(lq_tree_item)
            lq.tree_widget = widget
            tree_item.treeWidget().setItemWidget(lq_tree_item, 1, lq.tree_widget)
            #self.control_widgets[lqname] = widget
        return lq_tree_items

    
    def disconnect_all_from_hardware(self):
        for lq in self.as_list():
            lq.disconnect_from_hardware()
            


