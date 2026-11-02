from pathlib import Path
from typing import Dict, List, Set, Tuple, Union

import h5py

LOADERS_FNAME = "h5_data_loaders.py"

LOADERS_PY_HEADER = r"""# generated with ScopeFoundry.tools
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


def find_all_fnames_in_sources_of_ipynb(
    ignore_cells=[], ipynb_filename="overview.ipynb"
):
    fname_pattern = re.compile(r"\d{6}_\d{6}_[a-z0-9_]+\.h5")

    with open(ipynb_filename, "r", encoding="utf-8") as f:
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


def move_file(fname, target_folder=None):
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


def archive_unmentioned_h5_files(
    ignore_cells=(0, 1), target_folder=None, ipynb_filename="overview.ipynb"
):
    fnames_to_keep = find_all_fnames_in_sources_of_ipynb(
        ignore_cells=ignore_cells, ipynb_filename=ipynb_filename
    )
    counter = 0
    h5_file_counter = 0
    print("--- archiving unmentioned .h5 files ---")
    for fname in Path.cwd().glob("*.h5"):
        if fname.name not in fnames_to_keep:
            move_file(fname.name, target_folder)
            h5_file_counter += 1
            for f in Path.cwd().glob(fname.name.replace(".h5", ".*")):
                move_file(f.name, target_folder)
                counter += 1
    print(f"Archived {h5_file_counter} .h5 files and {counter} associated files.")
    print("--- done ---")

load_funcs = {}


def get_measurement_name(fname: str) -> str:
    with h5py.File(fname, "r") as file:
        if len(file["measurement"].keys()) == 1:
            return list(file["measurement"].keys())[0]
        return file.attrs.get("measurement", "root_measurement_name_unknown")


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

OTHER_MEASUREMENTS_GROUP = "other_measurements_settings"
def _settings_visitfunc(name: str, node: h5py.Group, settings: Dict[str, Any]) -> None:
    parts = name.split("/")
    if parts[-1] != "settings":
        return

    if len(parts) == 3 and parts[0] == OTHER_MEASUREMENTS_GROUP:
        parts[0] = "measurement"

    for key, val in node.attrs.items():
        settings["/".join(parts[:-1] + [key])] = val

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

DICT_STYLE_METHODS = r"""
    def __getitem__(self, key):
        if key in self.settings:
            return self.settings[key]
        return self.__dict__[key]

    def __setitem__(self, key, item):
        self.__dict__[key] = item

    def keys(self):
        return set(self.__dict__.keys()).union(set(self.settings.keys()))

    def items(self):
        d = self.__dict__.copy()
        d.update(self.settings)
        return d.items()
"""


def get_measurement_name(fname: str) -> str:
    with h5py.File(fname, "r") as file:
        if len(file["measurement"].keys()) == 1:
            return list(file["measurement"].keys())[0]
        return file.attrs.get("measurement", "root_measurement_name_unknown")


def generate_loaders(dsets: Dict[str, Dict[str, bool]]) -> List[str]:
    lines = []
    for mm_name, name_to_is_array in dsets.items():

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
        seen_attr_names = set()
        for name, is_array in name_to_is_array.items():
            # strip spaces for valid class attributes but keep the original name in the load function
            attr_name = name.strip().replace(" ", "_")
            if attr_name in seen_attr_names:
                continue
            seen_attr_names.add(attr_name)
            data_class_lines.append(f"{' ':>4}{attr_name}: np.ndarray")
            if is_array:
                load_func_lines.append(
                    f"{' ':>12}{attr_name}=m['{name}'][:] if '{name}' in m else None,"
                )
            else:
                load_func_lines.append(
                    f"{' ':>12}{attr_name}=m['{name}'] if '{name}' in m else None,"
                )

        data_class_lines.append(__STR__INFO)
        data_class_lines.append(DICT_STYLE_METHODS)

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


def get_dset_names(folder: str) -> Dict[str, Dict[str, bool]]:
    path = Path(folder)
    dset_names: Dict[str, Dict[str, bool]] = {}
    for fname in path.rglob("*.h5"):
        try:
            mm_name = get_measurement_name(fname)
            with h5py.File(fname, "r") as file:
                new_keys = {
                    name: bool(val.shape)
                    for name, val in file[f"measurement/{mm_name}"].items()
                    if isinstance(val, h5py.Dataset)
                }  # name -> is_array
                existing = dset_names.setdefault(mm_name, {})
                for name, is_array in new_keys.items():
                    # if the dataset is an array in any file, treat it as an array everywhere
                    existing[name] = existing.get(name, False) or is_array
        except OSError as err:
            print("Skipping", fname, err)
    return dset_names


def generate_loaders_py(folder: str = ".") -> Tuple[Path, Dict[str, Dict[str, bool]]]:
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
