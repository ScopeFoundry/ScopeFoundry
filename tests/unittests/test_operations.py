import unittest
from unittest.mock import Mock

from qtpy.QtWidgets import QApplication

from ScopeFoundry.operations import Operations


class TestOperations(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication([])

    def setUp(self):
        self.operations = Operations()

    def test_add_operation(self):
        mock_func = Mock()
        operation = self.operations.new(
            "test_op", mock_func, "Test Operation", "path/to/icon"
        )
        self.assertIn("test_op", self.operations)
        self.assertEqual(self.operations.get("test_op"), operation)

    def test_remove_operation(self):
        mock_func = Mock()
        self.operations.new("test_op", mock_func, "Test Operation", "path/to/icon")
        self.operations.remove("test_op")
        self.assertNotIn("test_op", self.operations)

    def test_get_operation(self):
        mock_func = Mock()
        operation = self.operations.new(
            "test_op", mock_func, "Test Operation", "path/to/icon"
        )
        retrieved_operation = self.operations.get("test_op")
        self.assertEqual(operation, retrieved_operation)

    def test_new_button(self):
        mock_func = Mock()
        self.operations.new("test_op", mock_func, "Test Operation", "path/to/icon")
        button = self.operations.new_button("test_op")
        self.assertEqual(button.objectName(), "test_op")
        self.assertEqual(button.toolTip(), "Test Operation")

    def test_signal_add_operation(self):
        mock_func = Mock()
        self.operations.q_object.added.connect(mock_func)
        self.operations.new("test_op", Mock(), "Test Operation", "path/to/icon")
        mock_func.assert_called_once_with("test_op")

    def test_signal_remove_operation(self):
        mock_func = Mock()
        self.operations.new("test_op", Mock(), "Test Operation", "path/to/icon")
        self.operations.q_object.removed.connect(mock_func)
        self.operations.remove("test_op")
        mock_func.assert_called_once_with("test_op")

    @classmethod
    def tearDownClass(cls):
        cls.app.quit()


if __name__ == "__main__":
    unittest.main()
