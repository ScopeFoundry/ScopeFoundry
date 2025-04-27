"""
Created on Feb 18, 2025

@author: Benedikt Ursprung
"""

from typing import Callable, Tuple

from ScopeFoundry.base_app.base_microscope_app import BaseMicroscopeApp
from ScopeFoundry.logged_quantity.logged_quantity import LoggedQuantity
from ScopeFoundry.measurement import Measurement


class Collector:
    """triggers measuements and collects data"""

    name: str
    repeated_dset_names: Tuple[str] = ()  # datasets collected at every scan poin
    settings_to_collect: Tuple[str] = ()  # lq_paths collected at every scan poin
    acquisition_duration_path: str = ""  # lq will be displayed in the GUI
    reps_lq_path: str = ""  # lq will be displayed in the GUI
    target_measure_name: str = ""  # used for default prepare and run methods
    color: Tuple[int] = (255, 0, 0)  # currently not used
    to_sec_multiplier: float = 1.0
    description: str = ""  # description of the collector displayed in the GUI

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
    ):
        self.app = app
        self.to_sec_multiplier = to_sec_multiplier

        if name is not None:
            self.name = name
        if acquisition_duration_path is not None:
            self.acquisition_duration_path = acquisition_duration_path
        if reps_lq_path is not None:
            self.reps_lq_path = reps_lq_path
        if target_measure_name is not None:
            self.target_measure_name = target_measure_name
        if color is not None:
            self.color = color
        if to_sec_multiplier is not None:
            self.to_sec_multiplier = to_sec_multiplier
        if description is not None:
            self.description = description

        if self.target_measure_name in app.measurements:
            self.target_measure = app.measurements[self.target_measure_name]
        else:
            self.target_measure = None

        self.data = {}

        # will be a lookup between global and local dsets names, do not change
        self.repeats = []  # will be overwritten

    def reset(self) -> None:
        self.data = {}

    def prepare(self, host_measurement: Measurement, *args, **kwargs):
        """override me! prepare for acquisition"""
        if self.target_measure is not None:
            if "save_h5" in self.target_measure.settings:
                self.target_measure.settings["save_h5"] = False
            if "run_mode" in self.target_measure.settings:
                self.target_measure.settings["run_mode"] = "finite"

    def run(
        self,
        index: int,
        host_measurement: Measurement,
        polling_func: Callable = None,
        polling_time: float = 0.001,
        int_time=None,
        *args,
        **kwargs,
    ):
        """override me!
        - populate / update self.data dict
        - the values of the data dict should not through an error if past
        - not all arguments need to be used.
        """
        host_measurement.start_nested_measure_and_wait(
            self.target_measure,
            nested_interrupt=False,
            polling_func=polling_func,
            polling_time=polling_time,
        )
        self.data = self.target_measure.data

    def release(self, host_measurement: Measurement, *args, **kwargs) -> None:
        """override me! clean up after acquisition or undo prepare"""
        pass

    @property
    def reps(self) -> int:
        return self.reps_lq.val

    @property
    def reps_lq(self) -> LoggedQuantity:
        return self.app.get_lq(self.reps_lq_path)

    @property
    def int_lq(self) -> LoggedQuantity:
        return self.app.get_lq(self.acquisition_duration_path)
