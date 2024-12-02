from ScopeFoundry.tools.features.new_app import new_app
from ScopeFoundry.tools.page import Page


class NewApp(Page):
    def setup(self):
        self.name = "new app"
        self.operations.add("new app", self.new_app)

        self.settings.New("cmd", str, initial="", is_cmd=True, is_clipboardable=True)

        self.operations.add("create", self.new_app)
        self.procedure = ("new app", "cmd")

    def new_app(self):
        self.settings["cmd"] = new_app()
