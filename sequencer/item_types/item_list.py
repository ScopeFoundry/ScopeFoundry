"""
Created on Sep 17, 2021

@author: Benedikt Ursprung
"""
from typing import Any, Dict, List, Union

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QListWidget

from .base_item import BaseItem


class ItemList:
    """implements the view, model and control of the list"""

    def __init__(self):
        self.view = QListWidget()
        self.view.setDefaultDropAction(Qt.MoveAction)
        self.view.setDragDropMode(QListWidget.DragDrop)

    def add(self, item: BaseItem, row: Union[int, None] = None):
        if row == None:
            row = self.get_current_row()
        self.view.insertItem(row + 1, item)
        self.view.setCurrentRow(row + 1)

    def remove(self, item: Union[BaseItem, None] = None):
        if item is not None:
            row = self.get_row(item)
        else:
            row = self.get_current_row()
        self.view.takeItem(row)
        del item

    def replace(self, new_item: BaseItem, old_item: Union[BaseItem, None] = None):
        if old_item is None:
            old_item = self.get_current_item()
        self.add(new_item, self.get_row(old_item))
        self.remove(old_item)

    def connect_item_double_clicked(self, fn):
        self.view.itemDoubleClicked.connect(fn)

    def get_view(self) -> QListWidget:
        return self.view

    def get_row(self, item: BaseItem) -> int:
        return self.view.row(item)

    def get_item(self, row: int) -> BaseItem:
        return self.view.item(row)  # type: ignore

    def get_current_row(self) -> int:
        return self.view.currentRow()

    def get_current_item(self) -> BaseItem:
        return self.view.currentItem()  # type: ignore

    def set_current_item(self, item: BaseItem):
        self.view.setCurrentItem(item)

    def clear(self):
        self.view.clear()

    def count_type(self, item_type="start-iteration"):
        counter = 0
        for i in range(self.view.count()):
            item = self.get_item(i)
            if item.item_type == item_type:
                counter += 1
        return counter

    def count(self) -> int:
        return self.view.count()

    def as_dicts(self) -> List[Dict[str, Any]]:
        l = []
        for i in range(self.view.count()):
            item = self.get_item(i)
            l.append({"type": item.item_type, **item.kwargs})
        return l
