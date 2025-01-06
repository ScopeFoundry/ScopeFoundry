import sys
from pathlib import Path

from qtpy import QtGui, QtWidgets

from ScopeFoundry.tools.page import Page
from ScopeFoundry.tools.pages.new_app import NewApp
from ScopeFoundry.tools.pages.new_hardware import NewHardware
from ScopeFoundry.tools.pages.new_measurement import NewMeasurement
from ScopeFoundry.tools.pages.welcome import WelcomePage

ROOT = Path(__file__).parent.parent
ICONS_PATH = ROOT / "base_app/icons"


class ToolsApp(QtWidgets.QMainWindow):

    def __init__(self) -> None:
        super().__init__()

        self.tab_widget = QtWidgets.QTabWidget()
        self.setCentralWidget(self.tab_widget)
        self.pages = []

    def add_page(self, page: Page) -> None:
        page.setup()
        page.setup_figure()
        self.tab_widget.addTab(page.ui, page.name)
        self.pages.append(page.name)

    def show_page(self, name: str) -> None:
        self.tab_widget.setCurrentIndex(self.pages.index(name))


def main() -> None:
    if len(sys.argv) > 1:
        start_app(" ".join(sys.argv[1:]))
    else:
        start_app()


def start_app(page="Welcome") -> None:
    app = QtWidgets.QApplication([])
    window = ToolsApp()
    window.setWindowTitle("ScopeFoundry tools")
    logo_icon = QtGui.QIcon(str(ICONS_PATH / "scopefoundry_logo2C_1024.png"))
    window.setWindowIcon(logo_icon)
    window.add_page(WelcomePage())
    window.add_page(NewApp())
    window.add_page(NewHardware())
    window.add_page(NewMeasurement())
    window.show()
    window.show_page(page)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
