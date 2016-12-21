from __future__ import division, print_function
from ScopeFoundry import BaseApp
from ScopeFoundry.helper_funcs import load_qt_ui_file, sibling_path
from collections import OrderedDict
import os
from PySide import QtCore, QtGui
import pyqtgraph as pg
import numpy as np


class DataBrowser(BaseApp):
    
    name = "DataBrowser"
    
    def __init__(self, argv):
        BaseApp.__init__(self, argv)
        self.setup()
    
    def setup(self):

        self.ui = load_qt_ui_file(sibling_path(__file__, "data_browser.ui"))
        self.ui.show()
        self.ui.raise_()
        
        
        self.views = OrderedDict()        

        
        self.settings.New('data_filename', dtype='file')
        self.settings.New('browse_dir', dtype='file', is_dir=True, initial='/')
        self.settings.New('file_filter', dtype=str, initial='*.*,')
        
        self.settings.data_filename.updated_value.connect(self.on_change_data_filename)
        self.settings.browse_dir.updated_value.connect(self.on_change_browse_dir)
        self.settings.file_filter.updated_value.connect(self.on_change_file_filter)

        self.settings.New('auto_select_view',dtype=bool, initial=True)

        self.settings.New('view_name', dtype=str, initial='0', choices=('0',))
        self.settings.view_name.updated_value.connect(self.on_change_view_name)
        
        # UI Connections
        self.settings.data_filename.connect_to_browse_widgets(self.ui.data_filename_lineEdit, 
                                                              self.ui.data_filename_browse_pushButton)
        self.settings.browse_dir.connect_to_browse_widgets(self.ui.browse_dir_lineEdit, 
                                                              self.ui.browse_dir_browse_pushButton)
        self.settings.view_name.connect_bidir_to_widget(self.ui.view_name_comboBox)
        self.settings.file_filter.connect_bidir_to_widget(self.ui.file_filter_lineEdit)
        
        # file system tree
        self.fs_model = QtGui.QFileSystemModel()
        self.fs_model.setRootPath(QtCore.QDir.currentPath())
        self.ui.treeView.setModel(self.fs_model)
        self.settings['browse_dir'] = os.getcwd()
        self.ui.treeView.setIconSize(QtCore.QSize(16,16))
        for i in (1,2,3):
            self.ui.treeView.hideColumn(i)
        #print("="*80, self.ui.treeView.selectionModel())
        self.tree_selectionModel = self.ui.treeView.selectionModel()
        self.tree_selectionModel.selectionChanged.connect(self.on_treeview_selection_change)

        # set views
        self.current_view = None
        
        self.load_view(FileInfoView(self))
        self.load_view(TestNPZView(self))

        self.settings['view_name'] = "file_info"
        
        self.console_widget.show()
        self.ui.show()

        
        
    def load_view(self, new_view):
        
        #instantiate view
        #new_view = ViewClass(self)
        
        # add to views dict
        self.views[new_view.name] = new_view
        
        self.ui.dataview_groupBox.layout().addWidget(new_view.ui)
        new_view.ui.hide()
        
        # update choices for view_name
        self.settings.view_name.change_choice_list(self.views.keys())
        

    def on_change_data_filename(self):
        fname = self.settings.data_filename.val 
        if not self.settings['auto_select_view']:
            self.current_view.on_change_data_filename(fname)
        else:
            view_name = self.auto_select_view(fname)
            if view_name == self.current_view.name:
                self.current_view.on_change_data_filename(fname)
            else:
                # update view (automatically calls on_change_data_filename)
                self.settings['view_name'] = view_name

    def on_change_browse_dir(self):
        #print("on_change_browse_dir")
        self.ui.treeView.setRootIndex(self.fs_model.index(self.settings['browse_dir']))
    
    def on_change_file_filter(self):
        filter_str = self.settings['file_filter']
        if filter_str == "":
            filter_str = "*"
            self.settings['file_filter'] = "*"
        filter_str_list = [x.strip() for x in filter_str.split(',')]
        print(filter_str_list)
        self.fs_model.setNameFilters(filter_str_list)
                    
    def on_change_view_name(self):
        #print('on_change_view_name')
        previous_view = self.current_view
        
        self.current_view = self.views[self.settings['view_name']]
    
        # hide current view
        if previous_view:
            previous_view.ui.hide() 
        else:
            self.ui.dataview_placeholder.hide()
        
        # show new view
        self.current_view.ui.show()
        
        # set datafile for new (current) view
        self.current_view.on_change_data_filename(self.settings['data_filename'])

    def on_treeview_selection_change(self, sel, desel):
        fname = self.fs_model.filePath(self.tree_selectionModel.currentIndex())
        self.settings['data_filename'] = fname
#        print( 'on_treeview_selection_change' , fname, sel, desel)

    def auto_select_view(self, fname):
        "return the name of the last supported view for the given fname"
        for view_name, view in self.views.items()[::-1]:
            if view.is_file_supported(fname):
                return view_name
        # return default file_info view if no others work
        return 'file_info'
        

class DataBrowserView(QtCore.QObject):
    """ Abstract class for DataBrowser Views"""
    
    def __init__(self, databrowser):
        self.databrowser =  databrowser
        self.setup()
        
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
    
    name = 'file_info'
    
    def setup(self):
        self.ui = QtGui.QTextEdit("file_info")
        
    def on_change_data_filename(self, fname=None):
        if fname is None:
            fname = self.databrowser.settings['data_filename']

        self.ui.setText(fname)
        
    def is_file_supported(self, fname):
        return True


class TestNPZView(DataBrowserView):
    
    name = 'test_npz_view'
    
    def setup(self):
        
        #self.ui = QtGui.QScrollArea()
        #self.display_label = QtGui.QLabel("TestNPZView")
        self.ui = self.display_textEdit = QtGui.QTextEdit()
        
        #self.ui.setLayout(QtGui.QVBoxLayout())
        #self.ui.layout().addWidget(self.display_label)
        #self.ui.setWidget(self.display_label)
        
    def on_change_data_filename(self, fname=None):
        import numpy as np
        
        try:
            self.dat = np.load(fname)
            
            self.display_txt = "File: {}\n".format(fname)
            
            for key,val in self.dat.items():
                self.display_txt += "\t-->{} {}\n".format(key, val.shape)
            
            #self.display_label.setText(self.display_txt)
            self.display_textEdit.setText(self.display_txt)
        except Exception as err:
            self.display_textEdit.setText("failed to load %s:\n%s" %(fname, err))
            raise(err)
        
    def is_file_supported(self, fname):
        return os.path.splitext(fname)[1] == ".npz"


class HyperSpectralBaseView(DataBrowserView):
    
    name = 'HyperSpectralBaseView'
    
    def setup(self):
        
        self.ui = QtGui.QWidget()
        self.ui.setLayout(QtGui.QVBoxLayout())
        self.imview = pg.ImageView()
        self.imview.getView().invertY(False) # lower left origin
        self.ui.layout().addWidget(self.imview)
        self.graph_layout = pg.GraphicsLayoutWidget()
        self.ui.layout().addWidget(self.graph_layout)

        self.spec_plot = self.graph_layout.addPlot()
        self.rect_plotdata = self.spec_plot.plot()
        self.point_plotdata = self.spec_plot.plot(pen=(0,9))
        
        
        # Rectangle ROI
        self.rect_roi = pg.RectROI([20, 20], [20, 20], pen=(0,9))
        self.rect_roi.addTranslateHandle((0.5,0.5))        
        self.imview.getView().addItem(self.rect_roi)        
        self.rect_roi.sigRegionChanged.connect(self.on_change_rect_roi)
        
        # Point ROI
        self.circ_roi = pg.CircleROI( (0,0), (2,2) , movable=True, pen=(0,9))
        #self.circ_roi.removeHandle(self.circ_roi.getHandles()[0])
        h = self.circ_roi.addTranslateHandle((0.5,.5))
        h.pen = pg.mkPen('r')
        h.update()
        self.imview.getView().addItem(self.circ_roi)
        self.circ_roi.removeHandle(0)
        self.circ_roi_plotline = pg.PlotCurveItem([0], pen=(0,9))
        self.imview.getView().addItem(self.circ_roi_plotline) 
        self.circ_roi.sigRegionChanged.connect(self.on_update_circ_roi)
        
        self.hyperspec_data = None
        self.display_image = None
        self.spec_x_array = None
        
        self.scan_specific_setup()
        
    def scan_specific_setup(self):
        #override this!
        pass
        
    def is_file_supported(self, fname):
        # override this!
        return False
    
    def on_change_data_filename(self, fname):
        try:
            self.load_data(fname)
            self.databrowser.ui.statusbar.clearMessage()
            
        except Exception as err:
            #self.imview.setImage(np.zeros((10,10)))
            HyperSpectralBaseView.load_data(self, fname) # load default dummy data
            self.databrowser.ui.statusbar.showMessage("failed to load %s:\n%s" %(fname, err))
            raise(err)
        finally:        
            # pyqtgraph axes are x,y, but data is stored in (frame, y,x, time), so we need to transpose        
            self.imview.setImage(self.display_image.T)
            self.on_change_rect_roi()
            self.on_update_circ_roi()
    
    def load_data(self, fname):
        """
        override to set hyperspectral dataset and the display image
        need to define:
            * self.hyperspec_data (shape Ny, Nx, Nspec)
            * self.display_image (shape Ny, Nx)
            * self.spec_x_array (shape Nspec)
        """
        self.hyperspec_data = np.zeros((10,10,34))#np.random.rand(10,10,34)
        self.display_image =np.zeros((10,10,34))# np.random.rand(10,10)
        self.spec_x_array = 3*np.arange(34)
        
    def on_change_rect_roi(self):
        # pyqtgraph axes are x,y, but data is stored in (frame, y,x, time)
        roi_slice, roi_tr = self.rect_roi.getArraySlice(self.hyperspec_data, self.imview.getImageItem(), axes=(1,0)) 
        
        #print("roi_slice", roi_slice)
        self.rect_plotdata.setData(self.spec_x_array, self.hyperspec_data[roi_slice].mean(axis=(0,1))+1)
        
        
    def on_update_circ_roi(self, roi=None):
        if roi is None:
            roi = self.circ_roi

        roi_state = roi.saveState()
        #print roi_state
        #xc, y
        x0, y0 = roi_state['pos']
        xc = x0 + 1
        yc = y0 + 1
        
        #Nframe, Ny, Nx, Nt = self.time_trace_map.shape 
        #print 'Nframe, Ny, Nx, Nt', Nframe, Ny, Nx, Nt, 
        Ny, Nx, Nspec = self.hyperspec_data.shape
        
        i = max(0, min(int(xc),  Nx-1))
        j = max(0, min(int(yc),  Ny-1))
        
        #print "xc,yc,i,j", xc,yc, i,j
        
        self.circ_roi_plotline.setData([xc, i+0.5], [yc, j + 0.5])        
        
        self.point_plotdata.setData(self.spec_x_array, self.hyperspec_data[j,i,:])


if __name__ == '__main__':
    import sys
    
    app = DataBrowser(sys.argv)
    
    sys.exit(app.exec_())
    