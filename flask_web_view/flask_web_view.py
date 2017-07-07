from flask import Flask, render_template
from flask_restful import Resource, Api
from qtpy import QtCore
from ScopeFoundry.base_app import BaseMicroscopeApp
from ScopeFoundry.helper_funcs import sibling_path
from collections import OrderedDict

class MicroscopeRestResource(Resource):

    def __init__(self, **kwargs):
        self.microscope_app = kwargs['microscope_app']

    def get(self):
        hardware = OrderedDict()
        for HW in self.microscope_app.hardware.values():
            hardware[HW.name] = dict(settings=OrderedDict([(S.name, S.val) for S in HW.settings.as_list()]))
        measurements = OrderedDict()
        for M in self.microscope_app.measurements.values():
            print(M)
            measurements[M.name] = dict(settings=OrderedDict([(S.name, S.val) for S in M.settings.as_list()]))
        return {'app': dict(name=self.microscope_app.name, settings={S.name: S.val for S in self.microscope_app.settings.as_list()}),
                'hardware': hardware, 
                'measurements': measurements,
                }


def settings_dict(settings):
    out =  OrderedDict([(S.name, S.val) for S in settings.as_list()])
    out['units'] = OrderedDict([(S.name, S.unit) for S in settings.as_list() if S.unit])
    return out

def lq_dict(lq):
    return OrderedDict( [('name', lq.name), ('val',lq.val), ('unit', lq.unit)])


class HardwareSettingsListRestResource(Resource):

    def __init__(self, microscope_app):
        self.microscope_app = microscope_app
        
    def get(self, hw_name):
        settings = self.microscope_app.hardware[hw_name].settings
        return settings_dict(settings)      

class HardwareSettingsLQRestResource(Resource):

    def __init__(self, microscope_app):
        self.microscope_app = microscope_app
        
    def get(self, hw_name, lq_name):
        lq = self.microscope_app.hardware[hw_name].settings.get_lq(lq_name)        
        return lq_dict(lq)

class MeasurementSettingsListRestResource(Resource):

    def __init__(self, microscope_app):
        self.microscope_app = microscope_app
        
    def get(self, measure_name):
        settings = self.microscope_app.measurements[measure_name].settings        
        return settings_dict(settings)
    
class MeasurementSettingsLQRestResource(Resource):

    def __init__(self, microscope_app):
        self.microscope_app = microscope_app
        
    def get(self, measure_name, lq_name):
        lq = self.microscope_app.hardware[measure_name].settings.get_lq(lq_name)        
        return lq_dict(lq)
    
class MicroscopeFlaskWebThread(QtCore.QThread):
    
    def __init__(self, app):
        QtCore.QThread.__init__(self)
        self.app = app
        
        
        self.flask_app = Flask(app.name, template_folder=sibling_path(__file__, 'templates'), )
    
        self.flask_app.route('/')(self.index)
        
        self.rest_api = Api(self.flask_app)
        self.flask_app.config['RESTFUL_JSON'] = dict(indent=4)
        

        self.rest_api.add_resource(MicroscopeRestResource,
                                   '/api/app',
                                   resource_class_kwargs={ 'microscope_app': self.app })
        
        self.rest_api.add_resource(HardwareSettingsListRestResource, 
                                   '/api/hardware/<string:hw_name>/settings', 
                                   resource_class_kwargs={ 'microscope_app': self.app })
        
        self.rest_api.add_resource(HardwareSettingsLQRestResource, 
                                   '/api/hardware/<string:hw_name>/settings/<string:lq_name>', 
                                   resource_class_kwargs={ 'microscope_app': self.app })

        self.rest_api.add_resource(MeasurementSettingsListRestResource, 
                                   '/api/measurements/<string:measure_name>/settings', 
                                   resource_class_kwargs={ 'microscope_app': self.app })
        
        self.rest_api.add_resource(MeasurementSettingsLQRestResource, 
                                   '/api/measurements/<string:measure_name>/settings/<string:lq_name>', 
                                   resource_class_kwargs={ 'microscope_app': self.app })
        for HW in self.app.hardware.values():
            #print(HW.web_ui())
            self.flask_app.route('/hw/{}'.format(HW.name))(HW.web_ui)
        for M in self.app.measurements.values():
            self.flask_app.route('/measure/{}'.format(M.name))(M.web_ui)
    
    def __del__(self):
        self.wait()

    def run(self):
        self.flask_app.run(port=5000)
        print("thread run")

    def index(self):
        return render_template("microscope_index.html", app=self.app)


if __name__ == '__main__':
    import sys
    
    app = BaseMicroscopeApp([])
    app.flask_thread = MicroscopeFlaskWebThread(app)
    app.flask_thread.start()
    sys.exit(app.exec_())