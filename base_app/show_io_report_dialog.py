from os import startfile
from pathlib import Path

from qtpy import QtWidgets

from .base_app import WRITE_RES


def show_io_report_dialog(fname: str, report, retry_func):

    failures = [f" - `{p}`" for p, v in report.items() if v == WRITE_RES.MISSING]
    protecteds = [f" - `{p}`" for p, v in report.items() if v == WRITE_RES.PROTECTED]
    successes = [f" - `{p}`" for p, v in report.items() if v is WRITE_RES.SUCCESS]

    name = Path(fname).name

    if not failures:
        if protecteds:
            print(f"{name} has protected settings that were not updated:")
            for p in protecteds:
                print(p)
        return

    lines = [f"### failed ({len(failures)})", "*check typos*", " "] + failures

    if protecteds:
        lines += [
            "  ",
            "  ",
            f"### protected ({len(protecteds)})",
            "*`protected` settings can not be update by a file*",
            "  ",
        ]
        lines += protecteds

    if successes:
        lines += ["  ", "  ", f"### sucesses ({len(successes)})"]
        lines += successes

    text_edit = QtWidgets.QTextEdit()
    text_edit.setMarkdown("\n".join(lines))

    dialog = QtWidgets.QDialog()
    dialog.setWindowTitle(f"{name} failed to update ({len(failures)})")
    layout = QtWidgets.QVBoxLayout()
    dialog.setLayout(layout)
    layout.addWidget(text_edit)

    if name.endswith(".ini"):

        def on_fix():
            startfile(fname)

        btn = QtWidgets.QPushButton("fix")
        btn.clicked.connect(on_fix)
        layout.addWidget(btn)

        def on_retry():
            dialog.close()
            retry_func(fname)

        btn = QtWidgets.QPushButton("retry")
        btn.clicked.connect(on_retry)
        layout.addWidget(btn)

    btn = QtWidgets.QPushButton(f"close")
    btn.clicked.connect(dialog.close)
    layout.addWidget(btn)

    dialog.exec_()
