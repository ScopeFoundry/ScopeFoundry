from ScopeFoundry import LQCollection, BaseApp

class LQConnectionTestApp(BaseApp):
    
    name = 'LQConnectionTestApp'

    def __init__(self,argv):
        BaseApp.__init__(self,argv)
        
        lq1 = self.settings.New('lq1', dtype=float,ro=False, initial=5)
        lq2 = self.settings.New('lq2', dtype=float,ro=False, initial=35)

        lq1.connect_to_lq(lq2)
        
        self.ui = self.settings.New_UI()
        
        self.ui.show()
        self.console_widget.show()
        
        
if __name__ == '__main__':
    app = LQConnectionTestApp([])
    app.exec_()