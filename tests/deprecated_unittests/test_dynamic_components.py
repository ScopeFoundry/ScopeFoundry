import json
import os
import shutil
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import PropertyMock, patch

from qtpy import QtCore, QtGui, QtWidgets

from ScopeFoundry import BaseMicroscopeApp
from ScopeFoundry.base_app.base_microscope_app import ComponentAlreadyExistsError
from ScopeFoundry.base_app.component_discovery import (
    BuiltinComponentSource,
    ComponentSource,
    discover_components,
    load_builtin_catalog,
    load_component_class,
)
from ScopeFoundry.base_app.component_picker import (
    ComponentArgumentsDialog,
    ComponentPersistenceError,
    ComponentPicker,
    DynamicComponents,
    SavedComponentsEditor,
    available_component_name,
)
from ScopeFoundry.base_app.profile_manager import ProfileManager
from ScopeFoundry.tests.unittests.unittest_helpers import close_app_widgets


class DynamicComponentsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.package_name = "components_" + uuid.uuid4().hex
        self.project = self.directory / self.package_name
        self.project.mkdir()
        (self.project / "__init__.py").write_text(
            "from .base import BaseHardware\n", encoding="utf-8"
        )
        (self.project / "base.py").write_text(
            "from ScopeFoundry import HardwareComponent as HardwareBase\n"
            "class BaseHardware(HardwareBase):\n"
            "    pass\n",
            encoding="utf-8",
        )
        (self.project / "components.py").write_text(
            "from pathlib import Path\n"
            "from . import BaseHardware as Parent\n"
            "from ScopeFoundry import Measurement\n"
            f"Path({str(self.directory / 'imported')!r}).write_text('yes')\n"
            "class Device(Parent):\n"
            "    name = 'dynamic_device'\n"
            "    def setup(self):\n"
            "        self.add_operation('key', lambda: None, keyboard_shortcut='Ctrl+9')\n"
            "class Acquisition(Measurement):\n"
            "    name = 'dynamic_measurement'\n"
            "    def setup_figure(self):\n"
            "        from qtpy import QtWidgets\n"
            "        self.ui = QtWidgets.QWidget()\n"
            "class NeedsArgument(Measurement):\n"
            "    def __init__(self, app, required):\n"
            "        self.required = required\n"
            "        super().__init__(app)\n"
            "class BrokenFigure(Measurement):\n"
            "    name = 'broken_figure'\n"
            "    def setup_figure(self):\n"
            "        raise RuntimeError('figure failed')\n",
            encoding="utf-8",
        )
        self.addCleanup(self.cleanup_modules)
        warning = patch.object(QtWidgets.QMessageBox, "warning")
        warning.start()
        self.addCleanup(warning.stop)

    def cleanup_modules(self):
        for name in list(sys.modules):
            if name == self.package_name or name.startswith(self.package_name + "."):
                del sys.modules[name]
        import_root = str(self.directory.resolve())
        if import_root in sys.path:
            sys.path.remove(import_root)

    def sources(self):
        candidates, errors = discover_components(self.project)
        self.assertEqual(errors, [])
        return {source.class_name: source for source in candidates}

    def make_app(self, mdi=True, profile_callback=None):
        implementation = patch(
            "ScopeFoundry.base_app.base_microscope_app.get_child_path",
            return_value=self.directory,
        )
        implementation.start()
        self.addCleanup(implementation.stop)
        startup = patch.object(
            ProfileManager,
            "initialize_startup_profile",
            profile_callback or (lambda _self: None),
        )
        startup.start()
        self.addCleanup(startup.stop)

        class App(BaseMicroscopeApp):
            name = "dynamic-test"
            enable_ipynb_analysis = False

        App.mdi = mdi
        app = App([])
        self.addCleanup(close_app_widgets, app)
        return app

    def test_static_discovery_alias_inheritance_and_no_import(self):
        sources = self.sources()
        self.assertEqual(
            set(sources),
            {"BaseHardware", "Device", "Acquisition", "NeedsArgument", "BrokenFigure"},
        )
        self.assertEqual(sources["Device"].kind, "hardware")
        self.assertEqual(sources["Acquisition"].kind, "measurement")
        self.assertEqual(sources["Device"].inferred_name, "dynamic_device")
        self.assertIsNone(sources["NeedsArgument"].inferred_name)
        self.assertFalse((self.directory / "imported").exists())
        self.assertNotIn(self.package_name, sys.modules)
        cls = load_component_class(sources["Device"])
        self.assertEqual(cls.__name__, "Device")
        self.assertTrue((self.directory / "imported").exists())
        self.assertEqual(
            load_component_class(sources["NeedsArgument"]).__name__, "NeedsArgument"
        )

    def test_default_component_folder_uses_nearest_hardware_directory(self):
        implementation = self.directory / "parent" / "app"
        implementation.mkdir(parents=True)
        app = type("App", (), {"implementation_path": implementation})()
        with patch.object(Path, "is_dir", return_value=False):
            self.assertEqual(DynamicComponents(app).root, implementation)
        parent_hw = implementation.parent / "ScopeFoundryHW"
        parent_hw.mkdir()
        self.assertEqual(DynamicComponents(app).root, parent_hw)
        local_hw = implementation / "ScopeFoundryHW"
        local_hw.mkdir()
        self.assertEqual(DynamicComponents(app).root, local_hw)

    def test_discovery_infers_only_literal_class_names(self):
        (self.project / "names.py").write_text(
            "from ScopeFoundry import HardwareComponent\n"
            "class Literal(HardwareComponent):\n"
            "    name: str = 'literal_name'\n"
            "class Computed(HardwareComponent):\n"
            "    name = 'prefix_' + 'suffix'\n"
            "class Reassigned(HardwareComponent):\n"
            "    name = 'old'\n"
            "    name = make_name()\n"
            "class Implicit(HardwareComponent):\n"
            "    pass\n",
            encoding="utf-8",
        )
        sources = self.sources()
        self.assertEqual(sources["Literal"].inferred_name, "literal_name")
        for name in ("Computed", "Reassigned", "Implicit"):
            self.assertIsNone(sources[name].inferred_name)
        self.assertNotIn("inferred_name", sources["Literal"].as_dict())
        self.assertNotIn(self.package_name, sys.modules)

    def test_scan_errors_and_invalid_class_are_reported(self):
        (self.project / "broken.py").write_text("class Broken(\n", encoding="utf-8")
        candidates, errors = discover_components(self.project)
        self.assertTrue(any("broken.py" in error for error in errors))
        source = next(item for item in candidates if item.class_name == "Device")
        invalid = ComponentSource(
            source.root, source.module, source.path, "Path", source.kind
        )
        with self.assertRaises(TypeError):
            load_component_class(invalid)

    def test_constructor_arguments_retry_and_restore(self):
        source = self.sources()["NeedsArgument"]
        app = self.make_app()
        picker = ComponentPicker(app.dynamic_components)
        self.addCleanup(picker.deleteLater)
        picker.root.setText(str(self.project))
        picker.refresh()
        for index in range(picker.list.topLevelItemCount()):
            item = picker.list.topLevelItem(index)
            candidate = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            if candidate and candidate.class_name == "NeedsArgument":
                picker.list.setCurrentItem(item)
                break
        else:
            self.fail("Component not found")

        def provide_arguments(dialog):
            dialog.named_inputs["required"].setText('"chosen"')
            dialog.accept()
            return dialog.result()

        with patch.object(
            ComponentArgumentsDialog,
            "exec_",
            autospec=True,
            side_effect=provide_arguments,
        ):
            picker.add_selected()
        self.assertEqual(app.measurements["NeedsArgument"].required, "chosen")
        entry = json.loads(app.microscope_config_path.read_text())[
            "dynamic_components"
        ][0]
        self.assertEqual(
            entry["arguments"], {"args": [], "kwargs": {"required": "chosen"}}
        )
        restored = self.make_app()
        self.assertEqual(restored.measurements["NeedsArgument"].required, "chosen")

    def test_picker_measurement_options_are_saved_and_restored(self):
        sources = self.sources()
        app = self.make_app()
        device = app.dynamic_components.add(sources["Device"])
        picker = ComponentPicker(app.dynamic_components)
        self.addCleanup(picker.deleteLater)
        picker.root.setText(str(self.project))
        picker.refresh()
        item = next(
            picker.list.topLevelItem(i)
            for i in range(picker.list.topLevelItemCount())
            if picker.list.topLevelItem(i).data(0, QtCore.Qt.ItemDataRole.UserRole)
            == sources["Acquisition"]
        )
        picker.list.setCurrentItem(item)
        self.assertTrue(picker.initially_hidden_checkbox.isEnabled())
        picker.initially_hidden_checkbox.setChecked(True)
        picker.hardware_combo.setCurrentIndex(
            picker.hardware_combo.findData(device.name)
        )
        self.assertFalse(picker.initially_hidden_checkbox.isEnabled())
        with patch.object(app, "add_measurement", wraps=app.add_measurement) as add:
            picker.add_selected()
        self.assertNotIn("unhide_on_connection", add.call_args.kwargs)
        self.assertFalse(add.call_args.kwargs["initially_hidden"])
        measurement = app.measurements["dynamic_measurement"]
        self.assertFalse(measurement.settings["hidden"])
        device.connected.updated_value[bool].emit(True)
        self.assertFalse(measurement.settings["hidden"])
        self.assertFalse(device.connected.val)
        device.connected.updated_value[bool].emit(False)
        self.assertFalse(measurement.settings["hidden"])
        saved = json.loads(app.microscope_config_path.read_text())["dynamic_components"]
        self.assertEqual(
            saved[1]["measurement_options"],
            {
                "initially_hidden": True,
                "unhide_on_connection": device.name,
            },
        )
        restored = self.make_app()
        restored_measurement = restored.measurements["dynamic_measurement"]
        restored_device = restored.hardware[device.name]
        self.assertTrue(restored_measurement.settings["hidden"])
        restored_device.connected.updated_value[bool].emit(True)
        self.assertFalse(restored_measurement.settings["hidden"])
        restored.remove_measurement(restored_measurement.name)
        restored_device.connected.updated_value[bool].emit(False)

    def test_picker_initially_hidden_without_hardware(self):
        source = self.sources()["Acquisition"]
        app = self.make_app()
        picker = ComponentPicker(app.dynamic_components)
        self.addCleanup(picker.deleteLater)
        picker.root.setText(str(self.project))
        picker.refresh()
        item = next(
            picker.list.topLevelItem(i)
            for i in range(picker.list.topLevelItemCount())
            if picker.list.topLevelItem(i).data(0, QtCore.Qt.ItemDataRole.UserRole)
            == source
        )
        picker.list.setCurrentItem(item)
        self.assertTrue(picker.initially_hidden_checkbox.isChecked())
        picker.add_selected()
        self.assertFalse(app.measurements["dynamic_measurement"].settings["hidden"])
        self.assertIn("dynamic_measurement", app._loaded_measure_uis)
        entry = json.loads(app.microscope_config_path.read_text())[
            "dynamic_components"
        ][0]
        self.assertTrue(entry["measurement_options"]["initially_hidden"])
        restored = self.make_app()
        self.assertTrue(restored.measurements["dynamic_measurement"].settings["hidden"])

    def test_picker_search_is_above_each_list(self):
        app = self.make_app()
        picker = ComponentPicker(app.dynamic_components)
        self.addCleanup(picker.deleteLater)
        picker.search.setText("device")
        for page, table in (
            (picker.folder_page, picker.list),
            (picker.builtin_page, picker.builtin_list),
            (picker.remove_page, picker.remove_page.list),
        ):
            picker.tabs.setCurrentWidget(page)
            self.assertEqual(
                page.layout().indexOf(picker.search) + 1, page.layout().indexOf(table)
            )
            self.assertEqual(picker.search.text(), "device")

    def test_edit_tab_options_apply_on_restart(self):
        sources = self.sources()
        app = self.make_app()
        device = app.dynamic_components.add(sources["Device"])
        measurement = app.dynamic_components.add(
            sources["Acquisition"],
            measurement_options={
                "initially_hidden": False,
                "unhide_on_connection": None,
            },
        )
        picker = ComponentPicker(app.dynamic_components)
        self.addCleanup(picker.deleteLater)
        picker.show()
        picker.tabs.setCurrentWidget(picker.remove_page)
        self.assertTrue(picker.add_button.isHidden())
        self.assertTrue(picker.initially_hidden_checkbox.isHidden())
        self.assertTrue(picker.hardware_combo.isHidden())
        self.assertFalse(picker.remove_page.list.isHidden())
        item = picker.remove_page.list.topLevelItem(1)
        checkbox = picker.remove_page.list.itemWidget(item, 5)
        checkbox.setChecked(True)
        entry = json.loads(app.microscope_config_path.read_text())[
            "dynamic_components"
        ][1]
        self.assertTrue(entry["measurement_options"]["initially_hidden"])
        self.assertFalse(measurement.settings["hidden"])
        item = picker.remove_page.list.topLevelItem(1)
        combo = picker.remove_page.list.itemWidget(item, 6)
        combo.setCurrentIndex(combo.findData(device.name))
        entry = json.loads(app.microscope_config_path.read_text())[
            "dynamic_components"
        ][1]
        self.assertEqual(
            entry["measurement_options"]["unhide_on_connection"], device.name
        )
        self.assertFalse(measurement.settings["hidden"])
        device.connected.updated_value[bool].emit(True)
        self.assertFalse(measurement.settings["hidden"])
        restored_with_link = self.make_app()
        linked_measurement = restored_with_link.measurements[measurement.name]
        linked_device = restored_with_link.hardware[device.name]
        self.assertTrue(linked_measurement.settings["hidden"])
        linked_device.connected.updated_value[bool].emit(True)
        self.assertFalse(linked_measurement.settings["hidden"])
        item = picker.remove_page.list.topLevelItem(1)
        combo = picker.remove_page.list.itemWidget(item, 6)
        combo.setCurrentIndex(0)
        linked_device.connected.updated_value[bool].emit(False)
        self.assertTrue(linked_measurement.settings["hidden"])
        device.connected.updated_value[bool].emit(False)
        self.assertFalse(measurement.settings["hidden"])
        restored = self.make_app()
        self.assertTrue(restored.measurements[measurement.name].settings["hidden"])
        picker.tabs.setCurrentWidget(picker.folder_page)
        self.assertFalse(picker.add_button.isHidden())

    def test_edit_options_save_failure_reverts_widgets(self):
        app = self.make_app()
        app.dynamic_components.add(
            self.sources()["Acquisition"],
            measurement_options={
                "initially_hidden": False,
                "unhide_on_connection": None,
            },
        )
        picker = ComponentPicker(app.dynamic_components)
        self.addCleanup(picker.deleteLater)
        picker.tabs.setCurrentWidget(picker.remove_page)
        item = picker.remove_page.list.topLevelItem(0)
        checkbox = picker.remove_page.list.itemWidget(item, 5)
        with patch.object(
            app.dynamic_components, "_save_config", side_effect=OSError("disk full")
        ):
            checkbox.setChecked(True)
        item = picker.remove_page.list.topLevelItem(0)
        self.assertFalse(picker.remove_page.list.itemWidget(item, 5).isChecked())
        self.assertFalse(
            json.loads(app.microscope_config_path.read_text())["dynamic_components"][0][
                "measurement_options"
            ]["initially_hidden"]
        )

    def test_missing_linked_hardware_is_reported_on_restore(self):
        source = self.sources()["Acquisition"]
        entry = source.as_dict()
        entry["measurement_options"] = {
            "initially_hidden": False,
            "unhide_on_connection": "missing_device",
        }
        config_path = self.directory / "dynamic-test.scopefoundry"
        config_path.write_text(json.dumps({"dynamic_components": [entry]}))
        app = self.make_app()
        self.assertNotIn("dynamic_measurement", app.measurements)
        self.assertEqual(app.dynamic_components.unresolved, [entry])
        QtWidgets.QMessageBox.warning.assert_called()

    def test_linked_measurement_rename_and_hardware_removal(self):
        sources = self.sources()
        app = self.make_app()
        app.dynamic_components.add(sources["Device"])
        app.dynamic_components.add(
            sources["Acquisition"],
            measurement_options={
                "initially_hidden": False,
                "unhide_on_connection": "dynamic_device",
            },
        )
        entries = json.loads(app.microscope_config_path.read_text())[
            "dynamic_components"
        ]
        with self.assertRaisesRegex(ValueError, "linked"):
            app.dynamic_components.remove_saved(entries, [entries[0]])
        with self.assertRaisesRegex(ValueError, "linked"):
            app.dynamic_components.rename_saved(entries, entries[0], "renamed_device")
        app.dynamic_components.rename_saved(entries, entries[1], "renamed_measurement")
        restored = self.make_app()
        self.assertTrue(restored.measurements["renamed_measurement"].settings["hidden"])
        restored.hardware["dynamic_device"].connected.updated_value[bool].emit(True)
        self.assertFalse(
            restored.measurements["renamed_measurement"].settings["hidden"]
        )

    def test_existing_saved_component_can_be_added_again_with_a_new_name(self):
        source = self.sources()["Device"]
        app = self.make_app()
        original = app.dynamic_components.add(source)
        picker = ComponentPicker(app.dynamic_components)
        self.addCleanup(picker.deleteLater)
        picker.root.setText(str(self.project))
        picker.refresh()
        item = next(
            picker.list.topLevelItem(i)
            for i in range(picker.list.topLevelItemCount())
            if picker.list.topLevelItem(i).data(0, QtCore.Qt.ItemDataRole.UserRole)
            == source
        )
        self.assertEqual(item.text(0), "dynamic_device_2")
        item.setText(0, "dynamic_device")
        picker.list.setCurrentItem(item)

        def provide_name(dialog):
            dialog.named_inputs["name"].setText('"second_device"')
            dialog.accept()
            return dialog.result()

        with patch.object(
            ComponentArgumentsDialog, "exec_", autospec=True, side_effect=provide_name
        ) as dialog:
            picker.add_selected()
            dialog.assert_called_once()
        self.assertIs(app.hardware["dynamic_device"], original)
        self.assertIn("second_device", app.hardware)
        entries = json.loads(app.microscope_config_path.read_text())[
            "dynamic_components"
        ]
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[1]["arguments"]["kwargs"]["name"], "second_device")
        picker.tabs.setCurrentWidget(picker.remove_page)
        self.assertEqual(
            "dynamic_device", picker.remove_page.list.topLevelItem(0).text(0)
        )
        self.assertEqual(
            "second_device", picker.remove_page.list.topLevelItem(1).text(0)
        )
        picker.search.setText("second_device")
        self.assertTrue(picker.remove_page.list.topLevelItem(0).isHidden())
        self.assertFalse(picker.remove_page.list.topLevelItem(1).isHidden())
        restored = self.make_app()
        self.assertIn("dynamic_device", restored.hardware)
        self.assertIn("second_device", restored.hardware)
        restored.dynamic_components.remove_saved(entries, [entries[1]])
        self.assertIn("dynamic_device", restored.hardware)
        self.assertNotIn("second_device", restored.hardware)
        self.assertEqual(
            json.loads(app.microscope_config_path.read_text())["dynamic_components"],
            entries[:1],
        )

    def test_existing_setup_component_can_be_added_with_a_new_name(self):
        source = self.sources()["Acquisition"]
        app = self.make_app()
        original = load_component_class(source)(app=app)
        app.add_measurement(original)
        picker = ComponentPicker(app.dynamic_components)
        self.addCleanup(picker.deleteLater)
        picker.root.setText(str(self.project))
        picker.refresh()
        item = next(
            picker.list.topLevelItem(i)
            for i in range(picker.list.topLevelItemCount())
            if picker.list.topLevelItem(i).data(0, QtCore.Qt.ItemDataRole.UserRole)
            == source
        )
        self.assertEqual(item.text(0), "dynamic_measurement_2")
        item.setText(0, "dynamic_measurement")
        picker.list.setCurrentItem(item)

        def provide_name(dialog):
            dialog.named_inputs["name"].setText('"second_measurement"')
            dialog.accept()
            return dialog.result()

        with patch.object(
            ComponentArgumentsDialog, "exec_", autospec=True, side_effect=provide_name
        ) as dialog:
            picker.add_selected()
            dialog.assert_called_once()
        self.assertIs(app.measurements["dynamic_measurement"], original)
        self.assertIn("second_measurement", app.measurements)
        entries = json.loads(app.microscope_config_path.read_text())[
            "dynamic_components"
        ]
        self.assertEqual(
            entries[0]["arguments"]["kwargs"]["name"], "second_measurement"
        )
        restored = self.make_app()
        self.assertIn("second_measurement", restored.measurements)

    def test_application_duplicate_registration_uses_shared_exception(self):
        app = self.make_app()
        sources = self.sources()
        hardware = app.dynamic_components.add(sources["Device"])
        measurement = app.dynamic_components.add(sources["Acquisition"])
        self.assertTrue(issubclass(ComponentAlreadyExistsError, ValueError))
        with self.assertRaisesRegex(
            ComponentAlreadyExistsError, "Hardware 'dynamic_device'"
        ):
            app.add_hardware(hardware)
        with self.assertRaisesRegex(
            ComponentAlreadyExistsError, "Measurement 'dynamic_measurement'"
        ):
            app.add_measurement(measurement)
        with self.assertRaises(ComponentAlreadyExistsError):
            app.dynamic_components.add(sources["Device"])
        self.assertIs(app.hardware["dynamic_device"], hardware)
        self.assertIs(app.measurements["dynamic_measurement"], measurement)

    def test_available_names_increment_numeric_suffix_and_skip_collisions(self):
        examples = [
            ("device", {"device"}, "device_2"),
            ("device_2", {"device_2"}, "device_3"),
            ("device_9", {"device_9", "device_10"}, "device_11"),
            ("device", {"device", "device_2", "device_3"}, "device_4"),
            ("device_2d", {"device_2d"}, "device_2d_2"),
            ("device", {"other"}, "device"),
        ]
        for name, occupied, expected in examples:
            with self.subTest(name=name, occupied=occupied):
                self.assertEqual(available_component_name(name, occupied), expected)

    def test_suggested_names_are_added_persisted_and_refreshed(self):
        source = self.sources()["Device"]
        app = self.make_app()
        app.dynamic_components.add(source)
        picker = ComponentPicker(app.dynamic_components)
        self.addCleanup(picker.deleteLater)
        picker.root.setText(str(self.project))
        picker.refresh()
        item = next(
            picker.list.topLevelItem(i)
            for i in range(picker.list.topLevelItemCount())
            if picker.list.topLevelItem(i).data(0, QtCore.Qt.ItemDataRole.UserRole)
            == source
        )
        self.assertEqual(item.text(0), "dynamic_device_2")
        picker.list.setCurrentItem(item)
        picker.add_selected()
        self.assertIn("dynamic_device_2", app.hardware)
        self.assertEqual(item.text(0), "dynamic_device_3")
        picker.add_selected()
        self.assertIn("dynamic_device_3", app.hardware)
        self.assertEqual(item.text(0), "dynamic_device_4")
        saved = json.loads(app.microscope_config_path.read_text())["dynamic_components"]
        self.assertEqual(
            [
                entry.get("arguments", {}).get("kwargs", {}).get("name")
                for entry in saved
            ],
            [None, "dynamic_device_2", "dynamic_device_3"],
        )
        restored = self.make_app()
        self.assertIn("dynamic_device_2", restored.hardware)
        self.assertIn("dynamic_device_3", restored.hardware)

    def test_builtin_suggestion_skips_existing_names_and_preserves_manual_names(self):
        source = BuiltinComponentSource(
            "ScopeFoundry.controlling.ranged_optimization",
            "RangedOptimization",
            "measurement",
            "ranged_optimization",
        )
        app = self.make_app()
        app.dynamic_components.add(source)
        app.dynamic_components.add(
            source, {"kwargs": {"name": "ranged_optimization_2"}}
        )
        with patch(
            "ScopeFoundry.base_app.component_picker.load_builtin_catalog",
            return_value=([source], []),
        ):
            picker = ComponentPicker(app.dynamic_components)
        self.addCleanup(picker.deleteLater)
        item = picker.builtin_list.topLevelItem(0)
        self.assertEqual(item.text(0), "ranged_optimization_3")
        picker.tabs.setCurrentWidget(picker.builtin_page)
        picker.builtin_list.setCurrentItem(item)
        picker.add_selected()
        self.assertIn("ranged_optimization_3", app.measurements)
        self.assertEqual(item.text(0), "ranged_optimization_4")
        saved = json.loads(app.microscope_config_path.read_text())["dynamic_components"]
        self.assertEqual(
            saved[-1]["arguments"]["kwargs"]["name"], "ranged_optimization_3"
        )
        item.setText(0, "custom")
        self.assertEqual(item.text(0), "custom")
        picker.builtin_list.setCurrentItem(item)
        picker.add_selected()
        self.assertIn("custom", app.measurements)
        self.assertEqual(item.text(0), "custom_2")

    def test_table_name_edit_adds_and_restores_named_folder_component(self):
        source = self.sources()["Device"]
        app = self.make_app()
        picker = ComponentPicker(app.dynamic_components)
        self.addCleanup(picker.deleteLater)
        picker.root.setText(str(self.project))
        picker.refresh()
        self.assertEqual(
            [picker.list.headerItem().text(i) for i in range(5)],
            ["Name", "Module", "Kind", "Class", "Path / details"],
        )
        item = next(
            picker.list.topLevelItem(i)
            for i in range(picker.list.topLevelItemCount())
            if picker.list.topLevelItem(i).data(0, QtCore.Qt.ItemDataRole.UserRole)
            == source
        )
        self.assertTrue(item.flags() & QtCore.Qt.ItemFlag.ItemIsEditable)
        item.setText(0, "chosen_device")
        picker.list.setCurrentItem(item)
        picker.add_selected()
        self.assertIn("chosen_device", app.hardware)
        saved = json.loads(app.microscope_config_path.read_text())["dynamic_components"]
        self.assertEqual(saved[0]["arguments"]["kwargs"]["name"], "chosen_device")
        restored = self.make_app()
        self.assertIn("chosen_device", restored.hardware)

    def test_table_name_edit_adds_builtin_component(self):
        source = BuiltinComponentSource(
            "ScopeFoundry.controlling.ranged_optimization",
            "RangedOptimization",
            "measurement",
        )
        app = self.make_app()
        with patch(
            "ScopeFoundry.base_app.component_picker.load_builtin_catalog",
            return_value=([source], []),
        ):
            picker = ComponentPicker(app.dynamic_components)
        self.addCleanup(picker.deleteLater)
        picker.tabs.setCurrentWidget(picker.builtin_page)
        item = picker.builtin_list.topLevelItem(0)
        item.setText(0, "chosen_builtin")
        picker.builtin_list.setCurrentItem(item)
        picker.add_selected()
        self.assertIn("chosen_builtin", app.measurements)
        restored = self.make_app()
        self.assertIn("chosen_builtin", restored.measurements)

    def test_invalid_constructor_arguments_reported_and_not_saved(self):
        app = self.make_app()
        source = self.sources()["NeedsArgument"]
        with self.assertRaisesRegex(TypeError, "required"):
            app.dynamic_components.add(source)
        with self.assertRaisesRegex(ValueError, "automatically"):
            app.dynamic_components.add(source, {"kwargs": {"app": 1}})
        dialog = ComponentArgumentsDialog(
            app.ui,
            load_component_class(source),
            "missing required",
            {"args": [], "kwargs": {}},
        )
        self.addCleanup(dialog.deleteLater)
        dialog.input.setPlainText('{"kwargs": {"required": NaN}}')
        with patch.object(QtWidgets.QMessageBox, "warning") as warning:
            dialog.accept()
            warning.assert_called_once()
        self.assertNotEqual(dialog.result(), QtWidgets.QDialog.DialogCode.Accepted)
        self.assertEqual(app.dynamic_components.order, [])

    def test_named_arguments_optional_defaults_and_advanced_conflicts(self):
        app = self.make_app()

        class Example:
            def __init__(self, app, required, optional=3, *, flag=False):
                pass

        dialog = ComponentArgumentsDialog(
            app.ui, Example, "failed", {"kwargs": {"required": "old", "flag": True}}
        )
        self.addCleanup(dialog.deleteLater)
        self.assertEqual(dialog.named_inputs["required"].text(), '"old"')
        self.assertEqual(dialog.named_inputs["flag"].text(), "true")
        self.assertEqual(dialog.named_inputs["optional"].text(), "3")
        self.assertIn("3", dialog.named_inputs["optional"].placeholderText())
        dialog.named_inputs["required"].setText("not json")
        with patch.object(QtWidgets.QMessageBox, "warning") as warning:
            dialog.accept()
            warning.assert_called_once()
        dialog.named_inputs["required"].setText('"new"')
        dialog.input.setPlainText('{"kwargs": {"required": "duplicate"}}')
        with patch.object(QtWidgets.QMessageBox, "warning") as warning:
            dialog.accept()
            warning.assert_called_once()
        dialog.input.setPlainText('{"args": [], "kwargs": {}}')
        dialog.accept()
        self.assertEqual(
            dialog.arguments,
            {"args": [], "kwargs": {"required": "new", "flag": True}},
        )
        self.assertEqual(dialog.result(), QtWidgets.QDialog.DialogCode.Accepted)

    def test_prefilled_defaults_are_optional_and_keep_python_default_semantics(self):
        app = self.make_app()

        class Example:
            def __init__(
                self,
                app,
                count=3,
                flag=False,
                name=None,
                text="hello",
                items=(1, 2),
                *,
                data=None,
            ):
                pass

        dialog = ComponentArgumentsDialog(app.ui, Example, "failed", {})
        self.addCleanup(dialog.deleteLater)
        expected = {
            "count": "3",
            "flag": "false",
            "name": "null",
            "text": '"hello"',
            "data": "null",
            "items": "",
        }
        self.assertEqual(
            {name: field.text() for name, field in dialog.named_inputs.items()},
            expected,
        )
        self.assertIn("(1, 2)", dialog.named_inputs["items"].placeholderText())
        dialog.input.setPlainText('{"args": [7], "kwargs": {}}')
        dialog.named_inputs["flag"].setText("true")
        dialog.named_inputs["name"].clear()
        dialog.accept()
        self.assertEqual(dialog.result(), QtWidgets.QDialog.DialogCode.Accepted)
        self.assertEqual(dialog.arguments, {"args": [7], "kwargs": {"flag": True}})

    def test_namespace_package_folder_preserves_import_identity(self):
        namespace = self.directory / ("namespace_" + uuid.uuid4().hex)
        namespace.mkdir()
        (namespace / "device.py").write_text(
            "from ScopeFoundry import HardwareComponent\n"
            "class Device(HardwareComponent):\n"
            "    pass\n",
            encoding="utf-8",
        )
        import_root = str(self.directory.resolve())
        sys.path.insert(0, import_root)
        sources, errors = discover_components(namespace)
        self.assertEqual(errors, [])
        self.assertEqual(sources[0].module, f"{namespace.name}.device")
        sys.path.remove(import_root)
        self.addCleanup(
            lambda: sys.path.remove(import_root) if import_root in sys.path else None
        )
        self.assertEqual(load_component_class(sources[0]).__module__, sources[0].module)
        self.addCleanup(sys.modules.pop, sources[0].module, None)
        self.addCleanup(sys.modules.pop, namespace.name, None)

    def test_folder_entries_do_not_save_root_and_legacy_entries_restore(self):
        source = self.sources()["Device"]
        entry = source.as_dict()
        self.assertNotIn("root", entry)
        self.assertEqual(entry["path"], source.path)
        legacy = {**entry, "root": source.root}
        config_path = self.directory / "dynamic-test.scopefoundry"
        config_path.write_text(
            json.dumps({"dynamic_components": [legacy], "other": 12})
        )
        app = self.make_app()
        self.assertIn("dynamic_device", app.hardware)
        editor = SavedComponentsEditor(app.dynamic_components, [legacy])
        self.addCleanup(editor.deleteLater)
        editor.list.setCurrentItem(editor.list.topLevelItem(0))
        editor.remove_selected()
        self.assertEqual(
            json.loads(config_path.read_text()), {"dynamic_components": [], "other": 12}
        )

    def test_folder_module_path_mismatch_is_rejected(self):
        source = self.sources()["Device"]
        bad = ComponentSource(
            "", "different.components", source.path, source.class_name, source.kind
        )
        with self.assertRaisesRegex(ValueError, "does not match"):
            load_component_class(bad)

    def test_picker_runtime_add_remove_and_shortcuts(self):
        app = self.make_app()
        with patch.object(ComponentPicker, "exec_") as execute:
            app.add_component_button.click()
            execute.assert_called_once()
        picker = ComponentPicker(app.dynamic_components)
        self.addCleanup(picker.deleteLater)
        picker.root.setText(str(self.project))
        picker.refresh()
        for row in range(picker.list.topLevelItemCount()):
            item = picker.list.topLevelItem(row)
            if item.data(0, QtCore.Qt.ItemDataRole.UserRole).class_name == "Device":
                picker.list.setCurrentItem(item)
                break
        else:
            self.fail("Device missing from picker")
        self.assertEqual(
            [item.text(i) for i in range(5)],
            [
                "dynamic_device",
                f"{self.package_name}.components",
                "Hardware",
                "Device",
                str(self.project.resolve() / "components.py"),
            ],
        )
        picker.add_selected()
        hw = app.hardware["dynamic_device"]
        self.assertIn("key", hw.operations._shortcuts)
        self.assertTrue(
            any(
                app.hw_tree.topLevelItem(i).text(0) == hw.name
                for i in range(app.hw_tree.topLevelItemCount())
            )
        )
        with self.assertRaisesRegex(ValueError, "already"):
            app.dynamic_components.add(self.sources()["Device"])
        app.remove_hardware(hw.name)
        self.assertEqual(hw.operations._shortcuts, {})
        self.assertEqual(app.dynamic_components.order, [])

    def test_picker_remove_tab_edits_saved_components(self):
        source = self.sources()["Device"]
        config_path = self.directory / "dynamic-test.scopefoundry"
        config_path.write_text(
            json.dumps({"dynamic_components": [source.as_dict()], "other": 1})
        )
        app = self.make_app()
        picker = ComponentPicker(app.dynamic_components)
        self.addCleanup(picker.deleteLater)
        self.assertEqual(
            [picker.tabs.tabText(i) for i in range(picker.tabs.count())],
            ["Add ScopeFoundry built-in", "Add from folder", "Edit"],
        )
        self.assertFalse(picker.tabs.tabIcon(0).isNull())
        self.assertFalse(picker.tabs.tabIcon(0).pixmap(16, 16).isNull())
        picker.tabs.setCurrentWidget(picker.remove_page)
        self.assertFalse(picker.add_button.isEnabled())
        self.assertEqual(picker.remove_page.list.topLevelItemCount(), 1)
        self.assertEqual(
            "dynamic_device", picker.remove_page.list.topLevelItem(0).text(0)
        )
        picker.remove_page.list.setCurrentItem(picker.remove_page.list.topLevelItem(0))
        picker.remove_page.remove_selected()
        picker.tabs.setCurrentWidget(picker.folder_page)
        picker.tabs.setCurrentWidget(picker.remove_page)
        self.assertEqual(picker.remove_page.list.topLevelItemCount(), 0)
        self.assertEqual(
            json.loads(config_path.read_text()), {"dynamic_components": [], "other": 1}
        )
        self.assertNotIn("dynamic_device", app.hardware)

    def test_filter_applies_to_all_tabs_and_preserves_hidden_entries(self):
        sources = self.sources()
        entries = [sources["Device"].as_dict(), sources["Acquisition"].as_dict()]
        config_path = self.directory / "dynamic-test.scopefoundry"
        config_path.write_text(json.dumps({"dynamic_components": entries}))
        app = self.make_app()
        builtin = BuiltinComponentSource(
            "ScopeFoundry.sequencer.sequencer", "Sequencer", "measurement"
        )
        with patch(
            "ScopeFoundry.base_app.component_picker.load_builtin_catalog",
            return_value=([builtin], []),
        ):
            picker = ComponentPicker(app.dynamic_components)
        self.addCleanup(picker.deleteLater)
        picker.root.setText(str(self.project))
        picker.refresh()
        picker.search.setText("device")
        folder_items = [
            picker.list.topLevelItem(i) for i in range(picker.list.topLevelItemCount())
        ]
        device = next(item for item in folder_items if "Device" in item.text(3))
        acquisition = next(
            item for item in folder_items if "Acquisition" in item.text(3)
        )
        self.assertFalse(device.isHidden())
        self.assertTrue(acquisition.isHidden())
        self.assertTrue(picker.builtin_list.topLevelItem(0).isHidden())
        picker.tabs.setCurrentWidget(picker.remove_page)
        self.assertFalse(picker.search.isHidden())
        saved = picker.remove_page.list
        self.assertFalse(saved.topLevelItem(0).isHidden())
        self.assertTrue(saved.topLevelItem(1).isHidden())
        saved.topLevelItem(0).setSelected(True)
        saved.topLevelItem(1).setSelected(True)
        picker.remove_page.remove_selected()
        self.assertEqual(
            json.loads(config_path.read_text())["dynamic_components"], [entries[1]]
        )
        self.assertTrue(saved.topLevelItem(0).isHidden())
        picker.tabs.setCurrentWidget(picker.builtin_page)
        picker.search.setText("sequencer")
        self.assertFalse(picker.builtin_list.topLevelItem(0).isHidden())
        self.assertTrue(device.isHidden())
        picker.search.clear()
        self.assertFalse(device.isHidden())
        self.assertFalse(saved.topLevelItem(0).isHidden())

    def test_picker_displays_scan_failures_in_folder_list(self):
        broken = self.project / "broken.py"
        broken.write_text("class Broken(\n", encoding="utf-8")
        app = self.make_app()
        with patch.object(QtWidgets.QMessageBox, "warning") as warning:
            picker = ComponentPicker(app.dynamic_components)
            self.addCleanup(picker.deleteLater)
            picker.root.setText(str(self.project))
            picker.refresh()
            warning.assert_not_called()
        error = next(
            picker.list.topLevelItem(i)
            for i in range(picker.list.topLevelItemCount())
            if "broken.py" in picker.list.topLevelItem(i).text(4)
        )
        self.assertIn("broken.py", error.text(4))
        self.assertIn("was never closed", error.text(4))
        self.assertEqual(error.toolTip(4), error.text(4))
        self.assertEqual(error.foreground(4).color(), QtGui.QColor("red"))
        picker.list.setCurrentItem(error)
        self.assertFalse(picker.add_button.isEnabled())
        with patch.object(app.dynamic_components, "add") as add, patch.object(
            QtWidgets.QMessageBox, "information"
        ):
            picker.add_selected()
            add.assert_not_called()
        picker.search.setText("broken.py")
        self.assertFalse(error.isHidden())
        picker.search.setText("no match")
        self.assertTrue(error.isHidden())
        broken.write_text("pass\n", encoding="utf-8")
        picker.refresh()
        self.assertFalse(
            any(
                "broken.py" in picker.list.topLevelItem(i).text(4)
                for i in range(picker.list.topLevelItemCount())
            )
        )

    def test_builtin_tab_search_and_selection_without_import(self):
        app = self.make_app()
        source = BuiltinComponentSource(
            "ScopeFoundry.sequencer.sequencer",
            "Sequencer",
            "measurement",
            "sequence_name",
        )
        with patch(
            "ScopeFoundry.base_app.component_picker.load_builtin_catalog",
            return_value=([source], []),
        ), patch(
            "ScopeFoundry.base_app.component_picker.load_component_class"
        ) as loader:
            picker = ComponentPicker(app.dynamic_components)
            self.addCleanup(picker.deleteLater)
            loader.assert_not_called()
            picker.tabs.setCurrentWidget(picker.builtin_page)
            item = picker.builtin_list.topLevelItem(0)
            self.assertEqual(
                [item.text(i) for i in range(5)],
                [
                    "sequence_name",
                    "ScopeFoundry.sequencer.sequencer",
                    "Measurement",
                    "Sequencer",
                    "",
                ],
            )
            picker.search.setText("sequence_name")
            self.assertFalse(item.isHidden())
            picker.search.setText("no match")
            self.assertTrue(item.isHidden())
            picker.search.clear()
            picker.builtin_list.setCurrentItem(item)
            self.assertTrue(picker.add_button.isEnabled())
            with patch.object(
                app.dynamic_components,
                "add",
                return_value=type("Component", (), {"name": "sequence"})(),
            ) as add:
                picker.add_selected()
                add.assert_called_once_with(
                    source,
                    arguments={"args": [], "kwargs": {}},
                    measurement_options={
                        "initially_hidden": True,
                        "unhide_on_connection": None,
                    },
                )

    def test_builtin_catalog_validation_and_errors(self):
        path = self.directory / "catalog.json"
        path.write_text(
            json.dumps(
                [
                    {
                        "module": "ScopeFoundry.sequencer.sequencer",
                        "class_name": "Sequencer",
                        "kind": "measurement",
                        "name": "sequence_name",
                    },
                    {
                        "module": "other.module",
                        "class_name": "Invalid",
                        "kind": "hardware",
                    },
                    {
                        "module": "ScopeFoundry.sequencer.sequencer",
                        "class_name": "Sequencer",
                        "kind": "measurement",
                        "name": "other_name",
                    },
                    {
                        "module": "ScopeFoundry.sweeping.map_2D",
                        "class_name": "Map2D",
                        "kind": "measurement",
                        "name": 42,
                    },
                ]
            )
        )
        sources, errors = load_builtin_catalog(path)
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0].name, "sequence_name")
        self.assertNotIn("name", sources[0].as_dict())
        self.assertEqual(len(errors), 3)
        self.assertIn("Entry 2", errors[0])
        self.assertIn("Duplicate", errors[1])
        self.assertIn("Entry 4", errors[2])
        path.write_text("{}")
        with self.assertRaisesRegex(ValueError, "must be a list"):
            load_builtin_catalog(path)
        app = self.make_app()
        with patch(
            "ScopeFoundry.base_app.component_picker.load_builtin_catalog",
            side_effect=ValueError("broken catalog"),
        ), patch.object(QtWidgets.QMessageBox, "warning") as warning:
            picker = ComponentPicker(app.dynamic_components)
            self.addCleanup(picker.deleteLater)
            warning.assert_called_once()
            self.assertEqual(picker.builtin_list.topLevelItemCount(), 0)

    def test_builtin_portable_identity_restore_and_editor(self):
        source = BuiltinComponentSource(
            "ScopeFoundry.controlling.ranged_optimization",
            "RangedOptimization",
            "measurement",
        )
        self.assertNotIn("path", source.as_dict())
        self.assertEqual(load_component_class(source).__name__, "RangedOptimization")
        config_path = self.directory / "dynamic-test.scopefoundry"
        config_path.write_text(
            json.dumps({"dynamic_components": [source.as_dict()], "other": 1})
        )
        app = self.make_app()
        self.assertTrue(
            any(
                type(measure).__name__ == source.class_name
                for measure in app.measurements.values()
            )
        )
        editor = SavedComponentsEditor(app.dynamic_components, [source.as_dict()])
        self.addCleanup(editor.deleteLater)
        self.assertEqual(editor.list.topLevelItem(0).text(4), "ScopeFoundry built-in")
        editor.list.topLevelItem(0).setSelected(True)
        editor.remove_selected()
        self.assertEqual(
            json.loads(config_path.read_text()), {"dynamic_components": [], "other": 1}
        )

    def test_builtin_added_in_picker_is_saved_and_restored_without_catalog(self):
        source = BuiltinComponentSource(
            "ScopeFoundry.controlling.ranged_optimization",
            "RangedOptimization",
            "measurement",
            "ranged_optimization",
        )
        app = self.make_app()
        with patch(
            "ScopeFoundry.base_app.component_picker.load_builtin_catalog",
            return_value=([source], []),
        ):
            picker = ComponentPicker(app.dynamic_components)
        self.addCleanup(picker.deleteLater)
        picker.tabs.setCurrentWidget(picker.builtin_page)
        self.assertEqual(
            picker.builtin_list.topLevelItem(0).text(0), "ranged_optimization"
        )
        picker.builtin_list.setCurrentItem(picker.builtin_list.topLevelItem(0))
        picker.add_selected()
        entry = dict(
            source.as_dict(),
            measurement_options={
                "initially_hidden": True,
                "unhide_on_connection": None,
            },
        )
        self.assertEqual(app.dynamic_components.order, [entry])
        saved = json.loads(app.microscope_config_path.read_text())
        self.assertEqual(saved["dynamic_components"], [entry])
        picker.tabs.setCurrentWidget(picker.remove_page)
        self.assertEqual(
            picker.remove_page.list.topLevelItem(0).text(4), "ScopeFoundry built-in"
        )
        with patch(
            "ScopeFoundry.base_app.component_picker.load_builtin_catalog",
            side_effect=FileNotFoundError("catalog removed"),
        ):
            restored = self.make_app()
        self.assertTrue(
            any(
                type(measure).__name__ == source.class_name
                for measure in restored.measurements.values()
            )
        )
        self.assertEqual(restored.dynamic_components.order, [entry])

    def test_measurement_registration_mdi_and_non_mdi(self):
        source = self.sources()["Acquisition"]
        for mdi in (True, False):
            with self.subTest(mdi=mdi):
                app = self.make_app(mdi=mdi)
                measure = app.dynamic_components.add(source)
                self.assertIs(app.measurements[measure.name], measure)
                if mdi:
                    self.assertIsNotNone(measure.subwin)
                    self.assertIn(measure.name, app._loaded_measure_uis)
                else:
                    self.assertIsNone(measure.subwin)
                app.remove_measurement(measure.name)
                self.assertNotIn(measure.name, app.measurements)
                config = json.loads(app.microscope_config_path.read_text())
                config["dynamic_components"] = []
                app.microscope_config_path.write_text(json.dumps(config))

    def test_failed_figure_setup_rolls_back_registration(self):
        app = self.make_app()
        with self.assertRaisesRegex(RuntimeError, "figure failed"):
            app.dynamic_components.add(self.sources()["BrokenFigure"])
        self.assertNotIn("broken_figure", app.measurements)
        self.assertNotIn("mm/broken_figure/activation", app._setting_paths)
        self.assertEqual(app.dynamic_components.order, [])

    def test_persistence_failure_does_not_open_constructor_dialog(self):
        app = self.make_app()
        picker = ComponentPicker(app.dynamic_components)
        self.addCleanup(picker.deleteLater)
        picker.root.setText(str(self.project))
        picker.refresh()
        item = next(
            picker.list.topLevelItem(i)
            for i in range(picker.list.topLevelItemCount())
            if picker.list.topLevelItem(i).text(3) == "Device"
        )
        picker.list.setCurrentItem(item)
        with patch.object(
            app.dynamic_components,
            "add",
            side_effect=ComponentPersistenceError("disk full"),
        ), patch.object(ComponentArgumentsDialog, "exec_") as dialog, patch.object(
            QtWidgets.QMessageBox, "warning"
        ) as warning:
            picker.add_selected()
            dialog.assert_not_called()
            warning.assert_called_once()

    def test_editor_removes_entries_and_running_components(self):
        sources = self.sources()
        device, measure = sources["Device"].as_dict(), sources["Acquisition"].as_dict()
        missing = {"broken": "entry"}
        config_path = self.directory / "dynamic-test.scopefoundry"
        config_path.write_text(
            json.dumps({"other": 12, "dynamic_components": [device, missing]})
        )
        app = self.make_app()
        manager = app.dynamic_components
        editor = SavedComponentsEditor(manager, [device, missing])
        self.addCleanup(editor.deleteLater)
        self.assertEqual("dynamic_device", editor.list.topLevelItem(0).text(0))
        self.assertEqual("unavailable", editor.list.topLevelItem(1).text(0))
        editor.list.topLevelItem(0).setSelected(True)
        editor.list.topLevelItem(1).setSelected(True)
        editor.remove_selected()
        self.assertEqual(
            json.loads(config_path.read_text()), {"other": 12, "dynamic_components": []}
        )
        self.assertNotIn("dynamic_device", app.hardware)
        manager.add(sources["Acquisition"])
        self.assertEqual(
            json.loads(config_path.read_text())["dynamic_components"],
            [manager._entry_for_source(sources["Acquisition"], {})],
        )

    def test_edit_tab_renames_running_component_and_restores_it(self):
        source = self.sources()["Device"]
        app = self.make_app()
        old = app.dynamic_components.add(source)
        entries = json.loads(app.microscope_config_path.read_text())[
            "dynamic_components"
        ]
        editor = SavedComponentsEditor(app.dynamic_components, entries)
        self.addCleanup(editor.deleteLater)
        with patch.object(
            QtWidgets.QMessageBox,
            "question",
            return_value=QtWidgets.QMessageBox.StandardButton.Yes,
        ):
            editor.list.topLevelItem(0).setText(0, "renamed_device")
        self.assertNotIn(old.name, app.hardware)
        self.assertIn("renamed_device", app.hardware)
        self.assertEqual(editor.list.topLevelItem(0).text(0), "renamed_device")
        saved = json.loads(app.microscope_config_path.read_text())["dynamic_components"]
        self.assertEqual(saved[0]["arguments"]["kwargs"]["name"], "renamed_device")
        restored = self.make_app()
        self.assertIn("renamed_device", restored.hardware)
        restored.dynamic_components.remove_saved(saved, saved[:])
        self.assertNotIn("renamed_device", restored.hardware)

    def test_edit_tab_rename_cancel_and_invalid_names(self):
        app = self.make_app()
        app.dynamic_components.add(self.sources()["Device"])
        entries = json.loads(app.microscope_config_path.read_text())[
            "dynamic_components"
        ]
        editor = SavedComponentsEditor(app.dynamic_components, entries)
        self.addCleanup(editor.deleteLater)
        with patch.object(
            QtWidgets.QMessageBox,
            "question",
            return_value=QtWidgets.QMessageBox.StandardButton.No,
        ):
            editor.list.topLevelItem(0).setText(0, "cancelled")
        self.assertEqual(editor.list.topLevelItem(0).text(0), "dynamic_device")
        with patch.object(
            QtWidgets.QMessageBox,
            "question",
            return_value=QtWidgets.QMessageBox.StandardButton.Yes,
        ), patch.object(QtWidgets.QMessageBox, "warning") as warning:
            editor.list.topLevelItem(0).setText(0, "")
            warning.assert_called_once()
        self.assertIn("dynamic_device", app.hardware)
        self.assertEqual(
            json.loads(app.microscope_config_path.read_text())["dynamic_components"],
            entries,
        )

    def test_rename_rejects_running_measurement_and_duplicate(self):
        app = self.make_app()
        sources = self.sources()
        measure = app.dynamic_components.add(sources["Acquisition"])
        app.dynamic_components.add(sources["Device"])
        entries = json.loads(app.microscope_config_path.read_text())[
            "dynamic_components"
        ]
        with patch.object(measure, "is_measuring", return_value=True):
            with self.assertRaisesRegex(ValueError, "Stop measurement"):
                app.dynamic_components.rename_saved(entries, entries[0], "renamed")
        with self.assertRaisesRegex(ComponentAlreadyExistsError, "already exists"):
            app.dynamic_components.rename_saved(entries, entries[1], "dynamic_device")
        self.assertEqual(
            json.loads(app.microscope_config_path.read_text())["dynamic_components"],
            entries,
        )

    def test_rename_rejects_connected_hardware_and_external_changes(self):
        app = self.make_app()
        hw = app.dynamic_components.add(self.sources()["Device"])
        entries = json.loads(app.microscope_config_path.read_text())[
            "dynamic_components"
        ]
        with patch.object(
            type(hw), "is_connected", new_callable=PropertyMock, return_value=True
        ):
            with self.assertRaisesRegex(ValueError, "Disconnect hardware"):
                app.dynamic_components.rename_saved(entries, entries[0], "renamed")
        updated = {"dynamic_components": entries + [{"invalid": True}], "other": 2}
        app.microscope_config_path.write_text(json.dumps(updated))
        with self.assertRaisesRegex(ValueError, "changed elsewhere"):
            app.dynamic_components.rename_saved(entries, entries[0], "renamed")
        self.assertIn("dynamic_device", app.hardware)
        self.assertEqual(json.loads(app.microscope_config_path.read_text()), updated)

    def test_rename_save_failure_removes_replacement(self):
        app = self.make_app()
        app.dynamic_components.add(self.sources()["Device"])
        entries = json.loads(app.microscope_config_path.read_text())[
            "dynamic_components"
        ]
        with patch.object(
            app.dynamic_components, "_save_config", side_effect=OSError("disk full")
        ):
            with self.assertRaisesRegex(OSError, "disk full"):
                app.dynamic_components.rename_saved(entries, entries[0], "renamed")
        self.assertIn("dynamic_device", app.hardware)
        self.assertNotIn("renamed", app.hardware)
        self.assertEqual(
            json.loads(app.microscope_config_path.read_text())["dynamic_components"],
            entries,
        )

    def test_rename_removal_failure_restores_old_entry_and_component(self):
        app = self.make_app()
        app.dynamic_components.add(self.sources()["Device"])
        entries = json.loads(app.microscope_config_path.read_text())[
            "dynamic_components"
        ]
        original_remove = app.remove_hardware

        def remove(name):
            if name == "dynamic_device":
                raise RuntimeError("remove failed")
            return original_remove(name)

        with patch.object(app, "remove_hardware", side_effect=remove):
            with self.assertRaisesRegex(RuntimeError, "remove failed"):
                app.dynamic_components.rename_saved(entries, entries[0], "renamed")
        self.assertIn("dynamic_device", app.hardware)
        self.assertNotIn("renamed", app.hardware)
        self.assertEqual(
            json.loads(app.microscope_config_path.read_text())["dynamic_components"],
            entries,
        )

    def test_rename_preserves_positional_arguments(self):
        app = self.make_app()
        app.dynamic_components.add(
            self.sources()["Device"], {"args": [False, "first"], "kwargs": {}}
        )
        entries = json.loads(app.microscope_config_path.read_text())[
            "dynamic_components"
        ]
        app.dynamic_components.rename_saved(entries, entries[0], "renamed")
        saved = json.loads(app.microscope_config_path.read_text())["dynamic_components"]
        self.assertEqual(
            saved[0]["arguments"], {"args": [False, "renamed"], "kwargs": {}}
        )
        restored = self.make_app()
        self.assertIn("renamed", restored.hardware)

    def test_editor_cancel_and_external_change_preserve_configuration(self):
        entry = self.sources()["Device"].as_dict()
        config_path = self.directory / "dynamic-test.scopefoundry"
        config_path.write_text(json.dumps({"dynamic_components": [entry], "other": 1}))
        app = self.make_app()
        editor = SavedComponentsEditor(app.dynamic_components, [entry])
        self.addCleanup(editor.deleteLater)
        editor.reject()
        self.assertEqual(
            json.loads(config_path.read_text())["dynamic_components"], [entry]
        )
        editor = SavedComponentsEditor(app.dynamic_components, [entry])
        self.addCleanup(editor.deleteLater)
        editor.list.topLevelItem(0).setSelected(True)
        updated = {"dynamic_components": [entry, {"unexpected": True}], "other": 2}
        config_path.write_text(json.dumps(updated))
        with patch.object(QtWidgets.QMessageBox, "warning") as warning:
            editor.remove_selected()
            warning.assert_called_once()
        self.assertEqual(json.loads(config_path.read_text()), updated)
        self.assertEqual(app.dynamic_components.order, [entry])

    def test_editor_preserves_other_pending_additions(self):
        sources = self.sources()
        device = sources["Device"].as_dict()
        config_path = self.directory / "dynamic-test.scopefoundry"
        config_path.write_text(json.dumps({"dynamic_components": [device]}))
        app = self.make_app()
        app.dynamic_components.add(sources["Acquisition"])
        saved = json.loads(config_path.read_text())["dynamic_components"]
        editor = SavedComponentsEditor(app.dynamic_components, saved)
        self.addCleanup(editor.deleteLater)
        editor.list.topLevelItem(0).setSelected(True)
        editor.remove_selected()
        self.assertEqual(
            json.loads(config_path.read_text())["dynamic_components"],
            [app.dynamic_components._entry_for_source(sources["Acquisition"], {})],
        )

    def test_restore_before_profile_and_failed_entries(self):
        sources = self.sources()
        config_path = self.directory / "dynamic-test.scopefoundry"
        original = {"other": {"value": 7}, "dynamic_components": []}
        config_path.write_text(json.dumps(original), encoding="utf-8")
        app = self.make_app()
        app.dynamic_components.add(sources["Device"])
        saved = json.loads(config_path.read_text())
        self.assertEqual(saved["other"], original["other"])
        self.assertEqual(
            saved["dynamic_components"],
            [app.dynamic_components._entry_for_source(sources["Device"], {})],
        )
        missing = sources["Acquisition"].as_dict()
        missing["path"] = str(self.project / "missing.py")
        saved["dynamic_components"].append(missing)
        config_path.write_text(json.dumps(saved), encoding="utf-8")
        observed = []
        app2 = self.make_app(
            profile_callback=lambda manager: observed.append(
                "dynamic_device" in manager.app.hardware
            )
        )
        self.assertEqual(observed, [True])
        self.assertIn("dynamic_device", app2.hardware)
        self.assertEqual(app2.dynamic_components.unresolved, [missing])
        self.assertEqual(
            json.loads(config_path.read_text())["dynamic_components"],
            saved["dynamic_components"],
        )


if __name__ == "__main__":
    unittest.main()
