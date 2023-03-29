'''
Created on $DATE_PRETTY

@author: $AUTHORS
'''
from ScopeFoundry.hardware import HardwareComponent


class $HW_CLASS_NAME(HardwareComponent):

    name = "$HW_NAME"

    def setup(self):
        S = self.settings
        S.New("port", str, initial="COM1",
              description='COMx see device manager')
        S.New("property_x", float, ro=False, unit='mm', spinbox_decimals=4, si=False)


    def connect(self):

        S = self.settings

        $IMPORT_DEV
        self.dev = $DEV_CLASS_NAME(S["port"], debug=S['debug_mode'])

        # attache read and write functions to settings
        S.property_x.connect_to_hardware(
            self.dev.read_property_x,
            self.dev.write_property_x)

    def disconnect(self):
        if not hasattr(self, 'dev'):
            return

        # self.settings.disconnect_all_from_hardware()
        self.dev.close()
        del self.dev

    # if you want to continuously update settings implement *run* method
    # def run(self):
    #     self.settings.property_x.read_from_hardware()
