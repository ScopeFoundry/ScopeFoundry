from typing import TypedDict

from qtpy.QtWidgets import QLineEdit

from .helper_func import new_q_completer
from .editor_base_ui import EditorBaseUI
from .base_item import BaseItem


ITEM_TYPE = "function"


class ExecFunctionKwargs(TypedDict):
    function: str
    args: str


class Function(BaseItem):
    item_type = ITEM_TYPE

    def visit(self) -> None:
        s = f"self.app.{self.kwargs['function']}({self.kwargs['args']})"
        print(eval(s))


class ExecFunctionEditorUI(EditorBaseUI):
    item_type = ITEM_TYPE
    description = "eval a function"

    def __init__(self, measure, all_functions) -> None:
        self.all_functions = all_functions
        super().__init__(measure)

    def setup_ui(self):
        self.function_le = QLineEdit()
        completer = new_q_completer(self.all_functions)
        self.function_le.setCompleter(completer)
        self.function_le.setToolTip("path to a function")
        self.args_le = QLineEdit()
        self.args_le.setToolTip("function arguments")
        self.layout.addWidget(self.function_le)
        self.layout.addWidget(self.args_le)

    def get_kwargs(self) -> ExecFunctionKwargs:
        f = self.function_le.text()
        args = self.args_le.text()
        return {"function": f, "args": args}

    def set_kwargs(self, **kwargs):
        self.function_le.setText(kwargs["function"])
        self.args_le.setText(kwargs["args"])
        self.args_le.selectAll()
