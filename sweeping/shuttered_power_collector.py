# shuttered_power_collector.py
from ScopeFoundry import Collector


class ShutteredPowerCollector(Collector):

    name = "power measurement with shutter"
    target_measure_name = "power_readout"
    repeated_dset_names = ("powers",)

    def prepare(self, host_measurement, *args, **kwargs):
        self.app.hardware.my_shutter.settings["position"] = "open"

    def run(
        self,
        index,
        host_measurement, # host measurement is the Sweep Measurement
        polling_func=None,
        polling_time=0.001,
        int_time=None,
        **kwargs,
    ):
     	
      	# self.target_measure.settings["integration_time"] = int_time
        
        # run a "target measurement" here the defined with the target_measure_name above
        host_measurement.start_nested_measure_and_wait(
            self.target_measure,
            nested_interrupt=False,
            polling_func=polling_func,
            polling_time=polling_time,
        )
        
        # populate the data dictionary of the collector. The host_measurement, ie the Sweep class, will incorporate this data for each repetition and sweep point.
        self.data["powers"] = self.target_measure.get_data()

    def release(self, host_measurement, *args, **kwargs) -> None:
        self.app.hardware.my_shutter.settings["position"] = "close"