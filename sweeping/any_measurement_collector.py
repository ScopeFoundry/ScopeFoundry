from typing import Tuple, Callable

from ScopeFoundry.base_app.base_microscope_app import BaseMicroscopeApp
from ScopeFoundry.logged_quantity import LoggedQuantity
from ScopeFoundry.measurement import Measurement

from .collector import Collector


class AnyMeasurementCollector(Collector):

    name = "any_measurement"
    description = "runs any measurement, does not collect data (measurement is responsible for that)"

    def __init__(
        self,
        host_measurement: Measurement,
        name: str = None,
        target_measure_name: str = None,
        color: Tuple[int] = None,
    ):
        self.host_measurement = host_measurement
        self.measure_lq = self.host_measurement.settings.New(name, str, choices=[])

        super().__init__(
            host_measurement.app,
            name,
            self.measure_lq.path,
            target_measure_name,
            color,
            1,
            "runs any measurement and collects its data",
        )

    def run(
        self,
        index: int,
        host_measurement: Measurement,
        polling_func: Callable = None,
        polling_time: float = 0.001,
        int_time: float = None,
        **kwargs,
    ):
        m_name = self.measure_lq.value
        measurement = self.app.measurements[m_name]

        host_measurement.start_nested_measure_and_wait(
            measurement, False, polling_func, polling_time
        )
        self.data = {}
