from ScopeFoundry.tools.features.new_app import new_app
from ScopeFoundry.tools.page import Page


class NewApp(Page):
    def setup(self) -> None:
        self.name = "new app"
        self.operations.new("new app", self.new_app)

        self.settings.New("cmd", str, initial="", is_cmd=True, is_clipboardable=True)

        self.operations.new("create", self.new_app)
        self.procedure = ("new app", "cmd")

    def new_app(self) -> None:
        self.settings["cmd"] = new_app()
