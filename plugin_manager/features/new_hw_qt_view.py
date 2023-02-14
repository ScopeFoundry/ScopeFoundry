from qtpy.QtWidgets import (QCheckBox, QComboBox, QGridLayout, QGroupBox,
                            QLabel, QLineEdit, QPushButton, QTextEdit)


class NewHWView(QGroupBox):

    def __init__(self) -> None:
        super().__init__()
        self.setup()

    def setup(self) -> None:
        layout = QGridLayout()
        self.setLayout(layout)
        col = 0

        self.company_label = QLabel('company')
        self.company_le = QLineEdit('thorlabs')
        layout.addWidget(QLabel('company'), col, 0)
        layout.addWidget(self.company_le, col, 1, 1, 2)
        col += 1

        self.model_label = QLabel('series or model')
        self.model_le = QLineEdit('XX312_Piezo_Controller')
        layout.addWidget(self.model_label, col, 0, 1, 2)
        layout.addWidget(self.model_le, col, 1, 1, 2)
        col += 1

        self.authors_label = QLabel('authors')
        self.authors_le = QLineEdit("Benedikt Ursprung")
        layout.addWidget(self.authors_label, col, 0)
        layout.addWidget(self.authors_le, col, 1, 1, 2)
        col += 1

        self.pretty_name_label = QLabel('pretty name')
        self.pretty_name_le = QLineEdit()
        self.guess_pretty_name_btn = QPushButton('U')
        self.guess_pretty_name_btn.setMaximumWidth(15)
        layout.addWidget(self.pretty_name_label, col, 0)
        layout.addWidget(self.pretty_name_le, col, 1)
        layout.addWidget(self.guess_pretty_name_btn, col, 2)
        col += 1

        self.com_types_label = QLabel('communication type')
        self.com_types_combob = QComboBox()

        layout.addWidget(self.com_types_label, col, 0)
        layout.addWidget(self.com_types_combob, col, 1, 1, 2)
        col += 1

        self.overwirte_label = QLabel('overwrite existing')
        self.overwrite_cb = QCheckBox()

        layout.addWidget(self.overwirte_label, col, 0)
        layout.addWidget(self.overwrite_cb, col, 1, 1, 2)
        col += 1

        self.create_pushButton = QPushButton('create new hardware')
        layout.addWidget(self.create_pushButton, col, 0, 1, 3)
        col += 1

        self.info_box = QTextEdit('')
        layout.addWidget(self.info_box, col, 0, 2, 3)
        col += 1

    def set_com_types_options(self, options):
        self.com_types_combob.clear()
        self.com_types_combob.addItems(tuple(options))

    def model_text_changed(self, callback):
        self.model_le.textChanged.connect(callback)

    def pretty_name_text_changed(self, callback):
        self.pretty_name_le.textChanged.connect(callback)

    def guess_button_clicked(self, callback):
        self.guess_pretty_name_btn.clicked.connect(callback)

    def com_texted_changed(self, callback):
        self.com_types_combob.currentTextChanged.connect(callback)

    def create_clicked(self, callback):
        self.create_pushButton.clicked.connect(callback)

    def get_company(self) -> str:
        return self.company_le.text()

    def set_company(self, text):
        self.company_le.setText(text)

    def get_model(self) -> str:
        return self.model_le.text()

    def set_model(self, text):
        print(text)
        self.model_le.setText(text)

    def set_authors(self, authors):
        self.authors_le.setText(authors)

    def get_authors(self) -> str:
        return self.authors_le.text()

    def get_pretty_name(self) -> str:
        return self.pretty_name_le.text()

    def set_pretty_name(self, text):
        self.pretty_name_le.setText(text)

    def get_overwrite(self) -> bool:
        return self.overwrite_cb.isChecked()

    def set_overwrite(self, checked) -> None:
        self.overwrite_cb.setChecked(checked)

    def get_com_option(self) -> str:
        return self.com_types_combob.currentText()

    def set_info_text(self, text):
        self.info_box.setHtml(text)

    def append_info(self, text):
        self.info_box.setHtml(self.info_box.toHtml() + text)
