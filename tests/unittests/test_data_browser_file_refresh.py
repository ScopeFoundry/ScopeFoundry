import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qtpy import QtCore, QtWidgets

from ScopeFoundry.data_browser import DataBrowser


def _pump_events(qtapp, duration=0.35):
    deadline = time.monotonic() + duration
    while time.monotonic() < deadline:
        qtapp.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 20)
        time.sleep(0.01)


def _wait_until(qtapp, predicate, timeout=3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        qtapp.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 20)
        if predicate():
            return True
        time.sleep(0.02)
    return predicate()


class TestDataBrowserFileRefresh(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root_dir = Path(self.tmp.name)
        self.sub_dir = self.root_dir / "sub"
        self.sub_dir.mkdir()
        (self.root_dir / "initial.txt").write_text("hello")
        (self.sub_dir / "sub_initial.txt").write_text("sub")

        with patch.object(sys, "argv", ["test"]):
            self.app = DataBrowser(["test"])
        # Disable Qt's OS file watcher to deterministically simulate network / WSL / FUSE mounts
        self.app.fs_model.setOption(
            QtWidgets.QFileSystemModel.Option.DontWatchForChanges, True
        )
        self.app.settings["auto_refresh_interval"] = 0.15
        self.app.settings["browse_dir"] = str(self.root_dir)
        _pump_events(self.app.qtapp, 0.35)

    def tearDown(self):
        self.app._stop_file_refresh()
        self.app.tree_view.setModel(None)
        self.app.fs_model.deleteLater()
        self.app.ui.close()
        self.app.ui.deleteLater()
        _pump_events(self.app.qtapp, 0.1)
        self.tmp.cleanup()

    def _entry_names(self, folder_path: Path):
        idx = self.app.fs_model.index(str(folder_path))
        return {
            self.app.fs_model.fileName(self.app.fs_model.index(r, 0, idx))
            for r in range(self.app.fs_model.rowCount(idx))
        }

    def test_auto_refresh_detects_new_and_deleted_root_files(self):
        self.assertIn("initial.txt", self._entry_names(self.root_dir))

        added = self.root_dir / "newly_added.txt"
        added.write_text("new file")
        self.assertTrue(
            _wait_until(
                self.app.qtapp,
                lambda: "newly_added.txt" in self._entry_names(self.root_dir),
            ),
            "Auto-refresh did not pick up newly added file in root directory",
        )

        added.unlink()
        self.assertTrue(
            _wait_until(
                self.app.qtapp,
                lambda: "newly_added.txt" not in self._entry_names(self.root_dir),
            ),
            "Auto-refresh did not remove deleted file from root directory",
        )

    def test_auto_refresh_updates_expanded_subdirectory_without_collapsing(self):
        sub_idx = self.app.fs_model.index(str(self.sub_dir))
        self.app.tree_view.expand(sub_idx)
        _pump_events(self.app.qtapp, 0.35)
        self.assertTrue(self.app.tree_view.isExpanded(sub_idx))
        self.assertIn("sub_initial.txt", self._entry_names(self.sub_dir))

        sub_added = self.sub_dir / "sub_new.txt"
        sub_added.write_text("sub new")
        self.assertTrue(
            _wait_until(
                self.app.qtapp,
                lambda: "sub_new.txt" in self._entry_names(self.sub_dir),
            ),
            "Auto-refresh did not pick up newly added file in expanded subdirectory",
        )
        self.assertTrue(
            self.app.tree_view.isExpanded(self.app.fs_model.index(str(self.sub_dir)))
        )

        sub_added.unlink()
        self.assertTrue(
            _wait_until(
                self.app.qtapp,
                lambda: "sub_new.txt" not in self._entry_names(self.sub_dir),
            ),
            "Auto-refresh did not remove deleted file in expanded subdirectory",
        )
        self.assertTrue(
            self.app.tree_view.isExpanded(self.app.fs_model.index(str(self.sub_dir)))
        )

    def test_refresh_preserves_selection_without_reloading_file(self):
        initial_path = self.root_dir / "initial.txt"
        idx = self.app.fs_model.index(str(initial_path))
        self.app.tree_view.setCurrentIndex(idx)
        _pump_events(self.app.qtapp, 0.25)
        self.assertEqual(Path(self.app.settings["data_filename"]), initial_path)

        spy = MagicMock(wraps=self.app.current_view.on_change_data_filename)
        self.app.current_view.on_change_data_filename = spy

        (self.root_dir / "another.txt").write_text("another")
        self.assertTrue(
            _wait_until(
                self.app.qtapp,
                lambda: "another.txt" in self._entry_names(self.root_dir),
            )
        )

        self.assertEqual(
            self.app.fs_model.fileName(self.app.tree_view.currentIndex()),
            "initial.txt",
        )
        spy.assert_not_called()

    def test_manual_refresh_and_disable_polling(self):
        self.app.settings["auto_refresh_interval"] = 0.0
        self.assertFalse(self.app._refresh_timer.isActive())

        manual_file = self.root_dir / "manual_only.txt"
        manual_file.write_text("manual")
        _pump_events(self.app.qtapp, 0.4)
        self.assertNotIn("manual_only.txt", self._entry_names(self.root_dir))

        # Trigger via Refresh button
        self.app.ui.browse_dir_refresh_pushButton.click()
        self.assertTrue(
            _wait_until(
                self.app.qtapp,
                lambda: "manual_only.txt" in self._entry_names(self.root_dir),
            ),
            "Manual Refresh button did not update file list",
        )


if __name__ == "__main__":
    unittest.main()
