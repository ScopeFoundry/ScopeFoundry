'''
Created on $DATE_PRETTY

@author: $AUTHORS
'''

from ScopeFoundry.base_app import BaseMicroscopeApp


class TestApp(BaseMicroscopeApp):

    name = "$TEST_APP_NAME"

    def setup(self):
        $ADD_TO_APP


if __name__ == '__main__':
    import sys
    app = TestApp(sys.argv)
    sys.exit(app.exec_())
