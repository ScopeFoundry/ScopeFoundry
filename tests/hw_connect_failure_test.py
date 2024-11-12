import logging
import time
import unittest

from ScopeFoundry import BaseMicroscopeApp, HardwareComponent


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
        if self.settings["fail_on_disconnect"]:
            raise IOError("DISCONNECT FAIL!")


class TestApp(BaseMicroscopeApp):

    name = 'test_app'

    def setup(self):

        self.add_hardware(TestFailHW(self))
        logging.getLogger("LoggedQuantity").setLevel('DEBUG')


class TestAppTest(unittest.TestCase):

    def setUp(self):
        # import sys

        self.app = TestApp([])
        self.hw = self.app.hardware["fail_hw"]
        logging.getLogger("LoggedQuantity").setLevel("ERROR")

    def tearDown(self) -> None:
        self.app.on_close()
        del self.app
        return super().tearDown()

    def test_connect(self):
        self.hw.settings["fail_on_connect"] = False
        self.hw.settings["fail_on_disconnect"] = False
        # self.hw.settings["connected"] = True
        self.hw.enable_connection(True)
        self.assertTrue(self.hw.settings["connected"])

    def test_connect_failure(self):
        self.hw.settings["fail_on_connect"] = True
        self.hw.settings["fail_on_disconnect"] = False
        with self.assertRaises(IOError):
            self.hw.enable_connection(True)
        time.sleep(0.1)
        self.assertFalse(self.hw.settings["connected"])

    def test_disconnect_failure(self):
        self.hw.settings["fail_on_connect"] = False
        self.hw.settings["fail_on_disconnect"] = True
        with self.assertRaises(IOError):
            self.hw.enable_connection(True)
            self.hw.enable_connection(False)
        # self.assertTrue(self.hw.settings["connected"]) # Behavior as of now. But what behaviour do we actully want here?


if __name__ == '__main__':
    # unittest.main()
    import sys
    app = TestApp(sys.argv)

    app.exec_()
