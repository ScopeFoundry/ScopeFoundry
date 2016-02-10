from PySide import  QtCore, QtGui
import pyqtgraph
import numpy as np
from collections import OrderedDict

class LoggedQuantity(QtCore.QObject):

    updated_value = QtCore.Signal((float,),(int,),(bool,), (), (str,),) # signal sent when value has been updated
    updated_text_value = QtCore.Signal(str)
    updated_choice_index_value = QtCore.Signal(int) # emits the index of the value in self.choices
    
    updated_min_max = QtCore.Signal((float,float),(int,int), (),) # signal sent when min max range updated
    updated_readonly = QtCore.Signal((bool,), (),)
    
    def __init__(self, name, dtype=float, 
                 hardware_read_func=None, hardware_set_func=None, 
                 initial=0, fmt="%g", si=True,
                 ro = False,
                 unit = None,
                 vmin=-1e12, vmax=+1e12, choices=None):
        QtCore.QObject.__init__(self)
        
        self.name = name
        self.dtype = dtype
        self.val = dtype(initial)
        self.hardware_read_func = hardware_read_func
        self.hardware_set_func = hardware_set_func
        self.fmt = fmt # string formatting string. This is ignored if dtype==str
        self.si   = si # will use pyqtgraph SI Spinbox if True
        self.unit = unit
        self.vmin = vmin
        self.vmax = vmax
        self.choices = choices # must be tuple [ ('name', val) ... ]
        self.ro = ro # Read-Only?
        
        if self.dtype == int:
            self.spinbox_decimals = 0
        else:
            self.spinbox_decimals = 2
        self.reread_from_hardware_after_write = False
        
        self.oldval = None
        
        self._in_reread_loop = False # flag to prevent reread from hardware loops
        
        self.widget_list = []
        
    def read_from_hardware(self, send_signal=True):
        if self.hardware_read_func:
            self.oldval = self.val
            val = self.hardware_read_func()
            #print "read_from_hardware", self.name, val
            self.val = self.dtype(val)
            if send_signal:
                self.send_display_updates()
        return self.val

    @QtCore.Slot(str)
    @QtCore.Slot(float)
    @QtCore.Slot(int)
    @QtCore.Slot(bool)
    @QtCore.Slot()
    def update_value(self, new_val=None, update_hardware=True, send_signal=True, reread_hardware=None):
        #print "LQ update_value", self.name, self.val, "-->",  new_val
        if new_val == None:
            new_val = self.sender().text()

        if (self.val == new_val):
            self._in_reread_loop = False #once value has settled in the event loop, re-enable reading from hardware
            return
        
        if reread_hardware is None:
            reread_hardware = self.reread_from_hardware_after_write
        
        self.oldval = self.val
        #print "called update_value", self.name, new_val, reread_hardware
        self.val = self.dtype(new_val)
        if update_hardware and self.hardware_set_func and not self._in_reread_loop:
            self.hardware_set_func(self.val)
            if reread_hardware:
                # re-reading from hardware can set off a loop of setting 
                # and re-reading from hardware if hardware readout is not
                # exactly the requested value. temporarily disable rereading
                # from hardware until value in LoggedQuantity has settled
                self._in_reread_loop = True 
                self.read_from_hardware(send_signal=False) # changed send_signal to false (ESB 2015-08-05)
        if send_signal:
            self.send_display_updates()
            
    def send_display_updates(self, force=False):
        #print "send_display_updates: {} force={}".format(self.name, force)
        if (self.oldval != self.val) or (force):
            
            #print "send display updates", self.name, self.val, self.oldval
            if self.dtype == str:
                self.updated_value[str].emit(self.val)
                self.updated_text_value.emit(self.val)
            else:
                self.updated_value[str].emit( self.fmt % self.val )
                self.updated_text_value.emit( self.fmt % self.val )
                
            self.updated_value[float].emit(self.val)
            if self.dtype != float:
                self.updated_value[int].emit(self.val)
            self.updated_value[bool].emit(self.val)
            self.updated_value[()].emit()
            
            if self.choices is not None:
                choice_vals = [c[1] for c in self.choices]
                if self.val in choice_vals:
                    self.updated_choice_index_value.emit(choice_vals.index(self.val) )
            self.oldval = self.val
        else:
            pass
            #print "\t no updates sent", (self.oldval != self.val) , (force), self.oldval, self.val
            
    def update_choice_index_value(self, new_choice_index, **kwargs):
        self.update_value(self.choices[new_choice_index][1], **kwargs)
        

    def connect_bidir_to_widget(self, widget):
        print type(widget)
        if type(widget) == QtGui.QDoubleSpinBox:
            #self.updated_value[float].connect(widget.setValue )
            #widget.valueChanged[float].connect(self.update_value)
            widget.setKeyboardTracking(False)
            if self.vmin is not None:
                widget.setMinimum(self.vmin)
            if self.vmax is not None:
                widget.setMaximum(self.vmax)
            if self.unit is not None:
                widget.setSuffix(" "+self.unit)
            if self.dtype == int:
                widget.setDecimals(0)
            self.change_readonly(self.ro)
            widget.setDecimals(self.spinbox_decimals)
            widget.setValue(self.val)
            #events
            self.updated_value[float].connect(widget.setValue)
            #if not self.ro:
            widget.valueChanged[float].connect(self.update_value)
                
        elif type(widget) == QtGui.QCheckBox:
            print self.name
            #self.updated_value[bool].connect(widget.checkStateSet)
            #widget.stateChanged[int].connect(self.update_value)
            # Ed's version
            print "connecting checkbox widget"
            self.updated_value[bool].connect(widget.setChecked)
            widget.toggled[bool].connect(self.update_value)
            if self.ro:
                #widget.setReadOnly(True)
                widget.setEnabled(False)
        elif type(widget) == QtGui.QLineEdit:
            self.updated_text_value[str].connect(widget.setText)
            if self.ro:
                widget.setReadOnly(True)  # FIXME     
            widget.textChanged[str].connect(self.updated_text_value)
        elif type(widget) == QtGui.QComboBox:
            # need to have a choice list to connect to a QComboBox
            assert self.choices is not None 
            widget.clear() # removes all old choices
            for choice_name, choice_value in self.choices:
                widget.addItem(choice_name, choice_value)
            self.updated_choice_index_value[int].connect(widget.setCurrentIndex)
            widget.currentIndexChanged.connect(self.update_choice_index_value)
            
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
            widget.setOpts(
                        suffix=suffix,
                        siPrefix=True,
                        dec=True,
                        step=step,
                        minStep=minStep,
                        bounds=[self.vmin, self.vmax],
                        int=integer)            
            if self.ro:
                widget.setEnabled(False)
                widget.setButtonSymbols(QtGui.QAbstractSpinBox.NoButtons)
                widget.setReadOnly(True)
            widget.setDecimals(self.spinbox_decimals)
            self.updated_value[float].connect(widget.setValue)
            if not self.ro:
                #widget.valueChanged[float].connect(self.update_value)
                widget.valueChanged.connect(self.update_value)
        elif type(widget) == QtGui.QLabel:
            self.updated_text_value.connect(widget.setText)
        else:
            raise ValueError("Unknown widget type")
        
        self.send_display_updates(force=True)
        #self.widget = widget
        self.widget_list.append(widget)
    
    def change_choice_list(self, choices):
        #widget = self.widget
        self.choices = choices
        
        for widget in self.widget_list:
            if type(widget) == QtGui.QComboBox:
                # need to have a choice list to connect to a QComboBox
                assert self.choices is not None 
                widget.clear() # removes all old choices
                for choice_name, choice_value in self.choices:
                    widget.addItem(choice_name, choice_value)
            else:
                raise RuntimeError("Invalid widget type.")
    
    def change_min_max(self, vmin=-1e12, vmax=+1e12):
        self.vmin = vmin
        self.vmax = vmax
        for widget in self.widget_list: # may not work for certain widget types
            widget.setRange(vmin, vmax)
        self.updated_min_max.emit(vmin,vmax)
        
    def change_readonly(self, ro=True):
        self.ro = ro
        for widget in self.widget_list:
            if type(widget) in [QtGui.QDoubleSpinBox, pyqtgraph.widgets.SpinBox.SpinBox]:
                widget.setReadOnly(self.ro)    
            #elif
        self.updated_readonly.emit(self.ro)
        
class LQRange(QtCore.QObject):
    """
    LQRange is a collection of logged quantities that describe a
    numpy.linspace array inputs
    Four LQ's are defined, min, max, num, step
    and are connected by signals/slots that keep the quantities
    in sync.
    LQRange.array is the linspace array and is kept upto date
    with changes to the 4 LQ's
    """
    updated_range = QtCore.Signal((),)# (float,),(int,),(bool,), (), (str,),) # signal sent when value has been updated
    
    def __init__(self, min_lq,max_lq,step_lq, num_lq):
        QtCore.QObject.__init__(self)

        self.min = min_lq
        self.max = max_lq
        self.num = num_lq
        self.step = step_lq
        
        assert self.num.dtype == int
                
        self.array = np.linspace(self.min.val, self.max.val, self.num.val)
        step = self.array[1]-self.array[0]
        self.step.update_value(step)
        
        self.num.updated_value[int].connect(self.recalc_with_new_num)
        self.min.updated_value.connect(self.recalc_with_new_min_max)
        self.max.updated_value.connect(self.recalc_with_new_min_max)
        self.step.updated_value.connect(self.recalc_with_new_step)        

    def recalc_with_new_num(self, new_num):
        print "recalc_with_new_num", new_num
        self.array = np.linspace(self.min.val, self.max.val, int(new_num))
        if len(self.array) > 1:
            new_step = self.array[1]-self.array[0]
            print "    new_step inside new_num", new_step
            self.step.update_value(new_step)#, send_signal=True, update_hardware=False)
            self.step.send_display_updates(force=True)
        self.updated_range.emit()
        
    def recalc_with_new_min_max(self, x):
        self.array = np.linspace(self.min.val, self.max.val, self.num.val)
        step = self.array[1]-self.array[0]
        self.step.update_value(step)#, send_signal=True, update_hardware=False)        
        self.updated_range.emit()
        
    def recalc_with_new_step(self,new_step):
        print "-->recalc_with_new_step"
        if len(self.array) > 1:
            old_step = self.array[1]-self.array[0]    
        else:
            old_step = np.nan
        diff = np.abs(old_step - new_step)
        print "step diff", diff
        if diff < 10**(-self.step.spinbox_decimals):
            print "steps close enough, no more recalc"
            return
        else:
            new_num = int((((self.max.val - self.min.val)/new_step)+1))
            self.array = np.linspace(self.min.val, self.max.val, new_num)
            new_step1 = self.array[1]-self.array[0]
            print "recalc_with_new_step", new_step, new_num, new_step1
            #self.step.val = new_step1
            #self.num.val = new_num
            #self.step.update_value(new_step1, send_signal=False)
            #if np.abs(self.step.val - new_step1)/self.step.val > 1e-2:
            self.step.val = new_step1
            self.num.update_value(new_num)
            #self.num.send_display_updates(force=True)
            #self.step.update_value(new_step1)

            #print "sending step display Updates"
            #self.step.send_display_updates(force=True)
            self.updated_range.emit()

class LQCollection(object):

    def __init__(self):
        self._logged_quantities = OrderedDict()
        
    def New(self, name, **kwargs):
        lq = LoggedQuantity(name=name, **kwargs)
        self._logged_quantities[name] = lq
        self.__dict__[name] = lq
        return lq
    
    """def __getattr__(self, name):
        return self.logged_quantities[name]

    def __getitem__(self, key):
        return self.logged_quantities[key]

    def __getattribute__(self,name):
        if name in self.logged_quantities.keys():
            return self.logged_quantities[name]
        else:
            return object.__getattribute__(self, name)
    """
    

def print_signals_and_slots(obj):
    for i in xrange(obj.metaObject().methodCount()):
        m = obj.metaObject().method(i)
        if m.methodType() == QtCore.QMetaMethod.MethodType.Signal:
            print "SIGNAL: sig=", m.signature(), "hooked to nslots=",obj.receivers(QtCore.SIGNAL(m.signature()))
        elif m.methodType() == QtCore.QMetaMethod.MethodType.Slot:
            print "SLOT: sig=", m.signature()