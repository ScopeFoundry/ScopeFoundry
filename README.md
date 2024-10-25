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

* qtpy (PyQt6 recommended, PySide6 currently unstable)
* Python 3.8+ (Currently tested with 3.9, 3.10 and 3.12)
* NumPy 1.24+
* PyQtGraph
* h5py
* xreload

_Optional:_

* qtconsole


Installation
------------

If you have all the requirements:

```
pip install scopefoundry
```

Alternatively, use [Anaconda]([https://www.anaconda.com/download/success) Python distribution to create an environment with required dependencies . In `anaconda prompt`run:

```
$ conda create -n scopefoundry python=3.12
$ conda activate scopefoundry
(scopefoundry) $ conda install numpy qtpy h5py pyqtgraph qtconsole
(scopefoundry) $ pip install pyqt6 scopefoundry
```

Documentation
-------------

See <http://www.scopefoundry.org>

