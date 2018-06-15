from ScopeFoundry import Measurement, BaseMicroscopeApp
import numpy as np
import pyqtgraph as pg
import time

class Measure1(Measurement):
    
    name = 'measure1'
    
    M = 5

    
    def run(self):
        
        m2 = self.app.measurements['measure2']
        
        self.current_data = [0]
        self.data = [None,]*self.M
        
        # start M2
        for j in range(self.M):
            if self.interrupt_measurement_called:
                break
            self.set_progress(100*(j+1)/(self.M+1))
            m2.settings['amplitude'] = j+1            
            self.start_nested_measure_and_wait(m2, nested_interrupt=True, 
                                               polling_func=self.m2_polling, polling_time=0.5)
            self.data[j] = m2.data_array
    
    def m2_polling(self):
        m2 = self.app.measurements['measure2']
        self.current_data = m2.data_array.copy()
    

    def setup_figure(self):
        self.ui = self.plot = pg.PlotWidget()

        self.current_plotline = self.plot.plot(pen='r')
        self.plot_lines = []
        for j in range(self.M):
            self.plot_lines.append(self.plot.plot())

    def update_display(self):
        
        self.current_plotline.setData(self.current_data)
        
        for j in range(self.M):
            if self.data[j] is None:
                self.plot_lines[j].setData([0])
            else:
                self.plot_lines[j].setData(self.data[j])

class Measure2(Measurement):
    
    name = 'measure2'
    
    def setup(self):
        
        self.settings.New('amplitude', dtype=float, initial=1.0)
        
        
    def setup_figure(self):
        self.ui = self.plot = pg.PlotWidget()
        
        self.plot_line = self.plot.plot()
        
    
    def run(self):
        
        N = 100
        
        self.data_array = np.zeros(N)
        
        for i in range(N):
            if self.interrupt_measurement_called:
                break            
            self.set_progress(100.0*i/N)
            self.data_array[i] = self.settings['amplitude']*np.sin(2*np.pi*i/N)
            time.sleep(0.1)
    
    def update_display(self):
        self.plot_line.setData(self.data_array)

class NestMeasureTestApp(BaseMicroscopeApp):
    
    name = 'nested_measure_test'
    
    def setup(self):
        
        self.add_measurement(Measure1(self))
        self.add_measurement(Measure2(self))
        
        
if __name__ == '__main__':
    import sys
    app = NestMeasureTestApp(sys.argv)
    
    app.exec_()
    