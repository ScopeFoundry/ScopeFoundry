import random
from ScopeFoundry import HardwareComponent


class DummmyXYZStageDevice:
    
    def __init__(self, debug=False):
        self.x = 0
        self.y = 0
        self.z = 0
        self.debug = debug
        # communicate with hardware here
    
    def read_x(self):
        self.x = self.x + self.noise()
        return self.x

    def read_y(self):
        self.y = self.y + self.noise()
        return self.y

    def read_z(self):
        self.z = self.z + self.noise()
        return self.z
    
    def write_x(self, x):
        self.x = x

    def write_y(self, y):
        self.y = y

    def write_z(self, z):
        self.z = z
    
    def close(self):
        pass
    
    def noise(self):
        return (random.random() - 0.5) * 10e-3


class DummyXYZStageHW(HardwareComponent):
    
    name = "dummy_xyz_stage"
    
    def setup(self):
        lq_params = dict(dtype=float, ro=False,
                           initial=-1,
                           vmin=-1,
                           vmax=100,
                           si=False,
                           unit='um')
        
        self.x_position = self.settings.New("x_position", **lq_params)
        self.y_position = self.settings.New("y_position", **lq_params)       
        self.z_position = self.settings.New("z_position", **lq_params)       

        self.x_position.reread_from_hardware_after_write = True
        self.x_position.spinbox_decimals = 3
        
        self.y_position.reread_from_hardware_after_write = True
        self.y_position.spinbox_decimals = 3

        self.z_position.reread_from_hardware_after_write = True
        self.z_position.spinbox_decimals = 3

    def connect(self):

        dev = self.stage_device = DummmyXYZStageDevice(debug=self.debug_mode.val)

        self.x_position.connect_to_hardware(dev.read_x, dev.write_x)
        self.y_position.connect_to_hardware(dev.read_y, dev.write_y)
        self.z_position.connect_to_hardware(dev.read_z, dev.write_z)

    def disconnect(self):
        
        self.settings.disconnect_all_from_hardware()

        if hasattr(self, 'stage_device'):
            self.stage_device.close()           
            del self.stage_device

