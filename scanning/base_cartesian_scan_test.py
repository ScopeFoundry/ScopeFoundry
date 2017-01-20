from ScopeFoundry import BaseMicroscopeApp  
from ScopeFoundry.examples.hardware.dummy_xy_stage import DummyXYStageHW
from base_cartesian_scan import TestCartesian2DSlowScan

import logging
logging.basicConfig(level=logging.DEBUG)#, filename='m3_log.txt')
#logging.getLogger("ipykernel").setLevel(logging.WARNING)
#logging.getLogger('PyQt4').setLevel(logging.WARNING)
logging.getLogger('ScopeFoundry').setLevel(logging.DEBUG)
logging.getLogger('').setLevel(logging.DEBUG)


class TestCartesian2DSlowScanApp(BaseMicroscopeApp):
    
    name = 'app'

    def setup(self):
        
        stage = self.add_hardware_component(DummyXYStageHW(self))
        stage.settings['connected'] = True
        self.test_cart_2d_slow_scan = self.add_measurement_component(TestCartesian2DSlowScan(self))
        
        self.ui.show()
        
        #self.ui.mdiArea.addSubWindow(self.test_cart_2d_slow_scan.ui)
        
        
        S = self.test_cart_2d_slow_scan.settings
        S['h1'] = 100
        S['v1'] = 100
        S['dh'] = S['dv'] = 1.0
        
        

if __name__ == '__main__':
    import sys
    app = TestCartesian2DSlowScanApp([])
    sys.exit(app.exec_())    

