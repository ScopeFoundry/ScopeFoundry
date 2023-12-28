import time

from qtpy.QtWidgets import QDoubleSpinBox
from typing_extensions import TypedDict

from .base_item import BaseItem
from .editor_base_ui import EditorBaseUI

ITEM_TYPE = "timeout"


class TimoutKwargs(TypedDict):
    time: float


class Timeout(BaseItem):
    item_type = ITEM_TYPE

    def visit(self):
        t0 = time.time()
        while True:
            dt = time.time() - t0
            if self.measure.interrupt_measurement_called or dt > self.kwargs["time"]:
                break
            time.sleep(0.50)


class TimeoutEditorUI(EditorBaseUI):
    item_type = ITEM_TYPE
    description = "wait for a bit"

    def setup_ui(self):
        time_out_layout = self.group_box.layout()
        self.time_dsb = QDoubleSpinBox()
        self.time_dsb.setValue(0.1)
        self.time_dsb.setToolTip("time-out in sec")
        self.time_dsb.setMaximum(1e6)
        self.time_dsb.setDecimals(3)
        time_out_layout.addWidget(self.time_dsb)

    def get_kwargs(self) -> TimoutKwargs:
        return {"time": self.time_dsb.value()}

    def set_kwargs(self, **kwargs):
        self.time_dsb.setValue(kwargs["time"])
        self.time_dsb.selectAll()
        self.time_dsb.setFocus()
