import datetime
import json
import re
import shutil
from pathlib import Path

from functools import partial
from typing import Optional

from qtpy import QtGui, QtWidgets

from ScopeFoundry import ini_io


class StateHistory:
    max_entries = 40

    def __init__(self, app, history_dir: Path):
        self.app = app
        self.history_dir = Path(history_dir)
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self._prune()
        self.history_menu = None
        self.undo_action = None
        self.redo_action = None
        self._cursor = None  # entry name of the current state; None means latest
        self._restoring = False

    def setup_menu(self, menu_bar: QtWidgets.QMenuBar) -> None:
        self.history_menu = menu_bar.addMenu("History")
        self.history_menu.setToolTipsVisible(True)
        self.history_menu.aboutToShow.connect(self.refresh_menu)
        self.undo_action = menu_bar.addAction("Undo")
        self.undo_action.setIcon(
            self._blue_icon(QtWidgets.QStyle.StandardPixmap.SP_ArrowBack)
        )
        self.undo_action.triggered.connect(self.undo_latest)
        self.app.add_operation(
            "Undo",
            self.undo_latest,
            description="restores the previous state from the history",
            keyboard_shortcut="Ctrl+U",
        )
        self.redo_action = menu_bar.addAction("Forward")
        self.redo_action.setIcon(
            self._blue_icon(QtWidgets.QStyle.StandardPixmap.SP_ArrowForward)
        )
        self.redo_action.triggered.connect(self.redo_latest)
        self.app.add_operation(
            "Forward",
            self.redo_latest,
            description="re-applies the state that was undone",
            keyboard_shortcut="Ctrl+Y",
        )
        self.refresh_menu()

    def _blue_icon(self, standard_pixmap) -> QtGui.QIcon:
        background = self.app.ui.palette().color(QtGui.QPalette.ColorRole.Window)
        blue = "#0057B8" if background.lightness() > 127 else "#70BFFF"
        pixmap = self.app.ui.style().standardIcon(standard_pixmap).pixmap(32, 32)
        painter = QtGui.QPainter(pixmap)
        painter.setCompositionMode(
            QtGui.QPainter.CompositionMode.CompositionMode_SourceIn
        )
        painter.fillRect(pixmap.rect(), QtGui.QColor(blue))
        painter.end()
        return QtGui.QIcon(pixmap)

    def _entry_paths(self):
        entries = []
        if not self.history_dir.is_dir():
            return entries
        for entry_dir in self.history_dir.iterdir():
            metadata_path = entry_dir / "metadata.json"
            if not entry_dir.is_dir() or not metadata_path.is_file():
                continue
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            entries.append((metadata.get("timestamp", entry_dir.name), entry_dir))
        return sorted(entries)

    def _prune(self) -> None:
        entries = self._entry_paths()
        for _, entry_dir in entries[: -self.max_entries]:
            shutil.rmtree(entry_dir, ignore_errors=True)

    def save_snapshot(self, reason: str) -> Optional[Path]:
        if self._restoring:
            return None
        try:
            entry_dir = self._save_snapshot(reason)
            self._cursor = None
            self.refresh_menu()
            return entry_dir
        except Exception:
            self.app.log.exception("Could not save app history snapshot")
            return None

    def _save_snapshot(self, reason: str) -> Path:
        self.history_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.datetime.now().astimezone()
        entry_name = timestamp.strftime("%Y%m%d_%H%M%S_%f")
        entry_dir = self.history_dir / entry_name
        entry_dir.mkdir()

        setting_paths = [
            path
            for path in self.app.get_setting_paths()
            if not self.app.get_lq(path).ro
        ]
        settings = self.app.read_settings(setting_paths, ini_string_value=True)
        ini_io.save_settings(entry_dir / "settings.ini", settings)

        positions = (
            self.app.get_window_positions()
            if self.app.mdi
            else {"main": {"geometry": self.app.ui.geometry().getRect()}}
        )
        with open(entry_dir / "window_positions.json", "w") as outfile:
            json.dump(positions, outfile, indent=4)
        metadata = {"timestamp": timestamp.isoformat(), "reason": reason}
        with open(entry_dir / "metadata.json", "w", encoding="utf-8") as outfile:
            json.dump(metadata, outfile, indent=2)

        self._prune()
        self.refresh_menu()
        return entry_dir

    def refresh_menu(self) -> None:
        if self.history_menu is None:
            return
        self.history_menu.clear()
        entries = self._entry_paths()
        if self.undo_action is not None:
            idx = self._undo_index(entries)
            self.undo_action.setEnabled(idx > 0)
            hint = self._history_item_text(entries[idx - 1][1]) if idx > 0 else ""
            self.undo_action.setToolTip(
                f"Undo (Ctrl+U): restore {hint}" if hint else "Undo (nothing to undo)"
            )
            self.undo_action.setStatusTip(hint)
        if self.redo_action is not None:
            idx = self._undo_index(entries)
            has_next = idx < len(entries) - 1
            self.redo_action.setEnabled(has_next)
            hint = self._history_item_text(entries[idx + 1][1]) if has_next else ""
            self.redo_action.setToolTip(
                f"Forward (Ctrl+Y): restore {hint}"
                if hint
                else "Forward (nothing to redo)"
            )
            self.redo_action.setStatusTip(hint)
        current = self._undo_index(entries)
        for i, (_, entry_dir) in reversed(list(enumerate(entries))):
            action = self.history_menu.addAction(self._history_item_text(entry_dir))
            action.setCheckable(True)
            action.setToolTip(
                "Current state"
                if i == current
                else "Restore settings and window layout of this snapshot"
            )
            action.setChecked(i == current)
            action.setData(entry_dir.name)
            action.triggered.connect(
                partial(self._on_menu_entry_triggered, entry_dir.name)
            )
        if not entries:
            self.history_menu.addAction("No history yet").setEnabled(False)

    def _history_item_text(self, entry_dir: Path) -> str:
        metadata = json.loads((entry_dir / "metadata.json").read_text(encoding="utf-8"))
        timestamp = datetime.datetime.fromisoformat(metadata["timestamp"])
        return f"{timestamp:%Y-%m-%d %H:%M:%S}  {metadata['reason']}"

    def _undo_index(self, entries) -> int:
        for i, (_, entry_dir) in enumerate(entries):
            if entry_dir.name == self._cursor:
                return i
        return len(entries) - 1

    def undo_latest(self, checked: bool = False) -> None:
        entries = self._entry_paths()
        idx = self._undo_index(entries)
        if idx <= 0:
            return
        self.restore_snapshot(entries[idx - 1][1].name)

    def redo_latest(self, checked: bool = False) -> None:
        entries = self._entry_paths()
        idx = self._undo_index(entries)
        if idx >= len(entries) - 1:
            return
        self.restore_snapshot(entries[idx + 1][1].name)

    def _on_menu_entry_triggered(self, entry_name: str, checked: bool = False) -> None:
        self.restore_snapshot(entry_name, restore_window_positions=True)

    def restore_snapshot(
        self, entry_name: str, restore_window_positions: bool = False
    ) -> None:
        entry_dir = self.history_dir / entry_name
        settings_path = entry_dir / "settings.ini"
        if not settings_path.is_file():
            return
        self._restoring = True
        try:
            self.app.settings_load_ini(
                settings_path, ignore_hw_connect=False, show_report=False
            )
            positions_path = entry_dir / "window_positions.json"
            if restore_window_positions and positions_path.is_file():
                self.app.load_window_positions_json(positions_path)
        finally:
            self._restoring = False
        self._cursor = entry_name
        self.refresh_menu()

    def trim_history_dir(self) -> None:
        max_history = self.max_entries
        entries = sorted(self.history_dir.iterdir(), key=lambda p: p.name)
        for i, entry_dir in enumerate(entries):
            if i < len(entries) - max_history:
                shutil.rmtree(entry_dir)
