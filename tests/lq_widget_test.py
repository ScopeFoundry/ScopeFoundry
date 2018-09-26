from ScopeFoundry import LQCollection, BaseApp
from qtpy import QtGui, QtWidgets

class LQWidgetTestApp(BaseApp):
    
    name = 'LQWidgetTestApp'

    def __init__(self,argv):
        BaseApp.__init__(self,argv)
        
        self.settings.New('long_string_test',  dtype=str, initial="Lorem ipsum dolor sit amet, consectetur adipiscing elit. Aliquam accumsan, ligula a tristique luctus, felis est blandit libero, nec placerat justo diam at lacus. Fusce volutpat vitae lacus non lobortis. Fusce porttitor varius placerat. Curabitur et varius urna, sit amet gravida leo. Etiam eleifend luctus erat, vel maximus libero lacinia at. Pellentesque mattis pulvinar sem, sit amet porttitor mi maximus in. Sed venenatis orci sit amet nulla luctus, vitae pulvinar neque facilisis. Donec in felis sodales libero fringilla aliquam eu non urna. Praesent ac elit ac lorem cursus aliquam eu venenatis mauris. Proin sed aliquet nunc. Duis venenatis mi dapibus.", ro=False)


        self.ui = self.settings.New_UI()
        
        long_string_test_plainTextEdit = QtWidgets.QPlainTextEdit()
        self.ui.layout().addRow("long_string_test_plainTextEdit", long_string_test_plainTextEdit)
        
        self.settings.long_string_test.connect_to_widget(long_string_test_plainTextEdit)
        
        self.console_widget.show()
        self.ui.show()

if __name__ == '__main__':
    import sys
    app = LQWidgetTestApp(sys.argv)
    app.exec_()