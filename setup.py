from setuptools import setup

setup(
    name = 'ScopeFoundry',
    
    version = '1.3.0',
    
    description = 'a platform for laboratory equipment control and scientific data analysis',
    long_description =open('README.md', 'r').read(),
    long_description_content_type='text/markdown',
    
    # Author details
    author='Edward S. Barnard',
    author_email='esbarnard@lbl.gov',

    # Choose your license
    license='BSD',
    
    url='http://www.scopefoundry.org/',

    package_dir={'ScopeFoundry': '.'},
    
    packages=['ScopeFoundry', 'ScopeFoundry.scanning','ScopeFoundry.examples','ScopeFoundry.graphics', 'ScopeFoundry.data_browser' ],
    
    #packages=find_packages('.', exclude=['contrib', 'docs', 'tests']),
    #include_package_data=True,  
    
    package_data={
        '':["*.ui", "*.icns", '*.png', '*.svg'], # include QT ui files and logo and icons
        },
        
    install_requires = [
    	'numpy', 'h5py', 'qtpy', 'xreload', 'uuid7']
    
    install_requires=['numpy', 'qtpy', 'h5py', 'pyqtgraph'],

    extras_require={
        'all' : ['qtconsole', 'pyqt5'],
    }

    )
