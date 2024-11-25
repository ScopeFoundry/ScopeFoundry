"""
Created on Sep 17, 2021

@author: Benedikt Ursprung
"""
import glob
import json
import os
import time
from builtins import getattr
from typing import List, Tuple, Dict

from qtpy.QtCore import Qt
from qtpy import QtWidgets


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
        self.settings.New(
            "cycles",
            int,
            initial=1,
            description="number of times the sequence is executed",
        )
        self.settings.New("paused", bool, initial=False)
        self.iter_values = {}
        self.letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        self.current_item = None

    def setup_figure(self):
        self.ui = QtWidgets.QWidget()
        self.layout = QtWidgets.QVBoxLayout(self.ui)

        # measurement controls and settings
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.settings.get_lq("cycles").new_default_widget())
        layout.addWidget(self.new_start_stop_button())
        btn = self.settings.get_lq("paused").new_pushButton(
            texts=["pause", "resume"], colors=[None, "rgba( 0, 255, 0, 220)"]
        )
        layout.addWidget(btn)
        self.layout.addLayout(layout)

        # select file combobox
        self.load_file_comboBox = QtWidgets.QComboBox()
        self.update_load_file_comboBox()
        self.load_file_comboBox.currentTextChanged.connect(
            self.on_load_file_comboBox_changed
        )
        self.layout.addWidget(self.load_file_comboBox)

        # item list
        self.item_list = ItemList()
        self.layout.addWidget(self.item_list.get_view())
        self.item_list.connect_item_double_clicked(self.item_double_clicked)

        # controls
        layout = QtWidgets.QHBoxLayout()
        self.layout.addLayout(layout)
        self.remove_pushButton = QtWidgets.QPushButton("remove selected item")
        self.remove_pushButton.setToolTip("DEL")
        self.remove_pushButton.clicked.connect(self.on_remove_item)
        layout.addWidget(self.remove_pushButton)
        btn = QtWidgets.QPushButton("save list ...")
        btn.clicked.connect(self.on_save)
        layout.addWidget(btn)
        btn = QtWidgets.QPushButton("load list ...")
        btn.clicked.connect(self.on_load)
        layout.addWidget(btn)
        btn = QtWidgets.QPushButton("run selected item")
        btn.setToolTip("SPACEBAR")
        btn.clicked.connect(self.on_run_item_and_proceed)
        layout.addWidget(btn)
        self.show_editor_checkBox = QtWidgets.QCheckBox("show|hide editor")
        layout.addWidget(self.show_editor_checkBox)

        # Editors
        self.editor_widget = QtWidgets.QWidget()
        self.editor_layout = QtWidgets.QVBoxLayout()
        self.editor_widget.setLayout(self.editor_layout)
        self.layout.addWidget(self.editor_widget)
        self.show_editor_checkBox.stateChanged.connect(self.editor_widget.setVisible)
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

    def add_editor(self, editor_ui: EditorBaseUI):
        self.editors[editor_ui.item_type] = EditorBaseController(editor_ui, self)

    def add_iteration_editor(self, editor_ui: IterationsEditorUI):
        editor = InterationsEditorController(editor_ui, self)
        self.editors["start-iteration"] = editor
        self.editors["end-iteration"] = editor

    def _editorKeyPressEvent(self, event):
        if not event.modifiers() & Qt.ControlModifier:
            return
        if not event.key() in (Qt.Key_R, Qt.Key_N):
            return
        fw = self.editor_widget.focusWidget()
        # find editor with focused widget
        for e in self.editors.values():
            gb = e.ui.group_box
            if fw in gb.findChildren(type(fw), fw.objectName()):
                if event.key() == Qt.Key_R:
                    e.on_replace_func()
                if event.key() == Qt.Key_N:
                    e.on_new_func()

    def _keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Delete:
            self.item_list.remove()
        if event.key() == Qt.Key_Space:
            self.on_run_item_and_proceed()
        if event.key() in (Qt.Key_Enter, Qt.Key_Return):
            item = self.item_list.get_current_item()
            self.item_double_clicked(item)

    def update_load_file_comboBox(self):
        fnames = glob.glob(glob.os.getcwd() + "\..\..\**/*.json", recursive=True)
        index0 = self.load_file_comboBox.currentIndex()
        self.load_file_comboBox.clear()
        self.seq_fnames = {}
        for fname in fnames:
            abbrev_fname = "\\".join(fname.split("\\")[-2:])
            self.seq_fnames.update({abbrev_fname: fname})
        self.load_file_comboBox.addItems(list(self.seq_fnames.keys()))
        self.load_file_comboBox.setCurrentIndex(index0)

    def on_load_file_comboBox_changed(self, fname):
        self.load_file(self.seq_fnames[fname])

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
        fname, _ = QtWidgets.QFileDialog.getOpenFileName(
            None, filter="Sequence (*.json)"
        )
        if fname:
            self.load_file(fname)
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
            if item == self.current_item:
                item.setBackground(Qt.green)
            else:
                item.setBackground(Qt.white)

    def shutdown(self):
        os.system("shutdown /s /f /t 1")

    def restart(self):
        os.system("restart /r /f /t 1")


def get_all_functions(app) -> List[str]:
    funcs = []

    def append_objs_callables(obj, from_app_path):
        for a in dir(obj):
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
