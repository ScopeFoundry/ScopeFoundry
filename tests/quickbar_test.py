import unittest

from qtpy import QtWidgets
import test

from ScopeFoundry import BaseMicroscopeApp


class AppWithQuickbarNoFavorites(BaseMicroscopeApp):

    name = "test_quickbar_no_favorites"

    def setup_ui(self):
        self.add_quickbar(QtWidgets.QLabel("this is a quickbar"))


class AppWithNoQuickbarWithFavorites(BaseMicroscopeApp):

    name = "test_no_quickbar_with_favorites"

    def setup_ui(self):
        self.add_favorites(("app/sample",))


class AppWithWithQuickbarWithFavorites(BaseMicroscopeApp):

    name = "test_with_quickbar_with_favorites"

    def setup_ui(self):
        self.add_quickbar(QtWidgets.QLabel("this is a quickbar"))
        self.add_favorites(("app/sample",))


class AppBare(BaseMicroscopeApp):

    name = "test_bare_app"

    def setup_ui(self):
        pass


class QuickbarTest(unittest.TestCase):

    def test_no_crash(self):
        self.app = AppWithQuickbarNoFavorites()

    def test_no_crash_no_quickbar_with_favorites(self):
        self.app = AppWithNoQuickbarWithFavorites()

    def test_no_crash_with_quickbar_with_favorites(self):
        self.app = AppWithWithQuickbarWithFavorites()

    def test_no_crash_bare(self):
        self.app = AppBare()


def main(test_case=0):
    import sys

    if test_case == 0:
        app = AppWithQuickbarNoFavorites(sys.argv)
    elif test_case == 1:
        app = AppWithNoQuickbarWithFavorites(sys.argv)
    elif test_case == 2:
        app = AppWithWithQuickbarWithFavorites(sys.argv)
    else:
        app = AppBare(sys.argv)

    app.exec_()


if __name__ == "__main__":
    # unittest.main()

    main(test_case=0)  # run test_case 0 ... 3 for visual inspection
