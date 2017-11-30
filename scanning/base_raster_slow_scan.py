from .base_raster_scan import BaseRaster2DScan
from ScopeFoundry import h5_io
import numpy as np
import time
import os

class BaseRaster2DSlowScan(BaseRaster2DScan):

    name = "base_raster_2Dslowscan"

    def run(self):
        S = self.settings
        
        
        #Hardware
        # self.apd_counter_hc = self.app.hardware_components['apd_counter']
        # self.apd_count_rate = self.apd_counter_hc.apd_count_rate
        # self.stage = self.app.hardware_components['dummy_xy_stage']

        # Data File
        # H5

        # Compute data arrays
        self.compute_scan_arrays()
        
        self.initial_scan_setup_plotting = True
        
        self.display_image_map = np.zeros(self.scan_shape, dtype=float)


        while not self.interrupt_measurement_called:        
            try:
                # h5 data file setup
                self.t0 = time.time()

                if self.settings['save_h5']:
                    self.h5_file = h5_io.h5_base_file(self.app, measurement=self)
                    self.h5_filename = self.h5_file.filename
                    
                    self.h5_file.attrs['time_id'] = self.t0
                    H = self.h5_meas_group  =  h5_io.h5_create_measurement_group(self, self.h5_file)
                
                    #create h5 data arrays
                    H['h_array'] = self.h_array
                    H['v_array'] = self.v_array
                    H['range_extent'] = self.range_extent
                    H['corners'] = self.corners
                    H['imshow_extent'] = self.imshow_extent
                    H['scan_h_positions'] = self.scan_h_positions
                    H['scan_v_positions'] = self.scan_v_positions
                    H['scan_slow_move'] = self.scan_slow_move
                    H['scan_index_array'] = self.scan_index_array
                
                
                # start scan
                self.pixel_i = 0
                self.current_scan_index = self.scan_index_array[0]

                self.pixel_time = np.zeros(self.scan_shape, dtype=float)
                if self.settings['save_h5']:
                    self.pixel_time_h5 = H.create_dataset(name='pixel_time', shape=self.scan_shape, dtype=float)            

                self.pre_scan_setup()
                
                self.move_position_start(self.scan_h_positions[0], self.scan_v_positions[0])
                
                for self.pixel_i in range(self.Npixels):                
                    if self.interrupt_measurement_called: break
                    
                    i = self.pixel_i
                    
                    self.current_scan_index = self.scan_index_array[i]
                    kk, jj, ii = self.current_scan_index
                    
                    h,v = self.scan_h_positions[i], self.scan_v_positions[i]
                    
                    if self.pixel_i == 0:
                        dh = 0
                        dv = 0
                    else:
                        dh = self.scan_h_positions[i] - self.scan_h_positions[i-1] 
                        dv = self.scan_v_positions[i] - self.scan_v_positions[i-1] 
                    
                    if self.scan_slow_move[i]:
                        self.move_position_slow(h,v, dh, dv)
                        if self.settings['save_h5']:    
                            self.h5_file.flush() # flush data to file every slow move
                        #self.app.qtapp.ProcessEvents()
                        time.sleep(0.01)
                    else:
                        self.move_position_fast(h,v, dh, dv)
                    
                    self.pos = (h,v)
                    # each pixel:
                    # acquire signal and save to data array
                    pixel_t0 = time.time()
                    self.pixel_time[kk, jj, ii] = pixel_t0
                    if self.settings['save_h5']:
                        self.pixel_time_h5[kk, jj, ii] = pixel_t0
                    self.collect_pixel(self.pixel_i, kk, jj, ii)
                    S['progress'] = 100.0*self.pixel_i / (self.Npixels)
            finally:
                self.post_scan_cleanup()
                if hasattr(self, 'h5_file'):
                    print('h5_file', self.h5_file)
                    try:
                        self.h5_file.close()
                    except ValueError as err:
                        self.log.warning('failed to close h5_file: {}'.format(err))
                if not self.settings['continuous_scan']:
                    break
        print(self.name, 'done')
                
    def move_position_start(self, h,v):
        self.stage.settings.x_position.update_value(h)
        self.stage.settings.y_position.update_value(v)
    
    def move_position_slow(self, h,v, dh, dv):
        self.stage.settings.x_position.update_value(h)
        self.stage.settings.y_position.update_value(v)
        
    def move_position_fast(self, h,v, dh, dv):
        self.stage.settings.x_position.update_value(h)
        self.stage.settings.y_position.update_value(v)
        #x = self.stage.settings['x_position']
        #y = self.stage.settings['y_position']        
        #x = self.stage.settings.x_position.read_from_hardware()
        #y = self.stage.settings.y_position.read_from_hardware()
        #print(x,y)
        
    def pre_scan_setup(self):
        print(self.name, "pre_scan_setup not implemented")
        # hardware
        # create data arrays
        # update figure        

    def collect_pixel(self, pixel_num, k, j, i):
        # collect data
        # store in arrays        
        print(self.name, "collect_pixel", pixel_num, k,j,i, "not implemented")
    
    def post_scan_cleanup(self):
        print(self.name, "post_scan_setup not implemented")

    def new_pt_pos(self, x,y):
        self.move_position_start(x, y)

 