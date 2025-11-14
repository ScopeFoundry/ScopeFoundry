from typing import Sequence, Union

from ScopeFoundry import BaseMicroscopeApp
from ScopeFoundry.scanning.actuators import (
    ActuatorDefinitions,
)

from .collector import Collector
from .sweep_nd_base import SweepNDBase
from .sweep_2D_modes import (
    SCAN_MODES,
    SCAN_MODES_DESCRIPTION,
    mk_data_shape,
    mk_indices_gen,
    mk_positions_gen,
    mk_ranges_consistent,
)


class Sweep2D(SweepNDBase):

    name = "sweep_2d"

    def __init__(
        self,
        app: BaseMicroscopeApp,
        name: Union[str, None] = None,
        collectors: Sequence[Collector] = (),
        actuators: Sequence[ActuatorDefinitions] = (),
        actuator_names: Sequence[str] = "12",
        range_n_intervals: Sequence[int] = (1, 1),
        n_read_any_settings: int = 2,
        n_any_measurements: int = 2,
    ):
        super().__init__(
            app=app,
            name=name,
            collectors=collectors,
            actuators=actuators,
            actuator_names=actuator_names,
            range_n_intervals=range_n_intervals,
            n_read_any_settings=n_read_any_settings,
            n_any_measurements=n_any_measurements,
        )

    # Implement abstract methods from base class
    def get_scan_modes(self):
        return SCAN_MODES

    def get_scan_modes_description(self):
        return SCAN_MODES_DESCRIPTION

    def mk_data_shape(self, *args):
        return mk_data_shape(*args)

    def mk_indices_gen(self, *args):
        return mk_indices_gen(*args)

    def mk_positions_gen(self, *args):
        return mk_positions_gen(*args)

    def mk_ranges_consistent(self, settings, actuator_names):
        return mk_ranges_consistent(settings, actuator_names)
