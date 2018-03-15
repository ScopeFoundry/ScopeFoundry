from ScopeFoundry import BaseMicroscopeApp, HardwareComponent
import logging

class TestFailHW(HardwareComponent):
    
    name = 'fail_hw'

    def setup(self):
        print(self.name, "setup")

        self.settings.New('fail_on_connect', dtype=bool)
        self.settings.New('fail_on_disconnect', dtype=bool, initial=False)

    def connect(self):
        print(self.name, "connect")  
        if self.settings['fail_on_connect']:     
            raise IOError("CONNECT FAIL!")

    def disconnect(self):
        print(self.name, "disconnect")        
        if self.settings['fail_on_disconnect']:     
            raise IOError("DISCONNECT FAIL!")


class TestApp(BaseMicroscopeApp):
    
    name = 'test_app'
    
    def setup(self):
        
        self.add_hardware(TestFailHW(self))
        logging.getLogger("LoggedQuantity").setLevel('DEBUG')
    
    
if __name__ == '__main__':
    import sys
    app = TestApp(sys.argv)
    
    app.exec_()
    