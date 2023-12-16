from pathlib import Path
import argparse
from collections import OrderedDict

from qtpy import QtCore, QtWidgets, QtGui

from ScopeFoundry import BaseApp
from ScopeFoundry.helper_funcs import load_qt_ui_from_pkg, sibling_path

from .viewers import H5SearchView, FileInfoView


class DataBrowser(BaseApp):

    name = "DataBrowser"

    def __init__(self, argv):
        BaseApp.__init__(self, argv)
        self.setup()
        parser = argparse.ArgumentParser()
        for lq in self.settings.as_list():
            parser.add_argument("--" + lq.name)
        args = parser.parse_args()
        for lq in self.settings.as_list():
            if lq.name in args:
                val = getattr(args, lq.name)
                if val is not None:
                    lq.update_value(val)

    def setup(self):

        self.views = OrderedDict()
        self.current_view = None

        s = self.settings
        s.New('data_filename', dtype='file')
        s.New('browse_dir', dtype='file', is_dir=True, initial='/')
        s.New('file_filter', dtype=str, initial='*.*,')
        s.New('auto_select_view', dtype=bool, initial=True,
              description="auto selects the view when file name is changed.")
        s.New('view_name', dtype=str, initial='0', choices=('0',))

        self.setup_ui()

        # add default views
        self.add_view(FileInfoView(self))
        self.settings['view_name'] = "file_info"
        self.add_view(H5SearchView(self))
        self.is_h5_search_showing = False

        # add callbacks
        s.data_filename.add_listener(self.on_change_data_filename)
        s.browse_dir.add_listener(self.on_change_browse_dir)
        s['browse_dir'] = Path.cwd()

        s.file_filter.add_listener(self.on_change_file_filter)
        s.view_name.add_listener(self.on_change_view_name)

    def setup_ui(self):

        self.ui = load_qt_ui_from_pkg(
            'ScopeFoundry.data_browser', 'data_browser.ui')

        self.ui.setWindowTitle("ScopeFoundry: Data Browser")
                
        logo_icon = QtGui.QIcon(sibling_path(__file__, "scopefoundry_logo2C_1024.png"))
        self.qtapp.setWindowIcon(logo_icon)
        self.ui.setWindowIcon(logo_icon)

        # file system tree
        self.tree_view = TreeView(
            self.on_recycle, self.on_rename, self.on_search_h5)
        self.ui.file_system_layout.insertWidget(2, self.tree_view)
        self.fs_model = QtWidgets.QFileSystemModel()
        self.fs_model.setRootPath(QtCore.QDir.currentPath())
        self.tree_view.setModel(self.fs_model)
        self.tree_view.setIconSize(QtCore.QSize(16, 16))
        self.tree_view.setSortingEnabled(True)
        self.tree_view.setColumnWidth(0, 500)  # make name column wider
        self.tree_selectionModel = self.tree_view.selectionModel()
        self.tree_selectionModel.selectionChanged.connect(
            self.on_treeview_selection_change)

        # UI Connections
        s = self.settings
        s.data_filename.connect_to_browse_widgets(self.ui.data_filename_lineEdit,
                                                  self.ui.data_filename_browse_pushButton)
        s.browse_dir.connect_to_browse_widgets(self.ui.browse_dir_lineEdit,
                                               self.ui.browse_dir_browse_pushButton)
        self.ui.data_filename_recycle_pushButton.clicked.connect(
            self.on_recycle)
        self.ui.data_filename_rename_pushButton.clicked.connect(self.on_rename)
        s.view_name.connect_bidir_to_widget(self.ui.view_name_comboBox)
        s.auto_select_view.connect_to_widget(self.ui.auto_select_checkBox)
        s.file_filter.connect_bidir_to_widget(self.ui.file_filter_lineEdit)

        self.ui.console_pushButton.clicked.connect(self.console_widget.show)
        self.ui.log_pushButton.clicked.connect(self.logging_widget.show)
        self.ui.search_h5_pushButton.clicked.connect(self.on_search_h5)

        self.ui.show()
        self.ui.raise_()


    def add_view(self, new_view):
        print("loading view", repr(new_view.name))
        self.log.debug('load_view called {}'.format(new_view))

        # Update views dict
        self.views[new_view.name] = new_view
        self.settings.view_name.change_choice_list(list(self.views.keys()))

        self.log.debug('load_view done {}'.format(new_view))

        return new_view

    def load_view(self, new_view):
        # deprecated use DataBrowser.add_view(new_view) instead
        self.add_view(new_view)

    def load_view_ui(self, view):
        if view.view_loaded:
            # view is already set-up / loaded
            return

        print(f"setting up view {self.current_view.name}")
        view.setup()
        self.ui.data_view_layout.addWidget(view.ui)
        view.view_loaded = True

    def on_change_data_filename(self):
        fname = self.settings['data_filename']
        if fname == "0":
            print("initial file 0")
            return
        else:
            print("file", fname)

        # select view
        if self.settings['auto_select_view']:
            view_name = self.auto_select_view(fname)
            if self.current_view is None or view_name != self.current_view.name:
                self.settings['view_name'] = view_name
        if Path(fname).is_file():
            self.current_view.on_change_data_filename(fname)

    @QtCore.Slot()
    def on_change_browse_dir(self):
        self.log.debug("on_change_browse_dir")
        self.tree_view.setRootIndex(
            self.fs_model.index(self.settings['browse_dir']))
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

    def on_change_view_name(self):

        # hide previous view
        if self.current_view:
            self.current_view.ui.hide()

        # show new view
        self.current_view = self.views[self.settings['view_name']]
        self.load_view_ui(self.current_view)
        self.current_view.ui.show()

        # set data file for new (current) view
        fname = self.settings['data_filename']
        if Path(fname).is_file():
            self.current_view.on_change_data_filename(fname)

    def on_treeview_selection_change(self, sel, desel):
        fname = self.fs_model.filePath(self.tree_selectionModel.currentIndex())
        self.settings['data_filename'] = fname
        # print("on_treeview_selection_change", sel, desel)

    def auto_select_view(self, fname):
        "return the name of the last supported view for the given fname"
        for view_name, view in list(self.views.items())[::-1]:
            if view.is_file_supported(fname):
                return view_name
        if fname.endswith(".h5"):
            return "h5_search"
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

    def on_search_h5(self):
        self.load_view_ui(self.views["h5_search"])
        if self.is_h5_search_showing:
            self.views["h5_search"].ui.hide()
            self.is_h5_search_showing = False
        else:
            self.views["h5_search"].ui.show()
            self.is_h5_search_showing = True


class TreeView(QtWidgets.QTreeView):

    def __init__(self, delete_func, rename_func, search_func, parent=None) -> None:
        QtWidgets.QTreeView.__init__(self, parent)
        self.delete_func = delete_func
        self.rename_func = rename_func
        self.search_func = search_func

    def keyPressEvent(self, event: QtGui.QKeyEvent)->None:
        QtWidgets.QTreeView.keyPressEvent(self, event)

        if event.key() == QtCore.Qt.Key_Delete:
            self.delete_func()

        elif event.key() == QtCore.Qt.Key_R:
            self.rename_func()

        elif event.key() == QtCore.Qt.Key_F:
            self.search_func()


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
