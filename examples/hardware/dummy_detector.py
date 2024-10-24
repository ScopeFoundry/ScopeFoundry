import random
from ScopeFoundry import HardwareComponent


class DectectorDev:
    def __init__(self, port) -> None:
        self.port = port
        # establishing a connection to hardware

    # some awesome value read
    def read_signal(self):
        return random.uniform(0, 1)

    # some awesome value read
    def write_voltage(self, voltage):
        print("wrote a voltage", voltage)


class DummyDetector(HardwareComponent):

    name = "dummy_detector"

    def setup(self):

        self.settings.New("port", str, initial="ComDummy")
        self.signal = self.settings.New(
            "current_signal", float, ro=True, unit="Hz", si=True
        )
        self.voltage = self.settings.New("voltage", float, unit="V", si=True)

    def connect(self):
        self.dev = DectectorDev(self.settings["port"])

        self.signal.connect_to_hardware(read_func=self.dev.read_signal)
        self.voltage.connect_to_hardware(write_func=self.dev.write_voltage)

    def disconnect(self):

        self.settings.disconnect_all_from_hardware()

        if hasattr(self, "dev"):
            del self.dev

    # def run(self):  # define for constant update
    #     self.signal.read_from_hardware()
    #     time.sleep(0.1)
