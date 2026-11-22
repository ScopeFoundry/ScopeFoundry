import argparse
from collections import OrderedDict
import os
from pathlib import Path
import threading

from qtpy import QtCore, QtWidgets, QtGui

from ScopeFoundry import BaseApp, LoggedQuantity
from ScopeFoundry.data_browser.data_browser_view import DataBrowserView
from ScopeFoundry.dynamical_widgets.tree_widget import new_tree_widget
from ScopeFoundry.helper_funcs import load_qt_ui_file, load_qt_ui_from_pkg, sibling_path
from ScopeFoundry.data_browser.viewers.file_info import FileInfoView


def _take_dir_snapshot(path: str):
    """Return a lightweight snapshot of directory entries, or None on error."""
    try:
        with os.scandir(path) as entries:
            return frozenset(
                (entry.name, entry.is_dir(follow_symlinks=False))
                for entry in entries
            )
    except OSError:
        return None


class DataBrowser(BaseApp):

    name = "DataBrowser"
    _dirs_changed = QtCore.Signal(list)

    def __init__(self, argv, dark_mode=None):
        BaseApp.__init__(self, argv)

        self.views = OrderedDict()
        self.view_stack_indices = {}

        self.plugin_update_funcs = []
        self.plugins = {}
        self.keys = {
            QtCore.Qt.Key_Delete: self.on_recycle,
        }
        self.ctrl_keys = {
            QtCore.Qt.Key_R: self.on_rename,
        }

        self._dir_snapshots = {}
        self._dir_snapshots_lock = threading.Lock()
        self._poll_in_progress = False
        self._refresh_stopped = False
        self._browse_gen = 0

        s = self.settings
        s.New("data_filename", dtype="file")
        s.New("browse_dir", dtype="file", is_dir=True, initial="/")
        s.New("file_filter", dtype=str, initial="*.*,")
        s.New(
            "auto_select_view",
            dtype=bool,
            initial=True,
            description="auto selects the view when file name is changed.",
        )
        s.New("view_name", dtype=str, initial="file_info", choices=("0",))
        s.New(
            "auto_refresh_interval",
            dtype=float,
            initial=2.0,
            unit="s",
            vmin=0.0,
            vmax=60.0,
            description="Polling interval (seconds) to detect added/removed files; 0 disables polling.",
        )

        self.setup_ui()

        self.current_view = self.add_view(FileInfoView(self))
        self.setup_view(self.current_view)

        # add callbacks
        s.data_filename.add_listener(self.on_change_data_filename)
        s.data_filename.add_listener(self.on_change_data_filename_handle_plugins)

        s.browse_dir.add_listener(self.on_change_browse_dir)
        s["browse_dir"] = Path.cwd()

        s.file_filter.add_listener(self.on_change_file_filter)
        s.view_name.add_listener(self.on_change_view_name)
        s.auto_refresh_interval.add_listener(self.on_change_auto_refresh_interval)

        self._dirs_changed.connect(
            self.refresh_file_list, QtCore.Qt.ConnectionType.QueuedConnection
        )
        self._refresh_timer = QtCore.QTimer(self)
        self._refresh_timer.timeout.connect(self._poll_watched_dirs)
        self.on_change_auto_refresh_interval()
        if self.qtapp is not None:
            self.qtapp.aboutToQuit.connect(self._stop_file_refresh)

        self.setup_dark_mode_option(dark_mode)

        self.setup()

        # Does this even work?
        parser = argparse.ArgumentParser()
        for lq in self.settings.as_list():
            parser.add_argument(f"--{lq.name}")
        args = parser.parse_args()
        for lq in self.settings.as_list():
            if lq.name in args:
                val = getattr(args, lq.name)
                if val is not None:
                    lq.update_value(val)

    def setup(self):
        """overite in child to add further views and plug_ins"""
        pass

    def setup_ui(self):
        self.ui = load_qt_ui_from_pkg("ScopeFoundry.data_browser", "data_browser.ui")

        self.ui.setWindowTitle("ScopeFoundry: Data Browser")

        logo_path = sibling_path(__file__, "logo.png")
        self.set_logo(logo_path)

        # file system tree
        self.tree_view = self.ui.treeView
        self.fs_model = QtWidgets.QFileSystemModel(self.ui)
        self.fs_model.setRootPath(QtCore.QDir.currentPath())
        self.tree_view.setModel(self.fs_model)
        self.tree_view.setIconSize(QtCore.QSize(16, 16))
        self.tree_view.setSortingEnabled(True)
        self.tree_view.setColumnWidth(0, 500)  # make name column wider
        self.tree_view.expanded.connect(self._on_tree_expanded)
        self.tree_selectionModel = self.tree_view.selectionModel()
        self.tree_selectionModel.selectionChanged.connect(
            self.on_treeview_selection_change
        )

        self.view_stack: QtWidgets.QStackedWidget = self.ui.views_stack_widget

        # UI Connections
        s = self.settings
        s.data_filename.connect_to_browse_widgets(
            self.ui.data_filename_lineEdit, self.ui.data_filename_browse_pushButton
        )
        s.browse_dir.connect_to_browse_widgets(
            self.ui.browse_dir_lineEdit, self.ui.browse_dir_browse_pushButton
        )
        if hasattr(self.ui, "browse_dir_refresh_pushButton"):
            self.ui.browse_dir_refresh_pushButton.clicked.connect(
                self.on_refresh_file_list
            )
            self.ui.browse_dir_refresh_pushButton.setShortcut(
                QtGui.QKeySequence(QtCore.Qt.Key_F5)
            )
        self.ui.data_filename_recycle_pushButton.clicked.connect(self.on_recycle)
        self.ui.data_filename_rename_pushButton.clicked.connect(self.on_rename)
        s.view_name.connect_to_widget(self.ui.view_name_comboBox)
        s.auto_select_view.connect_to_widget(self.ui.auto_select_checkBox)
        s.file_filter.connect_to_widget(self.ui.file_filter_lineEdit)

        self.ui.console_pushButton.clicked.connect(self.console_widget.show)
        self.ui.log_pushButton.clicked.connect(self.logging_widget.show)

        self.ui.action_save_as_ini.triggered.connect(self.settings_save_dialog)
        self.ui.action_load_ini.triggered.connect(self.settings_load_dialog)
        self.ui.action_show_settings.triggered.connect(self.on_show_settings)
        self.ui.show_settings_pushButton.clicked.connect(self.on_show_settings)

        self.ui.show()
        self.ui.raise_()

        self.ui.keyPressEvent = self.handle_key_board

    def set_logo(self, logo_path):
        logo_icon = QtGui.QIcon(logo_path)
        self.qtapp.setWindowIcon(logo_icon)
        self.ui.setWindowIcon(logo_icon)

    def handle_key_board(self, event):
        if event.modifiers() != QtCore.Qt.ControlModifier:
            func = self.keys.get(event.key(), None)
            if func is not None:
                func()
            return

        func = self.ctrl_keys.get(event.key(), None)
        if func is not None:
            func()

    def add_view(self, new_view):
        self.log.debug(f"add_view called {new_view}")

        # Update views dict
        self.views[new_view.name] = new_view

        self.add_lq_collection_to_settings_path(new_view.settings)

        self.settings.get_lq("view_name").change_choice_list(list(self.views.keys()))

        self.log.debug(f"add_view done {new_view}")

        return new_view

    def add_plugin(self, plugin):
        self.ui.plugin_buttons_layout.addWidget(plugin.get_show_hide_button())
        self.plugin_update_funcs.append(plugin.update_if_showing)
        self.ctrl_keys[plugin.show_keyboard_key] = plugin.toggle_show_hide
        self.plugins[plugin.name] = plugin
        self.add_lq_collection_to_settings_path(plugin.settings)

    def load_view(self, new_view):
        # deprecated use DataBrowser.add_view(new_view) instead
        self.add_view(new_view)

    def on_change_data_filename(self):
        fname = self.settings["data_filename"]
        if not Path(fname).is_file():
            print("invalid data_filename", fname)
            return

        print("file", fname)

        # select view
        if self.settings["auto_select_view"]:
            view_name = self.auto_select_view(fname)
            if view_name != self.current_view.name:
                self.settings["view_name"] = view_name
                self.setup_view(self.views[view_name])

        self.current_view.on_change_data_filename(fname)

    def on_change_data_filename_handle_plugins(self):
        fname = self.settings["data_filename"]
        for func in self.plugin_update_funcs:
            func(fname)

    @QtCore.Slot()
    def on_change_browse_dir(self):
        self.log.debug("on_change_browse_dir")
        browse_dir = self.settings["browse_dir"]
        root_idx = self.fs_model.setRootPath(browse_dir)
        self.ui.treeView.setRootIndex(root_idx)
        with self._dir_snapshots_lock:
            self._browse_gen += 1
            self._dir_snapshots.clear()
            gen = self._browse_gen
        self._seed_dir_snapshot_async(str(browse_dir), gen)

    def _on_tree_expanded(self, index):
        path = self.fs_model.filePath(index)
        if path and self.fs_model.isDir(index):
            with self._dir_snapshots_lock:
                gen = self._browse_gen
            self._seed_dir_snapshot_async(path, gen)

    def _seed_dir_snapshot_async(self, path: str, gen: int):
        if not path or self._refresh_stopped:
            return

        def _seed():
            snap = _take_dir_snapshot(path)
            if snap is None:
                return
            with self._dir_snapshots_lock:
                if gen == self._browse_gen and path not in self._dir_snapshots:
                    self._dir_snapshots[path] = snap

        threading.Thread(target=_seed, daemon=True).start()

    def _get_watched_dirs(self):
        browse_dir = str(self.settings["browse_dir"])
        if not browse_dir or not Path(browse_dir).is_dir():
            return []

        dirs = [browse_dir]
        root_idx = self.tree_view.rootIndex()
        if not root_idx.isValid():
            return dirs

        stack = [root_idx]
        while stack:
            parent = stack.pop()
            rows = self.fs_model.rowCount(parent)
            for row in range(rows):
                child = self.fs_model.index(row, 0, parent)
                if not child.isValid():
                    continue
                if self.tree_view.isExpanded(child) and self.fs_model.isDir(child):
                    path = self.fs_model.filePath(child)
                    if path:
                        dirs.append(path)
                    stack.append(child)
        return dirs

    def on_change_auto_refresh_interval(self):
        interval = float(self.settings["auto_refresh_interval"])
        if interval <= 0.0:
            self._refresh_timer.stop()
        else:
            self._refresh_timer.start(max(100, int(interval * 1000)))

    def _stop_file_refresh(self):
        self._refresh_stopped = True
        if hasattr(self, "_refresh_timer"):
            self._refresh_timer.stop()

    def _poll_watched_dirs(self):
        if self._refresh_stopped or self._poll_in_progress:
            return
        if self.ui is None or not self.ui.isVisible() or self.ui.isMinimized():
            return

        watched = self._get_watched_dirs()
        if not watched:
            return

        with self._dir_snapshots_lock:
            gen = self._browse_gen

        self._poll_in_progress = True
        threading.Thread(
            target=self._scan_dirs_worker, args=(watched, gen), daemon=True
        ).start()

    def _scan_dirs_worker(self, watched, gen: int):
        try:
            snapshots = {}
            for path in watched:
                snap = _take_dir_snapshot(path)
                if snap is not None:
                    snapshots[path] = snap

            changed = []
            with self._dir_snapshots_lock:
                if gen != self._browse_gen:
                    return
                watched_set = set(watched)
                for stale in list(self._dir_snapshots.keys()):
                    if stale not in watched_set:
                        del self._dir_snapshots[stale]

                for path, snap in snapshots.items():
                    prev = self._dir_snapshots.get(path)
                    self._dir_snapshots[path] = snap
                    if prev is not None and prev != snap:
                        changed.append(path)

            if changed and not self._refresh_stopped:
                self._dirs_changed.emit(changed)
        finally:
            self._poll_in_progress = False

    @QtCore.Slot(list)
    def refresh_file_list(self, changed_dirs=None):
        """Force QFileSystemModel to re-scan browse_dir and any expanded subdirectories."""
        browse_dir = str(self.settings["browse_dir"])
        if not browse_dir or not Path(browse_dir).is_dir():
            return

        targets = (
            list(changed_dirs)
            if changed_dirs is not None
            else self._get_watched_dirs()
        )
        for path in targets:
            if path != browse_dir and Path(path).is_dir():
                self.fs_model.setRootPath(path)

        self.fs_model.setRootPath("")
        root_idx = self.fs_model.setRootPath(browse_dir)
        self.ui.treeView.setRootIndex(root_idx)

    @QtCore.Slot()
    def on_refresh_file_list(self):
        """Manually refresh browse_dir and all expanded subdirectories."""
        targets = self._get_watched_dirs()
        with self._dir_snapshots_lock:
            gen = self._browse_gen
            self._dir_snapshots.clear()
        self.refresh_file_list(targets)
        for path in targets:
            self._seed_dir_snapshot_async(path, gen)

    def on_change_file_filter(self):
        self.log.debug("on_change_file_filter")
        filter_str = self.settings["file_filter"]
        if filter_str == "":
            filter_str = "*"
            self.settings["file_filter"] = "*"
        filter_str_list = [x.strip() for x in filter_str.split(",")]
        self.log.debug(filter_str_list)
        self.fs_model.setNameFilters(filter_str_list)

    def setup_view(self, view: DataBrowserView):

        if not view.view_loaded:
            view.setup()
            index = self.view_stack.addWidget(self.current_view.ui)
            self.view_stack_indices[view.name] = index
            view.view_loaded = True

        self.current_view = view
        self.view_stack.setCurrentIndex(self.view_stack_indices[view.name])

    def on_change_view_name(self):
        self.current_view = self.views[self.settings["view_name"]]
        self.setup_view(self.current_view)

        # udpate
        fname = self.settings["data_filename"]
        if Path(fname).is_file():
            self.current_view.on_change_data_filename(fname)

    def on_treeview_selection_change(self, sel, desel):
        fname = self.fs_model.filePath(self.tree_selectionModel.currentIndex())
        self.settings["data_filename"] = fname

    #        print( 'on_treeview_selection_change' , fname, sel, desel)

    def auto_select_view(self, fname):
        "return the name of the last supported view for the given fname"
        for view_name, view in list(self.views.items())[::-1]:
            if view.is_file_supported(fname):
                return view_name
        return "file_info"

    def on_recycle(self):
        # import here because send2trash is not a built in library.
        import send2trash

        send2trash.send2trash(Path(self.settings["data_filename"]))

    def on_rename(self):
        fname = self.settings["data_filename"]
        dialog = RenameDialog(prev_path_name=fname)
        if not dialog.exec_():
            return  # dialog was escaped

        if dialog.new_name:
            Path(fname).rename(dialog.new_name)

    def read_setting(self, path, ini_string_value=False):
        lq = self.get_lq(path)

        if ini_string_value:
            return lq.ini_string_value()
        return lq.val

    def get_lq(self, path: str) -> LoggedQuantity:
        """
        returns the LoggedQuantity defined by a path string of the form 'section/[component/]setting'
        where section are "view", "plugin" or "app"
        returns None if it does not exist
        """
        parts = path.split("/")

        settings = self.settings
        if parts[0] == "view":
            view = self.views.get(parts[1], None)
            if view is not None:
                self.load_view(view)
                settings = view.settings
        elif parts[0] == "plugin":
            plugin = self.plugins.get(parts[1], None)
            if plugin is not None:
                settings = plugin.settings

        if parts[-1] in settings:
            return settings.get_lq(parts[-1])

    def settings_save_dialog(self):
        """Opens a save as ini dialogue in the app user interface."""
        fname, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.ui, "Save Settings file", "", "Settings File (*.ini)"
        )
        if fname:
            self.settings_save_ini(fname)

    def settings_load_dialog(self):
        """Opens a load ini dialogue in the app user interface"""
        fname, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.ui, "Open Settings file", "", "Settings File (*.ini)"
        )
        if fname.endswith(".ini"):
            self.settings_load_ini(fname)
        # elif fname.endswith(".h5"):
        #     self.settings_load_h5(fname)

    def on_show_settings(self):
        if not hasattr(self, "_trees_dialog"):

            app_tree = new_tree_widget((self,), ("app", ""))
            views_tree = new_tree_widget(
                [obj for obj in self.views.values()], ("views", "")
            )
            plugins_tree = new_tree_widget(
                [obj for obj in self.plugins.values()], ("plugins", "")
            )

            splitter = QtWidgets.QSplitter()
            splitter.addWidget(app_tree)
            splitter.addWidget(views_tree)
            splitter.addWidget(plugins_tree)

            pb_hlayout = QtWidgets.QHBoxLayout()
            pb = QtWidgets.QPushButton("save ini ...")
            pb.clicked.connect(self.settings_save_ini_ask)
            pb_hlayout.addWidget(pb)
            pb = QtWidgets.QPushButton("load ini ...")
            pb.clicked.connect(self.settings_load_ini_ask)
            pb_hlayout.addWidget(pb)

            layout = QtWidgets.QVBoxLayout()
            layout.addWidget(splitter)
            layout.addLayout(pb_hlayout)

            self._trees_dialog = QtWidgets.QDialog()
            self._trees_dialog.setLayout(layout)

        self._trees_dialog.exec_()


class RenameDialog(QtWidgets.QDialog):

    def __init__(self, prev_path_name):
        QtWidgets.QDialog.__init__(self)

        self.new_name = None

        rename_btn = QtWidgets.QPushButton("rename")
        cancel_btn = QtWidgets.QPushButton("cancel")
        self.new_name_w = QtWidgets.QLineEdit(prev_path_name)

        cancel_btn.clicked.connect(self.on_cancel)
        rename_btn.clicked.connect(self.on_rename)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.new_name_w)
        layout.addWidget(rename_btn)
        layout.addWidget(cancel_btn)
        self.setLayout(layout)

        self.setWindowTitle("rename")
        self.setMinimumWidth(500)

    def on_cancel(self):
        self.new_name = None
        self.accept()

    def on_rename(self):
        self.new_name = self.new_name_w.text()
        self.accept()
