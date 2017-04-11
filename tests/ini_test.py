from ScopeFoundry import BaseApp
import unittest
import time


# see https://bitbucket.org/jmcgeheeiv/pyqttestexample/src/cf039f1a83e390778854f6533adb261d14017d05/src/MargaritaMixerTest.py?at=default&fileviewer=file-view-default

class INI_BaseAppSaveLoadTest(unittest.TestCase):
    
    def setUp(self):
        self.app = BaseApp([])
        
        self.app.settings.New('asdf', dtype=int, initial=12345432334, ro=False, unit='V')
        
        self.ui = self.app.settings.New_UI()
        self.ui.show()
        
        self.ini_fname = "ini_test_%i.ini" % time.time()
        
    def test_save_ini(self):
        self.app.settings_save_ini(self.ini_fname, save_ro=True)
        
    """def test_load_ini(self):
        self.app.settings_load_ini(fname)
    
    """
    def test_round_trip_ini(self):
        self.app.settings_save_ini(self.ini_fname, save_ro=True)
        self.app.settings_load_ini(self.ini_fname)
                        
if __name__ == '__main__':
    unittest.main()
    