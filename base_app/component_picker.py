"""UI and persistence for dynamically added microscope components."""

import json
import inspect
import os
import re
import stat
import tempfile
from pathlib import Path

from qtpy import QtCore, QtGui, QtWidgets

from .base_microscope_app import ComponentAlreadyExistsError
from .component_discovery import (
    BuiltinComponentSource,
    ComponentSource,
    component_source_from_dict,
    discover_components,
    load_builtin_catalog,
    load_component_class,
)


class ComponentPersistenceError(RuntimeError):
    pass


class ComponentArgumentsDialog(QtWidgets.QDialog):
    def __init__(self, parent, component_class, error, arguments):
        super().__init__(parent)
        self.component_class = component_class
        self.setWindowTitle("Component constructor arguments")
        self.resize(650, 400)
        layout = QtWidgets.QVBoxLayout(self)
        message = QtWidgets.QLabel(
            f"Adding {component_class.__name__} failed: {error}\n\n"
            f"Constructor: {component_class.__name__}{inspect.signature(component_class)}\n\n"
            'Enter each value as JSON (for example, "text", 42, true, or null). '
            "JSON-compatible defaults are prefilled; leave optional fields blank to use their defaults. "
            "ScopeFoundry supplies app automatically. "
            "Arguments may be saved in the .scopefoundry file in plain text; "
            "do not enter secrets."
        )
        message.setWordWrap(True)
        layout.addWidget(message)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        fields_widget = QtWidgets.QWidget()
        fields = QtWidgets.QFormLayout(fields_widget)
        self.named_inputs = {}
        self.prefilled_defaults = {}
        signature = inspect.signature(component_class)
        remaining_kwargs = dict(arguments.get("kwargs", {}))
        for parameter in signature.parameters.values():
            if parameter.name == "app" or parameter.kind not in (
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            ):
                continue
            editor = QtWidgets.QLineEdit()
            if parameter.name in remaining_kwargs:
                editor.setText(json.dumps(remaining_kwargs.pop(parameter.name)))
            if parameter.default is inspect.Parameter.empty:
                editor.setPlaceholderText("Required")
            else:
                editor.setPlaceholderText(f"Default: {parameter.default!r}")
                if parameter.name not in arguments.get("kwargs", {}):
                    try:
                        default = json.dumps(parameter.default, allow_nan=False)
                        decoded = json.loads(default)
                        if (
                            type(decoded) is type(parameter.default)
                            and decoded == parameter.default
                        ):
                            editor.setText(default)
                            self.prefilled_defaults[parameter.name] = default
                    except (TypeError, ValueError):
                        pass
            self.named_inputs[parameter.name] = editor
            fields.addRow(parameter.name, editor)
        if not self.named_inputs:
            fields.addRow(QtWidgets.QLabel("No named parameters available."))
        scroll.setWidget(fields_widget)
        layout.addWidget(scroll)
        layout.addWidget(
            QtWidgets.QLabel(
                "Advanced JSON: positional args and extra kwargs (optional)"
            )
        )
        self.input = QtWidgets.QPlainTextEdit()
        self.input.setPlainText(
            json.dumps(
                {"args": arguments.get("args", []), "kwargs": remaining_kwargs},
                indent=2,
            )
        )
        layout.addWidget(self.input)
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self):
        try:
            arguments = json.loads(self.input.toPlainText())
            validate_component_arguments(arguments)
            kwargs = arguments.setdefault("kwargs", {})
            for name, editor in self.named_inputs.items():
                value = editor.text().strip()
                if not value or value == self.prefilled_defaults.get(name):
                    continue
                if name in kwargs:
                    raise ValueError(
                        f"{name} is specified both as a named argument and in kwargs."
                    )
                try:
                    kwargs[name] = json.loads(value)
                except json.JSONDecodeError as error:
                    raise ValueError(f"Invalid JSON for {name}: {error.msg}") from error
            validate_component_arguments(arguments)
            bind_component_arguments(self.component_class, None, arguments)
        except (ValueError, TypeError) as error:
            QtWidgets.QMessageBox.warning(self, "Invalid arguments", str(error))
            return
        self.arguments = arguments
        super().accept()


def validate_component_arguments(arguments):
    if not isinstance(arguments, dict) or set(arguments) - {"args", "kwargs"}:
        raise ValueError('Enter an object with optional "args" and "kwargs" fields.')
    args = arguments.get("args", [])
    kwargs = arguments.get("kwargs", {})
    if not isinstance(args, list) or not isinstance(kwargs, dict):
        raise ValueError('"args" must be a list and "kwargs" must be an object.')
    if "app" in kwargs:
        raise ValueError("The app argument is supplied automatically.")
    try:
        json.dumps(arguments, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Arguments must be JSON-compatible: {error}") from error


def bind_component_arguments(component_class, app, arguments):
    validate_component_arguments(arguments)
    args = arguments.get("args", [])
    kwargs = arguments.get("kwargs", {})
    signature = inspect.signature(component_class)
    if args:
        parameters = list(signature.parameters.values())
        if (
            not parameters
            or parameters[0].name != "app"
            or parameters[0].kind
            not in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
        ):
            raise TypeError(
                "Positional arguments require app as the first positional parameter."
            )
        bound = signature.bind(app, *args, **kwargs)
    else:
        app_parameter = signature.parameters.get("app")
        if app_parameter and app_parameter.kind == inspect.Parameter.POSITIONAL_ONLY:
            bound = signature.bind(app, **kwargs)
        else:
            bound = signature.bind(app=app, **kwargs)
    return bound.args, bound.kwargs


class ComponentTable(QtWidgets.QTreeWidget):
    def __init__(self, editable_names=False):
        super().__init__()
        self.setColumnCount(5)
        self.setHeaderLabels(["Name", "Module", "Kind", "Class", "Path / details"])
        self.setRootIsDecorated(False)
        self.setAlternatingRowColors(True)
        self.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.header().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )
        self.header().setStretchLastSection(True)
        if editable_names:
            self.setItemDelegate(NameColumnDelegate(self))

    def add_row(self, values, data=None, editable=False):
        item = QtWidgets.QTreeWidgetItem([str(value) for value in values])
        item.setData(0, QtCore.Qt.ItemDataRole.UserRole, data)
        if editable:
            item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)
        self.addTopLevelItem(item)
        return item


class NameColumnDelegate(QtWidgets.QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        if index.column() != 0:
            return None
        return super().createEditor(parent, option, index)


def available_component_name(name, collection):
    while name in collection:
        match = re.fullmatch(r"(.*)_([0-9]+)", name)
        name = f"{match.group(1)}_{int(match.group(2)) + 1}" if match else f"{name}_2"
    return name


class ComponentPicker(QtWidgets.QDialog):
    def __init__(self, manager):
        super().__init__(manager.app.ui)
        self.manager = manager
        self.setWindowTitle("Add hardware or measurement")
        self.resize(750, 450)
        layout = QtWidgets.QVBoxLayout(self)
        self.tabs = QtWidgets.QTabWidget()
        self.builtin_page = QtWidgets.QWidget()
        builtin_layout = QtWidgets.QVBoxLayout(self.builtin_page)
        self.builtin_list = ComponentTable(editable_names=True)
        self.builtin_list.itemDoubleClicked.connect(self.on_add_double_clicked)
        builtin_layout.addWidget(self.builtin_list)
        logo = QtGui.QIcon(str(manager.app.icons_path / "scopefoundry_logo2B_1024.png"))
        self.tabs.addTab(self.builtin_page, logo, "Add ScopeFoundry built-in")

        self.folder_page = QtWidgets.QWidget()
        folder_layout = QtWidgets.QVBoxLayout(self.folder_page)
        root_layout = QtWidgets.QHBoxLayout()
        self.root = QtWidgets.QLineEdit(str(manager.root))
        browse = QtWidgets.QPushButton("Choose folder...")
        browse.clicked.connect(self.choose_folder)
        refresh = QtWidgets.QPushButton("Refresh")
        refresh.clicked.connect(self.refresh)
        root_layout.addWidget(self.root)
        root_layout.addWidget(browse)
        root_layout.addWidget(refresh)
        folder_layout.addLayout(root_layout)
        self.list = ComponentTable(editable_names=True)
        self.list.itemDoubleClicked.connect(self.on_add_double_clicked)
        folder_layout.addWidget(self.list)
        self.tabs.addTab(self.folder_page, "Add from folder")
        self.remove_page = SavedComponentsPanel(manager)
        self.remove_page.entries_changed.connect(self.filter_items)
        self.tabs.addTab(self.remove_page, "Edit")
        self.search = QtWidgets.QLineEdit()
        self.search.setPlaceholderText("Filter name, class, module, or component type")
        self.search.textChanged.connect(self.filter_items)
        self.add_hint = QtWidgets.QLabel(
            "Names already in use are incremented. Double-click a name to edit it."
        )
        layout.addWidget(self.tabs)
        layout.addWidget(self.add_hint)
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Close
        )
        self.add_button = buttons.addButton(
            "Add selected", QtWidgets.QDialogButtonBox.ButtonRole.ActionRole
        )
        self.initially_hidden_checkbox = QtWidgets.QCheckBox(
            "Hidden on startup (faster startup)"
        )
        self.initially_hidden_checkbox.setChecked(True)
        self.initially_hidden_checkbox.setToolTip(
            "On app startup, defer loading the measurement UI to save time. "
            "Measurements added now are shown."
        )
        self.hardware_combo = QtWidgets.QComboBox()
        self.hardware_combo.setToolTip(
            "On app startup, follow this hardware's connection; overrides initially hidden."
        )
        self.hardware_combo.currentIndexChanged.connect(self.update_measurement_options)
        options = QtWidgets.QHBoxLayout()
        options.addWidget(self.initially_hidden_checkbox)
        self.hardware_label = QtWidgets.QLabel("Unhide on connection:")
        options.addWidget(self.hardware_label)
        options.addWidget(self.hardware_combo)
        options.addWidget(buttons)
        self.measurement_options = (self.initially_hidden_checkbox, self.hardware_combo)
        self.add_button.clicked.connect(self.add_selected)
        self.tabs.currentChanged.connect(self.on_tab_changed)
        self.list.itemSelectionChanged.connect(self.update_add_button)
        self.builtin_list.itemSelectionChanged.connect(self.update_add_button)
        self.list.itemChanged.connect(self.filter_items)
        self.builtin_list.itemChanged.connect(self.filter_items)
        buttons.rejected.connect(self.reject)
        layout.addLayout(options)
        self.tabs.setCurrentWidget(self.folder_page)
        self.refresh_builtins()
        self.refresh()
        self.update_add_button()

    def on_add_double_clicked(self, item, column):
        if column != 0:
            self.add_selected()

    def on_tab_changed(self, _index):
        page = self.tabs.currentWidget()
        adding = page is not self.remove_page
        for widget in (
            self.add_hint,
            self.add_button,
            self.initially_hidden_checkbox,
            self.hardware_label,
            self.hardware_combo,
        ):
            widget.setVisible(adding)
        if page is self.remove_page:
            target = self.remove_page.list
            self.remove_page.reload()
        else:
            target = self.list if page is self.folder_page else self.builtin_list
            self.suggest_available_names()
        page.layout().insertWidget(page.layout().indexOf(target), self.search)
        self.search.show()
        self.refresh_hardware_choices()
        self.filter_items()
        self.update_add_button()

    def refresh_hardware_choices(self):
        selected = self.hardware_combo.currentData()
        blocker = QtCore.QSignalBlocker(self.hardware_combo)
        self.hardware_combo.clear()
        self.hardware_combo.addItem("None", None)
        for name in self.manager.app.hardware.keys():
            self.hardware_combo.addItem(name, name)
        index = self.hardware_combo.findData(selected)
        if index >= 0:
            self.hardware_combo.setCurrentIndex(index)
        del blocker
        self.update_measurement_options()

    def update_measurement_options(self, *_args):
        widget = self.tabs.currentWidget()
        selected_list = self.list if widget is self.folder_page else self.builtin_list
        item = selected_list.currentItem() if widget is not self.remove_page else None
        source = item.data(0, QtCore.Qt.ItemDataRole.UserRole) if item else None
        measurement = (
            isinstance(source, (ComponentSource, BuiltinComponentSource))
            and source.kind == "measurement"
            and not item.isHidden()
        )
        self.hardware_combo.setEnabled(measurement)
        self.initially_hidden_checkbox.setEnabled(
            measurement and self.hardware_combo.currentData() is None
        )

    def update_add_button(self):
        widget = self.tabs.currentWidget()
        selected_list = self.list if widget is self.folder_page else self.builtin_list
        item = selected_list.currentItem() if widget is not self.remove_page else None
        self.add_button.setEnabled(
            item is not None
            and not item.isHidden()
            and isinstance(
                item.data(0, QtCore.Qt.ItemDataRole.UserRole),
                (ComponentSource, BuiltinComponentSource),
            )
        )
        self.update_measurement_options()

    def refresh_builtins(self):
        self.builtin_list.clear()
        try:
            candidates, errors = load_builtin_catalog()
        except (OSError, ValueError) as error:
            self.manager.app.log.exception("Could not read built-in component catalog")
            QtWidgets.QMessageBox.warning(
                self, "Could not read built-in catalog", str(error)
            )
            return
        for candidate in candidates:
            original_name = candidate.name if candidate.name is not None else ""
            collection = (
                self.manager.app.hardware
                if candidate.kind == "hardware"
                else self.manager.app.measurements
            )
            name = (
                available_component_name(original_name, collection)
                if original_name
                else ""
            )
            item = self.builtin_list.add_row(
                [
                    name,
                    candidate.module,
                    candidate.kind.title(),
                    candidate.class_name,
                    "",
                ],
                candidate,
                editable=True,
            )
            item.setToolTip(
                0, "Catalog name; edit to override the constructor default."
            )
            item.setData(0, QtCore.Qt.ItemDataRole.UserRole + 1, original_name)
        if errors:
            self.manager.app.log.warning(
                "Invalid built-in catalog entries:\n%s", "\n".join(errors)
            )
            QtWidgets.QMessageBox.warning(
                self, "Invalid built-in catalog entries", "\n".join(errors)
            )
        self.filter_items()

    def choose_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Choose component folder", self.root.text()
        )
        if folder:
            self.root.setText(folder)
            self.refresh()

    def refresh(self):
        try:
            candidates, errors = discover_components(self.root.text())
        except (OSError, ValueError) as error:
            QtWidgets.QMessageBox.warning(self, "Discovery failed", str(error))
            return
        self.manager.root = Path(self.root.text()).expanduser().resolve()
        self.list.clear()
        for candidate in candidates:
            original_name = (
                candidate.inferred_name if candidate.inferred_name is not None else ""
            )
            collection = (
                self.manager.app.hardware
                if candidate.kind == "hardware"
                else self.manager.app.measurements
            )
            name = (
                available_component_name(original_name, collection)
                if original_name
                else ""
            )
            item = self.list.add_row(
                [
                    name,
                    candidate.module,
                    candidate.kind.title(),
                    candidate.class_name,
                    candidate.path,
                ],
                candidate,
                editable=True,
            )
            item.setData(0, QtCore.Qt.ItemDataRole.UserRole + 1, original_name)
            item.setToolTip(
                0, "Inferred from source; edit to override the constructor name."
            )
        for error in errors:
            item = self.list.add_row(["", "", "", "", error])
            item.setToolTip(4, error)
            for column in range(5):
                item.setForeground(column, QtGui.QColor("red"))
        self.filter_items()
        if errors:
            self.manager.app.log.warning(
                "Component discovery errors:\n%s", "\n".join(errors)
            )

    def suggest_available_names(self):
        for widget in (self.list, self.builtin_list):
            blocker = QtCore.QSignalBlocker(widget)
            for index in range(widget.topLevelItemCount()):
                item = widget.topLevelItem(index)
                source = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
                name = item.text(0)
                if (
                    isinstance(source, (ComponentSource, BuiltinComponentSource))
                    and name
                ):
                    collection = (
                        self.manager.app.hardware
                        if source.kind == "hardware"
                        else self.manager.app.measurements
                    )
                    item.setText(0, available_component_name(name, collection))
            del blocker

    def filter_items(self, *_args):
        text = self.search.text().casefold()
        for widget in (self.list, self.builtin_list, self.remove_page.list):
            for index in range(widget.topLevelItemCount()):
                item = widget.topLevelItem(index)
                item.setHidden(
                    not any(text in item.text(column).casefold() for column in range(5))
                )
        self.update_add_button()

    def add_selected(self, *_args):
        widget = self.tabs.currentWidget()
        selected_list = self.list if widget is self.folder_page else self.builtin_list
        item = selected_list.currentItem() if widget is not self.remove_page else None
        if (
            item is None
            or item.isHidden()
            or not isinstance(
                item.data(0, QtCore.Qt.ItemDataRole.UserRole),
                (ComponentSource, BuiltinComponentSource),
            )
        ):
            QtWidgets.QMessageBox.information(
                self, "Select a component", "Select a component to add."
            )
            return
        source = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        measurement_options = None
        if source.kind == "measurement":
            hardware_name = self.hardware_combo.currentData()
            measurement_options = {
                "initially_hidden": self.initially_hidden_checkbox.isChecked(),
                "unhide_on_connection": hardware_name,
            }
        arguments = {"args": [], "kwargs": {}}
        name = item.text(0).strip()
        if name != item.data(0, QtCore.Qt.ItemDataRole.UserRole + 1) and name:
            arguments["kwargs"]["name"] = name
        while True:
            try:
                component = self.manager.add(
                    source, arguments=arguments, measurement_options=measurement_options
                )
                break
            except ComponentPersistenceError as error:
                self.manager.app.log.exception("Could not save component")
                QtWidgets.QMessageBox.warning(
                    self, "Could not save component", str(error)
                )
                return
            except Exception as error:
                self.manager.app.log.exception("Could not add %s", source.class_name)
                try:
                    component_class = load_component_class(source)
                    inspect.signature(component_class)
                except Exception as inspect_error:
                    self.manager.app.log.exception(
                        "Could not inspect %s", source.class_name
                    )
                    QtWidgets.QMessageBox.warning(
                        self,
                        "Could not add component",
                        f"{error}\n\nCannot inspect the constructor: {inspect_error}",
                    )
                    return
                dialog = ComponentArgumentsDialog(
                    self, component_class, str(error), arguments
                )
                if dialog.exec_() != QtWidgets.QDialog.DialogCode.Accepted:
                    return
                arguments = dialog.arguments
        self.suggest_available_names()
        self.refresh_hardware_choices()
        self.filter_items()
        self.manager.app.show_status_bar_msg(
            f"Added {source.kind} {component.name}", 5000
        )


class SavedComponentsPanel(QtWidgets.QWidget):
    entries_changed = QtCore.Signal()

    def __init__(self, manager, entries=None, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.original_entries = []
        self.loaded = False
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(
            QtWidgets.QLabel(
                "Removing a component updates the saved list and removes it from the running app. "
                "Renaming a running component recreates it and resets its state."
            )
        )
        self.list = ComponentTable(editable_names=True)
        self.list.setColumnCount(7)
        self.list.setHeaderLabels(
            [
                "Name",
                "Module",
                "Kind",
                "Class",
                "Path / details",
                "Initially hidden",
                "Unhide on connection",
            ]
        )
        self.list.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.list.itemChanged.connect(self.rename_item)
        layout.addWidget(self.list)
        remove = QtWidgets.QPushButton("Remove selected")
        remove.clicked.connect(self.remove_selected)
        layout.addWidget(remove)
        if entries is not None:
            self.set_entries(entries)

    def set_entries(self, entries):
        self.original_entries = entries
        self.loaded = True
        blocker = QtCore.QSignalBlocker(self.list)
        self.list.clear()
        for entry in entries:
            if isinstance(entry, dict):
                name = self.manager.running_name(entry)
                arguments = entry.get("arguments")
                if name is None and isinstance(arguments, dict):
                    kwargs = arguments.get("kwargs")
                    if isinstance(kwargs, dict) and isinstance(kwargs.get("name"), str):
                        name = kwargs["name"]
                values = [
                    name if name is not None else "unavailable",
                    entry.get("module", "?"),
                    entry.get("kind", "?"),
                    entry.get("class_name", "?"),
                    (
                        entry.get("path", "")
                        if entry.get("source") != "builtin"
                        else "ScopeFoundry built-in"
                    ),
                ]
            else:
                values = [
                    "unavailable",
                    "",
                    "",
                    "",
                    json.dumps(entry, ensure_ascii=False),
                ]
            item = self.list.add_row(values, entry, editable=isinstance(entry, dict))
            for column in range(5):
                item.setToolTip(column, json.dumps(entry, ensure_ascii=False, indent=2))
            if isinstance(entry, dict) and entry.get("kind") == "measurement":
                options = entry.get("measurement_options", {})
                if not isinstance(options, dict):
                    continue
                checkbox = QtWidgets.QCheckBox()
                checkbox.setToolTip(
                    "Applies at startup unless a hardware connection is selected."
                )
                checkbox.setChecked(options.get("initially_hidden") is True)
                self.list.setItemWidget(item, 5, checkbox)
                combo = QtWidgets.QComboBox()
                combo.setToolTip(
                    "Startup setting; changes take effect after restarting the app."
                )
                combo.addItem("None", None)
                hardware_name = options.get("unhide_on_connection")
                for name in self.manager.app.hardware.keys():
                    combo.addItem(name, name)
                if hardware_name is not None and combo.findData(hardware_name) < 0:
                    combo.addItem(f"{hardware_name} (unavailable)", hardware_name)
                combo.setCurrentIndex(max(0, combo.findData(hardware_name)))
                self.list.setItemWidget(item, 6, combo)
                checkbox.setEnabled(combo.currentData() is None)
                checkbox.toggled.connect(
                    lambda _checked, row=item, cb=checkbox, hw=combo: self.change_measurement_options(
                        row, cb, hw
                    )
                )
                combo.currentIndexChanged.connect(
                    lambda _index, row=item, cb=checkbox, hw=combo: self.change_measurement_options(
                        row, cb, hw
                    )
                )
        del blocker
        self.entries_changed.emit()

    def change_measurement_options(self, item, checkbox, combo):
        entry = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        options = {
            "initially_hidden": checkbox.isChecked(),
            "unhide_on_connection": combo.currentData(),
        }
        try:
            self.manager.update_measurement_options(
                self.original_entries, entry, options
            )
        except Exception as error:
            self.manager.app.log.exception("Could not update measurement options")
            QtWidgets.QMessageBox.warning(
                self, "Could not update measurement options", str(error)
            )
        self.reload()

    def rename_item(self, item, column):
        if column != 0:
            return
        entry = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        old_name = self.manager.running_name(entry)
        if old_name is None and isinstance(entry, dict):
            arguments = entry.get("arguments")
            if isinstance(arguments, dict) and isinstance(
                arguments.get("kwargs"), dict
            ):
                old_name = arguments["kwargs"].get("name")
        name = item.text(0).strip()
        if name == old_name or (old_name is None and name == "unavailable"):
            return
        if self.manager.running_name(entry) is not None:
            answer = QtWidgets.QMessageBox.question(
                self,
                "Rename component",
                f"Renaming '{old_name}' recreates the component and resets its state. Continue?",
                QtWidgets.QMessageBox.StandardButton.Yes
                | QtWidgets.QMessageBox.StandardButton.No,
                QtWidgets.QMessageBox.StandardButton.No,
            )
            if answer != QtWidgets.QMessageBox.StandardButton.Yes:
                self.reload()
                return
        try:
            self.manager.rename_saved(self.original_entries, entry, name)
        except Exception as error:
            self.manager.app.log.exception("Could not rename saved component")
            QtWidgets.QMessageBox.warning(
                self, "Could not rename component", str(error)
            )
        self.reload()

    def reload(self):
        try:
            entries = self.manager._saved_entries(self.manager._read_config())
        except (OSError, ValueError) as error:
            self.list.clear()
            self.loaded = False
            self.manager.app.log.exception("Could not read saved components")
            QtWidgets.QMessageBox.warning(
                self, "Could not read saved components", str(error)
            )
            return
        self.set_entries(entries)

    def remove_selected(self):
        selected = [
            item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            for item in self.list.selectedItems()
            if not item.isHidden()
        ]
        if not selected:
            return
        try:
            self.manager.remove_saved(self.original_entries, selected)
        except Exception as error:
            self.manager.app.log.exception("Could not remove saved components")
            QtWidgets.QMessageBox.warning(
                self, "Could not remove components", str(error)
            )
        self.reload()


class SavedComponentsEditor(QtWidgets.QDialog):
    def __init__(self, manager, entries):
        super().__init__(manager.app.ui)
        self.setWindowTitle("Edit saved components")
        self.resize(750, 400)
        layout = QtWidgets.QVBoxLayout(self)
        self.panel = SavedComponentsPanel(manager, entries, self)
        layout.addWidget(self.panel)
        close = QtWidgets.QPushButton("Close")
        close.clicked.connect(self.accept)
        layout.addWidget(close)
        self.list = self.panel.list

    def remove_selected(self):
        self.panel.remove_selected()


class DynamicComponents:
    config_key = "dynamic_components"

    def __init__(self, app):
        self.app = app
        implementation_path = app.implementation_path
        self.root = next(
            (
                directory / "ScopeFoundryHW"
                for directory in (implementation_path, *implementation_path.parents)
                if (directory / "ScopeFoundryHW").is_dir()
            ),
            implementation_path,
        )
        self.added = {}
        self.unresolved = []
        self.order = []

    def show_picker(self):
        ComponentPicker(self).exec_()

    def show_saved_editor(self):
        try:
            entries = self._saved_entries(self._read_config())
        except (OSError, ValueError) as error:
            self.app.log.exception("Could not read saved components")
            QtWidgets.QMessageBox.warning(
                self.app.ui, "Could not read saved components", str(error)
            )
            return
        SavedComponentsEditor(self, entries).exec_()

    def _saved_entries(self, config):
        entries = config.get(self.config_key, [])
        if not isinstance(entries, list):
            raise ValueError(f"{self.config_key} must be a list")
        return entries

    def running_name(self, entry):
        for (kind, name), current in self.added.items():
            if current == entry:
                collection = (
                    self.app.hardware if kind == "hardware" else self.app.measurements
                )
                if name in collection:
                    return collection[name].name
        return None

    def update_measurement_options(self, original, entry, options):
        config = self._read_config()
        entries = self._saved_entries(config)
        if entries != original:
            raise ValueError(
                "Saved components changed elsewhere. Reopen the Edit tab and try again."
            )
        if not isinstance(entry, dict) or entry.get("kind") != "measurement":
            raise ValueError("Measurement options are only valid for measurements.")
        hardware_name = options["unhide_on_connection"]
        previous = entry.get("measurement_options", {})
        old_hardware_name = previous.get("unhide_on_connection")
        name = self.running_name(entry)
        if hardware_name != old_hardware_name and hardware_name is not None:
            if hardware_name not in self.app.hardware:
                raise ValueError(
                    f"Hardware '{hardware_name}' is not currently available."
                )
        updated = dict(entry, measurement_options=dict(options))
        revised = list(entries)
        revised[revised.index(entry)] = updated
        config[self.config_key] = revised
        self._save_config(config)
        if entry in self.order:
            self.order[self.order.index(entry)] = updated
        if entry in self.unresolved:
            self.unresolved[self.unresolved.index(entry)] = updated
        if name is not None:
            self.added[("measurement", name)] = updated

    def rename_saved(self, original, entry, name):
        if not name or name != name.strip():
            raise ValueError(
                "A component name must not be empty or have surrounding whitespace."
            )
        config = self._read_config()
        entries = self._saved_entries(config)
        if entries != original:
            raise ValueError(
                "Saved components changed elsewhere. Reopen the Edit tab and try again."
            )
        index = entries.index(entry)
        source = self._source_for_entry(entry)
        component_class = load_component_class(source)
        arguments = entry.get("arguments", {"args": [], "kwargs": {}})
        validate_component_arguments(arguments)
        args = list(arguments.get("args", []))
        kwargs = dict(arguments.get("kwargs", {}))
        signature = inspect.signature(component_class)
        parameters = list(signature.parameters.values())
        name_parameter = signature.parameters.get("name")
        if name_parameter and name_parameter.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        ):
            position = parameters.index(name_parameter) - 1
            if position >= 0 and position < len(args):
                args[position] = name
                kwargs.pop("name", None)
            elif name_parameter.kind == inspect.Parameter.POSITIONAL_ONLY:
                raise ValueError(
                    "This constructor requires the name as a positional argument."
                )
            else:
                kwargs["name"] = name
        else:
            kwargs["name"] = name
        new_arguments = {"args": args, "kwargs": kwargs}
        bind_component_arguments(component_class, self.app, new_arguments)
        updated = dict(entry, arguments=new_arguments)
        old_name = self.running_name(entry)
        if source.kind == "hardware":
            default_name = (
                source.inferred_name
                if isinstance(source, ComponentSource)
                else source.name
            )
            saved_name = (
                old_name or arguments.get("kwargs", {}).get("name") or default_name
            )
            if saved_name and any(
                isinstance(item, dict)
                and isinstance(item.get("measurement_options"), dict)
                and item["measurement_options"].get("unhide_on_connection")
                == saved_name
                for item in entries
            ):
                raise ValueError(
                    f"Remove measurements linked to hardware '{saved_name}' before renaming it."
                )
        collection = (
            self.app.hardware if source.kind == "hardware" else self.app.measurements
        )
        if name in collection and name != old_name:
            raise ComponentAlreadyExistsError(
                f"{source.kind.title()} '{name}' already exists."
            )
        if updated in entries and updated != entry:
            raise ComponentAlreadyExistsError(
                "This component is already in the saved list."
            )
        if old_name is None:
            entries[index] = updated
            config[self.config_key] = entries
            self._save_config(config)
            if entry in self.order:
                self.order[self.order.index(entry)] = updated
            if entry in self.unresolved:
                self.unresolved[self.unresolved.index(entry)] = updated
            return
        component = collection[old_name]
        if source.kind == "hardware" and component.is_connected:
            raise ValueError(f"Disconnect hardware '{old_name}' before renaming it.")
        if source.kind == "measurement" and component.is_measuring():
            raise ValueError(f"Stop measurement '{old_name}' before renaming it.")

        replacement = self.add(
            source,
            new_arguments,
            persist=False,
            measurement_options=entry.get("measurement_options"),
        )
        replacement_key = (source.kind, replacement.name)
        try:
            if replacement.name != name:
                raise ValueError(f"The constructor did not apply the name '{name}'.")
            latest = self._read_config()
            if self._saved_entries(latest) != original:
                raise ValueError("Saved components changed elsewhere during rename.")
            revised = list(original)
            revised[index] = updated
            latest[self.config_key] = revised
            self._save_config(latest)
        except Exception as error:
            try:
                self._remove_running(source.kind, replacement.name)
            except Exception as rollback_error:
                raise RuntimeError(
                    f"Rename failed ({error}); removing the replacement also failed ({rollback_error})."
                ) from error
            raise

        generated = self.added[replacement_key]
        self.added[replacement_key] = updated
        self.order[self.order.index(generated)] = updated
        try:
            self._remove_running(source.kind, old_name)
        except Exception as error:
            if old_name in collection:
                try:
                    latest = self._read_config()
                    if self._saved_entries(latest) != revised:
                        raise ValueError(
                            "Saved components changed elsewhere during rename."
                        )
                    latest[self.config_key] = original
                    self._save_config(latest)
                    self._remove_running(source.kind, replacement.name)
                except Exception as rollback_error:
                    raise RuntimeError(
                        f"Rename failed ({error}); rollback also failed ({rollback_error}). "
                        "Check the running components and saved configuration."
                    ) from error
            raise RuntimeError(
                f"Rename failed while removing '{old_name}': {error}."
            ) from error

    def _remove_running(self, kind, name):
        if kind == "hardware":
            self.app.remove_hardware(name)
        else:
            self.app.remove_measurement(name)

    def _save_config(self, config):
        path = self.app.microscope_config_path
        data = json.dumps(config, indent=2) + "\n"
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                file.write(data)
            if path.exists():
                os.chmod(temporary, stat.S_IMODE(path.stat().st_mode))
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def _entry_for_source(self, source, arguments):
        entry = source.as_dict()
        if isinstance(source, ComponentSource):
            base = self.app.implementation_path.resolve()
            path = Path(source.path).resolve()
            try:
                path.relative_to(base.parent)
            except ValueError:
                pass
            else:
                entry["path"] = os.path.relpath(path, base)
        if arguments.get("args") or arguments.get("kwargs"):
            entry["arguments"] = arguments
        return entry

    def _source_for_entry(self, entry):
        source = component_source_from_dict(entry)
        if isinstance(source, ComponentSource) and not Path(source.path).is_absolute():
            path = (self.app.implementation_path / source.path).resolve()
            source = ComponentSource(
                source.root, source.module, str(path), source.class_name, source.kind
            )
        return source

    def add(
        self,
        source,
        arguments=None,
        persist=True,
        measurement_options=None,
        *,
        restoring=False,
    ):
        component_class = load_component_class(source)
        arguments = arguments if arguments is not None else {"args": [], "kwargs": {}}
        args, kwargs = bind_component_arguments(component_class, self.app, arguments)
        if measurement_options is not None:
            if source.kind != "measurement" or not isinstance(
                measurement_options, dict
            ):
                raise ValueError("Measurement options are only valid for measurements.")
            if set(measurement_options) - {"initially_hidden", "unhide_on_connection"}:
                raise ValueError("Unknown measurement options.")
            initially_hidden = measurement_options.get("initially_hidden")
            hardware_name = measurement_options.get("unhide_on_connection")
            if initially_hidden is not None and not isinstance(initially_hidden, bool):
                raise ValueError("initially_hidden must be a boolean or null.")
            if hardware_name is not None and (
                not isinstance(hardware_name, str) or not hardware_name
            ):
                raise ValueError(
                    "unhide_on_connection must be a hardware name or null."
                )
            if hardware_name is not None and hardware_name not in self.app.hardware:
                raise ValueError(
                    f"Hardware '{hardware_name}' is not currently available."
                )
        try:
            config = self._read_config() if persist else None
            saved = self._saved_entries(config) if persist else None
        except (OSError, ValueError) as error:
            raise ComponentPersistenceError(
                f"Could not read the component configuration: {error}"
            ) from error
        entry = self._entry_for_source(source, arguments)
        if measurement_options is not None:
            entry["measurement_options"] = dict(measurement_options)
        if persist and entry in saved:
            raise ComponentAlreadyExistsError(
                f"{source.class_name} is already in the saved component list."
            )
        collection = (
            self.app.hardware if source.kind == "hardware" else self.app.measurements
        )
        bound = inspect.signature(component_class).bind(*args, **kwargs)
        expected_name = bound.arguments.get("name") or getattr(
            component_class, "name", component_class.__name__
        )
        if expected_name in collection:
            raise ComponentAlreadyExistsError(
                f"{source.kind.title()} '{expected_name}' already exists."
            )
        instance = component_class(*args, **kwargs)
        try:
            if source.kind == "hardware":
                self.app.add_hardware(instance)
            else:
                options = {"initially_hidden": False}
                if restoring and measurement_options is not None:
                    options["initially_hidden"] = initially_hidden
                    if hardware_name is not None:
                        options["unhide_on_connection"] = self.app.hardware[
                            hardware_name
                        ]
                self.app.add_measurement(instance, **options)
            instance.operations.set_shortcut_parent(self.app.ui)
            if persist:
                try:
                    config = self._read_config()
                    if self._saved_entries(config) != saved:
                        raise ValueError(
                            "Saved components changed elsewhere during addition."
                        )
                    config[self.config_key] = [*saved, entry]
                    self._save_config(config)
                except Exception as error:
                    raise ComponentPersistenceError(
                        f"Could not save the component configuration: {error}"
                    ) from error
        except Exception as error:
            if instance.name in collection and collection[instance.name] is instance:
                try:
                    if source.kind == "hardware":
                        self.app.remove_hardware(instance.name)
                    else:
                        self.app.remove_measurement(instance.name)
                except Exception as rollback_error:
                    self.app.log.exception(
                        "Could not roll back component %s", instance.name
                    )
                    raise ComponentPersistenceError(
                        f"Adding the component failed ({error}), and removing the partially "
                        f"added component also failed ({rollback_error})."
                    ) from error
            raise
        self.added[(source.kind, instance.name)] = entry
        self.order.append(entry)
        return instance

    def remove_saved(self, original, selected):
        config = self._read_config()
        entries = self._saved_entries(config)
        if entries != original:
            raise ValueError(
                "Saved components changed elsewhere. Reopen the Edit tab and try again."
            )
        remaining = list(entries)
        running = {}
        for entry in selected:
            remaining.remove(entry)
            for key, current in self.added.items():
                if current == entry:
                    collection = (
                        self.app.hardware
                        if key[0] == "hardware"
                        else self.app.measurements
                    )
                    if key[1] in collection:
                        component = collection[key[1]]
                        if key[0] == "measurement" and component.is_measuring():
                            raise ValueError(
                                f"Stop measurement '{key[1]}' before removing it."
                            )
                        running[id(entry)] = key
                    break
        for entry in selected:
            key = running.get(id(entry))
            if (
                key
                and key[0] == "hardware"
                and any(
                    isinstance(item, dict)
                    and isinstance(item.get("measurement_options"), dict)
                    and item["measurement_options"].get("unhide_on_connection")
                    == key[1]
                    for item in remaining
                )
            ):
                raise ValueError(
                    f"Remove measurements linked to hardware '{key[1]}' before removing it."
                )
        for entry in selected:
            config = self._read_config()
            if self._saved_entries(config) != entries:
                raise ValueError(
                    "Saved components changed elsewhere. Earlier removals remain applied."
                )
            previous = list(entries)
            entries.remove(entry)
            config[self.config_key] = entries
            try:
                self._save_config(config)
            except Exception as error:
                raise RuntimeError(
                    f"Could not save component removal ({error}). Earlier removals remain applied."
                ) from error
            key = running.get(id(entry))
            try:
                if key:
                    kind, name = key
                    if kind == "hardware":
                        self.app.remove_hardware(name)
                    else:
                        self.app.remove_measurement(name)
            except Exception as error:
                collection = (
                    self.app.hardware if kind == "hardware" else self.app.measurements
                )
                if name in collection:
                    try:
                        current = self._read_config()
                        if self._saved_entries(current) != entries:
                            raise ValueError(
                                "Saved components changed elsewhere during removal."
                            )
                        current[self.config_key] = previous
                        self._save_config(current)
                    except Exception as rollback_error:
                        self.app.log.exception("Could not restore saved component list")
                        raise RuntimeError(
                            f"Removal failed ({error}); restoring the saved list also failed "
                            f"({rollback_error}). Earlier removals remain applied."
                        ) from error
                else:
                    self.removed(kind, name)
                    if entry in self.unresolved:
                        self.unresolved.remove(entry)
                raise RuntimeError(
                    f"Removal failed ({error}). Earlier removals remain applied."
                ) from error
            if not key and entry in self.order:
                self.order.remove(entry)
            if entry in self.unresolved:
                self.unresolved.remove(entry)

    def removed(self, kind, name):
        source = self.added.pop((kind, name), None)
        if source is not None:
            self.order.remove(source)

    def _read_config(self):
        return self.app.configuration_handler.load_config()

    def restore(self):
        try:
            config = self._read_config()
            entries = self._saved_entries(config)
        except (OSError, ValueError) as error:
            self.app.log.exception("Could not read saved components")
            QtWidgets.QMessageBox.warning(
                self.app.ui, "Could not read saved components", str(error)
            )
            return
        errors = []
        for entry in entries:
            try:
                source = self._source_for_entry(entry)
                component_class = load_component_class(source)
                arguments = entry.get("arguments", {"args": [], "kwargs": {}})
                validate_component_arguments(arguments)
                args, kwargs = bind_component_arguments(
                    component_class, self.app, arguments
                )
                collection = (
                    self.app.hardware
                    if source.kind == "hardware"
                    else self.app.measurements
                )
                bound = inspect.signature(component_class).bind(*args, **kwargs)
                name = bound.arguments.get("name") or getattr(
                    component_class, "name", component_class.__name__
                )
                if name in collection and type(collection[name]) is component_class:
                    if "measurement_options" in entry:
                        raise ValueError(
                            f"Measurement '{name}' is already supplied by setup; "
                            "its saved measurement options cannot be applied."
                        )
                    self.app.log.info(
                        "Saved component %s is already supplied by setup", name
                    )
                    self.added[(source.kind, name)] = entry
                    self.order.append(entry)
                    continue
                self.add(
                    source,
                    arguments=arguments,
                    persist=False,
                    measurement_options=entry.get("measurement_options"),
                    restoring=True,
                )
                generated = self.order[-1]
                self.order[-1] = entry
                for key, current in list(self.added.items()):
                    if current is generated:
                        self.added[key] = entry
                        break
            except Exception as error:
                self.unresolved.append(entry)
                self.order.append(entry)
                self.app.log.exception("Could not restore component %r", entry)
                errors.append(f"{entry}: {error}")
        if errors:
            QtWidgets.QMessageBox.warning(
                self.app.ui,
                "Some components could not be restored",
                "\n".join(errors),
            )
