from setuptools import setup

setup(
    name = 'ScopeFoundry',
    
    version = '1.0.0',
    
    description = 'a platform for laboratory equipment control and scientific data analysis',
    long_description =open('README.md', 'r').read(), 
    
    # Author details
    author='Edward S. Barnard',
    author_email='esbarnard@lbl.gov',

    # Choose your license
    license='LICENSE',
    
    url='http://www.scopefoundry.org/',

    package_dir={'ScopeFoundry': '.'},
    
    packages=['ScopeFoundry', 'ScopeFoundry.scanning','ScopeFoundry.examples',],
    
    #packages=find_packages('.', exclude=['contrib', 'docs', 'tests']),
    #include_package_data=True,  
    
    package_data={
        '':["*.ui"], # include QT ui files 
        },
    
    )
