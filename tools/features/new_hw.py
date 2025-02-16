from enum import Enum
from functools import partial
import json
from pathlib import Path
from typing import Dict

from ScopeFoundry.tools.features.utils import (
    mk_authors,
    mk_dates,
    to_class_name,
    write_templated_file,
)


class ComTypes(Enum):
    OTHER = "OTHER"
    DLL = "DLL"
    SERIAL = "SERIAL"
    # VISA = 'VISA'


def new_hw(
    company: str = "thorlabs",
    model: str = "XX6000_glavo_mirror",
    authors: str = "Benedikt Ursprung, Mark E.Ziffer",
    pretty_name: str = "galvo_mirror",
    overwrite_existing_module: bool = True,
    com_type: str = ComTypes.DLL.value,
) -> Dict[str, str]:
    infos = gather_infos(
        company, model, authors, pretty_name, overwrite_existing_module
    )

    path_to_module = Path(infos["PATH_TO_MODULE"])
    path_to_module.mkdir(exist_ok=True)
    root = Path(__file__).parent.parent

    write = partial(
        write_templated_file,
        substitutions=infos,
        path_to_target=path_to_module,
    )

    write(root / "templates/_readout.py", infos["READOUT_FILE_NAME"])
    write(root / "templates/_test_app.py", infos["TEST_APP_FILE_NAME"])
    write(root / "templates/___init__.py", "__init__.py")
    write(root / "templates/_LICENSE", "LICENSE")
    write(root / "templates/_README.md", "README.md")
    write(root / "templates/.gitignore", ".gitignore")

    if com_type == ComTypes.DLL.value:
        write(root / "templates/_dll_dev.py", infos["DEV_FILE_NAME"])
        write(root / "templates/_dll_hw.py", infos["HW_FILE_NAME"])
    if com_type == ComTypes.SERIAL.value:
        write(root / "templates/_serial_dev.py", infos["DEV_FILE_NAME"])
        write(root / "templates/_serial_hw.py", infos["HW_FILE_NAME"])
    if com_type == ComTypes.OTHER.value:
        write(root / "templates/_serial_dev.py", infos["DEV_FILE_NAME"])
        write(root / "templates/_serial_hw.py", infos["HW_FILE_NAME"])

    docs_path = path_to_module / "docs"
    docs_path.mkdir()
    with open(docs_path / "my_docs.md", "x", encoding="utf-8") as file:
        file.write(
            "place your documentation and sharable hardware manuals in this folder"
        )
    with open(docs_path / "links.json", "x", encoding="utf-8") as file:
        json.dump({"my_link": "www.scopefoundry.com"}, file)

    return infos


def gather_infos(
    company: str,
    model: str,
    authors: str,
    pretty_name: str,
    overwrite_existing_module: bool,
) -> Dict[str, str]:
    module_name = f"{company.lower()}_{model.lower()}"

    path_to_module = assert_ScopeFoundryHW_directory() / module_name

    if path_to_module.exists() and not overwrite_existing_module:
        raise FileExistsError(
            f"{module_name} already exists! You can use overwrite flag at your own risk"
        )

    if pretty_name is None or pretty_name == "":
        pretty_name = model.lower()
    pretty_name = pretty_name.lower()

    dev_file_name = f"{pretty_name}_dev.py"
    dev_class_name = to_class_name(f"{model.upper()}_DEV")
    import_dev = f"from .{dev_file_name.rstrip('.py')} import {dev_class_name}"

    hw_file_name = f"{pretty_name.lower()}_hw.py"
    hw_class_name = f"{to_class_name(model.upper())}HW"

    readout_file_name = f"{pretty_name.lower()}_readout.py"
    readout_class_name = to_class_name(f"{model.upper()}_Readout")

    test_app_file_name = f"{ pretty_name.lower()}_test_app.py"

    init_imports = f"from .{hw_file_name.rstrip('.py')} import {hw_class_name} \nfrom .{readout_file_name.rstrip('.py')} import {readout_class_name}"
    test_app_imports = f"from ScopeFoundryHW.{module_name.rstrip('.py')} import {hw_class_name}, {readout_class_name}"

    add_to_app = f"""
        {test_app_imports}
        self.add_hardware({hw_class_name}(self))
        self.add_measurement({readout_class_name}(self))
"""

    infos = {
        "DEV_FILE_NAME": dev_file_name,
        "IMPORT_DEV": import_dev,
        "DEV_CLASS_NAME": dev_class_name,
        "HW_FILE_NAME": hw_file_name,
        "HW_CLASS_NAME": hw_class_name,
        "READOUT_CLASS_NAME": readout_class_name,
        "READOUT_NAME": f"{pretty_name.lower()}_readout",
        "READOUT_FILE_NAME": readout_file_name,
        "TEST_APP_NAME": f"{pretty_name.lower()}_test_app",
        "HW_NAME": pretty_name.lower(),
        "INIT_IMPORTS": init_imports,
        "IMPORTS_IN_TEST_APP": test_app_imports,
        "MODULE_NAME": module_name,
        "COMPANY": " ".join(company.split("_")),
        "MODEL": " ".join(model.split("_")),
        "ADD_TO_APP": add_to_app,
        "TEST_APP_FILE_NAME": test_app_file_name,
        "PATH_TO_MODULE": path_to_module,
    }
    infos.update(mk_dates())
    infos.update(mk_authors(authors))
    return infos


def assert_ScopeFoundryHW_directory():
    cwd = Path.cwd()
    if has_ScopeFoundryHW_directory(cwd):
        return cwd / "ScopeFoundryHW"
    elif has_ScopeFoundryHW_directory(cwd.parent):
        return cwd.parent / "ScopeFoundryHW"
    elif has_ScopeFoundryHW_directory(cwd.parent.parent):
        return cwd.parent.parent / "ScopeFoundryHW"
    else:
        try:
            from qtpy import QtWidgets

            a = QtWidgets.QFileDialog.getExistingDirectory(
                caption="Select your ScopeFoundryHW folder or create one",
                directory=str(cwd),
            )
            return Path(a)
        except Exception as e:
            print(
                "No ScopeFoundryHW directory found and no qtpy available: cd to your project folder or pip install qtpy"
            )


def has_ScopeFoundryHW_directory(path: Path) -> bool:
    for p in path.iterdir():
        if p.is_dir() and p.name == "ScopeFoundryHW":
            return True
    return False


if __name__ == "__main__":
    new_hw()
