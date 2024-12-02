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

Alternatively, use [Anaconda]([https://www.anaconda.com/download/success) Python distribution to create an environment with required dependencies . In `anaconda(3) prompt`run:

```
$ conda create -n scopefoundry python=3.12
$ conda activate scopefoundry
(scopefoundry) $ conda install numpy qtpy h5py pyqtgraph qtconsole
(scopefoundry) $ pip install pyqt6 scopefoundry
```

### Getting started

After installation, use anaconda prompt and navigate to where you want or have the source code for your setup and run:

```
$ python -m ScopeFoundry.tools
```

There will be tools to add a setup, templates to developpe hardware and add measurement components. 

### Analyze h5 with ipynb

With ScopeFoundry installed, you can navigate to your folder with h5 files and

```
$ python -m ScopeFoundry.tools
```

analyze_with_ipynb will generate a convinience functions to load data with python. (Recommended to use vscode with jupyter extension).


### Recommended folder structure

```
├── your_project_folder
│   ├── ScopeFoundryHW   						# your hardware component files
│   │	├── company1_model1						# for each hardware
│   │	│	├── company1_model1_hw.py			# define a HardwareComponent class that will be integrated
│   │	│	├── company1_model1_dev.py			# optional an interface class 
│   │	│	├── company1_model1_test_app.py		# a test app for quick developement
│   │	├── company2_model4
│   │	├── **
│   ├── your_fancy_microscope_app.py 			# your actual app that you will launch
│   ├── your_measurement_1.py				    # Measurement class 
│   ├── **
```



Upgrade
-------

```
$ conda activate scopefoundry
(scopefoundry) $ pip install --upgrade scopefoundry
```

In case you have a folder named `ScopeFoundry` in `your_project_folder` your are developer and you can either pull from git *or* rename to `ScopeFoundryArchive` and

```
$ conda activate scopefoundry
(scopefoundry) $ pip install scopefoundry
```


Documentation
-------------

See <http://www.scopefoundry.org>

For ScopeFoundry developers
---------------


```
$ conda create -n scopefoundry python=3.12
$ conda activate scopefoundry
(scopefoundry) $ pip install pyqt6 scopefoundry
```

fork on [github](https://github.com/ScopeFoundry/ScopeFoundry) and pull it into `your_project_folder` (see folder structure above).

