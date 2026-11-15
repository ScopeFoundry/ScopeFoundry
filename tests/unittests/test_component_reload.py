import importlib
import os
import sys
import tempfile
import types
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from qtpy import QtWidgets

from ScopeFoundry import BaseMicroscopeApp
from ScopeFoundry.base_app.component_reload import _validate_main_body
from ScopeFoundry.base_app.profile_manager import ProfileManager
from ScopeFoundry.tests.unittests.unittest_helpers import close_app_widgets


SOURCE = """
from ScopeFoundry import HardwareComponent, Measurement
from qtpy import QtWidgets

VERSION = {version}

class Device(HardwareComponent):
    def __init__(self, app, events, factor, *, name=None):
        self.events = events
        self.factor = factor
        super().__init__(app, name=name)

    def setup(self):
        self.settings.New("level", dtype=int, initial=VERSION)
        self.add_operation("record", self.record)

    def record(self):
        self.events.append(self)

    def connect(self):
        self.events.append(("connect", self.factor))

    def disconnect(self):
        self.events.append(("disconnect", self.factor))

class Parent(Measurement):
    def __init__(self, app, factor, name=None):
        self.factor = factor
        Measurement.__init__(self, app, name=name)

class Acquisition(Parent):
    def __init__(self, app, factor, *, name=None):
        super().__init__(app, factor, name=name)

    def setup(self):
        self.settings.New("level", dtype=int, initial=VERSION)

    def setup_figure(self):
        self.ui = QtWidgets.QWidget()

    def run(self):
        import time
        while not self.interrupt_measurement_called:
            time.sleep(0.005)
"""


class ComponentReloadTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.module_name = "reload_test_" + uuid.uuid4().hex
        self.path = self.directory / (self.module_name + ".py")
        self.write_source(1)
        sys.path.insert(0, str(self.directory))
        self.addCleanup(self.cleanup_modules)
        self.module = importlib.import_module(self.module_name)
        implementation = patch(
            "ScopeFoundry.base_app.base_microscope_app.get_child_path",
            return_value=self.directory,
        )
        implementation.start()
        self.addCleanup(implementation.stop)
        startup = patch.object(ProfileManager, "initialize_startup_profile", lambda _: None)
        startup.start()
        self.addCleanup(startup.stop)
        profiles = patch.object(
            ProfileManager, "_profiles_dir_for_app", return_value=self.directory / "profiles"
        )
        profiles.start()
        self.addCleanup(profiles.stop)
        restore = patch("ScopeFoundry.base_app.component_picker.DynamicComponents.restore")
        restore.start()
        self.addCleanup(restore.stop)
        console = patch(
            "ScopeFoundry.base_app.base_app.new_console_widget",
            side_effect=lambda *_args: QtWidgets.QWidget(),
        )
        console.start()
        self.addCleanup(console.stop)

    def cleanup_modules(self):
        sys.modules.pop(self.module_name, None)
        sys.path.remove(str(self.directory))

    def write_source(self, version):
        self.path.write_text(SOURCE.format(version=version), encoding="utf-8")

    def make_app(self, mdi=True):
        class App(BaseMicroscopeApp):
            name = "reload-test"

        App.mdi = mdi
        app = App([])
        self.addCleanup(close_app_widgets, app)
        return app

    def test_hardware_reconstructs_arguments_and_restores_history(self):
        app = self.make_app()
        events = []
        hw = app.add_hardware(self.module.Device(app, events, 7, name="custom"))
        app.add_hardware(self.module.Device(app, events, 9, name="other"))
        hw.settings["level"] = 42
        hw.settings["connected"] = True
        entry = {"kind": "hardware", "name": "custom"}
        app.dynamic_components.added[("hardware", "custom")] = entry
        app.dynamic_components.order.append(entry)
        stat = self.path.stat()
        self.write_source(2)
        os.utime(self.path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        new = app.reload_hardware(hw.name)
        self.assertIsNot(new, hw)
        self.assertIs(app.hardware["custom"], new)
        self.assertIs(new.events, events)
        self.assertEqual(new.factor, 7)
        self.assertEqual(new.settings["level"], 42)
        self.assertFalse(new.is_connected)
        self.assertEqual(events, [("connect", 7), ("disconnect", 7)])
        self.assertEqual(sys.modules[self.module_name].VERSION, 2)
        self.assertEqual(app.hardware["other"].factor, 9)
        self.assertEqual(app.dynamic_components.order, [entry])
        self.assertIs(app.dynamic_components.added[("hardware", "custom")], entry)

    def test_reload_orders_stop_snapshot_replace_and_restore(self):
        app = self.make_app()
        hw = app.add_hardware(self.module.Device(app, [], 7, name="device"))
        hw.settings["connected"] = True
        history = app.profile_manager.history
        events = []
        save = history.save_snapshot
        restore = history.restore_snapshot
        remove = app.remove_hardware
        add = app.add_hardware

        def capture(reason):
            self.assertFalse(hw.is_connected)
            self.assertIs(app.hardware["device"], hw)
            events.append("snapshot")
            return save(reason)

        def remove_old(name):
            events.append("remove")
            return remove(name)

        def add_new(component):
            events.append("add")
            return add(component)

        def apply_snapshot(name, **kwargs):
            self.assertIsNot(app.hardware["device"], hw)
            events.append("restore")
            return restore(name, **kwargs)

        self.write_source(2)
        with patch.object(history, "save_snapshot", side_effect=capture), \
             patch.object(history, "restore_snapshot", side_effect=apply_snapshot), \
             patch.object(app, "remove_hardware", side_effect=remove_old), \
             patch.object(app, "add_hardware", side_effect=add_new):
            app.reload_hardware("device")
        self.assertEqual(events, ["snapshot", "remove", "add", "restore"])

    def test_compile_error_does_not_stop_or_save_snapshot(self):
        app = self.make_app()
        hw = app.add_hardware(self.module.Device(app, [], 1, name="device"))
        hw.settings["connected"] = True
        self.path.write_text("class Broken(\n", encoding="utf-8")
        with patch.object(app.profile_manager.history, "save_snapshot") as save:
            with self.assertRaises(SyntaxError):
                app.reload_hardware("device")
        save.assert_not_called()
        self.assertTrue(hw.is_connected)
        self.assertIs(app.hardware["device"], hw)
        hw.settings["connected"] = False

    def test_import_error_is_reported_in_context_menu(self):
        app = self.make_app()
        hw = app.add_hardware(self.module.Device(app, [], 1, name="device"))
        self.path.write_text("raise RuntimeError('import failed')\n", encoding="utf-8")
        with patch.object(QtWidgets.QMessageBox, "warning") as warning:
            app._reload_component_from_ui(hw, "hardware")
        self.assertIn("import failed", warning.call_args.args[2])
        self.assertIs(app.hardware["device"], hw)

    def test_measurement_snapshot_is_saved_after_stop(self):
        app = self.make_app(mdi=False)
        measure = app.add_measurement(self.module.Acquisition(app, 1, name="measure"))
        measure.start()
        history = app.profile_manager.history
        save = history.save_snapshot

        def capture(reason):
            self.assertFalse(measure.is_thread_alive())
            self.assertFalse(measure.is_measuring())
            return save(reason)

        self.write_source(2)
        with patch.object(history, "save_snapshot", side_effect=capture):
            replacement = app.reload_measurement("measure")
        self.assertFalse(replacement.is_measuring())

    def test_snapshot_failure_aborts_replacement(self):
        app = self.make_app()
        hw = app.add_hardware(self.module.Device(app, [], 1, name="device"))
        self.write_source(2)
        with patch.object(app.profile_manager.history, "save_snapshot", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "Could not save history snapshot"):
                app.reload_hardware("device")
        self.assertIs(app.hardware["device"], hw)
        self.assertIs(sys.modules[self.module_name], self.module)

    def test_history_restores_other_component_settings(self):
        app = self.make_app()
        hw = app.add_hardware(self.module.Device(app, [], 1, name="device"))
        other = app.add_hardware(self.module.Device(app, [], 2, name="other"))
        other.settings["level"] = 17
        add = app.add_hardware

        def add_after_change(component):
            other.settings["level"] = 91
            return add(component)

        self.write_source(2)
        with patch.object(app, "add_hardware", side_effect=add_after_change):
            app.reload_hardware(hw.name)
        self.assertEqual(other.settings["level"], 17)

    def test_public_methods_resolve_each_collection_by_name(self):
        app = self.make_app()
        hw = app.add_hardware(self.module.Device(app, [], 1, name="shared"))
        measure = app.add_measurement(
            self.module.Acquisition(app, 2, name="shared")
        )
        self.write_source(2)
        new_hw = app.reload_hardware("shared")
        self.assertIs(app.hardware["shared"], new_hw)
        self.assertIs(app.measurements["shared"], measure)
        new_measure = app.reload_measurement("shared")
        self.assertIs(app.measurements["shared"], new_measure)
        self.assertIs(app.hardware["shared"], new_hw)
        self.assertIsNot(new_hw, hw)
        with self.assertRaises(KeyError):
            app.reload_hardware("missing")
        with self.assertRaises(KeyError):
            app.reload_measurement("missing")

    def test_context_menus_call_kind_specific_public_methods(self):
        app = self.make_app(mdi=False)
        hw = app.add_hardware(self.module.Device(app, [], 1, name="device"))
        measure = app.add_measurement(self.module.Acquisition(app, 2, name="measure"))

        def trigger(menu, *_args):
            next(action for action in menu.actions() if action.text() == "Reload Component").trigger()

        with patch.object(app, "reload_hardware", return_value=hw) as reload_hw, \
             patch.object(app, "reload_measurement", return_value=measure) as reload_mm, \
             patch.object(QtWidgets.QMenu, "exec_", trigger), \
             patch("ScopeFoundry.hardware.init_docs_path"), \
             patch("ScopeFoundry.measurement.init_docs_path"), \
             patch("ScopeFoundry.hardware.itemize_launchers", return_value=[]), \
             patch("ScopeFoundry.measurement.itemize_launchers", return_value=[]):
            hw.on_right_click()
            measure.on_right_click()
        reload_hw.assert_called_once_with("device")
        reload_mm.assert_called_once_with("measure")

    def test_stale_menu_does_not_reload_new_instance(self):
        app = self.make_app()
        hw = app.add_hardware(self.module.Device(app, [], 1, name="device"))
        self.write_source(2)
        new = app.reload_hardware("device")
        with patch.object(QtWidgets.QMessageBox, "warning") as warning:
            with patch.object(app, "reload_hardware") as reload_hw:
                app._reload_component_from_ui(hw, "hardware")
        reload_hw.assert_not_called()
        warning.assert_called_once()
        self.assertIs(app.hardware["device"], new)

    def check_running_measurement(self, mdi):
        app = self.make_app(mdi)
        measure = app.add_measurement(self.module.Acquisition(app, 13, name="m"))
        measure.settings["level"] = 23
        measure.start()
        self.write_source(2)
        new = app.reload_measurement(measure.name)
        self.assertFalse(measure.is_thread_alive())
        self.assertFalse(new.is_measuring())
        self.assertEqual(new.factor, 13)
        self.assertEqual(new.settings["level"], 23)
        self.assertIs(app.measurements["m"], new)
        self.assertEqual(new.subwin is not None, mdi)

    def test_running_measurement_mdi(self):
        self.check_running_measurement(True)

    def test_running_measurement_non_mdi(self):
        self.check_running_measurement(False)

    def test_favorites_follow_replacement(self):
        app = self.make_app()
        events = []
        hw = app.add_hardware(self.module.Device(app, events, 1, name="device"))
        app.add_favorites(
            lq_paths=["hw/device/level"],
            lq_paths_lists=[["group", "hw/device/level"]],
            operation_paths=["hw/device/record"],
        )
        old = dict(app.favorites_widget._widgets)
        self.write_source(2)
        new = app.reload_hardware(hw.name)
        for key in old:
            self.assertIsNot(old[key], app.favorites_widget._widgets[key])
        button = app.favorites_widget._widgets["hw/device/record"].findChild(
            QtWidgets.QPushButton, "record"
        )
        button.click()
        self.assertIs(events[-1], new)

    def test_bad_source_and_failed_construction_keep_old_component(self):
        app = self.make_app()
        hw = app.add_hardware(self.module.Device(app, [], 1, name="device"))
        self.path.write_text("class Broken(\n", encoding="utf-8")
        with self.assertRaises(SyntaxError):
            app.reload_hardware(hw.name)
        self.assertIs(app.hardware["device"], hw)
        self.path.write_text(
            SOURCE.format(version=2).replace(
                "self.factor = factor", "raise RuntimeError('construction failed')", 1
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(RuntimeError, "construction failed"):
            app.reload_hardware(hw.name)
        self.assertIs(app.hardware["device"], hw)
        self.assertIs(sys.modules[self.module_name], self.module)

    def test_unstoppable_measurement_is_not_removed(self):
        app = self.make_app()
        measure = app.add_measurement(self.module.Acquisition(app, 1, name="measure"))

        class StuckThread:
            def isRunning(self):
                return True

            def wait(self, _timeout):
                return False

        measure.acq_thread = StuckThread()
        self.addCleanup(setattr, measure, "acq_thread", None)
        with self.assertRaisesRegex(RuntimeError, "did not stop"):
            app.reload_measurement(measure.name)
        self.assertIs(app.measurements["measure"], measure)

    def test_history_restoration_errors_are_reported(self):
        app = self.make_app()
        hw = app.add_hardware(self.module.Device(app, [], 1, name="device"))
        self.path.write_text(
            SOURCE.format(version=2).replace('"level", dtype=int', '"level", dtype=bool'),
            encoding="utf-8",
        )
        history = app.profile_manager.history
        with patch.object(history, "restore_snapshot", side_effect=RuntimeError("restore failed")):
            with self.assertRaisesRegex(RuntimeError, "restore failed"):
                app.reload_hardware(hw.name)

    def test_safe_main_and_custom_new(self):
        import ast
        _validate_main_body(ast.parse("class C: pass\nif __name__ == '__main__': start()\n").body, "launch.py")
        with self.assertRaisesRegex(ValueError, "safely reload"):
            _validate_main_body(ast.parse("app = start()\n").body, "launch.py")
        app = self.make_app()
        class Custom(self.module.Device):
            def __new__(cls, *args, **kwargs):
                return super().__new__(cls)
        hw = app.add_hardware(Custom(app, [], 1, name="device"))
        with self.assertRaisesRegex(TypeError, "overrides __new__"):
            app.reload_hardware(hw.name)
        self.assertIs(app.hardware["device"], hw)

    def test_guarded_main_module_reloads_without_running_startup(self):
        app = self.make_app()
        module = types.ModuleType("__main__")
        module.__file__ = str(self.path)
        exec(compile(SOURCE.format(version=1), str(self.path), "exec"), module.__dict__)
        with patch.dict(sys.modules, {"__main__": module}):
            hw = app.add_hardware(module.Device(app, [], 4, name="main_device"))
            self.path.write_text(
                SOURCE.format(version=2)
                + "\nif __name__ == '__main__':\n    raise RuntimeError('startup ran')\n",
                encoding="utf-8",
            )
            new = app.reload_hardware(hw.name)
            self.addCleanup(sys.modules.pop, type(new).__module__, None)
            self.assertEqual(sys.modules[type(new).__module__].VERSION, 2)
            self.assertEqual(new.factor, 4)


if __name__ == "__main__":
    unittest.main()
