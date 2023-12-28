from .item_list import ItemList
from .editor_base_ui import EditorBaseUI
from . import new_item


class EditorBaseController:
    def __init__(self, editor_ui: EditorBaseUI, measure) -> None:
        self.ui = editor_ui
        self.item_type = editor_ui.item_type
        self.description = editor_ui.description
        self.ui.set_on_new_func(self.on_new_func)
        self.ui.set_on_replace_func(self.on_replace_func)
        self.measure = measure
        self.item_list: ItemList = measure.item_list

    def _new_item(self):
        return new_item(self.measure, self.item_type, **self.ui.get_kwargs())

    def on_new_func(self):
        self.item_list.add(self._new_item())

    def on_replace_func(self):
        self.item_list.replace(self._new_item())
