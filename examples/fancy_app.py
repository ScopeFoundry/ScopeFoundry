import sys

from ScopeFoundry import BaseMicroscopeApp
from ScopeFoundry.examples.ScopeFoundryHW.bsinc_noiser200 import Noiser200HW
from ScopeFoundry.examples.ScopeFoundryHW.simulon_xyz_stage import SimulonXYZStageHW
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

        # ## Example scan measurements
        # Each actuator can be defined with a tuple of settings paths. The following formats are supported:
        # 1. (name, position_path | position_read_func, target_position_path | target_position_write_func)
        # 2. (name, target_position_path | target_position_write_func) -> target_position_path=position_path
        # 3. (target_position_path) -> name=target_position_path=position_path
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

        # ## Other Built-in Measurements
        # https://scopefoundry.org/docs/20_built-in-measurements/
        #
        # from ScopeFoundry.sequencer import Sequencer, SweepSequencer

        # self.add_measurement(Sequencer)
        # self.add_measurement(SweepSequencer)

        # from ScopeFoundry import RangedOptimization

        # self.add_measurement(RangedOptimization(self))

        # from ScopeFoundry import PIDFeedbackControl

        # self.add_measurement(PIDFeedbackControl(self))


if __name__ == "__main__":
    app = FancyApp(sys.argv)
    app.settings_load_ini("default_settings.ini")
    sys.exit(app.exec_())
