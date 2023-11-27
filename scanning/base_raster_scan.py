'''
Created on Feb 4, 2016

@author: Edward Barnard
'''

from ScopeFoundry import Measurement
from ScopeFoundry.helper_funcs import sibling_path, load_qt_ui_file,replace_widget_in_layout
import numpy as np
import pyqtgraph as pg
import time
from qtpy import QtCore
from ScopeFoundry import LQRange

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
    name = "base_raster_2D_scan"
    
    def __init__(self, app, 
                 h_limits=(-1,1),        v_limits=(-1,1), 
                 h_unit='',              v_unit='', 
                 h_spinbox_decimals=4,   v_spinbox_decimals=4,
                 h_spinbox_step=0.1,     v_spinbox_step=0.1,
                 use_external_range_sync=False,
                 circ_roi_size=1.0,
                 ):        
        self.h_spinbox_decimals = h_spinbox_decimals
        self.v_spinbox_decimals = v_spinbox_decimals
        self.h_spinbox_step = h_spinbox_step
        self.v_spinbox_step = v_spinbox_step
        self.h_limits = h_limits
        self.v_limits = v_limits
        self.h_unit = h_unit
        self.v_unit = v_unit
        self.use_external_range_sync = use_external_range_sync
        self.circ_roi_size=circ_roi_size
        self.img_items = []
        Measurement.__init__(self, app)
        
    def setup(self):
        self.ui_filename = sibling_path(__file__,"raster_scan_base.ui")
        self.ui = load_qt_ui_file(self.ui_filename)
        #self.ui.show()
        self.ui.setWindowTitle(self.name)

        self.display_update_period = 0.010 #seconds

        #connect events        

        # local logged quantities
        h_lq_params = dict(vmin=self.h_limits[0], vmax=self.h_limits[1], unit=self.h_unit, 
                                spinbox_decimals=self.h_spinbox_decimals, spinbox_step=self.h_spinbox_step,
                                dtype=float,ro=False)
        h_range = self.h_limits[1] - self.h_limits[0]
        self.h0 = self.settings.New('h0',  initial=self.h_limits[0]+h_range*0.25, **h_lq_params  )
        self.h1 = self.settings.New('h1',  initial=self.h_limits[0]+h_range*0.75, **h_lq_params  )
        v_lq_params = dict(vmin=self.v_limits[0], vmax=self.v_limits[1], unit=self.v_unit, 
                                spinbox_decimals=self.v_spinbox_decimals, spinbox_step=self.v_spinbox_step,
                                dtype=float,ro=False)
        v_range = self.v_limits[1]-self.v_limits[0]
        self.v0 = self.settings.New('v0',  initial=self.v_limits[0] + v_range*0.25, **v_lq_params  )
        self.v1 = self.settings.New('v1',  initial=self.v_limits[0] + v_range*0.75, **v_lq_params  )

        lq_params = dict(dtype=float, vmin=1e-9, vmax=abs(h_range), ro=False, unit=self.h_unit )
        self.dh = self.settings.New('dh', initial=self.h_spinbox_step, **lq_params)
        self.dh.spinbox_decimals = self.h_spinbox_decimals
        lq_params = dict(dtype=float, vmin=1e-9, vmax=abs(v_range), ro=False, unit=self.v_unit )
        self.dv = self.settings.New('dv', initial=self.v_spinbox_step, **lq_params)
        self.dv.spinbox_decimals = self.v_spinbox_decimals
        
        self.Nh = self.settings.New('Nh', initial=11, vmin=1, dtype=int, ro=False)
        self.Nv = self.settings.New('Nv', initial=11, vmin=1, dtype=int, ro=False)
        
        self.h_center = self.settings.New('h_center', dtype=float, ro=False,unit=self.h_unit,spinbox_decimals=self.h_spinbox_decimals, spinbox_step=self.h_spinbox_step)
        self.v_center = self.settings.New('v_center', dtype=float, ro=False,unit=self.v_unit,spinbox_decimals=self.v_spinbox_decimals, spinbox_step=self.v_spinbox_step)

        self.h_span = self.settings.New('h_span', dtype=float, ro=False,spinbox_decimals=self.h_spinbox_decimals, spinbox_step=self.h_spinbox_step,unit=self.h_unit)
        self.v_span = self.settings.New('v_span', dtype=float, ro=False,spinbox_decimals=self.v_spinbox_decimals, spinbox_step=self.v_spinbox_step,unit=self.v_unit)
        
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
        
        if not self.use_external_range_sync:
            self.h_range = LQRange(self.h0, self.h1, self.dh, self.Nh, self.h_center, self.h_span)    
            self.v_range = LQRange(self.v0, self.v1, self.dv, self.Nv, self.v_center, self.v_span)

        for s in 'h0 h1 dh v0 v1 dv'.split():
            self.settings.get_lq(s).add_listener(self.compute_scan_params)

        self.scan_type.updated_value.connect(self.compute_scan_params)
        
        #connect events
        self.settings.show_previous_scans.add_listener(
            self.show_hide_previous_scans, argtype=(bool),)
        
        self.ui.start_pushButton.clicked.connect(self.start)
        self.ui.interrupt_pushButton.clicked.connect(self.interrupt)

        self.h0.connect_to_widget(self.ui.h0_doubleSpinBox)
        self.h1.connect_to_widget(self.ui.h1_doubleSpinBox)
        self.v0.connect_to_widget(self.ui.v0_doubleSpinBox)
        self.v1.connect_to_widget(self.ui.v1_doubleSpinBox)
        self.dh.connect_to_widget(self.ui.dh_doubleSpinBox)
        self.dv.connect_to_widget(self.ui.dv_doubleSpinBox)
        self.Nh.connect_to_widget(self.ui.Nh_doubleSpinBox)
        self.Nv.connect_to_widget(self.ui.Nv_doubleSpinBox)
        self.scan_type.connect_to_widget(self.ui.scan_type_comboBox)
        
        self.progress.connect_to_widget(self.ui.progress_doubleSpinBox)
        #self.progress.updated_value[str].connect(self.ui.xy_scan_progressBar.setValue)
        #self.progress.updated_value.connect(self.tree_progressBar.setValue)

        self.settings.continuous_scan.connect_to_widget(
            self.ui.continuous_scan_checkBox)
        self.settings.save_h5.connect_to_widget(
            self.ui.save_h5_checkBox)

        self.settings.show_previous_scans.connect_to_widget(
            self.ui.show_previous_scans_checkBox)

        self.initial_scan_setup_plotting = False
        self.scan_specific_setup()
        

        self.add_operation('clear_previous_scans', self.clear_previous_scans)

        self.ui.clear_previous_scans_pushButton.clicked.connect(
            self.clear_previous_scans)
        
        self.compute_scan_params()
        
        
    def set_details_widget(self, widget = None, ui_filename=None):
        #print('LOADING DETAIL UI')
        if ui_filename is not None:
            details_ui = load_qt_ui_file(ui_filename)
        if widget is not None:
            details_ui = widget
        if hasattr(self, 'details_ui'):
            if self.details_ui is not None:
                self.details_ui.deleteLater()
                self.ui.details_groupBox.layout().removeWidget(self.details_ui)
                #self.details_ui.hide()
                del self.details_ui
        self.details_ui = details_ui
        #return replace_widget_in_layout(self.ui.details_groupBox,details_ui)
        self.ui.details_groupBox.layout().addWidget(self.details_ui)
        return self.details_ui
        
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
            
        self.compute_scan_params()

    
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
        
        # GoTo position context menu
        #self.goto_cmenu_action = QtWidgets.QAction("GoTo Position", self.img_plot.scene())
        #self.img_plot.scene().contextMenu.append(self.goto_cmenu_action)
        #self.goto_cmenu_action.triggered.connect(self.on_goto_position)
        
        # Point ROI
        self.pt_roi = pg.CircleROI( (0,0), (self.circ_roi_size,self.circ_roi_size) , movable=True, pen=(0,9))
        #self.pt_roi.removeHandle(self.pt_roi.getHandles()[0])
            
        h = self.pt_roi.addTranslateHandle((0.5,0.5))
        
        h.pen = pg.mkPen('r')
        h.update()
        self.img_plot.addItem(self.pt_roi)
        self.pt_roi.removeHandle(0)
        #self.pt_roi_plotline = pg.PlotCurveItem([0], pen=(0,9))
        #self.imview.getView().addItem(self.pt_roi_plotline) 
        self.pt_roi.sigRegionChangeFinished[object].connect(self.on_update_pt_roi)

    def on_update_pt_roi(self, roi=None):
        if roi is None:
            roi = self.circ_roi
        roi_state = roi.saveState()
        x0, y0 = roi_state['pos']
        xc = x0 + self.circ_roi_size/2.
        yc = y0 + self.circ_roi_size/2.
        self.new_pt_pos(xc,yc)
    
    def new_pt_pos(self, x,y):
        print('new_pt_pos', x,y)

    
    def mouse_update_scan_roi(self):
        x0,y0 =  self.scan_roi.pos()
        w, h =  self.scan_roi.size()
        self.h_center.update_value(x0 + w/2)
        self.v_center.update_value(y0 + h/2)
        self.h_span.update_value(w-self.dh.val)
        self.v_span.update_value(h-self.dv.val)
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
    
    def on_goto_position(self):
        pass
    
    def update_display(self):
        #self.log.debug('update_display')
        if self.initial_scan_setup_plotting:
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
            self.disp_img = self.display_image_map[kk,:,:].T
            self.img_item.setImage(self.disp_img, autoRange=False, autoLevels=True)
            self.img_item.setRect(self.img_item_rect) # Important to set rectangle after setImage for non-square pixels
            self.update_LUT()
            
    def update_LUT(self):
        ''' override this function to control display LUT scaling'''
        self.hist_lut.imageChanged(autoLevel=False)
        #DISABLE below because of crashing
#         non_zero_index = np.nonzero(self.disp_img)
#         if len(non_zero_index[0]) > 0:
#             self.hist_lut.setLevels(*np.percentile(self.disp_img[non_zero_index],(1,99)))

    def show_hide_previous_scans(self, show):
        print("show_hide_previous_scans", show)
        if len(self.img_items) < 2:
            return
        for img_item in self.img_items[:-1]:
            img_item.setVisible(show)
              
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
        
        #self.app.hardware_components['dummy_xy_stage'].x_position.connect_to_widget(self.ui.x_doubleSpinBox)
        #self.app.hardware_components['dummy_xy_stage'].y_position.connect_to_widget(self.ui.y_doubleSpinBox)
        
        #self.app.hardware_components['apd_counter'].int_time.connect_to_widget(self.ui.int_time_doubleSpinBox)
       
       
       
        # logged quantities
        # connect events
        
    

    def initialize_controller(self):
#        self.controller = self.app.hardware['xbox_controller']
#         
#         if hasattr(self, 'controller'):
#             self.pt_roi.sigRegionChangeFinished.connect(self.on_update_pt_roi)
        pass
    
    def update_point_roi_xbox(self):
        """Not yet implemented."""
        dx = self.controller.settings['Axis_4']
        dy = self.controller.settings['Axis_3']
        x, y = self.pt_roi.pos()
        if abs(dx) < 0.25:
            dx = 0
        if abs(dy) < 0.25:
            dy = 0
        if dx != 0 or dy != 0:
            c = self.controller.settings.sensitivity.val
            self.pt_roi.setPos(x+(c*dx), y+(c*dy))
        
    @property
    def h_array(self):
        #return self.h_range.array
        return np.linspace(self.h0.val, self.h1.val, self.Nh.val)

    @property
    def v_array(self):
        #return self.v_range.array
        return np.linspace(self.v0.val, self.v1.val, self.Nv.val)

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
            
            self.scan_slow_move[::self.Nh.val] = True
            
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


class BaseRaster3DScan(Measurement):
    name = "base_raster_3D_scan"
    
    def __init__(self, app, 
                 h_limits=(-1,1),        v_limits=(-1,1),       z_limits=(-1,1),
                 h_unit='',              v_unit='',             z_unit='',
                 h_spinbox_decimals=4,   v_spinbox_decimals=4,  z_spinbox_decimals=4,
                 h_spinbox_step=0.1,     v_spinbox_step=0.1,    z_spinbox_step=0.1,
                 use_external_range_sync=False,
                 circ_roi_size=1.0,
                 ):        
        self.h_spinbox_decimals = h_spinbox_decimals
        self.v_spinbox_decimals = v_spinbox_decimals
        self.z_spinbox_decimals = z_spinbox_decimals
        self.h_spinbox_step = h_spinbox_step
        self.v_spinbox_step = v_spinbox_step
        self.z_spinbox_step = z_spinbox_step
        self.h_limits = h_limits
        self.v_limits = v_limits
        self.z_limits = z_limits
        self.h_unit = h_unit
        self.v_unit = v_unit
        self.z_unit = z_unit
        self.use_external_range_sync = use_external_range_sync
        self.circ_roi_size=circ_roi_size
        Measurement.__init__(self, app)
        
    def setup(self):
        self.ui_filename = sibling_path(__file__,"raster_3d_scan_base.ui")
        self.ui = load_qt_ui_file(self.ui_filename)
        #self.ui.show()
        self.ui.setWindowTitle(self.name)

        self.display_update_period = 0.010 #seconds

        #connect events        

        # local logged quantities
        h_lq_params = dict(vmin=self.h_limits[0], vmax=self.h_limits[1], unit=self.h_unit, 
                                spinbox_decimals=self.h_spinbox_decimals, spinbox_step=self.h_spinbox_step,
                                dtype=float,ro=False)
        h_range = self.h_limits[1] - self.h_limits[0]
        self.h0 = self.settings.New('h0',  initial=self.h_limits[0]+h_range*0.25, **h_lq_params  )
        self.h1 = self.settings.New('h1',  initial=self.h_limits[0]+h_range*0.75, **h_lq_params  )
        v_lq_params = dict(vmin=self.v_limits[0], vmax=self.v_limits[1], unit=self.v_unit, 
                                spinbox_decimals=self.v_spinbox_decimals, spinbox_step=self.v_spinbox_step,
                                dtype=float,ro=False)
        v_range = self.v_limits[1]-self.v_limits[0]
        self.v0 = self.settings.New('v0',  initial=self.v_limits[0] + v_range*0.25, **v_lq_params  )
        self.v1 = self.settings.New('v1',  initial=self.v_limits[0] + v_range*0.75, **v_lq_params  )
        
        z_lq_params = dict(vmin=self.z_limits[0], vmax=self.z_limits[1], unit=self.z_unit, 
                                spinbox_decimals=self.z_spinbox_decimals, spinbox_step=self.z_spinbox_step,
                                dtype=float,ro=False)
        z_range = self.z_limits[1]-self.z_limits[0]
        self.z0 = self.settings.New('z0',  initial=self.z_limits[0] + z_range*0.25, **z_lq_params  )
        self.z1 = self.settings.New('z1',  initial=self.z_limits[0] + z_range*0.75, **z_lq_params  )

        lq_params = dict(dtype=float, vmin=1e-9, vmax=abs(h_range), ro=False, unit=self.h_unit )
        self.dh = self.settings.New('dh', initial=self.h_spinbox_step, **lq_params)
        self.dh.spinbox_decimals = self.h_spinbox_decimals
        lq_params = dict(dtype=float, vmin=1e-9, vmax=abs(v_range), ro=False, unit=self.v_unit )
        self.dv = self.settings.New('dv', initial=self.v_spinbox_step, **lq_params)
        self.dv.spinbox_decimals = self.v_spinbox_decimals
        lq_params = dict(dtype=float, vmin=1e-9, vmax=abs(z_range), ro=False, unit=self.z_unit )
        self.dz = self.settings.New('dz', initial=self.z_spinbox_step, **lq_params)
        self.dz.spinbox_decimals = self.z_spinbox_decimals
        
        self.Nh = self.settings.New('Nh', initial=11, vmin=1, dtype=int, ro=False)
        self.Nv = self.settings.New('Nv', initial=11, vmin=1, dtype=int, ro=False)
        self.Nz = self.settings.New('Nz', initial=11, vmin=1, dtype=int, ro=False)
        
        self.h_center = self.settings.New('h_center', dtype=float, ro=False,unit=self.h_unit,spinbox_decimals=self.h_spinbox_decimals, spinbox_step=self.h_spinbox_step)
        self.v_center = self.settings.New('v_center', dtype=float, ro=False,unit=self.v_unit,spinbox_decimals=self.v_spinbox_decimals, spinbox_step=self.v_spinbox_step)
        self.z_center = self.settings.New('z_center', dtype=float, ro=False,unit=self.z_unit,spinbox_decimals=self.z_spinbox_decimals, spinbox_step=self.z_spinbox_step)

        self.h_span = self.settings.New('h_span', dtype=float, ro=False,spinbox_decimals=self.h_spinbox_decimals, spinbox_step=self.h_spinbox_step,unit=self.h_unit)
        self.v_span = self.settings.New('v_span', dtype=float, ro=False,spinbox_decimals=self.v_spinbox_decimals, spinbox_step=self.v_spinbox_step,unit=self.v_unit)
        self.z_span = self.settings.New('z_span', dtype=float, ro=False,spinbox_decimals=self.z_spinbox_decimals, spinbox_step=self.z_spinbox_step,unit=self.z_unit)

        self.Npixels = self.Nh.val*self.Nv.val*self.Nz.val
        
        self.scan_type = self.settings.New('scan_type', dtype=str, initial='raster',
                                                  choices=('raster', 'serpentine'))
        
        self.continuous_scan = self.settings.New("continuous_scan", dtype=bool, initial=False)
        self.settings.New('save_h5', dtype=bool, initial=True, ro=False)
        
        self.settings.New('show_previous_scans', dtype=bool, initial=True)
        
        self.settings.New('pixel_time', dtype=float, ro=True, si=True, initial=1, unit='s')
        self.settings.New('line_time' , dtype=float, ro=True, si=True, unit='s')
        self.settings.New('frame_time' , dtype=float, ro=True, si=True, unit='s')        
        self.settings.New('total_time', dtype=float, ro=True, si=True, unit='s')
        
        for lq_name in ['Nh', 'Nv', 'Nz', 'pixel_time']:
            self.settings.get_lq(lq_name).add_listener(self.compute_times)
            
        self.compute_times()
        
        if not self.use_external_range_sync:
            self.h_range = LQRange(self.h0, self.h1, self.dh, self.Nh, self.h_center, self.h_span)    
            self.v_range = LQRange(self.v0, self.v1, self.dv, self.Nv, self.v_center, self.v_span)
            self.z_range = LQRange(self.z0, self.z1, self.dz, self.Nz, self.z_center, self.z_span)

        for s in 'h0 h1 dh v0 v1 dv z0 z1 dz'.split():
            self.settings.get_lq(s).add_listener(self.compute_scan_params)

        self.scan_type.updated_value.connect(self.compute_scan_params)
        
        #connect events
        self.ui.start_pushButton.clicked.connect(self.start)
        self.ui.interrupt_pushButton.clicked.connect(self.interrupt)

        self.h0.connect_to_widget(self.ui.h0_doubleSpinBox)
        self.h1.connect_to_widget(self.ui.h1_doubleSpinBox)
        self.v0.connect_to_widget(self.ui.v0_doubleSpinBox)
        self.v1.connect_to_widget(self.ui.v1_doubleSpinBox)
        self.z0.connect_to_widget(self.ui.z0_doubleSpinBox)
        self.z1.connect_to_widget(self.ui.z1_doubleSpinBox)
        self.dh.connect_to_widget(self.ui.dh_doubleSpinBox)
        self.dv.connect_to_widget(self.ui.dv_doubleSpinBox)
        self.dz.connect_to_widget(self.ui.dz_doubleSpinBox)
        self.Nh.connect_to_widget(self.ui.Nh_doubleSpinBox)
        self.Nv.connect_to_widget(self.ui.Nv_doubleSpinBox)
        self.Nz.connect_to_widget(self.ui.Nz_doubleSpinBox)
        self.scan_type.connect_to_widget(self.ui.scan_type_comboBox)
        
        self.progress.connect_to_widget(self.ui.progress_doubleSpinBox)
        #self.progress.updated_value[str].connect(self.ui.xy_scan_progressBar.setValue)
        #self.progress.updated_value.connect(self.tree_progressBar.setValue)

        self.settings.continuous_scan.connect_to_widget(
            self.ui.continuous_scan_checkBox)
        self.settings.save_h5.connect_to_widget(
            self.ui.save_h5_checkBox)

        self.settings.show_previous_scans.connect_to_widget(
            self.ui.show_previous_scans_checkBox)

        self.initial_scan_setup_plotting = False
        self.scan_specific_setup()
        

        self.add_operation('clear_previous_scans', self.clear_previous_scans)

        self.ui.clear_previous_scans_pushButton.clicked.connect(
            self.clear_previous_scans)
        
        self.compute_scan_params()
        
    def set_details_widget(self, widget = None, ui_filename=None):
        #print('LOADING DETAIL UI')
        if ui_filename is not None:
            details_ui = load_qt_ui_file(ui_filename)
        if widget is not None:
            details_ui = widget
        if hasattr(self, 'details_ui'):
            if self.details_ui is not None:
                self.details_ui.deleteLater()
                self.ui.details_groupBox.layout().removeWidget(self.details_ui)
                #self.details_ui.hide()
                del self.details_ui
        self.details_ui = details_ui
        #return replace_widget_in_layout(self.ui.details_groupBox,details_ui)
        self.ui.details_groupBox.layout().addWidget(self.details_ui)
        return self.details_ui
        
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
            
    def set_z_limits(self, zmin, zmax, set_scan_to_max=False):
        self.settings.z0.change_min_max(zmin, zmax)
        self.settings.z1.change_min_max(zmin, zmax)
        if set_scan_to_max:
            self.settings['z0'] = zmin
            self.settings['z1'] = zmax

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
        self.scan_z_positions = np.zeros(self.Npixels, dtype=float)
        self.scan_slow_move   = np.zeros(self.Npixels, dtype=bool)
        self.scan_start_move  = np.zeros(self.Npixels, dtype=bool)
        self.scan_index_array = np.zeros((self.Npixels, 3), dtype=int)

    def pre_run(self):
        # set all logged quantities read only
        for lqname in "h0 h1 v0 v1 z0 z1 dh dv dz Nh Nv Nz".split():
            self.settings.as_dict()[lqname].change_readonly(True)
            
        self.compute_scan_params()

    
    def post_run(self):
            # set all logged quantities writable
            for lqname in "h0 h1 v0 v1 z0 z1 dh dv dz Nh Nv Nz".split():
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
            self.stage.settings.z_position.connect_to_widget(self.ui.z_doubleSpinBox)

        
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
        
        # GoTo position context menu
        #self.goto_cmenu_action = QtWidgets.QAction("GoTo Position", self.img_plot.scene())
        #self.img_plot.scene().contextMenu.append(self.goto_cmenu_action)
        #self.goto_cmenu_action.triggered.connect(self.on_goto_position)
        
        # Point ROI
        self.pt_roi = pg.CircleROI( (0,0), (self.circ_roi_size,self.circ_roi_size) , movable=True, pen=(0,9))
        #self.pt_roi.removeHandle(self.pt_roi.getHandles()[0])
            
        h = self.pt_roi.addTranslateHandle((0.5,0.5))
        
        h.pen = pg.mkPen('r')
        h.update()
        self.img_plot.addItem(self.pt_roi)
        self.pt_roi.removeHandle(0)
        #self.pt_roi_plotline = pg.PlotCurveItem([0], pen=(0,9))
        #self.imview.getView().addItem(self.pt_roi_plotline) 
        self.pt_roi.sigRegionChangeFinished[object].connect(self.on_update_pt_roi)

    def on_update_pt_roi(self, roi=None):
        if roi is None:
            roi = self.circ_roi
        roi_state = roi.saveState()
        x0, y0 = roi_state['pos']
        xc = x0 + self.circ_roi_size/2.
        yc = y0 + self.circ_roi_size/2.
        self.new_pt_pos(xc,yc)
    
    def new_pt_pos(self, x,y):
        print('new_pt_pos', x,y)

    
    def mouse_update_scan_roi(self):
        x0,y0 =  self.scan_roi.pos()
        w, h =  self.scan_roi.size()
        self.h_center.update_value(x0 + w/2)
        self.v_center.update_value(y0 + h/2)
        self.h_span.update_value(w-self.dh.val)
        self.v_span.update_value(h-self.dv.val)
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
    
    def on_goto_position(self):
        pass
    
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
            self.disp_img = self.display_image_map[kk,:,:].T
            self.img_item.setImage(self.disp_img, autoRange=False, autoLevels=True)
            self.img_item.setRect(self.img_item_rect) # Important to set rectangle after setImage for non-square pixels
            self.update_LUT()
            
    def update_LUT(self):
        ''' override this function to control display LUT scaling'''
        self.hist_lut.imageChanged(autoLevel=True)
        #DISABLE below because of crashing
        non_zero_index = np.nonzero(self.disp_img)
        if len(non_zero_index[0]) > 0:
            self.hist_lut.setLevels(*np.percentile(self.disp_img[non_zero_index],(1,99)))
               
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
        
        #self.app.hardware_components['dummy_xy_stage'].x_position.connect_to_widget(self.ui.x_doubleSpinBox)
        #self.app.hardware_components['dummy_xy_stage'].y_position.connect_to_widget(self.ui.y_doubleSpinBox)
        
        #self.app.hardware_components['apd_counter'].int_time.connect_to_widget(self.ui.int_time_doubleSpinBox)
       
       
       
        # logged quantities
        # connect events
        
    

    def initialize_controller(self):
#        self.controller = self.app.hardware['xbox_controller']
#         
#         if hasattr(self, 'controller'):
#             self.pt_roi.sigRegionChangeFinished.connect(self.on_update_pt_roi)
        pass
    
    def update_point_roi_xbox(self):
        """Not yet implemented."""
        dx = self.controller.settings['Axis_4']
        dy = self.controller.settings['Axis_3']
        x, y = self.pt_roi.pos()
        if abs(dx) < 0.25:
            dx = 0
        if abs(dy) < 0.25:
            dy = 0
        if dx != 0 or dy != 0:
            c = self.controller.settings.sensitivity.val
            self.pt_roi.setPos(x+(c*dx), y+(c*dy))
        
    @property
    def h_array(self):
        #return self.h_range.array
        return np.linspace(self.h0.val, self.h1.val, self.Nh.val)

    @property
    def v_array(self):
        #return self.v_range.array
        return np.linspace(self.v0.val, self.v1.val, self.Nv.val)
    
    @property
    def z_array(self):
        #return self.z_range.array
        return np.linspace(self.z0.val, self.z1.val, self.Nz.val)

    def compute_times(self):
        #self.settings['pixel_time'] = 1.0/self.scanDAQ.settings['dac_rate']
        S = self.settings
        S['line_time']  = S['pixel_time'] * S['Nh']
        S['frame_time'] = S['line_time'] * S['Nv']
        S['total_time'] = S['frame_time'] * S['Nz']
    
    #### Scan Generators
    def gen_raster_scan(self, gen_arrays=True):
        self.Npixels = self.Nh.val*self.Nv.val*self.Nz.val
        self.scan_shape = (self.Nz.val, self.Nv.val, self.Nh.val)
        
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
             
            V, Z, H = np.meshgrid(self.v_array, self.z_array, self.h_array)
            self.scan_h_positions[:] = H.flat
            self.scan_v_positions[:] = V.flat
            self.scan_z_positions[:] = Z.flat
            # print(self.scan_h_positions[0:self.Nh.val])
            # print(self.scan_v_positions[0:self.Nh.val*self.Nv.val])
            # print(self.scan_z_positions[0:self.Nh.val*self.Nv.val])
            
            self.scan_slow_move[::self.Nh.val] = True
            self.scan_start_move[::self.Nh.val*self.Nv.val] = True
            
            JJ, KK, II = np.meshgrid(np.arange(self.Nv.val), np.arange(self.Nz.val), np.arange(self.Nh.val))
            self.scan_index_array[:,0] = KK.flat
            self.scan_index_array[:,1] = JJ.flat
            self.scan_index_array[:,2] = II.flat
            #self.scan_v_positions
            print("array flatten raster gen", time.time() - t0)
             
         
    def gen_serpentine_scan(self, gen_arrays=True):
        self.Npixels = self.Nh.val*self.Nv.val*self.Nz.val
        self.scan_shape = (self.Nz.val, self.Nv.val, self.Nh.val)
 
        if gen_arrays:
            self.create_empty_scan_arrays()
            pixel_i = 0
            for kk in range(self.Nz.val):
                self.scan_start_move[pixel_i] = True
                for jj in range(self.Nv.val):
                    self.scan_slow_move[pixel_i] = True
                     
                    if jj % 2: #odd lines
                        h_line_indicies = range(self.Nh.val)[::-1]
                    else:       #even lines -- traverse in opposite direction
                        h_line_indicies = range(self.Nh.val)            
             
                    for ii in h_line_indicies:
                        self.scan_z_positions[pixel_i] = self.z_array[kk]            
                        self.scan_v_positions[pixel_i] = self.v_array[jj]
                        self.scan_h_positions[pixel_i] = self.h_array[ii]
                        self.scan_index_array[pixel_i,:] = [kk, jj, ii]                 
                        pixel_i += 1
#                 
#     def gen_trace_retrace_scan(self, gen_arrays=True):
#         self.Npixels = 2*self.Nh.val*self.Nv.val
#         self.scan_shape = (2, self.Nv.val, self.Nh.val)
# 
#         if gen_arrays:
#             self.create_empty_scan_arrays()
#             pixel_i = 0
#             for jj in range(self.Nv.val):
#                 self.scan_slow_move[pixel_i] = True     
#                 for kk, step in [(0,1),(1,-1)]: # trace kk =0, retrace kk=1
#                     h_line_indicies = range(self.Nh.val)[::step]
#                     for ii in h_line_indicies:            
#                         self.scan_v_positions[pixel_i] = self.v_array[jj]
#                         self.scan_h_positions[pixel_i] = self.h_array[ii]
#                         self.scan_index_array[pixel_i,:] = [kk, jj, ii]                 
#                         pixel_i += 1
#     
#     def gen_ortho_raster_scan(self, gen_arrays=True):
#         self.Npixels = 2*self.Nh.val*self.Nv.val
#         self.scan_shape = (2, self.Nv.val, self.Nh.val)
# 
#         if gen_arrays:
#             self.create_empty_scan_arrays()
#             pixel_i = 0
#             for jj in range(self.Nv.val):
#                 self.scan_slow_move[pixel_i] = True
#                 for ii in range(self.Nh.val):
#                     self.scan_v_positions[pixel_i] = self.v_array[jj]
#                     self.scan_h_positions[pixel_i] = self.h_array[ii]
#                     self.scan_index_array[pixel_i,:] = [0, jj, ii] 
#                     pixel_i += 1
#             for ii in range(self.Nh.val):
#                 self.scan_slow_move[pixel_i] = True
#                 for jj in range(self.Nv.val):
#                     self.scan_v_positions[pixel_i] = self.v_array[jj]
#                     self.scan_h_positions[pixel_i] = self.h_array[ii]
#                     self.scan_index_array[pixel_i,:] = [1, jj, ii] 
#                     pixel_i += 1
#     
#     def gen_ortho_trace_retrace_scan(self, gen_arrays=True):
#         print("gen_ortho_trace_retrace_scan")
#         self.Npixels = 4*len(self.h_array)*len(self.v_array) 
#         self.scan_shape = (4, self.Nv.val, self.Nh.val)                        
#         
#         if gen_arrays:
#             self.create_empty_scan_arrays()
#             pixel_i = 0
#             for jj in range(self.Nv.val):
#                 self.scan_slow_move[pixel_i] = True     
#                 for kk, step in [(0,1),(1,-1)]: # trace kk =0, retrace kk=1
#                     h_line_indicies = range(self.Nh.val)[::step]
#                     for ii in h_line_indicies:            
#                         self.scan_v_positions[pixel_i] = self.v_array[jj]
#                         self.scan_h_positions[pixel_i] = self.h_array[ii]
#                         self.scan_index_array[pixel_i,:] = [kk, jj, ii]                 
#                         pixel_i += 1
#             for ii in range(self.Nh.val):
#                 self.scan_slow_move[pixel_i] = True     
#                 for kk, step in [(2,1),(3,-1)]: # trace kk =2, retrace kk=3
#                     v_line_indicies = range(self.Nv.val)[::step]
#                     for jj in v_line_indicies:            
#                         self.scan_v_positions[pixel_i] = self.v_array[jj]
#                         self.scan_h_positions[pixel_i] = self.h_array[ii]
#                         self.scan_index_array[pixel_i,:] = [kk, jj, ii]                 
#                         pixel_i += 1
