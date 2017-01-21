from __future__ import division, print_function, absolute_import
from ScopeFoundry import HardwareComponent
import random

class DummmyXYStageDevice(object):
    
    def __init__(self, debug=False):
        self.x = 0
        self.y = 0
        self.debug=debug
        # communicate with hardware here
    
    def read_x(self):
        self.x = self.x + self.noise()
        #if self.debug: print "read_x", self.x
        #print("read_x", self.x)
        return self.x

    def read_y(self):
        self.y = self.y + self.noise()
        #if self.debug: print "read_y", self.y
        return self.y
    
    def write_x(self, x):
        self.x = x
        #print("write_x", self.x, x)
        #if self.debug: print "write_x", self.x
        

    def write_y(self, y):
        self.y = y
        #if self.debug: print "write_y", self.y
    
    def close(self):
        #print "dummy_xy_stage_equipment close"
        pass
    
    def noise(self):
        return (random.random()-0.5)*10e-3

class DummyXYStageHW(HardwareComponent):
    
    name = "dummy_xy_stage"
    
    def setup(self):
        lq_params = dict(  dtype=float, ro=False,
                           initial = -1,
                           vmin=-1,
                           vmax=100,
                           si = False,
                           unit='um')
        self.x_position = self.add_logged_quantity("x_position", **lq_params)
        self.y_position = self.add_logged_quantity("y_position", **lq_params)       

        self.x_position.reread_from_hardware_after_write = True
        self.x_position.spinbox_decimals = 3
        
        self.y_position.reread_from_hardware_after_write = True
        self.y_position.spinbox_decimals = 3

    def connect(self):
        #if self.debug_mode.val: print "connecting to dummy_xy_stage"

        # Open connection to hardware
        self.stage_device = DummmyXYStageDevice(debug=self.debug_mode.val)

        # connect logged quantities
        self.x_position.hardware_read_func = self.stage_device.read_x
        self.y_position.hardware_read_func = self.stage_device.read_y
        
        self.x_position.hardware_set_func  = self.stage_device.write_x
        self.y_position.hardware_set_func  = self.stage_device.write_y

    def disconnect(self):
        #if self.debug_mode.val: print "disconnecting to dummy_xy_stage"
        
        #disconnect logged quantities from hardware
        for lq in self.settings.as_list():
            lq.hardware_read_func = None
            lq.hardware_set_func = None
        
        if hasattr(self, 'stage_device'):
            #disconnect hardware
            self.stage_device.close()
            
            # clean up hardware object
            del self.stage_device



