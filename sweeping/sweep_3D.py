from typing import Sequence, Union

from ScopeFoundry import BaseMicroscopeApp
from ScopeFoundry.scanning.actuators import (
    ActuatorDefinitions,
)

from .collector import Collector
from .sweep_nd_base import SweepNDBase
from .sweep_3D_modes import (
    SCAN_MODES,
    SCAN_MODES_DESCRIPTION,
    mk_data_shape,
    mk_indices_gen,
    mk_positions_gen,
    mk_ranges_consistent,
)


class Sweep3D(SweepNDBase):

    name = "sweep_3d"

    def __init__(
        self,
        app: BaseMicroscopeApp,
        name: Union[str, None] = None,
        collectors: Sequence[Collector] = (),
        actuators: Sequence[ActuatorDefinitions] = (),
        actuator_names: Sequence[str] = "123",
        range_n_intervals: Sequence[int] = (1, 1, 1),
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
        """Override to customize layout for 3D scans."""
        from qtpy import QtWidgets

        w3 = self.settings.New_UI(("scan_mode",))
        w3.layout().setSpacing(4)

        h_layout = QtWidgets.QHBoxLayout()
        h_layout.setSpacing(6)

        for i in self.actuator_names:
            r = self.settings.ranges[f"range_{i}"]
            w1 = r.New_UI()
            w1.layout().insertRow(
                0, self.settings.get_lq(f"actuator_{i}").new_default_widget()
            )
            w1.layout().setSpacing(2)
            w1.setMaximumWidth(120)
            h_layout.addWidget(w1)

        widget = QtWidgets.QGroupBox("Scan Settings")
        v_layout = QtWidgets.QVBoxLayout(widget)
        v_layout.setSpacing(6)
        v_layout.setContentsMargins(8, 12, 8, 8)
        v_layout.addWidget(w3)
        v_layout.addLayout(h_layout)

        widget.setFlat(False)
        return widget
