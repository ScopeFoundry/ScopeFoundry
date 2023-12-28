from qtpy.QtWidgets import QLabel
from typing_extensions import TypedDict

from .editor_base_ui import EditorBaseUI
from .base_item import BaseItem

ITEMTYPE = "pause"


class PauseKwargs(TypedDict):
    info: str


class Pause(BaseItem):
    item_type = ITEMTYPE

    def visit(self):
        self.measure.settings["paused"] = True




class PauseEditorUI(EditorBaseUI):
    item_type = ITEMTYPE

    description = "pauses - click resume"

    def setup_ui(self):
        self.pause_spacer = QLabel()
        self.group_box.layout().addWidget(self.pause_spacer)

    def get_kwargs(self) -> PauseKwargs:
        return {"info": "click resume to continue"}

    def set_kwargs(self, **kwargs):
        self.pause_spacer.setFocus()
