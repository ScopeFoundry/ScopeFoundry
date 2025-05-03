'''
Created on $DATE_PRETTY

@author: $AUTHORS
'''

# INFO: THE GOAL OF THIS FILE IS TO HANDLE LOW-LEVEL COMMUNICATION THROUGH A DLL
# IT SHOULD BE INDEPENDENT OF ANY SCOPEFOUNDRY FUNCTIONALITY

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
        # Assuming the DLL header file (.5) has a init function:
        # self.dll.init()
        #
        # Assuming the DLL header file (.5) has:
        #   void OpenFirst(int *id)
        # _id = ctypes.c_int()
        # with self.lock:
        #     self.dll.OpenFirst(ctypes.byref(_id))
        # return _id  # Typically can be left as a ctypes object.

    def close(self):
        raise NotImplementedError
        # Example implementation:
        # with self.lock:
        #     self.dll.CLOSE(self._id)

    def write_property_x(self, value):
        raise NotImplementedError
        # Example implementation:
        # Assuming the DLL header file has:
        #   void SET_PROPERTY_X(int id, float value)
        # with self.lock:
        #     self.dll.SET_PROPERTY_X(ctypes.c_float(value))
        # if self.debug:
        #     print(f"write_property_x to value: {value}")

    def read_property_x(self):
        raise NotImplementedError
        # Example implementation:
        # Assuming the DLL header file has:
        #   void GET_PROPERTY_X(int id, float *value)
        # value = ctypes.c_float()
        # with self.lock:
        #     self.dll.GET_PROPERTY_X(self._id, ctypes.byref(value))
        # if self.debug:
        #     print(f"read_property_x: {value.value}")
        # return value.value

    def read_data(self):
        raise NotImplementedError
        # Example implementation:
        # return a list of data points


if __name__ == '__main__':
    dev = $DEV_CLASS_NAME('path_to_dll', debug=True)
    print(dev.read_property_x())
    dev.write_property_x(999.1)
    print(dev.read_property_x())
    dev.close()
