ScopeFoundry
============

A Python platform for controlling custom laboratory experiments.

<http://www.scopefoundry.org>

Requirements
------------

* Python 3.8+ (Currently tested with 3.9, 3.10, 3.12, 3.13)
* qtpy with any Qt-binding: PyQt6, PySide6, PyQt5, PySide
* NumPy 1.24+
* PyQtGraph
* h5py

_Optional:_

* qtconsole
* pyqtdarktheme

Documentation
-------------

See <http://www.scopefoundry.org>

Installation
------------

#### If you have all the requirements

```sh
pip install scopefoundry
```

#### From scratch

1. Download and install the [Miniconda](https://www.anaconda.com/download/success) Python distribution.
2. Create an environment with the required dependencies. In the `anaconda(3) prompt`, run:
    ```sh
    conda create -n scopefoundry python=3.13
    ```
    ```sh
    conda activate scopefoundry
    ```
3. To install `scopefoundry`:
    ```sh
    pip install pyqt6 qtconsole pyqtdarktheme matplotlib scopefoundry
    ```

    *`qtconsole`, `matplotlib`, and `pyqtdarktheme` are optional.*


#### Upgrade

```sh
# conda activate scopefoundry
pip install --upgrade scopefoundry
```

If you have a folder named `ScopeFoundry` in `your_project_folder`, you are a *core developer* and can either pull from [GitHub](https://github.com/ScopeFoundry/) *or* rename the `ScopeFoundry` to `ScopeFoundryArchive` and:

```sh
# conda activate scopefoundry
pip install scopefoundry
```

## Getting Started

After installation, use the Anaconda prompt and make or navigate to `your_project_folder`, then run:

```sh
python -m ScopeFoundry.tools
```

This will provide tools to create an initial ScopeFoundry App along with templates to develop hardware and add measurement components.

Equivalently run:

```sh
python -m ScopeFoundry init
```

[More details](https://scopefoundry.org/docs/1_getting-started/)

## Analyze h5 with Jupyter

With ScopeFoundry installed, you can navigate to your folder with h5 files and:

```sh
python -m ScopeFoundry ipynb
```

`analyze_with_ipynb` will generate convenience functions to load data with Python. For details [see here](https://scopefoundry.org/docs/30_tips-and-tricks/analyze-with-ipynb/).

## Recommended Folder Structure

```bash
├── your_project_folder
   	├── ScopeFoundryHW        # Your hardware component files
   	   	├── company1_model1        # For each hardware
   	   	   	├── company1_model1_hw.py        # Define a HardwareComponent class that will be integrated
   	   	   	├── company1_model1_dev.py        # Optional: an interface class 
   	   	   	├── company1_model1_test_app.py   # A test app for quick development
   	   	   	├── company2_model4
   	   	├── **
   	├── your_fancy_microscope_app.py 			# Your actual app that you will launch
   	├── measurements/
   	   	├──your_measurement_1.py        # Measurement class 
   	├── **
   	├── ScopeFoundry        # Optional: For ScopeFoundry core developers only
```

## For ScopeFoundry Core Developers

Follow the same steps as above and additionally:

1. Installation as above (although `scopefoundry` does not need to be pip-installed).
2. Fork the repository on [GitHub](https://github.com/ScopeFoundry/ScopeFoundry) and pull it into `your_project_folder` (see folder structure above).

Additions to ScopeFoundry are welcome. See [instructions here](https://scopefoundry.org/docs/1000_core-development/#contribute)

Maintainer
----------

Edward S. Barnard <esbarnard@lbl.gov>

## Contributors

* Benedikt Ursprung
* Nick Borys
* Jonas Zipfel
* Frank Ogletree
* Clarice Aiello
* Hao Wu
* Alan Buckley
* Peter Ercius
* Mark Hager
