'''
Created on Feb 4, 2016

@author: Edward Barnard
'''

from ScopeFoundry import Measurement
import numpy as np
import pyqtgraph as pg
import time
from ScopeFoundry import h5_io
from hardware_components import apd_counter
from PySide import QtCore
from ScopeFoundry import LQRange

class SimpleXYScan(Measurement):
    name = "simple_xy_scan"
    ui_filename = "ScopeFoundry/scanning/xy_scan_base.ui"
    
    def setup(self):
        self.display_update_period = 0.001 #seconds

        #connect events        

        # local logged quantities
        lq_params = dict(dtype=float, vmin=0,vmax=100, ro=False, unit='um' )
        self.h0 = self.add_logged_quantity('h0',  initial=25, **lq_params  )
        self.h1 = self.add_logged_quantity('h1',  initial=45, **lq_params  )
        self.v0 = self.add_logged_quantity('v0',  initial=25, **lq_params  )
        self.v1 = self.add_logged_quantity('v1',  initial=45, **lq_params  )

        lq_params = dict(dtype=float, vmin=1e-9,vmax=100, ro=False, unit='um' )
        self.dh = self.add_logged_quantity('dh', initial=1, **lq_params)
        self.dh.spinbox_decimals = 3
        self.dv = self.add_logged_quantity('dv', initial=1, **lq_params)
        self.dv.spinbox_decimals = 3
        
        self.Nh = self.add_logged_quantity('Nh', initial=11, vmin=1, dtype=int, ro=False)
        self.Nv = self.add_logged_quantity('Nv', initial=11, vmin=1, dtype=int, ro=False)

        #update Nh, Nv and other scan parameters when changes to inputs are made 
        #for lqname in 'h0 h1 v0 v1 dh dv'.split():
        #    self.logged_quantities[lqname].updated_value.connect(self.compute_scan_params)
        self.h_range = LQRange(self.h0, self.h1, self.dh, self.Nh)
        self.h_range.updated_range.connect(self.compute_scan_params)

        self.v_range = LQRange(self.v0, self.v1, self.dv, self.Nv)
        self.v_range.updated_range.connect(self.compute_scan_params) #update other scan parameters when changes to inputs are made

        
        #connect events
        self.ui.start_pushButton.clicked.connect(self.start)
        self.ui.interrupt_pushButton.clicked.connect(self.interrupt)

        self.h0.connect_bidir_to_widget(self.ui.h0_doubleSpinBox)
        self.h1.connect_bidir_to_widget(self.ui.h1_doubleSpinBox)
        self.v0.connect_bidir_to_widget(self.ui.v0_doubleSpinBox)
        self.v1.connect_bidir_to_widget(self.ui.v1_doubleSpinBox)
        self.dh.connect_bidir_to_widget(self.ui.dh_doubleSpinBox)
        self.dv.connect_bidir_to_widget(self.ui.dv_doubleSpinBox)
        self.Nh.connect_bidir_to_widget(self.ui.Nh_doubleSpinBox)
        self.Nv.connect_bidir_to_widget(self.ui.Nv_doubleSpinBox)
        
        
        
        self.progress.connect_bidir_to_widget(self.ui.progress_doubleSpinBox)
        #self.progress.updated_value[str].connect(self.ui.xy_scan_progressBar.setValue)
        #self.progress.updated_value.connect(self.tree_progressBar.setValue)

        self.initial_scan_setup_plotting = False
        self.display_image_map = np.zeros((10,10), dtype=float)
        self.scan_specific_setup()

    def compute_scan_params(self):
        # Don't recompute if a scan is running!
        if self.is_measuring():
            return # maybe raise error

        self.h_array = self.h_range.array #np.arange(self.h0.val, self.h1.val, self.dh.val, dtype=float)
        self.v_array = self.v_range.array #np.arange(self.v0.val, self.v1.val, self.dv.val, dtype=float)
        
        #self.Nh.update_value(len(self.h_array))
        #self.Nv.update_value(len(self.v_array))
        
        self.range_extent = [self.h0.val, self.h1.val, self.v0.val, self.v1.val]

        self.corners =  [self.h_array[0], self.h_array[-1], self.v_array[0], self.v_array[-1]]
        
        self.imshow_extent = [self.h_array[ 0] - 0.5*self.dh.val,
                              self.h_array[-1] + 0.5*self.dh.val,
                              self.v_array[ 0] - 0.5*self.dv.val,
                              self.v_array[-1] + 0.5*self.dv.val]
                
    
    def _run(self):
        
        # set all logged quantities read only
        for lqname in "h0 h1 v0 v1 dh dv Nh Nv".split():
            self.logged_quantities[lqname].change_readonly(True)
        
        #Hardware
        # self.apd_counter_hc = self.gui.hardware_components['apd_counter']
        # self.apd_count_rate = self.apd_counter_hc.apd_count_rate
        # self.stage = self.gui.hardware_components['dummy_xy_stage']

        # Data File
        # H5

        # Compute data arrays
        self.compute_scan_params()
        
        self.initial_scan_setup_plotting = True
        
        try:
            # h5 data file setup
            self.t0 = time.time()
            self.h5_file = h5_io.h5_base_file(self.gui, "%i_%s.h5" % (self.t0, self.name) )
            self.h5_file.attrs['time_id'] = self.t0
            H = self.h5_meas_group = self.h5_file.create_group(self.name)        
            
            #create h5 data arrays
            H['h_array'] = self.h_array
            H['v_array'] = self.v_array
            H['range_extent'] = self.range_extent
            H['corners'] = self.corners
            H['imshow_extent'] = self.imshow_extent
            
            self.pre_scan_setup()
            
            # start scan
            self.pixel_i = 0
            for jj, y in enumerate(self.v_array):
                if self.interrupt_measurement_called: break
                self.stage.y_position.update_value(y)
                self.h5_file.flush() # flush data to file every line
                for ii, x in enumerate(self.h_array):
                    if self.interrupt_measurement_called: break                    
                    self.stage.x_position.update_value(x)
                    # each pixel:
                    # acquire signal and save to data array
                    self.pixel_i += 1
                    self.collect_pixel(jj, ii)
                    self.progress.update_value(100.0*self.pixel_i / (self.Nh.val*self.Nv.val))
        finally:
            # set all logged quantities writable
            for lqname in "h0 h1 v0 v1 dh dv Nh Nv".split():
                self.logged_quantities[lqname].change_readonly(False)
            
            self.h5_file.close()
            
    def clear_qt_attr(self, attr_name):
        if hasattr(self, attr_name):
            attr = getattr(self, attr_name)
            attr.deleteLater()
            del attr
            
    def setup_figure(self):
        self.compute_scan_params()
            
        self.clear_qt_attr('graph_layout')
        self.graph_layout=pg.GraphicsLayoutWidget(border=(100,100,100))
        self.ui.plot_groupBox.layout().addWidget(self.graph_layout)
        
        self.clear_qt_attr('img_plot')
        self.img_plot = self.graph_layout.addPlot()
        self.img_item = pg.ImageItem()
        self.img_plot.addItem(self.img_item)
        self.img_plot.showGrid(x=True, y=True)
        self.img_plot.setAspectLocked(lock=True, ratio=1)
        
        
        #self.clear_qt_attr('current_stage_pos_arrow')
        self.current_stage_pos_arrow = pg.ArrowItem()
        self.current_stage_pos_arrow.setZValue(100)
        self.img_plot.addItem(self.current_stage_pos_arrow)
        
        #self.stage = self.gui.hardware_components['dummy_xy_stage']
        self.stage.x_position.updated_value.connect(self.update_arrow_pos, QtCore.Qt.UniqueConnection)
        self.stage.y_position.updated_value.connect(self.update_arrow_pos, QtCore.Qt.UniqueConnection)
        
        self.graph_layout.nextRow()
        self.pos_label = pg.LabelItem(justify='right')
        self.pos_label.setText("=====")
        self.graph_layout.addItem(self.pos_label)

        self.scan_roi = pg.ROI([0,0],[1,1], movable=True)
        self.scan_roi.addScaleHandle([1, 1], [0, 0])
        self.scan_roi.addScaleHandle([0, 0], [1, 1])
        self.update_scan_roi()
        self.scan_roi.sigRegionChangeFinished.connect(self.mouse_update_scan_roi)
        
        self.img_plot.addItem(self.scan_roi)        
        for lqname in 'h0 h1 v0 v1 dh dv'.split():
            self.logged_quantities[lqname].updated_value.connect(self.update_scan_roi)
                    
        self.img_plot.scene().sigMouseMoved.connect(self.mouseMoved)
    
    def mouse_update_scan_roi(self):
        x0,y0 =  self.scan_roi.pos()
        w, h =  self.scan_roi.size()
        print x0,y0, w, h
        self.h0.update_value(x0+self.dh.val)
        self.h1.update_value(x0+w-self.dh.val)
        self.v0.update_value(y0+self.dv.val)
        self.v1.update_value(y0+h-self.dv.val)
        self.compute_scan_params()
        self.update_scan_roi()
        
    def update_scan_roi(self):
        x0, x1, y0, y1 = self.imshow_extent
        self.scan_roi.blockSignals(True)
        self.scan_roi.setPos( (x0, y0, 0))
        self.scan_roi.setSize( (x1-x0, y1-y0, 0))
        self.scan_roi.blockSignals(False)
        
    def update_arrow_pos(self):
        x = self.stage.x_position.val
        y = self.stage.y_position.val
        self.current_stage_pos_arrow.setPos(x,y)
    
    def update_display(self):
        if self.initial_scan_setup_plotting:
            self.img_item = pg.ImageItem()
            self.img_plot.addItem(self.img_item)
            #self.hist_lut.setImageItem(self.img_item)
    
            self.img_item.setImage(self.display_image_map.T)
            x0, x1, y0, y1 = self.imshow_extent
            print x0, x1, y0, y1
            self.img_item.setRect(QtCore.QRectF(x0, y0, x1-x0, y1-y0))
            
            self.initial_scan_setup_plotting = False
        else:
            self.img_item.setImage(self.apd_map.T, autoRange=False, autoLevels=False)
            #self.hist_lut.imageChanged(autoLevel=True)        
    
    def mouseMoved(self,evt):
        mousePoint = self.img_plot.vb.mapSceneToView(evt)
        #print mousePoint
        
        #self.pos_label_text = "H {:+02.2f} um [{}], V {:+02.2f} um [{}]: {:1.2e} Hz ".format(
        #                mousePoint.x(), ii, mousePoint.y(), jj,
        #                self.count_rate_map[jj,ii] 
        #                )

        self.pos_label.setText(
            "H {:+02.2f} um [{}], V {:+02.2f} um [{}]: {:1.2e} Hz".format(
                        mousePoint.x(), 0, mousePoint.y(), 0, 0))

    def scan_specific_setup(self):
        "subclass this function to setup additional logged quantities and gui connections"
        self.stage = self.gui.hardware_components['dummy_xy_stage']
        
        #self.gui.hardware_components['dummy_xy_stage'].x_position.connect_bidir_to_widget(self.ui.x_doubleSpinBox)
        #self.gui.hardware_components['dummy_xy_stage'].y_position.connect_bidir_to_widget(self.ui.y_doubleSpinBox)
        
        #self.gui.hardware_components['apd_counter'].int_time.connect_bidir_to_widget(self.ui.int_time_doubleSpinBox)
       
       
       
        # logged quantities
        # connect events
        
    
    def pre_scan_setup(self):
        print self.name, "pre_scan_setup not implemented"
        # hardware
        # create data arrays
        # update figure
    
    def collect_pixel(self, i_h, i_v):
        # collect data
        # store in arrays        
        print self.name, "collect_pixel", i_h, i_v, "not implemented"
    
    def post_scan_cleanup(self):
        print self.name, "post_scan_setup not implemented"

