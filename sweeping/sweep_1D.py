from typing import Sequence, Union

from qtpy import QtWidgets

from ScopeFoundry import BaseMicroscopeApp
from ScopeFoundry.scanning.actuators import (
    ActuatorDefinitions,
)

from .collector import Collector
from .sweep_nd_base import SweepNDBase
from .sweep_1D_modes import (
    SCAN_MODES,
    SCAN_MODES_DESCRIPTION,
    mk_ranges_consistent,
    mk_positions_gen,
    mk_data_shape,
    mk_indices_gen,
)


class Sweep1D(SweepNDBase):

    name = "sweep_1d"

    def __init__(
        self,
        app: BaseMicroscopeApp,
        name: Union[str, None] = None,
        collectors: Sequence[Collector] = (),
        actuators: Sequence[ActuatorDefinitions] = (),
        actuator_names: Sequence[str] = "1",
        range_n_intervals: Sequence[int] = (1,),
        n_read_any_settings: int = 2,
        n_any_measurements: int = 2,
    ):
        # Add flag for average_to_scan_shape setting
        self.add_average_to_scan_shape = True
        # Add flag for left label in update_display
        self.set_left_label_in_update = True
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

    def should_show_positions_on_x_axis(self):
        """For 1D, don't check scan_mode, just return True if size == 1."""
        return True

    def mk_scan_settings_widget(self):
        """Override to customize layout for 1D scans - no scan mode selector."""
        # For 1D, we only have one actuator
        r = self.settings.ranges[f"range_{self.actuator_names[0]}"]
        w1 = r.New_UI()
        w1.layout().setSpacing(4)
        w1.setMaximumWidth(450)  # Slightly wider for 1D

        widget = QtWidgets.QGroupBox("Actuators")
        v_layout = QtWidgets.QVBoxLayout(widget)
        v_layout.setSpacing(4)
        v_layout.setContentsMargins(3, 5, 3, 3)
        v_layout.addWidget(
            self.settings.get_lq(
                f"actuator_{self.actuator_names[0]}"
            ).new_default_widget()
        )
        v_layout.addWidget(w1)
        widget.setFlat(False)

        return widget
