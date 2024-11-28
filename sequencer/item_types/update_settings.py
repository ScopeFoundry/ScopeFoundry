from qtpy.QtWidgets import QComboBox, QLineEdit
from typing import TypedDict

from .editor_base_ui import EditorBaseUI
from .base_item import BaseItem
from .helper_func import new_q_completer


ITEM_TYPE = "update-setting"
DESCRIPTION = "update a setting with value, a setting or __<iteration letter>"


class UpdateSettingKwargs(TypedDict):
    setting: str
    value: str


class UpdateSetting(BaseItem):
    item_type = ITEM_TYPE

    def visit(self):
        v = self.kwargs["value"]
        try:
            v = self.app.get_lq(v).val
        except:
            pass
        if isinstance(v, str):
            if "__" in v:
                letter = v[v.find("__") + 2]
                v = self.measure.iter_values[letter]
        self.app.get_lq(self.kwargs["setting"]).update_value(v)


LE_TOOL_TIP = """value used to update. Can be a value, a setting, 
or '__<iteration letter>' """


class UpdateSettingEditorUI(EditorBaseUI):
    item_type = ITEM_TYPE
    description = DESCRIPTION

    def __init__(self, measure, paths) -> None:
        self.paths = paths
        super().__init__(measure)

    def setup_ui(self):
        self.setting_cb = QComboBox()
        self.setting_cb.setEditable(True)
        self.setting_cb.addItems(self.paths)
        self.setting_cb.setToolTip("setting to update")
        self.completer = completer = new_q_completer(self.paths)
        self.setting_cb.setCompleter(completer)
        self.group_box.layout().addWidget(self.setting_cb)
        self.value_le = QLineEdit()
        completer = new_q_completer(
            self.paths + ["True", "False", "__A", "__B", "__C", "__D"]
        )
        self.value_le.setCompleter(completer)

        self.value_le.setToolTip(LE_TOOL_TIP)
        self.group_box.layout().addWidget(self.value_le)

    def get_kwargs(self) -> UpdateSettingKwargs:
        path = self.setting_cb.currentText()
        val = self.value_le.text()
        return {"setting": path, "value": val}

    def set_kwargs(self, **kwargs):
        self.setting_cb.setCurrentText(kwargs["setting"])
        self.value_le.setText(kwargs["value"])
        self.value_le.selectAll()
        self.value_le.setFocus()
