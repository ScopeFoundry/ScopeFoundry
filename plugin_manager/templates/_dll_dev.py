'''
Created on $DATE_PRETTY

@author: $AUTHORS
'''

# INFO: GOAL OF THIS FILE IS TO HANDLE LOW LEVEL COMMUNICATION THROUGH A DLL
# SHOULD BE INDEPENDENT OF ANY SCOPEFOUNDRY FUNCTIONALITY

import ctypes
from threading import Lock


class $DEV_CLASS_NAME:

    def __init__(self, dll_path=r"path_to_dll", debug=False):
        """
        serial_num if defined should be a string or integer
        """
        self.debug = debug
        self.dll = ctypes.windll.LoadLibrary(dll_path + r"/XX.dll")
        self.lock = Lock()
        self._id = self.open()

    def open(self):
        raise NotImplementedError
        # assuming dll .h file has init()
        # self.dll.init()
        #
        # Assuming dll .h file has
        #   void OpenFirst(int *id)
        # _id = ctypes.c_int()
        # with self.lock:
        #     self.dll.OpenFirst(ctypes.byref(_id))
        # return _id  #typically can be left as a ctype

    def close(self):
        raise NotImplementedError
        # good pratice to implement a close function
        # find CLOSE function in dll header file
        # with self.lock:
        #     self.dll.CLOSE(self._id)

    def write_property_x(self, value):
        raise NotImplementedError

        # assuming header file says
        #   void SET_PROPERTY_X(_id, float value)
        # with self.lock:
        #     self.dll.SET_PROPERTY_X(ctypes.c_float(value))
        # if self.debug:
        #     print(write_property_x to value)
        # find CLOSE function in dll header file

    def read_property_x(self):
        raise NotImplementedError

        # assuming header file says
        #   void GET_PROPERTY_X(int id, float *value)
        # value = ctypes.c_float()
        # with self.lock:
        #     self.dll.SET_PROPERTY_X(self._id, ctypes.byref(cvalue))
        # if self.debug:
        #     print(cvalue.value)
        # return cvalue.value

    def read_data(self):
        raise NotImplementedError
        # function name to generic, be more specific
        #
        # return a list of data points


if __name__ == '__main__':
    dev = $DEV_CLASS_NAME('path_to_dll', debug=True)
    print(dev.read_property_x())
    dev.write_property_x(999.1)
    print(dev.read_property_x())
    dev.close()
