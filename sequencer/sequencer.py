"""
Created on Sep 17, 2021

@author: Benedikt Ursprung
"""

import json
import os
from pathlib import Path
import time
from builtins import getattr
from typing import List, Tuple, Dict

from qtpy import QtWidgets, QtCore


from ScopeFoundry import Measurement
from .item_types.editor_base_controller import EditorBaseController
from .item_types.editor_base_ui import EditorBaseUI
from .item_types.item_list import ItemList
from .item_types import (
    BaseItem,
    ExecFunctionEditorUI,
    InterationsEditorController,
    IterationsEditorUI,
    IterruptIfEditorUI,
    NewDirEditorUI,
    PauseEditorUI,
    ReadFromHardWareEditorUI,
    RunMeasurementEditorUI,
    SaveDirToParentEditorUI,
    TimeoutEditorUI,
    UpdateSettingEditorUI,
    VisitReturnType,
    WaitUntilEditorUI,
    link_iteration_items,
    new_item,
)


class Sequencer(Measurement):
    name = "sequencer"

    def setup(self):

        self.item_list = ItemList()

        self.settings.New(
            "cycles",
            int,
            initial=1,
            description="number of times the sequence is executed",
        )
        self.settings.New("paused", bool, initial=False)
        self.settings.new_file(
            "recipe_folder", initial=str(Path.cwd()), is_dir=True
        ).add_listener(self.update_load_file_comboBox)
        self.seq_file = self.settings.new_file(
            "sequence_file",
            initial="",
            is_dir=False,
            file_filters=("Sequence (*.json)"),
        )

        self.seq_file.add_listener(self.on_load)

        self.iter_values = {}
        self.letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        self.current_item = None

    def setup_figure(self):
        # measurement controls and settings
        meas_layout = QtWidgets.QHBoxLayout()
        meas_layout.addWidget(self.settings.get_lq("cycles").new_default_widget())
        meas_layout.addWidget(self.new_start_stop_button())
        btn = self.settings.get_lq("paused").new_pushButton(
            texts=["pause", "resume"], colors=[None, "rgba( 0, 255, 0, 220)"]
        )
        meas_layout.addWidget(btn)

        # select file combobox
        self.load_file_comboBox = QtWidgets.QComboBox()
        self.load_file_comboBox.setToolTip("previously saved sequences")
        self.update_load_file_comboBox()
        self.load_file_comboBox.currentTextChanged.connect(
            self.on_load_file_comboBox_changed
        )

        # item list
        item_list_scroll_area = QtWidgets.QScrollArea()
        # item_list_scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        # item_list_scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        item_list_scroll_area.setWidgetResizable(True)
        item_list_scroll_area.setWidget(self.item_list.get_view())
        self.item_list.connect_item_double_clicked(self.item_double_clicked)

        # controls
        file_layout = QtWidgets.QHBoxLayout()
        self.remove_pushButton = QtWidgets.QPushButton("remove selected item")
        self.remove_pushButton.setToolTip("DEL")
        self.remove_pushButton.clicked.connect(self.on_remove_item)
        file_layout.addWidget(self.remove_pushButton)
        btn = QtWidgets.QPushButton("save ...")
        btn.clicked.connect(self.on_save)
        file_layout.addWidget(btn)
        btn = QtWidgets.QPushButton("load ...")
        btn.clicked.connect(self.seq_file.file_browser)
        file_layout.addWidget(btn)
        btn = QtWidgets.QPushButton("run selected item")
        btn.setToolTip("SPACEBAR")
        btn.clicked.connect(self.on_run_item_and_proceed)
        file_layout.addWidget(btn)
        self.show_editor_checkBox = QtWidgets.QCheckBox("show|hide editor")
        file_layout.addWidget(self.show_editor_checkBox)

        # Combine so far
        top_widget = QtWidgets.QWidget()
        self.layout = top_layout = QtWidgets.QVBoxLayout(top_widget)
        top_layout.addLayout(meas_layout)
        top_layout.addWidget(self.load_file_comboBox)
        top_layout.addWidget(item_list_scroll_area)
        top_layout.addLayout(file_layout)

        # Editors
        self.editor_widget = QtWidgets.QWidget()
        self.editor_layout = QtWidgets.QVBoxLayout(self.editor_widget)
        editor_scroll_area = QtWidgets.QScrollArea()
        # editor_scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        # editor_scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        editor_scroll_area.setWidgetResizable(True)
        editor_scroll_area.setWidget(self.editor_widget)
        self.show_editor_checkBox.stateChanged.connect(editor_scroll_area.setVisible)
        self.show_editor_checkBox.setChecked(True)

        paths = self.app.get_setting_paths()
        funcs = get_all_functions(self.app)
        self.editors: Dict[str, EditorBaseController] = {}
        self.add_editor(ReadFromHardWareEditorUI(self, paths))
        self.add_editor(UpdateSettingEditorUI(self, paths))
        self.add_editor(RunMeasurementEditorUI(self))
        self.add_editor(WaitUntilEditorUI(self, paths))
        self.add_editor(WaitUntilEditorUI(self, paths))
        self.add_editor(ExecFunctionEditorUI(self, funcs))
        self.add_editor(PauseEditorUI(self))
        self.add_editor(IterruptIfEditorUI(self, paths))
        self.add_editor(NewDirEditorUI(self))
        self.add_editor(SaveDirToParentEditorUI(self))
        self.add_editor(TimeoutEditorUI(self))
        self.add_iteration_editor(IterationsEditorUI(self, paths))

        for editor in self.editors.values():
            self.editor_layout.addWidget(editor.ui.group_box)

        self.editor_widget.keyPressEvent = self._editorKeyPressEvent
        self.item_list.get_view().keyReleaseEvent = self._keyReleaseEvent

        # try to load a file
        text = self.load_file_comboBox.currentText()
        if text in self.seq_fnames:
            self.seq_file.update_value(self.seq_fnames[text])

        self.ui = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self.ui.addWidget(top_widget)
        self.ui.addWidget(editor_scroll_area)
        self.ui.setStretchFactor(0, 1)
        self.ui.setStretchFactor(1, 1)

    def add_editor(self, editor_ui: EditorBaseUI):
        self.editors[editor_ui.item_type] = EditorBaseController(editor_ui, self)

    def add_iteration_editor(self, editor_ui: IterationsEditorUI):
        editor = InterationsEditorController(editor_ui, self)
        self.editors["start-iteration"] = editor
        self.editors["end-iteration"] = editor

    def _editorKeyPressEvent(self, event):
        if not event.modifiers() & QtCore.Qt.ControlModifier:
            return
        if not event.key() in (QtCore.Qt.Key_R, QtCore.Qt.Key_N):
            return
        fw = self.editor_widget.focusWidget()
        # find editor with focused widget
        for e in self.editors.values():
            gb = e.ui.group_box
            if fw in gb.findChildren(type(fw), fw.objectName()):
                if event.key() == QtCore.Qt.Key_R:
                    e.on_replace_func()
                if event.key() == QtCore.Qt.Key_N:
                    e.on_new_func()

    def _keyReleaseEvent(self, event):
        if event.key() == QtCore.Qt.Key_Delete:
            self.item_list.remove()
        if event.key() == QtCore.Qt.Key_Space:
            self.on_run_item_and_proceed()
        if event.key() in (QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return):
            item = self.item_list.get_current_item()
            self.item_double_clicked(item)

    def update_load_file_comboBox(self):
        root = Path(self.settings["recipe_folder"])
        fnames = list(root.rglob("*.json"))
        index0 = self.load_file_comboBox.currentIndex()
        self.load_file_comboBox.clear()
        self.seq_fnames = {}
        for fname in fnames:
            abbrev_fname = fname.relative_to(root)
            self.seq_fnames.update({str(abbrev_fname): fname})
        self.load_file_comboBox.addItems(list(self.seq_fnames.keys()))
        index = max(0, min(index0, self.load_file_comboBox.count() - 1))
        self.load_file_comboBox.setCurrentIndex(index)

    def insert_load_files(self, fname: Path):
        root = Path(self.settings["recipe_folder"])
        abbrev_fname = str(fname.relative_to(root))
        self.seq_fnames.update({abbrev_fname: fname})
        self.load_file_comboBox.insertItem(0, abbrev_fname)
        self.load_file_comboBox.setCurrentIndex(0)

    def on_load_file_comboBox_changed(self, abbrev_fname):
        self.load_file(self.seq_fnames[abbrev_fname])

    def next_iter_id(self) -> str:
        return self.letters[self.item_list.count_type("start-iteration")]

    def on_remove_item(self):
        self.item_list.remove(None)

    def on_save(self) -> str:
        fname, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.ui, caption="Save Sequence", filter="Sequence (*.json)"
        )
        if fname:
            self.save_to_file(fname)
        self.update_load_file_comboBox()
        return fname

    def save_to_file(self, fname):
        with open(fname, "w+") as f:
            f.write(json.dumps(self.item_list.as_dicts(), indent=1))

    def on_load(self) -> str:
        fname = Path(self.seq_file.val)
        if fname.exists() and not fname.is_dir():
            print(fname)
            self.load_file(fname)
            self.insert_load_files(fname)
        return fname

    def load_file(self, fname):
        self.item_list.clear()
        with open(fname, "r") as f:
            lines = json.loads(f.read())
        for kwargs in lines:
            item_type = kwargs.pop("type")
            item = new_item(self, item_type, **kwargs)
            self.item_list.add(item)
        success = link_iteration_items(self.item_list)
        if not success:
            print("invalid list")

    def on_run_item(self) -> Tuple[BaseItem, VisitReturnType]:
        item = self.item_list.get_current_item()
        if item.item_type == "measurement":
            print("WARNING running individually measurement not supported")
            return (item, None)
        return (item, self.item_list.get_current_item().visit())

    def on_run_item_and_proceed(self):
        item, next_item = self.on_run_item()
        if next_item is None:
            row = self.item_list.get_row(item)
            next_item = self.item_list.get_item(row + 1)
        self.item_list.set_current_item(next_item)

    def item_double_clicked(self, item: BaseItem):
        self.editors[item.item_type].ui.set_kwargs(**item.kwargs)

    def run(self):
        success = link_iteration_items(self.item_list)
        if not success:
            print("invalid list")

        N = self.item_list.count()
        for i in range(N):
            self.item_list.get_item(i).reset()

        for q in range(self.settings["cycles"]):
            # pct = int(100 * q / self.settings['cycles'])
            # self.set_progress(pct)
            if self.interrupt_measurement_called:
                break

            # go through list
            row = 0
            while row < self.item_list.count():
                while self.settings["paused"]:
                    if self.interrupt_measurement_called:
                        break
                    time.sleep(0.03)

                self.current_item = item = self.item_list.get_item(row)

                resp = item.visit()
                if resp is None:
                    # go to next item
                    row += 1
                else:
                    # jump to item returned
                    row = self.item_list.get_row(resp)

                if self.interrupt_measurement_called:
                    break

        self.current_item = None

    def update_display(self):
        for i in range(self.item_list.count()):
            item = self.item_list.get_item(i)
            item.setSelected(item == self.current_item)

    def shutdown(self):
        os.system("shutdown /s /f /t 1")

    def restart(self):
        os.system("restart /r /f /t 1")


def get_all_functions(app) -> List[str]:
    funcs = []

    def append_objs_callables(obj, from_app_path):
        for a in dir(obj):

            # exclude deprecated functions
            if isinstance(obj, Measurement) and a in ("gui",):
                continue

            try:  # Not sure why some python version seem to need this block
                if callable(getattr(obj, a)) and not a.startswith("__"):
                    funcs.append(f"{from_app_path}{obj.name}.{a}")
            except AttributeError as e:
                print(e)

    append_objs_callables(app, "")
    for m in app.measurements.values():
        append_objs_callables(m, "measurements.")
    for h in app.hardware.values():
        append_objs_callables(h, "hardware.")
    return funcs
