from ScopeFoundry import BaseMicroscopeApp  
from ScopeFoundry.examples.hardware.dummy_xy_stage import DummyXYStageHW
from ScopeFoundry.scanning import BaseRaster2DSlowScan, BaseRaster2DFrameSlowScan
import time
import numpy as np

import logging
logging.basicConfig(level=logging.DEBUG)#, filename='m3_log.txt')
#logging.getLogger("ipykernel").setLevel(logging.WARNING)
#logging.getLogger('PyQt4').setLevel(logging.WARNING)
logging.getLogger('ScopeFoundry').setLevel(logging.DEBUG)
logging.getLogger('').setLevel(logging.DEBUG)


class TestRaster2DSlowScan(BaseRaster2DSlowScan):
    name='test_cart_2d_slow_scan'
    
    def __init__(self, app):
        BaseRaster2DSlowScan.__init__(self, app, h_limits=(0,100), v_limits=(0,100), h_unit="um", v_unit="um")        
    
    def setup(self):
        BaseRaster2DSlowScan.setup(self)
        #self.settings.New('pixel_time', initial=0.001, unit='s', si=False, spinbox_decimals=5)
        self.settings.pixel_time.change_readonly(False) 
    
    def pre_scan_setup(self):
        self.display_update_period = 0.050 #seconds
        
        self.stage = self.app.hardware['dummy_xy_stage']
        if self.settings['save_h5']:
            self.test_data = self.h5_meas_group.create_dataset('test_data', self.scan_shape, dtype=float)
        
        self.prev_px = time.time()
         
    def post_scan_cleanup(self):
        print("post_scan_cleanup")
        
    def collect_pixel(self, pixel_i, k,j,i):
        #print pixel_i, k,j,i
        t0 = time.time()
        #px_data = np.random.rand()
        #px_data = t0 - self.prev_px
        x0,y0 = self.pos
        x_set = self.stage.settings['x_position']
        y_set = self.stage.settings['y_position']
        x_hw = self.stage.settings.x_position.read_from_hardware(send_signal=False)
        y_hw = self.stage.settings.y_position.read_from_hardware(send_signal=False)
        if np.abs(x_hw - x0) > 1:
            self.log.debug('='*60)
            self.log.debug('pos      {} {}'.format(x0, y0))
            self.log.debug('settings {} {}'.format(x_set, y_set))
            self.log.debug('hw       {} {}'.format(x_hw, y_hw))            
            self.log.debug('settings value delta {} {}'.format(x_set-x0, y_set-y0))
            self.log.debug('read_hw  value delta {} {}'.format(x_hw-x0, y_hw-y0))
            self.log.debug('='*60)
        
        x = x_hw
        y = y_hw
        
        px_data = np.sinc((x-50)*0.05)**2 * np.sinc(0.05*(y-50))**2 #+ 0.05*np.random.random()
        #px_data = (x-xhw)**2 + ( y-yhw)**2
        #if px_data > 1:
        #    print('hw', x, xhw, y, yhw)
        self.display_image_map[k,j,i] = px_data
        if self.settings['save_h5']:
            self.test_data[k,j,i] = px_data 
        time.sleep(self.settings['pixel_time'])
        #self.prev_px = t0

class TestRaster2DFrameSlowScan(BaseRaster2DFrameSlowScan):
    name='test_cart_2d_frame_slow_scan'
    
    def __init__(self, app):
        BaseRaster2DSlowScan.__init__(self, app, h_limits=(0,100), v_limits=(0,100), h_unit="um", v_unit="um")        
    
    def setup(self):
        BaseRaster2DSlowScan.setup(self)
        #self.settings.New('pixel_time', initial=0.001, unit='s', si=False, spinbox_decimals=5)
        self.settings.pixel_time.change_readonly(False)
        
    
    def pre_scan_setup(self):
        self.display_update_period = 0.050 #seconds
        
        self.stage = self.app.hardware['dummy_xy_stage']
        if self.settings['save_h5']:
            #self.test_data = self.h5_meas_group.create_dataset('test_data', self.frames_scan_shape, dtype=float)
            self.test_data = self.create_h5_framed_dataset("test_data",self.display_image_map)
        
        self.prev_px = time.time()
         
    def post_scan_cleanup(self):
        print("post_scan_cleanup")
        
    def collect_pixel(self, pixel_i, frame_i,  k,j,i):
        #print pixel_i, k,j,i
        t0 = time.time()
        #px_data = np.random.rand()
        #px_data = t0 - self.prev_px
        x_hw = self.stage.settings.x_position.read_from_hardware(send_signal=False)
        y_hw = self.stage.settings.y_position.read_from_hardware(send_signal=False)
        
        theta = np.pi/10. * frame_i
        x = x_hw*np.cos(theta) - y_hw*np.sin(theta)
        y = x_hw*np.sin(theta) + y_hw*np.cos(theta)
        
        px_data = np.sinc((x-50)*0.05)**2 * np.sinc(0.05*(y-50))**2 #+ 0.05*np.random.random()
        #px_data = (x-xhw)**2 + ( y-yhw)**2
        #if px_data > 1:
        #    print('hw', x, xhw, y, yhw)
        self.display_image_map[k,j,i] = px_data
        if self.settings['save_h5']:
            self.test_data[frame_i, k,j,i] = px_data 
        time.sleep(self.settings['pixel_time'])
        #self.prev_px = t0
    
    def on_new_frame(self, frame_i):
        print("on_new_frame")
        if self.settings['save_h5']:
            self.extend_h5_framed_dataset(self.test_data, frame_i) 



class TestRaster2DSlowScanApp(BaseMicroscopeApp):
    
    name = 'app'

    def setup(self):
        
        stage = self.add_hardware(DummyXYStageHW(self))
        stage.settings['connected'] = True
        self.add_measurement(TestRaster2DSlowScan(self))
        self.add_measurement(TestRaster2DFrameSlowScan(self))
                
        
        for m in self.measurements.values():
            S = m.settings
            #S = self.test_cart_2d_slow_scan.settings
            S['h1'] = 100
            S['v1'] = 100
            S['dh'] = S['dv'] = 1.0
            
        

if __name__ == '__main__':
    logging.basicConfig(level='DEBUG')
    logging.getLogger('').setLevel(logging.WARNING)
    logging.getLogger("ipykernel").setLevel(logging.WARNING)
    logging.getLogger('PyQt4').setLevel(logging.WARNING)
    logging.getLogger('PyQt5').setLevel(logging.WARNING)
    logging.getLogger('traitlets').setLevel(logging.WARNING)
    
    logging.getLogger('ScopeFoundry.logged_quantity').setLevel(logging.WARNING)
    
    
    import sys
    app = TestRaster2DSlowScanApp([])
    sys.exit(app.exec_())    

