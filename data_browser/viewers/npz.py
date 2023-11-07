from qtpy import QtWidgets
from ScopeFoundry.data_browser import DataBrowserView
import os

class NPZView(DataBrowserView):
    """Reads Numpy Z files (npz)
    
    """
    name = 'npz_view'
    
    def setup(self):
        
        #self.ui = QtGui.QScrollArea()
        #self.display_label = QtGui.QLabel("TestNPZView")
        self.ui = self.display_textEdit = QtWidgets.QTextEdit()
        
        #self.ui.setLayout(QtGui.QVBoxLayout())
        #self.ui.layout().addWidget(self.display_label)
        #self.ui.setWidget(self.display_label)
        
    def on_change_data_filename(self, fname=None):
        import numpy as np
        
        try:
            self.dat = np.load(fname)
            
            self.display_txt = "File: {}\n".format(fname)
            
            sorted_keys = sorted(self.dat.keys())
            
            for key in sorted_keys:
                val = self.dat[key]
                if val.shape == ():
                    self.display_txt += "    --> {}: {}\n".format(key, val)                    
                else:
                    self.display_txt += "    --D {}: Array of {} {}\n".format(key, val.dtype, val.shape)
            
            #self.display_label.setText(self.display_txt)
            self.display_textEdit.setText(self.display_txt)
        except Exception as err:
            self.display_textEdit.setText("failed to load %s:\n%s" %(fname, err))
            raise(err)
        
    def is_file_supported(self, fname):
        return os.path.splitext(fname)[1] == ".npz"

