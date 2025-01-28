ScopeFoundry
============

A Python platform for controlling custom laboratory 
experiments

<http://www.scopefoundry.org>


Requirements
------------

* Python 3.8+ (Currently tested with 3.9, 3.10, 3.12, 3.13)
* qtpy with any of Qt-binding: Pyqt6, PySide6, PyQt5, PySide
* NumPy 1.24+
* PyQtGraph
* h5py

_Optional:_

* qtconsole

Documentation
-------------

See <http://www.scopefoundry.org>

Installation
------------

###### If you have all the requirements

```sh
pip install scopefoundry
```

###### From scratch

1. Download and install [mininaconda]([https://www.anaconda.com/download/success) Python distribution 
2. Create an environment with required dependencies. In `anaconda(3) prompt` run:
	```sh
	conda create -n scopefoundry python=3.13
	```
	```sh
	conda activate scopefoundry
	```
3. to install `scopefoundry` 
	```sh
	pip install pyqt6 qtconsole matplotlib scopefoundry
	```

	*`qtconsole` `matplotlib` are optional*

[more details](https://scopefoundry.org/docs/1_getting-started/)

Upgrade
-------

```sh
# conda activate scopefoundry
pip install --upgrade scopefoundry
```

In case you have a folder named `ScopeFoundry` in `your_project_folder` your are a *core developer* and you can either pull from git *or* rename to `ScopeFoundryArchive` and

```sh
# conda activate scopefoundry
pip install scopefoundry
```

### Getting started

After installation, use anaconda prompt and navigate to where you want or have the source code for your setup and run:

```sh
python -m ScopeFoundry.tools
```

There will be tools to create an initial ScopeFoundry App along with templates to develop hardware and add measurement components.

### Analyze h5 with Jupyter

With ScopeFoundry installed, you can navigate to your folder with h5 files and

```sh
python -m ScopeFoundry.tools
```

analyze_with_ipynb will generate a convinience functions to load data with python. (For details [see](https://scopefoundry.org/docs/30_tips_and_tricks/analyze-with-ipynb/)).



### Recommended folder structure

```
├── your_project_folder
│   ├── ScopeFoundryHW        # your hardware component files
│   │	├── company1_model1        # for each hardware
│   │	│	├── company1_model1_hw.py        # define a HardwareComponent class that will be integrated
│   │	│	├── company1_model1_dev.py        # optional an interface class 
│   │	│	├── company1_model1_test_app.py        # a test app for quick developement
│   │	├── company2_model4
│   │	├── **
│   ├── your_fancy_microscope_app.py 			# your actual app that you will launch
│   ├── your_measurement_1.py        # Measurement class 
│   ├── **
│   ├── ScopeFoundry        # Optional: For ScopeFoundry core developers only
```



For ScopeFoundry core developers
---------------

```sh
conda create -n scopefoundry python=3.12
```
```sh
conda activate scopefoundry
```
```sh
conda install numpy qtpy h5py pyqtgraph qtconsole
```
```sh
pip install pyqt6
```


fork on [github](https://github.com/ScopeFoundry/ScopeFoundry) and pull it into `your_project_folder` (see folder structure above).


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
* Mark Hager
