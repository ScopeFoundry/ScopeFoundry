import sys

from ScopeFoundry import BaseMicroscopeApp
from ScopeFoundry.examples.ScopeFoundryHW.bsinc_noiser200 import Noiser200HW
from ScopeFoundry.examples.ScopeFoundryHW.simulon_xyzstage import SimulonXYZStageHW
from ScopeFoundry.examples.measurements.example_2d_slowscan_measure import (
    Example2DSlowScanMeasure,
)
from ScopeFoundry.examples.measurements.example_3d_slowscan_measure import (
    Example3DSlowScanMeasure,
)


class FancyApp(BaseMicroscopeApp):

    name = "fancy app"

    def setup(self):

        self.add_hardware(SimulonXYZStageHW(self))
        self.add_hardware(Noiser200HW(self))

        # Define the actuators for the scans
        # Each actuator can be defined with a tuple of settings paths. The following formats are supported:
        # 1. (name, position_path, target_position_path)
        # 2. (name, target_position_path) -> position_path=target_position_path
        # 3. (position_path, target_position_path) -> name=position_path
        # 4. (target_position_path) -> name=target_position_path=position_path
        actuators = (
            (
                "x_position",
                "hw/simulon_xyz_stage/x_position",
                "hw/simulon_xyz_stage/x_target_position",
            ),
            (
                "y_position",
                "hw/simulon_xyz_stage/y_position",
                "hw/simulon_xyz_stage/y_target_position",
            ),
            (
                "z_position",
                "hw/simulon_xyz_stage/z_position",
                "hw/simulon_xyz_stage/z_target_position",
            ),
        )

        self.add_measurement(Example2DSlowScanMeasure(self, actuators=actuators))
        self.add_measurement(Example3DSlowScanMeasure(self, actuators=actuators))

        # ## Example of Sweep4D with a custom collector
        # from ScopeFoundry import Sweep2D, Sweep4D
        # from measurements.collectors import Noiser200Collector

        # collectors = [Noiser200Collector(self)]

        # self.add_measurement(Sweep4D(self, actuators=actuators, collectors=collectors))

        # ## Built-in Measurements
        # from ScopeFoundry.sequencer import Sequencer, SweepSequencer

        # self.add_measurement(Sequencer)
        # self.add_measurement(SweepSequencer)

        # ## Other built-in measurements
        # from ScopeFoundry import RangedOptimization

        # self.add_measurement(RangedOptimization(self))

        # from ScopeFoundry import PIDFeedbackControl

        # self.add_measurement(PIDFeedbackControl(self))


if __name__ == "__main__":
    app = FancyApp(sys.argv)
    app.settings_load_ini("default_settings.ini")
    sys.exit(app.exec_())
