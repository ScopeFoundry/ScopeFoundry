import operator
from time import time

from qtpy.QtWidgets import QComboBox, QLineEdit

from .editor_base_ui import EditorBaseUI
from .base_item import BaseItem
from .helper_func import new_q_completer


ITEM_TYPE = "wait-until"
DESCRIPTION = "wait until condition is met"


class WaitUntil(BaseItem):
    item_type = ITEM_TYPE

    def visit(self):
        relate = {"=": operator.eq, ">": operator.gt, "<": operator.lt}[
            self.kwargs["operator"]
        ]
        lq = self.app.get_lq(self.kwargs["setting"])
        val = lq.coerce_to_type(self.kwargs["value"])
        while True:
            if relate(lq.val, val) or self.measure.interrupt_measurement_called:
                break
            time.sleep(0.05)


class WaitUntilEditorUI(EditorBaseUI):
    item_type = ITEM_TYPE
    description = DESCRIPTION

    def __init__(self, measure, paths) -> None:
        self.paths = paths
        super().__init__(measure)

    def setup_ui(self):
        self.setting_cb = QComboBox()
        self.setting_cb.setEditable(True)
        self.setting_cb.addItems(self.paths)
        self.setting_cb.setToolTip("setting")
        self.setting_cb.setCompleter(new_q_completer(self.paths))
        self.layout.addWidget(self.setting_cb)
        self.operator_cb = QComboBox()
        self.operator_cb.addItems(["=", "<", ">"])
        self.layout.addWidget(self.operator_cb)
        self.value_le = QLineEdit()
        self.value_le.setToolTip("wait until setting reaches this value")
        self.layout.addWidget(self.value_le)

    def get_kwargs(self):
        path = self.setting_cb.currentText()
        o = self.operator_cb.currentText()
        v = self.value_le.text()
        return {"setting": path, "operator": o, "value": v}

    def set_kwargs(self, **kwargs):
        self.setting_cb.setCurrentText(kwargs["setting"])
        self.operator_cb.setCurrentText(kwargs["operator"])
        self.value_le.setText(kwargs["value"])
        self.value_le.selectAll()
        self.value_le.setFocus()
