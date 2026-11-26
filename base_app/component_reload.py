"""Recompile component modules and replace registered instances."""

import time
import ast
import inspect
import sys
from typing import Union
from contextlib import contextmanager
from pathlib import Path


from ScopeFoundry.component_construction import ComponentConstruction
from ScopeFoundry import HardwareComponent, Measurement


def _literal(node):
    try:
        ast.literal_eval(node)
        return True
    except (ValueError, TypeError):
        return False


def _reference(node):
    return isinstance(node, ast.Name) or (
        isinstance(node, ast.Attribute) and _reference(node.value)
    )


def _safe_definition(node):
    args = node.args.posonlyargs + node.args.args + node.args.kwonlyargs
    args += [arg for arg in (node.args.vararg, node.args.kwarg) if arg is not None]
    return (
        not node.decorator_list
        and all(_literal(value) for value in node.args.defaults)
        and all(value is None or _literal(value) for value in node.args.kw_defaults)
        and all(arg.annotation is None or _reference(arg.annotation) for arg in args)
        and (node.returns is None or _reference(node.returns))
    )


def _main_guard(node):
    test = node.test
    return (
        not node.orelse
        and isinstance(test, ast.Compare)
        and isinstance(test.left, ast.Name)
        and test.left.id == "__name__"
        and len(test.ops) == len(test.comparators) == 1
        and isinstance(test.ops[0], ast.Eq)
        and isinstance(test.comparators[0], ast.Constant)
        and test.comparators[0].value == "__main__"
    )


def _validate_main_body(body, filename, in_class=False):
    for node in body:
        if not in_class and isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if _safe_definition(node):
                continue
        elif isinstance(node, ast.ClassDef):
            if (
                not node.decorator_list
                and not node.keywords
                and all(_reference(base) for base in node.bases)
            ):
                _validate_main_body(node.body, filename, True)
                continue
        elif isinstance(node, ast.Pass) or (
            isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
        ):
            continue
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            annotation = node.annotation if isinstance(node, ast.AnnAssign) else None
            if (
                all(isinstance(target, ast.Name) for target in targets)
                and (annotation is None or _reference(annotation))
                and (node.value is None or _literal(node.value))
            ):
                continue
        elif not in_class and isinstance(node, ast.If) and _main_guard(node):
            continue
        raise ValueError(
            f"Cannot safely reload launch script {filename} at line {node.lineno}; "
            "move the component to an importable module."
        )


def recompile_class(
    component, expected_base
) -> Union[type[Measurement], type[HardwareComponent]]:
    cls = type(component)
    module = sys.modules.get(cls.__module__)
    filename = getattr(module, "__file__", None)
    if module is None or not filename or Path(filename).suffix != ".py":
        raise ImportError(f"No Python source for {cls.__module__}.{cls.__qualname__}")
    if "<locals>" in cls.__qualname__:
        raise ValueError("Components defined inside a function cannot be reloaded")
    source = Path(filename).read_bytes()
    is_main = cls.__module__ == "__main__" or getattr(
        module, "__scopefoundry_main_source__", False
    )
    if is_main:
        _validate_main_body(ast.parse(source, filename).body, filename)
    code = compile(source, filename, "exec")
    exec(code, module.__dict__)
    component_class = module
    for part in cls.__qualname__.split("."):
        component_class = getattr(component_class, part)
    if (
        not inspect.isclass(component_class)
        or not issubclass(component_class, expected_base)
        or component_class.__module__ != cls.__module__
    ):
        raise TypeError(f"{cls.__qualname__} is no longer a valid component class")
    return component_class


def stop(component, kind) -> bool:
    if kind == "hardware":
        component.settings["connected"] = False
        return not component.is_connected

    if component.is_measuring:
        component.activation.update_value(False)

    if not component.is_measuring():
        return True

    time.sleep(0.1)

    if not component.is_measuring():
        return True

    component.terminate()

    time.sleep(0.1)
    return not component.is_measuring()


def reload_component(app, component, kind):
    if type(component).__new__ is not ComponentConstruction.__new__:
        raise TypeError(
            f"{type(component).__name__} overrides __new__; reload is unsupported"
        )
    call = getattr(component, "_component_constructor_call", None)
    if call is None:
        raise TypeError(
            f"{type(component).__name__} did not preserve its constructor arguments"
        )
    args, kwargs = call

    base = HardwareComponent if kind == "hardware" else Measurement
    name = component.name
    try:
        replacement_class = recompile_class(component, base)
        replacement = replacement_class(*args, **kwargs)
    except Exception as e:
        raise RuntimeError(f"Failed to reload component {name}") from e
    
    add = app.add_hardware if kind == "hardware" else app.add_measurement
    remove = app.remove_hardware if kind == "hardware" else app.remove_measurement
    history = app.profile_manager.history
    snapshot = history.save_snapshot(f"Before reload {kind} {name}")
    stop(component, kind)
    remove(name)
    add(replacement)

    history.restore_snapshot(snapshot.name, restore_window_positions=True)
    app.log.info("Reloaded %s %s", kind, name)
    favorites = getattr(app, "favorites_widget", None)
    if favorites is not None:
        prefix = "hw" if kind == "hardware" else "mm"
        problems = favorites.refresh_component(f"{prefix}/{name}")

    return replacement
