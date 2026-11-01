from pathlib import Path
from typing import Dict, List, Optional, Tuple

from qtpy import QtWidgets

from .base_app import WRITE_RES, get_missing_component
from .. import ini_io
from ..helper_funcs import open_file
from ..widgets import QSearchableComboBox

IGNORE = "ignore"
IGNORE_ALWAYS = "ignore_always"
REPLACE = "replace"
REMOVE = "remove"
MAP = "map"
NEVER = "never"
MODERATE = "moderate"
STRICT = "strict"
SETTINGS_LOADING_REPORTING_OPTIONS = [NEVER, MODERATE, STRICT]
OPTION_LABELS = {
    IGNORE: "Ignore now",
    IGNORE_ALWAYS: "Ignore now and in future",
    REPLACE: "Replace in file",
    REMOVE: "Remove in file",
    MAP: "Map to",
}


def collect_resolve_actions(rows):
    """rows: iterable of (missing_path, option, target). Returns the actions
    for every row: {missing_path: (option, target)}; incomplete rows count as ignore."""
    actions = {}
    for path, option, target in rows:
        if option in (REMOVE, IGNORE_ALWAYS):
            actions[path] = (option, None)
        elif option in (REPLACE, MAP) and target:
            actions[path] = (option, target)
        else:
            actions[path] = (IGNORE, None)
    return actions


class _ConflictTable(QtWidgets.QTableWidget):
    def __init__(self, missing, all_paths, mutable, mappings, ignored=()):
        super().__init__(len(missing), 2)
        self.missing = list(missing)
        self.options = (
            [IGNORE, IGNORE_ALWAYS, REPLACE, REMOVE, MAP]
            if mutable
            else [IGNORE, IGNORE_ALWAYS, MAP]
        )
        self.setHorizontalHeaderLabels(["missing setting", "resolution"])
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(
            0, QtWidgets.QHeaderView.ResizeToContents
        )
        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._combos = []
        self._searches = []
        for row, path in enumerate(self.missing):
            self.setItem(row, 0, QtWidgets.QTableWidgetItem(path))
            cell = QtWidgets.QWidget()
            lay = QtWidgets.QHBoxLayout(cell)
            lay.setContentsMargins(2, 2, 2, 2)
            combo = QtWidgets.QComboBox()
            for opt in self.options:
                combo.addItem(OPTION_LABELS[opt], opt)
            search = QSearchableComboBox()
            search.addItems(all_paths)
            search.setCurrentIndex(-1)
            search.setVisible(False)
            combo.currentIndexChanged.connect(
                lambda _i, c=combo, s=search: s.setVisible(
                    c.currentData() in (REPLACE, MAP)
                )
            )
            lay.addWidget(combo)
            lay.addWidget(search, 1)
            self.setCellWidget(row, 1, cell)
            self._combos.append(combo)
            self._searches.append(search)

            proposal = mappings.get(path)
            if path in ignored:
                combo.setCurrentIndex(combo.findData(IGNORE_ALWAYS))
            elif proposal in all_paths:
                combo.setCurrentIndex(combo.findData(MAP))
                search.setCurrentText(proposal)
        self.resizeRowsToContents()

    def rows(self):
        return [
            (path, combo.currentData(), search.currentText())
            for path, combo, search in zip(self.missing, self._combos, self._searches)
        ]


def get_ignored_missing_settings(app) -> List[str]:
    """paths that are never reported as missing, remembered in the .scopefoundry file"""
    ignored = app.load_microscope_config().get("ignored_missing_settings", [])
    return ignored if isinstance(ignored, list) else []


def get_setting_path_mappings(app) -> Dict[str, str]:
    """old path -> new path, remembered in the .scopefoundry file"""
    mappings = app.load_microscope_config().get("setting_path_mappings", {})
    return mappings if isinstance(mappings, dict) else {}


def resolve_missing_settings(
    app, fname: str, actions: Dict[str, Tuple[str, str]]
) -> None:
    """actions: {missing_path: ("replace" | "map" | "remove", target_path)}.
    The file values are written to the targets, "replace" also renames the keys
    in the (mutable) .ini file. Used mappings are stored in the .scopefoundry file."""
    settings = app.read_settings_file(fname)
    targets = {o: t for o, (opt, t) in actions.items() if opt in (REPLACE, MAP)}
    to_write = {t: settings[o] for o, t in targets.items() if o in settings}
    app.write_settings_safe(to_write)

    if Path(fname).suffix.lower() == ".ini":
        renames = {o: t for o, (opt, t) in actions.items() if opt == REPLACE}
        removed = {o for o, (opt, _t) in actions.items() if opt == REMOVE}
        if renames or removed:
            ini_io.save_settings(
                fname,
                {renames.get(k, k): v for k, v in settings.items() if k not in removed},
            )

    # the config reflects the choices: every resolved path is dropped from the
    # stored mappings/ignores first, then re-added according to its option
    ignore_always = [o for o, (opt, _t) in actions.items() if opt == IGNORE_ALWAYS]
    if actions:
        config = app.load_microscope_config()
        mappings = config.get("setting_path_mappings", {})
        if not isinstance(mappings, dict):
            mappings = {}
        mappings = {k: v for k, v in mappings.items() if k not in actions}
        mappings.update(targets)
        config["setting_path_mappings"] = mappings
        ignored = [p for p in get_ignored_missing_settings(app) if p not in actions]
        config["ignored_missing_settings"] = ignored + ignore_always
        app.save_microscope_config(config)
    app.log.info(f"resolved {len(actions)} missing settings of {fname}")


def remove_missing_from_ini(app, fname: str, missing_paths) -> None:
    missing = set(missing_paths)
    settings = ini_io.load_settings(fname)
    ini_io.save_settings(fname, {k: v for k, v in settings.items() if k not in missing})
    app.log.info(f"removed {len(missing)} missing settings from {fname}")


def apply_known_mappings(app, fname: str, missing_paths) -> bool:
    """Quietly writes the file values of missing paths to their stored mapping targets.
    Returns False (and writes nothing) unless every path has a registered target."""
    mappings = get_setting_path_mappings(app)
    targets = {p: mappings.get(p) for p in missing_paths}
    if not all(t and app.get_lq(t) is not None for t in targets.values()):
        return False
    settings = app.read_settings_file(fname)
    app.write_settings_safe(
        {t: settings[p] for p, t in targets.items() if p in settings}
    )
    app.log.info(f"applied {len(targets)} stored setting mappings for {fname}")
    return True


def show_io_report_dialog(fname: str, report, retry_func, error_msgs, app):

    reporting = app.settings["settings_loading_reporting"]
    if reporting == NEVER:
        return

    strict = reporting == STRICT
    ignored = set() if strict else set(get_ignored_missing_settings(app))
    missing_due_to_other_reasons = [
        p for p, v in report.items() if v == WRITE_RES.MISSING and p not in ignored
    ]
    missing_due_to_missing_components = [
        p
        for p, v in report.items()
        if v == WRITE_RES.MISSING_COMPONENT and p not in ignored
    ]
    missing_components = []
    for p in missing_due_to_missing_components:
        component = get_missing_component(app, p)
        if component not in missing_components:
            missing_components.append(component)

    if missing_components:
        app.log.info(
            f"{Path(fname).name}: settings of missing components: "
            + ", ".join(missing_components)
        )
    if not strict:
        missing_components = []
        missing_due_to_missing_components = []

        if missing_due_to_other_reasons and apply_known_mappings(
            app, fname, missing_due_to_other_reasons
        ):
            missing_due_to_other_reasons = []

    missing_paths = missing_due_to_other_reasons
    failures = [f" - `{p}`" for p in missing_paths + missing_due_to_missing_components]
    protecteds = [f" - `{p}`" for p, v in report.items() if v == WRITE_RES.PROTECTED]
    successes = [f" - `{p}`" for p, v in report.items() if v is WRITE_RES.SUCCESS]
    errors = [
        f" - `{p}`\n  {error_msgs.get(p, '')}"
        for p, v in report.items()
        if v == WRITE_RES.ERROR
    ]

    name = Path(fname).name

    if not failures:
        if protecteds:
            print(f"{name} has protected settings that were not updated:")
            for p in protecteds:
                print(p)
        return

    lines = []
    if missing_components:
        lines += [
            f"### MISSING Components ({len(missing_components)})",
            "*these hardware/measurements are not present, their settings were not loaded*",
            "  ",
        ]
        for c in missing_components:
            lines += [f" - `{c}`"]
            lines += [
                f"   - `{p}`"
                for p in missing_due_to_missing_components
                if get_missing_component(app, p) == c
            ]
        lines += ["  "]
    if protecteds:
        lines += [
            f"### protected ({len(protecteds)})",
            "*`protected` are only updated if allowed by app/file_loading_write_protected (DISCOURAGED by default) *",
            "  ",
        ]
        lines += protecteds

    if successes:
        lines += ["  ", "  ", f"### sucesses ({len(successes)})"]
        lines += successes

    if errors:
        lines += [
            "  ",
            "  ",
            f"### errors ({len(errors)})",
            "*errors occurred while trying to write these settings*",
            "  ",
        ]
        lines += errors

    mutable = name.lower().endswith(".ini")
    table = _ConflictTable(
        missing_paths,
        sorted(app._setting_paths),
        mutable,
        get_setting_path_mappings(app),
        get_ignored_missing_settings(app),
    )

    dialog = QtWidgets.QDialog()
    dialog.setWindowTitle(f"{name} failed to update ({len(failures)})")
    dialog.resize(900, 900)
    layout = QtWidgets.QVBoxLayout(dialog)
    layout.addWidget(
        QtWidgets.QLabel(f"<b>missing settings ({len(missing_paths)})</b>")
    )
    table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
    table_height = (
        table.horizontalHeader().height()
        + sum(table.rowHeight(i) for i in range(table.rowCount()))
        + 2 * table.frameWidth()
        + 4
    )
    table.setFixedHeight(min(table_height, 300))
    layout.addWidget(table)

    if lines:
        text_edit = QtWidgets.QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setMarkdown("\n".join(lines))
        layout.addWidget(text_edit, 1)
    else:
        layout.addStretch(1)

    buttons = QtWidgets.QHBoxLayout()
    layout.addLayout(buttons)

    reporting_lq = app.settings.get_lq("settings_loading_reporting")
    buttons.addWidget(QtWidgets.QLabel("settings loading reporting"))
    buttons.addWidget(reporting_lq.new_default_widget())
    buttons.addStretch(1)

    def add_button(text, func, style=None):
        btn = QtWidgets.QPushButton(text)
        if style:
            btn.setStyleSheet(style)
        btn.clicked.connect(func)
        buttons.addWidget(btn)
        return btn

    add_button("Ignore all", dialog.close)

    if mutable:

        def on_remove():
            dialog.close()
            remove_missing_from_ini(app, fname, missing_paths)

        add_button(
            "Remove all Missing from file",
            on_remove,
            "background-color: #c62828; color: white;",
        )

    def on_apply_resolution():
        actions = collect_resolve_actions(table.rows())
        dialog.close()
        if actions:
            resolve_missing_settings(app, fname, actions)

    add_button("Apply resolutions", on_apply_resolution, "background-color: green;")

    if mutable:
        add_button("Open", lambda: open_file(fname))

    dialog.exec_()
