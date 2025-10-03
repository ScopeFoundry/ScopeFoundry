import sys
import numpy as np
import pyqtgraph as pg
from qtpy import QtWidgets
from ScopeFoundry import BaseMicroscopeApp, HardwareComponent, Measurement


class TestHardware(HardwareComponent):
    name = "test_hw"
    
    def setup(self):
        self.settings.New("test_setting", dtype=float, initial=1.0, vmin=0, vmax=10, spinbox_decimals=2)
        self.settings.New("enable", dtype=bool, initial=True)
        self.settings.New("mode", dtype=str, initial="A", choices=["A", "B", "C"])
    
    def connect(self):
        print(f"{self.name} connected")
    
    def disconnect(self):
        print(f"{self.name} disconnected")


class TestMeasurement(Measurement):
    name = "test_measure"
    
    def setup(self):
        self.settings.New("duration", dtype=float, initial=1.0, unit="s", vmin=0.1, vmax=10)
        self.settings.New("amplitude", dtype=float, initial=1.0, vmin=0, vmax=5)
        self.settings.New("frequency", dtype=float, initial=1.0, unit="Hz", vmin=0.1, vmax=100)
        self.settings.New("enable_noise", dtype=bool, initial=True)
    
    def setup_figure(self):
        self.ui = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(self.ui)
        
        controls_widget = self.settings.New_UI(style="form")
        layout.addWidget(controls_widget)
        
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel('left', 'Signal')
        self.plot_widget.setLabel('bottom', 'Time', units='s')
        layout.addWidget(self.plot_widget)
        
        self.plot_line = self.plot_widget.plot([0], [0], pen='y')
        
        start_btn = QtWidgets.QPushButton("Start")
        start_btn.clicked.connect(self.start)
        stop_btn = QtWidgets.QPushButton("Stop")
        stop_btn.clicked.connect(self.interrupt)
        
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addWidget(start_btn)
        btn_layout.addWidget(stop_btn)
        layout.addLayout(btn_layout)
        
        self.data = []
        self.time_data = []
    
    def run(self):
        import time
        self.data = []
        self.time_data = []
        
        duration = self.settings['duration']
        amplitude = self.settings['amplitude']
        frequency = self.settings['frequency']
        enable_noise = self.settings['enable_noise']
        
        t0 = time.time()
        while True:
            if self.interrupt_measurement_called:
                break
            
            t = time.time() - t0
            if t > duration:
                break
            
            signal = amplitude * np.sin(2 * np.pi * frequency * t)
            if enable_noise:
                signal += 0.1 * amplitude * np.random.randn()
            
            self.time_data.append(t)
            self.data.append(signal)
            
            self.set_progress(100 * t / duration)
            time.sleep(0.05)
    
    def update_display(self):
        if len(self.time_data) > 0:
            self.plot_line.setData(self.time_data, self.data)


class TestApp(BaseMicroscopeApp):
    name = "Dynamic Loading Test"
    
    def setup(self):
        pass


if __name__ == '__main__':
    app = TestApp(sys.argv)
    
    print("\n=== Testing Dynamic Hardware Loading ===")
    hw1 = app.add_hardware(TestHardware)
    print(f"Added hardware: {hw1.name}")
    print(f"Hardware list: {list(app.hardware.keys())}")
    
    print("\n=== Testing Hardware Removal ===")
    app.remove_hardware("test_hw")
    print(f"Hardware list after removal: {list(app.hardware.keys())}")
    
    print("\n=== Testing Re-adding Hardware ===")
    hw2 = app.add_hardware(TestHardware)
    print(f"Added hardware again: {hw2.name}")
    print(f"Hardware list: {list(app.hardware.keys())}")

    print("\n=== Testing Dynamic Measurement Loading ===")
    m1 = app.add_measurement(TestMeasurement)
    print(f"Added measurement: {m1.name}")
    print(f"Measurement list: {list(app.measurements.keys())}")

    print("\n=== Testing Measurement Removal ===")
    app.remove_measurement("test_measure")
    print(f"Measurement list after removal: {list(app.measurements.keys())}")
    
    print("\n=== Testing Re-adding Measurement ===")
    m2 = app.add_measurement(TestMeasurement)
    print(f"Added measurement again: {m2.name}")
    print(f"Measurement list: {list(app.measurements.keys())}")
    
    print("\n=== Test Complete ===")
    print("You should see the tree widget update dynamically.")
    print("Try the following:")
    print("  1. Check that the hardware/measurement appears in the tree")
    print("  2. In the console, run: app.remove_hardware('test_hw')")
    print("  3. Check that it disappears from the tree")
    print("  4. Run: app.add_hardware(TestHardware)")
    print("  5. Check that it reappears")
    
    sys.exit(app.exec_())
