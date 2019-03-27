from __future__ import division, print_function, absolute_import
from ScopeFoundry import BaseApp
from ScopeFoundry.helper_funcs import load_qt_ui_file, sibling_path,\
    load_qt_ui_from_pkg
from ScopeFoundry.widgets import RegionSlicer
from collections import OrderedDict
import os
from qtpy import QtCore, QtWidgets, QtGui
import pyqtgraph as pg
import pyqtgraph.dockarea as dockarea
import numpy as np
from ScopeFoundry.logged_quantity import LQCollection
from scipy.stats import spearmanr
import argparse
import time
import h5py
from datetime import datetime

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

        self.ui = self.dockarea = dockarea.DockArea()
        self.imview = pg.ImageView()
        self.imview.getView().invertY(False) # lower left origin
        self.image_dock = self.dockarea.addDock(name='Image', widget=self.imview)
        self.graph_layout = pg.GraphicsLayoutWidget()
        self.spec_dock = self.dockarea.addDock(name='Spec Plot', widget=self.graph_layout)

        self.line_pens = ['w', 'r']
        self.spec_plot = self.graph_layout.addPlot()
        self.spec_plot.setLabel('left', 'Intensity', units='counts') 
        self.rect_plotdata = self.spec_plot.plot(y=[0,2,1,3,2],pen=self.line_pens[0])
        self.point_plotdata = self.spec_plot.plot(y=[0,2,1,3,2], pen=self.line_pens[1])
        self.point_plotdata.setZValue(-1)

        #correlation plot
        self.corr_layout = pg.GraphicsLayoutWidget()
        self.corr_plot = self.corr_layout.addPlot()
        self.corr_plotdata = pg.ScatterPlotItem(x=[0,1,2,3,4], y=[0,2,1,3,2], size=17, 
                                        pen=pg.mkPen(None), brush=pg.mkBrush(255, 255, 255, 60))
        self.corr_plot.addItem(self.corr_plotdata)        
        self.corr_dock = self.dockarea.addDock(name='correlation', widget=self.corr_layout, 
                              position='below',  relativeTo = self.spec_dock)
        self.spec_dock.raiseDock()
        
        
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
        
        #font
        font = QtGui.QFont("Times", 12)
        font.setBold(True)
            
        #settings
        self.default_display_image_choices = ['default', 'sum']
        self.settings.New('display_image', str, choices = self.default_display_image_choices, initial = 'default')    
        self.settings.display_image.add_listener(self.on_change_display_image)    
        
        self.default_x_axis_choices = ['default', 'index']
        self.x_axis = self.settings.New('x_axis', str, initial = 'default', choices = self.default_x_axis_choices)
        self.x_axis.add_listener(self.on_change_x_axis)

        self.norm_data = self.settings.New('norm_data', bool, initial = False)
        self.norm_data.add_listener(self.update_display)
        self.settings.New('default_view', bool, initial=True)
        
        self.binning = self.settings.New('binning', int, initial = 1, vmin=1)
        self.binning.add_listener(self.update_display)

        self.spatial_binning = self.settings.New('spatial_binning', int, initial = 1, vmin=1)
        self.spatial_binning.add_listener(self.bin_spatially)

        self.cor_X_data = self.settings.New('cor_X_data', str, choices = self.default_display_image_choices,
                                            initial = 'default')
        self.cor_Y_data = self.settings.New('cor_Y_data', str, choices = self.default_display_image_choices,
                                            initial = 'sum')
        self.cor_X_data.add_listener(self.on_change_corr_settings)
        self.cor_Y_data.add_listener(self.on_change_corr_settings)

        # data slicers
        self.x_slicer = RegionSlicer(self.spec_plot, name='x_slice',  slicer_updated_func=self.update_display, 
                                      brush = QtGui.QColor(0,255,0,70), ZValue=10, font = font, initial = [100,511])
        self.bg_slicer = RegionSlicer(self.spec_plot, name='bg_slice', slicer_updated_func=self.update_display, 
                                      brush = QtGui.QColor(255,255,255,70), ZValue=11, font = font, initial = [0,80])
                
        self.show_lines = ['show_circ_line','show_rect_line']
        for x in self.show_lines:
            lq = self.settings.New(x, bool, initial=True)
            lq.add_listener(self.on_change_show_lines)        
        
        self.hyperspec_data = None
        self.display_image = None
        self.spec_x_array = None
        
        self.display_images = dict()
        self.spec_x_arrays = dict()        

        self.settings_dock = self.dockarea.addDock(name='settings', position='left', relativeTo=self.image_dock)
        self.settings_widgets = [] # Hack part 1/2: allows to use settings.New_UI() and have settings defined in scan_specific_setup()
        self.settings_widgets.append(self.x_slicer.New_UI())
        self.settings_widgets.append(self.bg_slicer.New_UI())
        self.scan_specific_setup()
        self.generate_settings_ui() # Hack part 2/2: Need to generate settings after scan_specific_setup()

        
        #self.circ_roi_slice = self.rect_roi_slice = np.s_[:,:]

    
    def generate_settings_ui(self):
        self.settings_ui = self.settings.New_UI()
        self.settings_dock.addWidget(self.settings_ui)        

        #some more self.settings_widgets[]
        self.update_display_pushButton = QtWidgets.QPushButton(text = 'update display')
        self.settings_widgets.append(self.update_display_pushButton)
        self.update_display_pushButton.clicked.connect(self.update_display)  

        self.default_view_pushButton = QtWidgets.QPushButton(text = 'default img view')
        self.settings_widgets.append(self.default_view_pushButton)
        self.default_view_pushButton.clicked.connect(self.default_image_view) 
        
        self.recalc_median_pushButton = QtWidgets.QPushButton(text = 'recalc_median')
        self.settings_widgets.append(self.recalc_median_pushButton)
        self.recalc_median_pushButton.clicked.connect(self.recalc_median_map)

        self.recalc_sum_pushButton = QtWidgets.QPushButton(text = 'recalc_sum')
        self.settings_widgets.append(self.recalc_sum_pushButton)
        self.recalc_sum_pushButton.clicked.connect(self.recalc_sum_map)

        self.save_state_pushButton = QtWidgets.QPushButton(text = 'save_state')
        self.settings_widgets.append(self.save_state_pushButton)
        self.save_state_pushButton.clicked.connect(self.save_state)

        # Place the self.settings_widgets in a grid
        ui_widget =  QtWidgets.QWidget()
        gridLayout = QtWidgets.QGridLayout()
        ui_widget.setLayout(gridLayout)        
        for i,w in enumerate(self.settings_widgets):
            gridLayout.addWidget(w, int(i/2), i%2)
        self.settings_dock.addWidget(ui_widget)                               
        
    def add_spec_x_array(self, key, array):
        self.spec_x_arrays[key] = array
        self.settings.x_axis.add_choice(key, allow_duplicates=False)

    def add_display_image(self, key, image):
        self.display_images[key] = image
        self.settings.display_image.add_choice(key, allow_duplicates=False)
        self.cor_X_data.change_choice_list(self.display_images.keys())
        self.cor_Y_data.change_choice_list(self.display_images.keys())
        self.on_change_corr_settings()
    
    def get_xy(self, ji_slice, apply_use_x_slice=False):
        '''
        returns processed hyperspec_data averaged over a given spatial slice.
        '''
        x,hyperspec_dat = self.get_xhyperspec_data(apply_use_x_slice)
        y = hyperspec_dat[ji_slice].mean(axis=(0,1))
        self.databrowser.ui.statusbar.showMessage('get_xy(), counts in slice: {}'.format( y.sum() ) )

        if self.settings['norm_data']:
            y = norm(y)          
        return (x,y)

    def get_xhyperspec_data(self, apply_use_x_slice=True):
        '''
        returns processed hyperspec_data
        '''
        hyperspec_data = self.hyperspec_data
        if self.bg_slicer.activated.val:
            bg = hyperspec_data[:,:,self.bg_slicer.slice].mean()
        else:
            bg = 0
        x = self.spec_x_array
        if apply_use_x_slice and self.x_slicer.activated.val:
            x = x[self.x_slicer.slice]
            hyperspec_data = hyperspec_data[:,:,self.x_slicer.slice]
        binning = self.settings['binning']
        if  binning!= 1:
            x,hyperspec_data = bin_y_average_x(x, hyperspec_data, binning, -1, datapoints_lost_warning=False)   
        if self.settings['norm_data']:
            return (x,norm_map(hyperspec_data-bg))
        else:
            return (x,hyperspec_data-bg)
    
    def on_change_x_axis(self):
        key = self.settings['x_axis']
        if key in self.spec_x_arrays:
            self.spec_x_array = self.spec_x_arrays[key]
            self.x_slicer.set_x_array(self.spec_x_array)
            self.bg_slicer.set_x_array(self.spec_x_array)            
            self.spec_plot.setLabel('bottom', key)
            self.update_display()
            
    def on_change_display_image(self):
        key = self.settings['display_image']
        if key in self.display_images:
            self.display_image = self.display_images[key]
            self.update_display()
        if self.display_image.shape == (1,1):
            self.databrowser.ui.statusbar.showMessage('Can not display single pixel image!')
                
    def scan_specific_setup(self):
        #override this!
        pass
        
    def is_file_supported(self, fname):
        # override this!
        return False

    def post_load(self):
        # override this!
        pass    
    
    def on_change_data_filename(self, fname):
        self.reset()
        try:
            self.load_data(fname)
            if self.settings['spatial_binning'] != 1:
                self.hyperspec_data = bin_2D(self.hyperspec_data, self.settings['spatial_binning'])
                self.display_image = bin_2D(self.display_image, self.settings['spatial_binning'])
            self.display_images['default'] = self.display_image
            self.display_images['sum'] = self.hyperspec_data.sum(axis=-1)         
            self.spec_x_arrays['default'] = self.spec_x_array
            self.spec_x_arrays['index'] = np.arange(self.hyperspec_data.shape[-1])
            self.databrowser.ui.statusbar.clearMessage()
            self.post_load()
        except Exception as err:
            HyperSpectralBaseView.load_data(self, fname) # load default dummy data
            self.databrowser.ui.statusbar.showMessage("failed to load {}: {}".format(fname, err))
            raise(err)
        finally:
            self.on_change_display_image()
            self.on_change_corr_settings()
            self.update_display()
        self.on_change_x_axis()

        if self.settings['default_view']:
            self.default_image_view()   

    def update_display(self):
        # pyqtgraph axes are x,y, but data is stored in (frame, y,x, time), so we need to transpose        
        self.imview.setImage(self.display_image.T)
        self.on_change_rect_roi()
        self.on_update_circ_roi()

    def reset(self):
        '''
        resets the dictionaries
        '''
        k_to_delete = []
        for k in self.display_images.keys():
            if not k in self.default_display_image_choices:
                k_to_delete.append(k)
        for k in k_to_delete:
            self.display_images.pop(k)
        k_to_delete = []
        for k in self.spec_x_arrays.keys():
            if not k in self.default_x_axis_choices:
                k_to_delete.append(k)
        for k in k_to_delete:
            self.spec_x_arrays.pop(k)
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
        self.hyperspec_data = np.arange(10*10*34).reshape( (10,10,34) )
        self.display_image = self.hyperspec_data.sum(-1)# np.random.rand(10,10)
        self.spec_x_array = np.arange(34)
    
    @QtCore.Slot(object)
    def on_change_rect_roi(self, roi=None):
        # pyqtgraph axes are x,y, but data is stored in (frame, y,x, time)
        # NOTE: If data is indeed stored as (frame, y, x, time) in self.hyperspec_data, then axis argument should be axes = (2,1)
        roi_slice, roi_tr = self.rect_roi.getArraySlice(self.hyperspec_data, self.imview.getImageItem(), axes=(1,0)) 
        self.rect_roi_slice = roi_slice
        x,y = self.get_xy(roi_slice, apply_use_x_slice=False)
        self.rect_plotdata.setData(x, y)
        self.on_change_corr_settings()

        
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
        self.circ_roi_slice = np.s_[j:j+1,i:i+1]
        x,y = self.get_xy(self.circ_roi_slice, apply_use_x_slice=False)  
        self.point_plotdata.setData(x, y)
        self.on_change_corr_settings()

        
    def on_change_show_lines(self):
        if self.settings['show_circ_line']:
            self.point_plotdata.setOpacity(1)
        else:
            self.point_plotdata.setOpacity(0)
            
        if self.settings['show_rect_line']:
            self.rect_plotdata.setOpacity(1)
        else:
            self.rect_plotdata.setOpacity(0)       
        
    def default_image_view(self):
        'sets rect_roi congruent to imageItem and optimizes size of imageItem to fit the ViewBox'
        iI = self.imview.imageItem
        h,w  = iI.height(), iI.width()       
        self.rect_roi.setSize((w,h))
        self.rect_roi.setPos((0,0))
        self.imview.autoRange()
        
    def recalc_median_map(self):
        x,hyperspec_data = self.get_xhyperspec_data(apply_use_x_slice=True)
        median_map = spectral_median_map(hyperspec_data,x)
        self.add_display_image('median_map', median_map)
        
    def recalc_sum_map(self):
        x,hyperspec_data = self.get_xhyperspec_data(apply_use_x_slice=True)
        _sum = hyperspec_data.sum(-1)
        self.add_display_image('sum', _sum)
        
    def on_change_corr_settings(self):
        try:
            xname = self.settings['cor_X_data']
            yname = self.settings['cor_Y_data']
            X = self.display_images[xname]
            Y = self.display_images[yname]
            j,i = self.circ_roi_ji
            x_circ,y_circ = np.atleast_1d(X[j,i]),np.atleast_1d(Y[j,i])
            #mask selects points within rect_roi
            mask = np.zeros_like(X, dtype=bool)
            mask[self.rect_roi_slice[0:2]] = True
            mask_ = np.invert(mask)
            cor_x = X[mask].flatten()
            cor_y = Y[mask].flatten()
            self.corr_plotdata.setData(X[mask_].flat,Y[mask_].flat, brush=pg.mkBrush(255, 255, 255, 60), pen=None)
            self.corr_plotdata.addPoints(cor_x,cor_y, brush=pg.mkBrush(255, 255, 255, 60), pen=pg.mkPen(255, 0, 0, 200))
            self.corr_plotdata.addPoints(x=x_circ,y=y_circ, brush=pg.mkBrush(0, 0, 255, 255))
            self.corr_plot.autoRange()
            self.corr_plot.setLabels(**{'bottom':xname,'left':yname})
            sm = spearmanr(cor_x, cor_y)
            text = 'Pearson\'s: {:.3f}; Spearman\'s:corr={:.3f}, pvalue={:.3f}'.format(np.corrcoef(cor_x,cor_y)[0,1], 
                                    sm.correlation, sm.pvalue)
            self.corr_plot.setTitle(text)
        except Exception as err:
            self.databrowser.ui.statusbar.showMessage('Error in on_change_corr_settings: {}'.format(err))
        
    def bin_spatially(self):
        if not (self.settings['display_image'] in self.default_display_image_choices):
            self.settings.display_image.update_value( self.default_display_image_choices[0] )
        fname = self.databrowser.settings['data_filename']
        self.on_change_data_filename(fname)
    
    def save_state(self):
        from ScopeFoundry import h5_io
        fname = self.databrowser.settings['data_filename']
        view_state_fname = '{fname}_state_view_{timestamp:%y%m%d_%H%M%S}.{ext}'.format(
            fname = fname.strip('.h5'),
            timestamp=datetime.fromtimestamp(time.time()),
            ext='h5')
        h5_file = h5py.File(name = view_state_fname)
        
        with h5_file as h5_file:
            h5_group_display_images = h5_file.create_group('display_images')
            for k,v in self.display_images.items():
                h5_group_display_images.create_dataset(k, data=v)
            h5_group_spec_x_array = h5_file.create_group('spec_x_arrays')
            for k,v in self.spec_x_arrays.items():
                h5_group_spec_x_array.create_dataset(k, data=v)
            h5_group_settings_group = h5_file.create_group('settings')
            h5_io.h5_save_lqcoll_to_attrs(self.settings, h5_group_settings_group)
            h5_group_settings_group = h5_file.create_group('x_slicer_settings')
            h5_io.h5_save_lqcoll_to_attrs(self.x_slicer.settings, h5_group_settings_group)            
            h5_group_settings_group = h5_file.create_group('bg_slicer_settings')
            h5_io.h5_save_lqcoll_to_attrs(self.bg_slicer.settings, h5_group_settings_group)
            self.view_specific_save_state_func(h5_file)
            h5_file.close()          

    def view_specific_save_state_func(self, h5_file):
        '''
        you can override me, use 'h5_file' - it's already open 
        e.g:  h5_file.create_group('scan_specific_settings')
         ...
        '''
        pass
    
        
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

def bin_y_average_x(x, y, binning = 2, axis = -1, datapoints_lost_warning = True):
    '''
    y can be a n-dim array with length on axis `axis` equal to len(x)
    '''    
    new_len = int(x.__len__()/binning) * binning
    
    data_loss = x.__len__() - new_len
    if data_loss is not 0 and datapoints_lost_warning:
        print('bin_y_average_x() warining: lost final', data_loss, 'datapoints')
    
    def bin_1Darray(arr, binning=binning, new_len=new_len):
        return arr[:new_len].reshape((-1,binning)).sum(1)
    
    x_ = bin_1Darray(x) / binning
    y_ = np.apply_along_axis(bin_1Darray,axis,y)
    
    return x_, y_


def bin_2D(arr,binning=2):
    '''
    bins an array of at least 2 dimension along the axis 0 and 1
    '''
    shape = arr.shape
    new_dim = int(shape[0]/binning)
    salvaged_along_dim = new_dim*binning
    lost_lines_0 = shape[0]-salvaged_along_dim
    arr = arr[0:salvaged_along_dim].reshape((-1,binning,shape[1],*shape[2:])).sum(1)
    shape = arr.shape
    new_dim = int(shape[1]/binning)
    salvaged_along_dim = new_dim*binning
    lost_lines_1 = shape[1]-salvaged_along_dim
    arr = arr[:,0:salvaged_along_dim].reshape((shape[0],-1,binning,*shape[2:])).sum(2)
    if (lost_lines_1 + lost_lines_0) >0 :
        print('cropped data:', (lost_lines_0,lost_lines_1), 'lines lost' )
    return arr


if __name__ == '__main__':
    import sys
    
    app = DataBrowser(sys.argv)
    
    sys.exit(app.exec_())
    