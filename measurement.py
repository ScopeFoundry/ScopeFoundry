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
import traceback
import sys

class MeasurementQThread(QtCore.QThread):
    def __init__(self, measurement, parent=None):
        super(MeasurementQThread, self).__init__(parent)
        self.measurement = measurement
    
    def run(self):
        self.measurement._thread_run()



class Measurement(QtCore.QObject):
    """
    Base class for ScopeFoundry Measurement objects
    
    to subclass, implement :meth:`setup`, :meth:`run` 
    
    for measurements with graphical interfaces, 
    subclass and additionally implement :meth:`setup_figure`, :meth:`update_display` 
    
    
    Run States:
    
    stop_first -> run_starting -> run_pre_run --> run_thread_starting --> run_thread_run -->
    
    run_thread_end --> run_post_run --> stop_success | stop_interrupted | stop_failure
    
    
    
    """
    
    measurement_sucessfully_completed = QtCore.Signal(())
    """signal sent when full measurement is complete"""
    measurement_interrupted = QtCore.Signal(()) 
    """signal sent when  measurement is complete due to an interruption"""

    #measurement_state_changed = QtCore.Signal(bool) # signal sent when measurement started or stopped
    
    def __init__(self, app, name=None):
        """
        :type app: BaseMicroscopeApp
                
        """
        
        QtCore.QObject.__init__(self)
        self.log = get_logger_from_class(self)
        
        if not hasattr(self, 'name'):
            self.name = self.__class__.__name__

        if name is not None:
            self.name = name

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
        #self.running    = self.settings.New('running', dtype=bool, ro=True) # is the thread actually running?
        self.run_state = self.settings.New('run_state', dtype=str, initial='stop_first')
        self.progress   = self.settings.New('progress', dtype=float, unit="%", si=False, ro=True)
        self.settings.New('profile', dtype=bool, initial=False) # Run a profile on the run to find performance problems

        self.activation.updated_value[bool].connect(self.start_stop)

        self.add_operation("start", self.start)
        self.add_operation("interrupt", self.interrupt)
        #self.add_operation('terminate', self.terminate)
        #self.add_operation("setup", self.setup)
        #self.add_operation("setup_figure", self.setup_figure)
        self.add_operation("update_display", self.update_display)
        self.add_operation('show_ui', self.show_ui)
        
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
        Override setup_figure to build graphical interfaces. 
        This function is run on ScopeFoundry startup.
        """
        self.log.info("Empty setup_figure called")
        pass
    
    def start(self):
        """
        Starts the measurement
        
        calls *pre_run*
        creates acquisition thread 
        runs thread
        starts display timer which calls update_display periodically
        calls post run when thread is finished
        """ 
        #self.start_stop(True)
        self.activation.update_value(True)

        
    def _start(self):
        """
        INTERNAL DO NOT CALL DIRECTLY
        
        Starts the measurement
        
        calls *pre_run*
        creates acquisition thread 
        runs thread
        starts display timer which calls update_display periodically
        connects a signal/slot that calls post run when thread is finished
        """
        self.interrupt_measurement_called = False        
        self.run_state.update_value('run_starting')
        self.log.info("measurement {} start called from thread: {}".format(self.name, repr(threading.get_ident())))
        if self.is_thread_alive():
            raise RuntimeError("Cannot start a new measurement while still measuring {} {}".format(self.acq_thread, self.is_measuring()))
        # remove previous qthread with delete later
        #if self.acq_thread is not None:
        #    self.acq_thread.deleteLater()
        self.acq_thread = MeasurementQThread(self)
        self.acq_thread.finished.connect(self._call_post_run)
        #self.measurement_state_changed.emit(True)
        #self.running.update_value(True)
        self.run_state.update_value('run_prerun')
        try:
            self.pre_run()
        except Exception as err:
            #print("err", err)
            self.run_state.update_value('stop_failure')
            self.activation.update_value(False)            
            raise

        self.run_state.update_value('run_thread_starting')
        self.acq_thread.start()
        self.run_state.update_value('run_thread_run')
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
        
        Don't call this directly!
        """
        
        if hasattr(self, '_run'):
            self.log.warning("warning _run is deprecated, use run")
            self._run()
        else:
            raise NotImplementedError("Measurement {}.run() not defined".format(self.name))
    
    @QtCore.Slot()
    def _call_post_run(self):
        """
        Don't call this directly!
        """
        self.run_state.update_value('run_post_run')
        try:
            self.post_run()
        except Exception as err:
            self.end_state = 'stop_failure'
            raise
        finally:
            self.activation.update_value(False)
            self.run_state.update_value(self.end_state)            

    
    def post_run(self):
        """Override this method to enable main-thread finalization after to measurement thread completes"""
        pass
        
    def _thread_run(self):
        """
        This function governs the behavior of the measurement thread. 
        """
        print(self.name, "_thread_run thread_id:", threading.get_ident())
        self.set_progress(50.) # set progress bars to default run position at 50%
        try:
            if self.settings['profile']:
                import cProfile
                profile = cProfile.Profile()
                profile.enable()
            self.run()
            success = True
        except Exception as err:
            success = False
            raise
        finally:
            self.run_state.update_value('run_thread_end')

            #self.running.update_value(False)
            self.set_progress(0.) # set progress bars back to zero
            #self.measurement_state_changed.emit(False)
            if self.interrupt_measurement_called:
                self.measurement_interrupted.emit()
                self.interrupt_measurement_called = False
                end_state = 'stop_interrupted'
            elif not success:
                end_state = "stop_failure"
            else:
                self.measurement_sucessfully_completed.emit()
                end_state = "stop_success"
            if self.settings['profile']:
                profile.disable()
                profile.print_stats(sort='time')
                            
            self.end_state = end_state

    
            


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
    def _interrupt(self):
        """
        Kindly ask the measurement to stop.
        
        This raises the :attr:`interrupt_measurement_called` flag
        To actually stop, the threaded :meth:`run` method must check
        for this flag and exit
        """
        self.log.info("measurement {} stopping {}".format(self.name, self.settings['run_state']))
        # print("{} interrupt(): run_state={}".format(self.name, self.settings['run_state']))
        if self.settings['run_state'].startswith('run'):
            self.log.info("measurement {} interrupt called".format(self.name))
            self.interrupt_measurement_called = True
        #self.activation.update_value(False)
        #Make sure display is up to date        
        #self._on_display_update_timer()
        
    def interrupt(self):
        self.activation.update_value(False)
    

    def terminate(self):
        """
        Terminate MeasurementQThread. Usually a bad idea:
        This will not clean up the thread correctly and usually
        requires a reboot of the App
        """
        self.acq_thread.terminate()
        
    def start_stop(self, start):
        """
        Use boolean *start* to either start (True) or
        interrupt (False) measurement. Test.
        """
        self.log.info("{} start_stop {}".format(self.name, start))
        if start:
            self._start()
        else:
            self._interrupt()

        
    def is_measuring(self):
        """
        Returns whether the acquisition thread is running
        """
        #print(self.name, "is_measuring run_state", self.settings['run_state'])
        return self.settings['run_state'].startswith('run')
        
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
        """
    def is_thread_alive(self):
        if self.acq_thread is None:
            return False
        else:
            #resp =  self.acq_thread.is_alive()
            resp = self.acq_thread.isRunning()
            return resp        
    
    def update_display(self):
        "Override this function to provide figure updates when the display timer runs"
        pass
    
    
    @QtCore.Slot()
    def _on_display_update_timer(self):
        try:
            self.update_display()
        except Exception as err:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            self.log.error("{} Failed to update figure1: {}. {}".format(self.name, err, traceback.format_exception(exc_type, exc_value, exc_traceback)))          
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
        
    def start_nested_measure_and_wait(self, measure, nested_interrupt = True, 
                                      polling_func=None, polling_time=0.1):
        """
        Start another nested measurement *measure* and wait until completion.
        Should be called with run function.
        
        
        Optionally it can call a polling function *polling_func* with no arguments
        at an interval *polling_time* in seconds. 
        
        if *nested_interrupt* is True then interrupting the nested *measure* will
        also interrupt the outer measurement. *nested_interrupt* defaults to True
        
        returns True if successful run, otherwise returns false for a run failure or interrupted measurement
        """
        
        self.log.info("Starting nested measurement {} from {} on thread id {}".format(measure.name, self.name, threading.get_ident()))
        
        measure.start()
                
        # Wait until measurement has started, timeout of 1 second
        t0 = time.time()
        while not measure.is_measuring():
            time.sleep(0.010)
            if time.time() - t0 > 1.0:
                print(self.name, ': nested measurement', measure.name, 'has not started before timeout', )
                return measure.settings['run_state'] == 'stop_success'
                
        last_polling = time.time()
        
        # Now that it is running, wait until done
        while measure.is_measuring():
            if self.interrupt_measurement_called:
                #print('nest outer interrupted', self.interrupt_measurement_called)
                measure.interrupt()
                
            if measure.interrupt_measurement_called and nested_interrupt:
                # THIS IS MAYBE UNSAFE???: measure.interrupt_measurement_called might be also TRUE if measure finished successfully?
                # IDEA to TEST: also check the measure.settings['run_state'].startswidth('stop')
                print("nested interrupt bubbling up", measure.interrupt_measurement_called, self.interrupt_measurement_called)
                self.interrupt()
 
            time.sleep(0.010)
            
            # polling
            if measure.settings['run_state'] == 'run_thread_run':
                if polling_func:
                    t = time.time()
                    if t - last_polling > polling_time:
                        try:
                            polling_func()
                        except Exception as err:
                            self.log.error('start_nested_measure_and_wait polling failed {}'.format(err))
                        last_polling = t
                    
        #returns True if successful run, otherwise,
        #returns false for a run failure or interrupted measurement
        return measure.settings['run_state'] == 'stop_success'
                    
        
    
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
        #self.show_ui()
        
    def show_ui(self):
        """
        Shows the graphical user interface of this measurement. :attr:`ui`
        """
        self.app.bring_measure_ui_to_front(self)
#         if self.app.mdi and self.ui.parent():
#             self.ui.parent().raise_()
#             return
#         self.ui.show()
#         self.ui.activateWindow()
#         self.ui.raise_() #just to be sure it's on top
#         if self.app.mdi and self.ui.parent():
#             self.ui.parent().raise_()
    
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
            
    def web_ui(self):
        return "Hardware {}".format(self.name)
