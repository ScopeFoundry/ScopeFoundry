import unittest
from ScopeFoundry import BaseApp
from ScopeFoundry.logged_quantity.array_lq import ArrayLQ


class LQConnectionTestApp(BaseApp):

    name = "LQConnectionTestApp"

    def __init__(self, argv):
        BaseApp.__init__(self, argv)

        lq0 = self.settings.New("lq0", dtype=float, ro=False, initial=5)
        lq1 = self.settings.New("lq1", dtype=float, ro=False, initial=5)
        lq2 = self.settings.New("lq2", dtype=float, ro=False, initial=35)
        lq3 = self.settings.New("lq3", dtype=float, ro=True, initial=35)
        lq4 = self.settings.New("lq4", dtype=float, ro=False, initial=35)
        lq_sum = self.settings.New("lq_sum", dtype=float, ro=True, initial=35)
        lq_sum_bidir = self.settings.New(
            "lq_sum_bidir", dtype=float, ro=False, initial=35
        )

        lq_scale = self.settings.New("lq_scale", dtype=float, ro=False)
        lq_scale2 = self.settings.New("lq_scale2", dtype=float, ro=False)

        lq1.connect_to_lq(lq2)

        lq3.connect_lq_math(lq1, lambda x1: x1 + 1)

        lq4.connect_lq_math(
            lq1,
            func=lambda x: x + 5,
            reverse_func=lambda y: y - 5,
        )

        def sum_lq(*vals):
            return sum(vals)

        lq_sum.connect_lq_math(
            (lq1, lq2, lq3, lq4), func=lambda a, b, c, d: a + b + c + d
        )

        def lq_sum_reverse(new_val, old_vals):
            a, b = old_vals
            return new_val - b, b

        lq_sum_bidir.connect_lq_math(
            (lq0, lq1), func=sum_lq, reverse_func=lq_sum_reverse
        )

        lq_scale.connect_lq_math(
            (lq0,),
            func=lambda x: 10 * x,
            reverse_func=lambda y,: [
                0.1 * y,
            ],
        )

        lq_scale2.connect_lq_scale(lq0, 25.0)

        lq_array = self.settings.New(
            "lq_array", dtype=float, is_array=True, initial=[1.0, 2.0, 3.0, 4.0]
        )
        lq_array_element = self.settings.New("lq_array_element", dtype=float)
        lq_array_element.connect_lq_math((lq_array,), lambda arr: arr[1])

        test_array: ArrayLQ = self.settings.New(
            "test_array",
            dtype=float,
            is_array=True,
            ro=False,
            fmt="%1.2f",
            initial=[[147, 111, 100]],
        )

        array_follower = self.settings.New("array_follower", dtype=float)

        test_array.connect_element_follower_lq(array_follower, index=(0, 1), bidir=True)

        self.ui = self.settings.New_UI()

        # self.console_widget.show()
        self.ui.show()


class LQConnectionTest(unittest.TestCase):

    def setUp(self):
        self.app = LQConnectionTestApp([])

    def test_connect_to_lq(self):
        self.app.settings["lq1"] = 99
        self.assertEqual(self.app.settings["lq2"], 99)

    def test_connect_to_lq_rev(self):
        self.app.settings["lq2"] = 999
        self.assertEqual(self.app.settings["lq1"], 999)

    def test_lq_math(self):
        self.app.settings["lq1"] = 100
        self.assertEqual(self.app.settings["lq4"], 105)

    def test_lq_math_rev(self):
        self.app.settings["lq4"] = 1005
        self.assertEqual(self.app.settings["lq1"], 1000)

    def test_lq_math_multivariable(self):
        self.app.settings["lq0"] = 33
        self.app.settings["lq1"] = 66
        self.assertEqual(self.app.settings["lq_sum_bidir"], 33 + 66)

    def test_lq_math_multivariable_rev(self):
        self.app.settings["lq1"] = ini_val_lq1 = 1
        self.app.settings["lq_sum_bidir"] = 1
        self.assertEqual(self.app.settings["lq0"], 1 - ini_val_lq1)
        self.assertEqual(self.app.settings["lq1"], ini_val_lq1)

    def test_lq_scale(self):
        self.app.settings["lq0"] = 1
        self.assertEqual(self.app.settings["lq_scale2"], 25)

    def test_lq_scale_rev(self):
        self.app.settings["lq_scale2"] = 50
        self.assertEqual(self.app.settings["lq0"], 2)

    def test_lq_math_with_array(self):
        self.app.settings["lq_array"] = [100, 200, 300, 400]
        self.assertEqual(self.app.settings["lq_array_element"], 200)

    def test_array_follower_rev(self):
        self.app.settings["test_array"] = [[147, 33, 100]]
        self.assertEqual(self.app.settings["array_follower"], 33)
        self.app.settings["array_follower"] = 55
        self.assertEqual(self.app.settings["test_array"][0][1], 55)


if __name__ == "__main__":
    # unittest.main()
    app = LQConnectionTestApp([])
    app.exec_()
