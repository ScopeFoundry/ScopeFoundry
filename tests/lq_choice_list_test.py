import unittest
from ScopeFoundry.measurement import Measurement
from ScopeFoundry import BaseMicroscopeApp


class DummyMeasure(Measurement):
    name = "dummy"

    def setup(self):
        self.settings.New("choices", int, choices=INITIAL_CHOICES)


INITIAL_CHOICES = [("choice 1", 1), ("choice 2", 2)]


class ChoiceListTest(unittest.TestCase):
    
    def setUp(self):
        self.app = BaseMicroscopeApp([])
        self.app.add_measurement(DummyMeasure(self))
        
    def test_initial_value_set(self): 
        self.assertEqual(self.app.measurements.dummy.settings["choices"], 1)        

    def test_change_choice_list_all_new_choices(self): 
        lq = self.app.measurements.dummy.settings.get_lq("choices")
        lq.change_choice_list([("choice 3", 3)])  
        self.assertEqual(lq.val, 3)

    def test_change_choice_list_containing_oldval(self): 
        lq = self.app.measurements.dummy.settings.get_lq("choices")
        lq.change_choice_list([("choice 1 renamed", 1), ("choice 3", 3)])  
        self.assertEqual(lq.val, 1)
    
    def test_change_choice_list_all_new(self): 
        lq = self.app.measurements.dummy.settings.get_lq("choices")
        lq.change_choice_list([("choice 3", 3), ("choice 4", 4)])  
        self.assertEqual(lq.val, 3)    
        
    def test_change_choice_list_empty(self): 
        lq = self.app.measurements.dummy.settings.get_lq("choices")
        lq.change_choice_list([])  
        self.assertEqual(lq.val, 1)  # for now expected behavior

    def test_add_choices(self): 
        lq = self.app.measurements.dummy.settings.get_lq("choices")
        lq.add_choices([("choice 4", 4)])
        self.assertEqual(lq.val, 1)
        self.assertIn(("choice 4", 4), lq.choices)

    def test_add_choices_overlapping(self): 
        lq = self.app.measurements.dummy.settings.get_lq("choices")
        lq.add_choices([("choice 2", 2), ("choice 4", 4)])
        self.assertEqual(lq.val, 1)
        self.assertIn(("choice 1", 1), lq.choices)
        self.assertIn(("choice 2", 2), lq.choices)
        self.assertIn(("choice 4", 4), lq.choices)

    def test_add_choices_and_set(self): 
        lq = self.app.measurements.dummy.settings.get_lq("choices")
        lq.add_choices([("choice 4", 4)], new_val=2)
        self.assertEqual(lq.val, 2)

    def test_add_empty(self): 
        lq = self.app.measurements.dummy.settings.get_lq("choices")
        lq.add_choices([])
        self.assertEqual(lq.val, 1)  # for now expected behavior

    def test_remove_a_set_choice(self): 
        lq = self.app.measurements.dummy.settings.get_lq("choices")
        lq.remove_choices([("choice 1", 1)])
        self.assertEqual(lq.val, 2) 
        
    def test_remove_unset_choice(self): 
        lq = self.app.measurements.dummy.settings.get_lq("choices")
        lq.remove_choices([("choice 2", 2)])
        self.assertEqual(lq.val, 1)
   
    def test_remove_all(self): 
        lq = self.app.measurements.dummy.settings.get_lq("choices")
        lq.remove_choices(INITIAL_CHOICES)
        self.assertEqual(lq.val, 1)  # for now expected behavior

                                
if __name__ == '__main__':
    unittest.main()
    
