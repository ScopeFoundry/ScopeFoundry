from qtpy.QtCore import QObject
from qtpy.QtWidgets import QGroupBox, QHBoxLayout, QPushButton, QSizePolicy, QWidget
from qtpy.QtCore import QEvent


class MyGroupBox(QGroupBox):
    def __init__(self, title, parent=None):
        super().__init__(title, parent)

        self.setObjectName("sequencer_editor")
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Maximum)

    def hook_children_widget_focus(self):
        for widget in self.children():
            widget.installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.FocusIn:
            self.setStyleSheet("QGroupBox {border: 1px solid rgba(105, 240, 104, 220)}")
        if event.type() == QEvent.FocusOut:
            self.setStyleSheet("QGroupBox {border: none}")
        return watched.eventFilter(watched, event)


class EditorBaseUI:
    item_type = ""
    description = ""

    def __init__(self, measure) -> None:
        self.measure = measure

        self.group_box = gb = MyGroupBox(
            self.item_type.replace("_", " ").replace("-", " ").title()
        )
        gb.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Maximum)
        gb.setToolTip(self.description)
        self.layout = layout = QHBoxLayout(gb)

        self.add_btn = add_btn = QPushButton("New")
        add_btn.setToolTip("CTRL+N")
        add_btn.setFixedWidth(33)
        layout.addWidget(add_btn)

        self.replace_btn = replace_btn = QPushButton("Replace")
        replace_btn.setFixedWidth(50)
        replace_btn.setToolTip("CTRL+R")
        layout.addWidget(replace_btn)

        self.setup_ui()
        gb.hook_children_widget_focus()

    def set_on_new_func(self, fn):
        self.add_btn.clicked.connect(fn)

    def set_on_replace_func(self, fn):
        self.replace_btn.clicked.connect(fn)

    def setup_ui(self): ...

    def get_kwargs(self): ...

    def set_kwargs(self, **kwargs): ...
