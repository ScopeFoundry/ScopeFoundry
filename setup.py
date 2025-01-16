from setuptools import setup

setup(
    name = 'ScopeFoundry',
    
    version = '2.0.0',
    
    description = 'a platform for laboratory equipment control and scientific data analysis',
    long_description =open('README.md', 'r').read(),
    long_description_content_type='text/markdown',
    
    # Author details
    author='Edward S. Barnard',
    author_email='esbarnard@lbl.gov',

    # Choose your license
    license='BSD',
    
    url='https://www.scopefoundry.org/',

    package_dir={'ScopeFoundry': '.'},
    
    packages=['ScopeFoundry',
              'ScopeFoundry.base_app',
              'ScopeFoundry.controlling',
              'ScopeFoundry.data_browser',
                  'ScopeFoundry.data_browser.viewers',
                  'ScopeFoundry.data_browser.plug_ins',
              'ScopeFoundry.dynamical_widgets',
              'ScopeFoundry.examples',
                  'ScopeFoundry.examples.ScopeFoundryHW',
              'ScopeFoundry.graphics',
              'ScopeFoundry.graphics.zoomable_map',
              'ScopeFoundry.logged_quantity',
              'ScopeFoundry.scanning',
              'ScopeFoundry.sequencer',
              'ScopeFoundry.sequencer.item_types',              
              'ScopeFoundry.tools',  
                  'ScopeFoundry.tools.features',
                  'ScopeFoundry.tools.templates',
                  'ScopeFoundry.tools.pages',
            ],
    
    #packages=find_packages('.', exclude=['contrib', 'docs', 'tests']),
    #include_package_data=True,  
    
    package_data={
        '':["*.ui", "*.icns", '*.png', '*.svg'], # include QT ui files and logo and icons
        },
        
    install_requires = [
    	'numpy', 'h5py', 'qtpy', 'xreload', 'uuid7'],
    
    extras_require={
        'all' : ['qtconsole', 'pyqtdarktheme', 'qtpy6'],
    }

    )
