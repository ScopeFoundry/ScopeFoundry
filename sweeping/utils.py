import datetime
import pathlib
from typing import List

from ScopeFoundry import BaseMicroscopeApp


def mk_new_dir(root, name):
    new_folder_name = f"{datetime.datetime.now():%y%m%d_%H%M%S}_{name}"
    new_path = pathlib.Path(root) / new_folder_name
    new_path.mkdir()
    return new_path


def filtered_lq_paths(app: BaseMicroscopeApp) -> List[str]:
    return [
        p
        for p in app.get_setting_paths()
        if app.get_lq(p).dtype != str
        and p.split("/")[-1]
        not in (
            "any_measurement",
            "any_setting",
            "activation",
            "profile",
            "connected",
            "debug_mode",
            "dark_mode",
        )
    ]
