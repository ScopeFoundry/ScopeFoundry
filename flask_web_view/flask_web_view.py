from flask import Flask, render_template
from qtpy import QtCore
from ScopeFoundry.base_app import BaseMicroscopeApp
from ScopeFoundry.helper_funcs import sibling_path

class MicroscopeFlaskWebThread(QtCore.QThread):
    
    def __init__(self, app):
        QtCore.QThread.__init__(self)
        self.app = app
        
        
        self.flask_app = Flask(app.name, template_folder=sibling_path(__file__, 'templates'), )
    
        self.flask_app.route('/')(self.index)
    
    def __del__(self):
        self.wait()

    def run(self):
        self.flask_app.run(port=5000)
        print("tread run")

    def index(self):
        #return "<pre>hello {}</pre>".format(self.app.settings.keys())
        return render_template("microscope_index.html", app=self.app)
    
    
if __name__ == '__main__':
    import sys
    
    app = BaseMicroscopeApp([])
    app.flask_thread = MicroscopeFlaskWebThread(app)
    app.flask_thread.start()
    sys.exit(app.exec_())