from collections import OrderedDict
from typing import Callable

from qtpy import QtCore


class OperationsQObject(QtCore.QObject):

    added = QtCore.Signal(str)
    removed = QtCore.Signal(str)


class Operations(OrderedDict):

    def __init__(self, other=(), /, **kwds):
        super().__init__(other, **kwds)
        self.q_object = OperationsQObject()
        self._widgets_managers_ = []

    def add(self, name: str, value: Callable):
        if name in self.__dict__:
            return
        self[name] = value
        self.q_object.added.emit(name)

    def remove(self, name):
        if name not in self:
            return
        del self[name]
        self.q_object.removed.emit(name)
