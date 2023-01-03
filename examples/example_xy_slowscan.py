import sys
from PySide import QtGui

from ScopeFoundry import BaseMicroscopeApp

# Import Hardware Components
from hardware_components.apd_counter import  APDCounterHardwareComponent
from ScopeFoundry.examples.hardware.dummy_xy_stage import DummyXYStageHW

# Import Measurement Components
from measurement_components.apd_optimizer_simple import APDOptimizerMeasurement
from ScopeFoundry.scanning.xy_scan_base import SimpleXYScan


class ExampleXYSlowscanApp(BaseMicroscopeApp):

    #ui_filename = "../../ScopeFoundry/base_gui.ui"

    def setup(self):
        #Add hardware components
        print("Adding Hardware Components")
        self.add_hardware_component(APDCounterHardwareComponent(self))
        self.add_hardware_component(DummyXYStageHW(self))

        #Add measurement components
        print("Create Measurement objects")
        self.add_measurement_component(APDOptimizerMeasurement(self))
        self.add_measurement_component(SimpleXYScan(self))
        
        #set some default logged quantities
        self.hardware_components['apd_counter'].debug_mode.update_value(True)
        self.hardware_components['apd_counter'].dummy_mode.update_value(True)
        self.hardware_components['apd_counter'].connected.update_value(True)

        #Add additional logged quantities

        # Connect to custom gui
        self.ui.show()
        self.ui.activateWindow()


if __name__ == '__main__':
    app = ExampleXYSlowscanApp(sys.argv)
    sys.exit(app.exec_())
