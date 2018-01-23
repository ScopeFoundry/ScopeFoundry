ScopeFoundry
============

A Python platform for controlling custom laboratory experiments and
visualizing scientific data

http://www.scopefoundry.org

Maintainer
----------

Edward S. Barnard esbarnard@lbl.gov

Contributors
------------

-  Alan Buckley
-  Nick Borys
-  Frank Ogletree
-  Benedikt Ursprung
-  Clarice Aiello
-  Hao Wu

Requirements
------------

-  Python 2.7, or 3.x
-  PyQt 4.7+, PySide, or PyQt5 (via qtpy shim package)
-  NumPy
-  PyQtGraph
-  h5py

*Optional:*

-  qtconsole
-  Ipython

Installation
------------

If you have all the requirements:

::

    pip install git+git://github.com/ScopeFoundry/ScopeFoundry.git

If you use the Anaconda python distribution, you can create an
environment that has ScopeFoundry and its required dependencies. See the
``conda_env`` sub-directory for environment files and Windows batch
files for environment setup.

Alternatively:

::

    $ conda create -n scopefoundry python=3.5
    $ source activate scopefoundry
    (scopefoundry) $ conda install numpy pyqt qtpy h5py
    (scopefoundry) $ pip install pyqtgraph
    (scopefoundry) $ pip install git+git://github.com/ScopeFoundry/ScopeFoundry.git

Documentation
-------------

See http://www.scopefoundry.org
