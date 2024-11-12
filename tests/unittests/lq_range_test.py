import unittest

from ScopeFoundry.logged_quantity.collection import LQCollection


class LQRangeTest(unittest.TestCase):

    def setUp(self):
        self.settings = LQCollection("")
        self.settings.New_Range("x", True, False, (1000.0, 2000.0, 51))

    def test_set_initials(self):

        s = LQCollection("")
        s.New_Range("x", True, False, (1000.0, 2000.0, 100))

        self.assertEqual(s["x_min"], 1000.0)
        self.assertEqual(s["x_max"], 2000.0)
        self.assertEqual(s["x_center"], 1500.0)
        self.assertEqual(s["x_num"], 11)
        self.assertEqual(s["x_step"], 100.0)
        self.assertEqual(s["x_span"], 1000.0)

    def test_set_bounds(self):
        s = self.settings

        s["x_num"] = 11
        s["x_min"] = 0
        s["x_max"] = 1

        self.assertEqual(s["x_center"], 0.5)

    def test_update_center(self):
        s = self.settings

        s["x_num"] = 11
        s["x_min"] = 0
        s["x_max"] = 1
        s["x_center"] = 0.7

        self.assertAlmostEqual(s["x_min"], 0.2)
        self.assertAlmostEqual(s["x_max"], 1.2)

    def test_update_center_span(self):
        s = self.settings

        s["x_num"] = 11
        s["x_min"] = 0
        s["x_max"] = 1

        s["x_center"] = 0
        s["x_span"] = 100

        self.assertEqual(s["x_min"], -50)
        self.assertEqual(s["x_max"], 50)

    def test_span_num(self):
        s = self.settings

        s["x_span"] = 200
        s["x_num"] = 101

        self.assertEqual(s["x_step"], 2)


if __name__ == "__main__":
    unittest.main()
