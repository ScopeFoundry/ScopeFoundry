import datetime
import pathlib


def mk_new_dir(root, name):
    new_folder_name = f"{datetime.datetime.now():%y%m%d_%H%M%S}_{name}"
    new_path = pathlib.Path(root) / new_folder_name
    new_path.mkdir()
    return new_path
