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
import os
import shutil
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import h5py
import numpy as np


def find_all_fnames_in_sources_of_ipynb(ignore_cells=[]):
    fname_pattern = re.compile(r"\d{6}_\d{6}_[a-z0-9_]+\.h5")

    with open("overview.ipynb", "r", encoding="utf-8") as f:
        notebook = json.load(f)

    fnames = set()
    for ii, cell in enumerate(notebook["cells"]):
        if ii in ignore_cells:
            continue
        if cell["cell_type"] == "code":
            source = "".join(cell["source"])
            matches = fname_pattern.findall(source)
            fnames.update(matches)

    print(f"Found {len(fnames)} unique .h5 filenames in notebook sources.")

    return set(fnames)


def move_file_to_archive_folder(fname, target_folder=None):
    if target_folder is None:
        data_folder = os.path.join(os.getcwd(), "archived_data")
    else:
        data_folder = target_folder
    if not os.path.exists(data_folder):
        os.makedirs(data_folder)

    src_path = os.path.join(os.getcwd(), fname)
    dest_path = os.path.join(data_folder, fname)

    if os.path.exists(src_path):
        shutil.move(src_path, dest_path)
        print(f"Moved {fname} to {data_folder}")
    else:
        print(f"File {fname} does not exist in the current directory.")


def archive_unmentioned_h5_files(ignore_cells=(0, 1)):
    fnames_to_keep = find_all_fnames_in_sources_of_ipynb(ignore_cells=ignore_cells)
    counter = 0
    for fname in Path.cwd().glob("*.h5"):
        if fname.name not in fnames_to_keep:
            move_file_to_archive_folder(fname.name)
            move_file_to_archive_folder(fname.name.replace(".h5", ".png"))
            counter += 1
    print(f"Archived {counter} files.")

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
        for key, val in file.attrs.items():
            settings[key] = val       
        file.visititems(visit_func)
 
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

def load_non_settings_attrs(fname: str) -> Dict[str, Any]:
    path = Path(fname)
    if not path.suffix == ".h5":
        return {}

    attrs = {}
    visit_func = functools.partial(_non_settings_attrs_visitfunc, attrs=attrs)

    with h5py.File(fname, "r") as file:
        for key, val in file.attrs.items():
            attrs[key] = val
        file.visititems(visit_func)

    return attrs

def _non_settings_attrs_visitfunc(
    name: str, node: h5py.Group, attrs: Dict[str, Any]
) -> None:
    if name.endswith("settings") or name.endswith("settings/units"):
        return

    for key, val in node.attrs.items():
        lq_path = f"{name}/{key}"
        attrs[lq_path] = val

def get_mm_name(fname: str) -> str:
    with h5py.File(fname, "r") as file:
        if len(file["measurement"].keys()) == 1:
            return list(file["measurement"].keys())[0]
        return file.attrs["measurement"]
"""
__STR__INFO = r"""

    def __str__(self) -> str:
        lines = [f"{self.path}"]
        for key, value in self.__dict__.items():
            if isinstance(value, np.ndarray):
                lines.append(f"-D {key}: {value.shape}")
        lines += [f"{key}: {value}" for key, value in self.settings.items()]
        return "\n".join(lines)
"""


def get_measurement_name(fname: str) -> str:
    with h5py.File(fname, "r") as file:
        if "measurement" in file.attrs:
            mm_name = file.attrs["measurement"]
        else:
            mm_name = list(file["measurement"].keys())[0]
    return mm_name


def generate_loaders(dsets: Dict[str, Set[str]]) -> List[str]:
    lines = []
    for mm_name, key_set in dsets.items():

        class_name = "".join(x.title() for x in mm_name.split("_"))

        data_class_lines = [
            "@dataclass",
            f"class {class_name}:",
            f"{' ':>4}path: Path",
            f"{' ':>4}settings: dict",
        ]
        load_func_lines = [
            f"def load_{mm_name}(fname: str) -> {class_name}:",
            f"{' ':>4}with h5py.File(fname, 'r') as file:",
            f"{' ':>8}m = file['measurement/{mm_name}']",
            f"{' ':>8}return {class_name}(",
            f"{' ':>12}path=Path(fname),",
            f"{' ':>12}settings=load_settings(fname),",
        ]
        for name, is_array in key_set:
            data_class_lines.append(f"{' ':>4}{name}: np.ndarray")
            if is_array:
                load_func_lines.append(
                    f"{' ':>12}{name}=m['{name}'][:] if '{name}' in m else None,"
                )
            else:
                load_func_lines.append(
                    f"{' ':>12}{name}=m['{name}'] if '{name}' in m else None,"
                )

        data_class_lines.append(__STR__INFO)

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
        try:
            mm_name = get_measurement_name(fname)
            with h5py.File(fname, "r") as file:
                new_keys = set(
                    [
                        (name, bool(val.shape))
                        for name, val in file[f"measurement/{mm_name}"].items()
                        if isinstance(val, h5py.Dataset)
                    ]  # (name, is_array)
                )
                if mm_name in dset_names:
                    dset_names[mm_name] = dset_names[mm_name].union(new_keys)
                else:
                    dset_names[mm_name] = new_keys
        except OSError as err:
            print("Skipping", fname, err)
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
