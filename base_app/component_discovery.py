"""Discover project components without executing their modules."""

import ast
import importlib
import importlib.util
import inspect
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ScopeFoundry import HardwareComponent, Measurement


@dataclass(frozen=True)
class ComponentSource:
    root: str
    module: str
    path: str
    class_name: str
    kind: str
    inferred_name: Optional[str] = field(default=None, compare=False)

    def as_dict(self):
        return {
            "module": self.module,
            "path": self.path,
            "class_name": self.class_name,
            "kind": self.kind,
        }

    @classmethod
    def from_dict(cls, value):
        if not isinstance(value, dict):
            raise ValueError("Component entry must be an object")
        keys = ("module", "path", "class_name", "kind")
        if any(not isinstance(value.get(key), str) or not value[key] for key in keys):
            raise ValueError("Component entry is missing a valid identity")
        if value["kind"] not in ("hardware", "measurement"):
            raise ValueError("Unknown component kind: " + value["kind"])
        root = value.get("root", "")
        if not isinstance(root, str):
            raise ValueError("Component root must be a string")
        return cls(root=root, **{key: value[key] for key in keys})


@dataclass(frozen=True)
class BuiltinComponentSource:
    module: str
    class_name: str
    kind: str
    name: Optional[str] = field(default=None, compare=False)

    def as_dict(self):
        return {
            "source": "builtin",
            "module": self.module,
            "class_name": self.class_name,
            "kind": self.kind,
        }

    @classmethod
    def from_dict(cls, value):
        if not isinstance(value, dict):
            raise ValueError("Built-in entry must be an object")
        module = value.get("module")
        class_name = value.get("class_name")
        kind = value.get("kind")
        name = value.get("name")
        if (
            not isinstance(module, str)
            or not module.startswith("ScopeFoundry.")
            or any(not part.isidentifier() for part in module.split("."))
            or not isinstance(class_name, str)
            or not class_name.isidentifier()
            or kind not in ("hardware", "measurement")
            or (name is not None and (not isinstance(name, str) or not name.strip()))
        ):
            raise ValueError(f"Invalid built-in component: {value!r}")
        return cls(module, class_name, kind, name)


def load_builtin_catalog(path=None):
    """Read the curated catalog without importing its components."""
    if path is None:
        path = Path(__file__).with_name("builtin_components.json")
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Built-in catalog must be a list")
    sources = []
    errors = []
    for index, entry in enumerate(data):
        try:
            source = BuiltinComponentSource.from_dict(entry)
            if source in sources:
                raise ValueError(f"Duplicate built-in component: {source.module}.{source.class_name}")
            sources.append(source)
        except ValueError as error:
            errors.append(f"Entry {index + 1}: {error}")
    return sources, errors


def component_source_from_dict(value):
    if isinstance(value, dict) and value.get("source") == "builtin":
        return BuiltinComponentSource.from_dict(value)
    if isinstance(value, dict) and "source" in value:
        raise ValueError(f"Unknown component source: {value['source']!r}")
    return ComponentSource.from_dict(value)


def _module_location(root, path, module_name=None):
    """Return the import root and module name for a source file."""
    root = Path(root).resolve()
    path = Path(path).resolve()
    relative = path.relative_to(root)
    parts = list(relative.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    package_root = root
    if (
        not (root / "__init__.py").is_file()
        and root.name.isidentifier()
        and (
            module_name == ".".join([root.name, *parts])
            if module_name is not None
            else any(
                Path(entry or os.getcwd()).resolve() == root.parent for entry in sys.path
            )
        )
    ):
        parts.insert(0, root.name)
        package_root = root.parent
    while (package_root / "__init__.py").is_file():
        parts.insert(0, package_root.name)
        package_root = package_root.parent
    if not parts or any(not part.isidentifier() for part in parts):
        raise ValueError(f"Cannot import {path} as a Python module")
    return package_root, ".".join(parts)


def _expression_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _expression_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else None
    if isinstance(node, ast.Subscript):
        return _expression_name(node.value)
    return None


def _literal_class_name(node):
    name = None
    for statement in node.body:
        if isinstance(statement, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "name"
            for target in statement.targets
        ):
            value = statement.value
        elif isinstance(statement, ast.AnnAssign) and (
            isinstance(statement.target, ast.Name) and statement.target.id == "name"
        ):
            if statement.value is None:
                continue
            value = statement.value
        else:
            continue
        name = value.value if isinstance(value, ast.Constant) and isinstance(value.value, str) else None
    return name


def discover_components(root):
    """Return (candidates, errors); no scanned module is imported."""
    root = Path(root).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"Not a directory: {root}")
    errors = []
    modules = {}
    classes = {}
    ignored = {"__pycache__", "build", "dist", "venv", "env", "node_modules", "manufacturer_examples"}
    for directory, dirs, files in os.walk(
        root, onerror=lambda error: errors.append(str(error))
    ):
        dirs[:] = sorted(
            name for name in dirs if not name.startswith(".") and name not in ignored
        )
        for filename in sorted(files):
            if not filename.endswith(".py"):
                continue
            path = Path(directory) / filename
            try:
                _, module = _module_location(root, path)
                tree = ast.parse(path.read_bytes(), filename=str(path))
            except (OSError, UnicodeError, SyntaxError, ValueError) as error:
                errors.append(f"{path}: {error}")
                continue
            if module in modules:
                errors.append(f"Duplicate module name {module}: {path}")
                continue
            package = module if filename == "__init__.py" else module.rpartition(".")[0]
            aliases = {}
            for node in tree.body:
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        aliases[alias.asname or alias.name.split(".")[0]] = (
                            alias.name if alias.asname else alias.name.split(".")[0]
                        )
                elif isinstance(node, ast.ImportFrom):
                    try:
                        imported = (
                            importlib.util.resolve_name(
                                "." * node.level + (node.module or ""), package
                            )
                            if node.level
                            else node.module
                        )
                    except (ImportError, ValueError) as error:
                        errors.append(f"{path}:{node.lineno}: {error}")
                        continue
                    for alias in node.names:
                        if alias.name != "*":
                            aliases[alias.asname or alias.name] = (
                                f"{imported}.{alias.name}"
                            )
            modules[module] = (path, aliases)
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    classes[f"{module}.{node.name}"] = (module, node)

    known = {
        "ScopeFoundry.HardwareComponent": "hardware",
        "ScopeFoundry.hardware.HardwareComponent": "hardware",
        "ScopeFoundry.Measurement": "measurement",
        "ScopeFoundry.measurement.Measurement": "measurement",
    }
    for module_name, module in list(sys.modules.items()):
        if not module_name.startswith("ScopeFoundry.") or module is None:
            continue
        for name, value in list(vars(module).items()):
            if not inspect.isclass(value):
                continue
            if issubclass(value, HardwareComponent):
                known[f"{module_name}.{name}"] = "hardware"
            elif issubclass(value, Measurement):
                known[f"{module_name}.{name}"] = "measurement"

    def expand(name, module):
        first, dot, rest = name.partition(".")
        alias = modules[module][1].get(first)
        if alias:
            return alias + (dot + rest if dot else "")
        local = f"{module}.{name}"
        return local if local in classes else name

    # Resolve package re-exports and inherited classes to a fixed point.
    def resolve(name):
        seen = set()
        while name not in seen:
            seen.add(name)
            module, dot, attribute = name.rpartition(".")
            if not dot or module not in modules or attribute not in modules[module][1]:
                break
            name = modules[module][1][attribute]
        return name

    pending = dict(classes)
    changed = True
    while changed:
        changed = False
        for qualified, (module, node) in list(pending.items()):
            kinds = {
                known[base]
                for expression in node.bases
                if (name := _expression_name(expression))
                and (base := resolve(expand(name, module))) in known
            }
            if len(kinds) == 1:
                known[qualified] = kinds.pop()
                del pending[qualified]
                changed = True
    candidates = [
        ComponentSource(
            str(root), module, str(modules[module][0]), node.name, known[qualified],
            inferred_name=_literal_class_name(node),
        )
        for qualified, (module, node) in classes.items()
        if qualified in known
        and qualified not in (
            "ScopeFoundry.hardware.HardwareComponent",
            "ScopeFoundry.measurement.Measurement",
        )
    ]
    return sorted(candidates, key=lambda item: (item.kind, item.module, item.class_name)), errors


def load_component_class(source):
    """Import and validate a selected source; importing runs module code."""
    if isinstance(source, BuiltinComponentSource):
        module = importlib.import_module(source.module)
        return _validate_component_class(source, module)
    path = Path(source.path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Component source no longer exists: {path}")
    parts = source.module.split(".")
    if not parts or any(not part.isidentifier() for part in parts):
        raise ValueError(f"Invalid module name: {source.module}")
    expected_parts = parts if path.name == "__init__.py" else parts[:-1]
    if path.name != "__init__.py" and path.stem != parts[-1]:
        raise ValueError(f"Module identity does not match source: {source.module}")
    import_root = path.parent
    for part in reversed(expected_parts):
        if import_root.name != part:
            raise ValueError(f"Module identity does not match source: {source.module}")
        import_root = import_root.parent
    if str(import_root) not in sys.path:
        sys.path.append(str(import_root))

    module = next(
        (
            loaded
            for loaded in list(sys.modules.values())
            if loaded is not None
            and getattr(loaded, "__file__", None)
            and Path(loaded.__file__).resolve() == path
            and getattr(loaded, "__name__", None) in (source.module, "__main__")
        ),
        None,
    )
    if module is None:
        importlib.invalidate_caches()
        spec = importlib.util.find_spec(source.module)
        if spec is None or not spec.origin or Path(spec.origin).resolve() != path:
            origin = spec.origin if spec is not None else None
            raise ImportError(
                f"{source.module} resolves to {origin}, not {path}; "
                "check for conflicting module names on the Python path"
            )
        module = importlib.import_module(source.module)
    module_file = getattr(module, "__file__", None)
    if not module_file or Path(module_file).resolve() != path:
        raise ImportError(
            f"{source.module} resolved to {module_file}, not {path}; "
            "check for conflicting module names on the Python path"
        )
    return _validate_component_class(source, module)


def _validate_component_class(source, module):
    component = getattr(module, source.class_name)
    base = HardwareComponent if source.kind == "hardware" else Measurement
    if (
        not inspect.isclass(component)
        or component is base
        or not issubclass(component, base)
        or component.__module__ != module.__name__
    ):
        raise TypeError(f"{source.class_name} is not a source-defined {base.__name__}")
    if inspect.isabstract(component):
        raise TypeError(f"{source.class_name} is abstract")
    return component
