from ScopeFoundry import HardwareComponent
from ScopeFoundry.examples.ScopeFoundryHW.simulon_xyzstage.simulon_xyz_stage_dev import (
    SimulonXYZStageDev,
)


class SimulonXYZStageHW(HardwareComponent):

    name = "simulon_xyz_stage"

    def setup(self):
        position_params = {
            "dtype": float,
            "ro": False,
            "initial": -1,
            "vmin": -1,
            "vmax": 100,
            "si": False,
            "unit": "um",
            "reread_from_hardware_after_write": True,
            "spinbox_decimals": 3,
        }

        self.x_position = self.settings.New("x_position", **position_params)
        self.y_position = self.settings.New("y_position", **position_params)
        self.z_position = self.settings.New("z_position", **position_params)

    def connect(self):

        dev = self.stage_device = SimulonXYZStageDev(debug=self.debug_mode.val)

        self.x_position.connect_to_hardware(dev.read_x, dev.write_x)
        self.y_position.connect_to_hardware(dev.read_y, dev.write_y)
        self.z_position.connect_to_hardware(dev.read_z, dev.write_z)

    def disconnect(self):

        self.settings.disconnect_all_from_hardware()

        if hasattr(self, "stage_device"):
            self.stage_device.close()
            del self.stage_device
