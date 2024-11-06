import functools
import time
from datetime import datetime
from pathlib import Path

import h5py

from .cb32_uuid import cb32_uuid

"""
recommended HDF5 file format for ScopeFoundry
* = group
- = attr
D = data_set

* /
    - scope_foundry_version = 130
    - time_id = # unix epoch timestamp
    - unique_id = # persistent identifer for dataset, 26 character
    - uuid = # uuid string representation of unique_id
    * app
        - ScopeFoundry_Type = App
        - name = test_app
        * settings
            - log_quant_1
            - log_quant_1_unit
            - ...
    * hardware
        * hardware_component_1
            - ScopeFoundry_Type = Hardware
            - name = hardware_component_1
            * settings
                - log_quant_1
                - ...
                * units
                    - log_quant_1 = '[n_m]'
        * ...
    * measurement
        * measurement_1
            - ScopeFoundry_Type = Measurement
            - name = measurement_1
                * settings
                    - log_quant_1
                    - ...
                    * units
                        - log_quant_1 = '[n_m]'
            D simple_data_set_2
            D ...

other thoughts:
    store git revision of code
    store git revision of ScopeFoundry
    EMD compatibility, NeXUS compatibility
"""


def h5_base_file(app, fname=None, measurement=None):
    unique_id, u = cb32_uuid()  # persistent identifier for dataset
    t0 = time.time()

    if fname is None and measurement is not None:
        f = app.settings["data_fname_format"].format(
            app=app,
            measurement=measurement,
            timestamp=datetime.fromtimestamp(t0),
            unique_id=unique_id,
            unique_id_short=unique_id[0:13],
            ext="h5",
        )
        fname = Path(app.settings["save_dir"]) / f
    elif fname is None:
        fname = (
            Path(app.settings["save_dir"])
            / f"{datetime.fromtimestamp(t0):%y%m%d_%H%M%S}.h5"
        )

    h5_file = h5py.File(fname, "a")
    root = h5_file["/"]
    root.attrs["ScopeFoundry_version"] = 160
    root.attrs["time_id"] = int(t0)
    root.attrs["unique_id"] = unique_id
    root.attrs["uuid"] = str(u)

    h5_save_app_lq(app, root)
    h5_save_hardware_lq(app, root)
    return h5_file

def h5_save_app_lq(app, h5group):
    h5_app_group = h5group.create_group('app/')
    h5_app_group.attrs['name'] = app.name
    h5_app_group.attrs['ScopeFoundry_type'] = "App"
    settings_group = h5_app_group.create_group('settings')
    h5_save_lqcoll_to_attrs(app.settings, settings_group)

def h5_save_hardware_lq(app, h5group):
    h5_hardware_group = h5group.create_group('hardware/')
    h5_hardware_group.attrs['ScopeFoundry_type'] = "HardwareList"
    for hc_name, hc in app.hardware.items():
        h5_hc_group = h5_hardware_group.create_group(hc_name)
        h5_hc_group.attrs['name'] = hc.name
        h5_hc_group.attrs['ScopeFoundry_type'] = "Hardware"
        h5_hc_settings_group = h5_hc_group.create_group("settings")
        h5_save_lqcoll_to_attrs(hc.settings, h5_hc_settings_group)
    return h5_hardware_group

def h5_save_lqcoll_to_attrs(settings, h5group):
    """
    take a LQCollection
    and create attributes inside h5group

    :param logged_quantities:
    :param h5group:
    :return: None
    """
    unit_group = h5group.create_group('units')
    # TODO decide if we should specify h5 attr data type based on LQ dtype
    for lqname, lq in settings.as_dict().items():
        #print('h5_save_lqcoll_to_attrs', lqname, repr(lq.val))
        try:
            h5group.attrs[lqname] = lq.val
        except:
            h5group.attrs[lqname] = lq.ini_string_value()
        if lq.unit:
            unit_group.attrs[lqname] = lq.unit


def h5_create_measurement_group(measurement, h5group, group_name=None):
    if group_name is None:
        group_name = 'measurement/' + measurement.name
    h5_meas_group = h5group.create_group(group_name)
    h5_save_measurement_settings(measurement, h5_meas_group)
    return h5_meas_group

def h5_save_measurement_settings(measurement, h5_meas_group):
    h5_meas_group.attrs['name'] = measurement.name
    h5_meas_group.attrs['ScopeFoundry_type'] = "Measurement"
    settings_group = h5_meas_group.create_group("settings")
    h5_save_lqcoll_to_attrs(measurement.settings, settings_group)


def h5_measurement_file(measurement,  fname=None):
    """ Default way to create HDF5 file and fill with 
    metadata for measurement and hardware
    
    filename of file is determined by app settings unless fname is specified
    
    creates an h5 file with groups: /app, /hardware, /measurement/<measurement_name>
    
    with all settings written to the file
    
    returns Measurement H5 group where additional data objects can be added during the measurment
    """
    h5f = h5_base_file(
                    app=measurement.app,
                    fname=fname,
                    measurement=measurement)
    M = h5_create_measurement_group(measurement, h5group=h5f)
    return M


def h5_create_emd_dataset(name, h5parent, shape=None, data = None, maxshape = None, 
                          dim_arrays = None, dim_names= None, dim_units = None,  **kwargs):
    """
    create an EMD dataset v0.2 inside h5parent
    returns an h5 group emd_grp
    
    to access N-dim dataset:    emd_grp['data']
    to access a specific dimension array: emd_grp['dim1']

    HDF5 Hierarchy:
    ---------------
    * h5parent
        * name [emd_grp] (<--returned)
            - emd_group_type = 1
            D data [shape = shape] 
            D dim1 [shape = shape[0]]
                - name
                - units
            ...
            D dimN [shape = shape[-1]]      

    Parameters
    ----------
    
    h5parent : parent HDF5 group 
    
    shape : Dataset shape of N dimensions.  Required if "data" isn't provided.

    data : Provide data to initialize the dataset.  If used, you can omit
            shape and dtype arguments.
    
    Keyword Args:
    
    dtype : Numpy dtype or string.  If omitted, dtype('f') will be used.
            Required if "data" isn't provided; otherwise, overrides data
            array's dtype.
            
    dim_arrays : optional, a list of N dimension arrays
    
    dim_names : optional, a list of N strings naming the dataset dimensions 
    
    dim_units : optional, a list of N strings specifying units of dataset dimensions
    
    Other keyword arguments follow from h5py.File.create_dataset
    
    Returns
    -------
    emd_grp : h5 group containing dataset and dimension arrays, see hierarchy below
    
    """
    # set the emd version tag at root of h5 file
    h5parent.file['/'].attrs['version_major'] = 0
    h5parent.file['/'].attrs['version_minor'] = 2

    # create the EMD data group
    emd_grp = h5parent.create_group(name)
    emd_grp.attrs['emd_group_type'] = 1

    if data is not None:
        shape = data.shape

    # data set where the N-dim data is stored
    data_dset = emd_grp.create_dataset("data", shape=shape, maxshape=maxshape, data=data, **kwargs)

    if dim_arrays is not None: assert len(dim_arrays) == len(shape)
    if dim_names  is not None: assert len(dim_names)  == len(shape)
    if dim_units  is not None: assert len(dim_units)  == len(shape)
    if maxshape   is not None: assert len(maxshape)   == len(shape)

    # Create the dimension array datasets
    for ii in range(len(shape)):
        if dim_arrays is not None:
            dim_array = dim_arrays[ii]
            dim_dtype =  dim_array.dtype            
        else:
            dim_array = None
            dim_dtype = float
        if dim_names is not None:
            dim_name = dim_names[ii]
        else:
            dim_name = "dim" + str(ii+1)
        if dim_units is not None:
            dim_unit = dim_units[ii]
        else:
            dim_unit = None
        if maxshape is not None:
            dim_maxshape = (maxshape[ii],)
        else:
            dim_maxshape = None

        # create dimension array dataset
        dim_dset = emd_grp.create_dataset("dim" + str(ii+1), shape=(shape[ii],), 
                                           dtype=dim_dtype, data=dim_array, 
                                           maxshape=dim_maxshape)
        dim_dset.attrs['name'] = dim_name
        if dim_unit is not None:
            dim_dset.attrs['unit'] = dim_unit

    return emd_grp


def create_extendable_h5_dataset(h5_group, name, shape, axis=0, dtype=None, **kwargs):
    """
    Create and return an empty HDF5 dataset of type *dtype* in h5_group that can store
    an infinitely long log of along *axis* (defaults to axis=0). 
    Dataset will have an initial shape *shape* but can be extended along *axis*
            
    creates reasonable defaults for chunksize
    can be overridden with **kwargs that are sent directly to 
    h5_group.create_dataset
    """
    maxshape = list(shape)
    maxshape[axis] = None

    default_kwargs = dict(
        name=name,
        shape=shape,
        dtype=dtype,
        #chunks=(1,),
        chunks=shape,
        maxshape=maxshape,
        compression=None,
        #shuffle=True,
        )
    default_kwargs.update(kwargs)
    h5_dataset =  h5_group.create_dataset(
        **default_kwargs
        )
    return h5_dataset


def create_extendable_h5_like(h5_group, name, arr, axis=0, **kwargs):
    """
    Create and return an empty HDF5 dataset in h5_group that can store
    an infinitely long log of along *axis* (defaults to axis=0). Dataset will be the same
    shape as *arr* but can be extended along *axis*
            
    creates reasonable defaults for chunksize, and dtype,
    can be overridden with **kwargs that are sent directly to 
    h5_group.create_dataset
    """
    return create_extendable_h5_dataset(
        h5_group, name, arr.shape, axis, arr.dtype, **kwargs)

def extend_h5_dataset_along_axis(ds, new_len, axis=0):
    newshape = list(ds.shape)
    newshape[axis] = new_len
    ds.resize( newshape )    


def load_settings(fname):
    """
    returns a dictionary (path, value) of all settings stored in a h5 file
    """
    path = Path(fname)
    if not path.suffix == ".h5":
        return {}

    settings = {}
    visit_func = functools.partial(_settings_visitfunc, settings=settings)

    with h5py.File(fname) as file:
        file.visititems(visit_func)    

    return settings


def _settings_visitfunc(name, node, settings):
    if not name.endswith("settings"):
        return
    
    for key, val in node.attrs.items():
        lq_path = f"{name.replace('settings', key)}"
        settings[lq_path] = val
