import ast
from typing import Any, Dict, List, Tuple, TypedDict

from qtpy.QtWidgets import QLineEdit

from .helper_func import new_q_completer
from .editor_base_ui import EditorBaseUI
from .base_item import BaseItem
from ScopeFoundry.measurement import Measurement
from ScopeFoundry.hardware import HardwareComponent

ITEM_TYPE = "function"
MAX_ARGUMENT_STRING_LENGTH = 4096


class ExecFunctionKwargs(TypedDict):
    function: str
    args: str


def parse_arguments(argument_string: str) -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
    if len(argument_string) > MAX_ARGUMENT_STRING_LENGTH:
        raise ValueError(
            "Argument string exceeds the {} character limit".format(
                MAX_ARGUMENT_STRING_LENGTH
            )
        )

    call = ast.parse("_function({})".format(argument_string), mode="eval").body
    if (
        not isinstance(call, ast.Call)
        or not isinstance(call.func, ast.Name)
        or call.func.id != "_function"
    ):
        raise ValueError("Expected a function argument list")

    args = []
    for argument in call.args:
        if isinstance(argument, ast.Starred):
            args.extend(ast.literal_eval(argument.value))
        else:
            args.append(ast.literal_eval(argument))

    kwargs = {}
    for keyword in call.keywords:
        value = ast.literal_eval(keyword.value)
        if keyword.arg is None:
            if not isinstance(value, dict):
                raise TypeError("Keyword unpacking requires a dictionary literal")
            keyword_items = value.items()
        else:
            keyword_items = ((keyword.arg, value),)

        for key, value in keyword_items:
            if not isinstance(key, str):
                raise TypeError("Keyword names must be strings")
            if key in kwargs:
                raise TypeError(
                    "Got multiple values for keyword argument '{}'".format(key)
                )
            kwargs[key] = value

    return tuple(args), kwargs


def resolve_function(app, function_name: str, allowed_functions: List[str]):
    if function_name not in allowed_functions:
        raise ValueError("Function is not in the allowed function list")

    parts = function_name.split(".")
    if len(parts) == 2 and parts[0] == app.name:
        target = app
    elif len(parts) == 3 and parts[0] in ("measurements", "hardware"):
        objects = getattr(app, parts[0]).values()
        matches = [obj for obj in objects if obj.name == parts[1]]
        if len(matches) != 1:
            raise ValueError("Function path does not identify a unique object")
        target = matches[0]
    else:
        raise ValueError("Function path is not a supported application function")

    function = getattr(target, parts[-1])
    if not callable(function):
        raise TypeError("Selected application attribute is not callable")
    return function


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


class Function(BaseItem):
    item_type = ITEM_TYPE

    def visit(self) -> None:

        function = resolve_function(
            self.app, self.kwargs["function"], get_all_functions(self.app)
        )
        args, kwargs = parse_arguments(self.kwargs["args"])
        print(function(*args, **kwargs))


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
        self.function_le.setToolTip("allowed application function")
        self.args_le = QLineEdit()
        self.args_le.setToolTip(
            "literal function arguments (max {} characters)".format(
                MAX_ARGUMENT_STRING_LENGTH
            )
        )
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
