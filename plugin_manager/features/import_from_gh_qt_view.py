from qtpy.QtWidgets import (QCheckBox, QComboBox, QGroupBox, QHBoxLayout,
                            QLabel, QLineEdit, QPushButton, QTextEdit,
                            QVBoxLayout)


class ImportFromGhView(QGroupBox):

    def __init__(self) -> None:
        super().__init__()
        self.setup()

    def setup(self) -> None:
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.origin_repo_label = QLabel('origin repo')
        self.origin_repo_le = QLineEdit(
            'https://github.com/ScopeFoundry/HW_acton_spec.git')
        self.origin_repo_validat_btn = QPushButton('validate')
        self.origin_repo_validat_btn.setMaximumWidth(55)
        self.import_btn = QPushButton('Import from origin')
        self.import_btn.setEnabled(False)
        origin_layout = QHBoxLayout()
        origin_layout.addWidget(self.origin_repo_label)
        origin_layout.addWidget(self.origin_repo_le)
        origin_layout.addWidget(self.origin_repo_validat_btn)
        origin_layout.addWidget(self.import_btn)
        layout.addLayout(origin_layout)

        self.my_gh_acc_label = QLabel('my GitHub')
        self.my_gh_acc_le = QLineEdit('UBene')
        self.my_gh_acc_validate_btn = QPushButton('validate')
        self.my_gh_acc_validate_btn.setMaximumWidth(55)
        self.my_gh_acc_is_valid_cb = QCheckBox('')
        self.my_gh_acc_is_valid_cb.setEnabled(False)
        self.my_gh_acc_is_valid_cb.setMaximumWidth(15)
        self.fork_btn = QPushButton('Fork to my gh')
        self.validate_fork_btn = QPushButton('validate fork')
        self.import_from_fork_btn = QPushButton('import from fork')
        self.import_from_fork_btn.setEnabled(False)
        fork_layout = QHBoxLayout()
        fork_layout.addWidget(self.my_gh_acc_label)
        fork_layout.addWidget(self.my_gh_acc_le)
        fork_layout.addWidget(self.fork_btn)
        fork_layout.addWidget(self.validate_fork_btn)
        fork_layout.addWidget(self.import_from_fork_btn)
        layout.addLayout(fork_layout)

        self.info_box = QTextEdit('')
        layout.addWidget(self.info_box)

    def validate_origin_repo_clicked(self, callback):
        self.origin_repo_validat_btn.clicked.connect(callback)

    def validate_my_gh_acc_validate_clicked(self, callback):
        self.my_gh_acc_validate_btn.clicked.connect(callback)

    def fork_clicked(self, callback):
        self.fork_btn.clicked.connect(callback)

    def validate_fork_clicked(self, callback):
        self.validate_fork_btn.clicked.connect(callback)

    def import_from_fork_clicked(self, callback):
        self.import_from_fork_btn.clicked.connect(callback)

    def set_ready_to_import_from_fork(self, ready):
        self.import_from_fork_btn.setEnabled(ready)

    def import_clicked(self, callback):
        self.import_btn.clicked.connect(callback)

    def set_ready_to_import(self, ready):
        self.import_btn.setEnabled(ready)

    def set_my_gh_acc_valid(self, checked):
        self.my_gh_acc_is_valid_cb.setChecked(checked)

    def get_origin_repo(self) -> str:
        return self.origin_repo_le.text()

    def set_origin_repo(self, text):
        self.origin_repo_le.setText(text)

    def get_my_gh_acc(self) -> str:
        return self.my_gh_acc_le.text()

    def set_my_gh_acc(self, text):
        self.my_gh_acc_le.setText(text)

    def set_info_text(self, text):
        self.info_box.setHtml(text)

    def append_info(self, text):
        self.info_box.setHtml(self.info_box.toHtml() + text)
