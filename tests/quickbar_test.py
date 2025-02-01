import unittest

from qtpy import QtWidgets

from ScopeFoundry import BaseMicroscopeApp


class App(BaseMicroscopeApp):

    name = "quickbar_test"

    def setup_ui(self):
        self.add_quickbar(QtWidgets.QLabel("this is a quickbar"))


class QuickbarTest(unittest.TestCase):

    def test_no_crash(self):
        self.app = App()


if __name__ == "__main__":
    # unittest.main()
    import sys

    app = App(sys.argv)

    app.exec_()
