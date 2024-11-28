from typing_extensions import Type

factories = {}


from .base_item import BaseItem, VisitReturnType


def new_item(measure, item_type: str, **kwargs):
    return factories[item_type](measure, **kwargs)


def register_item(item: Type[BaseItem]):
    factories[item.item_type] = item


from .dir_operations import NewDir, NewDirEditorUI, SaveDirToParent, SaveDirToParentEditorUI
from .exec_function import Function, ExecFunctionEditorUI
from .interrupt_if import InterruptIf, IterruptIfEditorUI
from .iterations import (
    EndIterationItem,
    InterationsEditorController,
    IterationsEditorUI,
    StartIterationItem,
    link_iteration_items,
)
from .pause import Pause, PauseEditorUI
from .read_from_hardware import ReadFromHardWare, ReadFromHardWareEditorUI
from .run_measurement import RunMeasurement, RunMeasurementEditorUI
from .timeout import Timeout, TimeoutEditorUI
from .update_settings import UpdateSetting, UpdateSettingEditorUI
from .wait_until import WaitUntil, WaitUntilEditorUI

register_item(InterruptIf)
register_item(NewDir)
register_item(Function)
register_item(StartIterationItem)
register_item(EndIterationItem)
register_item(Pause)
register_item(ReadFromHardWare)
register_item(RunMeasurement)
register_item(Timeout)
register_item(UpdateSetting)
register_item(WaitUntil)
register_item(SaveDirToParent)
