import time

from ScopeFoundry import HardwareComponent
from ScopeFoundry.examples.ScopeFoundryHW.bsinc_noiser200.bsinc_noiser200_dev import (
    Noiser200Dev,
)


class Noiser200HW(HardwareComponent):

    name = "noiser_200"

    def setup(self):

        self.settings.New("port", str, initial="Com200")
        self.signal = self.settings.New("signal", float, ro=True, unit="Hz", si=True)
        self.voltage = self.settings.New(
            name="voltage",
            dtype=float,
            unit="V",
            si=True,
            protected=True,  # do not want to write a voltage from a file
        )

    def connect(self):
        self.dev = Noiser200Dev(self.settings["port"])

        self.signal.connect_to_hardware(read_func=self.dev.read_signal)
        self.voltage.connect_to_hardware(write_func=self.dev.write_voltage)

    def disconnect(self):

        self.settings.disconnect_all_from_hardware()

        if hasattr(self, "dev"):
            del self.dev

    # def threaded_update(self):  # define for continueous update after connect
    #     self.signal.read_from_hardware()
    #     time.sleep(0.1)
