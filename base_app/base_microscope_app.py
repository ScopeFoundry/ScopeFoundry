import datetime
import inspect
import json
import logging
import os
import time
import warnings
from collections import OrderedDict
from functools import partial
from pathlib import Path

from qtpy import QtCore, QtGui, QtWidgets

from ScopeFoundry import h5_io, ini_io
from ScopeFoundry.dynamical_widgets import new_tree_widget, new_widget
from ScopeFoundry.h5_analyze_with_ipynb import generate_ipynb, generate_loaders_py
from ScopeFoundry.helper_funcs import (
    OrderedAttrDict,
    confirm_on_close,
    find_matches,
    ignore_on_close,
    load_qt_ui_file,
    sibling_path,
)
from ScopeFoundry.logged_quantity import LoggedQuantity

from .base_app import BaseApp
from .logging_handlers import StatusBarHandler, new_log_file_handler
from .show_io_report_dialog import show_io_report_dialog

THIS_PATH = Path(__file__).parent
APP_WIDGET_STYLESHEET = """ QGroupBox { border: 2px dashed blue; border-radius: 2px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 3px; } """

class BaseMicroscopeApp(BaseApp):
    name = "ScopeFoundry"
    """The name of the microscope app, default is ScopeFoundry."""
    mdi = True
    """Multiple Document Interface flag. Tells the app whether to include an MDI widget in the app."""

    def __init__(self, argv=[], **kwargs):
        super().__init__(argv, **kwargs)

        self.settings_icon = str(THIS_PATH / "settings.png")
        self.jupyter_logo_path = str(THIS_PATH / "Jupyter_logo.png")

        self._setup_log_file_handler()
        self._setup_settings_operations(**kwargs)

        # objects to overwrite and populate with setup function.
        self.hardware = OrderedAttrDict()
        self.measurements = OrderedAttrDict()
        self.logo_path = str(THIS_PATH / "scopefoundry_logo2B_1024.png")
        self.quickbar = None  # also with self.add_quickbar
        self.setup()

        self._setup_ui_base()
        self._setup_ui_buttons()
        self._setup_ui_tree_column()
        if self.mdi:
            self._setup_ui_mdi_area()
        self._setup_ui_menu_bar()
        self.setup_ui()  # child may overrite
        self._post_setup_ui_quickaccess()
        self._setup_ui_logo()

    def setup(self):
        """Override to add Hardware and Measurement Components"""
        pass

    def setup_ui(self):
        """Optional Override to set up ui elements after default ui is built"""
        pass

    def _setup_settings_operations(self, **kwargs):
        initial_save_path = Path.cwd() / "data"
        if not initial_save_path.is_dir():
            initial_save_path.mkdir()
        self.settings.New(
            "save_dir", dtype="file", is_dir=True, initial=initial_save_path.as_posix()
        )
        self.settings.New("sample", dtype=str, initial="")
        self.settings.New(
            name="data_fname_format",
            dtype=str,
            initial="{timestamp:%y%m%d_%H%M%S}_{measurement.name}.{ext}",
        )
        # Potential new alternative default: '{unique_id_short}_{measurement.name}.{ext}'

        self.settings.New(
            name="propose_from_file",
            dtype="file",
            description="right click on setting widget to see and load value from a file",
            file_filters=["Settings (*.ini *.h5)"],
        ).add_listener(self.propose_settings_values_from_file)

        # self.settings.New('log_dir', dtype='file', is_dir=True, initial=initial_log_dir)

        self.setup_dark_mode_option(dark_mode=kwargs.get("dark_mode", None))
        self.add_operation(
            "analyze with ipynb",
            self.on_analyze_with_ipynb,
            "generates h5_data_loaders.py, overview.ipynb, and tries to launch overview.ipynb (vscode with jupyter extension recommended)",
            self.jupyter_logo_path,
        )

    def _setup_log_file_handler(self):
        log_path = Path.cwd() / "log"
        if not log_path.is_dir():
            log_path.mkdir()
        _fname = f"{self.name}_log_{datetime.datetime.now():%y%m%d_%H%M%S}.txt"
        self.log_file_handler = new_log_file_handler(log_path / _fname)
        logging.getLogger().addHandler(self.log_file_handler)

    def _setup_ui_base(self):
        """gets called before setup gets called. Could probabliy be called after but this might"""
        if not hasattr(self, "ui_filename"):
            self.ui_filename = sibling_path(__file__, "base_microscope_app_mdi.ui")

        self.ui = load_qt_ui_file(self.ui_filename)
        self.ui.mdiArea.setVisible(self.mdi)
        self.ui.quickaccess_scrollArea.setVisible(self.mdi)

        if self.mdi:
            self.ui.col_splitter.setStretchFactor(0, 0)
            self.ui.col_splitter.setStretchFactor(1, 1)

        self._loaded_measure_uis = {}

        self.ui.show()
        self.ui.activateWindow()

        confirm_on_close(
            widget=self.ui,
            title=f"Close {self.name}?",
            message=f"Do you wish to shut down {self.name}",
            func_on_close=self.on_close,
        )
        handler = StatusBarHandler(logging.INFO, self.show_status_bar_msg)
        self.log.addHandler(handler)

    def show_status_bar_msg(self, msg, timeout=2000):
        self.ui.statusbar.showMessage(msg, timeout)

    def _setup_ui_buttons(self):
        # since v 1.6 no longer required if default .ui is used.
        if hasattr(self.ui, "console_pushButton"):
            self.ui.console_pushButton.clicked.connect(self.console_widget.show)
            self.ui.console_pushButton.clicked.connect(
                self.console_widget.activateWindow
            )
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

    def _setup_ui_tree_column(self):

        mm_tree = new_tree_widget(self.measurements.values(), ["Measurements", "Value"])
        hw_tree = new_tree_widget(self.hardware.values(), ["Hardware", "Value"])
        app_widget = new_widget(
            obj=self,
            title="app",
            style="form",
            include=("save_dir", "sample"),
        )

        app_widget.setAcceptDrops(True)
        app_widget.dragEnterEvent = self.on_drag_on_app_widget
        app_widget.dropEvent = self.on_drop_on_app_widget

        app_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Maximum,
        )
        ipynb_btn = self.operations.new_button("analyze with ipynb")
        ipynb_btn.setText(" analyze")
        settings_btn = QtWidgets.QPushButton(" settings")
        settings_btn.clicked.connect(self.show_app_settings)
        settings_btn.setIcon(QtGui.QIcon(self.settings_icon))
        app_widget_btns_layout = QtWidgets.QHBoxLayout()
        app_widget_btns_layout.addWidget(ipynb_btn)
        app_widget_btns_layout.addWidget(settings_btn)
        app_widget.layout().addLayout(app_widget_btns_layout)
        # trying to indicate that one can drop file on this app
        app_widget.setStyleSheet(APP_WIDGET_STYLESHEET)
        app_widget.setTitle("to inspect drop a .h5 or .ini, to load also press ctrl")

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        splitter.addWidget(hw_tree)
        splitter.addWidget(mm_tree)
        splitter.addWidget(app_widget)
        self.ui.tree_layout.addWidget(splitter)

    def _setup_ui_mdi_area(self):
        self.ui.mdiArea.setTabsClosable(False)
        self.ui.mdiArea.setTabsMovable(True)

        self.logging_subwin = self.add_mdi_subwin(self.logging_widget, "Log")
        self.console_subwin = self.add_mdi_subwin(self.console_widget, "Console")

        for name, measure in self.measurements.items():
            self.log.debug(f"setting up figure for measurement {name}")
            ui = self.load_measure_ui(measure)
            if ui is not None:
                subwin = self.add_mdi_subwin(ui, measure.name)
                measure.subwin = subwin

    def _load_all_measure_uis(self):
        for measure in self.measurements.values():
            self.load_measure_ui(measure)
        self.ui.action_load_all_measure_uis.setVisible(False)

    def _setup_ui_menu_bar(self):
        self.ui.action_set_data_dir.triggered.connect(
            self.settings.save_dir.file_browser
        )
        self.ui.action_load_ini.triggered.connect(self.settings_load_dialog)
        self.ui.action_auto_save_ini.triggered.connect(self.settings_auto_save_ini)
        self.ui.action_save_ini.triggered.connect(self.settings_save_dialog)
        self.ui.action_load_last.triggered.connect(self.settings_load_last)
        if self.mdi:
            self.ui.action_console.triggered.connect(
                partial(self.bring_mdi_subwin_to_front, subwin=self.console_subwin)
            )
            self.ui.action_log_viewer.triggered.connect(
                partial(self.bring_mdi_subwin_to_front, subwin=self.logging_subwin)
            )
        else:
            self.ui.action_console.triggered.connect(self.console_widget.show)
            self.ui.action_log_viewer.triggered.connect(self.logging_widget.show)
        self.ui.action_console.setIcon(self.console_widget.windowIcon())
        self.ui.action_log_viewer.setIcon(self.logging_widget.windowIcon())
        self.ui.action_propose_from_file.triggered.connect(
            self.settings.get_lq("propose_from_file").file_browser
        )

        self.ui.action_show_settings.triggered.connect(self.show_app_settings)
        self.ui.action_show_settings.setIcon(QtGui.QIcon(self.settings_icon))
        self.ui.action_analyze_with_ipynb.triggered.connect(
            partial(self.on_analyze_with_ipynb, folder=None)
        )
        self.ui.action_analyze_with_ipynb.setIcon(QtGui.QIcon(self.jupyter_logo_path))

        self.ui.action_docs.triggered.connect(
            partial(
                self.launch_browser, url="https://www.scopefoundry.org/#documentation"
            )
        )
        self.ui.action_about.triggered.connect(self.on_about)
        # Refer to existing ui object:
        self.menubar = self.ui.menuWindow

        if self.mdi:
            self.ui.tab_action.triggered.connect(self.set_tab_mode)
            self.ui.window_action.triggered.connect(self.set_subwindow_mode)
            self.ui.cascade_action.triggered.connect(self.cascade_layout)
            self.ui.tile_action.triggered.connect(self.tile_layout)
            self.ui.action_load_window_positions.triggered.connect(
                self.window_positions_load_dialog
            )
            self.ui.action_save_window_positions.triggered.connect(
                self.window_positions_save_dialog
            )
            self.ui.action_load_all_measure_uis.setVisible(False)
        else:
            self.ui.tab_action.setVisible(False)
            self.ui.window_action.setVisible(False)
            self.ui.cascade_action.setVisible(False)
            self.ui.tile_action.setVisible(False)
            self.ui.action_load_window_positions.setVisible(False)
            self.ui.action_save_window_positions.setVisible(False)
            self.ui.action_load_all_measure_uis.triggered.connect(
                self._load_all_measure_uis
            )

    def _post_setup_ui_quickaccess(self):
        # check again if quickbar is defined.
        if isinstance(self.quickbar, QtWidgets.QWidget):
            self.ui.quickaccess_scrollArea.setVisible(True)
            layout: QtWidgets.QVBoxLayout = self.ui.quickaccess_layout
            if layout.isEmpty():
                layout.addWidget(self.quickbar)
        else:
            self.ui.quickaccess_scrollArea.setVisible(False)

    def _setup_ui_logo(self):
        logo_icon = QtGui.QIcon(self.logo_path)
        self.qtapp.setWindowIcon(logo_icon)
        self.ui.setWindowIcon(logo_icon)
        self.ui.setWindowTitle(self.name)

    def show(self):
        """Tells Qt to show the user interface"""
        # self.ui.exec_()
        self.ui.show()

    def __del__(self):
        self.ui = None

    def set_subwindow_mode(self):
        """Switches Multiple Document Interface to Subwindowed viewing mode."""
        self.ui.mdiArea.setViewMode(QtWidgets.QMdiArea.ViewMode.SubWindowView)

    def set_tab_mode(self):
        """Switches Multiple Document Interface to Tabbed viewing mode."""
        self.ui.mdiArea.setViewMode(QtWidgets.QMdiArea.ViewMode.TabbedView)

    def tile_layout(self):
        """Tiles subwindows in user interface. Specifically in the Multi Document Interface."""
        self.set_subwindow_mode()
        self.ui.mdiArea.tileSubWindows()

    def cascade_layout(self):
        """Cascades subwindows in user interface. Specifically in the Multi Document Interface."""
        self.set_subwindow_mode()
        self.ui.mdiArea.cascadeSubWindows()

    def bring_measure_ui_to_front(self, measure):
        ui = self._loaded_measure_uis.get(measure.name, None)
        if ui is None:
            # measure also has no subwin
            return
        if self.mdi:
            self.bring_mdi_subwin_to_front(measure.subwin)
        else:
            ui.show()

    def load_measure_ui(self, measure):
        if measure.name in self._loaded_measure_uis:
            return self._loaded_measure_uis[measure.name]

        measure.setup_figure()
        if not hasattr(measure, "ui"):
            self._loaded_measure_uis[measure.name] = None
            return None

        self._loaded_measure_uis[measure.name] = measure.ui
        measure.ui.setWindowTitle(measure.name)
        self.ui.menuWindow.addAction(measure.name, measure.show_ui)
        return measure.ui

    def bring_mdi_subwin_to_front(self, subwin):
        view_mode = self.ui.mdiArea.viewMode()
        if view_mode == QtWidgets.QMdiArea.ViewMode.SubWindowView:
            subwin.showNormal()
            subwin.raise_()
        elif view_mode == QtWidgets.QMdiArea.ViewMode.TabbedView:
            subwin.showMaximized()
            subwin.raise_()

    def add_mdi_subwin(self, widget: QtWidgets.QWidget, name):
        mdiArea: QtWidgets.QMdiArea = self.ui.mdiArea
        subwin = mdiArea.addSubWindow(
            widget,
            QtCore.Qt.WindowType.CustomizeWindowHint
            | QtCore.Qt.WindowType.WindowTitleHint
            | QtCore.Qt.WindowType.WindowMinMaxButtonsHint,
        )
        ignore_on_close(subwin)
        subwin.setWindowTitle(name)
        subwin.setWindowIcon(widget.windowIcon())
        subwin.show()
        widget.setAcceptDrops(True)
        widget.dragEnterEvent = self.on_drag_on_app_widget
        widget.dropEvent = self.on_drop_on_app_widget

        return subwin

    def add_quickbar(self, widget):
        self.ui.quickaccess_scrollArea.setVisible(True)
        self.ui.quickaccess_layout.addWidget(widget)
        self.quickbar = widget
        return self.quickbar

    def on_close(self):
        self.log.info("on_close")
        # disconnect all hardware objects
        for hw in self.hardware.values():
            self.log.info("disconnecting {}".format(hw.name))
            try:
                hw.settings["connected"] = False
                hw.settings.disconnect_all_from_hardware()
            except Exception as err:
                self.log.error("tried to disconnect {}: {}".format(hw.name, err))

    def on_analyze_with_ipynb(self, folder=None):
        if folder is None:
            folder = self.settings["save_dir"]
        loaders_fname, dset_names = generate_loaders_py(folder)
        ipynb_path = generate_ipynb(folder)
        print("")
        print("generated", loaders_fname, f"with {len(dset_names)} loader(s)")
        print("")
        print("check", ipynb_path)
        print("")
        if ipynb_path.exists():
            os.startfile(ipynb_path)
        return ipynb_path

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

        self.add_lq_collection_to_settings_path(hw.settings)

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

        self.add_lq_collection_to_settings_path(measure.settings)

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
            self.log.info(f"settings saved to {fname}")

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

        self.log.info(f"settings saved to {fname}")

    def settings_load_file(self, fname: Path):
        fname = Path(fname)
        if fname.suffix == ".ini":
            self.settings_load_ini(fname)
        elif fname.suffix == ".h5":
            self.settings_load_h5(fname)

    def settings_load_ini(self, fname, ignore_hw_connect=False, show_report=True):
        """
        ==============  =========  ==============================================
        **Arguments:**  **Type:**  **Description:**
        fname           str        relative path to the filename of the ini file.
        ==============  =========  ==============================================
        """
        settings = ini_io.load_settings(fname)

        if ignore_hw_connect:
            settings = {
                k: v for k, v in settings.items() if not k.endswith("connected")
            }

        report = self.write_settings_safe(settings)
        self._report = report  # _report for test purpose

        if show_report:
            show_io_report_dialog(fname, report, self.settings_load_ini)

        self.propose_settings_values(Path(fname).name, settings)
        self.log.info(f"settings loaded from {fname}")

    def settings_load_h5(self, fname, ignore_hw_connect=False, show_report=True):
        """
        Loads h5 settings given a filename.

        ==============  =========  ====================================================================================
        **Arguments:**  **Type:**  **Description:**
        fname           str        relative path to the filename of the h5 file.
        ==============  =========  ====================================================================================
        """
        settings = h5_io.load_settings(fname)
        if ignore_hw_connect:
            settings = {
                k: v for k, v in settings.items() if not k.endswith("connected")
            }

        report = self.write_settings_safe(settings)
        self._report = report  # _report for test purpose

        if show_report:
            show_io_report_dialog(fname, report, self.settings_load_h5)

        self.propose_settings_values(Path(fname).name, settings)
        self.log.info(f"settings loaded from {fname}")

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
        fnames = list(Path.cwd().glob("*_settings.ini"))
        fnames += list(Path(self.settings["save_dir"]).glob("*_settings.ini"))
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
        self.settings_load_file(fname)

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
        return self._setting_paths.get(path, None)

    def read_setting(self, path: str, read_from_hardware=True, ini_string_value=False):
        lq = self.get_lq(path)
        if read_from_hardware and lq.has_hardware_read:
            lq.read_from_hardware()
        if ini_string_value:
            return lq.ini_string_value()
        return lq.val

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

        exclude_paths = []
        if exclude_ro:
            exclude_paths += [path for path in paths if self.get_lq(path).ro]
        if exclude_patterns is not None:
            exclude_paths += find_matches(paths, exclude_patterns)

        return [path for path in paths if path not in exclude_paths]

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
        """
        if fname is None:
            fname = self.settings["propose_from_file"]
        path = Path(fname)
        if not path.exists() or path.suffix not in (".ini", ".h5"):
            return
        if path.suffix == ".ini":
            settings = ini_io.load_settings(path)
        elif path.suffix == ".h5":
            settings = h5_io.load_settings(path)
        self.propose_settings_values(path.name, settings)

    def launch_browser(self, url):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))

    def on_about(self):

        # There must be a better way to extract the version
        version = ""
        with open(Path(__file__).parent.parent / "setup.py") as f:
            for l in f.readlines():
                if "version" in l:
                    import re

                    version = ".".join(re.findall(r"\d+", l))
                    break

        readme = QtWidgets.QTextEdit()
        with open(Path(__file__).parent.parent / "README.md") as f:
            readme.setMarkdown(
                f.read().replace("ScopeFoundry", f"ScopeFoundry {version}", 1)
            )

        dialog = QtWidgets.QDialog()
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(readme)
        dialog.setLayout(layout)
        dialog.exec_()

    def on_drag_on_app_widget(self, event: QtGui.QDragEnterEvent):
        if event.mimeData().hasUrls():
            fname = Path([u.toLocalFile() for u in event.mimeData().urls()][0])
            if fname.suffix in (".ini", ".h5"):
                if event.modifiers() == QtCore.Qt.KeyboardModifier.ControlModifier:
                    event.setDropAction(QtCore.Qt.DropAction.CopyAction)
                    self.show_status_bar_msg("drop to load settings")
                else:
                    event.setDropAction(QtCore.Qt.DropAction.LinkAction)
                    self.show_status_bar_msg(
                        "hold ctrl key to load settings - otherwise values are proposed only."
                    )
                event.accept()
                return
        event.ignore()

    def on_drop_on_app_widget(self, event: QtGui.QDropEvent):
        fname = Path([u.toLocalFile() for u in event.mimeData().urls()][0])
        if event.modifiers() == QtCore.Qt.KeyboardModifier.ControlModifier:
            self.settings_load_file(fname)
        else:
            self.propose_settings_values_from_file(fname)

    def show_app_settings(self):
        if not hasattr(self, "_app_settings_widget"):

            app_widget = new_widget(self, "app")
            app_widget.setAcceptDrops(True)
            app_widget.dragEnterEvent = self.on_drag_on_app_widget
            app_widget.dropEvent = self.on_drop_on_app_widget
            app_widget.setStyleSheet(APP_WIDGET_STYLESHEET)

            save_btn = QtWidgets.QPushButton("save ...")
            save_btn.clicked.connect(self.settings_save_dialog)
            load_btn = QtWidgets.QPushButton("load ...")
            load_btn.clicked.connect(self.settings_load_dialog)
            hlayout = QtWidgets.QHBoxLayout()
            hlayout.addWidget(save_btn)
            hlayout.addWidget(load_btn)

            widget = self._app_settings_widget = QtWidgets.QWidget()
            widget.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.MinimumExpanding,
                QtWidgets.QSizePolicy.Policy.MinimumExpanding,
            )
            widget.setWindowTitle("settings")
            widget.setWindowIcon(QtGui.QIcon(self.settings_icon))
            layout = QtWidgets.QVBoxLayout(widget)
            layout.addWidget(app_widget)
            layout.addLayout(hlayout)

        self._app_settings_widget.show()
