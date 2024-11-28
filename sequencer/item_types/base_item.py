from qtpy.QtWidgets import QListWidgetItem

from ScopeFoundry.measurement import Measurement

# from typing import Union
# from typing_extensions import Self
# do not want rely on typing_extension anymore.
# Reintroduce VisitReturnType when only python 3.10+ is supported and Self can be import from typing.

# VisitReturnType = Union[Self, None]  # return either a go-to Item or None if next


class BaseItem(QListWidgetItem):
    item_type = "item - overwrite me"

    def __init__(self, measure:Measurement, **kwargs):
        super().__init__()
        self.app = measure.app
        self.measure = measure
        self.kwargs = kwargs
        self._update_appearance()

    # def visit(self) -> VisitReturnType:
    def visit(self):
        raise NotImplementedError

    def _update_appearance(self, text=None) -> str:
        if text == None:
            kwargs_str = " ".join([f"{val}" for val in self.kwargs.values()])
            text = f"{self.item_type}: {kwargs_str}"
        self.setText(text)
        return text

    def reset(self) -> None:
        pass
