import datetime
from pathlib import Path
from qtpy import QtCore, QtWidgets

from ScopeFoundry.data_browser.data_browser_plug_in import DataBrowserPlugIn


class TimeNote(DataBrowserPlugIn):
    name = "time_note"
    button_text = "🕑Note"
    show_keyboard_key = QtCore.Qt.Key_N
    description = "inject simple notes with time stamps (Ctrl + N)"

    def setup(self):
        self.subject_line = QtWidgets.QLineEdit()

        subj_layout = QtWidgets.QHBoxLayout()
        subj_layout.addWidget(QtWidgets.QLabel("🕑 subject"))
        subj_layout.addWidget(self.subject_line)

        self.text_edit = QtWidgets.QTextEdit()
        self.subject_line.setText("")
        self.create_before_btn = QtWidgets.QPushButton("create note before selected")
        self.create_btn = QtWidgets.QPushButton("create note now")

        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addWidget(self.create_before_btn)
        btn_layout.addWidget(self.create_btn)

        self.ui = QtWidgets.QWidget(objectName="NoteWidget")
        layout = QtWidgets.QVBoxLayout(self.ui)
        layout.addLayout(subj_layout)
        layout.addWidget(self.text_edit)
        layout.addLayout(btn_layout)
        self.ui.setStyleSheet("QWidget#NoteWidget{background-color:rgba(216, 120, 152, 0.1)}")

        self.create_before_btn.clicked.connect(self.new_before_selected_file)
        self.create_btn.clicked.connect(self.new_now)

    def update(self, fname: str = None) -> None:
        if not fname.endswith(".txt"):
            return
        
        subject = parse_subject(fname)
        if subject:
            self.subject_line.setText(subject)
        with open(fname, "r", encoding="utf8") as f:
            self.text_edit.setText(f.read())

    def new_now(self):
        time_str = "{timestamp:%y%m%d_%H%M%S}".format(timestamp=datetime.datetime.now())
        self.new_note(time_str)

    def new_before_selected_file(self):
        fname = self.new_fname
        time_str = parse_timestampe_before(fname)

        if time_str is False:
            print(fname, "not supported, select a file with name pattern YYMMDD_HHMMSS_*")
            return

        self.new_note(time_str)

    def new_note(self, time_str):
        subject = self.subject_line.text()
        new_fname = Path(self.new_fname).parent.absolute() / f"{time_str}_{subject.replace(' ', '_')}.txt"

        with open(new_fname, "w", encoding="utf8") as f:
            f.write(self.text_edit.toPlainText())

        print("made time note", new_fname)



def parse_timestampe_before(fname):
    parts = Path(fname).stem.split("_")

    if len(parts) >= 2 and parts[0].isnumeric() and parts[1].isnumeric():
        return f"{parts[0]}_{int(parts[1])-1}"
    
    return False


def parse_subject(fname):
    parts = Path(fname).stem.split("_")

    if len(parts) >= 2 and parts[0].isnumeric() and parts[1].isnumeric():
        return "_".join(parts[2:])

    return False
