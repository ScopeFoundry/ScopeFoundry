from ScopeFoundry import Measurement
from ScopeFoundry.helper_funcs import sibling_path, load_qt_ui_file
import configparser
import time
from ScopeFoundry.logged_quantity import LQCollection, LoggedQuantity
from collections import OrderedDict

class BaseRecipeControl(Measurement):
    """
    Load and save Recipes / settings
    """
    
    name = 'recipe_control'
    
    def __init__(self, app, name=None, settings_dict=dict(sample='app/sample'), ):
        
        self.settings_dict = settings_dict

        Measurement.__init__(self, app, name=name)


    def setup(self):
        
        self.settings.New('recipes_filename', dtype='file', initial='')
        self.settings.recipes_filename.add_listener(self.load_recipes_file)

        self.settings.New('recipe_name', dtype=str, initial='recipe1', choices=('recipe1', ))
        self.settings.New('recipe_date_modified', dtype=str, ro=True)

        #self.recipe_settings.Add(self.settings.recipe_name)
        #self.recipe_settings.Add(self.settings.recipe_date_modified)


        for name, lq_path in self.settings_dict.items():
            if isinstance(lq_path, LoggedQuantity):
                lq = lq_path
            else:
                lq = self.app.lq_path(lq_path)
            recipe_lq = self.settings.New('recipe_' + name,
                              dtype=lq.dtype,
                              unit=lq.unit,
                              choices=lq.choices,
                              spinbox_decimals=lq.spinbox_decimals,
                              ro=True)
            
            self.settings_dict[name] = (recipe_lq, lq)            
            
        # list of recipe dicts
        self.recipes = []        
    
    def setup_figure(self):
        self.load_default_recipe_ui()

    def load_default_recipe_ui(self):
        self.ui = load_qt_ui_file(sibling_path(__file__, 'stored_recipe_control.ui'))

        for name, (recipe_lq, lq) in self.settings_dict.items():
            self.ui.recipe_settings_groupBox.layout().addRow(name, recipe_lq.new_default_widget())
            self.ui.current_settings_groupBox.layout().addRow(name, lq.new_default_widget())

        self.settings.recipe_date_modified.connect_to_widget(self.ui.recipe_date_modified_label)

        self.ui.save_recipe_pushButton.clicked.connect(self.on_save_recipe)
        self.ui.execute_pushButton.clicked.connect(self.execute_current_recipe)
        self.ui.delete_recipe_pushButton.clicked.connect(self.delete_current_recipe)
        
        self.settings.recipe_name.connect_to_widget(self.ui.recipe_name_comboBox)
        self.settings.recipe_name.add_listener(self.select_current_recipe)
        

        
        self.settings.recipes_filename.connect_to_browse_widgets(
            self.ui.recipes_filename_lineEdit,
            self.ui.recipes_filename_browse_pushButton)
        



    def get_recipe_by_name(self, name):
        for recipe in self.recipes:
            if recipe['name'] == name:
                return recipe
        raise ValueError("recipe not found {}".format(name))


    def load_recipes_file(self):
        
        config = configparser.ConfigParser()
        config.optionxform = str
        config.read(self.settings['recipes_filename'])

        self.recipes.clear()
        for name in config.sections():
            recipe_dict = OrderedDict()
            recipe_dict['name'] = name
            for key, val in config.items(name):
                recipe_dict[key] = val
            self.recipes.append(recipe_dict)
    
        # update recipe choices
        self.settings.recipe_name.change_choice_list(tuple([r['name'] for r in self.recipes]))
        
        # set recipe_name to first record if current recipe_name is not in file
        current_recipe_name = self.settings['recipe_name']
        if current_recipe_name in self.recipes:
            self.select_current_recipe(current_recipe_name)
        else:
            self.settings['recipe_name'] = self.recipes[0]['name']

    def save_recipes_file(self):
        config = configparser.ConfigParser()
        config.optionxform = str
        
        for recipe in self.recipes:
            config.add_section(recipe['name'])
            for setting_name in (list(self.settings_dict.keys()) + ['date_modified',]):
                if setting_name in recipe:
                    print(recipe['name'], setting_name, recipe[setting_name])
                    config.set(recipe['name'], setting_name, str(recipe[setting_name]))
    
        with open(self.settings['recipes_filename'], 'w') as configfile:
            config.write(configfile)



    def select_current_recipe(self, name=None):
        print("select_current_recipe", name)
        if name is None:
            name = self.settings['recipe_name']
        print("select_current_recipe", name)
        recipe = self.get_recipe_by_name(name)
        
        self.ui.new_recipe_name_lineEdit.setText(name)       
        # update recipe logged quantities
        for setting_name in self.settings_dict.keys():
            self.settings['recipe_' + setting_name] = recipe[setting_name]
            
        self.settings['recipe_date_modified'] = recipe['date_modified']
    
    
    def delete_current_recipe(self):
        recipe = self.get_recipe_by_name(self.settings['recipe_name'])        
        self.recipes.remove(recipe) 
        self.save_recipes_file()
        self.load_recipes_file()
    
    
    def save_current_settings_as_recipe(self, name):
        new_recipe = OrderedDict()
        new_recipe['name'] = name
        for setting_name, (recipe_lq, current_lq) in self.settings_dict.items():
            new_recipe[setting_name] = current_lq.value
        new_recipe['date_modified'] = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(time.time()))
        
        try:
            old_recipe = self.get_recipe_by_name(name)
            if old_recipe['date_modified'] == 'SYSTEM':
                self.load_recipes_file()
                self.settings['recipe_name'] = name

                return
            old_recipe.update(new_recipe)
        except ValueError:
            self.recipes.append(new_recipe)

        self.save_recipes_file()
        self.load_recipes_file()
        self.settings['recipe_name'] = name
        
    
    def execute_current_recipe(self):
        # save first?
        # ask first?
        for setting_name, (recipe_lq, current_lq) in self.settings_dict.items():
            current_lq.update_value(recipe_lq.value)

    
    
    def on_save_recipe(self):
        new_name = self.ui.new_recipe_name_lineEdit.text()
        self.save_current_settings_as_recipe(new_name)



if __name__ == '__main__':
    from ScopeFoundry.base_app import BaseMicroscopeApp
    
    class TestApp(BaseMicroscopeApp):
        name = 'test_app'
        
        def setup(self):
            self.settings.New('asdf', dtype=float, initial=4)
            settings_dict = OrderedDict()
            settings_dict['asdf'] = 'app/asdf'
            settings_dict['sample'] = self.settings.sample
            M = self.add_measurement(BaseRecipeControl(self, settings_dict=settings_dict))
            
            M.settings['recipes_filename'] = 'test_stored_recipe_control.ini'

    
    app = TestApp([])
    app.exec_()