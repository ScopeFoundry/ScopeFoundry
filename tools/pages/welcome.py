from pathlib import Path

from ScopeFoundry.h5_analyze_with_ipynb import analyze_with_ipynb
from ScopeFoundry.tools.page import Page

ROOT = Path(__file__).parent.parent.parent
ICONS_PATH = ROOT / "base_app/icons"


class WelcomePage(Page):
    def setup(self):
        self.name = "Welcome"
        self.operations.new(
            " analyze with ipynb",
            analyze_with_ipynb,
            icon_path=ICONS_PATH / "jupyter_logo.png",
        )
