import json
import os
import stat
import tempfile
from functools import partial
from typing import Any, Dict

from qtpy import QtCore, QtWidgets

NEVER = "never"
MODERATE = "moderate"
STRICT = "strict"
SETTINGS_LOADING_REPORTING_OPTIONS = [NEVER, MODERATE, STRICT]
FILE_LOADING_OPTIONS = ("skip_protected_settings", "settings_loading_reporting")


class ConfigurationHandler(QtCore.QObject):
    """Manage .scopefoundry file-loading options and their persistent controls.

    The JSON keys ``skip_protected_settings`` and
    ``settings_loading_reporting`` default to true and ``moderate``. Reporting
    can also be ``never`` or ``strict``. These options are not profile settings.
    """

    skip_protected_settings_changed = QtCore.Signal(bool)
    settings_loading_reporting_changed = QtCore.Signal(str)

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.skip_protected_settings = True
        self.settings_loading_reporting = MODERATE
        self._load_file_loading_config()

    def _read_config(self) -> Dict[str, Any]:
        config = json.loads(self.app.microscope_config_path.read_text(encoding="utf-8"))
        if not isinstance(config, dict):
            raise ValueError("Microscope configuration must be a JSON object")
        return config

    def load_config(self) -> Dict[str, Any]:
        """Read configuration using the app's existing defaults if unavailable."""
        try:
            return self._read_config()
        except FileNotFoundError:
            return self._default_configs()
        except (OSError, ValueError) as error:
            self.app.log.error(
                "Could not load microscope configuration %s: %s",
                self.app.microscope_config_path,
                error,
            )
            return self._default_configs()

    @staticmethod
    def _default_configs() -> dict:
        return {
            "dynamic_components": [
                {
                    "source": "builtin",
                    "module": "ScopeFoundry.h5_analyze_with_ipynb.ipynb_analysis_measure",
                    "class_name": "IpynbAnalysisMeasurement",
                    "kind": "measurement",
                    "measurement_options": {
                        "initially_hidden": True,
                        "unhide_on_connection": None,
                    },
                }
            ],
            "setting_path_mappings": {
                "app/ipynb_option": "mm/ipynb_analysis/ipynb_option"
            },
        }

    def save_config(self, config: Dict[str, Any]) -> None:
        path = self.app.microscope_config_path
        path.parent.mkdir(parents=True, exist_ok=True)
        data = json.dumps(config, indent=2) + "\n"
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

    def _load_file_loading_config(self) -> None:
        try:
            config = self._read_config()
        except FileNotFoundError:
            return
        except (OSError, ValueError) as error:
            self.app.log.error(
                "Could not load microscope configuration %s: %s",
                self.app.microscope_config_path,
                error,
            )
            return
        for name in FILE_LOADING_OPTIONS:
            if name in config:
                try:
                    self._validate_file_loading_config(name, config[name])
                except ValueError as error:
                    self.app.log.error("Invalid microscope configuration: %s", error)
                else:
                    setattr(self, name, config[name])

    @staticmethod
    def _validate_file_loading_config(name: str, value: Any) -> None:
        if name == "skip_protected_settings":
            valid = isinstance(value, bool)
        elif name == "settings_loading_reporting":
            valid = (
                isinstance(value, str) and value in SETTINGS_LOADING_REPORTING_OPTIONS
            )
        else:
            raise ValueError(f"Unknown file loading configuration: {name}")
        if not valid:
            raise ValueError(f"Invalid value for {name}: {value!r}")

    def set_file_loading_config(self, name: str, value: Any) -> None:
        """Persist a file-loading option before applying it to the running app."""
        self._validate_file_loading_config(name, value)
        try:
            config = self._read_config()
        except FileNotFoundError:
            config = {}
        config[name] = value
        self.save_config(config)
        setattr(self, name, value)
        getattr(self, f"{name}_changed").emit(value)

    def _change_file_loading_config(self, name: str, value: Any) -> None:
        if value == getattr(self, name):
            return
        if name == "skip_protected_settings" and not value:
            answer = QtWidgets.QMessageBox.question(
                self.app.ui,
                "Enable protected setting writes?",
                "Loading a settings file can overwrite protected settings. "
                "This is discouraged. Enable this option?",
                QtWidgets.QMessageBox.StandardButton.Yes
                | QtWidgets.QMessageBox.StandardButton.No,
                QtWidgets.QMessageBox.StandardButton.No,
            )
            if answer != QtWidgets.QMessageBox.StandardButton.Yes:
                self.skip_protected_settings_changed.emit(self.skip_protected_settings)
                return
        try:
            self.set_file_loading_config(name, value)
        except (OSError, ValueError) as error:
            self.app.log.error("Could not save microscope configuration: %s", error)
            QtWidgets.QMessageBox.warning(
                self.app.ui, "Could not save microscope configuration", str(error)
            )
            getattr(self, f"{name}_changed").emit(getattr(self, name))

    def new_reporting_widget(self) -> QtWidgets.QComboBox:
        combo = QtWidgets.QComboBox()
        combo.addItems(SETTINGS_LOADING_REPORTING_OPTIONS)
        combo.setCurrentText(self.settings_loading_reporting)
        combo.currentTextChanged.connect(
            partial(self._change_file_loading_config, "settings_loading_reporting")
        )
        self.settings_loading_reporting_changed.connect(combo.setCurrentText)
        combo.setToolTip("Stored in the microscope's .scopefoundry file.")
        return combo

    def new_widget(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox("Loading settings from files")
        layout = QtWidgets.QFormLayout(group)
        protected = QtWidgets.QCheckBox()
        protected.setChecked(self.skip_protected_settings)
        protected.setToolTip(
            "Skip protected settings (🔒) when loading settings from files."
        )
        protected.toggled.connect(
            partial(self._change_file_loading_config, "skip_protected_settings")
        )
        self.skip_protected_settings_changed.connect(protected.setChecked)
        layout.addRow("Skip protected settings", protected)
        reporting = self.new_reporting_widget()
        reporting.setToolTip("""<b>Never:</b> never show a report. 
            <b>Moderate:</b> skip missing components and use saved mappings and ignores.<br> 
            <b>Strict:</b> report all missing settings.""")
        layout.addRow("reporting model", reporting)
        return group
