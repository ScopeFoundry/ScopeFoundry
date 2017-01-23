from setuptools import setup

setup(
    name = 'ScopeFoundry',
    
    version = '0.0.1.dev1',
    
    description = 'a framework for laboratory equipment control and data analysis',
    
    # Author details
    author='Edward S. Barnard',
    author_email='esbarnard@lbl.gov',

    # Choose your license
    license='BSD',

    package_dir={'ScopeFoundry': '.'},
    
    packages=['ScopeFoundry', 'ScopeFoundry.scanning','ScopeFoundry.examples',],
    
    #packages=find_packages('.', exclude=['contrib', 'docs', 'tests']),
    #include_package_data=True,  
    
    package_data={
        '':["*.ui"], # include QT ui files 
        },
    
    )
