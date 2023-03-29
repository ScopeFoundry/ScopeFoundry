'''
Created on $DATE_PRETTY

@author: $AUTHORS
'''

from ScopeFoundry.base_app import BaseMicroscopeApp


class TestApp(BaseMicroscopeApp):

    name = "$TEST_APP_NAME"

    def setup(self):
        $IMPORTS_IN_TEST_APP
        self.add_hardware($HW_CLASS_NAME(self))
        self.add_measurement($READOUT_CLASS_NAME(self))


if __name__ == '__main__':
    import sys
    app = TestApp(sys.argv)
    sys.exit(app.exec_())
