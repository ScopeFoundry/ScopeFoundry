'''
Created on Feb 3, 2023

@author: Benedikt Ursprung
'''
import logging

from ScopeFoundry.base_app import BaseMicroscopeApp

logging.basicConfig(level=logging.DEBUG)

class App(BaseMicroscopeApp):

    name = 'test_app'

    def setup(self):

        from ScopeFoundry.controlling import PIDFeedbackControl
        self.add_measurement(PIDFeedbackControl(self))
        from ScopeFoundry.controlling import RangedOptimization
        self.add_measurement(RangedOptimization(self))
        
    def setup_ui(self):
        from qtpy.QtWidgets import QWidget, QVBoxLayout
        widget = QWidget()
        widget.setMaximumWidth(380)
        layout = QVBoxLayout(widget)
        self.add_quickbar(widget)
        layout.addWidget(self.measurements['pid_feedback_control'].New_mini_UI())

if __name__ == '__main__':
    import sys
    app = App(sys.argv)
    sys.exit(app.exec_())
