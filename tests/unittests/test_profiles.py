import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from qtpy import QtCore, QtTest, QtWidgets

from ScopeFoundry import BaseMicroscopeApp, ini_io
from ScopeFoundry.base_app.profile_manager import ProfileManager
from ScopeFoundry.base_app.state_history import StateHistory
from ScopeFoundry.tests.unittests.test_settings_io import Hardware1, Measure1
from ScopeFoundry.tests.unittests.unittest_helpers import close_app_widgets


class ProfileTest(unittest.TestCase):

    def setUp(self):
        self._app_implementation_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._app_implementation_dir.cleanup)
        implementation_dir_patch = patch.object(
            ProfileManager,
            "_app_implementation_dir",
            return_value=Path(self._app_implementation_dir.name),
        )
        implementation_dir_patch.start()
        self.addCleanup(implementation_dir_patch.stop)
        self.app = BaseMicroscopeApp([])
        self.addCleanup(close_app_widgets, self.app)
        self.ms = self.app.add_measurement(Measure1(self.app))
        self.hw = self.app.add_hardware(Hardware1(self.app))

        self.mms = self.ms.settings
        self.hws = self.hw.settings

    def test_profile_saves_selected_components_and_window_positions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.app.profile_manager.profiles_dir = Path(temp_dir)
            self.app.settings["sample"] = "not saved"
            self.hws["float"] = 2.0
            self.hws["choices"] = 1
            self.mms["float"] = 3.0

            self.app.profile_manager.save_profile(
                "test profile",
                setting_paths=["hw/hardware1/choices", "hw/hardware1/float"],
            )

            profile_dir = Path(temp_dir) / "test profile"
            self.assertTrue((profile_dir / "settings.ini").is_file())
            self.assertTrue((profile_dir / "window_positions.json").is_file())
            window_positions = json.loads(
                (profile_dir / "window_positions.json").read_text(encoding="utf-8")
            )
            self.assertIn("fullscreen", window_positions["main"])
            self.hws["float"] = 4.0
            self.hws["choices"] = 3
            self.mms["float"] = 5.0
            self.app.settings["sample"] = "changed"

            self.app.profile_manager.load_profile("test profile")

            self.assertEqual(self.hws["float"], 4.0)
            self.assertEqual(self.hws["choices"], 1)
            self.assertEqual(self.mms["float"], 5.0)
            self.assertEqual(self.app.settings["sample"], "changed")

    def test_startup_profile_is_persistent_and_independent_of_last_selection(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = self.app.profile_manager
            manager.profiles_dir = Path(temp_dir) / "profiles"
            config_path = Path(temp_dir) / "app" / "test.scopefoundry"
            manager.save_profile(
                "startup choice", setting_paths=[], select_profile=False
            )
            manager.save_profile("last loaded", setting_paths=[], select_profile=False)

            with patch.object(self.app, "microscope_config_path", config_path):
                manager._set_startup_profile("startup choice")
                manager._set_selected_profile("last loaded")

                self.assertEqual(
                    json.loads(config_path.read_text(encoding="utf-8"))[
                        "startup_profile"
                    ],
                    "startup choice",
                )
                self.assertEqual(manager._read_startup_profile(), "startup choice")
                with patch.object(manager, "load_profile") as load_profile:
                    manager.initialize_startup_profile()
            load_profile.assert_called_once_with("startup choice")

    def test_profile_settings_tree_cascades_component_checks(self):
        tree, components, settings = self.app.profile_manager._make_settings_tree(
            "measure1"
        )
        hardware_item = components["hw/hardware1"]
        measurement_item = components["mm/measure1"]

        self.assertEqual(hardware_item.checkState(0).value, 0)
        self.assertEqual(measurement_item.checkState(0).value, 2)
        self.assertFalse(hardware_item.isExpanded())
        self.assertTrue(measurement_item.isExpanded())
        self.assertTrue(
            all(
                item.checkState(0).value == 2
                for path, item in settings.items()
                if path.startswith("mm/measure1/") and not item.isDisabled()
            )
        )
        for path in ("mm/measure1/string", "mm/measure1/float"):
            self.assertTrue(settings[path].isDisabled())
            self.assertEqual(settings[path].checkState(0).value, 0)

        hardware_item.setCheckState(0, hardware_item.checkState(0).Checked)
        self.assertTrue(
            all(
                item.checkState(0).value == 2
                for path, item in settings.items()
                if path.startswith("hw/hardware1/") and not item.isDisabled()
            )
        )
        for path in ("hw/hardware1/string", "hw/hardware1/float"):
            self.assertTrue(settings[path].isDisabled())
            self.assertEqual(settings[path].checkState(0).value, 0)

        settings["hw/hardware1/choices"].setCheckState(
            0, settings["hw/hardware1/choices"].checkState(0).Unchecked
        )
        self.assertEqual(hardware_item.checkState(0).value, 1)

    def test_update_selected_profile_preserves_settings_subset(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.app.profile_manager.profiles_dir = Path(temp_dir)
            self.hws["choices"] = 1
            self.hws["float"] = 2.0
            self.app.profile_manager.save_profile(
                "selected profile", setting_paths=["hw/hardware1/choices"]
            )

            self.assertEqual(
                self.app.profile_manager.selected_profile_name, "selected profile"
            )
            self.assertEqual(
                self.app.profile_manager._read_selected_profile(), "selected profile"
            )
            self.hws["choices"] = 2
            self.hws["float"] = 3.0
            self.app.profile_manager.update_selected_profile()

            profile_settings = ini_io.load_settings(
                Path(temp_dir) / "selected profile" / "settings.ini"
            )
            self.assertEqual(list(profile_settings), ["hw/hardware1/choices"])
            self.hws["choices"] = 3
            self.app.profile_manager.load_profile("selected profile")
            self.assertEqual(self.hws["choices"], 2)
            self.assertEqual(self.hws["float"], 3.0)

    def test_delete_selected_profile_clears_saved_selection(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.app.profile_manager.profiles_dir = Path(temp_dir)
            self.app.profile_manager.save_profile("selected profile", setting_paths=[])

            with patch(
                "ScopeFoundry.base_app.base_microscope_app.QtWidgets.QMessageBox.question",
                return_value=QtWidgets.QMessageBox.StandardButton.Yes,
            ):
                self.app.profile_manager.delete_selected_profile()

            self.assertFalse((Path(temp_dir) / "selected profile").exists())
            self.assertFalse((Path(temp_dir) / ".last_selected_profile").exists())
            self.assertEqual(self.app.profile_manager.selected_profile_name, "")

    def test_profile_editor_saves_window_layout_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = self.app.profile_manager
            manager.profiles_dir = Path(temp_dir)
            manager.save_profile("p", setting_paths=[])
            self.assertEqual(
                manager._read_profile_metadata("p"),
                {
                    "load_window_positions": True,
                    "adjust_main_window_size": False,
                    "favorite": False,
                },
            )

            manager.edit_profiles_dialog()
            editor = manager._profile_editor
            self.addCleanup(editor.deleteLater)
            checkboxes = {
                box.text(): box for box in editor.findChildren(QtWidgets.QCheckBox)
            }
            adjust = checkboxes["Adjust size of the main window"]
            self.assertFalse(
                adjust.isEnabled()
                and not checkboxes["Load window positions"].isChecked()
            )
            adjust.setChecked(True)
            save = next(
                b
                for b in editor.findChildren(QtWidgets.QPushButton)
                if b.text() == "Save"
            )
            save.click()

            self.assertEqual(
                manager._read_profile_metadata("p"),
                {
                    "load_window_positions": True,
                    "adjust_main_window_size": True,
                    "favorite": False,
                },
            )
            editor.can_close = lambda: True
            editor.close()

    def test_new_profile_menu_selects_connected_hardware_and_measurement(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = self.app.profile_manager
            manager.profiles_dir = Path(temp_dir)
            manager.save_profile("existing", setting_paths=[])
            with patch.object(self.hw, "connect"):
                self.hws["connected"] = True
            self.assertTrue(self.hws["connected"])
            self.hws["choices"] = 2
            with patch.object(
                manager, "_selected_measurement_name", return_value="measure1"
            ):
                manager.refresh_menu()
                action = next(
                    a
                    for a in manager.profile_menu.actions()
                    if a.text() == "New profile..."
                )
                action.trigger()
            editor = manager._profile_editor
            self.addCleanup(editor.deleteLater)
            editor.can_close = lambda: True

            tree = editor.findChild(QtWidgets.QTreeWidget)
            items = {}
            iterator = QtWidgets.QTreeWidgetItemIterator(tree)
            while iterator.value():
                item = iterator.value()
                path = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
                if path:
                    items[path] = item
                iterator += 1
            checked = QtCore.Qt.CheckState.Checked
            choices = items["hw/hardware1/choices"]
            self.assertEqual(choices.checkState(0), checked)
            self.assertEqual(choices.text(2), "2")
            self.assertTrue(choices.parent().isExpanded())
            measure_item = items["mm/measure1/choices"]
            self.assertEqual(measure_item.checkState(0), checked)
            self.assertTrue(measure_item.parent().isExpanded())
            self.assertEqual(
                items["app/sample"].checkState(0), QtCore.Qt.CheckState.Unchecked
            )
            editor.close()

    def test_favorite_profile_gets_menu_bar_button(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = self.app.profile_manager
            manager.profiles_dir = Path(temp_dir)
            manager.save_profile("fav", setting_paths=[])
            manager.save_profile("plain", setting_paths=[])
            manager.refresh_menu()
            bar = self.app.ui.menubar

            def texts():
                return [a.text() for a in manager._favorite_actions]

            self.assertEqual(texts(), [])

            manager.edit_profiles_dialog()
            editor = manager._profile_editor
            self.addCleanup(editor.deleteLater)
            editor.can_close = lambda: True
            selector = editor.findChild(QtWidgets.QComboBox)
            selector.setCurrentText("fav")
            favorite = next(
                b
                for b in editor.findChildren(QtWidgets.QCheckBox)
                if b.text() == "Show as button in the menu bar"
            )
            favorite.setChecked(True)
            next(
                b
                for b in editor.findChildren(QtWidgets.QPushButton)
                if b.text() == "Save"
            ).click()

            self.assertEqual(texts(), ["fav"])
            actions = bar.actions()
            fav_action = manager._favorite_actions[0]
            self.assertEqual(
                actions.index(fav_action),
                actions.index(manager.history.redo_action) + 1,
            )
            QtWidgets.QApplication.processEvents()
            geometry = bar.actionGeometry(fav_action)
            self.assertGreater(geometry.width(), 0)
            self.assertGreaterEqual(
                geometry.left(), bar.actionGeometry(manager.history.redo_action).right()
            )
            self.hws["choices"] = 1
            manager.save_profile("fav", setting_paths=["hw/hardware1/choices"])
            self.hws["choices"] = 3
            fav_action.trigger()
            self.assertEqual(self.hws["choices"], 1)
            editor.close()

    def test_history_restores_state_and_retains_configured_limit(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            history = self.app.profile_manager.history
            history.history_dir = Path(temp_dir) / "history"
            self.hws["choices"] = 1
            first_entry = history.save_snapshot("checkpoint")
            self.hws["choices"] = 2
            history.restore_snapshot(first_entry.name)
            self.assertEqual(self.hws["choices"], 1)

            for index in range(history.max_entries + 1):
                self.hws["choices"] = index % 4
                history.save_snapshot(f"checkpoint {index}")
            self.assertEqual(len(history._entry_paths()), history.max_entries)
            reloaded_history = StateHistory(self.app, history.history_dir)
            self.assertEqual(len(reloaded_history._entry_paths()), history.max_entries)

    def test_history_menu_item_restores_snapshot(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            history = self.app.profile_manager.history
            history.history_dir = Path(temp_dir) / "history"
            self.hws["choices"] = 1
            entry = history.save_snapshot("menu checkpoint")
            self.hws["choices"] = 3

            history.refresh_menu()
            history_action = next(
                action
                for action in history.history_menu.actions()
                if action.data() == entry.name
            )
            history_action.trigger()

            self.assertEqual(self.hws["choices"], 1)

    def _make_undoable_change(self):
        history = self.app.profile_manager.history
        initial_value = self.app.settings["sample"]
        history.save_snapshot("baseline")
        self.app.settings["sample"] = "changed"
        history.save_snapshot("sample changed")
        self.assertTrue(history.undo_action.isEnabled())
        return initial_value

    def test_undo_and_forward_operations_register_shortcuts(self):
        self.assertEqual(self.app.operations.get("Undo").keyboard_shortcut, "Ctrl+U")
        self.assertEqual(self.app.operations.get("Forward").keyboard_shortcut, "Ctrl+Y")
        initial_value = self._make_undoable_change()

        self.app.operations["Undo"]()
        self.assertEqual(self.app.settings["sample"], initial_value)
        self.app.operations["Forward"]()
        self.assertEqual(self.app.settings["sample"], "changed")

    def test_focused_text_widget_keeps_ctrl_z(self):
        self._make_undoable_change()
        editor = QtWidgets.QLineEdit(self.app.ui)
        self.addCleanup(editor.deleteLater)
        editor.setText("editor text")
        editor.show()
        editor.setFocus()
        self.app.ui.activateWindow()
        QtWidgets.QApplication.processEvents()
        QtTest.QTest.keyClicks(editor, "!")
        QtTest.QTest.keyClick(
            editor,
            QtCore.Qt.Key.Key_Z,
            QtCore.Qt.KeyboardModifier.ControlModifier,
        )

        self.assertEqual(self.app.settings["sample"], "changed")

    def test_nested_measurement_start_skips_history(self):
        history = self.app.profile_manager.history
        nested = self.app.measurements["measure1"]
        with (
            patch.object(nested, "_start") as start_measurement,
            patch.object(nested, "is_measuring", side_effect=[True, False]),
            patch.object(history, "save_snapshot") as save_snapshot,
        ):
            self.ms.start_nested_measure_and_wait(nested)

        start_measurement.assert_called_once_with()
        save_snapshot.assert_not_called()

    def test_settings_autosave_records_history(self):
        history = self.app.profile_manager.history
        with (
            patch.object(self.app, "settings_save_ini") as save_settings,
            patch.object(history, "save_snapshot") as save_snapshot,
        ):
            self.app.settings_auto_save_ini()

        save_settings.assert_called_once()
        save_snapshot.assert_called_once_with("Settings autosaved")

    def test_app_close_records_history_before_disconnect(self):
        history = self.app.profile_manager.history
        with (
            patch.object(history, "save_snapshot") as save_snapshot,
            patch.object(
                self.hw.settings, "disconnect_all_from_hardware"
            ) as disconnect,
        ):
            self.app.on_close()

        save_snapshot.assert_called_once_with("Application closing")
        disconnect.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
