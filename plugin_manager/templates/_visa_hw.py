'''
Created on $DATE_PRETTY

@author: $AUTHORS
'''
from ScopeFoundry.hardware import HardwareComponent


class $HW_CLASS_NAME(HardwareComponent):

    name = "$HW_NAME"



    def setup(self):
        S = self.settings
        S.New("GPIB_address", str, initial="GPIB0::27::INSTR")
        S.New("property_x", float, ro=False, unit='mm', spinbox_decimals=4, si=False)
                          

    def connect(self):
        if hasattr(self, 'dev'):
            return

        S = self.settings

        import pyvisa
        rm = pyvisa.ResourceManager()
        self.dev = rm.open_resource(S["GPIB_address"])
        # attache read and write functions to settings
        # S.property_x.connect_to_hardware(
        #     self.read_property_x,
        #     self.write_property_x)

    def disconnect(self):
        if not hasattr(self, 'dev'):
            return

        # self.settings.disconnect_all_from_hardware()
        self.dev.close()
        del self.dev


    def write_property_x(self, value):
        raise NotImplementedError
        # TYPICALLY:
        # return self.dev.query('SET_PROPERTY_X_CMD_FROM_DOCUMENTATION')

    def read_property_x(self):
        raise NotImplementedError
        # TYPICALLY:
        # return self.dev.query('GET_PROPERTY_X_CMD_FROM_DOCUMENTATION')


    def read_data(self):
        # NOTE read_data is a too generic function name
        raise NotImplementedError

        # TYPICALLY:
        # return self.dev.query('GET_PROPERTY_X_CMD_FROM_DOCUMENTATION')


    # if you want to continuously update settings implement *run* method
    # def run(self):
    #     self.settings.property_x.read_from_hardware()

