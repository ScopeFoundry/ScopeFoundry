import random


class SimulonXYZStageDev:

    def __init__(self, debug=False):
        self.x = 0
        self.y = 0
        self.z = 0
        self.debug = debug
        # communicate with hardware here

    def read_x(self):
        self.x = self.x + self.noise()
        return self.x

    def read_y(self):
        self.y = self.y + self.noise()
        return self.y

    def read_z(self):
        self.z = self.z + self.noise()
        return self.z

    def write_x(self, x):
        self.x = x

    def write_y(self, y):
        self.y = y

    def write_z(self, z):
        self.z = z

    def close(self):
        pass

    def noise(self):
        return (random.random() - 0.5) * 10e-3
