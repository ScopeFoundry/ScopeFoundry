'''
Created on Jul 23, 2014

Modified by Ed Barnard
UI enhancements by Ed Barnard, Alan Buckley
'''
from __future__ import print_function, division, absolute_import

import sys, os
import time
import datetime
import numpy as np
import collections
from collections import OrderedDict
import logging
import inspect

try:
    import configparser
except: # python 2
    import ConfigParser as configparser


from qtpy import QtCore, QtGui, QtWidgets
import pyqtgraph as pg
#import pyqtgraph.console

try:
    import IPython
    if IPython.version_info[0] < 4: #compatibility for IPython < 4.0 (pre Jupyter split)
        from IPython.qt.console.rich_ipython_widget import RichIPythonWidget as RichJupyterWidget
        from IPython.qt.inprocess import QtInProcessKernelManager
    else:
        from qtconsole.rich_jupyter_widget import RichJupyterWidget
        from qtconsole.inprocess import QtInProcessKernelManager
    CONSOLE_TYPE = 'qtconsole'
except Exception as err:
    logging.warning("ScopeFoundry unable to import iPython console, using pyqtgraph.console instead. Error: {}".format( err))
    import pyqtgraph.console
    CONSOLE_TYPE = 'pyqtgraph.console'
    
#import matplotlib
#matplotlib.rcParams['backend.qt4'] = 'PySide'
#from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
#from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar2

#from matplotlib.figure import Figure

from .logged_quantity import LoggedQuantity, LQCollection

from .helper_funcs import confirm_on_close, ignore_on_close, load_qt_ui_file, \
    OrderedAttrDict, sibling_path, get_logger_from_class, str2bool

#from equipment.image_display import ImageDisplay


import warnings
import traceback

# See https://riverbankcomputing.com/pipermail/pyqt/2016-March/037136.html
# makes sure that unhandled exceptions in slots don't crash the whole app with PyQt 5.5 and higher
# old version:
## sys.excepthook = traceback.print_exception
# new version to send to logger
def log_unhandled_exception(*exc_info):
    text = "".join(traceback.format_exception(*exc_info))
    logging.critical("Unhandled exception:" + text)
    #print("Unhandled exception:" + text)
sys.excepthook = log_unhandled_exception

class BaseApp(QtCore.QObject):
    
    def __init__(self, argv):
        QtCore.QObject.__init__(self)
        self.log = get_logger_from_class(self)
        
        self.this_dir, self.this_filename = os.path.split(__file__)

        self.qtapp = QtWidgets.QApplication.instance()
        if not self.qtapp:
            self.qtapp = QtWidgets.QApplication(argv)
        
        self.settings = LQCollection()
        
        self.setup_console_widget()
        # FIXME Breaks things for microscopes, but necessary for stand alone apps!
        #if hasattr(self, "setup"):
        #    self.setup() 

        if not hasattr(self, 'name'):
            self.name = "ScopeFoundry"
        self.qtapp.setApplicationName(self.name)

        
    def exec_(self):
        return self.qtapp.exec_()
        
    def setup_console_widget(self):
        # Console
        if CONSOLE_TYPE == 'pyqtgraph.console':
            self.console_widget = pyqtgraph.console.ConsoleWidget(namespace={'app':self, 'pg':pg, 'np':np}, text="ScopeFoundry Console")
        elif CONSOLE_TYPE == 'qtconsole':
            # https://github.com/ipython/ipython-in-depth/blob/master/examples/Embedding/inprocess_qtconsole.py
            self.kernel_manager = QtInProcessKernelManager()
            self.kernel_manager.start_kernel()
            self.kernel = self.kernel_manager.kernel
            self.kernel.gui = 'qt4'
            self.kernel.shell.push({'np': np, 'app': self})
            self.kernel_client = self.kernel_manager.client()
            self.kernel_client.start_channels()
    
            #self.console_widget = RichIPythonWidget()
            self.console_widget = RichJupyterWidget()
            self.console_widget.setWindowTitle("ScopeFoundry IPython Console")
            self.console_widget.kernel_manager = self.kernel_manager
            self.console_widget.kernel_client = self.kernel_client
        else:
            raise ValueError("CONSOLE_TYPE undefined")
        
        return self.console_widget         

    def setup(self):
        pass


    def settings_save_ini(self, fname, save_ro=True):
        """"""
        config = configparser.ConfigParser()
        config.optionxform = str
        config.add_section('app')
        config.set('app', 'name', self.name)
        for lqname, lq in self.settings.as_dict().items():
            if not lq.ro or save_ro:
                config.set('app', lqname, lq.ini_string_value())
                
        with open(fname, 'w') as configfile:
            config.write(configfile)
        
        self.log.info("ini settings saved to {} {}".format( fname, config.optionxform))    

    def settings_load_ini(self, fname):
        self.log.info("ini settings loading from " + fname)
        

        config = configparser.ConfigParser()
        config.optionxform = str
        config.read(fname)

        if 'app' in config.sections():
            for lqname, new_val in config.items('app'):
                #print(lqname)
                lq = self.settings.as_dict().get(lqname)
                if lq:
                    if lq.dtype == bool:
                        new_val = str2bool(new_val)
                    lq.update_value(new_val)

    def settings_save_ini_ask(self, dir=None, save_ro=True):
        """Opens a Save dialogue asking the user to select a save destination and give the save file a filename. Saves settings to an .ini file."""
        # TODO add default directory, etc
        fname, _ = QtWidgets.QFileDialog.getSaveFileName(self.ui, caption=u'Save Settings', dir=u"", filter=u"Settings (*.ini)")
        #print(repr(fname))
        if fname:
            self.settings_save_ini(fname, save_ro=save_ro)
        return fname

    def settings_load_ini_ask(self, dir=None):
        """Opens a Load dialogue asking the user which .ini file to load into our app settings. Loads settings from an .ini file."""
        # TODO add default directory, etc
        fname, _ = QtWidgets.QFileDialog.getOpenFileName(None, "Settings (*.ini)")
        #print(repr(fname))
        if fname:
            self.settings_load_ini(fname)
        return fname  

class BaseMicroscopeApp(BaseApp):
    name = "ScopeFoundry"
    """The name of the microscope app, default is ScopeFoundry."""
    mdi = True
    """Multiple Document Interface flag. Tells the app whether to include an MDI widget in the app."""
    
    def __del__ ( self ): 
        self.ui = None

    def show(self):
        """Tells Qt to show the user interface"""
        #self.ui.exec_()
        self.ui.show()

    def __init__(self, argv):
        BaseApp.__init__(self, argv)
        
        initial_data_save_dir = os.path.abspath(os.path.join('.', 'data'))
        if not os.path.isdir(initial_data_save_dir):
            os.makedirs(initial_data_save_dir)
        
        self.settings.New('save_dir', dtype='file', is_dir=True, initial=initial_data_save_dir)
        self.settings.New('sample', dtype=str, initial='')
        self.settings.New('data_fname_format', dtype=str,
                          initial='{timestamp:%y%m%d_%H%M%S}_{measurement.name}.{ext}')
        
        if not hasattr(self, 'ui_filename'):
            if self.mdi:
                self.ui_filename = sibling_path(__file__,"base_microscope_app_mdi.ui")
            else:
                self.ui_filename = sibling_path(__file__,"base_microscope_app.ui")
        # Load Qt UI from .ui file
        self.ui = load_qt_ui_file(self.ui_filename)
        if self.mdi:
            self.ui.col_splitter.setStretchFactor(0,0)
            self.ui.col_splitter.setStretchFactor(1,1)
        
        self.hardware = OrderedAttrDict()
        self.measurements = OrderedAttrDict()

        self.quickbar = None
                   
        self.setup()
        
        self.setup_default_ui()
        

    def setup_default_ui(self):
        self.ui.show()
        self.ui.activateWindow()
                
        """Loads various default features into the user interface upon app startup."""
        confirm_on_close(self.ui, title="Close %s?" % self.name, message="Do you wish to shut down %s?" % self.name, func_on_close=self.on_close)
        
        self.ui.hardware_treeWidget.setColumnWidth(0,175)
        self.ui.measurements_treeWidget.setColumnWidth(0,175)

        self.ui.measurements_treeWidget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.ui.measurements_treeWidget.customContextMenuRequested.connect(self.on_measure_tree_context_menu)

        self.ui.hardware_treeWidget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.ui.hardware_treeWidget.customContextMenuRequested.connect(self.on_hardware_tree_context_menu)


        # Setup the Measurement UI's         
        for name, measure in self.measurements.items():
            self.log.info("setting up figures for {} measurement {}".format( name, measure.name) )            
            measure.setup_figure()
            if self.mdi and hasattr(measure, 'ui'):
                measure.subwin = self.ui.mdiArea.addSubWindow(measure.ui, QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowMinMaxButtonsHint)
                measure.subwin.setWindowTitle(measure.name)
                measure.subwin.measure = measure
                ignore_on_close(measure.subwin)
                measure.subwin.show()          
                # add menu                    
                self.ui.menuWindow.addAction(measure.name, measure.show_ui)
        
        if hasattr(self.ui, 'console_pushButton'):
            self.ui.console_pushButton.clicked.connect(self.console_widget.show)
            self.ui.console_pushButton.clicked.connect(self.console_widget.activateWindow)
                        
        if self.quickbar is None:
            # Collapse sidebar
            self.ui.quickaccess_scrollArea.setVisible(False)
        
        
        # Save Dir events
        self.ui.action_set_data_dir.triggered.connect(self.settings.save_dir.file_browser)
        self.settings.save_dir.connect_to_browse_widgets(self.ui.save_dir_lineEdit, self.ui.save_dir_browse_pushButton)
        
        # Sample meta data
        self.settings.sample.connect_bidir_to_widget(self.ui.sample_lineEdit)
        
        #settings button events
        if hasattr(self.ui, "settings_autosave_pushButton"):
            self.ui.settings_autosave_pushButton.clicked.connect(self.settings_auto_save_ini)
        if hasattr(self.ui, "settings_load_last_pushButton"):
            self.ui.settings_load_last_pushButton.clicked.connect(self.settings_load_last)
        if hasattr(self.ui, "settings_save_pushButton"):
            self.ui.settings_save_pushButton.clicked.connect(self.settings_save_dialog)
        if hasattr(self.ui, "settings_load_pushButton"):
            self.ui.settings_load_pushButton.clicked.connect(self.settings_load_dialog)
        
        #Menu bar entries:
        # TODO: connect self.ui.action_log_viewer to log viewer function
            # (Function has yet to be created)
        self.ui.action_load_ini.triggered.connect(self.settings_load_dialog)
        self.ui.action_auto_save_ini.triggered.connect(self.settings_auto_save_ini)
        self.ui.action_save_ini.triggered.connect(self.settings_save_dialog)
        self.ui.action_console.triggered.connect(self.console_widget.show)
        self.ui.action_console.triggered.connect(self.console_widget.activateWindow)
        
        
        #Refer to existing ui object:
        self.menubar = self.ui.menuWindow

        #Create new action group for switching between window and tab mode
        self.action_group = QtWidgets.QActionGroup(self)
        #Add actions to group:
        self.action_group.addAction(self.ui.window_action)
        self.action_group.addAction(self.ui.tab_action)
        
        self.ui.mdiArea.setTabsClosable(False)
        self.ui.mdiArea.setTabsMovable(True)
        
        self.ui.tab_action.triggered.connect(self.set_tab_mode)
        self.ui.window_action.triggered.connect(self.set_subwindow_mode)
        self.ui.cascade_action.triggered.connect(self.cascade_layout)
        self.ui.tile_action.triggered.connect(self.tile_layout)
        
        self.ui.setWindowTitle(self.name)

        
            
    def set_subwindow_mode(self):
        """Switches Multiple Document Interface to Subwindowed viewing mode."""
        self.ui.mdiArea.setViewMode(self.ui.mdiArea.SubWindowView)
    
    def set_tab_mode(self):
        """Switches Multiple Document Interface to Tabbed viewing mode."""
        self.ui.mdiArea.setViewMode(self.ui.mdiArea.TabbedView)
        
    def tile_layout(self):
        """Tiles subwindows in user interface. Specifically in the Multi Document Interface."""
        self.set_subwindow_mode()
        self.ui.mdiArea.tileSubWindows()
        
    def cascade_layout(self):
        """Cascades subwindows in user interface. Specifically in the Multi Document Interface."""
        self.set_subwindow_mode()
        self.ui.mdiArea.cascadeSubWindows()
        
    def bring_measure_ui_to_front(self, measure):
        S = measure.subwin
        viewMode = self.ui.mdiArea.viewMode()
        if viewMode == self.ui.mdiArea.SubWindowView:
            S.showNormal()
            S.raise_()
        elif viewMode == self.ui.mdiArea.TabbedView:
            S.showMaximized()
            S.raise_()

    
    def add_quickbar(self, widget):
        self.ui.quickaccess_scrollArea.setVisible(True)
        self.ui.quickaccess_scrollAreaWidgetContents.layout().addWidget(widget)
        self.quickbar = widget
        return self.quickbar
        
    def on_close(self):
        self.log.info("on_close")
        # disconnect all hardware objects
        for hw in self.hardware.values():
            self.log.info("disconnecting {}".format( hw.name))
            if hw.settings['connected']:
                try:
                    hw.disconnect()
                except Exception as err:
                    self.log.error("tried to disconnect {}: {}".format( hw.name, err) )

    def on_measure_tree_context_menu(self, position):
#         indexes =  self.ui.measurements_treeWidget.selectedIndexes()
#         if len(indexes) > 0:
#             level = 0
#             index = indexes[0]
#             while index.parent().isValid():
#                 index = index.parent()
#                 level += 1
#         if level == 0:
#             startAction = menu.addAction(self.tr("Start Measurement"))
#             interruptAction = menu.addAction(self.tr("Interrupt Measurement"))
        selected_items = self.ui.measurements_treeWidget.selectedItems()
        if len(selected_items) < 1:
            return
        selected_measurement_name = selected_items[0].text(0)
        if selected_measurement_name not in self.measurements:
            return
        M = self.measurements[selected_measurement_name]
        
        cmenu = QtWidgets.QMenu()        
        a = cmenu.addAction(selected_measurement_name)
        a.setEnabled(False)
        cmenu.addSeparator()
        cmenu.addAction("Start", M.start)
        cmenu.addAction("Interrupt", M.interrupt)
        cmenu.addSeparator()
        cmenu.addAction("Show", lambda M=M: self.bring_measure_ui_to_front(M))
        
        action = cmenu.exec_(QtGui.QCursor.pos())
    
    def on_hardware_tree_context_menu(self, position):
        selected_items = self.ui.hardware_treeWidget.selectedItems()
        if len(selected_items) < 1:
            return
        selected_hw_name = selected_items[0].text(0)
        if selected_hw_name not in self.hardware:
            return
        H = self.hardware[selected_hw_name]
        
        cmenu = QtWidgets.QMenu()        
        a = cmenu.addAction(selected_hw_name)
        a.setEnabled(False)
        connect_action = cmenu.addAction("Connect")
        disconnect_action = cmenu.addAction("Disconnect")
        
        action = cmenu.exec_(QtGui.QCursor.pos())
        if action == connect_action:
            H.settings['connected']=True
        elif action == disconnect_action:
            H.settings['connected']=False
        

    def setup(self):
        """ Override to add Hardware and Measurement Components"""
        #raise NotImplementedError()
        pass
    
        
    """def add_image_display(self,name,widget):
        print "---adding figure", name, widget
        if name in self.figs:
            return self.figs[name]
        else:
            disp=ImageDisplay(name,widget)
            self.figs[name]=disp
            return disp
    """
        
    def add_pg_graphics_layout(self, name, widget):
        self.log.info("---adding pg GraphicsLayout figure {} {}".format( name, widget))
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
            
            
    
#     def add_figure_mpl(self,name, widget):
#         """creates a matplotlib figure attaches it to the qwidget specified
#         (widget needs to have a layout set (preferably verticalLayout) 
#         adds a figure to self.figs"""
#         print "---adding figure", name, widget
#         if name in self.figs:
#             return self.figs[name]
#         else:
#             fig = Figure()
#             fig.patch.set_facecolor('w')
#             canvas = FigureCanvas(fig)
#             nav    = NavigationToolbar2(canvas, self.ui)
#             widget.layout().addWidget(canvas)
#             widget.layout().addWidget(nav)
#             canvas.setFocusPolicy( QtCore.Qt.ClickFocus )
#             canvas.setFocus()
#             self.figs[name] = fig
#             return fig
    
    def add_figure(self,name,widget):
        # DEPRECATED
        return self.add_figure_mpl(name,widget)
    

    def add_hardware(self,hw):
        """Loads a HardwareComponent object into the app. 
        After calling this, the HW appears in the Hardware tree.
        
        If *hw* is a class, rather an instance, create an instance 
        and add it to self.hardware
        """
        assert not hw.name in self.hardware.keys()

        if inspect.isclass(hw):
            #If *hw* is a class, rather an instance, create an instance 
            hw = hw(app=self)
        
        self.hardware.add(hw.name, hw)
        
        hw.add_widgets_to_tree(tree=self.ui.hardware_treeWidget)
        return hw
    
    
    def add_hardware_component(self,hw):
        # DEPRECATED use add_hardware()
        return self.add_hardware(hw)
    
    
    def add_measurement(self, measure):
        """Loads a Measurement object into the app.
        After calling this, the measurement appears in the Measurement tree.
        
        If *measure* is a class, rather an instance, create an instance 
        and add it to self.measurements

        """
        
        #If *measure* is a class, rather an instance, create an instance 
        if inspect.isclass(measure):
            measure = measure(app=self)

            
        assert not measure.name in self.measurements.keys()
        

        self.measurements.add(measure.name, measure)
        
        measure.add_widgets_to_tree(tree=self.ui.measurements_treeWidget)

        return measure
    
    def add_measurement_component(self, measure):
        # DEPRECATED, use add_measurement()
        return self.add_measurement(measure)
    
    def settings_save_h5(self, fname):
        """
        Saves h5 file to a file.

        ==============  =========  =============================================
        **Arguments:**  **Type:**  **Description:**
        fname           str        relative path to the filename of the h5 file.              
        ==============  =========  =============================================
        """
        from . import h5_io
        with h5_io.h5_base_file(self, fname) as h5_file:
            for measurement in self.measurements.values():
                h5_io.h5_create_measurement_group(measurement, h5_file)
            self.log.info("settings saved to {}".format(h5_file.filename))
            
    def settings_save_ini(self, fname, save_ro=True, save_app=True, save_hardware=True, save_measurements=True):
        """
        ==============  =========  ==============================================
        **Arguments:**  **Type:**  **Description:**
        fname           str        relative path to the filename of the ini file.              
        ==============  =========  ==============================================
        """
        config = configparser.ConfigParser(interpolation=None)
        config.optionxform = str
        if save_app:
            config.add_section('app')
            for lqname, lq in self.settings.as_dict().items():
                print(lq.ini_string_value())                
                config.set('app', lqname, lq.ini_string_value(), )
        if save_hardware:
            for hc_name, hc in self.hardware.items():
                section_name = 'hardware/'+hc_name
                config.add_section(section_name)
                for lqname, lq in hc.settings.as_dict().items():
                    if not lq.ro or save_ro:
                        print(lq.ini_string_value())
                        config.set(section_name, lqname, lq.ini_string_value())
        if save_measurements:
            for meas_name, measurement in self.measurements.items():
                section_name = 'measurement/'+meas_name            
                config.add_section(section_name)
                for lqname, lq in measurement.settings.as_dict().items():
                    if not lq.ro or save_ro:
                        config.set(section_name, lqname, lq.ini_string_value())
        with open(fname, 'w') as configfile:
            config.write(configfile)
        
        self.log.info("ini settings saved to {} {}".format( fname, config.optionxform))


        
    def settings_load_ini(self, fname):
        """
        ==============  =========  ==============================================
        **Arguments:**  **Type:**  **Description:**
        fname           str        relative path to the filename of the ini file.              
        ==============  =========  ==============================================
        """

        self.log.info("ini settings loading from {}".format(fname))
        config = configparser.ConfigParser(interpolation=None)
        #config = configparser.ConfigParser()
        config.optionxform = str
        config.read(fname)

        if 'app' in config.sections():
            for lqname, new_val in config.items('app'):
                lq = self.settings.get_lq(lqname)
                lq.update_value(new_val)
        
        for hc_name, hc in self.hardware.items():
            section_name = 'hardware/'+hc_name
            self.log.info(section_name)
            if section_name in config.sections():
                for lqname, new_val in config.items(section_name):
                    try:
                        lq = hc.settings.get_lq(lqname)
                        if not lq.ro:
                            lq.update_value(new_val)
                    except Exception as err:
                        self.log.info("-->Failed to load config for {}/{}, new val {}: {}".format(section_name, lqname, new_val, repr(err)))
                        
        for meas_name, measurement in self.measurements.items():
            section_name = 'measurement/'+meas_name            
            if section_name in config.sections():
                for lqname, new_val in config.items(section_name):
                    try:
                        lq = measurement.settings.get_lq(lqname)
                        if not lq.ro:
                            lq.update_value(new_val)
                    except Exception as err:
                        self.log.info("-->Failed to load config for {}/{}, new val {}: {}".format(section_name, lqname, new_val, repr(err)))
                            
        
        self.log.info("ini settings loaded from: {}".format(fname))
        
    def settings_load_h5(self, fname):
        """
        Loads h5 settings given a filename.

        ==============  =========  ====================================================================================
        **Arguments:**  **Type:**  **Description:**
        fname           str        relative path to the filename of the h5 file.              
        ==============  =========  ====================================================================================
        """
        # TODO finish this function
        import h5py
        with h5py.File(fname) as h5_file:
            pass
    
    def settings_auto_save_ini(self):
        """
        Saves the ini file to the pre-defined directory with a time stamp in the filename.
        """
        #fname = "%i_settings.h5" % time.time()
        #self.settings_save_h5(fname)
        self.settings_save_ini(os.path.join(self.settings['save_dir'], "%i_settings.ini" % time.time()))

    def settings_load_last(self):
        """
        Loads last saved ini file.
        """
        import glob
        #fname = sorted(glob.glob("*_settings.h5"))[-1]
        #self.settings_load_h5(fname)
        fname = sorted(glob.glob("*_settings.ini"))[-1]
        self.settings_load_ini(fname)
    
    
    def settings_save_dialog(self):
        """Opens a save as ini dialogue in the app user interface."""
        fname, selectedFilter = QtWidgets.QFileDialog.getSaveFileName(self.ui, "Save Settings file", "", "Settings File (*.ini)")
        if fname:
            self.settings_save_ini(fname)
    
    def settings_load_dialog(self):
        """Opens a load ini dialogue in the app user interface"""
        fname, selectedFilter = QtWidgets.QFileDialog.getOpenFileName(self.ui,"Open Settings file", "", "Settings File (*.ini *.h5)")
        self.settings_load_ini(fname)
        
    def lq_path(self,path):
        """returns the lq based on path string of the form 'domain/[component/]setting'
        domain = "measurement", "hardware" or "app"
        """
        try:
            domain,component,setting = path.split('/')
        except ValueError:#app settings do not have a component hierarchy
            domain,setting = path.split('/')
        try:
            if domain in ['hardware','HW','hw']:
                lq = getattr(self.hardware[component].settings, setting)
            if domain in ['measurement','measure']:
                lq = getattr(self.measurement[component].settings, setting)
            if domain == 'app':
                lq = getattr(self.settings, setting)
            return lq
        except UnboundLocalError:
            print('WARNING:',domain,'does not exist')
            
    def lq_paths_list(self):
        """returns all logged_quantity paths as a list"""
        list = []
        for hw_name,hw in self.hardware.items():
            for lq_name in hw.settings.keys():
                list.append('hardware/'+hw_name+"/"+lq_name)
        for measure_name,measure in self.measurement.items():
            for lq_name in measure.settings.keys():
                list.append('measurement/'+measure_name+"/"+lq_name)
        for lq_name in self.settings.keys():
            list.append('app/'+lq_name)
        return list
        
    @property
    def hardware_components(self):
        warnings.warn("App.hardware_components deprecated, used App.hardware", DeprecationWarning)
        return self.hardware
    @property
    def measurement_components(self):
        warnings.warn("App.measurement_components deprecated, used App.measurements", DeprecationWarning)
        return self.measurements
    @property
    def logged_quantities(self):
        warnings.warn('app.logged_quantities deprecated use app.settings', DeprecationWarning)
        return self.settings.as_dict()

if __name__ == '__main__':
    
    app = BaseMicroscopeApp(sys.argv)
    
    sys.exit(app.exec_())