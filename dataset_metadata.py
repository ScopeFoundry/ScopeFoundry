from dataclasses import dataclass
from ScopeFoundry.cb32_uuid import cb32_uuid


import time
from datetime import datetime
from pathlib import Path


@dataclass
class DatasetMetadata:
    unique_id: str  # persistent identifier for dataset
    u: str
    t0: int
    h5_file_path: Path
    app_name: str = None

    def get_file_path(self, suffix: str = ".h5") -> Path:
        return self.h5_file_path.with_suffix(suffix)

    def savefig_kwargs(self, suffix: str = ".png") -> dict:
        return {
            "filename_or_obj": self.get_file_path(suffix),
            "metadata": {
                "Title": self.h5_file_path.stem,
                # "Author": self.unique_id,
                "Description": self.unique_id,
                "Created": datetime.fromtimestamp(self.t0).strftime(
                    "%a, %d %b %Y %H:%M:%S GMT"
                ),
                "Software": "ScopeFoundry",
                # "Disclaimers": "This dataset is for internal use only.",
                # "Warning": "This dataset is not for public distribution.",
                "Source": self.app_name,    
                # "Comment": "This dataset is for internal use only.",
            },
        }


def new_dataset_metadata(measurement=None, fname: str = None) -> DatasetMetadata:
    unique_id, u = cb32_uuid()  # persistent identifier for dataset
    t0 = time.time()

    if measurement is not None:
        app = measurement.app
        if fname is None:
            fname = app.settings["data_fname_format"].format(
                app=app,
                measurement=measurement,
                timestamp=datetime.fromtimestamp(t0),
                unique_id=unique_id,
                unique_id_short=unique_id[0:13],
                ext="h5",
            )
        h5_file_path = Path(app.settings["save_dir"]) / fname
        return DatasetMetadata(unique_id, u, t0, h5_file_path, app_name=app.name)

    if fname is None:
        h5_file_path = Path.cwd() / f"{datetime.fromtimestamp(t0):%y%m%d_%H%M%S}.h5"
    else:
        h5_file_path = Path(fname).with_suffix(".h5")

    return DatasetMetadata(unique_id, u, t0, h5_file_path, app_name=None)
