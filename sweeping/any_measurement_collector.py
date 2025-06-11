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
        app: BaseMicroscopeApp,
        name: str = None,
        acquisition_duration_path: str = None,
        reps_lq_path: str = None,
        target_measure_name: str = None,
        color: Tuple[int] = None,
        to_sec_multiplier: float = None,
        description: str = None,
        measure_lq: LoggedQuantity = None,
    ):

        super().__init__(
            app,
            name,
            acquisition_duration_path,
            reps_lq_path,
            target_measure_name,
            color,
            to_sec_multiplier,
            description,
        )
        self.measure_lq = measure_lq

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
