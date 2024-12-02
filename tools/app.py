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
    def __init__(self):
        super().__init__()

        self.tab_widget = QtWidgets.QTabWidget()
        self.setCentralWidget(self.tab_widget)

    def add_page(self, page: Page):
        page.setup()
        page.setup_figure()
        self.tab_widget.addTab(page.ui, page.name)


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = ToolsApp()
    window.setWindowTitle("ScopeFoundry tools")
    logo_icon = QtGui.QIcon(str(ICONS_PATH / "scopefoundry_logo2C_1024.png"))
    window.setWindowIcon(logo_icon)
    window.add_page(WelcomePage())
    window.add_page(NewApp())
    window.add_page(NewHardware())
    window.add_page(NewMeasurement())
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
