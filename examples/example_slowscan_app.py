import sys


from ScopeFoundry import BaseMicroscopeApp
from ScopeFoundry.examples.example_2d_slowscan_measure import Example2DSlowScanMeasure
from ScopeFoundry.examples.example_3d_slowscan_measure import Example3DSlowScanMeasure
from ScopeFoundry.examples.ScopeFoundryHW.bsinc_noiser200.bsinc_noiser200_hw import (
    Noiser200HW,
)
from ScopeFoundry.examples.ScopeFoundryHW.simulon_xyzstage.simulon_xyz_stage_hw import (
    SimulonXYZStageHW,
)


class Example2DSlowScanApp(BaseMicroscopeApp):

    name = "Example 2D Slow Scan"

    def setup(self):

        from ScopeFoundry.sequencer import Sequencer

        self.add_measurement(Sequencer)

        self.add_hardware(SimulonXYZStageHW(self))
        self.add_hardware(Noiser200HW(self))

        self.add_measurement(Example2DSlowScanMeasure(self))
        self.add_measurement(Example3DSlowScanMeasure(self))


if __name__ == "__main__":
    app = Example2DSlowScanApp(sys.argv)
    app.settings_load_ini("default_settings.ini")
    sys.exit(app.exec_())
