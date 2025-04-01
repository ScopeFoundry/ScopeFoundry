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


if __name__ == "__main__":
    app = Example2DSlowScanApp(sys.argv)
    app.settings_load_ini("default_settings.ini")
    sys.exit(app.exec_())
