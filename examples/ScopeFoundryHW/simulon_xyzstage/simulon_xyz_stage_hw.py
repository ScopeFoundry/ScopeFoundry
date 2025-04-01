from ScopeFoundry import HardwareComponent
from ScopeFoundry.examples.ScopeFoundryHW.simulon_xyzstage.simulon_xyz_stage_dev import (
    SimulonXYZStageDev,
)


class SimulonXYZStageHW(HardwareComponent):

    name = "simulon_xyz_stage"

    def setup(self):
        position_params = {
            "dtype": float,
            "initial": -1,
            "vmin": -1,
            "vmax": 100,
            "si": False,
            "unit": "um",
            "spinbox_decimals": 3,
        }

        self.x_position = self.settings.New("x_position", ro=True, **position_params)
        self.y_position = self.settings.New("y_position", ro=True, **position_params)
        self.z_position = self.settings.New("z_position", ro=True, **position_params)
        self.x_target_position = self.settings.New(
            "x_target_position", ro=False, **position_params
        )
        self.y_target_position = self.settings.New(
            "y_target_position", ro=False, **position_params
        )
        self.z_target_position = self.settings.New(
            "z_target_position", ro=False, **position_params
        )

    def connect(self):

        dev = self.stage_device = SimulonXYZStageDev(debug=self.debug_mode.val)

        self.x_position.connect_to_hardware(read_func=dev.read_x)
        self.y_position.connect_to_hardware(read_func=dev.read_y)
        self.z_position.connect_to_hardware(read_func=dev.read_z)

        self.x_target_position.connect_to_hardware(write_func=dev.write_x)
        self.y_target_position.connect_to_hardware(write_func=dev.write_y)
        self.z_target_position.connect_to_hardware(write_func=dev.write_z)

    def disconnect(self):

        self.settings.disconnect_all_from_hardware()

        if hasattr(self, "stage_device"):
            self.stage_device.close()
            del self.stage_device
