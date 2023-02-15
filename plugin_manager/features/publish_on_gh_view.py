from qtpy.QtWidgets import (QCheckBox, QComboBox, QGridLayout, QGroupBox,
                            QHBoxLayout, QLabel, QLineEdit, QPushButton,
                            QTextEdit, QVBoxLayout)


class PublishOnGhView(QGroupBox):

    def __init__(self) -> None:
        super().__init__()
        self.setup()

    def setup(self) -> None:
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.my_gh_acc_label = QLabel('my GitHub')
        self.my_gh_acc_le = QLineEdit('UBene')
        self.my_gh_acc_validate_btn = QPushButton('validate')
        self.my_gh_acc_validate_btn.setMaximumWidth(55)
        self.my_gh_acc_is_valid_cb = QCheckBox('')
        self.my_gh_acc_is_valid_cb.setEnabled(False)
        self.my_gh_acc_is_valid_cb.setMaximumWidth(15)
        my_gh_layout = QHBoxLayout()
        my_gh_layout.addWidget(self.my_gh_acc_label)
        my_gh_layout.addWidget(self.my_gh_acc_le)
        layout.addLayout(my_gh_layout)

        self.hw_label = QLabel('Hardware')
        self.hw_cb = QComboBox()
        self.update_hws = QPushButton('update')
        self.update_hws.setMaximumWidth(55)
        hw_layout = QHBoxLayout()
        hw_layout.addWidget(self.hw_label)
        hw_layout.addWidget(self.hw_cb)
        hw_layout.addWidget(self.update_hws)
        layout.addLayout(hw_layout)

        publish_layout = QHBoxLayout()
        self.subtree_btn = QPushButton('1. subtree push')
        publish_layout.addWidget(self.subtree_btn)
        self.publish_btn = QPushButton('2. publish')
        publish_layout.addWidget(self.publish_btn)

        layout.addLayout(publish_layout)

        self.info_box = QTextEdit('')
        layout.addWidget(self.info_box)

    def update_hw_options_clicked(self, callback):
        self.update_hws.clicked.connect(callback)

    def validate_my_gh_acc_clicked(self, callback):
        self.my_gh_acc_validate_btn.clicked.connect(callback)

    def publish_clicked(self, callback):
        self.publish_btn.clicked.connect(callback)

    def subtree_clicked(self, callback):
        self.subtree_btn.clicked.connect(callback)

    def set_my_gh_acc_valid(self, checked):
        self.my_gh_acc_is_valid_cb.setChecked(checked)

    def get_hw(self) -> str:
        return self.hw_cb.currentText()

    def set_hw_options(self, options):
        self.hw_cb.clear()
        self.hw_cb.addItems(options)

    def get_my_gh_acc(self) -> str:
        return self.my_gh_acc_le.text()

    def set_my_gh_acc(self, text):
        self.my_gh_acc_le.setText(text)

    def set_info_text(self, text):
        self.info_box.setHtml(text)

    def append_info(self, text):
        self.info_box.setHtml(self.info_box.toHtml() + text)
