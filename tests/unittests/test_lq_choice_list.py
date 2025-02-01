import unittest
from ScopeFoundry.logged_quantity import LoggedQuantity


INITIAL_CHOICES = [("choice 1", 1), ("choice 2", 2)]


class ChoiceListTest(unittest.TestCase):

    def setUp(self):
        self.lq = LoggedQuantity("choices", int, choices=INITIAL_CHOICES)

    def tearDown(self):
        del self.lq

    def test_initial_value_set(self):
        self.assertEqual(self.lq.val, 1)

    def test_change_choice_list_all_new_choices(self):
        self.lq.change_choice_list([("choice 3", 3)])
        self.assertEqual(self.lq.val, 3)

    def test_change_choice_list_containing_oldval(self):
        self.lq.change_choice_list([("choice 1 renamed", 1), ("choice 3", 3)])
        self.assertEqual(self.lq.val, 1)

    def test_change_choice_list_all_new(self):
        self.lq.change_choice_list([("choice 3", 3), ("choice 4", 4)])
        self.assertEqual(self.lq.val, 3)

    def test_change_choice_list_empty(self):
        self.lq.change_choice_list([])
        self.assertEqual(self.lq.val, 1)  # for now expected behavior

    def test_add_choices(self):
        self.lq.add_choices([("choice 4", 4)])
        self.assertEqual(self.lq.val, 1)
        self.assertIn(("choice 4", 4), self.lq.choices)

    def test_add_choices_overlapping(self):
        self.lq.add_choices([("choice 2", 2), ("choice 4", 4)])
        self.assertEqual(self.lq.val, 1)
        self.assertIn(("choice 1", 1), self.lq.choices)
        self.assertIn(("choice 2", 2), self.lq.choices)
        self.assertIn(("choice 4", 4), self.lq.choices)

    def test_add_choices_and_set(self):
        self.lq.add_choices([("choice 4", 4)], new_val=2)
        self.assertEqual(self.lq.val, 2)

    def test_add_empty(self):
        self.lq.add_choices([])
        self.assertEqual(self.lq.val, 1)  # for now expected behavior

    def test_remove_a_set_choice(self):
        self.lq.remove_choices([("choice 1", 1)])
        self.assertEqual(self.lq.val, 2)

    def test_remove_unset_choice(self):
        self.lq.remove_choices([("choice 2", 2)])
        self.assertEqual(self.lq.val, 1)

    def test_remove_all(self):
        self.lq.remove_choices(INITIAL_CHOICES)
        self.assertEqual(self.lq.val, 1)  # for now expected behavior


if __name__ == "__main__":
    unittest.main()
