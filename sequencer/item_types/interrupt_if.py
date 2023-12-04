import operator

from qtpy.QtWidgets import QComboBox, QLineEdit
from typing_extensions import TypedDict

from .helper_func import new_q_completer
from .editor_base_ui import EditorBaseUI
from .base_item import BaseItem

ITEM_TYPE = "interrupt-if"


class InterruptIfKwargs(TypedDict):
    setting: str
    operator: str
    value: str


class InterruptIf(BaseItem):
    item_type = ITEM_TYPE

    def visit(self):
        relate = {"=": operator.eq, ">": operator.gt, "<": operator.lt}[
            self.kwargs["operator"]
        ]
        lq = self.app.get_lq(self.kwargs["setting"])
        val = lq.coerce_to_type(self.kwargs["value"])
        if relate(lq.val, val):
            self.measure.interrupt()


class IterruptIfEditorUI(EditorBaseUI):
    item_type = ITEM_TYPE
    description = "interrupt if a condition is met"

    def __init__(self, measure, paths) -> None:
        self.paths = paths
        super().__init__(measure)

    def setup_ui(self):
        self.setting_cb = QComboBox()
        self.setting_cb.setEditable(True)
        self.setting_cb.addItems(self.paths)
        self.setting_cb.setToolTip("setting")
        completer = new_q_completer(self.paths)
        self.setting_cb.setCompleter(completer)
        self.layout.addWidget(self.setting_cb)
        self.operator_cb = QComboBox()
        self.operator_cb.addItems(["=", "<", ">"])
        self.layout.addWidget(self.operator_cb)
        self.value_le = QLineEdit()
        self.value_le.setCompleter(completer)
        self.layout.addWidget(self.value_le)

    def get_kwargs(self) -> InterruptIfKwargs:
        path = self.setting_cb.currentText()
        o = self.operator_cb.currentText()
        val = self.value_le.text()
        return {"setting": path, "operator": o, "value": val}

    def set_kwargs(self, **kwargs):
        self.setting_cb.setEditText(kwargs["setting"])
        self.operator_cb.setEditText(kwargs["operator"])
        self.value_le.setText(kwargs["value"])
