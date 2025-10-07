from pathlib import Path

from ScopeFoundry.h5_analyze_with_ipynb import analyze_with_ipynb
from ScopeFoundry.tools.page import Page

ROOT = Path(__file__).parent.parent.parent
ICONS_PATH = ROOT / "base_app/icons"


class WelcomePage(Page):
    def setup(self):
        self.name = "Welcome"

        self.settings.new_file("ipynb_folder", is_dir=True)
        self.settings.New(
            "ipynb_option", str, initial="all", choices=["all", "last", "smart"]
        )

        self.operations.new(
            "analyze with ipynb",
            self.h5_analyze_with_ipynb,
            icon_path=str(ICONS_PATH / "jupyter_logo.png"),
        )

        self.procedure = ("ipynb_folder", "ipynb_option", "analyze with ipynb")

    def h5_analyze_with_ipynb(self):
        analyze_with_ipynb(
            self.settings["ipynb_folder"],
            option=self.settings["ipynb_option"],
        )
