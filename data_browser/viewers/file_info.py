from pathlib import Path
from qtpy import QtWidgets

from ScopeFoundry.data_browser import DataBrowserView

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
        
        if ext in ('.py', '.ini', '.txt'):
            with open(fname, 'r') as f:
                self.ui.setText(f.read())
        else:
            self.ui.setText(str(fname))
        
    def is_file_supported(self, fname):
        return True