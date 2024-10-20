import datetime
import inspect
import json
import logging
import time
import warnings
from collections import OrderedDict
from pathlib import Path

import pyqtgraph as pg
from qtpy import QtCore, QtGui, QtWidgets

from ScopeFoundry import h5_io, ini_io
from ScopeFoundry.helper_funcs import (
    OrderedAttrDict,
    sibling_path,
    load_qt_ui_file,
    confirm_on_close,
    ignore_on_close,
)
from ScopeFoundry.logged_quantity import LoggedQuantity, LQCollection

from .base_app import BaseApp


class BaseMicroscopeApp(BaseApp):
    name = "ScopeFoundry"
    """The name of the microscope app, default is ScopeFoundry."""
    mdi = True
    """Multiple Document Interface flag. Tells the app whether to include an MDI widget in the app."""

    def __del__(self):
        self.ui = None

    def show(self):
        """Tells Qt to show the user interface"""
        # self.ui.exec_()
        self.ui.show()

    def __init__(self, argv=[], dark_mode=False):
        super().__init__(argv, dark_mode)

        self._setting_paths = {}

        log_path = Path.cwd() / "log"
        if not log_path.is_dir():
            log_path.mkdir()
        _fname = f"{self.name}_log_{datetime.datetime.now():%y%m%d_%H%M%S}.txt"
        self.log_file_handler = logging.FileHandler(str(log_path / _fname))
        fmt = "%(asctime)s|%(levelname)s|%(name)s|%(message)s"
        datefmt = "%Y-%m-%dT%H:%M:%S"
        formatter = logging.Formatter(fmt, datefmt)
        self.log_file_handler.setFormatter(formatter)

        logging.getLogger().addHandler(self.log_file_handler)

        initial_save_path = Path.cwd() / "data"
        if not initial_save_path.is_dir():
            initial_save_path.mkdir()

        self.settings.New(
            "save_dir", dtype="file", is_dir=True, initial=initial_save_path.as_posix()
        )
        self.settings.New("sample", dtype=str, initial="")
        self.settings.New(
            "data_fname_format",
            dtype=str,
            initial="{timestamp:%y%m%d_%H%M%S}_{measurement.name}.{ext}",
        )
        # Potential new alternative default: '{unique_id_short}_{measurement.name}.{ext}'

        self.settings.New(
            "inspect file",
            dtype="file",
            description="right click on setting widget to see and load value from a file",
        ).add_listener(self.propose_settings_values_from_file)

        # self.settings.New('log_dir', dtype='file', is_dir=True, initial=initial_log_dir)

        if not hasattr(self, "ui_filename"):
            if self.mdi:
                self.ui_filename = sibling_path(__file__, "base_microscope_app_mdi.ui")
            else:
                self.ui_filename = sibling_path(__file__, "base_microscope_app.ui")
        # Load Qt UI from .ui file
        self.ui = load_qt_ui_file(self.ui_filename)
        if self.mdi:
            self.ui.col_splitter.setStretchFactor(0, 0)
            self.ui.col_splitter.setStretchFactor(1, 1)

        self.hardware = OrderedAttrDict()
        self.measurements = OrderedAttrDict()

        self.quickbar = None

        self.setup()

        self.setup_settings_paths()

        self.setup_default_ui()

        self.setup_ui()

    def setup_default_ui(self):
        self.ui.show()
        self.ui.activateWindow()

        """Loads various default features into the user interface upon app startup."""
        confirm_on_close(
            self.ui,
            title="Close %s?" % self.name,
            message="Do you wish to shut down %s?" % self.name,
            func_on_close=self.on_close,
        )

        # Hardware and Measurement Settings Trees
        self.ui.hardware_treeWidget.setColumnWidth(0, 175)
        self.ui.measurements_treeWidget.setColumnWidth(0, 175)

        self.ui.measurements_treeWidget.setContextMenuPolicy(
            QtCore.Qt.CustomContextMenu
        )
        self.ui.measurements_treeWidget.customContextMenuRequested.connect(
            self.on_measure_tree_context_menu
        )

        self.ui.hardware_treeWidget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.ui.hardware_treeWidget.customContextMenuRequested.connect(
            self.on_hardware_tree_context_menu
        )

        for name, hw in self.hardware.items():
            hw.add_widgets_to_tree(tree=self.ui.hardware_treeWidget)

        for name, measure in self.measurements.items():
            measure.add_widgets_to_tree(tree=self.ui.measurements_treeWidget)

        # Add log widget to mdiArea
        self.logging_subwin = self.add_mdi_subwin(self.logging_widget, "Log")
        self.console_subwin = self.add_mdi_subwin(self.console_widget, "Console")

        # Setup the Measurement UI's
        for name, measure in self.measurements.items():
            self.log.info(
                "setting up figures for {} measurement {}".format(name, measure.name)
            )
            measure.setup_figure()
            if self.mdi and hasattr(measure, "ui"):
                subwin = self.add_mdi_subwin(measure.ui, measure.name)
                measure.subwin = subwin

        if hasattr(self.ui, "console_pushButton"):
            self.ui.console_pushButton.clicked.connect(self.console_widget.show)
            self.ui.console_pushButton.clicked.connect(
                self.console_widget.activateWindow
            )

        if self.quickbar is None:
            # Collapse sidebar
            self.ui.quickaccess_scrollArea.setVisible(False)

        # Save Dir events
        self.ui.action_set_data_dir.triggered.connect(
            self.settings.save_dir.file_browser
        )
        self.settings.save_dir.connect_to_browse_widgets(
            self.ui.save_dir_lineEdit, self.ui.save_dir_browse_pushButton
        )

        # Sample meta data
        self.settings.sample.connect_to_widget(self.ui.sample_lineEdit)

        # settings button events
        if hasattr(self.ui, "settings_autosave_pushButton"):
            self.ui.settings_autosave_pushButton.clicked.connect(
                self.settings_auto_save_ini
            )
        if hasattr(self.ui, "settings_load_last_pushButton"):
            self.ui.settings_load_last_pushButton.clicked.connect(
                self.settings_load_last
            )
        if hasattr(self.ui, "settings_save_pushButton"):
            self.ui.settings_save_pushButton.clicked.connect(self.settings_save_dialog)
        if hasattr(self.ui, "settings_load_pushButton"):
            self.ui.settings_load_pushButton.clicked.connect(self.settings_load_dialog)

        # Menu bar entries:
        # TODO: connect self.ui.action_log_viewer to log viewer function
        # (Function has yet to be created)
        self.ui.action_load_ini.triggered.connect(self.settings_load_dialog)
        self.ui.action_auto_save_ini.triggered.connect(self.settings_auto_save_ini)
        self.ui.action_save_ini.triggered.connect(self.settings_save_dialog)
        self.ui.action_console.triggered.connect(self.console_widget.show)
        self.ui.action_console.triggered.connect(self.console_widget.activateWindow)
        self.ui.action_load_window_positions.triggered.connect(
            self.window_positions_load_dialog
        )
        self.ui.action_save_window_positions.triggered.connect(
            self.window_positions_save_dialog
        )

        # Refer to existing ui object:
        self.menubar = self.ui.menuWindow

        # Create new action group for switching between window and tab mode
        self.action_group = QtWidgets.QActionGroup(self)
        # Add actions to group:
        self.action_group.addAction(self.ui.window_action)
        self.action_group.addAction(self.ui.tab_action)

        self.ui.mdiArea.setTabsClosable(False)
        self.ui.mdiArea.setTabsMovable(True)

        self.ui.tab_action.triggered.connect(self.set_tab_mode)
        self.ui.window_action.triggered.connect(self.set_subwindow_mode)
        self.ui.cascade_action.triggered.connect(self.cascade_layout)
        self.ui.tile_action.triggered.connect(self.tile_layout)

        self.ui.setWindowTitle(self.name)

        # Set Icon
        logo_icon = QtGui.QIcon(sibling_path(__file__, "scopefoundry_logo2B_1024.png"))
        self.qtapp.setWindowIcon(logo_icon)
        self.ui.setWindowIcon(logo_icon)

        ### parameter tree
        ## disabled for now
        """
        import pyqtgraph.parametertree.parameterTypes as pTypes
        from pyqtgraph.parametertree import Parameter, ParameterTree, ParameterItem, registerParameterType

        self.ptree = ParameterTree()
        p = Parameter.create(name='Settings', type='group')

        app_params = Parameter.create(name='App', type='group')
        for lq_name, lq in self.settings.as_dict().items():
            print(lq_name, lq)
            lq_p = lq.new_pg_parameter()#Parameter.create(name=lq.name, type=lq.dtype)
            app_params.addChild(lq_p)

        p.addChild(app_params)



        hw_params = Parameter.create(name='Hardware', type='group')
        p.addChild(hw_params)

        for name, measure in self.hardware.items():
            hw_group = Parameter.create(name=name, type='group')
            hw_params.addChild(hw_group)
            for lq_name, lq in measure.settings.as_dict().items():
                print(lq_name, lq)
                lq_p = lq.new_pg_parameter()
                hw_group.addChild(lq_p)

        measure_params = Parameter.create(name='Measurements', type='group')
        p.addChild(measure_params)

        for name, measure in self.measurements.items():
            m_group = Parameter.create(name=name, type='group')
            measure_params.addChild(m_group)
            for lq_name, lq in measure.settings.as_dict().items():
                print(lq_name, lq)
                lq_p = lq.new_pg_parameter()
                m_group.addChild(lq_p)


        self.ptree.setParameters(p, showTop=True)
        #self.ptree.show()
        """

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
        self.bring_mdi_subwin_to_front(measure.subwin)

    def bring_mdi_subwin_to_front(self, subwin):
        viewMode = self.ui.mdiArea.viewMode()
        if viewMode == self.ui.mdiArea.SubWindowView:
            subwin.showNormal()
            subwin.raise_()
        elif viewMode == self.ui.mdiArea.TabbedView:
            subwin.showMaximized()
            subwin.raise_()

    def add_mdi_subwin(self, widget, name):
        subwin = self.ui.mdiArea.addSubWindow(
            widget, QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowMinMaxButtonsHint
        )
        ignore_on_close(subwin)
        subwin.setWindowTitle(name)
        subwin.show()
        self.ui.menuWindow.addAction(
            name, lambda subwin=subwin: self.bring_mdi_subwin_to_front(subwin)
        )
        return subwin

    def add_quickbar(self, widget):
        self.ui.quickaccess_scrollArea.setVisible(True)
        self.ui.quickaccess_scrollAreaWidgetContents.layout().addWidget(widget)
        self.quickbar = widget
        return self.quickbar

    def on_close(self):
        self.log.info("on_close")
        # disconnect all hardware objects
        for hw in self.hardware.values():
            self.log.info("disconnecting {}".format(hw.name))
            if hw.settings["connected"]:
                try:
                    hw.disconnect()
                except Exception as err:
                    self.log.error("tried to disconnect {}: {}".format(hw.name, err))

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
            H.settings["connected"] = True
        elif action == disconnect_action:
            H.settings["connected"] = False

    def setup(self):
        """Override to add Hardware and Measurement Components"""
        # raise NotImplementedError()
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

    def setup_ui(self):
        """Override to set up ui elements after default ui is built"""
        pass

    def add_pg_graphics_layout(self, name, widget):
        self.log.info("---adding pg GraphicsLayout figure {} {}".format(name, widget))
        if name in self.figs:
            return self.figs[name]
        else:
            disp = pg.GraphicsLayoutWidget(border=(100, 100, 100))
            widget.layout().addWidget(disp)
            self.figs[name] = disp
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

    def add_figure(self, name, widget):
        # DEPRECATED
        return self.add_figure_mpl(name, widget)

    def add_hardware(self, hw):
        """Loads a HardwareComponent object into the app.

        If *hw* is a class, rather an instance, create an instance
        and add it to self.hardware
        """
        assert not hw.name in self.hardware.keys()

        # If *hw* is a class, rather an instance, create an instance
        if inspect.isclass(hw):
            hw = hw(app=self)

        self.hardware.add(hw.name, hw)

        return hw

    def add_hardware_component(self, hw):
        # DEPRECATED use add_hardware()
        return self.add_hardware(hw)

    def add_measurement(self, measure):
        """Loads a Measurement object into the app.

        If *measure* is a class, rather an instance, create an instance
        and add it to self.measurements

        """
        # If *measure* is a class, rather an instance, create an instance
        if inspect.isclass(measure):
            measure = measure(app=self)

        assert not measure.name in self.measurements.keys()

        self.measurements.add(measure.name, measure)

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
        with h5_io.h5_base_file(self, fname) as h5_file:
            for measurement in self.measurements.values():
                h5_io.h5_create_measurement_group(measurement, h5_file)
            self.log.info("settings saved to {}".format(h5_file.filename))

    def settings_save_ini(
        self,
        fname,
        save_ro=True,
        save_app=True,
        save_hardware=True,
        save_measurements=True,
    ):
        """
        ==============  =========  ==============================================
        **Arguments:**  **Type:**  **Description:**
        fname           str        relative path to the filename of the ini file.
        ==============  =========  ==============================================
        """
        exclude_patterns = []
        if not save_app:
            exclude_patterns.append("app")
        if not save_hardware:
            exclude_patterns.append("measurement")
        if not save_measurements:
            exclude_patterns.append("hardware")
        paths = self.get_setting_paths(exclude_patterns, exclude_ro=not save_ro)

        settings = self.read_settings(paths, ini_string_value=True)
        ini_io.save_settings(fname, settings)

        self.propose_settings_values(Path(fname).name, settings)

        self.log.info(f"ini settings saved to {fname} str")

    def settings_load_ini(self, fname, ignore_hw_connect=False):
        """
        ==============  =========  ==============================================
        **Arguments:**  **Type:**  **Description:**
        fname           str        relative path to the filename of the ini file.
        ==============  =========  ==============================================
        """
        settings = ini_io.load_settings(fname)
        if not ignore_hw_connect:
            self.write_settings_safe(
                {k: v for k, v in settings.items() if k.endswith("connected")}
            )
        self.write_settings_safe(
            {k: v for k, v in settings.items() if not k.endswith("connected")}
        )
        self.propose_settings_values(Path(fname).name, settings)

    def settings_load_h5(self, fname, ignore_hw_connect=False):
        """
        Loads h5 settings given a filename.

        ==============  =========  ====================================================================================
        **Arguments:**  **Type:**  **Description:**
        fname           str        relative path to the filename of the h5 file.
        ==============  =========  ====================================================================================
        """
        settings = h5_io.load_settings(fname)
        if not ignore_hw_connect:
            self.write_settings_safe(
                {k: v for k, v in settings.items() if k.endswith("connected")}
            )
        self.write_settings_safe(
            {k: v for k, v in settings.items() if not k.endswith("connected")}
        )
        self.propose_settings_values(Path(fname).name, settings)

    def settings_auto_save_ini(self):
        """
        Saves the ini file to app/save_dir directory with a time stamp in the filename.
        """
        fname = (
            Path(self.settings["save_dir"])
            / f"{datetime.datetime.now():%y%m%d_%H%M%S}_settings.ini"
        )
        self.settings_save_ini(fname)

    def settings_load_last(self):
        """
        Loads last saved ini file.
        """
        fnames = Path.cwd().glob("*_settings.ini")
        fnames.extend(Path(self.settings["save_dir"]).glob("*_settings.ini"))
        self.settings_load_ini(sorted(fnames)[-1])

    def settings_save_dialog(self):
        """Opens a save as ini dialogue in the app user interface."""
        fname, selectedFilter = QtWidgets.QFileDialog.getSaveFileName(
            self.ui, "Save Settings file", "", "Settings File (*.ini)"
        )
        if fname:
            self.settings_save_ini(fname)

    def settings_load_dialog(self):
        """Opens a load ini dialogue in the app user interface"""
        fname, selectedFilter = QtWidgets.QFileDialog.getOpenFileName(
            self.ui, "Open Settings file", "", "Settings File (*.ini *.h5)"
        )
        if fname.endswith(".ini"):
            self.settings_load_ini(fname)
        elif fname.endswith(".h5"):
            self.settings_load_h5(fname)

    def window_positions_load_dialog(self):
        fname, selectedFilter = QtWidgets.QFileDialog.getOpenFileName(
            self.ui, "Open Window Position file", "", "position File (*.json)"
        )
        self.load_window_positions_json(fname)

    def window_positions_save_dialog(self):
        """Opens a save as ini dialogue in the app user interface."""
        fname, selectedFilter = QtWidgets.QFileDialog.getSaveFileName(
            self.ui, "Save Window Position file", "", "position File (*.json)"
        )
        if fname:
            self.save_window_positions_json(fname)

    def get_lq(self, path: str) -> LoggedQuantity:
        """
        returns the LoggedQuantity defined by a path string of the form 'section/[component/]setting'
        where section are "mm", "hw" or "app"
        """
        parts = path.split("/")
        section = parts[0]
        if section in ("HW", "hardware"):
            path = f"hw/{parts[1]}/{parts[2]}"
        elif section in ("measurement", "measure", "measurements"):
            path = f"mm/{parts[1]}/{parts[2]}"
        if not path in self._setting_paths:
            print(f"WARNING: {'/'.join(parts)} does not exist")
        else:
            return self._setting_paths[path]

    def write_setting(self, path: str, value):
        self.get_lq(path).update_value(value)

    def write_setting_safe(self, path: str, value):
        lq = self.get_lq(path)
        if lq is None or lq.protected:
            return
        lq.update_value(value)

    def write_settings_safe(self, settings):
        """
        updates settings based on a dictionary, silently ignores protected logged quantities and non-existing.

        ==============  =========  ====================================================================================
        **Arguments:**  **Type:**  **Description:**
        settings        dict       (path, value) map
        ==============  =========  ====================================================================================
        """
        for path, value in settings.items():
            self.write_setting_safe(path, value)

    def read_setting(self, path: str, read_from_hardware=True, ini_string_value=False):
        lq = self.get_lq(path)
        if read_from_hardware and lq.has_hardware_read:
            lq.read_from_hardware()
        if ini_string_value:
            return lq.ini_string_value()
        return lq.val

    def setup_settings_paths(self):
        for hw_name, hw in self.hardware.items():
            self.add_lq_collection_to_settings_path(hw.settings)
        for mm_name, mm in self.measurements.items():
            self.add_lq_collection_to_settings_path(mm.settings)
        self.add_lq_collection_to_settings_path(self.settings)

    def add_lq_collection_to_settings_path(self, settings: LQCollection):
        settings.q_object.new_lq_added.connect(self.add_setting_path)
        settings.q_object.lq_removed.connect(self.remove_setting_path)
        for lq in settings.as_dict().values():
            self.add_setting_path(lq)

    def add_setting_path(self, lq: LoggedQuantity):
        self._setting_paths[lq.path] = lq

    def remove_setting_path(self, lq: LoggedQuantity):
        if lq.path in self._setting_paths:
            path = lq.path
        self._setting_paths.pop(path)

    def get_setting_paths(
        self,
        filter_has_hardware_read=False,
        filter_has_hardware_write=False,
        exclude_patterns=None,
        exclude_ro=False,
    ):
        if filter_has_hardware_read and filter_has_hardware_write:
            paths = (
                path
                for path, lq in self._setting_paths.items()
                if lq.has_hardware_read() or lq.has_hardware_write()
            )
        elif filter_has_hardware_read:
            paths = (
                path
                for path, lq in self._setting_paths.items()
                if lq.has_hardware_read()
            )
        elif filter_has_hardware_write:
            paths = (
                path
                for path, lq in self._setting_paths.items()
                if lq.has_hardware_write()
            )
        else:
            paths = self._setting_paths.keys()
        if exclude_ro:
            ro_paths = [path for path in paths if self.get_lq(path).ro]
            exclude_patterns = (
                ro_paths if not exclude_patterns else list(exclude_patterns) + ro_paths
            )
        if exclude_patterns:
            paths = (
                path
                for path in paths
                if not any(pattern in path for pattern in exclude_patterns)
            )
        return list(paths)

    def read_settings(
        self, paths=None, read_from_hardware=False, ini_string_value=False
    ):
        """returns a dictionary (path, value):
        ================== =========  =============================================================================
        **Arguments:**     **Type:**  **Description:**
        paths              list[str]  paths to setting, if None(default) all paths are used
        read_from_hardware bool       if True, values are read from hardware, else the current value is used
        ================== =========  =============================================================================
        """
        paths = self.get_setting_paths() if paths is None else paths
        return {
            p: self.read_setting(p, read_from_hardware, ini_string_value) for p in paths
        }

    def lq_path(self, path):
        warnings.warn(
            "App.lq_path deprecated, use App.get_lq instead", DeprecationWarning
        )
        return self.get_lq(path)

    def lq_paths_list(self):
        warnings.warn(
            "App.lq_paths_list deprecated, use App.get_setting_paths instead",
            DeprecationWarning,
        )
        return self.get_setting_paths()

    @property
    def hardware_components(self):
        warnings.warn(
            "App.hardware_components deprecated, used App.hardware", DeprecationWarning
        )
        return self.hardware

    @property
    def measurement_components(self):
        warnings.warn(
            "App.measurement_components deprecated, used App.measurements",
            DeprecationWarning,
        )
        return self.measurements

    @property
    def logged_quantities(self):
        warnings.warn(
            "app.logged_quantities deprecated use app.settings", DeprecationWarning
        )
        return self.settings.as_dict()

    def set_window_positions(self, positions):
        def restore_win_state(subwin, win_state):
            subwin.showNormal()
            if win_state["maximized"]:
                subwin.showMaximized()
            elif win_state["minimized"]:
                subwin.showMinimized()
            else:
                subwin.setGeometry(*win_state["geometry"])

        self.set_subwindow_mode()
        for name, win_state in positions.items():
            if name == "log":
                restore_win_state(self.logging_subwin, win_state)
            elif name == "console":
                restore_win_state(self.console_subwin, win_state)
            elif name == "main":
                restore_win_state(self.ui, win_state)
                self.ui.col_splitter.setSizes(win_state["col_splitter_sizes"])
            elif name.startswith("measurement/"):
                M = self.measurements[name.split("/")[-1]]
                restore_win_state(M.subwin, win_state)

    def get_window_positions(self):
        positions = OrderedDict()

        def qrect_to_tuple(qr):
            return (qr.x(), qr.y(), qr.width(), qr.height())

        def win_state_from_subwin(subwin):
            window_state = dict(
                geometry=qrect_to_tuple(subwin.geometry()),
                maximized=subwin.isMaximized(),
                minimized=subwin.isMinimized(),
                fullscreen=subwin.isFullScreen(),
            )
            return window_state

        positions["main"] = win_state_from_subwin(self.ui)
        positions["main"]["col_splitter_sizes"] = self.ui.col_splitter.sizes()

        positions["log"] = win_state_from_subwin(self.logging_subwin)
        positions["console"] = win_state_from_subwin(self.console_subwin)

        for name, M in self.measurements.items():
            if hasattr(M, "ui"):
                positions["measurement/" + name] = win_state_from_subwin(M.subwin)

        return positions

    def save_window_positions_json(self, fname):
        positions = self.get_window_positions()
        with open(fname, "w") as outfile:
            json.dump(positions, outfile, indent=4)

    def load_window_positions_json(self, fname):
        with open(fname, "r") as infile:
            positions = json.load(infile)
        self.set_window_positions(positions)

    def generate_data_path(self, measurement, ext, t=None):
        if t is None:
            t = time.time()
        f = self.settings["data_fname_format"].format(
            app=self,
            measurement=measurement,
            timestamp=datetime.datetime.fromtimestamp(t),
            ext=ext,
        )
        return Path(self.settings["save_dir"]) / f

    def propose_settings_values_from_file(self, fname=None):
        """
        Adds to proposed_values of LQs.
        proposed_values can be inspected with right click corresponding widget
        """
        if fname is None:
            fname = self.settings["inspect file"]
        fname = Path(fname)
        ext = fname.suffix
        if fname.exists() and ext in (".ini", ".h5"):
            if ext == ".ini":
                settings = ini_io.load_settings(fname)
            elif ext == ".h5":
                settings = h5_io.load_settings(fname)
            self.propose_settings_values(fname.name, settings)

    def propose_settings_values(self, name, settings):
        """
        Adds to proposed_values of LQs.
        proposed_values can be inspected with right click corresponding widget
        """
        for path, val in settings.items():
            lq = self.get_lq(path)
            if lq is None:
                continue
            lq.propose_value(name, val)
