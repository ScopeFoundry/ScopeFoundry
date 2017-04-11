'''
Created on Feb 4, 2016

@author: Edward Barnard
'''

from ScopeFoundry import Measurement
from ScopeFoundry.helper_funcs import sibling_path, load_qt_ui_file
import numpy as np
import pyqtgraph as pg
import time
from ScopeFoundry import h5_io
from qtpy import QtCore
from ScopeFoundry import LQRange
import os

def ijk_zigzag_generator(dims, axis_order=(0,1,2)):
    """3D zig-zag scan pattern generator with arbitrary fast axis order"""

    ax0, ax1, ax2 = axis_order
    
    for i_ax0 in range( dims[ax0] ):
        zig_or_zag0 = (1,-1)[i_ax0 % 2]
        for i_ax1 in range( dims[ax1] )[::zig_or_zag0]:
            zig_or_zag1 = (1,-1)[(i_ax0+i_ax1) % 2]
            for i_ax2 in range( dims[ax2] )[::zig_or_zag1]:
            
                ijk = [0,0,0]
                ijk[ax0] = i_ax0
                ijk[ax1] = i_ax1
                ijk[ax2] = i_ax2
                
                yield tuple(ijk)
    return

class BaseRaster2DScan(Measurement):
    name = "base_raster_2Dscan"
    
    def __init__(self, app, h_limits=(-1,1), v_limits=(-1,1), h_unit='', v_unit=''):
        self.h_limits = h_limits
        self.v_limits = v_limits
        self.h_unit = h_unit
        self.v_unit = v_unit
        Measurement.__init__(self, app)
        
    def setup(self):
        self.ui_filename = sibling_path(__file__,"raster_scan_base.ui")
        self.ui = load_qt_ui_file(self.ui_filename)
        #self.ui.show()
        self.ui.setWindowTitle(self.name)

        self.display_update_period = 0.010 #seconds

        #connect events        

        # local logged quantities
        lq_params = dict(dtype=float, vmin=self.h_limits[0],vmax=self.h_limits[1], ro=False, unit=self.h_unit )
        self.h0 = self.settings.New('h0',  initial=self.h_limits[0], **lq_params  )
        self.h1 = self.settings.New('h1',  initial=self.h_limits[1], **lq_params  )
        lq_params = dict(dtype=float, vmin=self.v_limits[0],vmax=self.v_limits[1], ro=False, unit=self.h_unit )
        self.v0 = self.settings.New('v0',  initial=self.v_limits[0], **lq_params  )
        self.v1 = self.settings.New('v1',  initial=self.v_limits[1], **lq_params  )

        lq_params = dict(dtype=float, vmin=1e-9, vmax=abs(self.h_limits[1]-self.h_limits[0]), ro=False, unit=self.h_unit )
        self.dh = self.settings.New('dh', initial=0.1, **lq_params)
        self.dh.spinbox_decimals = 3
        lq_params = dict(dtype=float, vmin=1e-9, vmax=abs(self.v_limits[1]-self.v_limits[0]), ro=False, unit=self.v_unit )
        self.dv = self.settings.New('dv', initial=0.1, **lq_params)
        self.dv.spinbox_decimals = 3
        
        self.Nh = self.settings.New('Nh', initial=11, vmin=1, dtype=int, ro=False)
        self.Nv = self.settings.New('Nv', initial=11, vmin=1, dtype=int, ro=False)
        
        self.Npixels = self.Nh.val*self.Nv.val
        
        
        self.scan_type = self.settings.New('scan_type', dtype=str, initial='raster',
                                                  choices=('raster', 'serpentine', 'trace_retrace', 
                                                           'ortho_raster', 'ortho_trace_retrace'))
        
        self.continuous_scan = self.settings.New("continuous_scan", dtype=bool, initial=False)
        self.settings.New('save_h5', dtype=bool, initial=True, ro=False)
        
        self.settings.New('show_previous_scans', dtype=bool, initial=True)
        
        
        self.settings.New('n_frames', dtype=int, initial=1, vmin=1)
        
        self.settings.New('pixel_time', dtype=float, ro=True, si=True, initial=1, unit='s')
        self.settings.New('line_time' , dtype=float, ro=True, si=True, unit='s')
        self.settings.New('frame_time' , dtype=float, ro=True, si=True, unit='s')        
        self.settings.New('total_time', dtype=float, ro=True, si=True, unit='s')
        
        for lq_name in ['Nh', 'Nv', 'pixel_time', 'n_frames']:
            self.settings.get_lq(lq_name).add_listener(self.compute_times)
            
        self.compute_times()
        
        #update Nh, Nv and other scan parameters when changes to inputs are made 
        #for lqname in 'h0 h1 v0 v1 dh dv'.split():
        #    self.logged_quantities[lqname].updated_value.connect(self.compute_scan_params)
        self.h_range = LQRange(self.h0, self.h1, self.dh, self.Nh)
        self.h_range.updated_range.connect(self.compute_scan_params)

        self.v_range = LQRange(self.v0, self.v1, self.dv, self.Nv)
        self.v_range.updated_range.connect(self.compute_scan_params) #update other scan parameters when changes to inputs are made

        self.scan_type.updated_value.connect(self.compute_scan_params)
        
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
        self.scan_type.connect_bidir_to_widget(self.ui.scan_type_comboBox)
        
        self.progress.connect_bidir_to_widget(self.ui.progress_doubleSpinBox)
        #self.progress.updated_value[str].connect(self.ui.xy_scan_progressBar.setValue)
        #self.progress.updated_value.connect(self.tree_progressBar.setValue)

        self.settings.continuous_scan.connect_to_widget(
            self.ui.continuous_scan_checkBox)
        self.settings.save_h5.connect_to_widget(
            self.ui.save_h5_checkBox)

        self.settings.show_previous_scans.connect_to_widget(
            self.ui.show_previous_scans_checkBox)

        self.initial_scan_setup_plotting = False
        self.display_image_map = np.zeros(self.scan_shape, dtype=float)
        self.scan_specific_setup()
        

        self.add_operation('clear_previous_scans', self.clear_previous_scans)

        self.ui.clear_previous_scans_pushButton.clicked.connect(
            self.clear_previous_scans)
        
    def set_h_limits(self, vmin, vmax, set_scan_to_max=False):
        self.settings.h0.change_min_max(vmin, vmax)
        self.settings.h1.change_min_max(vmin, vmax)
        if set_scan_to_max:
            self.settings['h0'] = vmin
            self.settings['h1'] = vmax
    def set_v_limits(self, vmin, vmax, set_scan_to_max=False):
        self.settings.v0.change_min_max(vmin, vmax)
        self.settings.v1.change_min_max(vmin, vmax)
        if set_scan_to_max:
            self.settings['v0'] = vmin
            self.settings['v1'] = vmax

    def compute_scan_params(self):
        self.log.debug('compute_scan_params')
        # Don't recompute if a scan is running!
        if self.is_measuring():
            return # maybe raise error

        #self.h_array = self.h_range.array #np.arange(self.h0.val, self.h1.val, self.dh.val, dtype=float)
        #self.v_array = self.v_range.array #np.arange(self.v0.val, self.v1.val, self.dv.val, dtype=float)
        
        #self.Nh.update_value(len(self.h_array))
        #self.Nv.update_value(len(self.v_array))
        
        self.range_extent = [self.h0.val, self.h1.val, self.v0.val, self.v1.val]

        #self.corners =  [self.h_array[0], self.h_array[-1], self.v_array[0], self.v_array[-1]]
        self.corners = self.range_extent
        
        self.imshow_extent = [self.h0.val - 0.5*self.dh.val,
                              self.h1.val + 0.5*self.dh.val,
                              self.v0.val - 0.5*self.dv.val,
                              self.v1.val + 0.5*self.dv.val]
        
        self.compute_times()
        
        # call appropriate scan generator to determine scan size, don't compute scan arrays yet
        getattr(self, "gen_%s_scan" % self.scan_type.val)(gen_arrays=False)
    
    def compute_scan_arrays(self):
        print("params")
        self.compute_scan_params()
        gen_func_name = "gen_%s_scan" % self.scan_type.val
        print("gen_arrays:", gen_func_name)
        # calls correct scan generator function
        getattr(self, gen_func_name)(gen_arrays=True)
    
    def create_empty_scan_arrays(self):
        self.scan_h_positions = np.zeros(self.Npixels, dtype=float)
        self.scan_v_positions = np.zeros(self.Npixels, dtype=float)
        self.scan_slow_move   = np.zeros(self.Npixels, dtype=bool)
        self.scan_index_array = np.zeros((self.Npixels, 3), dtype=int)

    def pre_run(self):
        # set all logged quantities read only
        for lqname in "h0 h1 v0 v1 dh dv Nh Nv".split():
            self.settings.as_dict()[lqname].change_readonly(True)
    
    
    
    
    
    def post_run(self):
            # set all logged quantities writable
            for lqname in "h0 h1 v0 v1 dh dv Nh Nv".split():
                self.settings.as_dict()[lqname].change_readonly(False)

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

        self.img_items = []
        
        
        self.img_item = pg.ImageItem()
        self.img_items.append(self.img_item)
        
        self.img_plot.addItem(self.img_item)
        self.img_plot.showGrid(x=True, y=True)
        self.img_plot.setAspectLocked(lock=True, ratio=1)

        self.hist_lut = pg.HistogramLUTItem()
        self.graph_layout.addItem(self.hist_lut)

        
        #self.clear_qt_attr('current_stage_pos_arrow')
        self.current_stage_pos_arrow = pg.ArrowItem()
        self.current_stage_pos_arrow.setZValue(100)
        self.img_plot.addItem(self.current_stage_pos_arrow)
        
        #self.stage = self.app.hardware_components['dummy_xy_stage']
        if hasattr(self, 'stage'):
            self.stage.settings.x_position.updated_value.connect(self.update_arrow_pos, QtCore.Qt.UniqueConnection)
            self.stage.settings.y_position.updated_value.connect(self.update_arrow_pos, QtCore.Qt.UniqueConnection)
            
            self.stage.settings.x_position.connect_to_widget(self.ui.x_doubleSpinBox)
            self.stage.settings.y_position.connect_to_widget(self.ui.y_doubleSpinBox)

        
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
            self.settings.as_dict()[lqname].updated_value.connect(self.update_scan_roi)
                    
        self.img_plot.scene().sigMouseMoved.connect(self.mouseMoved)
    
    def mouse_update_scan_roi(self):
        x0,y0 =  self.scan_roi.pos()
        w, h =  self.scan_roi.size()
        #print x0,y0, w, h
        self.h0.update_value(x0+self.dh.val)
        self.h1.update_value(x0+w-self.dh.val)
        self.v0.update_value(y0+self.dv.val)
        self.v1.update_value(y0+h-self.dv.val)
        self.compute_scan_params()
        self.update_scan_roi()
        
    def update_scan_roi(self):
        self.log.debug("update_scan_roi")
        x0, x1, y0, y1 = self.imshow_extent
        self.scan_roi.blockSignals(True)
        self.scan_roi.setPos( (x0, y0, 0))
        self.scan_roi.setSize( (x1-x0, y1-y0, 0))
        self.scan_roi.blockSignals(False)
        
    def update_arrow_pos(self):
        x = self.stage.settings['x_position']
        y = self.stage.settings['y_position']
        self.current_stage_pos_arrow.setPos(x,y)
    
    def update_display(self):
        #self.log.debug('update_display')
        if self.initial_scan_setup_plotting:
            if self.settings['show_previous_scans']:
                self.img_item = pg.ImageItem()
                self.img_items.append(self.img_item)
                self.img_plot.addItem(self.img_item)
                self.hist_lut.setImageItem(self.img_item)
    
            self.img_item.setImage(self.display_image_map[0,:,:])
            x0, x1, y0, y1 = self.imshow_extent
            self.log.debug('update_display set bounds {} {} {} {}'.format(x0, x1, y0, y1))
            self.img_item_rect = QtCore.QRectF(x0, y0, x1-x0, y1-y0)
            self.img_item.setRect(self.img_item_rect)
            self.log.debug('update_display set bounds {}'.format(self.img_item_rect))
            
            self.initial_scan_setup_plotting = False
        else:
            #if self.settings.scan_type.val in ['raster']
            kk, jj, ii = self.current_scan_index
            self.img_item.setImage(self.display_image_map[kk,:,:].T, autoRange=False, autoLevels=False)
            self.img_item.setRect(self.img_item_rect) # Important to set rectangle after setImage for non-square pixels
            self.update_LUT()
            
    def update_LUT(self):
        ''' override this function to control display LUT scaling'''
        self.hist_lut.imageChanged(autoLevel=True)
               
    def clear_previous_scans(self):
        #current_img = img_items.pop()
        for img_item in self.img_items[:-1]:
            print('removing', img_item)
            self.img_plot.removeItem(img_item)  
            img_item.deleteLater()
    
        self.img_items = [self.img_item,]
    
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
        pass
        #self.stage = self.app.hardware.dummy_xy_stage
        
        #self.app.hardware_components['dummy_xy_stage'].x_position.connect_bidir_to_widget(self.ui.x_doubleSpinBox)
        #self.app.hardware_components['dummy_xy_stage'].y_position.connect_bidir_to_widget(self.ui.y_doubleSpinBox)
        
        #self.app.hardware_components['apd_counter'].int_time.connect_bidir_to_widget(self.ui.int_time_doubleSpinBox)
       
       
       
        # logged quantities
        # connect events
        
    
    
    @property
    def h_array(self):
        return self.h_range.array

    @property
    def v_array(self):
        return self.v_range.array

    def compute_times(self):
        #self.settings['pixel_time'] = 1.0/self.scanDAQ.settings['dac_rate']
        S = self.settings
        S['line_time']  = S['pixel_time'] * S['Nh']
        S['frame_time'] = S['pixel_time'] * self.Npixels
        S['total_time'] = S['frame_time'] * S['n_frames']
    
    #### Scan Generators
    def gen_raster_scan(self, gen_arrays=True):
        self.Npixels = self.Nh.val*self.Nv.val
        self.scan_shape = (1, self.Nv.val, self.Nh.val)
        
        if gen_arrays:
            #print "t0", time.time() - t0
            self.create_empty_scan_arrays()            
            #print "t1", time.time() - t0
            
#             t0 = time.time()
#             pixel_i = 0
#             for jj in range(self.Nv.val):
#                 #print "tjj", jj, time.time() - t0
#                 self.scan_slow_move[pixel_i] = True
#                 for ii in range(self.Nh.val):
#                     self.scan_v_positions[pixel_i] = self.v_array[jj]
#                     self.scan_h_positions[pixel_i] = self.h_array[ii]
#                     self.scan_index_array[pixel_i,:] = [0, jj, ii] 
#                     pixel_i += 1
#             print "for loop raster gen", time.time() - t0
             
            t0 = time.time()
             
            H, V = np.meshgrid(self.h_array, self.v_array)
            self.scan_h_positions[:] = H.flat
            self.scan_v_positions[:] = V.flat
            
            II,JJ = np.meshgrid(np.arange(self.Nh.val), np.arange(self.Nv.val))
            self.scan_index_array[:,1] = JJ.flat
            self.scan_index_array[:,2] = II.flat
            #self.scan_v_positions
            print("array flatten raster gen", time.time() - t0)
            
        
    def gen_serpentine_scan(self, gen_arrays=True):
        self.Npixels = self.Nh.val*self.Nv.val
        self.scan_shape = (1, self.Nv.val, self.Nh.val)

        if gen_arrays:
            self.create_empty_scan_arrays()
            pixel_i = 0
            for jj in range(self.Nv.val):
                self.scan_slow_move[pixel_i] = True
                
                if jj % 2: #odd lines
                    h_line_indicies = range(self.Nh.val)[::-1]
                else:       #even lines -- traverse in opposite direction
                    h_line_indicies = range(self.Nh.val)            
        
                for ii in h_line_indicies:            
                    self.scan_v_positions[pixel_i] = self.v_array[jj]
                    self.scan_h_positions[pixel_i] = self.h_array[ii]
                    self.scan_index_array[pixel_i,:] = [0, jj, ii]                 
                    pixel_i += 1
                
    def gen_trace_retrace_scan(self, gen_arrays=True):
        self.Npixels = 2*self.Nh.val*self.Nv.val
        self.scan_shape = (2, self.Nv.val, self.Nh.val)

        if gen_arrays:
            self.create_empty_scan_arrays()
            pixel_i = 0
            for jj in range(self.Nv.val):
                self.scan_slow_move[pixel_i] = True     
                for kk, step in [(0,1),(1,-1)]: # trace kk =0, retrace kk=1
                    h_line_indicies = range(self.Nh.val)[::step]
                    for ii in h_line_indicies:            
                        self.scan_v_positions[pixel_i] = self.v_array[jj]
                        self.scan_h_positions[pixel_i] = self.h_array[ii]
                        self.scan_index_array[pixel_i,:] = [kk, jj, ii]                 
                        pixel_i += 1
    
    def gen_ortho_raster_scan(self, gen_arrays=True):
        self.Npixels = 2*self.Nh.val*self.Nv.val
        self.scan_shape = (2, self.Nv.val, self.Nh.val)

        if gen_arrays:
            self.create_empty_scan_arrays()
            pixel_i = 0
            for jj in range(self.Nv.val):
                self.scan_slow_move[pixel_i] = True
                for ii in range(self.Nh.val):
                    self.scan_v_positions[pixel_i] = self.v_array[jj]
                    self.scan_h_positions[pixel_i] = self.h_array[ii]
                    self.scan_index_array[pixel_i,:] = [0, jj, ii] 
                    pixel_i += 1
            for ii in range(self.Nh.val):
                self.scan_slow_move[pixel_i] = True
                for jj in range(self.Nv.val):
                    self.scan_v_positions[pixel_i] = self.v_array[jj]
                    self.scan_h_positions[pixel_i] = self.h_array[ii]
                    self.scan_index_array[pixel_i,:] = [1, jj, ii] 
                    pixel_i += 1
    
    def gen_ortho_trace_retrace_scan(self, gen_arrays=True):
        print("gen_ortho_trace_retrace_scan")
        self.Npixels = 4*len(self.h_array)*len(self.v_array) 
        self.scan_shape = (4, self.Nv.val, self.Nh.val)                        
        
        if gen_arrays:
            self.create_empty_scan_arrays()
            pixel_i = 0
            for jj in range(self.Nv.val):
                self.scan_slow_move[pixel_i] = True     
                for kk, step in [(0,1),(1,-1)]: # trace kk =0, retrace kk=1
                    h_line_indicies = range(self.Nh.val)[::step]
                    for ii in h_line_indicies:            
                        self.scan_v_positions[pixel_i] = self.v_array[jj]
                        self.scan_h_positions[pixel_i] = self.h_array[ii]
                        self.scan_index_array[pixel_i,:] = [kk, jj, ii]                 
                        pixel_i += 1
            for ii in range(self.Nh.val):
                self.scan_slow_move[pixel_i] = True     
                for kk, step in [(2,1),(3,-1)]: # trace kk =2, retrace kk=3
                    v_line_indicies = range(self.Nv.val)[::step]
                    for jj in v_line_indicies:            
                        self.scan_v_positions[pixel_i] = self.v_array[jj]
                        self.scan_h_positions[pixel_i] = self.h_array[ii]
                        self.scan_index_array[pixel_i,:] = [kk, jj, ii]                 
                        pixel_i += 1
                    



