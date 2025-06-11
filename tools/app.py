import sys
from pathlib import Path
from typing import Dict

from qtpy import QtGui, QtWidgets

from ScopeFoundry import ini_io
from ScopeFoundry.tools.page import Page
from ScopeFoundry.tools.pages.new_app import NewApp
from ScopeFoundry.tools.pages.new_hardware import NewHardware
from ScopeFoundry.tools.pages.new_measurement import NewMeasurement
from ScopeFoundry.tools.pages.publish_hw import PublishHW
from ScopeFoundry.tools.pages.welcome import WelcomePage

ROOT = Path(__file__).parent.parent
ICONS_PATH = ROOT / "base_app/icons"
DEFAULT_INI_FILE_CONTENT = {
    "new hardware/authors": "Benedikt Ursprung",
    "publish HW on GitHub/gh_username": "UBene",
    "publish HW on GitHub/ScopeFoundryHW_dir": "/Users/benediktursprung/Library/CloudStorage/OneDrive-Personal/scope_foundries/scopefoundry_trovatello_lab/ScopeFoundry/tools",
    "publish HW on GitHub/private_or_public": "--public",
}


class ToolsApp(QtWidgets.QMainWindow):

    def __init__(self) -> None:
        super().__init__()

        self.tab_widget = QtWidgets.QTabWidget()
        self.setCentralWidget(self.tab_widget)
        self.pages: Dict[str, Page] = {}
        self.pages_index = []

    def add_page(self, page: Page) -> None:
        page.setup()
        page.setup_figure()
        self.tab_widget.addTab(page.ui, page.name)
        self.pages[page.name] = page
        self.pages_index.append(page.name)

    def show_page(self, name: str) -> None:
        self.tab_widget.setCurrentIndex(self.pages_index.index(name))

    def read_and_set_settings(self) -> None:
        ins = self.read_settings()
        print(ins)
        for path, value in ins.items():
            d, name = path.split("/")
            if name == "ScopeFoundryHW_dir":
                if not Path(value).is_dir():
                    continue
            self.pages[d].settings[name] = value

    def read_settings(self):
        if not Path("tools_defaults.ini").is_file():
            ini_io.save_settings("tools_defaults.ini", DEFAULT_INI_FILE_CONTENT)
            return DEFAULT_INI_FILE_CONTENT
        DEFAULT_INI_FILE_CONTENT.update(ini_io.load_settings("tools_defaults.ini"))
        return DEFAULT_INI_FILE_CONTENT

    def save_settings(self):
        ins = self.read_settings()
        for path, value in ins.items():
            d, name = path.split("/")

            ins[path] = self.pages[d].settings[name]

        ini_io.save_settings("tools_defaults.ini", ins)


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
    window.add_page(WelcomePage(window))
    window.add_page(NewApp(window))
    window.add_page(NewHardware(window))
    window.add_page(NewMeasurement(window))
    window.add_page(PublishHW(window))
    window.show()
    window.show_page(page)
    window.read_settings()
    window.read_and_set_settings()
    app.exec_()
    window.save_settings()
    sys.exit()


if __name__ == "__main__":
    main()
