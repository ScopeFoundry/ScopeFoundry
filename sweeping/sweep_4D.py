from typing import Sequence, Union

from qtpy import QtWidgets

from ScopeFoundry import BaseMicroscopeApp
from ScopeFoundry.scanning.actuators import (
    ActuatorDefinitions,
)

from .collector import Collector
from .sweep_nd_base import SweepNDBase
from .sweep_4D_modes import (
    SCAN_MODES,
    SCAN_MODES_DESCRIPTION,
    mk_ranges_consistent,
    mk_positions_gen,
    mk_data_shape,
    mk_indices_gen,
)


class Sweep4D(SweepNDBase):

    name = "sweep_4d"

    def __init__(
        self,
        app: BaseMicroscopeApp,
        name: Union[str, None] = None,
        collectors: Sequence[Collector] = (),
        actuators: Sequence[ActuatorDefinitions] = (),
        actuator_names: Sequence[str] = "1234",
        range_n_intervals: Sequence[int] = (1, 1, 1, 1),
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

    def mk_scan_settings_widget(self):
        """Override to customize layout for 4D scans."""
        mode_selector_mode = self.settings.New_UI(("scan_mode",))
        h_layout = QtWidgets.QHBoxLayout()
        h_layout.setSpacing(0)
        h_layout.setContentsMargins(0, 0, 0, 0)
        for i in self.actuator_names:
            l = QtWidgets.QVBoxLayout()
            l.setSpacing(0)
            l.setContentsMargins(0, 0, 0, 0)
            l.addWidget(self.settings.get_lq(f"actuator_{i}").new_default_widget())
            r = self.settings.ranges[f"range_{i}"]
            w = r.New_UI()
            l.addWidget(w)
            h_layout.addLayout(l)

        widget = QtWidgets.QGroupBox("Actuators")
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(mode_selector_mode)
        layout.addLayout(h_layout)
        widget.setMaximumWidth(500)
        widget.setFlat(False)
        return widget
