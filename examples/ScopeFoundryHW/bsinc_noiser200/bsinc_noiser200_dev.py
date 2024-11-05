import random


class Noiser200Dev:
    """provides an interface between your hardware and python."""

    def __init__(self, port) -> None:
        self.port = port
        # establishing a connection to hardware

    # some awesome value read
    def read_signal(self):
        return random.uniform(0, 1)

    # some awesome value read
    def write_voltage(self, voltage):
        print("wrote a voltage", voltage)
