from typing import List
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QCompleter


def new_q_completer(l: List[str]) -> QCompleter:
    completer = QCompleter(l)
    completer.setCompletionMode(QCompleter.PopupCompletion)
    completer.setModelSorting(QCompleter.UnsortedModel)
    completer.setFilterMode(Qt.MatchContains)
    completer.setCaseSensitivity(Qt.CaseInsensitive)
    return completer
