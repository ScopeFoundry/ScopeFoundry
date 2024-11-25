import unittest


from ScopeFoundry import BaseMicroscopeApp
from ScopeFoundry.controlling import PIDFeedbackControl


class TestApp(BaseMicroscopeApp):

    name = "nested_measure_test"

    def setup(self):

        self.pid_m = PIDFeedbackControl(self)
        self.add_measurement(self.pid_m)

    def setup_ui(self):
        self.add_quickbar(self.pid_m.New_mini_UI())


class QuickbarTest(unittest.TestCase):

    def test_no_crash(self):
        self.app = TestApp([])


if __name__ == "__main__":
    # unittest.main()
    import sys

    app = TestApp(sys.argv)

    app.exec_()
