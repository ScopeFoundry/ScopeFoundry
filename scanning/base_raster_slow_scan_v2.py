from typing import Iterable, List, Tuple

from ScopeFoundry.scanning.actuators import (
    ActuatorDefinitions,
    get_actuator_funcs,
    add_all_possible_actuators_and_parse_definitions,
)

from .base_raster_slow_scan import BaseRaster2DSlowScan, BaseRaster3DSlowScan


class BaseRaster2DSlowScanV2(BaseRaster2DSlowScan):

    name = "BaseRaster2DSlowScanV2"

    def __init__(
        self,
        app,
        name: str = None,
        actuators: Iterable[ActuatorDefinitions] = (),
        h_limits: Tuple[float, float] = (-1_000_000_000_000, 1_000_000_000_000),
        v_limits: Tuple[float, float] = (-1_000_000_000_000, 1_000_000_000_000),
        h_unit: str = "",
        v_unit: str = "",
        h_spinbox_decimals: int = 4,
        v_spinbox_decimals: int = 4,
        h_spinbox_step: float = 0.1,
        v_spinbox_step: float = 0.1,
        use_external_range_sync: bool = False,
        circ_roi_size: float = 1.0,
    ):
        self.actuators = actuators
        super().__init__(
            app=app,
            h_limits=h_limits,
            v_limits=v_limits,
            h_unit=h_unit,
            v_unit=v_unit,
            h_spinbox_decimals=h_spinbox_decimals,
            v_spinbox_decimals=v_spinbox_decimals,
            h_spinbox_step=h_spinbox_step,
            v_spinbox_step=v_spinbox_step,
            use_external_range_sync=use_external_range_sync,
            circ_roi_size=circ_roi_size,
        )
        if name is not None:
            self.name = name

    def setup(self):
        super().setup()
        self.h_actuator = self.settings.New("h_actuator", str, choices=())
        self.v_actuator = self.settings.New("v_actuator", str, choices=())
        self.update_actuator_choices()

        self.ui.h_axis_comboBox.setVisible(True)
        self.ui.v_axis_comboBox.setVisible(True)

        self.h_actuator.connect_to_widget(self.ui.h_axis_comboBox)
        self.v_actuator.connect_to_widget(self.ui.v_axis_comboBox)

        self.add_operation("update_actuator_choices", self.update_actuator_choices)

    def update_actuator_choices(self):
        self.actuator_defs = add_all_possible_actuators_and_parse_definitions(
            self.actuators, self.app
        )
        self.actuator_funcs = get_actuator_funcs(self.app, self.actuator_defs)
        choices = list(self.actuator_funcs.keys())
        self.h_actuator.change_choice_list(choices, choices[0])
        self.v_actuator.change_choice_list(choices, choices[1])

    def move_position_slow(self, h, v, dh, dv):
        self.move_position_fast(h, v, dh, dv)

    def move_position_fast(self, h, v, dh, dv):
        self.move_position_start(h, v)

    def move_position_start(self, h, v):
        h_read, h_write = self.actuator_funcs[self.settings["h_actuator"]]
        v_read, v_write = self.actuator_funcs[self.settings["v_actuator"]]

        h_write(h)
        v_write(v)

    def connect_pos_widgets(self):
        try:
            self.disconnect_pos_widgets()
        except ValueError as err:
            print(err)

        sh = self.app.get_lq(self.actuator_defs[self.settings["h_actuator"]][1])
        sv = self.app.get_lq(self.actuator_defs[self.settings["v_actuator"]][1])

        sh.connect_to_widget(self.ui.x_doubleSpinBox)
        sv.connect_to_widget(self.ui.y_doubleSpinBox)

        sh.add_listener(self.update_arrow_pos)
        sv.add_listener(self.update_arrow_pos)

    def disconnect_pos_widgets(self):
        sh = self.app.get_lq(self.actuator_defs[self.settings["h_actuator"]][1])
        sv = self.app.get_lq(self.actuator_defs[self.settings["v_actuator"]][1])

        sh.disconnect_from_widget(self.ui.x_doubleSpinBox)
        sv.disconnect_from_widget(self.ui.y_doubleSpinBox)

        sh.listeners.remove(self.update_arrow_pos)
        sv.listeners.remove(self.update_arrow_pos)

    def update_arrow_pos(self):
        rh, wh = self.actuator_defs[self.settings["h_actuator"]]
        rv, wv = self.actuator_defs[self.settings["v_actuator"]]

        h = self.app.get_lq(wh).value
        v = self.app.get_lq(wv).value

        self.current_stage_pos_arrow.setPos(h, v)


class BaseRaster3DSlowScanV2(BaseRaster3DSlowScan):

    name = "BaseRaster3DSlowScanV2"

    def __init__(
        self,
        app,
        name: str = None,
        actuators: List[ActuatorDefinitions] = (),
        h_limits: Tuple[float, float] = (-1_000_000_000_000, 1_000_000_000_000),
        v_limits: Tuple[float, float] = (-1_000_000_000_000, 1_000_000_000_000),
        z_limits: Tuple[float, float] = (-1_000_000_000_000, 1_000_000_000_000),
        h_unit: str = "",
        v_unit: str = "",
        z_unit: str = "",
        h_spinbox_decimals: int = 4,
        v_spinbox_decimals: int = 4,
        z_spinbox_decimals: int = 4,
        h_spinbox_step: float = 0.1,
        v_spinbox_step: float = 0.1,
        z_spinbox_step: float = 0.1,
        use_external_range_sync: bool = False,
        circ_roi_size: float = 1.0,
    ):
        self.actuators = actuators
        super().__init__(
            app=app,
            h_limits=h_limits,
            v_limits=v_limits,
            z_limits=z_limits,
            h_unit=h_unit,
            v_unit=v_unit,
            z_unit=z_unit,
            h_spinbox_decimals=h_spinbox_decimals,
            v_spinbox_decimals=v_spinbox_decimals,
            z_spinbox_decimals=z_spinbox_decimals,
            h_spinbox_step=h_spinbox_step,
            v_spinbox_step=v_spinbox_step,
            z_spinbox_step=z_spinbox_step,
            use_external_range_sync=use_external_range_sync,
            circ_roi_size=circ_roi_size,
        )
        if name is not None:
            self.name = name

    def setup(self):
        super().setup()
        self.h_actuator = self.settings.New("h_actuator", str, choices=())
        self.v_actuator = self.settings.New("v_actuator", str, choices=())
        self.z_actuator = self.settings.New("z_actuator", str, choices=())
        self.update_actuator_choices()

        self.ui.h_axis_comboBox.setVisible(True)
        self.ui.v_axis_comboBox.setVisible(True)
        self.ui.z_axis_comboBox.setVisible(True)

        self.h_actuator.connect_to_widget(self.ui.h_axis_comboBox)
        self.v_actuator.connect_to_widget(self.ui.v_axis_comboBox)
        self.z_actuator.connect_to_widget(self.ui.z_axis_comboBox)

    def update_actuator_choices(self):
        self.actuator_defs = add_all_possible_actuators_and_parse_definitions(
            self.actuators, self.app
        )
        self.actuator_funcs = get_actuator_funcs(self.app, self.actuator_defs)
        choices = list(self.actuator_funcs.keys())
        self.h_actuator.change_choice_list(choices, choices[0])
        self.v_actuator.change_choice_list(choices, choices[1])
        self.z_actuator.change_choice_list(choices, choices[2])

    def move_position_slow(self, h, v, dh, dv):
        h_read, h_write = self.actuator_funcs[self.settings["h_actuator"]]
        v_read, v_write = self.actuator_funcs[self.settings["v_actuator"]]

        h_write(h)
        v_write(v)

    def move_position_fast(self, h, v, dh, dv):
        self.move_position_slow(h, v, dh, dv)

    def move_position_start(self, h: float, v: float, z: float):
        h_read, h_write = self.actuator_funcs[self.settings["h_actuator"]]
        v_read, v_write = self.actuator_funcs[self.settings["v_actuator"]]
        z_read, z_write = self.actuator_funcs[self.settings["z_actuator"]]

        h_write(h)
        v_write(v)
        z_write(z)

    def connect_pos_widgets(self):
        try:
            self.disconnect_pos_widgets()
        except ValueError as err:
            print(err)

        sh = self.app.get_lq(self.actuator_defs[self.settings["h_actuator"]][1])
        sv = self.app.get_lq(self.actuator_defs[self.settings["v_actuator"]][1])
        sz = self.app.get_lq(self.actuator_defs[self.settings["z_actuator"]][1])

        sh.connect_to_widget(self.ui.x_doubleSpinBox)
        sv.connect_to_widget(self.ui.y_doubleSpinBox)
        sz.connect_to_widget(self.ui.z_doubleSpinBox)

        sh.add_listener(self.update_arrow_pos)
        sv.add_listener(self.update_arrow_pos)
        # sz.add_listener(self.update_arrow_pos)

    def disconnect_pos_widgets(self):

        sh = self.app.get_lq(self.actuator_defs[self.settings["h_actuator"]][1])
        sv = self.app.get_lq(self.actuator_defs[self.settings["v_actuator"]][1])
        sz = self.app.get_lq(self.actuator_defs[self.settings["z_actuator"]][1])

        sh.disconnect_from_widget(self.ui.x_doubleSpinBox)
        sv.disconnect_from_widget(self.ui.y_doubleSpinBox)
        sz.disconnect_from_widget(self.ui.z_doubleSpinBox)

        sh.listeners.remove(self.update_arrow_pos)
        sv.listeners.remove(self.update_arrow_pos)
        # sz.listeners.remove(self.update_arrow_pos)

    def update_arrow_pos(self):
        rh, wh = self.actuator_defs[self.settings["h_actuator"]]
        rv, wv = self.actuator_defs[self.settings["v_actuator"]]
        # rz, wz = self.actuators_definitions[self.settings["z_actuator"]]

        h = self.app.get_lq(wh).value
        v = self.app.get_lq(wv).value
        # z = self.app.get_lq(wz).value

        self.current_stage_pos_arrow.setPos(h, v)
