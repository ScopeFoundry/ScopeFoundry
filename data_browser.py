from __future__ import division, print_function, absolute_import
from ScopeFoundry import BaseApp
from ScopeFoundry.helper_funcs import load_qt_ui_file, sibling_path,\
    load_qt_ui_from_pkg
from collections import OrderedDict
import os
from qtpy import QtCore, QtWidgets
import pyqtgraph as pg
import pyqtgraph.dockarea as dockarea
import numpy as np
from ScopeFoundry.logged_quantity import LQCollection


import time
import array

class DataBrowser(BaseApp):
    
    name = "DataBrowser"
    
    def __init__(self, argv):
        BaseApp.__init__(self, argv)
        self.setup()
    
    def setup(self):

        #self.ui = load_qt_ui_file(sibling_path(__file__, "data_browser.ui"))
        self.ui = load_qt_ui_from_pkg('ScopeFoundry', 'data_browser.ui')
        self.ui.show()
        self.ui.raise_()
        
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
        self.settings.view_name.connect_bidir_to_widget(self.ui.view_name_comboBox)
        self.settings.file_filter.connect_bidir_to_widget(self.ui.file_filter_lineEdit)
        
        # file system tree
        self.fs_model = QtWidgets.QFileSystemModel()
        self.fs_model.setRootPath(QtCore.QDir.currentPath())
        self.ui.treeView.setModel(self.fs_model)
        self.ui.treeView.setIconSize(QtCore.QSize(16,16))
        self.ui.treeView.setSortingEnabled(True)
        #for i in (1,2,3):
        #    self.ui.treeView.hideColumn(i)
        #print("="*80, self.ui.treeView.selectionModel())
        self.tree_selectionModel = self.ui.treeView.selectionModel()
        self.tree_selectionModel.selectionChanged.connect(self.on_treeview_selection_change)


        self.settings.browse_dir.add_listener(self.on_change_browse_dir)
        self.settings['browse_dir'] = os.getcwd()

        # set views
        
        self.load_view(FileInfoView(self))
        self.load_view(NPZView(self))

        self.settings.view_name.add_listener(self.on_change_view_name)
        self.settings['view_name'] = "file_info"
        
        self.settings.file_filter.add_listener(self.on_change_file_filter)
        
        #self.console_widget.show()
        self.ui.console_pushButton.clicked.connect(self.console_widget.show)
        self.ui.log_pushButton.clicked.connect(self.logging_widget.show)
        self.ui.show()
        

        
    def load_view(self, new_view):
        
        #instantiate view
        #new_view = ViewClass(self)
        
        self.log.debug('load_view called {}'.format(new_view))
        # add to views dict
        self.views[new_view.name] = new_view
        
        self.ui.dataview_groupBox.layout().addWidget(new_view.ui)
        new_view.ui.hide()
        
        # update choices for view_name
        self.settings.view_name.change_choice_list(list(self.views.keys()))
        self.log.debug('load_view done {}'.format(new_view))
        return new_view

    def on_change_data_filename(self):
        fname = self.settings.data_filename.val 
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
        

class DataBrowserView(QtCore.QObject):
    """ Abstract class for DataBrowser Views"""
    
    def __init__(self, databrowser):
        QtCore.QObject.__init__(self)
        self.databrowser =  databrowser
        self.settings = LQCollection()
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
        self.ui = QtWidgets.QTextEdit("file_info")
        
    def on_change_data_filename(self, fname=None):
        if fname is None:
            fname = self.databrowser.settings['data_filename']

        _, ext = os.path.splitext(fname)
        
        if ext in ('.py', '.ini', '.txt'):
            with open(fname, 'r') as f:
                self.ui.setText(f.read())
        else:
            self.ui.setText(fname)
        
    def is_file_supported(self, fname):
        return True


class NPZView(DataBrowserView):
    
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


class HyperSpectralBaseView(DataBrowserView):
    
    name = 'HyperSpectralBaseView'
    
    def setup(self):
        
        #self.ui = self.splitter = QtWidgets.QSplitter()
        #self.ui.setLayout(QtWidgets.QVBoxLayout())
        self.ui = self.dockarea = dockarea.DockArea()
        self.imview = pg.ImageView()
        self.imview.getView().invertY(False) # lower left origin
        #self.splitter.addWidget(self.imview)
        self.image_dock = self.dockarea.addDock(name='Image', widget=self.imview)
        self.graph_layout = pg.GraphicsLayoutWidget()
        #self.splitter.addWidget(self.graph_layout)
        self.spec_dock = self.dockarea.addDock(name='Spec Plot', widget=self.graph_layout)

        self.spec_plot = self.graph_layout.addPlot()
        self.spec_plot.setLabel('left', 'Intensity', units='counts') 
        self.rect_plotdata = self.spec_plot.plot()
        self.point_plotdata = self.spec_plot.plot(pen=(0,9))
        
        
        # Rectangle ROI
        self.rect_roi = pg.RectROI([20, 20], [20, 20], pen=(0,9))
        self.rect_roi.addTranslateHandle((0.5,0.5))        
        self.imview.getView().addItem(self.rect_roi)        
        self.rect_roi.sigRegionChanged[object].connect(self.on_change_rect_roi)
        
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
        self.circ_roi.sigRegionChanged[object].connect(self.on_update_circ_roi)
        
        self.corr_layout = pg.GraphicsLayoutWidget()
        self.corr_plot = self.corr_layout.addPlot()
        self.corr_plot.setLabel('left', 'intensity', units='')  
        self.corr_plot.setLabel('bottom', 'median wls', units='nm') 
        
        self.corr_plotdata = self.corr_plot.plot(symbol='o')
        self.dockarea.addDock(name='correlation', widget=self.corr_layout, 
                              position='below',  relativeTo = self.spec_dock)
        self.spec_dock.raiseDock()
        
        self.default_display_image_choices = ['default', 'sum']
        self.settings.New('display_image', str, choices = self.default_display_image_choices, initial = 'sum')    
        self.settings.display_image.add_listener(self.on_display_image_change)    
        
        self.default_x_axis_choices = ['default', 'index']
        self.x_axis = self.settings.New('x_axis', str, choices = self.default_x_axis_choices)
        self.x_axis.add_listener(self.on_x_axis_change)

        self.norm_data = self.settings.New('norm_data', bool, initial=False)
        self.norm_data.add_listener(self.update_display)
        self.settings.New('default_view', bool, initial=True)
        
        self.hyperspec_data = None
        self.display_image = None
        self.spec_x_array = None
        
        self.display_images = dict()
        self.spec_x_arrays = dict()        
        
        self.settings_widgets = [] #Not required
        
        self.scan_specific_setup()
        
        self.add_settings_dock() #Hack: Need to generate settings after scan_specific_setup()
        
    
    def add_settings_dock(self):
        self.settings_ui = self.settings.New_UI()
        ds = self.dockarea.addDock(name='settings', widget=self.settings_ui,
                                   position='left', relativeTo=self.image_dock)
        ds.setStretch(1,2)     

        self.update_display_pushButton = QtWidgets.QPushButton(text = 'update display')
        self.settings_ui.layout().addWidget(self.update_display_pushButton)
        self.update_display_pushButton.clicked.connect(self.update_display)  

        self.default_view_pushButton = QtWidgets.QPushButton(text = 'default img view')
        self.settings_ui.layout().addWidget(self.default_view_pushButton)
        self.default_view_pushButton.clicked.connect(self.default_image_view) 
        
        self.recalc_median_pushButton = QtWidgets.QPushButton(text = 'recalc_median')
        self.settings_widgets.append(self.recalc_median_pushButton)
        self.recalc_median_pushButton.clicked.connect(self.recalc_median_map)
        
        for w in self.settings_widgets:
            self.settings_ui.layout().addWidget(w)
        
    def add_spec_x_array(self, key, array):
        self.spec_x_arrays[key] = array
        self.settings.x_axis.add_choice(key, allow_duplicates=False)

    def add_display_image(self, key, image):
        self.display_images[key] = image
        self.settings.display_image.add_choice(key, allow_duplicates=False)
    
    def on_x_axis_change(self):
        key = self.settings['x_axis']
        if key in self.spec_x_arrays:
            self.spec_x_array = self.spec_x_arrays[key]
            self.spec_plot.setLabel('bottom', key)
            self.update_display()

    def on_display_image_change(self):
        key = self.settings['display_image']
        if key in self.display_images:
            self.display_image = self.display_images[key]
            self.update_display()
                
    def scan_specific_setup(self):
        #override this!
        pass
        
    def is_file_supported(self, fname):
        # override this!
        return False
    
    def on_change_data_filename(self, fname):
        self.reset()
        try:
            self.load_data(fname)
            self.display_images['default'] = self.display_image
            self.display_images['sum'] = self.hyperspec_data.sum(axis=-1)
            self.spec_x_arrays['default'] = self.spec_x_array
            self.spec_x_arrays['index'] = np.arange(self.hyperspec_data.shape[-1])
            self.databrowser.ui.statusbar.clearMessage()
            self.recalc_median_map()            
        except Exception as err:
            #self.imview.setImage(np.zeros((10,10)))
            HyperSpectralBaseView.load_data(self, fname) # load default dummy data
            self.databrowser.ui.statusbar.showMessage("failed to load %s:\n%s" %(fname, err))
            raise(err)
        finally:
            self.on_display_image_change()
            self.on_x_axis_change()

        if self.settings['default_view']:
            self.default_image_view()  
            
    def update_display(self):
        # pyqtgraph axes are x,y, but data is stored in (frame, y,x, time), so we need to transpose        
        self.imview.setImage(self.display_image.T)
        self.on_change_rect_roi()
        self.on_update_circ_roi()

    def reset(self):
        self.display_images = dict()
        self.spec_x_arrays = dict() 
        self.settings.display_image.change_choice_list(self.default_display_image_choices)
        self.settings.x_axis.change_choice_list(self.default_x_axis_choices)
    
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
    
    @QtCore.Slot(object)
    def on_change_rect_roi(self, roi=None):
        # pyqtgraph axes are x,y, but data is stored in (frame, y,x, time)
        # NOTE: If data is indeed stored as (frame, y, x, time) in self.hyperspec_data, then axis argument should be axes = (2,1)
        roi_slice, roi_tr = self.rect_roi.getArraySlice(self.hyperspec_data, self.imview.getImageItem(), axes=(1,0)) 
        
        #print("roi_slice", roi_slice)
        y = self.hyperspec_data[roi_slice].mean(axis=(0,1))+1
        if self.settings['norm_data']:
            y = norm(y)
        self.rect_plotdata.setData(self.spec_x_array, y)
        
    @QtCore.Slot(object)        
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
        
        self.circ_roi_ji = (j,i)       
        
        y = self.hyperspec_data[j,i,:]
        if self.settings['norm_data']:
            y = norm(y)      
        self.point_plotdata.setData(self.spec_x_array, y)
        
    def default_image_view(self):
        'sets rect_roi congruent to imageItem and optimizes size of imageItem to fit the ViewBox'
        iI = self.imview.imageItem
        h,w  = iI.height(), iI.width()       
        self.rect_roi.setSize((w,h))
        self.rect_roi.setPos((0,0))
        self.imview.autoRange()
        
    def recalc_median_map(self):
        median_map = spectral_median_map(self.hyperspec_data, wls=self.spec_x_array)
        self.add_display_image('median_map', median_map)
        x = self.display_images['median_map'].flatten()
        y = self.display_images['sum'].flatten()
        self.corr_plotdata.setData(x,y)
        
def spectral_median(spec, wls, count_min=200):
    int_spec = np.cumsum(spec)
    total_sum = int_spec[-1]
    if total_sum > count_min:
        pos = int_spec.searchsorted( 0.5*total_sum)
        wl = wls[pos]
    else:
        wl = 0
    return wl
def spectral_median_map(hyperspectral_data, wls):
    return np.apply_along_axis(spectral_median, -1, hyperspectral_data, wls=wls)

def norm(x):
    x_max = x.max()
    if x_max==0:
        return x*0.0
    else:
        return x*1.0/x_max
def norm_map(map_):
    return np.apply_along_axis(norm, -1, map_)

if __name__ == '__main__':
    import sys
    
    app = DataBrowser(sys.argv)
    
    sys.exit(app.exec_())
    