from qtpy.QtWidgets import QGroupBox, QHBoxLayout, QPushButton


class EditorBaseUI:
    item_type = ""
    description = ""

    def __init__(self, measure) -> None:
        self.measure = measure

        self.layout = layout = QHBoxLayout()
        self.group_box = gb = QGroupBox(self.item_type.replace("_", "-"))
        gb.setToolTip(self.description)
        gb.setLayout(layout)

        self.add_btn = add_btn = QPushButton("New")
        add_btn.setToolTip("CTRL+N")
        add_btn.setFixedWidth(30)
        layout.addWidget(add_btn)

        self.replace_btn = replace_btn = QPushButton("Replace")
        replace_btn.setFixedWidth(50)
        replace_btn.setToolTip("CTRL+R")
        layout.addWidget(replace_btn)

        self.setup_ui()

    def set_on_new_func(self, fn):
        self.add_btn.clicked.connect(fn)

    def set_on_replace_func(self, fn):
        self.replace_btn.clicked.connect(fn)

    def setup_ui(self):
        ...

    def get_kwargs(self):
        ...

    def set_kwargs(self, **kwargs):
        ...
