'''
Created on Feb 2, 2023

@author: Benedikt Ursprung
'''
import logging
import sys

from features.import_from_gh_controller import ImportFromGhController
from features.import_from_gh_qt_view import ImportFromGhView
from features.new_hw_controller import NewHWController
from features.new_hw_qt_view import NewHWView
from features.publish_on_gh_controller import PublishOnGhController
from features.publish_on_gh_view import PublishOnGhView
from qtpy.QtWidgets import QApplication, QMainWindow, QTabWidget

logger = logging.getLogger()
logger.addHandler(logging.StreamHandler(sys.stdout))

logger.setLevel(logging.DEBUG)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)

        self.publish_on_gh_controller = PublishOnGhController(
            PublishOnGhView())
        self.tab_widget.addTab(
            self.publish_on_gh_controller.view, 'publish on GitHub')

        self.import_from_gh_controller = ImportFromGhController(
            ImportFromGhView())
        self.tab_widget.addTab(
            self.import_from_gh_controller.view, 'import from GitHub')

        self.new_hw_controller = NewHWController(NewHWView())
        self.tab_widget.addTab(self.new_hw_controller.view, 'create new HW')

        self.show()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.setWindowTitle('ScopeFoundry plugin manager')
    sys.exit(app.exec_())
