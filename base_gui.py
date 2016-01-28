'''
Created on Jul 23, 2014

'''

import sys, os
import time
import datetime
import numpy as np
import collections

from PySide import QtCore, QtGui, QtUiTools
import pyqtgraph as pg
#import pyqtgraph.console
import IPython
if IPython.version_info[0] < 4:
    from IPython.qt.console.rich_ipython_widget import RichIPythonWidget as RichJupyterWidget
    from IPython.qt.inprocess import QtInProcessKernelManager
else:
    from qtconsole.rich_jupyter_widget import RichJupyterWidget
    from qtconsole.inprocess import QtInProcessKernelManager

import matplotlib
matplotlib.rcParams['backend.qt4'] = 'PySide'
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QTAgg as NavigationToolbar2

from matplotlib.figure import Figure

from logged_quantity import LoggedQuantity

#from equipment.image_display import ImageDisplay

import h5_io

class BaseMicroscopeGUI(object):
    
    ui_filename = "base_gui.ui"
    
    def __del__ ( self ): 
        self.ui = None

    def show(self): 
        #self.ui.exec_()
        self.ui.show()

    def __init__(self, app):
        self.app = app
        self.logged_quantities = collections.OrderedDict()
        self.hardware_components = collections.OrderedDict()
        self.measurement_components = collections.OrderedDict()
        self.figs = collections.OrderedDict()

        # Load Qt UI from .ui file
        ui_loader = QtUiTools.QUiLoader()
        ui_file = QtCore.QFile(self.ui_filename)
        ui_file.open(QtCore.QFile.ReadOnly)
        self.ui = ui_loader.load(ui_file)
        ui_file.close()
        
        self.closeEventEater = CloseEventEater()
        self.ui.installEventFilter(self.closeEventEater)

        # Run the subclass setup function
        self.setup()

        self.ui.hardware_treeWidget.setColumnWidth(0,175)
        self.ui.measurements_treeWidget.setColumnWidth(0,175)

        # Setup the figures         
        for name, measure in self.measurement_components.items():
            print "setting up figures for", name, "measurement", measure.name
            measure.setup_figure()

        # Console 
        #self.console_widget = pyqtgraph.console.ConsoleWidget(namespace={'gui':self, 'pg':pg, 'np':np}, text="ScopeFoundry GUI console")
        # https://github.com/ipython/ipython-in-depth/blob/master/examples/Embedding/inprocess_qtconsole.py
        self.kernel_manager = QtInProcessKernelManager()
        self.kernel_manager.start_kernel()
        self.kernel = self.kernel_manager.kernel
        self.kernel.gui = 'qt4'
        self.kernel.shell.push({'np': np, 'gui': self})
        self.kernel_client = self.kernel_manager.client()
        self.kernel_client.start_channels()

        #self.console_widget = RichIPythonWidget()
        self.console_widget = RichJupyterWidget()
        self.console_widget.setWindowTitle("ScopeFoundry IPython Console")
        self.console_widget.kernel_manager = self.kernel_manager
        self.console_widget.kernel_client = self.kernel_client
        #self.console_widget.exit_requested.connect(stop)
        #self.console_widget.show()
        
        if hasattr(self.ui, 'console_pushButton'):
            self.ui.console_pushButton.clicked.connect(self.console_widget.show)
            self.ui.console_pushButton.clicked.connect(self.console_widget.activateWindow)
        
        #settings events
        if hasattr(self.ui, "settings_autosave_pushButton"):
            self.ui.settings_autosave_pushButton.clicked.connect(self.settings_auto_save)
        if hasattr(self.ui, "settings_load_last_pushButton"):
            self.ui.settings_load_last_pushButton.clicked.connect(self.settings_load_last)
        if hasattr(self.ui, "settings_save_pushButton"):
            self.ui.settings_save_pushButton.clicked.connect(self.settings_save_dialog)
        if hasattr(self.ui, "settings_load_pushButton"):
            self.ui.settings_load_pushButton.clicked.connect(self.settings_load_dialog)
        

    def setup(self):
        """ Override to add Hardware and Measurement Components"""
        #raise NotImplementedError()
    
        
    def add_image_display(self,name,widget):
        print "---adding figure", name, widget
        if name in self.figs:
            return self.figs[name]
        else:
            disp=ImageDisplay(name,widget)
            self.figs[name]=disp
            return disp
        
    def add_pg_graphics_layout(self, name, widget):
        print "---adding pg GraphicsLayout figure", name, widget
        if name in self.figs:
            return self.figs[name]
        else:
            disp=pg.GraphicsLayoutWidget(border=(100,100,100))
            widget.layout().addWidget(disp)
            self.figs[name]=disp
            return disp
        
        # IDEA: write an abstract function to add pg.imageItem() for maps, 
        # which haddels, pixelscale, ROI ....
        # could also be implemented in the base_2d class? 
            
            
    
    def add_figure_mpl(self,name, widget):
        """creates a matplotlib figure attaches it to the qwidget specified
        (widget needs to have a layout set (preferably verticalLayout) 
        adds a figure to self.figs"""
        print "---adding figure", name, widget
        if name in self.figs:
            return self.figs[name]
        else:
            fig = Figure()
            fig.patch.set_facecolor('w')
            canvas = FigureCanvas(fig)
            nav    = NavigationToolbar2(canvas, self.ui)
            widget.layout().addWidget(canvas)
            widget.layout().addWidget(nav)
            canvas.setFocusPolicy( QtCore.Qt.ClickFocus )
            canvas.setFocus()
            self.figs[name] = fig
            return fig
    
    def add_figure(self,name,widget):
        return self.add_figure_mpl(name,widget)
    
    def add_logged_quantity(self, name, **kwargs):
        lq = LoggedQuantity(name=name, **kwargs)
        self.logged_quantities[name] = lq
        return lq

    def add_hardware_component(self,hc):
        self.hardware_components[hc.name] = hc
        return hc
    
    def add_measurement_component(self, measure):
        assert not measure.name in self.measurement_components.keys()
        self.measurement_components[measure.name] = measure
        return measure
    
    def settings_save_h5(self, fname):
        with h5_io.h5_base_file(self, fname) as h5_file:
            for measurement in self.measurement_components.values():
                h5_io.h5_create_measurement_group(measurement, h5_file)
            print "settings saved to", h5_file.filename
            
    def settings_save_ini(self, fname, save_ro=True, save_gui=True, save_hardware=True, save_measurements=True):
        import ConfigParser
        config = ConfigParser.ConfigParser()
        config.optionxform = str
        if save_gui:
            config.add_section('gui')
            for lqname, lq in self.logged_quantities.items():
                config.set('gui', lqname, lq.val)
        if save_hardware:
            for hc_name, hc in self.hardware_components.items():
                section_name = 'hardware/'+hc_name            
                config.add_section(section_name)
                for lqname, lq in hc.logged_quantities.items():
                    if not lq.ro or save_ro:
                        config.set(section_name, lqname, lq.val)
        if save_measurements:
            for meas_name, measurement in self.measurement_components.items():
                section_name = 'measurement/'+meas_name            
                config.add_section(section_name)
                for lqname, lq in measurement.logged_quantities.items():
                    if not lq.ro or save_ro:
                        config.set(section_name, lqname, lq.val)
        with open(fname, 'wb') as configfile:
            config.write(configfile)
        
        print "ini settings saved to", fname, config.optionxform


        
    def settings_load_ini(self, fname):
        print "ini settings loading from", fname
        
        def str2bool(v):
            return v.lower() in ("yes", "true", "t", "1")


        import ConfigParser
        config = ConfigParser.ConfigParser()
        config.optionxform = str
        config.read(fname)

        if 'gui' in config.sections():
            for lqname, new_val in config.items('gui'):
                lq = self.logged_quantities[lqname]
                if lq.dtype == bool:
                    new_val = str2bool(new_val)
                lq.update_value(new_val)
        
        for hc_name, hc in self.hardware_components.items():
            section_name = 'hardware/'+hc_name
            print section_name
            if section_name in config.sections():
                for lqname, new_val in config.items(section_name):
                    try:
                        lq = hc.logged_quantities[lqname]
                        if lq.dtype == bool:
                            new_val = str2bool(new_val)
                        if not lq.ro:
                            lq.update_value(new_val)
                    except Exception as err:
                        print "-->Failed to load config for {}/{}, new val {}: {}".format(section_name, lqname, new_val, repr(err))
                        
        for meas_name, measurement in self.measurement_components.items():
            section_name = 'measurement/'+meas_name            
            if section_name in config.sections():
                for lqname, new_val in config.items(section_name):
                    lq = measurement.logged_quantities[lqname]
                    if lq.dtype == bool:
                        new_val = str2bool(new_val)                    
                    if not lq.ro:
                        lq.update_value(new_val)
        
        print "ini settings loaded from", fname
        
    def settings_load_h5(self, fname):
        import h5py
        with h5py.File(fname) as h5_file:
            pass
    
    def settings_auto_save(self):
        #fname = "%i_settings.h5" % time.time()
        #self.settings_save_h5(fname)
        self.settings_save_ini("%i_settings.ini" % time.time())

    def settings_load_last(self):
        import glob
        #fname = sorted(glob.glob("*_settings.h5"))[-1]
        #self.settings_load_h5(fname)
        fname = sorted(glob.glob("*_settings.ini"))[-1]
        self.settings_load_ini(fname)
    
    
    def settings_save_dialog(self):
        fname, selectedFilter = QtGui.QFileDialog.getSaveFileName(self.ui, "Save Settings file", "", "Settings File (*.ini)")
        if fname:
            self.settings_save_ini(fname)
    
    def settings_load_dialog(self):
        fname, selectedFilter = QtGui.QFileDialog.getOpenFileName(self.ui,"Open Settings file", "", "Settings File (*.ini *.h5)")
        self.settings_load_ini(fname)
    
class CloseEventEater(QtCore.QObject):
    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Close:
            # eat close event
            print "close"
            reply = QtGui.QMessageBox.question(None, 
                                               "Close ScopeFoundry?", 
                                               "Do you wish to shut down ScopeFoundry?",
                                               QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
            if reply == QtGui.QMessageBox.Yes:
                QtGui.QApplication.quit()
                event.accept()
            else:
                event.ignore()
            return True
        else:
            # standard event processing            
            return QtCore.QObject.eventFilter(self,obj, event)

if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    app.setApplicationName("Microscope Control Application")
    
    gui = BaseMicroscopeGUI(app)
    gui.show()
    
    sys.exit(app.exec_())