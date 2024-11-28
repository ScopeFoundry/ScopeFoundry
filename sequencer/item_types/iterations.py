from typing import TypedDict, Union

import numpy as np
from qtpy.QtWidgets import QComboBox, QDoubleSpinBox

from .editor_base_controller import EditorBaseController
from .editor_base_ui import EditorBaseUI
from .base_item import BaseItem
from .helper_func import new_q_completer


class StartIterationDict(TypedDict):
    values: list
    setting: str


class StartIterationItem(BaseItem):
    item_type = "start-iteration"

    def __init__(self, measure, **kwargs):
        self.iter_id = kwargs["iter_id"]
        self.values = kwargs["values"]
        self._name = kwargs["setting"]
        self.lq = measure.app.get_lq(kwargs["setting"])
        self.val = 0
        BaseItem.__init__(self, measure=measure, **kwargs)
        self.reset()
        self.end_item = None

    def _update_appearance(self, text=None):
        # text = BaseItem._update_appearance(self, text=text)
        t = f"START {self.iter_id}| for {self._name} in {self.values}:"
        self.setText(t)
        return t

    def visit(self) -> Union[None, BaseItem]:
        self.idx += 1
        if self.idx == len(self.values) - 1:
            # next time end-iteration is visited the loop breaks
            self.end_item.break_next = True
        self.lq.update_value(self.values[self.idx])
        self.update_text()
        self.measure.iter_values.update({self.iter_id: self.values[self.idx]})
        self.val = self.values[self.idx]

    def reset(self):
        self.idx = -1
        self.update_text()

    def set_end_iteration_item(self, end_item):
        self.end_item = end_item

    def update_text(self):
        text = self.text().split("  ")[0]
        pct = 100.0 * (self.idx + 1) / len(self.values)
        if self.idx >= 0:
            texts = [text, f"(current value: {self.values[self.idx]})", f"{pct: 1.0f}%"]
        else:
            texts = [text, f"{pct: 1.0f}%"]
        self.setText("  ".join(texts))


class EndIterationItem(BaseItem):
    item_type = "end-iteration"

    def __init__(self, measure, **kwargs):
        self.kwargs = kwargs
        self.iter_id = kwargs["iter_id"]
        self.values = kwargs["values"]
        self._name = kwargs["setting"]
        self.lq = measure.app.get_lq(kwargs["setting"])
        self.val = 0
        BaseItem.__init__(self, measure=measure, **kwargs)
        self.reset()
        self.start_item = None

    def _update_appearance(self, text=None):
        text = f"   END {self.iter_id}|"
        self.setText(text)
        return text

    def visit(self) -> Union[None, BaseItem]:
        self.update_text()
        if self.break_next:
            self.start_item.reset()
            self.reset()
            return None
        else:
            return self.start_item

    def reset(self):
        self.break_next = False
        self.update_text()

    def set_start_iteration_item(self, start_item: StartIterationItem):
        self.start_item = start_item
        self.iter_id = start_item.iter_id
        self._update_appearance()

    def update_text(self):
        try:
            pct = (self.start_item.idx + 1) / len(self.start_item.values) * 100
            self.setText(f"   END {self.iter_id}|  {pct: 1.0f}%")
        except AttributeError:
            pass


class IterationsEditorUI(EditorBaseUI):
    item_type = "start-iteration"
    description = "a setting is iterated over a range of values"

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
        self.start_dsb = QDoubleSpinBox()
        self.start_dsb.setToolTip("start value")
        self.layout.addWidget(self.start_dsb)
        self.stop_dsb = QDoubleSpinBox()
        self.stop_dsb.setToolTip("stop value")
        self.stop_dsb.setValue(10)
        self.layout.addWidget(self.stop_dsb)
        self.step_dsb = QDoubleSpinBox()
        self.step_dsb.setToolTip("step value")
        self.step_dsb.setValue(1)
        self.layout.addWidget(self.step_dsb)
        for sp in [self.start_dsb, self.step_dsb, self.stop_dsb]:
            sp.setMinimum(-1e6)
            sp.setMaximum(1e6)
            sp.setDecimals(6)

    def get_kwargs(self) -> StartIterationDict:
        path = self.setting_cb.currentText()
        start = self.start_dsb.value()
        stop = self.stop_dsb.value()
        step = self.step_dsb.value()
        values = np.arange(start, stop, step)
        return {"setting": path, "values": values}

    def set_kwargs(self, **kwargs):
        self.start_dsb.setValue(kwargs["values"][0])
        step = kwargs["values"][1] - kwargs["values"][0]
        self.step_dsb.setValue(step)
        self.stop_dsb.setValue(kwargs["values"][-1] + step)
        self.setting_cb.setCurrentText(kwargs["setting"])
        self.start_dsb.selectAll()
        self.start_dsb.setFocus()


class InterationsEditorController(EditorBaseController):
    def on_new_func(self):
        kwargs = self.ui.get_kwargs()
        kwargs["iter_id"] = self.measure.next_iter_id()
        self.item_list.add(StartIterationItem(self.measure, **kwargs))
        self.item_list.add(EndIterationItem(self.measure, **kwargs))
        link_iteration_items(self.item_list)

    def on_replace_func(self):
        cur_item = self.item_list.get_current_item()

        if isinstance(cur_item, StartIterationItem):
            start_item, end_item = cur_item, cur_item.end_item
        elif isinstance(cur_item, EndIterationItem):
            start_item, end_item = cur_item.start_item, cur_item
        else:
            return

        kwargs = self.ui.get_kwargs()
        kwargs["iter_id"] = cur_item.iter_id
        self.item_list.replace(StartIterationItem(self.measure, **kwargs), start_item)
        self.item_list.replace(EndIterationItem(self.measure, **kwargs), end_item)
        link_iteration_items(self.item_list)


def link_iteration_items(item_list) -> bool:
    """returns if the list is valid in terms iteration items"""
    start_iter_items: list[StartIterationItem] = []
    for i in range(item_list.count()):
        item = item_list.get_item(i)
        if isinstance(item, StartIterationItem):
            start_iter_items.append(item)
        if isinstance(item, EndIterationItem):
            s_item = start_iter_items.pop()
            item.set_start_iteration_item(s_item)
            s_item.set_end_iteration_item(item)

    if len(start_iter_items) != 0:
        return False
    return True
