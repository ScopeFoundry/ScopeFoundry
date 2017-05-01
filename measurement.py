# -*- coding: utf-8 -*-
"""
Created on Tue Apr  1 09:25:48 2014
@author: esbarnard
"""
from __future__ import absolute_import, print_function

from qtpy import QtCore, QtWidgets
import threading
import time
from .logged_quantity import LQCollection
from .helper_funcs import load_qt_ui_file
from collections import OrderedDict
import pyqtgraph as pg
from ScopeFoundry.helper_funcs import get_logger_from_class

class MeasurementQThread(QtCore.QThread):
    def __init__(self, measurement, parent=None):
        super(MeasurementQThread, self).__init__(parent)
        self.measurement = measurement
    
    def run(self):
        self.measurement._thread_run()



class Measurement(QtCore.QObject):
    """
    Base class for ScopeFoundry Hardware objects
    
    to subclass, implement :meth:`setup`, :meth:`run` 
    
    for measurements with graphical interfaces, 
    subclass and additionally implement :meth:`setup_figure`, :meth:`update_display` 
    """
    
    measurement_sucessfully_completed = QtCore.Signal(())
    """signal sent when full measurement is complete"""
    measurement_interrupted = QtCore.Signal(()) 
    """signal sent when  measurement is complete due to an interruption"""

    #measurement_state_changed = QtCore.Signal(bool) # signal sent when measurement started or stopped
    
    def __init__(self, app):
        """
        :type app: BaseMicroscopeApp
                
        """
        
        QtCore.QObject.__init__(self)
        self.log = get_logger_from_class(self)
        
        if not hasattr(self, 'name'):
            self.name = self.__class__.__name__


        self.app = app
        
        self.display_update_period = 0.1 # seconds
        self.display_update_timer = QtCore.QTimer(self)
        self.display_update_timer.timeout.connect(self._on_display_update_timer)
        self.acq_thread = None
        
        self.interrupt_measurement_called = False
        
        #self.logged_quantities = OrderedDict()
        self.settings = LQCollection()
        self.operations = OrderedDict()
        
        
        self.activation = self.settings.New('activation', dtype=bool, ro=False) # does the user want to the thread to be running
        self.running    = self.settings.New('running', dtype=bool, ro=True) # is the thread actually running?
        self.progress   = self.settings.New('progress', dtype=float, unit="%", si=False, ro=True)
        self.settings.New('profile', dtype=bool, initial=False) # Run a profile on the run to find performance problems

        self.activation.updated_value[bool].connect(self.start_stop)

        self.add_operation("start", self.start)
        self.add_operation("interrupt", self.interrupt)
        #self.add_operation('terminate', self.terminate)
        #self.add_operation("setup", self.setup)
        #self.add_operation("setup_figure", self.setup_figure)
        self.add_operation("update_display", self.update_display)
        #self.add_operation('show_ui', self.show_ui)
        
        if hasattr(self, 'ui_filename'):
            self.load_ui()
        
        self.setup()
        
        
    def setup(self):
        """Override this to set up logged quantities and gui connections
        Runs during __init__, before the hardware connection is established
        Should generate desired LoggedQuantities"""
        pass
        #raise NotImplementedError()
        
    def setup_figure(self):
        """
        Overide setup_figure to build graphical interfaces. 
        This function is run on ScopeFoundry startup.
        """
        self.log.info("Empty setup_figure called")
        pass
    
    @QtCore.Slot()
    def start(self):
        """
        Starts the measurement
        
        calls *pre_run*
        creates acquisition thread 
        runs thread
        """ 
        self.log.info("measurement {} start".format(self.name))
        self.interrupt_measurement_called = False
        if (self.acq_thread is not None) and self.is_measuring():
            raise RuntimeError("Cannot start a new measurement while still measuring")
        #self.acq_thread = threading.Thread(target=self._thread_run)
        self.acq_thread = MeasurementQThread(self)
        self.acq_thread.finished.connect(self.post_run)
        #self.measurement_state_changed.emit(True)
        self.running.update_value(True)
        self.pre_run()
        self.acq_thread.start()
        self.t_start = time.time()
        self.display_update_timer.start(self.display_update_period*1000)

    def pre_run(self):
        """Override this method to enable main-thread initialization prior to measurement thread start"""
        pass
    
   
    def run(self):
        """
        *run* method runs in an separate thread and is used for data acquisition
        
        No GUI updates should occur within the *run* function, any Qt related GUI work 
        should occur in :meth:`update_display` 
        """
        
        if hasattr(self, '_run'):
            self.log.warning("warning _run is deprecated, use run")
            self._run()
        else:
            raise NotImplementedError("Measurement {}.run() not defined".format(self.name))
    
    
    def post_run(self):
        """Override this method to enable main-thread finalization after to measurement thread completes"""
        pass
        
    def _thread_run(self):
        """
        This function governs the behavior of the measurement thread. 
        """
        self.set_progress(50.) # set progress bars to default run position at 50%
        try:
            if self.settings['profile']:
                import cProfile
                profile = cProfile.Profile()
                profile.enable()
            self.run()
        #except Exception as err:
        #    self.interrupt_measurement_called = True
        #    raise err
        finally:
            self.running.update_value(False)
            self.activation.update_value(False)
            self.set_progress(0.) # set progress bars back to zero
            #self.measurement_state_changed.emit(False)
            if self.interrupt_measurement_called:
                self.measurement_interrupted.emit()
                self.interrupt_measurement_called = False
            else:
                self.measurement_sucessfully_completed.emit()
            if self.settings['profile']:
                profile.disable()
                profile.print_stats(sort='time')   
    
            


    @property
    def gui(self):
        self.log.warning("Measurement.gui is deprecated, use Measurement.app " + repr(DeprecationWarning))
        return self.app
    
    def set_progress(self, pct):
        """
        This function updates the logged quantity progress which is used for the display of progress bars in the UI.
         
        ==============  ==============================================================================================
        **Arguments:** 
        pct             The percentage of progress given by a measurement module                                      
        ==============  ==============================================================================================
        """
        self.progress.update_value(pct)
                
    @QtCore.Slot()
    def interrupt(self):
        """
        Kindly ask the measurement to stop.
        
        This raises the :attr:`interrupt_measurement_called` flag
        To actually stop, the threaded :meth:`run` method must check
        for this flag and exit
        """
        self.log.info("measurement {} interrupt".format(self.name))
        self.interrupt_measurement_called = True
        self.activation.update_value(False)
        #Make sure display is up to date        
        #self._on_display_update_timer()

    def terminate(self):
        """
        Terminate MeasurementQThread.
        """
        self.acq_thread.terminate()
        
    def start_stop(self, start):
        """
        Use boolean *start* to either start (True) or
        interrupt (False) measurement. Test.
        """
        self.log.info("{} start_stop {}".format(self.name, start))
        if start:
            self.start()
        else:
            self.interrupt()

        
    def is_measuring(self):
        """
        Returns whether the acquisition thread is running
        """
        
        if self.acq_thread is None:
            self.running.update_value(False)
            self.activation.update_value(False)
            self.settings['progress'] = 0.0
            return False
        else:
            #resp =  self.acq_thread.is_alive()
            resp = self.acq_thread.isRunning()
            self.running.update_value(resp)            
            return resp
    
    def update_display(self):
        "Override this function to provide figure updates when the display timer runs"
        pass
    
    
    @QtCore.Slot()
    def _on_display_update_timer(self):
        try:
            self.update_display()
        except Exception as err:
            pass
            self.log.error("{} Failed to update figure: {}".format(self.name, err))          
        finally:
            if not self.is_measuring():
                self.display_update_timer.stop()

    def add_logged_quantity(self, name, **kwargs):
        """
        Create a new :class:`LoggedQuantity` and adds it to the measurement's
        :attr:`settings` (:class:`LQCollection`)
        """
        lq = self.settings.New(name=name, **kwargs)
        return lq
    
    def add_operation(self, name, op_func):
        """
        Used to create a logged quantity connection between a button in the Measurement tree
        and a function.

        ==============  =================
        **type name:**  **type op_func:**
        str             QtCore.Slot
        ==============  =================
        """
        self.operations[name] = op_func   
    
    def load_ui(self, ui_fname=None):
        """
        Loads and shows user interface.

        ==============  ===============================================================
        **Arguments:** 
        ui_fname        filename of user interface file (usually made with Qt Designer)                                      
        ==============  ===============================================================
        """

        # TODO destroy and rebuild UI if it already exists
        if ui_fname is not None:
            self.ui_filename = ui_fname
        # Load Qt UI from .ui file
        self.ui = load_qt_ui_file(self.ui_filename)
        self.show_ui()
        
    def show_ui(self):
        """
        Shows the graphical user interface of this measurement. :attr:`ui`
        """
        if self.app.mdi and self.ui.parent():
            self.ui.parent().raise_()
            return
        self.ui.show()
        self.ui.activateWindow()
        self.ui.raise_() #just to be sure it's on top
        if self.app.mdi and self.ui.parent():
            self.ui.parent().raise_()
    
    def new_control_widgets(self):
        
        self.controls_groupBox = QtWidgets.QGroupBox(self.name)
        self.controls_formLayout = QtWidgets.QFormLayout()
        self.controls_groupBox.setLayout(self.controls_formLayout)
        
                
        self.control_widgets = OrderedDict()
        for lqname, lq in self.settings.as_dict().items():
            #: :type lq: LoggedQuantity
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
            lq.connect_bidir_to_widget(widget)

            # Add to formlayout
            self.controls_formLayout.addRow(lqname, widget)
            self.control_widgets[lqname] = widget
            
            
        self.op_buttons = OrderedDict()
        for op_name, op_func in self.operations.items(): 
            op_button = QtWidgets.QPushButton(op_name)
            op_button.clicked.connect(op_func)
            self.controls_formLayout.addRow(op_name, op_button)
            
        return self.controls_groupBox
            
            
    def add_widgets_to_tree(self, tree):
        """
        Adds Measurement items and their controls to Measurements tree in the user interface.
        """
        #if tree is None:
        #    tree = self.app.ui.measurements_treeWidget
        tree.setColumnCount(2)
        tree.setHeaderLabels(["Measurements", "Value"])

        self.tree_item = QtWidgets.QTreeWidgetItem(tree, [self.name, ""])
        tree.insertTopLevelItem(0, self.tree_item)
        #self.tree_item.setFirstColumnSpanned(True)
        self.tree_progressBar = QtWidgets.QProgressBar()
        tree.setItemWidget(self.tree_item, 1, self.tree_progressBar)
        self.progress.updated_value.connect(self.tree_progressBar.setValue)

        # Add logged quantities to tree
        self.settings.add_widgets_to_subtree(self.tree_item)
                
        # Add operation buttons to tree
        self.op_buttons = OrderedDict()
        for op_name, op_func in self.operations.items(): 
            op_button = QtWidgets.QPushButton(op_name)
            op_button.clicked.connect(op_func)
            self.op_buttons[op_name] = op_button
            #self.controls_formLayout.addRow(op_name, op_button)
            op_tree_item = QtWidgets.QTreeWidgetItem(self.tree_item, [op_name, ""])
            tree.setItemWidget(op_tree_item, 1, op_button)
