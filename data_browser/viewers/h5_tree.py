from ScopeFoundry.data_browser import DataBrowserView
from qtpy import QtWidgets
import h5py


class H5TreeView(DataBrowserView):

    name = 'h5_tree'
    
    def is_file_supported(self, fname):
        return ('.h5' in fname)
    
    def setup(self):
        self.ui = QtWidgets.QTextEdit("file_info")
    
    def on_change_data_filename(self, fname=None):
        self.ui.setText("loading {}".format(fname))
        try:        
            self.f = h5py.File(fname, 'r')
            
            self.tree_str = "{}\n{}\n".format(fname, "="*len(fname)) 
            self.f.visititems(self._visitfunc)
            self.ui.setText(self.tree_str)
            
        except Exception as err:
            self.databrowser.ui.statusbar.showMessage("failed to load %s:\n%s" %(fname, err))
            raise(err)

    def _visitfunc(self, name, node):
        
        level = len(name.split('/'))
        indent = '    '*level
        localname = name.split('/')[-1]
    
        if isinstance(node, h5py.Group):
            self.tree_str += indent +"|> {}\n".format(localname)
        elif isinstance(node, h5py.Dataset):
            self.tree_str += indent +"|D {}: {} {}\n".format(localname, node.shape, node.dtype)
        for key, val in node.attrs.items():
            self.tree_str += indent+"    |- {} = {}\n".format(key, val)  
            
            
class H5TreeSearchView(DataBrowserView):
    
    name = 'h5_tree_search'
    
    def is_file_supported(self, fname):
        return ('.h5' in fname)
    
    def setup(self):
        
        #self.settings.New('search_text', dtype=str, initial="")
        
        self.ui = QtWidgets.QWidget()
        self.ui.setLayout(QtWidgets.QVBoxLayout())
        self.search_lineEdit = QtWidgets.QLineEdit()
        self.tree_textEdit = QtWidgets.QTextEdit("")
        
        self.ui.layout().addWidget(self.search_lineEdit)
        self.ui.layout().addWidget(self.tree_textEdit)
         
        #self.settings.search_text.connect_to_widget(self.search_lineEdit)
        #self.settings.search_text.add_listener(self.on_new_search_text)
        self.search_text = ""
        
        self.search_lineEdit.textChanged.connect(self.on_new_search_text)
        

    def on_change_data_filename(self, fname=None):
        self.tree_textEdit.setText("loading {}".format(fname))
        try:
            self.fname = fname        
            self.f = h5py.File(fname, 'r')
            self.on_new_search_text()
            self.databrowser.ui.statusbar.showMessage("")
            
        except Exception as err:
            msg = "Failed to load %s:\n%s" %(fname, err)
            self.databrowser.ui.statusbar.showMessage(msg)
            self.tree_textEdit.setText(msg)
            raise(err)


    def on_new_search_text(self, x=None):
        if x is not None:
            self.search_text = x.lower()
        old_scroll_pos = self.tree_textEdit.verticalScrollBar().value()
        self.tree_str = ""  
        self.f.visititems(self._visitfunc)
        
        self.tree_text_html = \
        """<html><b>{}</b><hr/>
        <div style="font-family: Courier;">
         {} 
         </div>
         </html>""".format(self.fname, self.tree_str)
        
        self.tree_textEdit.setText(self.tree_text_html)
        self.tree_textEdit.verticalScrollBar().setValue(old_scroll_pos)
           
            
    def _visitfunc(self, name, node):
        
        level = len(name.split('/'))
        indent = '&nbsp;'*4*(level-1)
    
        #indent = '<span style="color:blue;">'.format(level*4)
        localname = name.split('/')[-1]
        
        #search_text = self.settings['search_text'].lower()
        search_text = self.search_text
        if search_text and (search_text in localname.lower()):
            localname = """<span style="color: red;">{}</span>""".format(localname)
    
        if isinstance(node, h5py.Group):
            self.tree_str += indent +"|> <b>{}/</b><br/>".format(localname)
        elif isinstance(node, h5py.Dataset):
            self.tree_str += indent +"|D <b>{}</b>: {} {}<br/>".format(localname, node.shape, node.dtype)
        for key, val in node.attrs.items():
            if search_text:
                if search_text in str(key).lower(): 
                    key = """<span style="color: red;">{}</span>""".format(key)
                if search_text in str(val).lower(): 
                    val = """<span style="color: red;">{}</span>""".format(val)
            self.tree_str += indent+"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|- <i>{}</i> = {}<br/>".format(key, val)          
    
