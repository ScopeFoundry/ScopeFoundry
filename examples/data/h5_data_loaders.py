# generated with ScopeFoundry.analyze_with_ipynb()
# Probality you want to
#
# from h5_data_loaders import load
# data = load('your_file_name.h5')

import functools
from dataclasses import dataclass
from pathlib import Path

import h5py
import numpy as np

load_funcs = {}


def get_measurement_name(fname):
    with h5py.File(fname) as file:
        if len(file["measurement"].keys()) == 1:
            return list(file["measurement"].keys())[0]
        return file.attrs["measurement"]


def load(fname: str):
    mm_name = get_measurement_name(fname)
    return load_funcs[mm_name](fname)


def load_settings(fname):
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

def get_mm_name(fname):
    with h5py.File(fname) as file:
        if len(file["measurement"].keys()) == 1:
            return list(file["measurement"].keys())[0]
        return file.attrs["measurement"]


@dataclass
class Example2DScan:
    settings:dict
    pixel_time: np.ndarray
    range_extent: np.ndarray
    corners: np.ndarray
    signal_map: np.ndarray
    scan_v_positions: np.ndarray
    h_array: np.ndarray
    imshow_extent: np.ndarray
    v_array: np.ndarray
    scan_h_positions: np.ndarray
    scan_slow_move: np.ndarray
    scan_index_array: np.ndarray


def load_example_2d_scan(fname:str) -> Example2DScan:
    with h5py.File(fname) as file:
        m = file['measurement/example_2d_scan']
        return Example2DScan(
            settings=load_settings(fname),
            pixel_time=m['pixel_time'][:] if 'pixel_time' in m else None,
            range_extent=m['range_extent'][:] if 'range_extent' in m else None,
            corners=m['corners'][:] if 'corners' in m else None,
            signal_map=m['signal_map'][:] if 'signal_map' in m else None,
            scan_v_positions=m['scan_v_positions'][:] if 'scan_v_positions' in m else None,
            h_array=m['h_array'][:] if 'h_array' in m else None,
            imshow_extent=m['imshow_extent'][:] if 'imshow_extent' in m else None,
            v_array=m['v_array'][:] if 'v_array' in m else None,
            scan_h_positions=m['scan_h_positions'][:] if 'scan_h_positions' in m else None,
            scan_slow_move=m['scan_slow_move'][:] if 'scan_slow_move' in m else None,
            scan_index_array=m['scan_index_array'][:] if 'scan_index_array' in m else None,
        )


load_funcs['example_2d_scan'] = load_example_2d_scan


@dataclass
class Example3DScan:
    settings:dict
    pixel_time: np.ndarray
    range_extent: np.ndarray
    corners: np.ndarray
    signal_map: np.ndarray
    scan_v_positions: np.ndarray
    h_array: np.ndarray
    imshow_extent: np.ndarray
    v_array: np.ndarray
    scan_h_positions: np.ndarray
    scan_slow_move: np.ndarray
    z_array: np.ndarray
    scan_z_positions: np.ndarray
    scan_index_array: np.ndarray


def load_example_3d_scan(fname:str) -> Example3DScan:
    with h5py.File(fname) as file:
        m = file['measurement/example_3d_scan']
        return Example3DScan(
            settings=load_settings(fname),
            pixel_time=m['pixel_time'][:] if 'pixel_time' in m else None,
            range_extent=m['range_extent'][:] if 'range_extent' in m else None,
            corners=m['corners'][:] if 'corners' in m else None,
            signal_map=m['signal_map'][:] if 'signal_map' in m else None,
            scan_v_positions=m['scan_v_positions'][:] if 'scan_v_positions' in m else None,
            h_array=m['h_array'][:] if 'h_array' in m else None,
            imshow_extent=m['imshow_extent'][:] if 'imshow_extent' in m else None,
            v_array=m['v_array'][:] if 'v_array' in m else None,
            scan_h_positions=m['scan_h_positions'][:] if 'scan_h_positions' in m else None,
            scan_slow_move=m['scan_slow_move'][:] if 'scan_slow_move' in m else None,
            z_array=m['z_array'][:] if 'z_array' in m else None,
            scan_z_positions=m['scan_z_positions'][:] if 'scan_z_positions' in m else None,
            scan_index_array=m['scan_index_array'][:] if 'scan_index_array' in m else None,
        )


load_funcs['example_3d_scan'] = load_example_3d_scan
