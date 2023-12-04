import time
from datetime import datetime
from pathlib import Path

from qtpy.QtWidgets import QLabel, QLineEdit
from typing_extensions import TypedDict

from .editor_base_ui import EditorBaseUI
from .base_item import BaseItem

ITEMTYPE = "new_dir"
SAVEDIRITEMTYPE = "save_dir_to_parent"


class NewDirKwargs(TypedDict):
    new_dir_name: str


class NewDir(BaseItem):
    item_type = ITEMTYPE

    def visit(self):
        t0 = time.time()
        name = self.kwargs["new_dir_name"]
        sub_dir = f"{datetime.fromtimestamp(t0):%y%m%d_%H%M%S}_{name}"
        new_dir = Path(self.app.settings["save_dir"]) / sub_dir
        new_dir.mkdir()
        self.app.settings["save_dir"] = new_dir.as_posix()


class NewDirEditorUI(EditorBaseUI):
    item_type = ITEMTYPE
    description = f"creates sub folder and set as save_dir"

    def setup_ui(self):
        self.new_dir_name_lineEdit = QLineEdit()
        self.group_box.layout().addWidget(self.new_dir_name_lineEdit)

    def get_kwargs(self):
        val = self.new_dir_name_lineEdit.text()
        return {"new_dir_name": val}

    def set_kwargs(self, **kwargs):
        self.new_dir_name_lineEdit.setText(kwargs["new_dir_name"])


class SaveDirToParent(BaseItem):
    item_type = SAVEDIRITEMTYPE

    def visit(self):
        cur = Path(self.app.settings["save_dir"])
        self.app.settings["save_dir"] = cur.parent.as_posix()


class SaveDirToParentKwargs(TypedDict):
    info: str


class SaveDirToParentEditorUI(EditorBaseUI):
    item_type = SAVEDIRITEMTYPE
    description = "save_dir to parent, designed use in conjunction with new_dir"

    def setup_ui(self):
        self.spacer = QLabel()
        self.layout.addWidget(self.spacer)

    def get_kwargs(self) -> SaveDirToParentKwargs:
        return {"info": "save_dir jumps to parent"}

    def set_kwargs(self, **kwargs):
        self.spacer.setFocus()
