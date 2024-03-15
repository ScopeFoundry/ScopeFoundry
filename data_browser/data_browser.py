import argparse
from collections import OrderedDict
from pathlib import Path

from qtpy import QtCore, QtWidgets, QtGui

from ScopeFoundry import BaseApp
from ScopeFoundry.helper_funcs import load_qt_ui_from_pkg, sibling_path
from .viewers.file_info import FileInfoView

class DataBrowser(BaseApp):
    
    name = "DataBrowser"
    
    def __init__(self, argv,dark_mode=False):
        BaseApp.__init__(self, argv, dark_mode)
        self.setup()
        parser = argparse.ArgumentParser()
        for lq in self.settings.as_list():
            parser.add_argument("--" + lq.name)
        args = parser.parse_args()
        for lq in self.settings.as_list():
            if lq.name in args:
                val = getattr(args,lq.name)
                if val is not None:
                    lq.update_value(val)

    def setup(self):
        self.views = OrderedDict()

        self.plugin_update_funcs = []
        self.keys = {
            QtCore.Qt.Key_Delete: self.on_recycle,
        }
        self.ctrl_keys = {
            QtCore.Qt.Key_R: self.on_rename,
        }

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


    def setup_ui(self):
        self.ui = load_qt_ui_from_pkg("ScopeFoundry.data_browser", "data_browser.ui")

        self.ui.setWindowTitle("ScopeFoundry: Data Browser")

        logo_path = sibling_path(__file__, "logo.png")
        self.set_logo(logo_path)

        # file system tree
        self.tree_view = self.ui.treeView
        self.fs_model = QtWidgets.QFileSystemModel()
        self.fs_model.setRootPath(QtCore.QDir.currentPath())
        self.tree_view.setModel(self.fs_model)
        self.tree_view.setIconSize(QtCore.QSize(16, 16))
        self.tree_view.setSortingEnabled(True)
        self.tree_view.setColumnWidth(0, 500)  # make name column wider
        self.tree_selectionModel = self.tree_view.selectionModel()
        self.tree_selectionModel.selectionChanged.connect(
            self.on_treeview_selection_change
        )

        # UI Connections
        s = self.settings
        s.data_filename.connect_to_browse_widgets(
            self.ui.data_filename_lineEdit, self.ui.data_filename_browse_pushButton
        )
        s.browse_dir.connect_to_browse_widgets(
            self.ui.browse_dir_lineEdit, self.ui.browse_dir_browse_pushButton
        )
        self.ui.data_filename_recycle_pushButton.clicked.connect(self.on_recycle)
        self.ui.data_filename_rename_pushButton.clicked.connect(self.on_rename)
        s.view_name.connect_bidir_to_widget(self.ui.view_name_comboBox)
        s.auto_select_view.connect_to_widget(self.ui.auto_select_checkBox)
        s.file_filter.connect_bidir_to_widget(self.ui.file_filter_lineEdit)

        self.ui.console_pushButton.clicked.connect(self.console_widget.show)
        self.ui.log_pushButton.clicked.connect(self.logging_widget.show)

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
        self.log.debug("add_view called {}".format(new_view))

        # Update views dict
        self.views[new_view.name] = new_view
        self.settings.view_name.change_choice_list(list(self.views.keys()))

        self.log.debug("add_view done {}".format(new_view))
        print("added view", repr(new_view.name))

        return new_view

    def add_plugin(self, plugin):
        self.ui.plugin_buttons_layout.addWidget(plugin.get_show_hide_button())
        self.plugin_update_funcs.append(plugin.update_if_showing)
        self.ctrl_keys[plugin.show_keyboard_key] = plugin.toggle_show_hide

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
        self.ui.treeView.setRootIndex(self.fs_model.index(self.settings['browse_dir']))
        self.fs_model.setRootPath(self.settings['browse_dir'])

    def on_change_file_filter(self):
        self.log.debug("on_change_file_filter")
        filter_str = self.settings['file_filter']
        if filter_str == "":
            filter_str = "*"
            self.settings['file_filter'] = "*"
        filter_str_list = [x.strip() for x in filter_str.split(',')]
        self.log.debug(filter_str_list)
        self.fs_model.setNameFilters(filter_str_list)

    def setup_view(self, view):
        if view.view_loaded:
            return
        view.setup()
        self.ui.data_view_layout.addWidget(self.current_view.ui)
        view.view_loaded = True

    def on_change_view_name(self):
        # hide previous
        self.current_view.ui.hide()

        # setup, show new
        self.current_view = self.views[self.settings["view_name"]]
        self.setup_view(self.current_view)
        self.current_view.ui.show()

        # udpate
        fname = self.settings["data_filename"]
        if Path(fname).is_file():
            self.current_view.on_change_data_filename(fname)

    def on_treeview_selection_change(self, sel, desel):
        fname = self.fs_model.filePath(self.tree_selectionModel.currentIndex())
        self.settings['data_filename'] = fname
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
