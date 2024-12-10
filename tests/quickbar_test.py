import unittest

from qtpy import QtWidgets

from ScopeFoundry import BaseMicroscopeApp


class TestApp(BaseMicroscopeApp):

    name = "quickbar_test"

    def setup_ui(self):
        self.add_quickbar(QtWidgets.QLabel("this is a quickbar"))


class QuickbarTest(unittest.TestCase):

    def test_no_crash(self):
        self.app = TestApp()


if __name__ == "__main__":
    # unittest.main()
    import sys

    app = TestApp(sys.argv)

    app.exec_()
