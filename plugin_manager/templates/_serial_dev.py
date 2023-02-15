
'''
Created on $DATE_PRETTY

@author: $AUTHORS
'''

# GOAL OF THIS FILE IS TO HANDLE LOW LEVEL COMMUNICATION THROUGH A SERIAL PORT
# SHOULD BE INDEPENDENT OF ANY SCOPEFOUNDRY FUNCTIONALITY.
# RUN THIS FILE TO TEST CONNECTION, TESTING COMMANDS WHILE CHECK main()

import serial
import time

# GUESS OR FROM DEVICE DOCUMENTATION
NEWLINE = "\r"  # typically "\r", "\r\n" or "\n"


class $DEV_CLASS_NAME:

    def __init__(self,
                 port="COM1",  # on windows see device manager
                 debug=False):

        self.port = port
        self.debug = debug

        # TODO: FROM DEVICE DOCUMENTATION
        baudrate = 115200
        bytesize = 8
        parity = 'N'
        stopbits = 1
        xonxoff = False
        rtscts = True

        timeout = 1.0

        self.ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=bytesize,
            parity=parity,
            stopbits=stopbits,
            xonxoff=xonxoff,
            rtscts=rtscts,
            timeout=timeout
        )

    def write(self, cmd: str):
        if self.debug:
            print("write:", repr(cmd))
        self.ser.write((cmd + NEWLINE).encode())

    def query(self, cmd: str):
        self.write(cmd)
        time.sleep(0.01)
        resp: bytes = self.ser.readline()
        if self.debug:
            print("resp:", resp.decode())
        return resp.decode()

    def close(self):
        self.ser.close()

    def write_property_x(self, value):
        raise NotImplementedError
        # TYPICALLY:
        # self.write(f'SET_PROPERTY_X_CMD {value}')

    def read_property_x(self):
        raise NotImplementedError
        # TYPICALLY:
        # resp = self.query(f'GET_PROPERTY_X_CMD {value}')
        # return 'convert_to_float(resp)'

    def read_data(self):
        # NOTE read_data is a too generic function name
        raise NotImplementedError

        # TYPICALLY:
        # resp = self.query(f'GET_DATA_COMMAND {value}')
        # return a list of data points from resp.


if __name__ == '__main__':
    print('start')
    dev = $DEV_CLASS_NAME(port="COM1",  # TODO: on windows see device manager
                          debug=True)
    print(dev.query('TEST_DOCUMENTED_CMD_HERE'))

    # print(dev.read_property_x())
    # print(dev.read_data())

    print('done')
