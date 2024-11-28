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
    include_timestamp: bool


class NewDir(BaseItem):
    item_type = ITEMTYPE

    def visit(self):
        t0 = time.time()
        name = self.kwargs["new_dir_name"]
        include_timestamp = self.kwargs.get("include_timestamp", True)
        if include_timestamp or not name:
            sub_dir = f"{datetime.fromtimestamp(t0):%y%m%d_%H%M%S}_{name}"
        else:
            sub_dir = name
        new_dir = Path(self.app.settings["save_dir"]) / sub_dir
        new_dir.mkdir(exist_ok=True)
        self.app.settings["save_dir"] = new_dir.as_posix()

    def _update_appearance(self, text=None) -> str:
        kwargs: NewDirKwargs = self.kwargs
        if text == None:
            if self.kwargs.get("include_timestamp", True):
                text = f"New dir: [Timestamp]_{kwargs['new_dir_name']}"
            else:
                text = f"New dir: {kwargs['new_dir_name']}"
        self.setText(text)
        return text


class NewDirEditorUI(EditorBaseUI):
    item_type = ITEMTYPE
    description = f"creates sub folder and set as save_dir"

    def setup_ui(self):
        self.new_dir_name_lineEdit = QLineEdit()
        self.include_timestamp_cb = QCheckBox()
        self.include_timestamp_cb.setFixedWidth(22)
        self.include_timestamp_cb.setToolTip("include a date in the folder name")
        self.group_box.layout().addWidget(self.include_timestamp_cb)
        self.group_box.layout().addWidget(self.new_dir_name_lineEdit)

    def get_kwargs(self) -> NewDirKwargs:
        val = self.new_dir_name_lineEdit.text()
        include_timestamp = self.include_timestamp_cb.isChecked()
        return {"new_dir_name": val, "include_timestamp": include_timestamp}

    def set_kwargs(self, new_dir_name, include_timestamp=True):
        self.new_dir_name_lineEdit.setText(new_dir_name)
        self.include_timestamp_cb.setChecked(include_timestamp)
        self.new_dir_name_lineEdit.setFocus()


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
