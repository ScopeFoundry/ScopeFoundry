from typing import Sequence
from qtpy import QtWidgets

from ScopeFoundry.dynamical_widgets.generic_widget import add_to_layout
from ScopeFoundry.logged_quantity.collection import LQCollection
from ScopeFoundry.operations import Operations


class Page:
    name = None

    def __init__(self, app) -> None:
        if self.name is None:
            self.name = "page"

        self.settings = LQCollection()
        self.operations = Operations()
        self.procedure = ()
        self.app = app

    def setup(self):
        """override me"""
        self.procedure = ()
        self.name = "page"

    def setup_figure(self):
        self.ui = QtWidgets.QWidget()
        self.layout = QtWidgets.QFormLayout(self.ui)
        if not self.procedure:
            add_to_layout(self.settings, self.layout)
            add_to_layout(self.operations, self.layout)
            return
        procedure_to_layout(self.procedure, self.layout, self.settings, self.operations)


def procedure_to_layout(
    procedure: Sequence[str],
    layout: QtWidgets.QFormLayout,
    settings: LQCollection,
    operations: Operations,
):
    n_text_instruction = 1
    for step in procedure:
        if step in operations:
            layout.addRow(operations.new_button(step))
        elif step in settings:
            lq = settings.get_lq(step)
            layout.addRow(step, lq.new_default_widget())
        else:
            inst = QtWidgets.QLabel(f"{n_text_instruction}. {step}")
            inst.setStyleSheet(
                "font: italic bolt 18; padding-top:23px; padding-bottom: 10px"
            )
            layout.addRow(inst)
            n_text_instruction += 1
