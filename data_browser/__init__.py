from ScopeFoundry import BaseApp, LQCollection
from ScopeFoundry.helper_funcs import load_qt_ui_from_pkg
import argparse
from collections import OrderedDict
from qtpy import QtCore, QtWidgets, QtGui
import os
from pathlib import Path

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
                val = getattr(args,lq.name)
                if val is not None:
                    lq.update_value(val)

    def setup(self):

        #self.ui = load_qt_ui_file(sibling_path(__file__, "data_browser.ui"))
        self.ui = load_qt_ui_from_pkg('ScopeFoundry.data_browser', 'data_browser.ui')
        self.ui.show()
        self.ui.raise_()
        
        self.ui.setWindowTitle("ScopeFoundry: Data Browser")
        self.ui.setWindowIcon(QtGui.QIcon('scopefoundry_logo2C_1024.png'))
        
        self.views = OrderedDict()        
        self.current_view = None        

        self.settings.New('data_filename', dtype='file')
        self.settings.New('browse_dir', dtype='file', is_dir=True, initial='/')
        self.settings.New('file_filter', dtype=str, initial='*.*,')
        
        self.settings.data_filename.add_listener(self.on_change_data_filename)

        self.settings.New('auto_select_view',dtype=bool, initial=True)

        self.settings.New('view_name', dtype=str, initial='0', choices=('0',))
        
        # UI Connections
        self.settings.data_filename.connect_to_browse_widgets(self.ui.data_filename_lineEdit, 
                                                              self.ui.data_filename_browse_pushButton)
        self.settings.browse_dir.connect_to_browse_widgets(self.ui.browse_dir_lineEdit, 
                                                              self.ui.browse_dir_browse_pushButton)
        self.ui.data_filename_recycle_pushButton.clicked.connect(self.on_recycle)
        self.ui.data_filename_rename_pushButton.clicked.connect(self.on_rename)
        self.settings.view_name.connect_bidir_to_widget(self.ui.view_name_comboBox)
        self.settings.file_filter.connect_bidir_to_widget(self.ui.file_filter_lineEdit)
        
        
        
        # file system tree
        self.tree_view = TreeView(self.on_recycle, self.on_rename)
        self.ui.file_system_layout.insertWidget(2, self.tree_view)
        self.fs_model = QtWidgets.QFileSystemModel()
        self.fs_model.setRootPath(QtCore.QDir.currentPath())
        self.tree_view.setModel(self.fs_model)
        self.tree_view.setIconSize(QtCore.QSize(16,16))
        self.tree_view.setSortingEnabled(True)
        self.tree_view.setColumnWidth(0, 500) # make name column wider
        self.tree_selectionModel = self.tree_view.selectionModel()
        self.tree_selectionModel.selectionChanged.connect(self.on_treeview_selection_change)

        self.settings.browse_dir.add_listener(self.on_change_browse_dir)
        self.settings['browse_dir'] = os.getcwd()

        # Load file information view as default view
        self.load_view(FileInfoView(self))

        self.settings.view_name.add_listener(self.on_change_view_name)
        self.settings['view_name'] = "file_info"
        
        self.settings.file_filter.add_listener(self.on_change_file_filter)
        
        #self.console_widget.show()
        self.ui.console_pushButton.clicked.connect(self.console_widget.show)
        self.ui.log_pushButton.clicked.connect(self.logging_widget.show)
        self.ui.show()
        
    def load_view(self, new_view):
        print("loading view", repr(new_view.name))
        
        #instantiate view
        #new_view = ViewClass(self)
        
        self.log.debug('load_view called {}'.format(new_view))
        # add to views dict
        self.views[new_view.name] = new_view
        
        # self.ui.data_view_layout.addWidget(new_view.ui)
        # new_view.ui.hide()
        
        # update choices for view_name
        self.settings.view_name.change_choice_list(list(self.views.keys()))
        self.log.debug('load_view done {}'.format(new_view))
        return new_view

    def on_change_data_filename(self):
        fname = self.settings['data_filename'] 
        if fname == "0":
            print("initial file 0")
            return
        else:
            print("file", fname)
        if not self.settings['auto_select_view']:
            self.current_view.on_change_data_filename(fname)
        else:
            view_name = self.auto_select_view(fname)
            if self.current_view is None or view_name != self.current_view.name:
                # update view (automatically calls on_change_data_filename)
                self.settings['view_name'] = view_name
            else:
                # force update
                if  os.path.isfile(fname):
                    self.current_view.on_change_data_filename(fname)

    @QtCore.Slot()
    def on_change_browse_dir(self):
        self.log.debug("on_change_browse_dir")
        self.tree_view.setRootIndex(self.fs_model.index(self.settings['browse_dir']))
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
        #print('on_change_view_name')
        previous_view = self.current_view
        
        self.current_view = self.views[self.settings['view_name']]
    
        # hide current view 
        # (handle the initial case where previous_view is None )
        if previous_view:
            previous_view.ui.hide() 
        else:
            self.ui.dataview_placeholder.hide()
        
        # set up view if not already loaded
        if not self.current_view.view_loaded:
            print(f"setting up view {self.current_view.name}")
            self.current_view.setup()
            self.ui.data_view_layout.addWidget(self.current_view.ui)
            #new_view.ui.hide()            
            self.current_view.view_loaded = True
        # show new view
        self.current_view.ui.show()
        
        # set datafile for new (current) view
        fname = self.settings['data_filename']
        if  os.path.isfile(fname):
            self.current_view.on_change_data_filename(self.settings['data_filename'])

    def on_treeview_selection_change(self, sel, desel):
        fname = self.fs_model.filePath(self.tree_selectionModel.currentIndex())
        self.settings['data_filename'] = fname
#        print( 'on_treeview_selection_change' , fname, sel, desel)

    def auto_select_view(self, fname):
        "return the name of the last supported view for the given fname"
        for view_name, view in list(self.views.items())[::-1]:
            if view.is_file_supported(fname):
                return view_name
        # return default file_info view if no others work
        return 'file_info'

    def on_recycle(self):
        import send2trash #decided to import here because send2trash is not a built in library.
        send2trash.send2trash(Path(self.settings["data_filename"]))

    def on_rename(self):
        path = Path(self.settings["data_filename"])               
        dialog = RenameDialog(prev_path_name=str(path))
        if dialog.exec_():
            if dialog.new_name is not None:
                path.rename(dialog.new_name)


class TreeView(QtWidgets.QTreeView):
    
    def __init__(self, delete_func, rename_func, parent=None) -> None:
        QtWidgets.QTreeView.__init__(self, parent)
        self.delete_func = delete_func
        self.rename_func = rename_func
        
    def keyPressEvent(self, event:QtGui.QKeyEvent)->None:
        QtWidgets.QTreeView.keyPressEvent(self, event)
        if event.key() == QtCore.Qt.Key_Delete:
            self.delete_func()
            
        if event.key() == QtCore.Qt.Key_R:
            self.rename_func()
            
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
        
class DataBrowserView(QtCore.QObject):
    """ Abstract class for DataBrowser Views"""
    
    def __init__(self, databrowser):
        QtCore.QObject.__init__(self)
        self.databrowser =  databrowser
        self.settings = LQCollection()
        self.view_loaded = False
        #self.setup()
        
    def setup(self):
        pass
        # create view with no data file

    def on_change_data_filename(self, fname=None):
        pass
        # load data file
        
        # update display
        
    def is_file_supported(self, fname):
        # returns whether view can handle file, should return False early to avoid
        # too much computation when selecting a file
        return False
        
class FileInfoView(DataBrowserView):
    """A general viewer to handle text files and
    unsupported file types."""
    name = 'file_info'
    
    def setup(self):
        self.ui = QtWidgets.QTextEdit("file_info")
        
    def on_change_data_filename(self, fname=None):
        if fname is None:
            fname = self.databrowser.settings['data_filename']
        
        # Use pathlib
        fname = Path(fname)
        
        ext = fname.suffix
        
        if ext in ('.py', '.ini', '.txt', '.yml', '.yaml'):
            with open(fname, 'r') as f:
                self.ui.setText(f.read())
        else:
            self.ui.setText(str(fname))
        
    def is_file_supported(self, fname):
        return True