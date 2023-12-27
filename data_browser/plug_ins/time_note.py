import datetime
from pathlib import Path
from qtpy import QtCore, QtWidgets

from ScopeFoundry.data_browser.plug_in import DataBrowserPlugin


class TimeNote(DataBrowserPlugin):
    name = "time_note"
    button_text = "🕑Note"
    show_keyboard_key = QtCore.Qt.Key_N

    def setup(self):
        self.subject_line = QtWidgets.QLineEdit()

        subj_layout = QtWidgets.QHBoxLayout()
        subj_layout.addWidget(QtWidgets.QLabel("subject"))
        subj_layout.addWidget(self.subject_line)

        self.text_edit = QtWidgets.QTextEdit()
        self.subject_line.setText("")
        self.create_before_btn = QtWidgets.QPushButton(
            "create timestamp before selected"
        )
        self.create_before_btn.clicked.connect(self.new_before_selected_file)
        self.create_btn = QtWidgets.QPushButton("create timestamp now")
        self.create_btn.clicked.connect(self.new_now)

        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addWidget(self.create_before_btn)
        btn_layout.addWidget(self.create_btn)

        self.ui = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(self.ui)
        layout.addLayout(subj_layout)
        layout.addWidget(self.text_edit)
        layout.addLayout(btn_layout)

    def update(self, fname: str = None) -> None:
        subject = parse_subject(fname)
        print(subject)
        if subject:
            self.subject_line.setText(subject)
    
        with open(fname, "r") as f:
            self.text_edit.setText(f.read())

    def new_now(self):
        time_str = "{timestamp:%y%m%d_%H%M%S}".format(timestamp=datetime.datetime.now())
        print(time_str)
        self.new_note(time_str)

    def new_before_selected_file(self):
        fname = self.new_fname
        time_str = parse_fname_for_before(fname)
        if time_str is False:
            print(
                fname,
                "not supported, select a file with fname of the form YYMMDD_HHMMSS_*",
            )
            return

        self.new_note(time_str)

    def new_note(self, time_str):
        subject = self.subject_line.text()
        new_fname = Path(self.new_fname).parent.absolute() / f"{time_str}_{subject.replace(" ", "_")}.txt"

        with open(new_fname, "w") as f:
            f.write(self.text_edit.toPlainText())

        print("made", new_fname)


def fname_from_standart_sf_h5(fname, subject):
    parts = fname.split("_")
    if parts[1].isnumeric():
        pre = f"{parts[0]}_{int(parts[1])-1}"

    return f"{pre}_{subject}.txt"


def fname_from_note(fname, subject):
    parts = Path(fname).name.split("_")

    print(parts)

    if parts[1].isnumeric():
        pre = f"{parts[0]}_{parts[1]}"
    return f"{pre}_{subject}.txt"


def parse_fname_for_before(fname):
    parts = Path(fname).name.split("_")

    if len(parts) >= 2 and parts[0].isnumeric() and parts[1].isnumeric():
        return f"{parts[0]}_{int(parts[1])-1}"
    
    return False


def parse_subject(fname):
    parts = Path(fname).name.split("_")
    print(parts)

    if len(parts) >= 2 and parts[0].isnumeric() and parts[1].isnumeric():
        return "_".join(parts[2:])

    return False
