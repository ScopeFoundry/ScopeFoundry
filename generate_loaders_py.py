from pathlib import Path
from typing import Dict, List, Set, Tuple

import h5py

LOADERS_FNAME = "h5_data_loaders.py"

LOADERS_PY_HEADER = """# generated with ScopeFoundry.tools
#
# pip install ScopeFoundry
# python -m ScopeFoundry.tools
#
# from h5_data_loaders import load, find_settings
# data = load('your_file_name.h5')

import functools
import fnmatch
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import h5py
import numpy as np

load_funcs = {}


def get_measurement_name(fname: str) -> str:
    with h5py.File(fname, "r") as file:
        if len(file["measurement"].keys()) == 1:
            return list(file["measurement"].keys())[0]
        return file.attrs["measurement"]


def load(fname: str) -> Any:
    mm_name = get_measurement_name(fname)
    return load_funcs[mm_name](fname)


def load_settings(fname: str) -> Dict[str, Any]:
    path = Path(fname)
    if not path.suffix == ".h5":
        return {}

    settings = {}
    visit_func = functools.partial(_settings_visitfunc, settings=settings)

    with h5py.File(fname, "r") as file:
        file.visititems(visit_func)
        for key, val in file.attrs.items():
            settings[key] = val        

    return settings


def find_settings(settings: Dict, pattern: str = "measurement/*") -> Dict:
    if type(settings) is str:
        settings = load_settings(settings)
    if hasattr(settings, "settings"):
        settings = settings.settings
    matching = [key for key in settings.keys() if fnmatch.fnmatch(key, pattern)]
    if not matching:
        print("no matching key found")
        return {}
    return {k: settings[k] for k in matching}


def _settings_visitfunc(name: str, node: h5py.Group, settings: Dict[str, Any]) -> None:
    if not name.endswith("settings"):
        return

    for key, val in node.attrs.items():
        lq_path = f"{name.replace('settings', key)}"
        settings[lq_path] = val


def get_mm_name(fname: str) -> str:
    with h5py.File(fname, "r") as file:
        if len(file["measurement"].keys()) == 1:
            return list(file["measurement"].keys())[0]
        return file.attrs["measurement"]
"""


def get_measurement_name(fname: str) -> str:
    with h5py.File(fname, "r") as file:
        if len(file["measurement"].keys()) == 1:
            return list(file["measurement"].keys())[0]
        return file.attrs["measurement"]


def generate_loaders(dsets: Dict[str, Set[str]]) -> List[str]:
    lines = []
    for mm_name, key_set in dsets.items():

        class_name = "".join(x.title() for x in mm_name.split("_"))

        data_class_lines = [
            "@dataclass",
            f"class {class_name}:",
            f"{' ':>4}settings: dict",
        ]
        load_func_lines = [
            f"def load_{mm_name}(fname: str) -> {class_name}:",
            f"{' ':>4}with h5py.File(fname, 'r') as file:",
            f"{' ':>8}m = file['measurement/{mm_name}']",
            f"{' ':>8}return {class_name}(",
            f"{' ':>12}settings=load_settings(fname),",
        ]
        for name in key_set:
            data_class_lines.append(f"{' ':>4}{name}: np.ndarray")
            load_func_lines.append(
                f"{' ':>12}{name}=m['{name}'][:] if '{name}' in m else None,"
            )
        load_func_lines.append(f"{' ':>8})")

        lines.append("")
        lines += data_class_lines
        lines.append("")
        lines.append("")
        lines += load_func_lines
        lines.append("")
        lines.append("")
        lines.append(f"load_funcs['{mm_name}'] = load_{mm_name}")
        lines.append("")

    return lines


def get_dset_names(folder: str) -> Dict[str, Set[str]]:
    path = Path(folder)
    dset_names = {}
    for fname in path.rglob("*.h5"):
        mm_name = get_measurement_name(fname)
        with h5py.File(fname, "r") as file:
            new_keys = set(
                [
                    name
                    for name, val in file[f"measurement/{mm_name}"].items()
                    if isinstance(val, h5py.Dataset)
                ]
            )
            if mm_name in dset_names:
                dset_names[mm_name] = dset_names[mm_name].union(new_keys)
            else:
                dset_names[mm_name] = new_keys

    return dset_names


def generate_loaders_py(folder: str = ".") -> Tuple[Path, Dict[str, Set[str]]]:
    path = Path(folder)
    fnames = tuple(path.rglob("*.h5"))
    lines = [LOADERS_PY_HEADER]

    if len(fnames):
        dset_names = get_dset_names(folder)
        lines += generate_loaders(dset_names)
    else:
        print(f"WARNING no h5 files found in {folder}. No loaders created.")
        return Path(), {}

    loaders_fname = path / LOADERS_FNAME
    with open(loaders_fname, "w") as file:
        file.write("\n".join(lines))

    return loaders_fname, dset_names
