from pathlib import Path
from typing import Dict

from ScopeFoundry.tools.features.utils import (
    mk_authors,
    mk_dates,
    to_class_name,
    write_templated_file,
)


def gather_infos(name: str, module_path: str = ".") -> Dict[str, str]:
    readout_file_name = f"{name.lower()}.py"
    readout_class_name = to_class_name(name)
    module_name = name
    module_path = Path(module_path.lower())
    readout_import_line = f"from {'.'.join(list(Path(module_path).parts)+[module_name.rstrip('.py')])} import {readout_class_name}"
    add_to_app = f"""
        {readout_import_line}
        self.add_measurement({readout_class_name}(self))
"""
    infos = {
        "READOUT_FILE_NAME": readout_file_name,
        "READOUT_CLASS_NAME": readout_class_name,
        "READOUT_NAME": f"{name.lower()}_readout",
        "TEST_APP_NAME": f"{name.lower()}_test_app",
        "HW_NAME": "",
        "MODULE_PATH": module_path,
        "READOUT_IMPORT_LINE": readout_import_line,
        "ADD_TO_APP": add_to_app,
    }
    infos.update(mk_dates())
    infos.update(mk_authors(""))
    return infos


def new_measure(name: str) -> Dict[str, str]:
    infos = gather_infos(name, ".")
    root = Path(__file__).parent.parent

    write_templated_file(
        template_path=root / "templates/_readout.py",
        target_fname=infos["READOUT_FILE_NAME"],
        substitutions=infos,
        path_to_target=Path(infos["MODULE_PATH"]),
    )
    return infos


def main() -> None:
    name = input("name of measurement: ")
    subs = new_measure(name)

    print("add to your setup")
    print(subs["ADD_TO_APP"])


if __name__ == "__main__":
    main()
