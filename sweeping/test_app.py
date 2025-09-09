import sys
from qtpy import QtWidgets

from ScopeFoundry import BaseMicroscopeApp


class MyFancyApp(BaseMicroscopeApp):

    name = "My Fancy App"

    def setup(self):
        from ScopeFoundry import Map2D, Sweep1D, Sweep2D, Sweep3D, Sweep4D

        self.add_measurement(Sweep2D(self))
        ...


if __name__ == "__main__":
    app = MyFancyApp(sys.argv)
    sys.exit(app.exec_())


class MyFancyApp(BaseMicroscopeApp):

    name = "My Fancy App"

    def setup(self):
        from .shuttered_power_collector import ShutteredPowerCollector

        collectors = [ShutteredPowerCollector]

        from ScopeFoundry import Map2D, Sweep1D, Sweep2D, Sweep3D, Sweep4D

        self.add_measurement(Sweep2D(self, collectors=collectors))
        ...


explicite_actuators = [
    (
        "x",
        "hw/xyz_stage/x_position",
        "hw/xyz_stage/x_target_position",
    ),
    (
        "y",
        "hw/xyz_stage/y_position",
        "hw/xyz_stage/y_target_position",
    ),
]


class MyFancyApp(BaseMicroscopeApp):

    name = "My Fancy App"

    def setup(self):
        from .shuttered_power_collector import ShutteredPowerCollector

        collectors = [ShutteredPowerCollector]

        from ScopeFoundry import Map2D, Sweep1D, Sweep2D, Sweep3D, Sweep4D

        self.add_measurement(Sweep2D(self, actuators=explicite_actuators))
        ...

    def write_target_signal_wavelength_powermeter(self, wl):
        self.get_lq("hw/thorlabs_powermeter/wavelength").update_value(wl)
        self.get_lq("hw/thorlabs_powermeter_2/wavelength").update_value(wl)
        self.opo.write_target_signal_wavelength_and_wait(wl)


class MyFancyApp(BaseMicroscopeApp):

    name = "My Fancy App"

    def my_generic_actuator_write_function(self, new_value):
        self.hardware.my_hardware.settings["target_position"] = new_value
        self.hardware.my_hardware_2.settings["target_position"] = new_value
        # potentially wait until values are set.
        ...

    def my_generic_actuator_read_function(self) -> float:
        pass
        # return a value

    def setup(self):
        ...
        actuators = [
            (
                "generic_actuator",
                self.my_generic_actuator_read_function,
                self.my_generic_actuator_write_function,
            ),
            ...,
        ]

        from ScopeFoundry import Map2D, Sweep1D, Sweep2D, Sweep3D, Sweep4D

        self.add_measurement(Sweep2D(self, actuators=actuators))
        ...
