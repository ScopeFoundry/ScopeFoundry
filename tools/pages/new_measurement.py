from qtpy import QtWidgets

from ScopeFoundry.tools.features.new_measurement import new_measure
from ScopeFoundry.tools.page import Page


class NewMeasurement(Page):
    def setup(self):
        self.name = "new measurement"
        self.settings.New("name", dtype=str, initial="my_measurement_name")
        self.settings.New(
            "import",
            str,
            initial="",
            default_widget_factory=QtWidgets.QTextEdit,
            is_clipboardable=True,
        )

        self.operations.new("create", self.new_measurement)
        self.procedure = (
            "define name and press create",
            "name",
            "create",
            "copy paste to your apps setup function",
            # "run",
            "import",
        )

    def new_measurement(self):
        info = new_measure(self.settings["name"])
        self.settings["import"] = info["ADD_TO_APP"]
        # self.settings["run"] = "python"
