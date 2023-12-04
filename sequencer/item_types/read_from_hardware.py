from qtpy.QtWidgets import QComboBox
from typing_extensions import TypedDict

from .editor_base_ui import EditorBaseUI
from .base_item import BaseItem
from .helper_func import new_q_completer

ITEM_TYPE = "read_from_hardware"


class ReadFromHardWareKwargs(TypedDict):
    setting: str


class ReadFromHardWare(BaseItem):
    item_type = ITEM_TYPE

    def visit(self):
        self.app.get_lq(self.kwargs["setting"]).read_from_hardware()


class ReadFromHardWareEditorUI(EditorBaseUI):
    item_type = ITEM_TYPE
    description = "trigger read_from_hardware"

    def __init__(self, measure, paths) -> None:
        self.paths = paths
        super().__init__(measure)

    def setup_ui(self):
        self.setting_cb = QComboBox()
        self.setting_cb.setEditable(True)
        self.setting_cb.addItems(self.paths)
        self.setting_cb.setToolTip("setting to update")
        self.setting_cb.setCompleter(new_q_completer(self.paths))
        self.layout.addWidget(self.setting_cb)

    def get_kwargs(self) -> ReadFromHardWareKwargs:
        return {"setting": self.setting_cb.currentText()}

    def set_kwargs(self, **kwargs):
        self.setting_cb.setCurrentText(kwargs["setting"])
        self.setting_cb.setFocus()
