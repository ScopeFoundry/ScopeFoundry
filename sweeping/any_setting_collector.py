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
        app: BaseMicroscopeApp,
        name: str = None,
        acquisition_duration_path: str = None,
        reps_lq_path: str = None,
        target_measure_name: str = None,
        color: Tuple[int] = None,
        to_sec_multiplier: float = None,
        description: str = None,
        setting_lq: LoggedQuantity = None,
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
        self.setting_lq = setting_lq

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
