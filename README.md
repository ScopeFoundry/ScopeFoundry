ScopeFoundry
============

A Python platform for controlling custom laboratory 
experiments and visualizing scientific data

<http://www.scopefoundry.org>

Maintainer
----------

Edward S. Barnard <esbarnard@lbl.gov>

Contributors
------------

* Benedikt Ursprung
* Nick Borys
* Jonas Zipfel
* Frank Ogletree
* Clarice Aiello
* Hao Wu
* Alan Buckley
* Peter Ercius


Requirements
------------

* Python 3.x (Currently tested with 3.9 and 3.10)
* PySide, or PyQt5 (via qtpy shim package)
* NumPy
* PyQtGraph
* h5py
* xreload

_Optional:_

* qtconsole
* Ipython
  
Installation
------------

If you have all the requirements:

```
pip install git+git://github.com/ScopeFoundry/ScopeFoundry.git
```

If you use the Anaconda Python distribution, you can create an environment
that has ScopeFoundry and its required dependencies. See the `conda_env`
sub-directory for environment files and Windows batch files for environment
setup.

Alternatively:

```
$ conda create -n scopefoundry python=3.10
$ source activate scopefoundry
(scopefoundry) $ conda install numpy pyqt qtpy h5py pyqtgraph
(scopefoundry) $ pip install git+git://github.com/ScopeFoundry/ScopeFoundry.git
```

Documentation
-------------

See <http://www.scopefoundry.org>
