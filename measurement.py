# -*- coding: utf-8 -*-
"""
Created on Tue Apr  1 09:25:48 2014
@author: esbarnard
"""
from __future__ import absolute_import, print_function

import sys
import threading
import time
import traceback
from typing import Callable
from warnings import warn

from qtpy import QtCore, QtGui, QtWidgets

from .operations import Operations
from .base_app import BaseMicroscopeApp
from .dynamical_widgets.generic_widget import add_to_layout, new_widget
from .dynamical_widgets.tree_widget import SubtreeManager
from .helper_funcs import get_logger_from_class, load_qt_ui_file
from .logged_quantity import LQCollection


class MeasurementQThread(QtCore.QThread):
    def __init__(self, measurement, parent=None):
        super(MeasurementQThread, self).__init__(parent)
        self.measurement = measurement

    def run(self):
        self.measurement._thread_run()


class Measurement:
    """
    Base class for ScopeFoundry Measurement objects

    to subclass, implement :meth:`setup`, :meth:`run`

    for measurements with graphical interfaces,
    subclass and additionally implement :meth:`setup_figure`, :meth:`update_display`


    Run States:

    stop_first -> run_starting -> run_pre_run --> run_thread_starting --> run_thread_run -->

    run_thread_end --> run_post_run --> stop_success | stop_interrupted | stop_failure

    """

    def __init__(self, app: BaseMicroscopeApp, name: str = None):

        self.q_object = MeasurementQObject(self)
        self.measurement_sucessfully_completed = (
            self.q_object.measurement_sucessfully_completed
        )
        self.measurement_interrupted = self.q_object.measurement_interrupted

        self.log = get_logger_from_class(self)

        if not hasattr(self, "name"):
            self.name = self.__class__.__name__

        if name is not None:
            self.name = name

        self.app = app

        self.display_update_period = 0.1  # seconds

        self.acq_thread = None

        self.interrupt_measurement_called = False

        self.settings = LQCollection(path=f"mm/{self.name}")
        self.operations = Operations()
        self._subtree_managers_ = []
        self._widgets_managers_ = []

        self.activation = self.settings.New(
            name="activation",
            dtype=bool,
            ro=False,
            description=f"<i>{self.name}</i>",
            protected=True,
        )  # does the user want to the thread to be running

        self.run_state = self.settings.New(
            "run_state", dtype=str, initial="stop_first", ro=True, protected=True
        )
        self.progress = self.settings.New(
            "progress", dtype=float, unit="%", si=False, ro=True, protected=True
        )
        self.settings.New(
            "profile",
            dtype=bool,
            initial=False,
            description="Run a profile on the run to find performance problems",
        )

        self.activation.updated_value[bool].connect(self.start_stop)

        self.add_operation("start", self.start)
        self.add_operation("interrupt", self.interrupt)
        # self.add_operation('terminate', self.terminate)
        # self.add_operation("setup", self.setup)
        # self.add_operation("setup_figure", self.setup_figure)
        self.add_operation("update_display", self.update_display)
        self.add_operation("show_ui", self.show_ui)
        self.add_operation("Reload_Code", self.reload_code)

        if hasattr(self, "ui_filename"):
            self.load_ui()

        self.setup()

    def setup(self):
        """Override this to set up logged quantities and gui connections
        Runs during __init__, before the hardware connection is established
        Should generate desired LoggedQuantities"""
        pass
        # raise NotImplementedError()

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
        # self.start_stop(True)
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
        self.run_state.update_value("run_starting")

        msg = f"measurement {self.name} start called from thread: {repr(threading.get_ident())}"
        self.log.info(msg)

        if self.is_thread_alive():
            msg = f"Cannot start a new measurement while still measuring {self.acq_thread} {self.is_measuring()}"
            raise RuntimeError(msg)

        # remove previous qthread with delete later
        # if self.acq_thread is not None:
        #    self.acq_thread.deleteLater()
        self.acq_thread = MeasurementQThread(self)
        self.acq_thread.finished.connect(self._call_post_run)
        # self.measurement_state_changed.emit(True)
        # self.running.update_value(True)
        self.run_state.update_value("run_prerun")
        try:
            self.pre_run()
        except Exception as err:
            # print("err", err)
            self.run_state.update_value("stop_failure")
            self.activation.update_value(False)
            raise

        self.run_state.update_value("run_thread_starting")
        self.acq_thread.start()
        self.run_state.update_value("run_thread_run")
        self.t_start = time.time()
        self.q_object.display_update_timer.start(int(self.display_update_period * 1000))

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

        if hasattr(self, "_run"):
            self.log.warning("warning _run is deprecated, use run")
            self._run()
        else:
            raise NotImplementedError(
                "Measurement {}.run() not defined".format(self.name)
            )

    def _call_post_run(self):
        """
        Don't call this directly!
        """
        self.run_state.update_value("run_post_run")
        try:
            self.post_run()
        except Exception as err:
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
        self.progress.update_value(50.0)  # default 50% w/o time remaining estimation
        self._t0 = time.time()
        try:
            if self.settings["profile"]:
                import cProfile

                profile = cProfile.Profile()
                profile.enable()
            self.run()
            success = True
        except Exception as err:
            success = False
            raise
        finally:
            self.run_state.update_value("run_thread_end")

            # self.running.update_value(False)
            self.set_progress(0.0)  # set progress bars back to zero
            # self.measurement_state_changed.emit(False)
            if self.interrupt_measurement_called:
                self.measurement_interrupted.emit()
                self.interrupt_measurement_called = False
                end_state = "stop_interrupted"
            elif not success:
                end_state = "stop_failure"
            else:
                self.measurement_sucessfully_completed.emit()
                end_state = "stop_success"
            if self.settings["profile"]:
                profile.disable()
                profile.print_stats(sort="time")

            self.end_state = end_state

    @property
    def gui(self):
        self.log.warning(
            "Measurement.gui is deprecated, use Measurement.app "
            + repr(DeprecationWarning)
        )
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

        if pct:
            text = f"{self.name} (in {to_etr_str((100 - pct)/pct * (time.time() - self._t0))})"
        else:
            text = self.name

        if hasattr(self, "subwin"):
            self.subwin.setWindowTitle(text)

        for manager in self._subtree_managers_:
            manager.set_header_text(0, text, None)

    def _interrupt(self):
        """
        Kindly ask the measurement to stop.

        This raises the :attr:`interrupt_measurement_called` flag
        To actually stop, the threaded :meth:`run` method must check
        for this flag and exit
        """
        self.log.info(
            "measurement {} stopping {}".format(self.name, self.settings["run_state"])
        )
        # print("{} interrupt(): run_state={}".format(self.name, self.settings['run_state']))
        if self.settings["run_state"].startswith("run"):
            self.log.info("measurement {} interrupt called".format(self.name))
            self.interrupt_measurement_called = True
        # self.activation.update_value(False)
        # Make sure display is up to date
        # self.q_object._on_display_update_timer()

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
        # print(self.name, "is_measuring run_state", self.settings['run_state'])
        return self.settings["run_state"].startswith("run")

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
            # resp =  self.acq_thread.is_alive()
            resp = self.acq_thread.isRunning()
            return resp

    def update_display(self):
        "Override this function to provide figure updates when the display timer runs"
        pass

    def add_logged_quantity(self, name, **kwargs):
        """
        Create a new :class:`LoggedQuantity` and adds it to the measurement's
        :attr:`settings` (:class:`LQCollection`)
        """
        lq = self.settings.New(name=name, **kwargs)
        return lq

    def start_nested_measure_and_wait(
        self, measure, nested_interrupt=True, polling_func=None, polling_time=0.1
    ):
        """
        Start another nested measurement *measure* and wait until completion.
        Should be called with run function.


        Optionally it can call a polling function *polling_func* with no arguments
        at an interval *polling_time* in seconds.

        if *nested_interrupt* is True then interrupting the nested *measure* will
        also interrupt the outer measurement. *nested_interrupt* defaults to True

        returns True if successful run, otherwise returns false for a run failure or interrupted measurement
        """

        self.log.info(
            "Starting nested measurement {} from {} on thread id {}".format(
                measure.name, self.name, threading.get_ident()
            )
        )

        measure.start()

        # Wait until measurement has started, timeout of 1 second
        t0 = time.time()
        while not measure.is_measuring():
            time.sleep(0.010)
            if time.time() - t0 > 1.0:
                print(
                    self.name,
                    ": nested measurement",
                    measure.name,
                    "has not started before timeout",
                )
                return measure.settings["run_state"] == "stop_success"

        last_polling = time.time()

        # Now that it is running, wait until done
        while measure.is_measuring():
            if self.interrupt_measurement_called:
                # print('nest outer interrupted', self.interrupt_measurement_called)
                measure.interrupt()

            if measure.interrupt_measurement_called and nested_interrupt:
                # THIS IS MAYBE UNSAFE???: measure.interrupt_measurement_called might be also TRUE if measure finished successfully?
                # IDEA to TEST: also check the measure.settings['run_state'].startswidth('stop')
                print(
                    "nested interrupt bubbling up",
                    measure.interrupt_measurement_called,
                    self.interrupt_measurement_called,
                )
                self.interrupt()

            time.sleep(0.010)

            # polling
            if measure.settings["run_state"] == "run_thread_run":
                if polling_func:
                    t = time.time()
                    if t - last_polling > polling_time:
                        try:
                            polling_func()
                        except Exception as err:
                            self.log.error(
                                "start_nested_measure_and_wait polling failed {}".format(
                                    err
                                )
                            )
                        last_polling = t

        # returns True if successful run, otherwise,
        # returns false for a run failure or interrupted measurement
        return measure.settings["run_state"] == "stop_success"

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
        # self.show_ui()

    def show_ui(self):
        """
        Shows the graphical user interface of this measurement. :attr:`ui`
        """
        self.app.bring_measure_ui_to_front(self)

    def new_control_widgets(self, title: str = None, include=None, exclude=None):
        """creates scroll area group box that updates on dynamical add/remove of settings/operations"""
        if title is None:
            title = self.name
        return new_widget(self, title, include, exclude)

    def add_to_layout(self, layout, include=None, exclude=None):
        add_to_layout(self, layout, include, exclude)

    def add_operation(self, name: str, op_func: Callable[[], None]):
        """
        Create an operation for the Measurement.

        *op_func* is a function that will be called upon operation activation

        for op_name in include_operations:
            btn = QtWidgets.QPushButton(op_name)
            btn.clicked.connect(self.operations[op_name])
            additional_widgets[op_name] = btn
        operations are typically exposed in the default ScopeFoundry gui via a pushButton

        :type name: str
        :type op_func: QtCore.Slot or Callable without Argument
        """
        self.operations.add(name, op_func)

    def remove_operation(self, name: str):
        self.operations.remove(name)

    def web_ui(self):
        return "Hardware {}".format(self.name)

    def reload_code(self):
        import inspect

        import xreload

        mod = inspect.getmodule(self)
        x = xreload.xreload(mod)
        print("Reloading from code", mod, x)

    def on_new_subtree(self, subtree: SubtreeManager):
        progress_bar = QtWidgets.QProgressBar()
        self.progress.connect_to_widget(progress_bar)
        subtree.tree_widget.setItemWidget(subtree.header_item, 1, progress_bar)
        subtree.progress_bar = progress_bar

    @property
    def tree_progressBar(self):
        # for backward compatibility
        warn(
            "Measurement.tree_progressBar deprecated, loop through Measurement._subtree_managers_[i].progress_bar instead.",
            DeprecationWarning,
        )
        return self._subtree_managers_[0].progress_bar

    def on_right_click(self):
        cmenu = QtWidgets.QMenu()
        a = cmenu.addAction(self.name)
        a.setEnabled(False)
        cmenu.addSeparator()
        cmenu.addAction("Start", self.start)
        cmenu.addAction("Interrupt", self.interrupt)
        cmenu.addSeparator()
        cmenu.addAction("Show", self.show_ui)
        cmenu.exec_(QtGui.QCursor.pos())


class MeasurementQObject(QtCore.QObject):

    measurement_sucessfully_completed = QtCore.Signal(())
    """signal sent when full measurement is complete"""
    measurement_interrupted = QtCore.Signal(())
    """signal sent when  measurement is complete due to an interruption"""

    def __init__(self, measurement: Measurement, parent: QtCore.QObject = None) -> None:
        super().__init__(parent)
        self.m = measurement
        self.display_update_timer = QtCore.QTimer()
        self.display_update_timer.timeout.connect(self._on_display_update_timer)

    @QtCore.Slot()
    def _on_display_update_timer(self):
        try:
            self.m.update_display()
        except Exception as err:
            exc_type, exc_value, exc_tb = sys.exc_info()
            self.m.log.error(
                "{} Failed to update display: {}. {}".format(
                    self.m.name,
                    err,
                    "\n".join(traceback.format_exception(exc_type, exc_value, exc_tb)),
                )
            )
        finally:
            if not self.m.is_measuring():
                self.display_update_timer.stop()


def to_etr_str(secs):
    mins, mins_rem = divmod(secs, 60)
    if not mins:
        return f"{int(secs)}s"
    hours, hours_rem = divmod(secs, 3600)
    if not hours:
        return f"{mins + mins_rem/60:0.1f}min"
    days, days_rem = divmod(secs, 86400)
    if not days:
        return f"{hours + hours_rem/3600:0.1f}h"
    return f"{secs/86400:0.1f}d"
