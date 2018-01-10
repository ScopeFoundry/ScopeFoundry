from __future__ import absolute_import, print_function
from qtpy import QtCore, QtWidgets, uic
from collections import OrderedDict
import os
import logging
import pyqtgraph as pg
import threading

class OrderedAttrDict(object):

    def __init__(self):
        self._odict = OrderedDict()
        
    def add(self, name, obj):
        self._odict[name] = obj
        self.__dict__[name] = obj
        return obj
    
    
    def keys(self):
        return self._odict.keys()
    def values(self):
        return self._odict.values()
    def items(self):
        return self._odict.items()
    
    def __len__(self):
        return len(self._odict)
    
    def __getitem__(self, key):
        return self._odict[key]
    
    def __contains__(self, k):
        return self._odict.__contains__(k)

def sibling_path(a, b):
    """
    Returns the path of a filename *b* in the same folder as *a*
    (i.e. dirname(a)/b )
    
    ==============  ==============================
    **Arguments:**
    *a*             directory name of pathname *a*
    b               path suffix
    ==============  ==============================

    :returns: combined path of above arguments.
    """
    return os.path.join(os.path.dirname(a), b)


def load_qt_ui_file(ui_filename):
    """
    Loads a QT user interface file (files ending in .ui). 
    This function is typically called from :class:`Measurement` level modules.
    """
    ### PySide version
        #ui_loader = QtUiTools.QUiLoader()
        #ui_file = QtCore.QFile(ui_filename)
        #ui_file.open(QtCore.QFile.ReadOnly)
        #ui = ui_loader.load(ui_file)
        #ui_file.close()
    ### qtpy / PyQt version
    ui = uic.loadUi(ui_filename)
    return ui

def confirm_on_close(widget, 
                     title="Close ScopeFoundry?",
                     message="Do you wish to shut down ScopeFoundry?", 
                     func_on_close=None):
    """
    Calls the :class:`ConfirmCloseEventEater` class which asks for user
    confirmation in a pop-up dialog upon closing the ScopeFoundry app.
    """
    widget.closeEventEater = ConfirmCloseEventEater(title, message, func_on_close)
    widget.installEventFilter(widget.closeEventEater)
    
class ConfirmCloseEventEater(QtCore.QObject):
    
    """
    Tells the Qt to confirm the closing of the app by the user with a pop-up
    confirmation dialog.
    """
    
    def __init__(self, title="Close ScopeFoundry?", 
                 message="Do you wish to shut down ScopeFoundry?", 
                 func_on_close=None):
        QtCore.QObject.__init__(self)
        self.title = title
        self.message = message
        self.func_on_close = func_on_close
    
    def eventFilter(self, obj, event):
        """
        Listens for QtCore.QEvent.Close signal and asks the user whether to
        close the app in a pop-up dialog."""
        if event.type() == QtCore.QEvent.Close:
            # eat close event
            logging.debug("close")
            reply = QtWidgets.QMessageBox.question(None, 
                                               self.title, 
                                               self.message,
                                               QtWidgets.QMessageBox.Yes, 
                                               QtWidgets.QMessageBox.No)
            if reply == QtWidgets.QMessageBox.Yes:
                logging.debug("closing")
                if self.func_on_close:
                    self.func_on_close()
                QtWidgets.QApplication.quit()
                event.accept()
            else:
                event.ignore()
            return True
        else:
            # standard event processing            
            return QtCore.QObject.eventFilter(self,obj, event)
    
def ignore_on_close(widget):
    """
    Calls the :class:`IgnoreCloseEventEater` class which intercepts the
    QtCore.QEvent.Close signal and prevents the deletion of subwindows and their
    associated objects.
    """
    widget.ignoreCloseEventEater = IgnoreCloseEventEater()
    widget.installEventFilter(widget.ignoreCloseEventEater)
    
class IgnoreCloseEventEater(QtCore.QObject):
    """
    This class is utilized to prevent the closing of important subwindows 
    and prevent the deletion of related python objects. Tells the Qt event 
    manager to ignore calls to close the subwindow when user hits [x] on 
    the subwindow.
    """

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Close:
            # eat close event
            event.ignore()
            return True
        else:
            # standard event processing            
            return QtCore.QObject.eventFilter(self, obj, event)            
        
def replace_widget_in_layout(old_widget, new_widget, retain_font=True, 
                             retain_sizePolicy=True, retain_size=True):
    """
    Replace a widget with a new widget instance in an existing layout.
    
    returns new_widget
    
    Useful for replacing placeholder widgets created with QtCreator 
    with custom widgets
    Note: currently works for widgets in  QGridLayouts only
    
    inspiration from:
    -- http://stackoverflow.com/questions/4625102/how-to-replace-a-widget-with-another-using-qt
    -- http://stackoverflow.com/questions/24189202/how-to-get-the-row-column-location-of-a-widget-in-a-qgridlayout
    """
    
    # find position of old_widget
    layout = old_widget.parentWidget().layout()
    index = layout.indexOf(old_widget)
    row, column, rowSpan, colSpan = layout.getItemPosition(index)
    

    # transfer retained attributes of old_widget to  new_widget
    if retain_font:
        new_widget.setFont(old_widget.font())
    if retain_sizePolicy:
        new_widget.setSizePolicy(old_widget.sizePolicy())
    if retain_size:
        new_widget.setMinimumSize(old_widget.minimumSize())
        new_widget.setMaximumSize(old_widget.maximumSize())
    
    # remove old widget
    layout.removeWidget(old_widget)
    old_widget.close()


    # add new widget
    layout.addWidget(new_widget, row, column, rowSpan, colSpan)
    layout.update()
    
    
    
    return new_widget

def replace_spinbox_in_layout(old_widget, **kwargs):
    new_spinbox = pg.SpinBox()
    return replace_widget_in_layout(old_widget, new_widget=new_spinbox, **kwargs)

def print_all_connected(qobject, signal=None):
    if signal is None:
        signals = qobject.signals()
    else:
        signals = [signal]
    for signal in qobject.signals():
        for slot in qobject.connectedSlots():
            print(slot)

def print_signals_and_slots(obj):
    # http://visitusers.org/index.php?title=PySide_Recipes
    for i in range(obj.metaObject().methodCount()):
        m = obj.metaObject().method(i)
        if m.methodType() == QtCore.QMetaMethod.MethodType.Signal:
            print("SIGNAL: sig=", m.signature(), "hooked to nslots=",obj.receivers(QtCore.SIGNAL(m.signature())))
        elif m.methodType() == QtCore.QMetaMethod.MethodType.Slot:
            print("SLOT: sig=", m.signature())
            
def get_logger_from_class(obj):
    """ returns a named Logger from the logging package using the
    full name of the class of the object (obj) as the log name
    """ 
    #return logging.getLogger(obj.__module__ + "." + obj.__class__.__name__)
    return logging.getLogger(obj.__class__.__name__)

def str2bool(v):
    return v.lower() in ("yes", "true", "t", "1")


class QLock(QtCore.QMutex):
    def acquire(self):
        self.lock()
    def release(self):
        self.unlock()
    def __enter__(self):
        self.acquire()
        return self
    def __exit__(self, *args):
        self.release()


# https://stackoverflow.com/questions/5327614/logging-lock-acquire-and-release-calls-in-multi-threaded-application
class LogLock(object):
    def __init__(self, name):
        self.name = str(name)
        self.lock = threading.Lock()
        self.log = logging.getLogger('LogLock')


    def acquire(self, blocking=True):
        self.log.debug("{0:x} Trying to acquire {1} lock".format(
            id(self), self.name))
        ret = self.lock.acquire(blocking)
        if ret == True:
            self.log.debug("{0:x} Acquired {1} lock".format(
                id(self), self.name))
        else:
            self.log.debug("{0:x} Non-blocking aquire of {1} lock failed".format(
                id(self), self.name))
        return ret

    def release(self):
        self.log.debug("{0:x} Releasing {1} lock".format(id(self), self.name))
        self.lock.release()

    def __enter__(self):
        self.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False    # Do not swallow exceptions
