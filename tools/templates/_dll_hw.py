'''
Created on $DATE_PRETTY

@author: $AUTHORS
'''
# from time import time

from ScopeFoundry.hardware import HardwareComponent


class $HW_CLASS_NAME(HardwareComponent):

    name = "$HW_NAME"

    def setup(self):


        self.settings.New('dll_path',
                          str,
                          initial=r"path_to_dll")

        self.settings.New("property_x",
                          dtype=float,
                          ro=False,
                          unit='mm',
                          spinbox_decimals=4,
                          si=False
                          )
                          
    def connect(self):
        $IMPORT_DEV

        S = self.settings

        self.dev = $DEV_CLASS_NAME(
            dll_path=S['dll_path'],
            debug=S['debug_mode'])

        # bind read and/or write functions to a setting (sometimes only one is applicable)
        S.get_lq("property_x").connect_to_hardware(
            read_func=self.dev.read_property_x, write_func=self.dev.write_property_x
        )

    def disconnect(self):
        if not hasattr(self, 'dev'):
            return

        # self.settings.disconnect_all_from_hardware()
        self.dev.close()
        del self.dev

    # if you want to continuously update settings implement *run* method
    # def run(self):
    #     self.settings.property_x.read_from_hardware()
    #     time.sleep(0.1)