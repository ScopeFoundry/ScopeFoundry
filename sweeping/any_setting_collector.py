from typing import Tuple, Callable

from ScopeFoundry.base_app.base_microscope_app import BaseMicroscopeApp
from ScopeFoundry.logged_quantity import LoggedQuantity
from ScopeFoundry.measurement import Measurement

from .collector import Collector


class AnySettingCollector(Collector):

    name = "read_any_setting"
    description = "reads any setting and collects it as data"

    def __init__(
        self,
        host_measurement: Measurement,
        name: str = None,
        reps_lq_path: str = None,
        color: Tuple[int] = None,
    ):
        self.host_measurement = host_measurement
        self.setting_lq = host_measurement.settings.New(name, str, choices=[])

        super().__init__(
            app=host_measurement.app,
            name=name,
            acquisition_duration_path=self.setting_lq.path,
            color=color,
            to_sec_multiplier=1,
            description="read a setting and collect it",
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
        self.repeated_dset_names = (self.setting_lq.val,)
        new_val = self.app.get_lq(self.setting_lq.val).read_from_hardware()
        self.data = {self.setting_lq.val: new_val}
